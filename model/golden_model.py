"""NumPy reference model for the systolic-array accelerator.

Used by the cocotb testbenches and by host/host.py to check hardware results.
"""
import numpy as np


def random_int8(shape, rng=None):
    rng = rng or np.random.default_rng()
    return rng.integers(-128, 128, size=shape, dtype=np.int64)


def matmul_int32(a, b):
    """C = A @ B with int8 inputs and int32 wrap-around accumulation (like the RTL)."""
    c = np.asarray(a, dtype=np.int64) @ np.asarray(b, dtype=np.int64)
    return ((c + 2**31) % 2**32 - 2**31).astype(np.int64)


def expected_perf(n, k):
    """Perf counter values after one job (register map in rtl/core/mm_regs.sv).

    Array enabled for K (COMPUTE) + 2N-1 (DRAIN) cycles; all N*N PEs are busy
    only for steps 2N-1 .. K, i.e. max(0, K - 2N + 2) of them.
    """
    compute = k + 2 * n - 1
    return {
        "PERF_TOTAL": compute + 1,                        # + 1 CLEAR cycle
        "PERF_COMPUTE": compute,
        "PERF_FILLDRAIN": compute - max(0, k - 2 * n + 2),
        "PERF_MACS": n * n * k,
    }


def expected_cycles(n, k):
    """START-to-DONE cycles (PERF_TOTAL)."""
    return expected_perf(n, k)["PERF_TOTAL"]


def edge_cases(n, k):
    """Named (A, B) pairs that stress sign handling and accumulation."""
    full = lambda v, s: np.full(s, v, dtype=np.int64)
    eye_k = np.eye(n, k, dtype=np.int64)
    return {
        "zeros":        (full(0, (n, k)), full(0, (k, n))),
        "all_min":      (full(-128, (n, k)), full(-128, (k, n))),   # max positive sum
        "all_max":      (full(127, (n, k)), full(127, (k, n))),
        "min_times_max": (full(-128, (n, k)), full(127, (k, n))),   # max negative sum
        "identity":     (eye_k, random_int8((k, n))),
    }
