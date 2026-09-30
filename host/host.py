#!/usr/bin/env python3
"""Host driver for the systolic-array accelerator.

Talks the UART-to-bus bridge protocol (PLAN.md §5) and the register map
(PLAN.md §6, rtl/core/mm_regs.sv, model/regmap.py).

    python host/host.py                       # auto-detect port, 100 random tests
    python host/host.py --tests 1000 --k 64   # fixed K instead of random K
    python host/host.py --bench               # sweep K, write CSV + plots to docs/results/
    python host/host.py --fake                # no board: talk to a software model (self-test)

Every result is compared with NumPy; the script prints PASS/FAIL and exits 1 on failure.
"""
import argparse
import csv
import struct
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from model.golden_model import edge_cases, expected_perf, matmul_int32, random_int8  # noqa: E402
from model import regmap as rm  # noqa: E402

CLK_HZ = 50_000_000


class ProtocolError(RuntimeError):
    pass


class Accelerator:
    """Register-level driver: W/R/B/D/P commands -> bus reads and writes."""

    def __init__(self, link):
        self.link = link
        self.link.reset_input_buffer()
        reply = self._cmd(b"P", 3)
        if reply[0] != ord("K"):
            raise ProtocolError(f"bad ping reply {reply!r}")
        self.n, self.k_max = reply[1], reply[2]
        self.version = self.read(rm.INFO) >> 16

    # ---- raw protocol
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

    def _expect_ok(self, data):
        got = self._cmd(data, 1)
        if got != b"K":
            raise ProtocolError(f"command {bytes(data[:1])!r}: expected b'K', got {got!r}")

    def write(self, addr, value):
        self._expect_ok(b"W" + struct.pack("<HI", addr, value & 0xFFFFFFFF))

    def read(self, addr):
        return struct.unpack("<I", self._cmd(b"R" + struct.pack("<H", addr), 4))[0]

    def write_block(self, addr, data):
        self._expect_ok(b"B" + struct.pack("<HH", addr, len(data)) + bytes(data))

    def read_block(self, addr, length):
        return self._cmd(b"D" + struct.pack("<HH", addr, length), length)

    # ---- one matrix multiply
    def matmul(self, a, b):
        """Returns (C, perf counters dict, host timings dict in seconds)."""
        n, k = a.shape
        assert n == self.n and b.shape == (k, n) and 1 <= k <= self.k_max
        t0 = time.perf_counter()
        self.write(rm.CFG_K, k)
        for i in range(n):                                  # A rows are K_MAX apart
            self.write_block(rm.a_addr(i, 0, self.k_max), a[i].astype(np.int8).tobytes())
        self.write_block(rm.B_BUF, b.astype(np.int8).tobytes())    # B rows are contiguous
        t1 = time.perf_counter()
        self.write(rm.CTRL, rm.CTRL_START)
        for _ in range(1000):
            if self.read(rm.STATUS) & rm.STATUS_DONE:
                break
        else:
            raise ProtocolError("DONE never set")
        t2 = time.perf_counter()
        raw = self.read_block(rm.C_BUF, 4 * n * n)
        c = np.frombuffer(raw, dtype="<i4").reshape(n, n).astype(np.int64)
        perf = {name: self.read(addr) for name, addr in rm.PERF.items()}
        t3 = time.perf_counter()
        return c, perf, {"load": t1 - t0, "go": t2 - t1, "read": t3 - t2}


