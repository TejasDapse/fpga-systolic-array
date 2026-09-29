"""mm_core: load A/B through the write port, pulse start, read C back (Day 12/17).

Checks every result against the NumPy golden model and checks the cycle count.
"""
import os

import cocotb
import numpy as np
import pytest
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import CORE, run_sim, start_clock, to_signed
from model.golden_model import edge_cases, expected_cycles, matmul_int32, random_int8

K_MAX = 64
N_RANDOM = int(os.environ.get("MM_RANDOM", "300"))    # random tests per N


async def write(dut, sel, lane, addr, value):
    dut.wr_en.value = 1
    dut.wr_sel.value = sel
    dut.wr_lane.value = lane
    dut.wr_addr.value = addr
    dut.wr_data.value = int(value) & 0xFF
    await FallingEdge(dut.clk)
    dut.wr_en.value = 0


async def matmul(dut, n, a, b):
    k = a.shape[1]
    for i in range(n):
        for kk in range(k):
            await write(dut, 0, i, kk, a[i, kk])
    for kk in range(k):
        for j in range(n):
            await write(dut, 1, j, kk, b[kk, j])
    dut.k_len.value = k
    dut.start.value = 1
    await FallingEdge(dut.clk)
    dut.start.value = 0
    for _ in range(K_MAX + 4 * n + 10):
        if int(dut.done.value):
            break
        await FallingEdge(dut.clk)
    else:
        raise AssertionError("done never pulsed")
    c = np.zeros((n, n), dtype=np.int64)
    for idx in range(n * n):
        dut.rd_idx.value = idx
        await FallingEdge(dut.clk)
        c[idx // n, idx % n] = to_signed(dut.rd_data.value, 32)
    return c, int(dut.cycles.value)


@cocotb.test()
async def random_and_edge_matrices(dut):
    n = 2 ** len(dut.wr_lane)                  # N is a power of 2 here
    start_clock(dut.clk)
    for sig in (dut.wr_en, dut.wr_sel, dut.wr_lane, dut.wr_addr, dut.wr_data,
                dut.start, dut.rd_idx):
        sig.value = 0
    dut.k_len.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)

    rng = np.random.default_rng(n)
    cases = []
    for k in (1, K_MAX):
        cases += [(f"{name}_k{k}", ab) for name, ab in edge_cases(n, k).items()]
    for r in range(N_RANDOM):
        k = int(rng.integers(1, K_MAX + 1))
        cases.append((f"random{r}_k{k}", (random_int8((n, k), rng), random_int8((k, n), rng))))

    for name, (a, b) in cases:
        got, cycles = await matmul(dut, n, a, b)
        want = matmul_int32(a, b)
        assert np.array_equal(got, want), f"{name}:\n got\n{got}\n want\n{want}"
        assert cycles == expected_cycles(n, a.shape[1]), f"{name}: cycles {cycles}"
    dut._log.info("N=%d: %d matrix multiplies passed", n, len(cases))


@pytest.mark.parametrize("n", [4, 8])
def test_mm_core(n):
    run_sim("mm_core",
            [CORE / f for f in ["pe.sv", "systolic_array.sv", "skew_buffer.sv",
                                "sram_sp.sv", "mm_controller.sv", "mm_core.sv"]],
            "test_mm_core", parameters={"N": n, "K_MAX": K_MAX}, build_name=f"mm_core_n{n}")
