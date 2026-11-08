# How We Built the FPGA Design Flow — Interview Guide

**Question this answers:** *"Walk me through the FPGA design flow you used in this project."*

How to use it:
1. Open with the **30-second answer**.
2. If they want depth, walk the **15 steps** in order, using the "Say it" lines.
3. Be clear about status: **steps 1–11 and 15 are done (simulation); steps 12–14 need the board and are not done yet.**
4. Say **"we"** for team work and **"I"** for your own part (the RTL compute core).

---

## 1. The 30-second answer

> "We followed the standard flow: spec, micro-architecture, RTL, then verification before any hardware.
> The RTL is SystemVerilog, linted with Verilator and Verible. We verified it in layers: cocotb unit
> and system tests with X-propagation checks, bit-accurate C++ and SystemC reference models,
> Verilator co-simulation of RTL against the SystemC model, a UVM testbench with a DPI-C scoreboard and
> assertions, formal proofs with SymbiYosys, and code coverage. A Yosys estimate shows the design fits the
> MAX 10's multipliers up to 16×16. The next stage is Quartus — synthesis, place and route, pin
> assignment, timing with an SDC constraint, then programming the DE10-Lite and correlating the
> on-board cycle counters with the models."

---

## 2. The flow at a glance

```
 SPEC ─▶ MICRO-ARCH ─▶ RTL ─▶ LINT ─▶ SIMULATE ─▶ MODELS ─▶ CO-SIM ─▶ UVM ─▶ FORMAL ─▶ COVERAGE
  1          2          3      4         5           6         7       8       9         10
                                                                                          │
   ┌──────────────────────────────────────────────────────────────────────────────────────┘
   ▼
 PRE-SYNTH ESTIMATE ─▶ QUARTUS: SYNTH ▶ FIT (P&R) ▶ PINS ▶ STA ─▶ PROGRAM + BRING-UP ─▶ ON-BOARD CHECK
        11                              12                              13                    14
 + 15. Automation: Makefiles, regression scripts, pinned toolchain, CI (written)

 ✅ done in simulation: 1–11, 15        ⏳ needs Quartus + board: 12, 13, 14
```

---

## 3. Step by step

### Step 1 — Specification and architecture ✅
- **What:** C = A × B on an N×N **output-stationary systolic array**; signed **int8** inputs, **int32**
  accumulators; N and K_MAX are parameters; one **50 MHz** clock; host link over UART.
- **Why:** int8 matches ML inference; int32 cannot overflow for K ≤ 64 (16-bit products + 6 bits of growth);
  one clock domain means no clock-domain crossing.
- **Numbers fixed here:** a job takes **K + 2N** cycles; 8×8 at K = 64 → **81 %** PE utilisation.
- **Files:** `docs/PLAN.md` §1, §6.
- **Say it:** "We fixed data types, dataflow and the cycle formula before writing RTL, so every later
  step had a number to check against."

### Step 2 — Micro-architecture and interfaces ✅
- **What:** split into small modules: PE → array → skew buffers → banked RAMs → controller FSM →
  register block → core → UART bridge → board top.
- **Key decisions:**
  - **Banked RAM** (one RAM per row of A / column of B) so a whole column and row are read every cycle.
  - **Skew buffers** (lane n delayed n cycles) so A[i][k] and B[k][j] meet in PE(i, j).
  - **One valid/ready register bus** with a fixed register map, used by the UART bridge, cocotb, SystemC
    and UVM alike.
  - **Performance counters** in hardware (total, compute, fill/drain, idle, MACs) for HW/SW correlation.
- **Say it:** "The register bus was a verification decision: one interface means one agent and one
  model can drive everything."

### Step 3 — RTL coding ✅  *(your part: the compute core)*
- **What:** synthesizable **SystemVerilog**, all sizes parameterized; `genvar` loops build the grid.
- **Rules followed:** single clock, synchronous active-low reset; `<=` only in `always_ff`; every `case`
  has a `default` (no latches); asynchronous inputs through a **2-flip-flop synchronizer**; slow events use a
  **tick enable**, never a derived clock; RAM written in the pattern Quartus infers as **M9K**.
- **Guard:** illegal parameters (N not a power of 2, buffers too large) stop simulation with `$fatal`.
- **Files:** `rtl/core/`, `rtl/top/`, `rtl/common/`.
- **Say it:** "The PE is a signed 8×8 multiply into a 32-bit accumulator with pass-through registers;
  the array is two genvar loops; the skew buffer is a triangle of shift registers."

### Step 4 — Lint ✅
- **What:** Verilator `--lint-only -Wall` for N = 4, 8, 16 (clean on `rtl/core`, `rtl/top`); Verible for style.
- **Why:** catches width mismatches, unused signals and latches **before** simulation.
- **Files:** `tools/lint.sh`.

### Step 5 — Simulation: unit and system tests ✅
- **What:** **cocotb** (Python) testbenches on **Icarus** (4-state); NumPy golden model for expected results.
- **Coverage of tests:** PE, skew buffer, array, RAM, controller, bus, UART, bridge, full board top over UART;
  random matrices and edge cases (−128 × −128, zeros, K = 1, the 2N−1 boundary).
