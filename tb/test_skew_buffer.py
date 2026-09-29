"""skew_buffer: lane n output equals lane n input from n cycles ago."""
import random

import cocotb
import pytest
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import CORE, run_sim, start_clock


@cocotb.test()
async def lane_delays(dut):
    n = len(dut.din) // 8
    start_clock(dut.clk)
    dut.din.value = 0
    dut.clear.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    history = []                           # history[-1] = value driven last cycle
    for cycle in range(200):
        await FallingEdge(dut.clk)
        out = int(dut.dout.value)
        for i in range(1, min(n, len(history) + 1)):
            assert (out >> (8 * i)) & 0xFF == history[-i][i], f"cycle {cycle} lane {i}"
        lanes = [random.randrange(256) for _ in range(n)]
        dut.din.value = sum(v << (8 * i) for i, v in enumerate(lanes))
        history.append(lanes)
    await FallingEdge(dut.clk)
    assert int(dut.dout.value) & 0xFF == history[-1][0], "lane 0 has no delay"


@pytest.mark.parametrize("n", [2, 4, 8])
def test_skew_buffer(n):
    run_sim("skew_buffer", [CORE / "skew_buffer.sv"], "test_skew_buffer",
            parameters={"N": n}, build_name=f"skew_buffer_n{n}")
