#!/usr/bin/env python3
"""RTL code coverage (line / branch / toggle) from a UVM regression subset.

Builds the testbench with Verilator coverage (make build COV=1), runs every
directed test plus a few random seeds, merges the coverage databases and
reports per RTL file. Points inside UVM / testbench code are ignored.

    python3 uvm/code_coverage.py                 # N=8, K_MAX=64
    python3 uvm/code_coverage.py --config 4:64
"""
import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UVM = Path(__file__).resolve().parent
ROOT = UVM.parent
ENV = Path(os.environ.get("FPGA_ENV", Path.home() / "miniconda3" / "envs" / "fpga"))
TESTS = ["mm_reg_access_test", "mm_edge_values_test", "mm_back_to_back_test",
         "mm_start_while_busy_test", "mm_soft_reset_test", "mm_hard_reset_test"]
RANDOM = [("mm_random_test", 200, 3), ("mm_all_test", 50, 3)]
KINDS = {"v_line": "line", "v_branch": "branch", "v_toggle": "toggle", "v_user": "assert/cover"}

# Points that cannot be reached in simulation, with the reason. Matched against
# (file, kind, comment); reported separately and excluded from the "waived" figure.
WAIVERS = [
    ("mm_controller.sv", "v_line", r"^case$", "FSM `default:` branch: all 5 states are decoded"),
    ("", "v_toggle", r"^(perf_\w+|reg_rdata)\[", "upper bits of 32-bit counters: a job lasts <= K_MAX + 2N "
     "cycles, so they would need ~2^31 cycles of simulation; perf_macs low bits are always "
     "a multiple of N^2"),
]


def waived(f, kind, comment):
    for wf, wk, pat, _ in WAIVERS:
        if (not wf or wf == f) and wk == kind and re.search(pat, comment):
            return True
    return False


def parse_dat(path):
    """Yields (file, line, kind, hierarchy, comment, count) for every coverage point."""
    for raw in Path(path).read_text(errors="replace").splitlines():
        m = re.match(r"C '(.*)' (\d+)$", raw)
        if not m:
            continue
        fields = dict(f.split("\x02", 1) for f in m.group(1).split("\x01") if "\x02" in f)
        kind = fields.get("page", "").split("/")[0]
        yield (fields.get("f", ""), int(fields.get("l", 0)), kind, fields.get("h", ""),
               fields.get("o", ""), int(m.group(2)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--config", default="8:64", help="N:K_MAX")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "results" / "code_coverage.md")
    args = ap.parse_args()
    n, k = args.config.split(":")
    build = UVM / "build" / f"n{n}_k{k}_cov"

    print(f"building coverage testbench N={n} K_MAX={k} ...", flush=True)
    r = subprocess.run(["make", "-s", "build", f"N={n}", f"KMAX={k}", "COV=1"], cwd=UVM,
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stdout[-3000:] + r.stderr[-3000:])

    runs = [(t, 1, 0) for t in TESTS] + [(t, s, j) for t, j, seeds in RANDOM for s in range(1, seeds + 1)]

    def run(item):
        test, seed, jobs = item
        dat = build / f"cov_{test}_{seed}.dat"
        out = subprocess.run([str(build / "Vtb_top"), f"+TEST={test}", f"+JOBS={jobs}",
                              f"+verilator+seed+{seed}", f"+verilator+coverage+file+{dat}"],
                             cwd=UVM, capture_output=True, text=True,
                             env=dict(os.environ, PATH=f"{ENV / 'bin'}:{os.environ['PATH']}"))
        return test, seed, "TEST PASSED" in out.stdout, dat

    with ThreadPoolExecutor(os.cpu_count()) as pool:
        results = list(pool.map(run, runs))
    failed = [f"{t} seed {s}" for t, s, ok, _ in results if not ok]
    merged = build / "merged.dat"
    subprocess.run([str(ENV / "bin" / "verilator_coverage"), "--write", str(merged)] +
                   [str(d) for *_, d in results], check=True, capture_output=True)

    # Merge points by (file, line, kind, comment) across hierarchy instances:
    # a point counts as covered if any instance hit it.
    points = defaultdict(int)
    for f, line, kind, hier, comment, count in parse_dat(merged):
        if "/rtl/" not in f or kind not in KINDS:
            continue
        points[(Path(f).name, line, kind, comment)] = max(points[(Path(f).name, line, kind, comment)], count)

    table = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))     # covered, total, waived
    missed = defaultdict(list)
    for (f, line, kind, comment), count in points.items():
        cell = table[f][kind]
        cell[1] += 1
        cell[0] += count > 0
        if count == 0:
            if waived(f, kind, comment):
                cell[2] += 1
            else:
                missed[f].append(f"{KINDS[kind]} L{line} {comment}".rstrip())

    lines = [f"# RTL Code Coverage (N = {n}, K_MAX = {k})", "",
             f"Verilator line / branch / toggle coverage merged over {len(results)} UVM runs "
             f"({len(TESTS)} directed tests + random seeds). Generated by `python3 uvm/code_coverage.py`. "
             "A point inside a `generate` loop counts as covered if any instance hit it.", "",
             "Each cell: raw % (covered/total), and after waivers in brackets.", "",
             "| File | Line | Branch | Toggle |", "|---|---|---|---|"]
    totals = defaultdict(lambda: [0, 0, 0])

    def fmt(c, t, w, bold=False):
        if not t:
            return "—"
        b = "**" if bold else ""
        after = f" [{100 * c / (t - w):.1f} %]" if w else ""
        return f"{b}{100 * c / t:.1f} %{b} ({c}/{t}){after}"

    for f in sorted(table):
        cells = []
        for kind in ("v_line", "v_branch", "v_toggle"):
            c, t, w = table[f][kind]
            for i, v in enumerate((c, t, w)):
                totals[kind][i] += v
            cells.append(fmt(c, t, w))
        lines.append(f"| {f} | " + " | ".join(cells) + " |")
    lines.append("| **total** | " + " | ".join(
        fmt(*totals[kd], bold=True) for kd in ("v_line", "v_branch", "v_toggle")) + " |")
    lines += ["", "## Waivers", ""] + [f"- `{wf or '*'}` {KINDS[wk]} `{pat}`: {why}"
                                        for wf, wk, pat, why in WAIVERS]
    lines += ["", "## Not covered (after waivers)", ""]
    if not missed:
        lines.append("Nothing.")
    for f in sorted(missed):
        lines.append(f"**{f}** ({len(missed[f])} points)")
        lines += [f"- {m}" for m in sorted(missed[f])[:25]]
        if len(missed[f]) > 25:
            lines.append(f"- … {len(missed[f]) - 25} more")
        lines.append("")
    if failed:
        lines += ["## Failed runs", ""] + [f"- {x}" for x in failed]
    args.out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:14 + len(table)]))
    print(f"wrote {args.out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
