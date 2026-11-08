# RTL Design Lab — Build the Project's Hardware Yourself

**Goal:** design the project's RTL with your own hands, using the same tools the project used, until you
can rebuild the compute core from an empty file and prove it correct.

**How it works:** each lab gives you a specification, not the answer. You write the module, then the
**project's own tests grade it**. Only after it passes do you compare with the project's version.

**Where:** everything runs on the **Ubuntu machine**, in the `fpga` conda environment.
**Time:** about 25–30 hours for Labs 0–9. Lab 10 needs the board.

Read alongside: `docs/NOTES.md` §5–§9 and §12–§14, and the RTL slide deck in `docs/slides/01_rtl_overview/`.

---

## The design loop you will repeat in every lab

1. **Read the spec** and draw the hardware on paper first (registers, muxes, wires).
2. **Write** the module in VS Code.
3. **Lint** with Verilator — catches width mistakes and latches in seconds.
4. **Simulate** with Icarus + cocotb — the tests say PASS or FAIL.
5. **Debug** with GTKWave when a test fails — look at the waveform, not the code.
6. **Synthesize** (Yosys estimate, then Quartus) — see what hardware your code became, and its timing.
7. **Compare** with the project's version and write down every difference you notice.

---

## Lab 0 — Set up your workbench (1 hour)

**Editor:** VS Code with the extension **"Verilog-HDL/SystemVerilog/Bluespec SystemVerilog"** (syntax
colours). Optional: **Verible** formatter/linter integration.

**Terminal setup (every new terminal):**
```bash
cd ~/fpga-systolic-array
conda activate fpga
git pull
```

**Your own branch and folder** — your work never touches `main`:
```bash
git checkout -b my-rtl
mkdir -p labs/my_rtl
```

**Check the tools answer:**
```bash
iverilog -V | head -1          # Icarus Verilog (simulator)
verilator --version            # Verilator (lint, fast simulation)
yosys -V                       # Yosys (open-source synthesis)
gtkwave --version | head -1    # waveform viewer
quartus_sh --version | head -2 # Quartus (only after the hardware runbook, Part 0)
```

- [ ] Every command prints a version.
- [ ] You are on branch `my-rtl` (`git branch` shows `* my-rtl`).

**Rule for all labs:** don't open the project's version of a module until your own passes its test.
To look afterwards: `git show main:rtl/core/pe.sv`.

---

## Lab 1 — First module with the raw tools (2 hours)

**Learn:** the bare tool flow without any framework — compile, simulate, view waves, lint, synthesize.

**Spec — `counter`:** a W-bit counter (parameter `W`, default 4).
Ports: `clk`, `rst_n` (synchronous, active low), `en`, output `q[W-1:0]`.
On a rising clock edge: if `rst_n` is 0, `q` becomes 0; else if `en` is 1, `q` adds 1 (wrapping).

**1. Write `labs/my_rtl/counter.sv` yourself.** Then compare with this reference:
```systemverilog
module counter #(parameter int W = 4) (
    input  logic         clk,
    input  logic         rst_n,
    input  logic         en,
    output logic [W-1:0] q
);
    always_ff @(posedge clk) begin
        if (!rst_n)  q <= '0;
        else if (en) q <= q + 1'b1;
    end
endmodule
```

