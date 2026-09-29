#!/usr/bin/env python3
"""Host driver for the systolic-array accelerator (PLAN.md §5 protocol).

    python host/host.py                       # auto-detect port, 100 random tests
    python host/host.py --tests 1000 --k 64   # fixed K instead of random K
    python host/host.py --bench               # sweep K, write CSV + plots to docs/results/
    python host/host.py --fake                # no board: talk to a software model (self-test)

Every result is compared with NumPy; the script prints PASS/FAIL and exits 1 on failure.
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from model.golden_model import edge_cases, expected_cycles, matmul_int32, random_int8  # noqa: E402

CLK_HZ = 50_000_000


class ProtocolError(RuntimeError):
    pass


class Accelerator:
    def __init__(self, link):
        self.link = link
        self.link.reset_input_buffer()
        reply = self._cmd(b"P", 3)
        if reply[0] != ord("K"):
            raise ProtocolError(f"bad ping reply {reply!r}")
        self.n, self.k_max = reply[1], reply[2]

    def _read(self, count):
        data = self.link.read(count)
        if len(data) != count:
            raise ProtocolError(
                f"timeout: expected {count} bytes, got {len(data)}. Check wiring "
                "(TX<->RX crossed, GND), that the .sof is loaded, and try KEY0 (reset).")
        return data

    def _cmd(self, data, reply_len):
        self.link.write(bytes(data))
        return self._read(reply_len)

    def _expect(self, data, want):
        got = self._cmd(data, 1)
        if got != want:
            raise ProtocolError(f"command {bytes(data[:1])!r}: expected {want!r}, got {got!r}")

    def matmul(self, a, b):
        """Returns (C, cycles, timings dict in seconds)."""
        n, k = a.shape
        assert n == self.n and b.shape == (k, n) and 1 <= k <= self.k_max
        t0 = time.perf_counter()
        self._expect(b"S" + bytes([k]), b"K")
        self._expect(b"A" + a.astype(np.int8).tobytes(), b"K")
        self._expect(b"B" + b.astype(np.int8).tobytes(), b"K")
        t1 = time.perf_counter()
        self._expect(b"G", b"D")
        t2 = time.perf_counter()
        c = np.frombuffer(self._cmd(b"R", 4 * n * n), dtype="<i4").reshape(n, n)
        cycles = int.from_bytes(self._cmd(b"C", 4), "little")
        t3 = time.perf_counter()
        return c.astype(np.int64), cycles, {"load": t1 - t0, "go": t2 - t1, "read": t3 - t2}


class FakeBoard:
    """Software stand-in for the FPGA that speaks the same byte protocol."""

    def __init__(self, n=8, k_max=64):
        self.n, self.k_max, self.k = n, k_max, k_max
        self.a = np.zeros((n, k_max), dtype=np.int64)
        self.b = np.zeros((k_max, n), dtype=np.int64)
        self.c = np.zeros((n, n), dtype=np.int64)
        self.cycles = 0
        self.inbuf, self.outbuf = bytearray(), bytearray()

    def reset_input_buffer(self):
        self.outbuf.clear()

    def write(self, data):
        self.inbuf += data
        while self._step():
            pass

    def read(self, count):
        data, self.outbuf = bytes(self.outbuf[:count]), self.outbuf[count:]
        return data

    def _step(self):
        buf, n, k = self.inbuf, self.n, self.k
        if not buf:
            return False
        cmd, need = chr(buf[0]), {"S": 2, "A": 1 + n * k, "B": 1 + k * n}.get(chr(buf[0]), 1)
        if len(buf) < need:
            return False
        body = np.frombuffer(bytes(buf[1:need]), dtype=np.int8).astype(np.int64)
        del buf[:need]
        if cmd == "P":
            self.outbuf += bytes([ord("K"), n, self.k_max])
        elif cmd == "S":
            kk = int(body[0]) & 0xFF
            ok = 1 <= kk <= self.k_max
            self.k = kk if ok else self.k
            self.outbuf += b"K" if ok else b"E"
        elif cmd == "A":
            self.a[:, :k] = body.reshape(n, k)
            self.outbuf += b"K"
        elif cmd == "B":
            self.b[:k, :] = body.reshape(k, n)
            self.outbuf += b"K"
        elif cmd == "G":
            self.c = matmul_int32(self.a[:, :k], self.b[:k, :])
            self.cycles = expected_cycles(n, k)
            self.outbuf += b"D"
        elif cmd == "R":
            self.outbuf += self.c.astype("<i4").tobytes()
        elif cmd == "C":
            self.outbuf += self.cycles.to_bytes(4, "little")
        else:
            self.outbuf += b"E"
        return True


# ------------------------------------------------------------------ modes
def run_tests(acc, count, k_fixed, rng):
    n = acc.n
    cases = []
    for k in (1, acc.k_max):
        cases += [(f"{name}_k{k}", ab) for name, ab in edge_cases(n, k).items()]
    for r in range(count):
        k = k_fixed or int(rng.integers(1, acc.k_max + 1))
        cases.append((f"random{r}_k{k}", (random_int8((n, k), rng), random_int8((k, n), rng))))

    fails = 0
    start = time.time()
    for idx, (name, (a, b)) in enumerate(cases, 1):
        c, cycles, _ = acc.matmul(a, b)
        want = matmul_int32(a, b)
        ok = np.array_equal(c, want) and cycles == expected_cycles(n, a.shape[1])
        if not ok:
            fails += 1
            print(f"FAIL {name}: cycles {cycles} (expected {expected_cycles(n, a.shape[1])})")
            if not np.array_equal(c, want):
                print(f"  got\n{c}\n  want\n{want}\n  wrong elements: {np.argwhere(c != want).tolist()}")
        if idx % 50 == 0 or idx == len(cases):
            print(f"  {idx}/{len(cases)} done, {fails} failed ({time.time() - start:.1f} s)")
    print(f"{len(cases) - fails}/{len(cases)} matrix multiplies correct")
    return fails == 0


def run_bench(acc, rng, out_dir):
    n = acc.n
    ks = sorted({k for k in (1, 2, 4, 8, 16, 32, 48, 64, acc.k_max) if k <= acc.k_max})
    rows = []
    for k in ks:
        a, b = random_int8((n, k), rng), random_int8((k, n), rng)
        reps = []
        for _ in range(5):
            c, cycles, t = acc.matmul(a, b)
            assert np.array_equal(c, matmul_int32(a, b)), f"wrong result at K={k}"
            reps.append(t)
        t = {key: float(np.median([r[key] for r in reps])) for key in reps[0]}
        t_np = min(_time_numpy(a, b) for _ in range(5))
        compute_s = cycles / CLK_HZ
        macs = n * n * k
        rows.append({
            "N": n, "K": k, "cycles": cycles,
            "ideal_cycles": k + 2 * n - 2,
            "utilization": k / cycles,
            "compute_us": compute_s * 1e6,
            "gops": 2 * macs / compute_s / 1e9,
            "peak_gops": 2 * n * n * CLK_HZ / 1e9,
            "uart_load_ms": t["load"] * 1e3,
            "uart_read_ms": t["read"] * 1e3,
            "end_to_end_ms": sum(t.values()) * 1e3,
            "numpy_us": t_np * 1e6,
        })
        r = rows[-1]
        print(f"K={k:3d}: {cycles:4d} cycles, util {r['utilization']:.0%}, "
              f"{r['gops']:.2f} GOPS compute, UART load {r['uart_load_ms']:.1f} ms, "
              f"end-to-end {r['end_to_end_ms']:.1f} ms, NumPy {r['numpy_us']:.1f} us")

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"bench_n{n}.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {csv_path}")
    _plot(rows, out_dir, n)


def _time_numpy(a, b):
    a8, b8 = a.astype(np.int8), b.astype(np.int8)
    t0 = time.perf_counter()
    for _ in range(100):
        a8.astype(np.int32) @ b8.astype(np.int32)
    return (time.perf_counter() - t0) / 100


def _plot(rows, out_dir, n):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping plots")
        return
    k = [r["K"] for r in rows]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(k, [r["cycles"] for r in rows], "o-", label="measured")
    ax.plot(k, [r["ideal_cycles"] for r in rows], "--", label="K + 2N - 2 (ideal)")
    ax2 = ax.twinx()
    ax2.plot(k, [100 * r["utilization"] for r in rows], "s:", color="gray", label="utilization")
    ax.set_xlabel("K (inner dimension)")
    ax.set_ylabel("compute cycles")
    ax2.set_ylabel("array utilization (%)")
    ax.set_title(f"{n}x{n} systolic array: cycles vs K")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / f"cycles_vs_k_n{n}.png", dpi=150)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.semilogy(k, [r["compute_us"] for r in rows], "o-", label="FPGA compute")
    ax.semilogy(k, [r["end_to_end_ms"] * 1e3 for r in rows], "s-", label="FPGA end-to-end (UART)")
    ax.semilogy(k, [r["numpy_us"] for r in rows], "^-", label="NumPy on host")
    ax.set_xlabel("K (inner dimension)")
    ax.set_ylabel("time (us, log scale)")
    ax.set_title(f"{n}x{n}: compute vs I/O time")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / f"time_breakdown_n{n}.png", dpi=150)
    print(f"wrote plots to {out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--port", default=None)
    ap.add_argument("--baud", type=int, default=115_200)
    ap.add_argument("--tests", type=int, default=100, help="random tests (edge cases are extra)")
    ap.add_argument("--k", type=int, default=None, help="fixed K (default: random 1..K_MAX)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--bench", action="store_true", help="benchmark K sweep instead of tests")
    ap.add_argument("--fake", action="store_true", help="use a software model instead of a board")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "results")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    if args.fake:
        link = FakeBoard()
        print("Using FakeBoard (software model, no hardware)")
    else:
        import serial
        from uart_echo_test import find_port
        port = args.port or find_port()
        link = serial.Serial(port, args.baud, timeout=2)
        print(f"Port {port} @ {args.baud} baud")

    try:
        acc = Accelerator(link)
        print(f"Accelerator: N = {acc.n}, K_MAX = {acc.k_max}")
        if args.bench:
            run_bench(acc, rng, args.out)
            ok = True
        else:
            ok = run_tests(acc, args.tests, args.k, rng)
    except ProtocolError as e:
        print(f"ERROR: {e}")
        ok = False
    finally:
        if hasattr(link, "close"):
            link.close()

    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
