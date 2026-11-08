# Resume Defense Guide — Learn Everything Your Resume Entry Claims

Your resume entry makes 17 claims. An interviewer can pick any word and ask "explain that". This guide
takes each claim in order and gives you:

- **Know** — what you must be able to say without notes.
- **Where** — the project files and docs that hold it.
- **Prove it** — one exercise (on Ubuntu) that makes the claim yours.
- **Questions** — what interviewers ask, with short answers.

Work top to bottom. A claim is learned when you can answer its questions out loud and have done its exercise.
Deeper material: the learning plan (claude.ai), `docs/labs/RTL_DESIGN_LAB.md`, `docs/NOTES.md`, and the two slide decks.

**The entry being defended:**

> Systolic-Array Matrix-Multiplication Accelerator on FPGA | Group project with PhD scholar, EE Dept., IIT H | GitHub, Sept 2026 – present
> - Designed the RTL compute core of an N×N output-stationary systolic array in SystemVerilog: signed int8 MAC processing elements with 32-bit accumulators, input skew buffers, and a parameterized PE grid run by a controller FSM.
> - Derived and verified the latency (K + 2N cycles) and PE utilization (4×4, 8×8, 5.1 GOPS at 50 MHz in simulation) with self-checking cocotb testbenches against a NumPy golden model, using random and edge-case inputs.
> - Worked in a team co-simulation flow (Verilator + C++/SystemC models), 2,000 tests. In progress: FPGA bring-up on the Intel DE10-Lite and a UVM testbench.
> - Tools: RTL design, cocotb, Python, Intel Quartus, DE10-Lite (MAX 10)

---

## Part 1 — The project itself

### Claim 1: "Systolic-array matrix-multiplication accelerator"

**Know**
- An accelerator is hardware built for one job; here the job is C = A × B.
- Matrix multiply dominates ML workloads (fully connected layers, convolutions, attention).
- A CPU does a few multiply-adds per cycle; our 8×8 array does **64 per cycle**.
- A systolic array is a grid of identical processing elements (PEs) that each multiply-add and pass data
  to their neighbours, like a heartbeat pumping data through.

**Where:** `docs/NOTES.md` §12–§13; RTL slide deck slides 3 and 16.

**Prove it:** explain the project to a friend in 2 minutes with one drawing, no slides.

**Questions**
- *Why is a systolic array good for matrix multiply?* → n³ operations on only n² data: each value is
  reused N times as it moves, and only neighbour-to-neighbour wires are needed, so the clock can be fast.
- *Where is this used in industry?* → Google's TPU (a 256×256 array, 65,536 8-bit MACs), many phone and
  edge NPUs.

### Claim 2: "Group project with PhD scholar"

**Know** exactly which parts are yours and which are the team's. Your part: the **RTL compute core**
(PE, skew buffers, array, controller). Team work: models, co-simulation, UVM, board top level.

**Prove it:** finish Labs 3–6 of `docs/labs/RTL_DESIGN_LAB.md` so the compute core is genuinely your design.

**Questions**
- *What did you do yourself?* → "I designed and verified the compute core: the PE, skew buffers,
  parameterized array and controller FSM. The co-simulation and UVM flows were built with the team."

---

## Part 2 — Bullet 1: the design

### Claim 3: "Designed the RTL compute core … in SystemVerilog"

**Know**
- RTL = register-transfer level: registers plus the logic between them, written in an HDL.
- The rules the code follows: one clock, synchronous active-low reset, `<=` only in `always_ff`, a
  `default` in every `case` (no latches), synchronizers on asynchronous inputs.

**Where:** `rtl/core/pe.sv`, `skew_buffer.sv`, `systolic_array.sv`, `mm_controller.sv`; RTL slide deck.

**Prove it:** RTL lab, Labs 1–6.

**Questions**
- *Blocking vs non-blocking?* → `<=` updates all registers together at the clock edge (sequential logic);
  `=` updates immediately (combinational logic). Mixing them causes simulation races.
- *How do you avoid latches?* → assign every output on every path of `always_comb`; give every `case` a `default`.

### Claim 4: "N×N output-stationary systolic array"

**Know**
- **Output-stationary:** each PE(i, j) keeps C[i][j] in its own accumulator; A moves right, B moves down.
- **Weight-stationary** (Google TPU): each PE holds a weight; inputs move across and partial sums move down.
- **Input-stationary:** the input stays, weights and sums move.
- Output-stationary gives the simplest control and suits long dot products (large K).
- **N×N** is a parameter: the same RTL builds 2×2, 4×4, 8×8 or 16×16.

