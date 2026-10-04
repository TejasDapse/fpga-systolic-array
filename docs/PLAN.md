# Systolic Array Matrix-Multiply Accelerator — Project Plan

**Board:** Terasic DE10-Lite (Intel MAX 10, 10M50DAF484C7G, 50 MHz clock)
**Duration:** 7 weeks (49 days) at ~2–3 hrs/day (~120 hrs total)
**Companion notes:** [NOTES.md](NOTES.md) — read the listed sections *before* each day's work.
**Ubuntu machine:** [UBUNTU_HANDOFF.md](UBUNTU_HANDOFF.md) — setup + hardware tasks for the build PC.

---

## 0. Phase Map

| Phase | Weeks | Content | Where it runs |
|---|---|---|---|
| **1. Foundations** | 1 | Tool flow, 7-seg, UART TX/RX, FIFO | Sim (Mac/Ubuntu) + **board** |
| **2. Compute engine** | 2 | PE, N×N array, skew buffers | Sim |
| **3. System integration** | 3 | BRAM buffers, controller, **register-bus interface + perf counters**, UART bridge, host | Sim |
| **4. Hardware & results** | 4 | Bring-up, 8×8, benchmarks | **Board** (Ubuntu) |
| **5. Reference models & SystemC co-sim** | 5 | C++ bit-accurate model, SystemC/TLM-2.0 models, Verilator co-simulation | Sim only |
| **6. UVM verification & correlation** | 6–7 | UVM env + DPI-C scoreboard, coverage, testcases, HW↔SW performance correlation | Sim + board counters |