- **X-propagation:** checks that control, bus and board outputs are never X after reset.
- **Result:** **37 tests pass** (+1 slow N = 8 system test).
- **Files:** `tb/`, `model/golden_model.py`.
- **Say it:** "Bottom-up: each module first, then the core on the bus, then the whole board over the UART pins."

### Step 6 — Reference models ✅
- **What:** bit-accurate **C++** model (uint32 accumulate = defined wrap), an **analytical** cycle model,
  and **SystemC/TLM-2.0** loosely-timed and cycle-approximate models.
- **Why:** a trusted answer **and** a trusted cycle count, usable from SystemC and UVM (DPI-C).
- **Result:** models agree with NumPy on 3 × 1000 shared vectors (N = 4, 8, 16).
- **Files:** `model/cpp/`, `model/systemc/`, `model/vectors.py`.

### Step 7 — Co-simulation ✅
- **What:** Verilator `--sc` turns the RTL into a SystemC module; it runs next to the cycle-approximate
  model on one clock with the same job sequence.
- **Checks per job:** result C, all counters, and START→DONE cycles measured **at the pins**.
- **Result:** **5 configurations × 1000 jobs, 0 mismatches, 0-cycle error.**
- **Files:** `cosim/`, `docs/results/phase5_models.md`.
- **Say it:** "It proves the model and the RTL are the same machine, so the model can be trusted for
  performance studies."

### Step 8 — UVM ✅
- **What:** UVM environment: bus agent (driver, monitor, sequencer), **DPI-C scoreboard** calling the C++ model,
  functional coverage, **SVA** assertions; directed + constrained-random tests.
- **Result:** **104/104** simulations over 4 configurations, **1.89 M** scoreboard checks, **100 %** of the
  55 coverage bins, 0 assertion failures.
- **Honest limits:** runs on **Verilator** (not Questa/VCS/Xcelium); coverage is an explicit-bin collector,
  not native covergroups; Verilator is 2-state.
- **Files:** `uvm/`, `docs/results/uvm_regression.md`, `docs/vplan.md`.

### Step 9 — Formal verification ✅
- **What:** **SymbiYosys** proves bus-protocol and FSM properties by **k-induction** with **unconstrained**
  bus inputs (holds for any bus master): `rvalid` exactly one cycle after a read, legal FSM states,
  one-cycle `done`, correct state transitions. Cover points show the proof is not vacuous.
- **Mutation check:** a deliberately broken `rvalid` fails with a counterexample waveform.
- **Files:** `formal/`.
- **Say it:** "Simulation shows it works for the inputs we drove; formal shows the protocol holds for all inputs."

### Step 10 — Code coverage and closure ✅
- **What:** Verilator RTL coverage: **line 96.9 %, branch 100 %, toggle 90.7 %**; **100 % after 2 documented
  waivers** (unreachable FSM default; upper bits of 32-bit counters).
- **Plus:** injected bugs (mutations) were each caught — one only by the performance counters.
- **Files:** `uvm/code_coverage.py`, `docs/results/code_coverage.md`, `docs/results/verification_report.md`.

### Step 11 — Pre-synthesis estimate ✅
- **What:** sv2v + **Yosys** coarse synthesis to count hard blocks before Quartus.
- **Result:** multipliers **16 / 64 / 256** and RAMs **8 / 16 / 32** for N = **4 / 8 / 16**;
  the MAX 10 10M50 has **288** 9-bit multipliers and **182** M9K → fits up to 16×16 on multipliers.
- **Honest limit:** no MAX 10 mapping and **no timing** — logic usage and Fmax need Quartus.
- **Files:** `tools/synth_estimate.sh`.

### Step 12 — Quartus implementation ⏳ *(not done — Quartus not installed yet)*
- **Synthesis:** RTL → LUTs, flip-flops, M9K RAMs, embedded multipliers.
- **Fitter (place and route):** places logic on the chip and routes wires.
- **Pin assignment:** generated by `tools/gen_quartus.py` (one pin table → `.qsf`), 3.3-V LVTTL;
  **still to be checked** against Terasic's System Builder.
- **Timing constraints (SDC):** `create_clock -period 20.000` (50 MHz) on `MAX10_CLK1_50`;
  `set_false_path` on buttons, switches, LEDs and UART pins (asynchronous / slow I/O).
- **Static timing analysis:** Timing Analyzer must show **slack ≥ 0**; record Fmax and resources.
- **Plan if timing fails:** add a pipeline register between multiplier and adder in each PE
  (latency becomes K + 2N + 1; update the model).
- **Files:** `quartus/`, `tools/build.sh`.

### Step 13 — Programming and bring-up ⏳ *(not done)*
- Program the `.sof` over the on-board **USB-Blaster** (`quartus_pgm`).
- **Order:** small warm-up designs first (switch → LED, blinky, hex counter, UART echo) to prove pins,
  clock, reset and UART wiring; then the accelerator at **N = 4**, then **N = 8**.