**Where:** `docs/NOTES.md` §13; RTL deck slide 16.

**Questions**
- *Why output-stationary and not weight-stationary?* → simplest control, no partial-sum movement, and
  C is read straight out of the accumulators at the end. Weight-stationary wins when the same weights
  are reused across many inputs, as in neural-network inference.

### Claim 5: "Signed int8 MAC processing elements with 32-bit accumulators"

**Know**
- A **MAC** (multiply-accumulate) does `acc = acc + a × b` every enabled cycle.
- **int8:** −128 … 127, two's complement. Both operands are declared `signed`, so the multiplier is signed.
- Product: 8 × 8 bits → 16 bits. Largest: (−128) × (−128) = **16,384**.
- Sum of K = 64 products: up to 64 × 16,384 = **1,048,576**, which needs 22 bits. 32 bits are safe up to
  K = 2¹⁷.
- The 16-bit product is **sign-extended** to 32 bits before adding.
- Each PE has 48 flip-flops: a 32-bit accumulator and two 8-bit pass-through registers.

**Where:** `rtl/core/pe.sv`; `docs/NOTES.md` §1 and §15.

**Prove it:** write your own `pe.sv` and pass `tb/test_pe.py` (RTL lab, Lab 3).

**Questions**
- *Why 32 bits?* → the bit-growth numbers above.
- *What happens if you forget `signed`?* → negative numbers are treated as large positive ones; −1 × −1
  gives 65,025 instead of 1.
- *Why int8?* → 4× less memory than fp32, much smaller multipliers (one 9×9 DSP each), and standard for
  ML inference.

### Claim 6: "Input skew buffers"

**Know**
- The RAMs give a whole column of A (and row of B) in the same cycle, but PE(i, j) is j hops from the left
  edge and i hops from the top.
- So lane n is delayed by n cycles: a triangle of registers, **N(N−1)/2** per buffer (6 for N = 4, 28 for N = 8).
- With the skew, A[i][k] and B[k][j] both reach PE(i, j) at step **k + 1 + i + j**, so they always meet.

**Where:** `rtl/core/skew_buffer.sv`; RTL deck slides 15 and 18.

**Prove it:** RTL lab, Lab 4; fill the 3×3 cycle table in `docs/NOTES.md` §14.

**Questions**
- *Why skew?* → without it, operands for PE(i, j) would arrive at different cycles and be multiplied with the wrong partners.

### Claim 7: "A parameterized PE grid"

**Know**
- Two `for (genvar …)` loops create N × N `pe` instances.
- Wires `a_h[i][j]` carry A rightward, `b_v[i][j]` carry B downward.
- All accumulators leave on one flat bus: C(i, j) is `c_out[(i*N + j)*32 +: 32]`.
- Changing N at the top changes every width below it, through `$clog2`.

**Where:** `rtl/core/systolic_array.sv`; RTL deck slides 5–6 and 16.

**Prove it:** RTL lab, Lab 5; pass `tb/test_systolic_array.py` for N = 2, 4, 8.

**Questions**
- *How does the design scale to 16×16?* → change N; 256 multipliers needed, and the DE10-Lite has 288
  9-bit multipliers (Yosys estimate), so it fits on multipliers; logic and timing need Quartus.

### Claim 8: "Run by a controller FSM"

**Know**
- Five states: IDLE → CLEAR (1 cycle) → COMPUTE (K cycles) → DRAIN (2N − 1 cycles) → DONE (1 cycle) → IDLE.
- COMPUTE reads column/row t of the RAMs; DRAIN feeds zeros while the last values travel to PE(N−1, N−1).
- Outputs: `busy`, `clear`, `rd_en`, `rd_addr = t`, `array_en`, `done`, `all_active`.

**Where:** `rtl/core/mm_controller.sv`; RTL deck slide 14.

**Prove it:** RTL lab, Lab 6; pass `tb/test_mm_core.py` and the co-simulation with your controller.

**Questions**
- *Why a DRAIN state?* → after the last read, values still need 2N − 1 cycles to reach the bottom-right PE.

---

## Part 3 — Bullet 2: the numbers and how they were verified

### Claim 9: "Derived and verified the latency (K + 2N cycles)"

