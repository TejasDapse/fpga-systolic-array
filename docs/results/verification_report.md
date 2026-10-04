# Verification Report — Systolic-Array Accelerator

Scope: `mm_core` (N×N output-stationary array, register bus, perf counters) and the UART system top.
Everything here is **pre-silicon** (simulation); the board-dependent items are listed at the end.
Plan: [../vplan.md](../vplan.md). All of it re-runs in CI (`.github/workflows/sim.yml`).

## 1. Verification layers

| Layer | Tooling | What it proves | Result |
|---|---|---|---|
| Unit tests | cocotb + Icarus 13 (`tb/`) | PE, skew buffer, array, bridge commands, UART, FIFO | ✅ |
| Block, bus level | cocotb (`tb/test_mm_core.py`) | random jobs, busy protection, soft reset, shared vectors, **X-propagation**; 5 (N, K_MAX) configs | ✅ |
| System, UART pins | cocotb (`tb/test_top_de10lite.py`) | host protocol end-to-end, LEDs/HEX, stall recovery, no X on board outputs | ✅ N = 4 (N = 8 with `SLOW=1`) |
| Reference models | C++ bit-accurate + analytical, SystemC LT/CA (`model/`) | models agree with NumPy on 3 × 1000 vectors (N = 4, 8, 16) | ✅ 0 mismatches |
| Co-simulation | Verilator `--sc` vs SystemC CA (`cosim/`) | RTL == model: C, all counters, pin-level cycles | ✅ 5 configs × 1000 jobs, 0-cycle error |
| UVM | UVM on Verilator + DPI-C + SVA (`uvm/`) | stimulus-independent checking, functional coverage closure | ✅ 104/104 sims, 100 % |
| Code coverage | Verilator line/branch/toggle (`uvm/code_coverage.py`) | which RTL the UVM tests actually exercise | ✅ 100 % after waivers |
| Formal | SymbiYosys + z3 (`formal/`) | bus protocol + FSM properties for **any** bus master, unbounded (k-induction) | ✅ proved; covers reached |
| Lint | Verilator `-Wall`, Verible (`tools/lint.sh`) | coding problems / style | ✅ Verilator clean on core/top; 6 Verible style notes |
| Host software | `host.py --fake`, `mm_host` on a pty, tiling tests | host drivers + tiling speak the protocol correctly | ✅ |

cocotb total: 37 tests pass (+1 slow, skipped by default).

Parameter configurations (N, K_MAX) verified: **(4, 64), (8, 64), (16, 64)** everywhere; **(4, 16), (8, 128)** in
cocotb and co-sim; (8, 128) also in UVM. Illegal combinations (non-power-of-2, windows > 4 KB, K_MAX > 255)
stop simulation with `$fatal` (`rtl/core/mm_regs.sv`).

## 2. UVM regression ([uvm_regression.md](uvm_regression.md))

| | 4:64 | 8:64 | 16:64 | 8:128 |
|---|---|---|---|---|
| 6 directed tests | 6/6 | 6/6 | 6/6 | 6/6 |
| `mm_random_test` × 10 seeds (200 jobs) | 10/10 | 10/10 | 10/10 | 10/10 |
| `mm_all_test` × 10 seeds | 10/10 | 10/10 | 10/10 | 10/10 |
| Functional coverage (55 bins) | **100 %** | **100 %** | **100 %** | **100 %** |

Total: **104/104 simulations, 13 828 jobs, 1.89 M scoreboard checks, 0 assertion failures.**

## 3. RTL code coverage ([code_coverage.md](code_coverage.md), N = 8, K_MAX = 64)

| | Line | Branch | Toggle |
|---|---|---|---|
| raw | 96.9 % (31/32) | 100 % (56/56) | 90.7 % (3001/3308) |
| after waivers | **100 %** | **100 %** | **100 %** |

Waivers (both structural): the controller's `default:` branch (all 5 states are decoded) and the upper bits of
the 32-bit performance counters (a job lasts ≤ K_MAX + 2N cycles; flipping bit 31 needs ~2³¹ cycles).

Toggle coverage found two things: no test addressed the top of the 4 KB buffer windows (fixed in
`mm_reg_access_seq`), and `a_row`/`b_row` in `mm_regs.sv` were declared 12 bits wide although only
12 − log2(K_MAX) / 12 − log2(N) bits can ever be non-zero (narrowed; behaviour unchanged, all tests re-run).

## 4. X-propagation

Verilator is 2-state, so this is checked in the 4-state Icarus tests (`no_x_after_reset` in
`tb/test_mm_core.py`, board outputs in `tb/test_top_de10lite.py`), in all 5 configurations:
- every register and C read after reset is fully defined;
- `bus_ready`, `bus_rvalid`, `busy`, `done`, `state`, `perf_compute` are never X/Z on any cycle, including
  while a job runs on **never-written RAM** — whose C *is* X, which the test checks too (proves the
  4-state check is alive: the operand RAMs deliberately have no reset);
- once A/B are written, every C word is defined and correct;
- LEDR, HEX0–5 and UART_TXD are defined after reset and after a full UART session.

## 5. Does the environment find bugs? (mutation checks)

Each bug was injected into the RTL, the relevant check run, and the RTL restored.

| Injected bug | Detected by | Symptom |
|---|---|---|
| A/B writes accepted while BUSY (`mm_regs.sv`) | UVM scoreboard | C mismatch on the rerun-without-reload |
| DRAIN one cycle short (`mm_controller.sv`) | SVA `a_drain_length` | assertion at first job |
| "all PEs active" bound off by one (`mm_controller.sv`) | Verilator co-sim | PERF_FILLDRAIN mismatch, C still correct |

