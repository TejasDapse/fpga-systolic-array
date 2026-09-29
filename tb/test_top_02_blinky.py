"""Foundations 02: LEDR[0] toggles once per tick, LEDR[9:1] counts ticks.

Simulated with CLK_HZ = 100, TICK_HZ = 10 -> one tick every 10 cycles.
"""
import cocotb
from cocotb.triggers import FallingEdge

from tb_utils import COMMON, ROOT, board_reset, run_sim

CLK_HZ, TICK_HZ = 100, 10
DIV = CLK_HZ // TICK_HZ


@cocotb.test()
async def blink_period_and_counter(dut):
    await board_reset(dut)
    toggle_cycles, counts = [], []
    prev, cycle = int(dut.LEDR.value) & 1, 0
    while len(toggle_cycles) < 5:
        await FallingEdge(dut.MAX10_CLK1_50)
        cycle += 1
        assert cycle < 20 * DIV, "LEDR[0] is not blinking"
        leds = int(dut.LEDR.value)
        if (leds & 1) != prev:
            prev = leds & 1
            toggle_cycles.append(cycle)
            counts.append(leds >> 1)

    periods = [b - a for a, b in zip(toggle_cycles, toggle_cycles[1:])]
    assert all(p == DIV for p in periods), f"toggle periods {periods}, expected {DIV}"
    assert all(b == a + 1 for a, b in zip(counts, counts[1:])), f"counter {counts}"


def test_02_blinky():
    run_sim("blinky_top",
            [COMMON / "sync_2ff.sv", COMMON / "tick_gen.sv",
             ROOT / "foundations/02_blinky/blinky_top.sv"],
            "test_top_02_blinky", parameters={"CLK_HZ": CLK_HZ, "TICK_HZ": TICK_HZ})