**2. Write a plain SystemVerilog testbench** `labs/my_rtl/tb_counter.sv`:
```systemverilog
`timescale 1ns/1ps
module tb_counter;
    logic clk = 0, rst_n = 0, en = 0;
    logic [3:0] q;

    counter #(.W(4)) dut (.clk(clk), .rst_n(rst_n), .en(en), .q(q));

    always #10 clk = ~clk;                 // 20 ns period = 50 MHz

    initial begin
        $dumpfile("counter.vcd");
        $dumpvars(0, tb_counter);
        repeat (2) @(posedge clk);
        @(negedge clk) begin rst_n = 1; en = 1; end   // change inputs away from the rising edge
        repeat (20) @(posedge clk);
        #1;
        if (q !== 4'd4) $display("FAIL: q = %0d, expected 4", q);   // 20 counts wrap to 4
        else            $display("PASS: q = %0d", q);
        $finish;
    end
endmodule
```

**3. Compile and run with Icarus:**
```bash
cd labs/my_rtl
iverilog -g2012 -o counter_sim counter.sv tb_counter.sv
vvp counter_sim
```
- [ ] Prints `PASS: q = 4`.

**4. Look at the waveform in GTKWave:**
```bash
gtkwave counter.vcd &
```
In the left panel click `tb_counter`, select `clk`, `rst_n`, `en`, `q`, press **Append**. Use
**Time → Zoom → Zoom Best Fit**. Right-click `q` → **Data Format → Decimal**.
- [ ] You can see `q` step 0, 1, 2 … 15, 0, 1 … on rising edges after `en` goes high.

**5. Lint with Verilator:**
```bash
verilator --lint-only -Wall counter.sv
```
- [ ] No output (clean).
- [ ] Now break it on purpose: change `q <= q + 1'b1` to `q = q + 1'b1` (blocking in `always_ff`). Lint
      again and read the warning. Undo it.

**6. See the hardware with Yosys:**
```bash
yosys -p "read_verilog -sv counter.sv; synth -top counter; stat"
```
- [ ] The cell list shows **4 flip-flops** (`$_SDFFE_…` or similar) and a handful of logic cells for the adder.
      Change `W` to 8 in the file and run again: the flip-flop count doubles.

If Yosys rejects a SystemVerilog construct, convert the file to plain Verilog first with **sv2v** (the
project's `tools/synth_estimate.sh` does the same):
```bash
SV2V=~/tools/sv2v/sv2v-Linux/sv2v
$SV2V counter.sv > /tmp/counter.v
yosys -p "read_verilog /tmp/counter.v; synth -top counter; stat"
```

**Check questions:** Why are inputs changed on the falling edge? What does `'0` mean? Why `<=`?

---

## Lab 2 — The same test in cocotb (2 hours)

**Learn:** how the project writes tests — Python, run by pytest, using the project's helpers.

**1. Create `labs/test_lab_counter.py`:**
```python
"""Lab 2: cocotb test for labs/my_rtl/counter.sv, using the project's tb/tb_utils.py helpers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tb"))

import cocotb
from cocotb.triggers import ClockCycles, FallingEdge

from tb_utils import ROOT, run_sim, start_clock


@cocotb.test()
async def counts_when_enabled(dut):
    start_clock(dut.clk)
    dut.en.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await FallingEdge(dut.clk)
    assert int(dut.q.value) == 0

    dut.en.value = 1
    for expected in range(1, 40):
        await FallingEdge(dut.clk)
        assert int(dut.q.value) == expected % 16, f"after {expected} edges"

    dut.en.value = 0
    held = int(dut.q.value)
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    assert int(dut.q.value) == held, "q must hold while en = 0"


def test_lab_counter():
    run_sim("counter", [ROOT / "labs" / "my_rtl" / "counter.sv"], "test_lab_counter",
            parameters={"W": 4}, build_name="lab_counter")
```

**2. Run it, then run it again with waveforms:**
```bash
cd labs
pytest -q test_lab_counter.py
WAVES=1 pytest -q test_lab_counter.py
ls ../tb/sim_build/lab_counter/        # the waveform file (.fst or .vcd) is here
```
- [ ] `1 passed`.
- [ ] Break the counter (for example remove the `en` check), run again, and read the assertion message
      cocotb prints. Undo it.

**Check questions:** Why does the test read values on `FallingEdge`? What does `run_sim` do (open
`tb/tb_utils.py` and read it)?

---

## Lab 3 — The processing element, `pe.sv` (3 hours)

**Learn:** signed arithmetic, bit growth, registers with clear and enable — the heart of the project.

**Spec — must match exactly, because the project's test grades it:**
- Module `pe`, parameters `DW = 8` (operand width) and `AW = 32` (accumulator width).
- Inputs: `clk`, `rst_n`, `clear`, `en`, `a_in` (signed, DW bits), `b_in` (signed, DW bits).
- Outputs: `a_out`, `b_out` (signed, DW bits), `acc` (signed, AW bits).
- On a rising edge:
  - if `rst_n` is 0 **or** `clear` is 1 → `acc`, `a_out`, `b_out` all become 0 (`clear` wins over `en`);
  - else if `en` is 1 → `acc` becomes `acc + a_in × b_in` (signed), `a_out` becomes `a_in`, `b_out` becomes `b_in`;
  - else everything holds.

**Design steps (on paper first):** one multiplier, one adder, three registers. How many bits is the product?
How do you make sure −128 × −128 is +16384 and not a large unsigned number?

**1. Write `labs/my_rtl/pe.sv`.** Lint it:
```bash
verilator --lint-only -Wall labs/my_rtl/pe.sv
```

**2. Grade it with the project's test** (on your `my-rtl` branch only):
```bash
cp labs/my_rtl/pe.sv rtl/core/pe.sv
cd tb && pytest -q test_pe.py
```
The test checks 1000+ random signed pairs, the corner cases −128 × −128 and 127 × −128, `en` hold and `clear`.
- [ ] `test_pe.py` passes.

**3. Debug if it fails:** `WAVES=1 pytest -q test_pe.py`, open the waveform from `tb/sim_build/pe/`,
right-click `acc` → **Data Format → Signed Decimal**, find the first wrong value.

**4. Compare:** `git diff main -- rtl/core/pe.sv`. Write down each difference and whether it matters.

**5. See the multiplier** (sv2v converts SystemVerilog for Yosys):
```bash
~/tools/sv2v/sv2v-Linux/sv2v rtl/core/pe.sv > /tmp/pe.v
yosys -p "read_verilog /tmp/pe.v; synth -top pe; stat"
```
- [ ] The report contains a multiply cell; note how many flip-flops (expect 32 + 8 + 8 = 48).

**Common mistakes:** forgetting `signed` (wrong results for negative numbers); clearing only `acc` but not
`a_out`/`b_out`; using `=` inside `always_ff`.

---

## Lab 4 — The skew buffer, `skew_buffer.sv` (2 hours)

**Learn:** parameterized `generate` loops, shift registers, flat lane buses.

**Spec:**
- Module `skew_buffer`, parameters `N = 4` (lanes) and `DW = 8` (lane width).
- Inputs: `clk`, `rst_n`, `clear`, `din[N*DW-1:0]`. Output: `dout[N*DW-1:0]`.
- Lane n is bits `[n*DW +: DW]`. **Lane n of `dout` equals lane n of `din` from n cycles ago.**
  Lane 0 has no delay (a plain wire). Reset or `clear` empties every register (zeros).

**Design steps:** lane 1 has 1 register, lane 2 has 2, … lane N−1 has N−1. How many registers in total for N = 4?

**1. Write `labs/my_rtl/skew_buffer.sv`**, lint it with `-GN=4` and `-GN=8`:
```bash
verilator --lint-only -Wall -GN=8 labs/my_rtl/skew_buffer.sv
```

**2. Grade it:**
```bash
cp labs/my_rtl/skew_buffer.sv rtl/core/skew_buffer.sv
cd tb && pytest -q test_skew_buffer.py      # runs N = 2, 4, 8
```
- [ ] All three sizes pass.

**3. Compare:** `git diff main -- rtl/core/skew_buffer.sv`.

**Common mistakes:** registering lane 0; an off-by-one in the number of registers; part-select
written as `[n*DW+DW-1 : n*DW]` with a variable `n` (use `+:` instead).

---

## Lab 5 — The systolic array, `systolic_array.sv` (3 hours)

**Learn:** building a grid with two `genvar` loops, wiring neighbours, flattening outputs.

**Spec:**
- Module `systolic_array`, parameters `N = 4`, `DW = 8`, `AW = 32`.
- Inputs: `clk`, `rst_n`, `clear`, `en`, `a_in[N*DW-1:0]` (lane i = row i, left edge),
  `b_in[N*DW-1:0]` (lane j = column j, top edge). Output: `c_out[N*N*AW-1:0]`.
- Instantiate N×N of **your** `pe`. `a` flows left → right along a row, `b` flows top → bottom along a column.
- PE(i, j)'s accumulator goes to `c_out[(i*N + j)*AW +: AW]`.
- The inputs arrive already skewed (the test does it), so the array itself has no skew logic.

**Design steps:** draw a 2×2 grid. You need wires for "a entering PE(i, j) from the left" (N rows × N+1
columns) and "b entering PE(i, j) from above" (N+1 rows × N columns).

**1. Write `labs/my_rtl/systolic_array.sv`.** Lint:
```bash
verilator --lint-only -Wall -GN=4 labs/my_rtl/pe.sv labs/my_rtl/systolic_array.sv --top-module systolic_array
```

**2. Grade it** (it uses your PE from Lab 3):
```bash
cp labs/my_rtl/systolic_array.sv rtl/core/systolic_array.sv
cd tb && pytest -q test_systolic_array.py   # N = 2, 4, 8; random and edge-case matrices vs NumPy
```
- [ ] All sizes pass.

**3. In the waveform** (`WAVES=1`), pick PE(1, 1) inside the hierarchy and watch its `acc` grow, one product per cycle.

**4. Count hardware:** the project's estimate script synthesizes the core (now with your PE and array)
for N = 4, 8 and 16 — expect 16, 64 and 256 multipliers:
```bash
tools/synth_estimate.sh
```

---

## Lab 6 — Block RAM and the controller FSM (4 hours)

**Learn:** writing RAM so the tool infers block RAM; a state machine that sequences a whole job.

**Part A — `sram_sp.sv`.**
- Parameters `WIDTH = 8`, `DEPTH = 64`. Inputs `clk`, `we`, `addr[$clog2(DEPTH)-1:0]`, `wdata[WIDTH-1:0]`;
  output `rdata[WIDTH-1:0]`.
- Write when `we` is 1. **Read is registered:** `rdata` shows `mem[addr]` one cycle later (this is what
  makes Quartus use M9K block RAM). No reset on the memory.

**Part B — `mm_controller.sv`** (ports must match, because `mm_core.sv` instantiates it):
- Parameters `N = 4`, `K_MAX = 64`. Inputs `clk`, `rst_n`, `start`, `k_len[$clog2(K_MAX+1)-1:0]`.
- Outputs `busy`, `done`, `clear`, `array_en`, `all_active`, `rd_en`, `rd_addr[$clog2(K_MAX)-1:0]`, `state_o[2:0]`.
- States in this order (their numbers appear on the LEDs): IDLE = 0, CLEAR = 1, COMPUTE = 2, DRAIN = 3, DONE = 4.
- A step counter `t`:
  - IDLE: on `start`, save `k_len` as K and go to CLEAR.
  - CLEAR: set `t` to 0, go to COMPUTE.
  - COMPUTE: `t` counts up each cycle; after the cycle where `t` = K − 1, go to DRAIN.
  - DRAIN: keep counting; when `t` = K + 2N − 2, go to DONE.
  - DONE: go back to IDLE.
- Outputs: `busy` = not IDLE; `done` = in DONE; `clear` = in CLEAR; `array_en` = in COMPUTE or DRAIN;
  `rd_en` = in COMPUTE; `rd_addr` = low bits of `t`; `all_active` = `array_en` and 2N − 1 ≤ `t` ≤ K;
  `state_o` = the state number.

**Why these exact rules:** the performance counters and every model (C++, SystemC, UVM) assume them. A
total of **K + 2N** cycles per job falls out of them — check it on paper before you code.

**1. Write both files**, lint them.

**2. Grade them together with the whole core:**
```bash
cp labs/my_rtl/sram_sp.sv rtl/core/sram_sp.sv
cp labs/my_rtl/mm_controller.sv rtl/core/mm_controller.sv
cd tb && pytest -q test_mm_core.py          # 200+ random jobs per N, checks C and every counter
cd .. && make -C cosim run N=4              # your RTL vs the SystemC model, 1000 jobs
```
- [ ] `test_mm_core.py` passes.
- [ ] Co-simulation reports 0 mismatches and 0-cycle error.

**3. Check the RAM was inferred:** after Lab 8's Quartus compile, the Fitter report's **RAM Summary**
lists M9K blocks. A combinational read (`assign rdata = mem[addr];`) cannot be placed in M9K block RAM,
because M9K reads are registered; Quartus would build the memory from flip-flops instead.

---

## Lab 7 — Read and trace the rest of the core (3 hours)

You won't rewrite these, but you must be able to explain them line by line:
- `rtl/core/mm_regs.sv` — address decode, registers, performance counters, 1-cycle read latency.
- `rtl/core/mm_core.sv` — how the banked RAMs, skew buffers, array and controller connect.
- `rtl/top/uart_bus_bridge.sv` and `rtl/top/top_de10lite.sv` — UART commands onto the bus, board pins.

**Exercise:** trace one value from a bus write at address `0x1083` to the PE that uses it. Write each
signal name it passes through, and the clock cycle it arrives (`docs/slides/01_rtl_overview/`, slide 18,
has the formula).

**Then run everything with your RTL in place:**
```bash
cd tb && pytest -q && cd ..                      # all cocotb tests
python3 uvm/regress.py --config 4:64 --seeds 2  # UVM, short
tools/lint.sh                                    # lint, N = 4 / 8 / 16
make -C formal                                   # formal proof of bus + FSM properties
```
- [ ] Everything passes with **your** PE, skew buffer, array, RAM and controller.

---

## Lab 8 — Synthesis and timing in Quartus (3 hours, needs Quartus installed)

**Learn:** what your RTL became on the real chip, and whether it is fast enough.

**1. Compile the accelerator with your RTL:**
```bash
tools/build.sh quartus
```
Read the printed summary: logic elements, registers, memory bits, 9-bit multipliers, Fmax, slack.

**2. Open the reports** in `quartus/output_files/`:
- `top_de10lite.map.rpt` (Analysis & Synthesis) → **Resource Usage by Entity**: how much each of your modules uses.
- `top_de10lite.fit.rpt` (Fitter) → **RAM Summary**: your `sram_sp` should appear as M9K.
- `top_de10lite.sta.rpt` (Timing Analyzer) → **Fmax Summary** and the worst setup path.

**3. Look at the circuits in the Quartus GUI** (`quartus quartus/top_de10lite.qpf &`):
- **Tools → Netlist Viewers → RTL Viewer:** your PE drawn as multiplier, adder and registers.
- **Technology Map Viewer:** the same after mapping to LUTs and DSP blocks.
- **Tools → Timing Analyzer → Report Timing:** the slowest path. Which of your modules does it start and end in?

- [ ] I recorded Fmax and slack for my RTL.
- [ ] I can point to the critical path and explain why it is the slowest.

---

## Lab 9 — A design change with a measurable result (4 hours)

**Pipeline the PE** — the change interviewers like most because it has a before/after number.

1. In your `pe.sv`, register the product before adding it (two stages instead of one).
2. The last product now reaches the accumulator one cycle later, so DRAIN needs one more cycle:
   change the DRAIN end condition in your controller.
3. Every prediction moves by one cycle: update `expected_perf()` in `model/golden_model.py` and
   `predict_perf()` in `model/cpp/mm_ref.cpp`, the SystemC CA model, and the drain-length assertion in
   `uvm/tb/mm_sva.sv`; regenerate vectors with `python3 model/vectors.py`.
4. Re-run Lab 7's full check list, then Lab 8's compile.

- [ ] All tests pass with the 2-stage PE.
- [ ] I can state **Fmax before → after** and the cost (+1 cycle latency, +16 bits of registers per PE).

---

## Lab 10 — See it on the board (needs the board)

1. Follow the **hardware runbook** (claude.ai doc) to program the accelerator built from your RTL.
2. Run `python host/host.py --tests 100` — your design, on real hardware.
3. Optional: add a **SignalTap** instance (Tools → Signal Tap Logic Analyzer) on your controller's `state_o`
   and `t`, trigger on `start`, and watch one job run inside the FPGA.

---

## When you finish

- Your branch `my-rtl` holds your own versions of `pe`, `skew_buffer`, `systolic_array`, `sram_sp` and
  `mm_controller`, all passing the project's tests. Keep it; don't merge it unless you want to.
- Write `docs/my_changes.md`: what you designed, what differed from the original, what you changed in
  Lab 9 and the Fmax numbers.
- Push your branch: `git push -u origin my-rtl`.

**Interview line you can now say honestly:** "I designed the processing element, skew buffers, array,
block-RAM wrapper and controller myself, verified them against the project's cocotb, co-simulation and
UVM suites, and measured the timing impact of pipelining the PE in Quartus."