**Know — the derivation:**
- The array alone needs K + 2N − 2 steps: the last product reaches PE(N−1, N−1) at step K − 1 + 2(N − 1).
- The controller adds **1 CLEAR** cycle and the block RAM adds **1 read-latency** cycle.
- So START → DONE = K + 2N − 2 + 1 + 1 = **K + 2N**. Example: N = 8, K = 64 → **80 cycles**.
- Verified by the hardware counter `PERF_TOTAL` in every test, and independently by timing the `done` pin in co-simulation.

**Where:** `rtl/core/mm_controller.sv`; `model/golden_model.py::expected_perf`; `docs/results/verification_report.md` (issue 5).

**Prove it:** derive K + 2N on paper; then check three rows of `docs/results/perf_model.csv`.

**Questions**
- *Your plan said K + 2N − 2 — why is it K + 2N?* → the array alone is K + 2N − 2; the CLEAR cycle and the
  RAM's one-cycle read latency add 2.

### Claim 10: "PE utilization"

**Know**
- Utilization = useful MACs ÷ (N² × cycles the array is enabled) = N²·K ÷ (N²·(K + 2N − 1)) = **K ÷ (K + 2N − 1)**.
- 4×4, K = 64: 64 ÷ 71 = **90.1 %**. 8×8, K = 64: 64 ÷ 79 = **81.0 %**.
- Lost cycles are fill and drain: the array is fully busy only from step 2N − 1 to K.
- Larger K → closer to 100 %; larger N → more fill/drain overhead.

**Where:** `docs/results/perf_model.csv`; `rtl/core/mm_regs.sv` (counters); RTL deck slide 12.

**Fix on your resume:** the parentheses currently list "4×4, 8×8" but no utilization number. Write it as
"81 % PE utilization for 8×8 at K = 64".

### Claim 11: "5.1 GOPS at 50 MHz in simulation"

**Know**
- One MAC = 2 operations (multiply + add).
- GOPS = 2 × MACs ÷ time = 2 × 4,096 ÷ (80 cycles ÷ 50 MHz) = **5.12 GOPS** for 8×8, K = 64.
- Peak (every PE busy every cycle) = 2 × 64 × 50 MHz = 6.4 GOPS.
- "In simulation" matters: real Fmax is unknown until Quartus runs. Say this clearly.
- End to end on the board, the **UART** dominates: loading A and B takes about 89 ms, computing about 1.6 µs.

**Questions**
- *Is 5.1 GOPS measured on hardware?* → no; it is computed from the simulated cycle count at the 50 MHz board clock.
- *What limits real performance?* → the UART link, not the array; real accelerators use high-bandwidth memory and data reuse.

### Claim 12: "Self-checking cocotb testbenches"

**Know**
- cocotb: testbenches in Python driving the simulator (Icarus) through `await RisingEdge(...)`, `dut.signal.value`.
- Self-checking: every test compares the DUT against expected values and prints PASS/FAIL by itself.
- Organised bottom-up: PE → skew buffer → array → core on the bus → whole board over UART. **37 tests** pass.
- X-propagation checks: no unknown values on outputs after reset.

**Where:** `tb/`; `tb/tb_utils.py`; learning plan Step 5.

**Prove it:** RTL lab, Lab 2; write one new test (learning plan Step 5).

**Questions**
- *Why cocotb instead of a SystemVerilog testbench?* → Python is quick to write, NumPy gives the reference
  model directly, and the same tests run on any simulator.

### Claim 13: "Against a NumPy golden model"

**Know**
- `matmul_int32()`: multiply in 64-bit, then wrap to 32 bits exactly like the hardware accumulator.
- `expected_perf()`: the formula for every counter.
- A golden model must follow the **spec**, not the RTL code — otherwise both can share the same bug.

**Where:** `model/golden_model.py`.

### Claim 14: "Using random and edge-case inputs"

**Know**
- Random: random matrices and random K from 1 to 64, hundreds of jobs per size.
- Edge cases and why: all zeros; all −128 (largest positive sum); all 127; −128 × 127 (largest negative sum);
  identity matrix; K = 1; K = 2N − 2 and 2N − 1 (exactly where `all_active` turns on — an off-by-one hotspot).

**Where:** `model/golden_model.py::edge_cases`; `model/vectors.py`.

**Questions**
- *Why not only random tests?* → random tests rarely hit exact corners like −128 × −128 or the fill/drain boundary.

---

## Part 4 — Bullet 3: team flows and what's in progress

