"""host.py tiling (stretch goal): arbitrary (M x K) @ (K x P) on the N x N array.

Pure software against the FakeBoard register model, so it runs in milliseconds.
The FakeBoard itself mirrors the RTL protocol and register map, which the
cocotb system test (test_top_de10lite.py) checks against the real RTL.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "host"))
from host import Accelerator, FakeBoard  # noqa: E402
from tb_utils import ROOT  # noqa: E402,F401  (sets sys.path for model/)
from model.golden_model import matmul_int32, random_int8  # noqa: E402


@pytest.mark.parametrize("n", [4, 8])
@pytest.mark.parametrize("m,k,p", [(1, 1, 1), (4, 64, 4), (8, 65, 8), (13, 100, 7),
                                    (32, 32, 32), (64, 200, 33), (3, 130, 17)])
def test_tiled_matches_numpy(n, m, k, p):
    rng = np.random.default_rng(m * 1000 + k * 10 + p)
    acc = Accelerator(FakeBoard(n=n))
    a, b = random_int8((m, k), rng), random_int8((k, p), rng)
    c, stats = acc.matmul_tiled(a, b)
    assert np.array_equal(c, matmul_int32(a, b))
    tiles = -(-m // n) * -(-p // n) * -(-k // acc.k_max)
    assert stats["jobs"] == tiles
    assert stats["b_loads"] == -(-p // n) * -(-k // acc.k_max), "B is reused across row tiles"


def test_tiled_wraps_like_int32():
    acc = Accelerator(FakeBoard(n=4))
    k = 140_000                         # 140000 * 128 * 128 > 2^31: the sum must wrap
    a = np.full((4, k), -128)
    b = np.full((k, 4), -128)
    c, _ = acc.matmul_tiled(a, b)
    assert k * 128 * 128 > 2**31 - 1
    assert np.array_equal(c, matmul_int32(a, b))
    assert c[0, 0] == k * 128 * 128 - 2**32