- **Debug:** LEDs show the FSM state; HEX shows the compute-cycle counter; **SignalTap** if needed.

### Step 14 — On-board validation and correlation ⏳ *(not done)*
- `host.py --tests` on the board, results compared with NumPy.
- `mm_host --csv` reads the hardware counters → `tools/correlate.py` fills the **FPGA column**
  next to analytical, SystemC and RTL (currently 0 % error between those three).

### Step 15 — Automation and reproducibility ✅
- One command per stage: `pytest`, `make -C model/...`, `make -C cosim`, `uvm/regress.py`, `make -C formal`,
  `tools/lint.sh`, `tools/build.sh`.
- Toolchain pinned in `environment.yml`; tool list in `docs/TOOLS.md`.
- **CI workflow is written but not active yet** (needs a GitHub token with the `workflow` scope).

---

## 4. Design decisions you may be asked to defend

| Decision | Alternative | Why we chose it |
|---|---|---|
| Output-stationary | Weight-stationary (TPU) | Simplest control; C stays in place; good for large K |
| int8 × int8 → int32 | Floating point | Small multipliers (fit 9×9 DSPs); no overflow for K ≤ 64 |
| One 50 MHz clock | Faster PLL clock | No CDC; DE10-Lite board clock; raise later only after STA |
| Banked RAM | One wide RAM | Needs N reads per cycle at the same address |
| Valid/ready register bus | Ad-hoc ports | One interface for UART, cocotb, SystemC, UVM |
| Hardware perf counters | Software timing only | Lets HW and SW models be compared cycle for cycle |
| UART host link | PCIe / Ethernet | Simple, board-independent; we know it is the bottleneck (≈ 89 ms load vs ≈ 1.6 µs compute) |

---

## 5. Likely interview questions

| Question | Short answer |
|---|---|
| What is the difference between synthesis and place-and-route? | Synthesis maps RTL to the chip's resources (LUTs, FFs, RAMs, DSPs); place-and-route decides where they go and wires them. |
| What does your SDC do? | Defines the 50 MHz clock (20 ns) so the tool knows the target, and marks asynchronous board I/O as false paths. |
| What is slack? | Required time minus arrival time; negative slack means the design fails at that clock. |
| How would you fix a timing failure? | Find the critical path in the Timing Analyzer; pipeline it (register after the multiplier), reduce logic depth, or lower the clock. |
| Where is your critical path likely to be? | Inside the PE: multiply, then 32-bit add, into the accumulator; possibly the 64:1 result mux for 8×8. |
| Why a 2-FF synchronizer? | The UART RX pin and buttons are asynchronous; two flops make metastability very unlikely. |
| Any clock-domain crossings? | No — one clock; the only asynchronous inputs go through synchronizers. |
| Why does the RAM have 1-cycle latency? | M9K block RAM has registered inputs; the controller delays its valid signal by one cycle to match. |
| `.sof` vs `.pof`? | `.sof` loads into the FPGA and is lost at power-off; `.pof` writes the on-chip flash. |
| Why simulate so much before hardware? | Bugs are much cheaper to find in simulation; on the board you only see pins, LEDs and SignalTap. |
| What does formal give you that UVM doesn't? | A proof for all inputs, not just the ones the tests generated. |
| Why X-propagation checks? | Verilator is 2-state and hides X; the 4-state Icarus tests show no X reaches outputs after reset. |
| Have you done gate-level simulation? | Not yet — it needs the Quartus netlist (step 12). |
| How is an ASIC flow different? | Adds floorplanning, clock-tree synthesis, power, DFT, sign-off STA and physical checks; FPGA resources are fixed. |
| Is it working on the board? | Not yet: everything is verified in simulation; Quartus compile and bring-up are the next steps. |

---

## 6. Two-minute spoken version

> "We started from a spec: an N×N output-stationary systolic array, int8 inputs, int32 accumulators,
> one 50 MHz clock, and a cycle budget of K + 2N. I designed the compute core — the processing element,
> skew buffers and parameterized array — in SystemVerilog, with the team adding the RAM banks,
> controller FSM, a valid/ready register bus with performance counters, and a UART bridge.
>
> Before any hardware we verified in layers. Lint with Verilator and Verible. cocotb tests on Icarus,
> including X-propagation checks — 37 tests. Bit-accurate C++ and SystemC reference models, then
> Verilator co-simulation against the SystemC model: five configurations, a thousand jobs each, zero
> mismatches and zero cycles of timing error. A UVM environment with a DPI-C scoreboard, assertions and
> 100 % of its coverage bins. Formal proofs of the bus protocol and FSM with SymbiYosys, and code coverage
> closed with two documented waivers. A Yosys estimate shows even 16×16 fits the MAX 10's multipliers.
>
> The next stage is Quartus: synthesis, fitting, pin assignment, timing with our SDC — if the multiply-add
> path fails 50 MHz I'd pipeline the PE — then program the DE10-Lite, bring up 4×4 then 8×8, and
> compare the on-board cycle counters with the models."