The last case is the argument for performance counters in the scoreboard: a functional-only check passes.

## 6. Issues found during verification

| # | Found by | Issue | Resolution |
|---|---|---|---|
| 1 | UVM regression (8/52 fails) | SVA `a_drain_length` / `a_clear_then_compute` fired on a **legal** soft reset during DRAIN — they were only disabled by hard reset | `disable iff (!rst_n \|\| soft_reset)` for FSM sequences |
| 2 | UVM busy test review | ignored A/B writes were never observed afterwards (next job reloads) — a bug could hide | sequence reruns the job without reload; mutation #1 proves it now catches it |
| 3 | Toggle coverage | buffer-window address bits 10–11 never driven | `mm_reg_access_seq` addresses the top of each window |
| 4 | Toggle coverage | `a_row`/`b_row` wider than any value they can hold | narrowed in `mm_regs.sv` |
| 5 | cocotb array test | `to_signed()` helper did not mask upper bits → false mismatches | fixed helper (testbench bug) |
| 6 | bridge unit test | payload bytes 2 cycles apart + random bus stalls overran the one-byte bridge buffer | real UART gives ≥ 4340 cycles/byte; assumption documented, test uses realistic spacing |
| 7 | X-prop test | cocotb tests share one simulation, so "RAM never written" only holds for the first test | X test runs first, documented |
| 8 | K_MAX = 128 co-sim | shared vectors were generated for K ≤ 64, so K 65…128 was silently untested | per-K_MAX vector files (`vectors.py --k-max`) |
| 9 | Plan vs RTL | plan estimated ≈ 78 cycles (K + 2N − 2) for N = 8, K = 64; RTL reads 80 | +1 CLEAR, +1 RAM read latency; documented |
| 10 | Tools | Icarus: genvar compare in port expression; Verilator: no covergroups, `dist` + inline constraint unsatisfiable, no dynamic arrays to DPI | workarounds in code, vplan §6 |

No functional datapath bug was found after Phase 2; the mutations above show the checks would catch one.

## 7. Performance correlation ([correlation.md](correlation.md))

| Source | N = 4 | N = 8 | N = 16 |
|---|---|---|---|
| Analytical (K + 2N) vs SystemC CA | 0 % | 0 % | 0 % |
| Analytical vs RTL counters and RTL pin timing | 0 % | 0 % | 0 % |
| FPGA measured | pending — needs the board | pending | pending (fit unknown) |

## 8. Open items

Need the board or Quartus:
1. Quartus compile: resources, Fmax, slack ≥ 0 at N = 4 and 8; does N = 16 fit (256 multipliers)? (PLAN Days 13, 22)
2. `host.py --tests` on the board (Days 23–24); `host.py --bench` for real UART timing.
3. `host/mm_host --csv docs/results/fpga_perf_n{4,8}.csv`, then `tools/correlate.py` (Days 45–46).
4. Gate-level simulation of the Quartus netlist (optional).

Need a commercial simulator (optional): native covergroups and the UVM env on Questa (Starter edition ships
with Quartus) or on VCS / Xcelium via EDA Playground — see [../TOOLS.md](../TOOLS.md).

## 9. Formal verification ([../../formal/](../../formal/))

`formal/mm_core_props.v` wraps `mm_core` (N = 2, K_MAX = 4) with **unconstrained** bus inputs and
proves, by k-induction (unbounded, not just to a depth): `rvalid` exactly one cycle after every read
accept and never otherwise; `ready` low for at most one cycle; legal FSM states; `busy`/`done`
consistent with the state; `done` is a one-cycle pulse; DONE → IDLE; CLEAR → COMPUTE (or IDLE on soft
reset); COMPUTE → COMPUTE/DRAIN (or IDLE). Cover statements show DONE and "read while busy" are
reachable, so the proof is not vacuous. Proof time ≈ 1 min.

Mutation check: making `bus_rvalid` sticky fails `a_rvalid_only_after` in the base case within
seconds, with a counterexample VCD for GTKWave.

These are the same properties as the simulation SVA (`uvm/tb/mm_sva.sv`), now proven for all inputs
instead of the inputs the tests happened to drive.

## 10. Pre-Quartus synthesis estimate (`tools/synth_estimate.sh`)

sv2v + Yosys coarse synthesis (no MAX 10 mapping, no timing — Quartus is still required):

| N | 8×8 multipliers | RAMs (M9K candidates) | 10M50 capacity |
|---|---|---|---|
| 4 | 16 | 8 | 288 9-bit multipliers, 182 M9K |
| 8 | 64 | 16 | |
| 16 | 256 | 32 | fits on multipliers (256 ≤ 288) — logic/Fmax unknown |

## 11. Reproduce

```bash
conda env create -f environment.yml && conda activate fpga
git clone --depth 1 https://github.com/accellera-official/uvm-core ~/tools/uvm-core
(cd tb && pytest -q)                                  # cocotb (SLOW=1 adds N=8 system sim)
python3 model/vectors.py && make -C model/cpp test && make -C model/systemc test
make -C cosim                                         # RTL vs SystemC, 5 configurations
python3 uvm/regress.py                                # UVM regression + functional coverage
python3 uvm/code_coverage.py                          # RTL code coverage
make -C formal                                        # formal proof (needs ~/tools/sby, sv2v)
tools/lint.sh && tools/synth_estimate.sh              # lint + pre-Quartus estimate
python3 tools/correlate.py
```
