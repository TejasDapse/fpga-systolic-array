# Verification Plan — mm_core (Phase 6)

**DUT:** `rtl/core/mm_core.sv` (N×N output-stationary systolic array behind the register bus of PLAN.md §6).
**Environment:** `uvm/` — UVM (Accellera uvm-core) on Verilator 5.052, z3 for constraints, C++ reference model via DPI-C.
**Results:** [results/uvm_regression.md](results/uvm_regression.md) · [results/verification_report.md](results/verification_report.md)

## 1. Environment

```
             +------------------------------- mm_env ----------------------------------+
 sequences ->| bus_agent: sequencer -> driver ==pins==> mm_core <==pins== monitor --+   |
             |                                                                     |   |
             |   mm_scoreboard <-- analysis port (accepted transactions, edge#) ---+   |
             |      | predicts every read; C and counters from C++ via DPI-C           |
             |      +--> mm_coverage (bins, cross, scenarios)                          |
             +-------------------------------------------------------------------------+
 tb_top: clock, mm_bus_if, DUT, mm_sva (assertions), run_test(+TEST=...)
```

- **Driver** drives on falling edges and holds a request until `bus_ready`; reads complete on `bus_rvalid`.
- **Monitor** publishes each *accepted* transaction stamped with its rising-edge index, plus hard resets.
- **Scoreboard** is stimulus-independent: it rebuilds CFG_K, the A/B RAMs and job timing from the
  accepted traffic and predicts **every** read: STATUS exactly (BUSY/DONE cycle by cycle), CFG_K, INFO,
  C (via `mm_ref_dpi`), counters (via `mm_perf_dpi`), PERF_IDLE monotonic, unmapped/aliased reads = 0.
  C and counters read while BUSY are skipped (partial values), STATUS is not.
- **Assertions** (`uvm/tb/mm_sva.sv`) cover the bus handshake from both sides and the controller FSM.

## 2. Features → checks → tests → coverage

| # | Feature | How it is checked | Tests | Coverage |
|---|---|---|---|---|
| F1 | C = A·B, int8 in, int32 wrap | scoreboard vs C++ model (DPI-C) | random, edge_values, all | `cp_k`, `cp_kind`, `x_k_kind`, `cp_values` |
| F2 | Operand corners −128 / 0 / 127, identity | same | edge_values | `cp_kind.*`, `cp_values.*` |
| F3 | K range 1 … K_MAX incl. fill/drain boundary 2N−1 | same + counters | edge_values, random | `cp_k.*` (5 bins) |
| F4 | Perf counters TOTAL/COMPUTE/FILLDRAIN/MACS | scoreboard vs analytical model | all job tests | via F1 |
| F5 | PERF_IDLE counts while idle, saturating | monotonic between resets | reg_access, all | — |
| F6 | STATUS BUSY/DONE timing | exact cycle prediction | every test (polling) | `scenario.status_saw_busy` |
| F7 | START ignored while busy | scoreboard timing + results | start_while_busy, back_to_back | `scenario.start_while_busy` |
| F8 | A/B writes ignored while busy | rerun without reload must match | start_while_busy | `scenario.buffer_write_while_busy` |
| F9 | CFG_K legal range, not busy-protected | CFG_K read-back | reg_access, start_while_busy | `scenario.cfg_k_invalid` |
| F10 | Back-to-back jobs, rerun without reload | results | back_to_back | `scenario.back_to_back` |
| F11 | Soft reset (CTRL.SOFT_RESET) mid-job | reset values + next job | soft_reset | `scenario.soft_reset_while_busy` |
| F12 | Hard reset (rst_n) mid-job | reset values + next job | hard_reset | `scenario.hard_reset_while_busy` |
| F13 | Register map: INFO, holes, aliasing, write-only buffers, out-of-range A/B/C | read = 0 / ignored | reg_access | `scenario.*_out_of_range` |
| F14 | Reads during compute don't disturb it | results after | start_while_busy | `scenario.c_read_while_busy`, `perf_read_while_busy` |
| F15 | Bus protocol: rvalid exactly 1 cycle after a read, ready low ≤ 1 cycle, master holds request | SVA | all | `c_ready_low`, `c_back_to_back_rd` (cover property) |
| F16 | FSM: legal states, CLEAR→COMPUTE, DRAIN = 2N−1 cycles, DONE→IDLE, done/busy consistent | SVA | all | — |
| F17 | No X/Z on control, bus or board outputs after reset (RAMs have no reset) | 4-state Icarus checks | cocotb `no_x_after_reset`, system test | — |
| F18 | Parameterisation: N ∈ {4, 8, 16}, K_MAX ∈ {16, 64, 128}; illegal values rejected | all of the above per config | cocotb, co-sim, UVM | per-config coverage |

## 3. Stimulus

`mm_job` randomizes `k` and `kind` under constraints (`c_k_legal`, weighted `c_k_dist` favouring 1,
2N−1 and K_MAX, `c_kind_dist`); operands are filled from `kind` in `post_randomize`. Directed sequences pin
values with inline `randomize() with {...}` and switch the matching `dist` off with `constraint_mode(0)`.

## 4. Closure criteria

- All directed tests pass for (N, K_MAX) = (4, 64), (8, 64), (16, 64), (8, 128).
- Constrained-random: ≥ 10 seeds each of `mm_random_test` (200 jobs) and `mm_all_test`, all passing.
- Merged functional coverage **≥ 95 %** per configuration (all 55 bins targeted). Achieved: 100 %.
- RTL code coverage (line / branch / toggle) **100 % after documented waivers** (`uvm/code_coverage.py`).
- Zero assertion failures; mutation checks (below) must fail.

## 5. Mutation checks (does the environment catch real bugs?)

| Injected RTL bug | Caught by |
|---|---|
| `mm_regs.sv`: buffer writes not blocked while BUSY | scoreboard: C mismatch on the rerun-without-reload |
| `mm_controller.sv`: DRAIN one cycle short | SVA `a_drain_length` (and timing/counters) |
| `mm_controller.sv`: fill/drain bound 2N−2 instead of 2N−1 | co-sim PERF_FILLDRAIN mismatch (Phase 5) |

## 6. Tool notes (Verilator 5.052)

- UVM built with `+define+UVM_NO_DPI` (no HDL backdoor needed); tests selected with `+TEST=`.
- Covergroups parse but coverpoints are not implemented → coverage is an explicit-bin collector with the
  same structure (coverpoints, cross, scenario bins) and a mergeable hit file.
- `dist` is applied by bucket selection, so it cannot be combined with an inline constraint on the same
  variable → sequences disable the dist (`constraint_mode(0)`) when they pin the value.
- Dynamic arrays can't be passed to DPI open arrays yet → fixed-size arrays (N ≤ 16, K_MAX ≤ 64).
