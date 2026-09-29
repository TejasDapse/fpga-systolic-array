"""systolic_array: the testbench does the skewing itself (Day 10 exercise).

Row i of A enters the left edge delayed by i cycles; column j of B enters the
top edge delayed by j cycles. After K + 2N - 2 feed cycles, PE(i,j) holds C[i][j].
"""
import cocotb
import numpy as np
import pytest
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import CORE, run_sim, start_clock, to_signed
from model.golden_model import edge_cases, matmul_int32, random_int8


def pack(values):
    return sum((int(v) & 0xFF) << (8 * n) for n, v in enumerate(values))


async def run_matmul(dut, n, a, b):
    k = a.shape[1]
    dut.clear.value = 1
    await FallingEdge(dut.clk)
    dut.clear.value = 0
    dut.en.value = 1
    for t in range(k + 2 * n - 1):
        # lane i gets element k = t - i (zero outside 0..K-1)
        dut.a_in.value = pack(a[i, t - i] if 0 <= t - i < k else 0 for i in range(n))
        dut.b_in.value = pack(b[t - j, j] if 0 <= t - j < k else 0 for j in range(n))
        await FallingEdge(dut.clk)
    raw = int(dut.c_out.value)
    return np.array([[to_signed(raw >> (32 * (i * n + j)), 32) for j in range(n)]
                     for i in range(n)])


@cocotb.test()
async def random_and_edge_matrices(dut):
    n = len(dut.a_in) // 8
    start_clock(dut.clk)
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.en.value = 0
    dut.clear.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)

    rng = np.random.default_rng(1)
    cases = list(edge_cases(n, 8).items())
    cases += [(f"random{r}", (random_int8((n, k), rng), random_int8((k, n), rng)))
              for r, k in enumerate([1, 2, 3, n, 17, 64] * 5)]
    for name, (a, b) in cases:
        got = await run_matmul(dut, n, a, b)
        want = matmul_int32(a, b)
        assert np.array_equal(got, want), f"{name}:\n got\n{got}\n want\n{want}"


@pytest.mark.parametrize("n", [2, 4, 8])
def test_systolic_array(n):
    run_sim("systolic_array", [CORE / "pe.sv", CORE / "systolic_array.sv"],
            "test_systolic_array", parameters={"N": n}, build_name=f"systolic_array_n{n}")
