#!/usr/bin/env python3
"""Shared test vectors (Phase 5, Day 29): one file read by NumPy, C++, SystemC and RTL tests.

Text format, one job per 5 lines, all numbers hex, whitespace separated:

    job <N> <K>
    a <N*K int8 bytes, row-major>
    b <K*N int8 bytes, row-major>
    c <N*N int32 words, row-major>              (expected result)
    p <PERF_TOTAL> <PERF_COMPUTE> <PERF_FILLDRAIN> <PERF_MACS>   (expected counters)

Usage:
    python3 model/vectors.py                    # writes model/vectors/{n4,n8}.hex
    python3 model/vectors.py --n 8 --count 1000 --seed 5 --out /tmp/v.hex
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from model.golden_model import edge_cases, expected_perf, matmul_int32, random_int8  # noqa: E402

PERF_KEYS = ("PERF_TOTAL", "PERF_COMPUTE", "PERF_FILLDRAIN", "PERF_MACS")


def make_jobs(n, count, k_max=64, seed=0):
    rng = np.random.default_rng(seed)
    jobs = []
    for k in (1, 2 * n - 2, 2 * n - 1, k_max):
        jobs += list(edge_cases(n, k).values())
    while len(jobs) < count:
        k = int(rng.integers(1, k_max + 1))
        jobs.append((random_int8((n, k), rng), random_int8((k, n), rng)))
    return jobs[:count]


def write_vectors(path, jobs):
    with open(path, "w") as f:
        for a, b in jobs:
            n, k = a.shape
            c = matmul_int32(a, b)
            perf = expected_perf(n, k)
            f.write(f"job {n:x} {k:x}\n")
            f.write("a " + " ".join(f"{int(v) & 0xFF:02x}" for v in a.flat) + "\n")
            f.write("b " + " ".join(f"{int(v) & 0xFF:02x}" for v in b.flat) + "\n")
            f.write("c " + " ".join(f"{int(v) & 0xFFFFFFFF:08x}" for v in c.flat) + "\n")
            f.write("p " + " ".join(f"{perf[key]:x}" for key in PERF_KEYS) + "\n")


def read_vectors(path):
    """Yields dicts with n, k, a, b, c (int64 arrays) and perf (dict)."""
    def signed(v, bits):
        return v - (1 << bits) if v >> (bits - 1) else v

    lines = [ln.split() for ln in Path(path).read_text().splitlines() if ln.strip()]
    for i in range(0, len(lines), 5):
        (_, n, k), a, b, c, p = lines[i:i + 5]
        n, k = int(n, 16), int(k, 16)
        yield {
            "n": n, "k": k,
            "a": np.array([signed(int(x, 16), 8) for x in a[1:]]).reshape(n, k),
            "b": np.array([signed(int(x, 16), 8) for x in b[1:]]).reshape(k, n),
            "c": np.array([signed(int(x, 16), 32) for x in c[1:]]).reshape(n, n),
            "perf": dict(zip(PERF_KEYS, (int(x, 16) for x in p[1:]))),
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--n", type=int, default=None, help="one N (default: 4 and 8)")
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    for n in ([args.n] if args.n else [4, 8]):
        out = args.out or ROOT / "model" / "vectors" / f"n{n}.hex"
        out.parent.mkdir(parents=True, exist_ok=True)
        write_vectors(out, make_jobs(n, args.count, seed=args.seed + n))
        print(f"wrote {args.count} jobs to {out}")


if __name__ == "__main__":
    main()