Phases 5–6 target **pre-silicon verification / performance-modeling roles**
(e.g. "simulation & performance analysis, functional and performance correlation
between HW and SW models, co-simulation in UVM and SystemC, testcases in UVM/C/C++").
They are **simulation-only** — no board or wiring changes. The only RTL impact is
the clean interface and counters added in Phase 3 (see §6).

---

## 1. Project Goal

Build a hardware accelerator on the FPGA that computes **C = A × B** using a
systolic array, driven from a Python script over UART — then verify it the way
industry does: C++/SystemC reference models, UVM, coverage, and correlation of
predicted vs. measured performance.

```
  Host (Python)                          DE10-Lite FPGA
 ┌──────────────┐   UART 115200   ┌─────────────────────────────────────────────┐
 │ host.py      │ ──────────────▶ │ UART RX → UART-to-bus bridge ─┐             │
 │ - random A,B │                 │                               ▼             │
 │ - send/recv  │                 │   register bus ──▶ mm_core ───────────────┐ │
 │ - compare    │                 │                  │ A/B buffers (M9K)      │ │
 │   w/ numpy   │                 │                  │ skew → N×N PE array    │ │
 │ - timing     │ ◀────────────── │ UART TX ◀────────│ C readout, FSM,        │ │
 └──────────────┘                 │                  │ perf counters          │ │
                                  │                  └────────────────────────┘ │
                                  └─────────────────────────────────────────────┘

  Verification (Phases 5–6, simulation only)
   C++ ref model ◀─DPI-C─ UVM scoreboard ◀─ monitor ◀─ mm_core RTL ─▶ driver ◀─ sequences
   SystemC TLM model ──▶ predicted cycles ──┐
   RTL perf counters (sim) ─────────────────┼──▶ correlation report (% error)
   FPGA perf counters (board) ──────────────┘
```

### Final Specification

| Item | Value |
|---|---|
| Array size | Parameterized `N`; bring-up at **4×4**, final target **8×8** (stretch 16×16) |
| Dataflow | **Output-stationary** (each PE owns one C[i][j]) |
| Input type | Signed **int8** |
| Accumulator | Signed **int32** |
| Matrix shapes | A: N×K, B: K×N, C: N×N, with K up to 64 (configurable) |
| Clock | 50 MHz (single clock domain) |
| **Core interface** | Simple **valid/ready register bus** (32-bit data, 16-bit address) — see §6 |
| **Perf counters** | total, compute, fill/drain, idle cycles; MAC count |
| Host link | UART 8N1 @ 115200 via USB-to-UART adapter (3.3 V) on GPIO; bridged onto the register bus |
| Status display | HEX0–HEX5 = compute cycle count; LEDR = FSM state / errors |
| Verification | cocotb (Phases 1–4); C++/SystemC models, Verilator co-sim, UVM + DPI-C (Phases 5–6) |

### Deliverables (what goes on your resume / GitHub)
1. Parameterized, verified RTL (SystemVerilog)
2. cocotb testbenches with random tests (1000+ random matrices pass)
3. Working hardware demo: Python → FPGA → correct results
4. Results table: resources (LEs, multipliers, M9K), Fmax, cycles, GOPS, utilization
5. **C++ bit-accurate reference model** + **SystemC/TLM-2.0 functional & cycle-approximate models**
6. **Verilator + SystemC co-simulation** comparing RTL against the SystemC model
7. **UVM environment** (agent, sequences, DPI-C scoreboard, functional coverage, SVA assertions)
8. **Verification plan + coverage report** (target ≥ 95 % functional coverage)
9. **Performance correlation report:** SystemC-predicted vs. RTL-simulated vs. FPGA-measured cycles, % error
10. README with block diagram, dataflow diagram and performance analysis

---

## 2. Setup Checklist

### Buy
- [ ] USB-to-UART adapter, **3.3 V** logic (CP2102 or FT232RL), ~₹200–300
- [ ] 3–4 female-to-female jumper wires

### Simulation machine (Mac or Ubuntu)
- [ ] Icarus Verilog (`brew install icarus-verilog` / `sudo apt install iverilog`)
- [ ] `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- [ ] Phase 5: SystemC 2.3.x/3.0 + Verilator ≥ 5.0 (`brew install systemc verilator`; on Ubuntu see UBUNTU_HANDOFF.md)
- [ ] Phase 6: a UVM-capable simulator — **Questa-Intel FPGA Starter Edition** (free, ships with Quartus, Ubuntu) or **EDA Playground** (online)

### Build machine (Ubuntu 22.04 or Windows, x86-64)
- [ ] **Quartus Prime Lite** + **MAX 10 device support**
- [ ] USB-Blaster access (udev rule on Ubuntu — `tools/setup_ubuntu.sh` does it)
- [ ] DE10-Lite CD from Terasic (System Builder, user manual)

> Everything can run on one Ubuntu PC. See [UBUNTU_HANDOFF.md](UBUNTU_HANDOFF.md).

---

## 3. Project Directory Structure

```
Systolic_Array/
├── docs/          PLAN.md, NOTES.md, UBUNTU_HANDOFF.md, results/
├── foundations/   Phase 1 board designs (01–04) + Quartus projects
├── rtl/
│   ├── common/    sync_2ff, tick_gen, hex7seg, uart_tx, uart_rx, fifo_sync
│   ├── core/      pe, systolic_array, skew_buffer, sram_sp, mm_controller, mm_regs, mm_core
│   └── top/       uart_bus_bridge, top_de10lite
├── tb/            cocotb tests (pytest)
├── model/
│   ├── golden_model.py          NumPy reference (Phases 2–4)
│   ├── cpp/                     bit-accurate C++ model + analytical perf model (Phase 5)
│   └── systemc/                 SystemC TLM-2.0 LT + cycle-approximate models (Phase 5)
├── cosim/         Verilator + SystemC co-simulation harness (Phase 5)
├── uvm/           UVM env, agents, sequences, tests, DPI-C glue, coverage (Phase 6)
├── host/          Python board scripts + C++ host test (Phase 6)
├── quartus/       systolic project (.qpf/.qsf/.sdc) for the full design
└── tools/         gen_quartus.py, setup_ubuntu.sh, build.sh
```

---

## 4. Week-by-Week Plan

### WEEK 1 — Phase 1: Foundations  ✅ RTL + sim done · ⏳ board
**Goal:** Comfortable with the full flow; working UART (reused later).
**Read first:** NOTES §1–§8, §10–§11

| Day | Task | Done when… |
|---|---|---|
| 1 | Setup checklist. Read NOTES §1–§4. | Quartus sees USB-Blaster; `iverilog -V` works |
| 2 | Read NOTES §5–§6. Simulate a mux, adder, counter; view in GTKWave. | You can explain `=` vs `<=` |
| 3 | **01 – switches → LEDs.** Verify pins with System Builder, compile, program. | SW[i] lights LEDR[i] |
| 4 | **02 – blinky**, **03 – hex counter**. | LED blinks at 1 Hz; HEX counts |
| 5 | Read NOTES §7–§8. KEY synchronizer + RUN/PAUSE FSM (in 03). Check Timing Analyzer. | Slack ≥ 0 |
| 6 | Read NOTES §10. Study `uart_tx.sv`; wire the adapter. | Adapter wired, `screen` connects |
| 7 | **04 – UART echo**; `host/uart_echo_test.py`, 10,000 bytes. | 0 byte errors |

**Checkpoint:** LUT? `=` vs `<=`? setup/slack/Fmax? metastability? UART mid-bit sampling?

---

### WEEK 2 — Phase 2: Compute Engine (simulation)  ✅ sim done · ⏳ Day 13 (needs Quartus)
**Goal:** A verified, parameterized N×N systolic array.
**Read first:** NOTES §12–§15

| Day | Task | Done when… |
|---|---|---|
| 8 | Trace the 2×2 × K=2 example on paper; fill the 3×3 table in NOTES §14. | You can predict every PE's MAC per cycle |
| 9 | `pe.sv` (MAC + pass-through regs, `clear`, `en`) + cocotb test incl. −128×−128. | PE test passes |
| 10 | `systolic_array.sv` 2×2 via `generate`; hand-skewed inputs. | 2×2 matches NumPy |
| 11 | `skew_buffer.sv`; parameterize to N. | 4×4 passes with un-skewed inputs |
| 12 | `model/golden_model.py`; random N=4/8, K∈[1,64], edge cases. | 500+ random tests pass |
| 13 | Synthesis-only compile N=4, N=8; record LEs, multipliers, Fmax. | Fmax > 50 MHz @ N=8 |
| 14 | Buffer day; write a 1-page dataflow explanation. | Checkpoint answered |

**Checkpoint:** why "systolic"? OS vs WS? why skew? latency K + 2N − 2? why int32 accumulators?

---

### WEEK 3 — Phase 3: System Integration (simulation)  ✅ sim done
**Goal:** Complete design passing full-system simulation, with a **verification-friendly interface**.
**Read first:** NOTES §9, §8, §16

| Day | Task | Done when… |
|---|---|---|
| 15 | `sram_sp.sv` (inferred M9K, 1-cycle read). A-buffer (N×K), B-buffer (K×N). | Quartus infers M9K |
| 16 | `mm_controller.sv` FSM: `IDLE → CLEAR → COMPUTE → DRAIN → DONE`. | FSM matches your diagram |
| 17 | **`mm_regs.sv` + `mm_core.sv`:** register-bus slave (§6 map), buffers + skew + array + controller, **perf counters** (§6). | 200 random tests through the bus pass |
| 18 | `uart_bus_bridge.sv`: UART commands → bus reads/writes (§5). | Unit test of each command passes |
| 19 | `top_de10lite.sv` (clock, reset, UART, HEX = compute cycles, LEDs = state). Full-system sim via UART. | One matmul works through UART in sim |
| 20 | `host/host.py`: write K/A/B, start, poll status, read C + counters, compare with NumPy. | Script ready for hardware |
| 21 | Buffer day; clean up, commit. | Everything committed |

**Checkpoint:** BRAM vs registers? draw the FSM? why a register bus instead of ad-hoc ports?

---

### WEEK 4 — Phase 4: Hardware Bring-up & Results (board, Ubuntu)
**Goal:** Working demo on the board with measured results.
**Read first:** NOTES §16–§18

| Day | Task | Done when… |
|---|---|---|
| 22 | `quartus/` project for the full design; compile N=4; fix timing; program. | Slack ≥ 0 |
| 23 | `host.py` on hardware for N=4; SignalTap if needed. | 100 random HW tests pass |
| 24 | Scale to **N=8**; re-verify sim + HW. | 1,000 HW tests pass |
| 25 | Benchmarks: cycles vs K, utilization, GOPS, UART vs compute time; plots. | Results table + 2 plots |
| 26 | Stretch: host tiling / double buffering / PLL for higher Fmax. ✅ host tiling done (`host.py --tile`, tested with the software board) | Stretch works |
| 27 | README: overview, diagrams, how to run, results. | README complete |
| 28 | Mock interview on Phases 1–4. | 2-min and 10-min pitch ready |

---

### WEEK 5 — Phase 5: Reference Models & SystemC Co-simulation (simulation only)  ✅ done — [results](results/phase5_models.md)
**Goal:** Software models of the accelerator and a co-simulation proving RTL == model.
**Read first:** NOTES §20–§24

| Day | Task | Done when… |
|---|---|---|
| 29 | Read NOTES §20–§21. **C++ bit-accurate model** `model/cpp/mm_ref.{h,cpp}` (int8×int8→int32, wrap semantics identical to RTL). Shared test-vector files (`.hex`) so NumPy, C++, RTL all read the same inputs. | C++ == NumPy on 1,000 vectors |
| 30 | **Analytical performance model** in C++: `cycles(N, K) = K + 2N − 2 + overhead`; define what each perf counter should read. | Predictions for N∈{4,8}, K∈{1..64} |
| 31 | Read NOTES §22–§23. **SystemC functional model** (`model/systemc/mm_lt.cpp`): TLM-2.0 target socket, `b_transport`, same register map as RTL (§6), loosely-timed. | SystemC test writes A/B, starts, reads C correctly |
| 32 | **Cycle-approximate SystemC model** (`mm_ca.cpp`): SC_THREAD per stage, `wait(clk)` per cycle; exposes the same perf counters. | Predicted cycles within ±2 of the analytical model |
| 33 | Read NOTES §24. **Verilator → SystemC**: build `mm_core` as a SystemC module; SystemC testbench drives RTL and model with the same stimulus. | Co-sim harness builds and runs 1 test |
| 34 | **Co-sim regression:** 1,000 random cases; compare C and perf counters RTL vs SystemC; write CSV. | 0 functional mismatches; cycle error table |
| 35 | Buffer day; document the modeling approach. | Phase 5 checkpoint answered |

**Checkpoint:** LT vs AT modeling? what is `b_transport`? delta cycle? why a bit-accurate model? how does Verilator co-sim differ from event-driven simulation?

---

### WEEK 6 — Phase 6a: UVM Environment (simulation only)  ✅ done — [vplan](vplan.md), [regression](results/uvm_regression.md)
**Goal:** A reusable, coverage-driven UVM testbench for `mm_core`.
**Read first:** NOTES §25–§26

| Day | Task | Done when… |
|---|---|---|
| 36 | Set up UVM simulator (Questa-Intel Starter on Ubuntu, or EDA Playground). Run a hello-world UVM test. Write the **verification plan** (features → tests → coverage). | `uvm_info` prints; vplan drafted |
| 37 | `mm_bus_if` interface (+ clocking block), `bus_item` (sequence item), `mm_job` (N, K, A, B) with **constraints**. | Items randomize correctly |
| 38 | **Agent:** sequencer, driver (drives bus), monitor (publishes via `uvm_analysis_port`). | Driver writes/reads registers in sim |
| 39 | **Scoreboard with DPI-C:** export C++ `mm_ref()` via `import "DPI-C"`, compare C matrix + counters. | Scoreboard reports PASS on a directed job |
| 40 | `mm_env`, `base_test`, `random_job_seq`; factory + `uvm_config_db`. | First random UVM test passes |
| 41 | **Functional coverage** (covergroups: K bins, value corners −128/0/127, back-to-back jobs, reset during compute) + **SVA** on bus handshake and FSM. | Coverage report generated |
| 42 | Buffer day. | Phase 6a checkpoint answered |

---

### WEEK 7 — Phase 6b: Testcases & HW/SW Correlation  ✅ sim done — [report](results/verification_report.md) · ⏳ Days 45–46 on the board
**Goal:** Close coverage, correlate performance across model / RTL / FPGA.

| Day | Task | Done when… |
|---|---|---|
| 43 | **Directed UVM tests:** identity, zeros, all −128, all 127, K=1, K=K_MAX, back-to-back, start-while-busy, reset mid-compute. | All directed tests pass |
| 44 | **Constrained-random regression** script (many seeds); coverage closure. | Functional coverage ≥ 95 % |
| 45 | **C/C++ testcase on hardware:** `host/mm_host.cpp` drives the FPGA over UART with the same `.hex` vectors, reads perf counters. (Ubuntu + board) | C++ host test passes on board |
| 46 | **Performance correlation:** SystemC-predicted vs RTL-sim vs FPGA-measured cycles for N∈{4,8}, K sweep; error %; explain any gap. | Correlation table + plot, error < 5 % |
| 47 | Write verification report: vplan, test list, coverage, bugs found, correlation. | `docs/results/verification_report.md` |
| 48 | Update README with Phases 5–6 results. | README updated |
| 49 | Mock interview focused on verification (NOTES §27). | You can whiteboard the UVM env + co-sim flow |

---

## 5. UART Command Protocol (host ↔ UART-to-bus bridge)

The UART bridge turns simple commands into register-bus transactions, so the
host, the UVM driver and the SystemC model all use the **same register map** (§6).

| Command | Bytes sent | Response |
|---|---|---|
| Write word | `'W'` + addr (2 B) + data (4 B) | `'K'` |
| Read word | `'R'` + addr (2 B) | data (4 B) |
| Write block | `'B'` + addr (2 B) + len (2 B) + len bytes | `'K'` |
| Read block | `'D'` + addr (2 B) + len (2 B) | len bytes |
| Ping | `'P'` | `'K'` + N (1 B) + K_MAX (1 B) |

All multi-byte values little-endian. Unknown command → `'E'` + error LED.

---

## 6. Core Interface, Register Map & Perf Counters (Phase 3 — RTL impact of Phases 5–6)

### Register bus (valid/ready, single clock)
| Signal | Dir (core) | Meaning |
|---|---|---|
| `bus_valid` | in | request valid |
| `bus_ready` | out | core accepts request this cycle |
| `bus_write` | in | 1 = write, 0 = read |
| `bus_addr[15:0]` | in | byte address |
| `bus_wdata[31:0]` | in | write data |
| `bus_rvalid` | out | read data valid (1+ cycles after accept) |
| `bus_rdata[31:0]` | out | read data |

This one interface is driven by the UART bridge (board), the cocotb tests, the
UVM driver, and maps 1:1 onto a TLM-2.0 generic payload (SystemC).

### Register map
| Address | Name | Access | Description |
|---|---|---|---|
| `0x0000` | `CTRL` | W | bit0 = START (self-clearing), bit1 = SOFT_RESET |
| `0x0004` | `STATUS` | R | bit0 = BUSY, bit1 = DONE (clears on START) |
| `0x0008` | `CFG_K` | R/W | K (1 … K_MAX) |
| `0x000C` | `INFO` | R | [7:0] = N, [15:8] = K_MAX, [31:16] = version |
| `0x0010` | `PERF_TOTAL` | R | cycles from START to DONE (= K + 2N: 1 CLEAR + K COMPUTE + 2N−1 DRAIN) |
| `0x0014` | `PERF_COMPUTE` | R | cycles with the array enabled (= K + 2N − 1) |
| `0x0018` | `PERF_FILLDRAIN` | R | compute cycles where not all PEs are active (= K + 2N − 1 − max(0, K − 2N + 2)) |
| `0x001C` | `PERF_IDLE` | R | cycles in IDLE since reset (saturating) |
| `0x0020` | `PERF_MACS` | R | useful MACs issued (should equal N·N·K) |
| `0x1000–0x1FFF` | `A_BUF` | W | A[i][k] at `0x1000 + i·K_MAX + k` (row stride K_MAX), int8 in `wdata[7:0]` |
| `0x2000–0x2FFF` | `B_BUF` | W | B[k][j] at `0x2000 + k·N + j` (contiguous), int8 in `wdata[7:0]` |
| `0x3000–0x3FFF` | `C_BUF` | R | C[i][j] at `0x3000 + 4·(i·N + j)`, int32 |

### Why this matters
- **UVM:** a single bus agent can drive and monitor everything.
- **SystemC:** the TLM model implements the same map, so the same test runs on both.
- **Correlation:** the same counters exist in the SystemC model, RTL sim and FPGA.

---

## 7. Expected Results (sanity targets)

| Metric | Expected (N=8, K=64, 50 MHz) |
|---|---|
| Compute cycles | ≈ K + 2N − 2 = **78** ideal; RTL sim: PERF_COMPUTE = **79**, PERF_TOTAL = **80** |
| Peak throughput | 64 MACs/cycle × 50 MHz = **3.2 GMAC/s = 6.4 GOPS** |
| Array utilization | 64 / 78 ≈ **82 %** |
| Embedded multipliers | ~64 (of 144 available) |
| UART time for A + B | 1,024 B ÷ 11,520 B/s ≈ **89 ms** vs compute ≈ **1.6 µs** |
| SystemC vs RTL cycle error | target **0–2 cycles** (cycle-approximate model) |
| Functional coverage | target **≥ 95 %** |

> The design is **I/O-bound** over UART — a key interview insight (NOTES §16).

---

## 8. Risk List & Mitigations

| Risk | Mitigation |
|---|---|
| No Quartus on Mac | Build on Ubuntu/Windows; simulate anywhere |
| UART garbage | Baud divider 434, common GND, TX↔RX crossed, 3.3 V jumper |
| Off-by-one in skew / BRAM latency | Paper trace (Day 8); compare waveforms cycle by cycle |
| Signed arithmetic wrong | `logic signed`, `$signed()`, test −128×−128 |
| Timing failure at N=8/16 | 2-stage PE, reduce N, check critical path |
| Works in sim, fails on HW | Synchronizers, reset polarity, SignalTap |
| Ubuntu apt Verilator too old (4.x) | Build Verilator ≥ 5 from source (UBUNTU_HANDOFF.md) |
| No free UVM simulator locally | Questa-Intel Starter (free license) or EDA Playground |
| SystemC model drifts from RTL | Same register map + shared `.hex` vectors + co-sim regression in CI |

---

## 9. Progress Tracker

- [x] Phase 1 — RTL + cocotb tests pass (13/13, Icarus 13)
- [ ] Phase 1 — board: designs 01–04 work, UART echo 0 errors (Ubuntu)
- [x] Phase 2 — N×N array verified in simulation (N = 2, 4, 8)
- [x] Phase 3 — full system (register bus + perf counters) verified in simulation (N = 4, 8, over UART)
- [ ] Phase 4 — hardware demo, benchmarks, README
- [x] Phase 5 — C++ + SystemC models, Verilator co-sim regression clean (2 × 1000 jobs, 0 mismatches, 0-cycle error)
- [x] Phase 6 — UVM env, coverage ≥ 95 % (100 %), correlation report (model/RTL; FPGA column pending the board)
