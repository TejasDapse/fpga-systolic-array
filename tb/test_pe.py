"""pe: random signed MACs checked against a Python accumulator, plus clear/en."""
import random

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import CORE, run_sim, start_clock, to_signed


async def setup(dut):
    start_clock(dut.clk)
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.en.value = 0
    dut.clear.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)


@cocotb.test()
async def random_macs(dut):
    await setup(dut)
    pairs = [(-128, -128), (-128, 127), (127, -128), (127, 127), (0, -128)]
    pairs += [(random.randint(-128, 127), random.randint(-128, 127)) for _ in range(1000)]
    acc = 0
    prev = None
    for a, b in pairs:
        dut.a_in.value = a & 0xFF
        dut.b_in.value = b & 0xFF
        dut.en.value = 1
        await FallingEdge(dut.clk)
        acc += a * b
        assert to_signed(dut.acc.value, 32) == acc
        assert to_signed(dut.a_out.value, 8) == a, "a must pass through with 1-cycle delay"
        assert to_signed(dut.b_out.value, 8) == b, "b must pass through with 1-cycle delay"


@cocotb.test()
async def enable_and_clear(dut):
    await setup(dut)
    dut.a_in.value = 5
    dut.b_in.value = 7
    dut.en.value = 1
    await FallingEdge(dut.clk)
    dut.en.value = 0                       # hold: accumulator must not change
    dut.a_in.value = 100
    await ClockCycles(dut.clk, 4)
    await FallingEdge(dut.clk)
    assert to_signed(dut.acc.value, 32) == 35
    assert to_signed(dut.a_out.value, 8) == 5
    dut.clear.value = 1                    # clear wins even with en = 1
    dut.en.value = 1
    await FallingEdge(dut.clk)
    dut.clear.value = 0
    assert int(dut.acc.value) == 0
    assert int(dut.a_out.value) == 0 and int(dut.b_out.value) == 0


def test_pe():
    run_sim("pe", [CORE / "pe.sv"], "test_pe")
