# Phase 5 — Reference Models & SystemC Co-simulation

All results below are simulation-only (Ubuntu 22.04, g++ 11.4, SystemC 3.0.2, Verilator 5.052).

## Model stack

| Level | File | What it models | Timing |
|---|---|---|---|
| NumPy golden | `model/golden_model.py` | C = A·B with int32 wrap; expected perf counters | none |
| C++ bit-accurate | `model/cpp/mm_ref.{h,cpp}` | Same arithmetic as `pe.sv`: int8×int8→int16, int32 wrap-around accumulate | none |
| Analytical perf | `mm::predict_perf()` in `mm_ref.cpp` | Every counter in `mm_regs.sv` as a closed formula | cycles |
| SystemC LT | `model/systemc/mm_lt.h` | TLM-2.0 target, `b_transport`, full register map; START computes C at once | annotated delay = predicted cycles |
| SystemC CA | `model/systemc/mm_ca.h` | Clocked `SC_THREAD` running the RTL FSM (IDLE→CLEAR→COMPUTE→DRAIN→DONE) and counters cycle by cycle | clock-accurate at the register interface |
| RTL | `rtl/core/mm_core.sv` | The design | cycle-exact |

Shared pieces keep the models from drifting apart:
- **One register map** (`model/regmap.py`, `model/systemc/mm_regmap.h`, `rtl/core/mm_regs.sv`).
  One TLM generic payload (4-byte data, byte address) = one RTL bus transaction.
- **One vector file format** (`model/vectors.py` → `model/vectors/n{4,8}.hex`): A, B, expected C and
  expected counters. Read by NumPy, the C++ test, the SystemC tests, the co-sim and cocotb
  (`tb/test_mm_core.py::shared_vectors`).
- **One job sequence** (`mm::run_job` in `model/systemc/bus_initiator.h`) drives both a TLM socket
  and the RTL pins.

## Analytical performance model (Day 30)

For one job with inner dimension K on an N×N array:

| Counter | Formula | Why |
|---|---|---|
| PERF_TOTAL | K + 2N | 1 CLEAR + K COMPUTE + (2N − 1) DRAIN |
| PERF_COMPUTE | K + 2N − 1 | array enabled in COMPUTE and DRAIN |
| PERF_FILLDRAIN | (K + 2N − 1) − max(0, K − 2N + 2) | all N² PEs busy only for array steps 2N−1 … K |
| PERF_MACS | N²·K | N² MACs per column of A fed |

Utilisation = MACS / (N² · COMPUTE). Full table for N ∈ {4, 8}, K = 1…64: [perf_model.csv](perf_model.csv).

| N | K | total | compute | fill/drain | utilisation | GOPS @ 50 MHz (compute only) |
|---|---|---|---|---|---|---|
| 4 | 64 | 72 | 71 | 13 | 90.1 % | 1.42 |
| 8 | 16 | 32 | 31 | 29 | 51.6 % | 3.20 |
| 8 | 64 | 80 | 79 | 29 | 81.0 % | 5.12 (peak 6.4) |

## Results

| Check | Vectors | Result |
|---|---|---|
| C++ model == NumPy (C and counters) — `make -C model/cpp test` | 2 × 1000 | ✅ 2000/2000 |
| SystemC LT: C + counters — `make -C model/systemc test` | 2 × 1000 | ✅ 0 mismatches |
| SystemC CA: C + counters; measured START→DONE vs analytical | 2 × 1000 | ✅ 0 mismatches, max error **0 cycles** (target ±2) |
| **Co-sim RTL vs CA** (Verilator `--sc`) — `make -C cosim` | 2 × 1000 | ✅ 0 C mismatches, 0 counter mismatches, pin-level START→DONE error **0 cycles** |
| cocotb RTL on the shared vectors | 2 × 100 | ✅ |

Per-job co-sim rows: [cosim_n4.csv](cosim_n4.csv), [cosim_n8.csv](cosim_n8.csv).

**Harness sanity check (mutation test):** changing the RTL "all PEs active" bound from 2N−1 to
2N−2 in `mm_controller.sv` made the co-sim report PERF_FILLDRAIN mismatches immediately
(C still correct — only a counter is wrong, which is exactly what a functional-only check would miss).

## Why the CA model is exact here

The model reproduces the controller FSM and the counter update conditions, and register accesses
take effect at the next rising edge, as on the RTL bus. What it does *not* model: the datapath
pipeline (C is computed functionally at DONE), RAM contents over time, and reads of C mid-job
(RTL returns partial sums, the model returns the previous result). PERF_IDLE depends on host
access timing and is excluded from the RTL/model comparison.

## Reproduce

```bash
conda activate fpga                        # iverilog, verilator, systemc (see UBUNTU_HANDOFF.md)
python3 model/vectors.py                   # model/vectors/n4.hex, n8.hex (1000 jobs each)
make -C model/cpp test
make -C model/systemc test
make -C cosim                              # writes docs/results/cosim_n{4,8}.csv
```
