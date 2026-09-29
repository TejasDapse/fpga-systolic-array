"""uart_rx: decodes frames correctly, tolerates baud mismatch, flags framing errors.

32 clocks per bit in simulation (CLK_HZ = 3.2 MHz, BAUD = 100 kHz).
"""
import random

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge

from tb_utils import COMMON, run_sim, start_clock, uart_send

CLK_HZ, BAUD = 3_200_000, 100_000
CPB = CLK_HZ // BAUD


async def setup(dut):
    start_clock(dut.clk)
    dut.rx.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


def start_monitor(dut):
    """Collect every received byte and count framing errors in the background."""
    log = {"bytes": [], "frame_errs": 0}

    async def monitor():
        while True:
            await RisingEdge(dut.clk)
            if int(dut.valid.value):
                log["bytes"].append(int(dut.data.value))
            if int(dut.frame_err.value):
                log["frame_errs"] += 1

    cocotb.start_soon(monitor())
    return log


async def check_stream(dut, sender_cpb):
    log = start_monitor(dut)
    data = [0x00, 0xFF, 0x55, 0xAA] + [random.randrange(256) for _ in range(40)]
    for b in data:                                   # back-to-back, no idle gap
        await uart_send(dut.rx, dut.clk, sender_cpb, b)
    await ClockCycles(dut.clk, 2 * CPB)
    assert log["bytes"] == data, f"sent {data}\n got {log['bytes']}"
    assert log["frame_errs"] == 0


@cocotb.test()
async def exact_baud(dut):
    await setup(dut)
    await check_stream(dut, CPB)


@cocotb.test()
async def sender_3pct_fast(dut):
    """Real adapters are never exactly on frequency -- receiver must tolerate ~3%."""
    await setup(dut)
    await check_stream(dut, CPB - 1)


@cocotb.test()
async def sender_3pct_slow(dut):
    await setup(dut)
    await check_stream(dut, CPB + 1)


@cocotb.test()
async def framing_error_detected(dut):
    await setup(dut)
    log = start_monitor(dut)
    await uart_send(dut.rx, dut.clk, CPB, 0x42, stop_bit=0)   # bad stop bit
    await ClockCycles(dut.clk, 3 * CPB)                        # let the line idle
    assert log["frame_errs"] == 1
    assert log["bytes"] == [], "a byte with a bad stop bit must be discarded"
    await uart_send(dut.rx, dut.clk, CPB, 0x99)                 # recovers afterwards
    await ClockCycles(dut.clk, 2 * CPB)
    assert log["bytes"] == [0x99]


def test_uart_rx():
    run_sim("uart_rx", [COMMON / "sync_2ff.sv", COMMON / "uart_rx.sv"], "test_uart_rx",
            parameters={"CLK_HZ": CLK_HZ, "BAUD": BAUD})
