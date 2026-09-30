# Verification Report — Systolic-Array Accelerator

Scope: `mm_core` (N×N output-stationary array, register bus, perf counters) and the UART system top.
Everything here is **pre-silicon** (simulation); the board-dependent items are listed at the end.
Plan: [../vplan.md](../vplan.md).

## 1. Verification layers

| Layer | Tooling | What it proves | Result |
|---|---|---|---|
| Unit tests | cocotb + Icarus 13 (`tb/`) | PE, skew buffer, array, bridge commands, UART, FIFO | ✅ 19 tests (+1 slow) |
| Block, bus level | cocotb (`tb/test_mm_core.py`) | 200+ random jobs/N, busy protection, soft reset, shared vectors | ✅ N = 4, 8 |
| System, UART pins | cocotb (`tb/test_top_de10lite.py`) | host protocol end-to-end, LEDs/HEX, stall recovery | ✅ N = 4, 8 |
| Reference models | C++ bit-accurate + analytical, SystemC LT/CA (`model/`) | models agree with NumPy on 2 × 1000 vectors | ✅ 0 mismatches |
| Co-simulation | Verilator `--sc` vs SystemC CA (`cosim/`) | RTL == model: C, all counters, pin-level cycles | ✅ 2 × 1000 jobs, 0-cycle error |
| UVM | UVM on Verilator + DPI-C + SVA (`uvm/`) | stimulus-independent checking, coverage closure | ✅ 52/52 sims, 100 % coverage |
| Host software | `host.py --fake`, `mm_host` on a pty | host drivers speak the protocol correctly | ✅ 210/210, 2 × 200/200 |

## 2. UVM regression ([uvm_regression.md](uvm_regression.md))

| | N = 4 | N = 8 |
|---|---|---|
| Directed tests (reg access, edge values, back-to-back, start-while-busy, soft reset, hard reset) | 6/6 | 6/6 |
| `mm_random_test` × 10 seeds (200 jobs each) | 10/10 | 10/10 |
| `mm_all_test` × 10 seeds | 10/10 | 10/10 |
| Scoreboard checks | 145 k | 331 k |
| Functional coverage (55 bins: K classes, operand patterns, cross, value corners, 11 scenarios) | **100 %** | **100 %** |
| Assertion failures | 0 | 0 |

## 3. Does the environment find bugs? (mutation checks)

Each bug was injected into the RTL, the relevant check run, and the RTL restored.

| Injected bug | Detected by | Symptom |
|---|---|---|
| A/B writes accepted while BUSY (`mm_regs.sv`) | UVM scoreboard | C mismatch on the rerun-without-reload |
| DRAIN one cycle short (`mm_controller.sv`) | SVA `a_drain_length` | assertion at first job |
| "all PEs active" bound off by one (`mm_controller.sv`) | Verilator co-sim | PERF_FILLDRAIN mismatch, C still correct |

The last case is the argument for performance counters in the scoreboard: a functional-only check passes.

## 4. Issues found during verification

| # | Found by | Issue | Resolution |
|---|---|---|---|
| 1 | UVM regression (8/52 fails) | SVA `a_drain_length` / `a_clear_then_compute` fired on a **legal** soft reset during DRAIN — the assertions were only disabled by hard reset | added `disable iff (!rst_n \|\| soft_reset)` for FSM sequences |
| 2 | UVM busy test review | ignored A/B writes were never observed afterwards (next job reloads) — a bug could hide | sequence reruns the job without reload; mutation #1 proves it now catches it |
| 3 | cocotb array test | `to_signed()` helper did not mask upper bits → false mismatches | fixed helper (testbench bug) |
| 4 | bridge unit test | payload bytes 2 cycles apart + random bus stalls overran the one-byte bridge buffer | real UART gives ≥ 4340 cycles/byte; assumption documented in `uart_bus_bridge.sv`, test uses realistic spacing |
| 5 | Plan vs RTL | plan estimated ≈ 78 cycles (K + 2N − 2) for N=8, K=64; RTL reads 80 | +1 CLEAR, +1 RAM read latency; documented in PLAN §6 and the analytical model |
| 6 | Tools | Icarus: genvar compare in port expression; Verilator: covergroups not implemented, `dist` + inline constraint unsatisfiable, no dynamic arrays to DPI | workarounds in the code, listed in vplan §6 |

No functional RTL bug was found in the datapath after Phase 2; the counter/FSM checks and the mutations
above show the checks would have caught one.

## 5. Performance correlation ([correlation.md](correlation.md))

| Source | N = 4 | N = 8 |
|---|---|---|
| Analytical (K + 2N) vs SystemC CA | 0 % error, all K | 0 % error, all K |
| Analytical vs RTL counters and RTL pin timing | 0 % error, all K | 0 % error, all K |
| FPGA measured | pending — needs the board | pending |

## 6. Open items (need hardware)

1. Quartus compile: resources, Fmax, slack ≥ 0 at N = 4 and 8 (PLAN Day 13, 22).
2. `host.py --tests` on the board (Days 23–24).
3. `host/mm_host --csv docs/results/fpga_perf_n{4,8}.csv` on the board, then `python3 tools/correlate.py`
   to fill the FPGA column (Days 45–46).

## 7. Reproduce

```bash
conda activate fpga                                   # see docs/UBUNTU_HANDOFF.md
(cd tb && pytest -q)                                  # cocotb (SLOW=1 adds N=8 system sim)
python3 model/vectors.py && make -C model/cpp test && make -C model/systemc test
make -C cosim                                         # RTL vs SystemC
python3 uvm/regress.py                                # UVM regression + coverage
make -C host && python3 host/fake_serial.py &         # C++ host against the fake board
python3 tools/correlate.py
```