class FakeBoard:
    """Software stand-in for the FPGA: bridge protocol + register map, no timing."""

    def __init__(self, n=8, k_max=64):
        self.n, self.k_max = n, k_max
        self.regs = {rm.CFG_K: k_max, rm.STATUS: 0, rm.INFO: (1 << 16) | (k_max << 8) | n}
        self.regs.update({addr: 0 for addr in rm.PERF.values()})
        self.a = np.zeros((n, k_max), dtype=np.int64)
        self.b = np.zeros((k_max, n), dtype=np.int64)
        self.c = np.zeros((n, n), dtype=np.int64)
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

    # ---- register model (mirrors rtl/core/mm_regs.sv)
    def _bus_write(self, addr, value):
        n, k_max = self.n, self.k_max
        byte = ((value & 0xFF) ^ 0x80) - 0x80
        if addr == rm.CTRL and value & rm.CTRL_START:
            k = self.regs[rm.CFG_K]
            self.c = matmul_int32(self.a[:, :k], self.b[:k, :])
            self.regs.update({rm.PERF[key]: v for key, v in expected_perf(n, k).items()})
            self.regs[rm.STATUS] = rm.STATUS_DONE
        elif addr == rm.CFG_K and 1 <= value <= k_max:
            self.regs[rm.CFG_K] = value
        elif rm.A_BUF <= addr < rm.A_BUF + n * k_max:
            self.a.flat[addr - rm.A_BUF] = byte
        elif rm.B_BUF <= addr < rm.B_BUF + k_max * n:
            self.b.flat[addr - rm.B_BUF] = byte

    def _bus_read(self, addr):
        if rm.C_BUF <= addr < rm.C_BUF + 4 * self.n * self.n:
            return int(self.c.flat[(addr - rm.C_BUF) // 4]) & 0xFFFFFFFF
        return self.regs.get(addr, 0)

    # ---- bridge protocol (mirrors rtl/top/uart_bus_bridge.sv)
    def _step(self):
        buf = self.inbuf
        if not buf:
            return False
        cmd = chr(buf[0])
        need = {"W": 7, "R": 3, "B": 5, "D": 5}.get(cmd, 1)
        if cmd == "B" and len(buf) >= 5:
            need += struct.unpack_from("<H", buf, 3)[0]
        if len(buf) < need:
            return False
        body = bytes(buf[1:need])
        del buf[:need]
        if cmd == "P":
            info = self._bus_read(rm.INFO)
            self.outbuf += bytes([ord("K"), info & 0xFF, (info >> 8) & 0xFF])
        elif cmd == "W":
            addr, value = struct.unpack("<HI", body)
            self._bus_write(addr, value)
            self.outbuf += b"K"
        elif cmd == "R":
            self.outbuf += struct.pack("<I", self._bus_read(struct.unpack("<H", body)[0]))
        elif cmd == "B":
            addr, _ = struct.unpack_from("<HH", body)
            for i, v in enumerate(body[4:]):
                self._bus_write(addr + i, v)
            self.outbuf += b"K"
        elif cmd == "D":
            addr, length = struct.unpack("<HH", body)
            for i in range(length):
                a = addr + i
                self.outbuf.append((self._bus_read(a & ~3) >> (8 * (a & 3))) & 0xFF)
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
        c, perf, _ = acc.matmul(a, b)
        want = matmul_int32(a, b)
        exp = expected_perf(n, a.shape[1])
        bad_perf = {key: (perf[key], v) for key, v in exp.items() if perf[key] != v}
        ok = np.array_equal(c, want) and not bad_perf
        if not ok:
            fails += 1
            print(f"FAIL {name}: perf (got, expected) {bad_perf}")
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
            c, perf, t = acc.matmul(a, b)
            assert np.array_equal(c, matmul_int32(a, b)), f"wrong result at K={k}"
            reps.append(t)
        t = {key: float(np.median([r[key] for r in reps])) for key in reps[0]}
        t_np = min(_time_numpy(a, b) for _ in range(5))
        cycles = perf["PERF_TOTAL"]
        compute_s = cycles / CLK_HZ
        macs = perf["PERF_MACS"]
        rows.append({
            "N": n, "K": k, "cycles": cycles,
            "compute_cycles": perf["PERF_COMPUTE"],
            "filldrain_cycles": perf["PERF_FILLDRAIN"],
            "ideal_cycles": k + 2 * n - 2,
            "utilization": macs / (n * n * perf["PERF_COMPUTE"]),
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
        print(f"Accelerator: N = {acc.n}, K_MAX = {acc.k_max}, version {acc.version}")
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
