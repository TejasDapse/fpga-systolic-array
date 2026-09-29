"""Foundations 03: HEX displays count; KEY1 toggles pause/run.

Simulated with CLK_HZ = 1000, TICK_HZ = 100 -> one count every 10 cycles.
"""
import cocotb
from cocotb.triggers import ClockCycles

from tb_utils import COMMON, ROOT, board_reset, press_key1, read_displays, run_sim


@cocotb.test()
async def counts_pauses_resumes(dut):
    await board_reset(dut)
    clk = dut.MAX10_CLK1_50

    await ClockCycles(clk, 205)                       # ~20 ticks
    v1 = read_displays(dut)
    assert 19 <= v1 <= 21, f"expected ~20, display shows {v1}"
    assert int(dut.LEDR.value) & 1 == 1, "LEDR[0] should show RUNNING"

    await press_key1(dut)                             # -> PAUSED
    v2 = read_displays(dut)
    await ClockCycles(clk, 100)
    assert read_displays(dut) == v2, "counter must not change while paused"
    assert int(dut.LEDR.value) & 1 == 0, "LEDR[0] should show PAUSED"

    await press_key1(dut)                             # -> RUNNING
    await ClockCycles(clk, 100)
    assert read_displays(dut) > v2, "counter should resume"


def test_03_hex_counter():
    run_sim("hex_counter_top",
            [COMMON / "sync_2ff.sv", COMMON / "tick_gen.sv", COMMON / "hex7seg.sv",
             ROOT / "foundations/03_hex_counter/hex_counter_top.sv"],
            "test_top_03_hex_counter", parameters={"CLK_HZ": 1000, "TICK_HZ": 100})
