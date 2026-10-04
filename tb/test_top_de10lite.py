"""Full system (Day 19): UART bridge protocol on the board pins, exactly like host.py.

Simulated at 32 clocks per bit (CLK_HZ = 3.2 MHz, BAUD = 100 kHz).
"""
import os
import struct

import cocotb
import numpy as np
import pytest
from cocotb.queue import Queue
from cocotb.triggers import ClockCycles

from tb_utils import COMMON, CORE, TOP, board_reset, read_displays, run_sim, uart_recv, uart_send
from model.golden_model import edge_cases, expected_perf, matmul_int32, random_int8
from model import regmap as rm

CLK_HZ, BAUD = 3_200_000, 100_000
CPB = CLK_HZ // BAUD
K_MAX = 64


class Host:
    """Minimal protocol driver mirroring host/host.py, but on simulated pins."""

    def __init__(self, dut):
        self.dut, self.clk = dut, dut.MAX10_CLK1_50
        self.rxq = Queue()
        cocotb.start_soon(self._monitor())

    async def _monitor(self):                      # the PC's UART receiver
        while True:
            self.rxq.put_nowait(await uart_recv(self.dut.UART_TXD, self.clk, CPB,
                                                timeout_cycles=10**9))

    async def send(self, data):
        for b in bytes(data):
            await uart_send(self.dut.UART_RXD, self.clk, CPB, b)

    async def recv(self, count):
        return bytes([await self.rxq.get() for _ in range(count)])

    async def cmd(self, data, reply_len):
        await self.send(data)
        return await self.recv(reply_len)

    async def write(self, addr, data):
        assert await self.cmd(b"W" + struct.pack("<HI", addr, data & 0xFFFFFFFF), 1) == b"K"

    async def read(self, addr):
        return struct.unpack("<I", await self.cmd(b"R" + struct.pack("<H", addr), 4))[0]

    async def write_block(self, addr, data):
        assert await self.cmd(b"B" + struct.pack("<HH", addr, len(data)) + bytes(data), 1) == b"K"

    async def read_block(self, addr, length):
        return await self.cmd(b"D" + struct.pack("<HH", addr, length), length)

    async def matmul(self, a, b, k_max=K_MAX):
        n, k = a.shape
        await self.write(rm.CFG_K, k)
        for i in range(n):                              # A rows are K_MAX apart
            await self.write_block(rm.a_addr(i, 0, k_max), a[i].astype(np.int8).tobytes())
        await self.write_block(rm.B_BUF, b.astype(np.int8).tobytes())   # B is contiguous
        await self.write(rm.CTRL, rm.CTRL_START)
        while not await self.read(rm.STATUS) & rm.STATUS_DONE:
            pass
        raw = await self.read_block(rm.C_BUF, 4 * n * n)
        c = np.frombuffer(raw, dtype="<i4").reshape(n, n).astype(np.int64)
        perf = {name: await self.read(addr) for name, addr in rm.PERF.items()}
        return c, perf


def no_x(dut):
    """Board outputs must be fully defined after reset (Icarus is 4-state)."""
    sigs = [dut.LEDR, dut.UART_TXD] + [getattr(dut, f"HEX{i}") for i in range(6)]
    return [s._name for s in sigs if any(ch in str(s.value).lower() for ch in "xz")]


@cocotb.test()
async def protocol_and_matmul(dut):
    await board_reset(dut)
    assert not no_x(dut), f"X/Z on board outputs after reset: {no_x(dut)}"
    n = 2 ** len(dut.u_core.u_regs.wr_lane)
    host = Host(dut)

    # Ping reports the build parameters.
    assert await host.cmd(b"P", 3) == bytes([ord("K"), n, K_MAX])

    # INFO over the bus agrees with ping; an unknown command lights LEDR[6].
    assert await host.read(rm.INFO) == (1 << 16) | (K_MAX << 8) | n
    assert await host.cmd(b"x", 1) == b"E"
    assert int(dut.LEDR.value) >> 6 & 1

    rng = np.random.default_rng(n)
    cases = [(f"{name}", ab) for name, ab in edge_cases(n, 5).items()]
    cases += [(f"random{r}", (random_int8((n, k), rng), random_int8((k, n), rng)))
              for r, k in enumerate([1, 3, n, 16, K_MAX if n == 4 else 24])]
    for name, (a, b) in cases:
        c, perf = await host.matmul(a, b)
        assert np.array_equal(c, matmul_int32(a, b)), f"{name}:\n{c}\n{matmul_int32(a, b)}"
        for key, value in expected_perf(n, a.shape[1]).items():
            assert perf[key] == value, f"{name}: {key} = {perf[key]}, expected {value}"
        assert read_displays(dut) == perf["PERF_COMPUTE"], "HEX shows PERF_COMPUTE"

    assert not no_x(dut), f"X/Z on board outputs: {no_x(dut)}"
    led = int(dut.LEDR.value)
    assert led >> 8 & 1, "LEDR[8]: a multiply has completed"
    assert led >> 5 & 1 == 0, "no UART framing errors expected"


@cocotb.test()
async def recovers_from_stalled_host(dut):
    await board_reset(dut)
    host = Host(dut)
    await host.send(b"B\x00\x10\x10\x00\x01\x02")  # host "crashes" mid-block-write
    await ClockCycles(dut.MAX10_CLK1_50, CLK_HZ // 10 + 100)
    assert int(dut.LEDR.value) >> 7 & 1, "LEDR[7]: timeout flag"
    assert (await host.cmd(b"P", 3))[0] == ord("K"), "parser must accept commands again"


SLOW = pytest.mark.skipif(os.environ.get("SLOW") != "1",
                          reason="N=8 full-system sim takes ~6 min; run with SLOW=1")


@pytest.mark.parametrize("n", [4, pytest.param(8, marks=SLOW)])
def test_top_de10lite(n):
    run_sim("top_de10lite",
            [COMMON / f for f in ["sync_2ff.sv", "tick_gen.sv", "hex7seg.sv",
                                  "uart_rx.sv", "uart_tx.sv", "fifo_sync.sv"]]
            + [CORE / f for f in ["pe.sv", "systolic_array.sv", "skew_buffer.sv", "sram_sp.sv",
                                  "mm_controller.sv", "mm_regs.sv", "mm_core.sv"]]
            + [TOP / "uart_bus_bridge.sv", TOP / "top_de10lite.sv"],
            "test_top_de10lite",
            parameters={"N": n, "K_MAX": K_MAX, "CLK_HZ": CLK_HZ, "BAUD": BAUD},
            build_name=f"top_de10lite_n{n}")
