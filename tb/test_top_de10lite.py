"""Full system (Day 19): drive the UART protocol on the board pins, like host.py will.

Simulated at 32 clocks per bit (CLK_HZ = 3.2 MHz, BAUD = 100 kHz).
"""
import cocotb
import numpy as np
import pytest
from cocotb.queue import Queue
from cocotb.triggers import ClockCycles

from tb_utils import COMMON, CORE, TOP, board_reset, read_displays, run_sim, uart_recv, uart_send
from model.golden_model import edge_cases, expected_cycles, matmul_int32, random_int8

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

    async def matmul(self, a, b):
        n, k = a.shape
        assert await self.cmd(b"S" + bytes([k]), 1) == b"K"
        assert await self.cmd(b"A" + a.astype(np.int8).tobytes(), 1) == b"K"
        assert await self.cmd(b"B" + b.astype(np.int8).tobytes(), 1) == b"K"
        assert await self.cmd(b"G", 1) == b"D"
        c = np.frombuffer(await self.cmd(b"R", 4 * n * n), dtype="<i4").reshape(n, n)
        cycles = int.from_bytes(await self.cmd(b"C", 4), "little")
        return c.astype(np.int64), cycles


@cocotb.test()
async def protocol_and_matmul(dut):
    await board_reset(dut)
    n = 2 ** len(dut.u_core.wr_lane)
    host = Host(dut)

    # Ping reports the build parameters.
    assert await host.cmd(b"P", 3) == bytes([ord("K"), n, K_MAX])

    # Bad command and bad K are rejected, and light LEDR[6].
    assert await host.cmd(b"x", 1) == b"E"
    assert await host.cmd(b"S\x00", 1) == b"E"
    assert await host.cmd(b"S" + bytes([K_MAX + 1]), 1) == b"E"
    assert int(dut.LEDR.value) >> 6 & 1

    rng = np.random.default_rng(n)
    cases = [(f"{name}", ab) for name, ab in edge_cases(n, 5).items()]
    cases += [(f"random{r}", (random_int8((n, k), rng), random_int8((k, n), rng)))
              for r, k in enumerate([1, 3, n, 16, K_MAX if n == 4 else 24])]
    for name, (a, b) in cases:
        c, cycles = await host.matmul(a, b)
        assert np.array_equal(c, matmul_int32(a, b)), f"{name}:\n{c}\n{matmul_int32(a, b)}"
        assert cycles == expected_cycles(n, a.shape[1]), f"{name}: cycles {cycles}"
        assert read_displays(dut) == cycles, "HEX should show the cycle count"

    led = int(dut.LEDR.value)
    assert led >> 8 & 1, "LEDR[8]: a multiply has completed"
    assert led >> 5 & 1 == 0, "no UART framing errors expected"


@cocotb.test()
async def recovers_from_stalled_host(dut):
    await board_reset(dut)
    host = Host(dut)
    await host.send(b"A\x01\x02\x03")              # host "crashes" mid-load
    await ClockCycles(dut.MAX10_CLK1_50, CLK_HZ // 10 + 100)
    assert int(dut.LEDR.value) >> 7 & 1, "LEDR[7]: timeout flag"
    assert (await host.cmd(b"P", 3))[0] == ord("K"), "parser must accept commands again"


@pytest.mark.parametrize("n", [4, 8])
def test_top_de10lite(n):
    run_sim("top_de10lite",
            [COMMON / f for f in ["sync_2ff.sv", "tick_gen.sv", "hex7seg.sv",
                                  "uart_rx.sv", "uart_tx.sv", "fifo_sync.sv"]]
            + [CORE / f for f in ["pe.sv", "systolic_array.sv", "skew_buffer.sv",
                                  "sram_sp.sv", "mm_controller.sv", "mm_core.sv"]]
            + [TOP / "cmd_parser.sv", TOP / "top_de10lite.sv"],
            "test_top_de10lite",
            parameters={"N": n, "K_MAX": K_MAX, "CLK_HZ": CLK_HZ, "BAUD": BAUD},
            build_name=f"top_de10lite_n{n}")
