"""fifo_sync: random push/pop compared against a Python deque (golden model)."""
import random
from collections import deque

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import COMMON, run_sim, start_clock

DEPTH = 16


@cocotb.test()
async def random_push_pop(dut):
    start_clock(dut.clk)
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.wdata.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

    model = deque()
    for cycle in range(3000):
        await FallingEdge(dut.clk)          # outputs are stable mid-cycle

        # 1) Check DUT outputs against the model.
        assert int(dut.empty.value) == (len(model) == 0), f"cycle {cycle}: empty flag"
        assert int(dut.full.value) == (len(model) == DEPTH), f"cycle {cycle}: full flag"
        if model:
            assert int(dut.rdata.value) == model[0], f"cycle {cycle}: rdata"

        # 2) Pick random inputs (bias changes over time to hit full and empty).
        p_write = 0.8 if (cycle // 500) % 2 == 0 else 0.2
        wr = random.random() < p_write
        rd = random.random() < 0.5
        wdata = random.randrange(256)
        dut.wr_en.value = int(wr)
        dut.rd_en.value = int(rd)
        dut.wdata.value = wdata

        # 3) Update the model the same way the hardware will at the next edge.
        was_full, was_empty = len(model) == DEPTH, len(model) == 0
        if rd and not was_empty:
            model.popleft()
        if wr and not was_full:
            model.append(wdata)


def test_fifo_sync():
    run_sim("fifo_sync", [COMMON / "fifo_sync.sv"], "test_fifo_sync",
            parameters={"WIDTH": 8, "DEPTH": DEPTH})