### Claim 15: "Worked in a team co-simulation flow (Verilator + C++/SystemC models), 2,000 tests"

**Know**
- C++ bit-accurate model: adds in `uint32_t` because signed overflow is undefined in C++.
- SystemC models: loosely-timed (TLM-2.0 `b_transport`, fastest) and cycle-approximate (clocked, same FSM as the RTL).
- Verilator `--sc` turns the RTL into a SystemC module; it runs next to the CA model on the same jobs.
- Checked per job: result C, every counter, and START → DONE cycles at the pins.
- Result: **0 mismatches, 0-cycle error**. The "2,000" is N = 4 and 8 × 1,000 jobs each; the flow now
  covers 5 configurations × 1,000 jobs.
- Mutation test: changing `2N−1` to `2N−2` in the controller was caught only by the counters, while C stayed correct.

**Where:** `model/cpp/`, `model/systemc/`, `cosim/`; models slide deck; `docs/results/phase5_models.md`.

**Prove it:** learning plan Step 6 (run the co-simulation and the mutation test yourself).

**Questions**
- *Why co-simulate if cocotb already passes?* → it checks timing and counters against an independent model,
  which caught a bug that result-only checks missed.

### Claim 16: "In progress: FPGA bring-up on the Intel DE10-Lite (MAX 10)" and the Quartus tool

**Know**
- The flow: synthesis → fitter (place and route) → timing analysis → `.sof` → program over USB-Blaster.
- Pins from `tools/gen_quartus.py`; the 50 MHz clock and false paths in `quartus/top_de10lite.sdc`.
- Slack ≥ 0 means timing met; how pipelining the PE would fix a failure.
- MAX 10 10M50: 49,760 logic elements, 288 9-bit multipliers, 182 M9K RAM blocks; 8×8 needs 64 multipliers and 16 RAMs.

**Where:** the hardware runbook (claude.ai); `docs/interview/FPGA_FLOW_INTERVIEW.md`; RTL lab Lab 8.

**Prove it:** do the hardware runbook. Until then keep "in progress", and be ready to say exactly what is not yet done.

### Claim 17: "In progress: a UVM testbench"

**Know** — the UVM environment now exists and passes in simulation (104/104 runs, 100 % of 55 coverage bins):
- Bus agent: driver, monitor, sequencer; sequences of jobs; a scoreboard that calls the C++ model through **DPI-C**.
- Functional coverage and SVA assertions; directed and constrained-random tests.
- Runs on Verilator, so coverage is a hand-written collector rather than native covergroups.

**Where:** `uvm/`; `docs/vplan.md`; `docs/results/uvm_regression.md`; learning plan Step 7.

**Fix on your resume:** UVM is no longer "in progress" in simulation. Once you have studied it (learning plan
Step 7), you can write "UVM testbench (DPI-C scoreboard, coverage, SVA) on Verilator: 104/104 regressions".

---

## Part 5 — The "Tools" line

- **"RTL design"** is a skill, not a tool. Replace it with the language: **SystemVerilog**.
- **cocotb, Python:** you will have used both by the end of Step 5.
- **Intel Quartus, DE10-Lite (MAX 10):** keep only once you have compiled and programmed the board yourself.
- Worth adding once learned: **Verilator**, **Icarus Verilog**, **SystemC**, **GTKWave**.

---

## Suggested order (three weeks)

1. **Week 1 — the design (Claims 1–8):** RTL lab Labs 0–6. This makes "Designed the RTL compute core" true.
2. **Week 2 — the numbers and verification (Claims 9–14):** derive K + 2N, utilization and GOPS on paper;
   write one new cocotb test; run the hardware runbook (Claim 16).
3. **Week 3 — the team flows (Claims 15, 17):** learning plan Steps 6–7; run the co-simulation and the UVM
   regression yourself; update the resume lines marked above.

## Final self-test

Answer each out loud in under one minute, with no notes:

- [ ] Draw a PE and say how many bits each register has and why.
- [ ] Derive K + 2N for N = 8, K = 64 (= 80) and explain the extra 2 cycles.
- [ ] Compute utilization (81 %) and GOPS (5.12) for 8×8 at K = 64.
- [ ] Explain why the inputs are skewed and how many skew registers 8×8 needs (28 per buffer).
- [ ] Name five edge cases and why each exists.
- [ ] Explain what co-simulation compares and the mutation-test story.
- [ ] Say exactly what has and hasn't run on the board.
- [ ] Say exactly which parts you designed and which the team built.
