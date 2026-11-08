# Concept Question Bank: Basics to Advanced

Every concept an interviewer can reach from the resume entry, in nine levels. For each one:

- **Used?** whether the project uses it, and where.
- **What / Why / How:** what it is, why it matters, how our project does it.
- **Questions:** what interviewers ask, with short answers to say out loud.

Status marks:

- ✅ **Yes**: the project uses it directly. You can say "we did this".
- 🔶 **Partly**: used indirectly, only in software, or written but not yet run on the board. Say exactly which part.
- ❌ **No**: not in the project. Know the idea, and say "we didn't do this; here is how it would fit".

Companion files: [RESUME_DEFENSE.md](RESUME_DEFENSE.md) (claim by claim),
[FPGA_FLOW_INTERVIEW.md](FPGA_FLOW_INTERVIEW.md) (the Quartus flow), [../NOTES.md](../NOTES.md) (theory, by section),
[../slides/03_pe_basics/](../slides/03_pe_basics/) (the PE in pictures).

**How to answer any question:** say what it is, then why it matters, then how we did it, then give the number, then name
the limitation. Example: "Skewing delays row i by i cycles (what) so A and B meet in the right PE (why). Our
`skew_buffer.sv` uses a shift register of length n for lane n (how), which is 28 registers per buffer for 8×8
(number). It adds 2N − 2 cycles of fill and drain (limitation)."

---

## The 30 most likely questions

Practise these first. The section number points to the full answer below.

1. Walk me through your project in two minutes. (9.1)
2. What is a systolic array, and why use one for matrix multiplication? (4.1)
3. Draw your PE. Why is the accumulator 32 bits? (4.2, 3.4)
4. What does output-stationary mean? How is it different from weight-stationary, as in the TPU? (4.3)
5. Why do you skew the inputs? How many registers does that cost? (4.4)
6. Derive K + 2N. Where do the extra 2 cycles come from? (4.5)
7. Why 5.12 GOPS and not the 6.4 GOPS peak? (4.6)
8. What is two's complement? What goes wrong if you forget `signed`? (1.1, 2.3)
9. Blocking vs non-blocking assignment: what breaks in a shift register? (2.2)
10. Setup and hold time. How do you fix a setup violation? A hold violation? (1.5)
11. What is your critical path, and what is your Fmax? (1.5, 6.4)
12. Synchronous vs asynchronous reset. Which did you use and why? (1.4)
13. What is metastability, and where in your design do you handle it? (1.8)
14. Explain your controller FSM. Is it Moore or Mealy? (1.6)
15. How does the valid/ready handshake work? (2.7)
16. How did you verify the design? What is a golden model? (7.1, 7.3)
17. What is the int8 overflow trap in NumPy? (7.3)
18. Directed vs constrained-random testing. (7.4)
19. Code coverage vs functional coverage. Is 100% code coverage enough? (7.5)
20. What does co-simulation add if cocotb already passes? (7.6)
21. What are the parts of a UVM testbench? (7.7)
22. Write an SVA assertion for "rvalid one cycle after a read". (7.8)
23. Your design is I/O-bound. What does that mean, and how would you fix it? (5.2)
24. How would you multiply matrices bigger than the array? (4.7)
25. What is quantization, and how does int8 inference work? (3.3)
26. FPGA vs ASIC vs GPU for this workload? (6.2)
27. What are LUTs, DSP blocks and block RAM? How much of each does your design use? (6.1)
28. How would you pipeline the PE for a faster clock? (8.1)
29. What did you personally design, and what did the team build? (9.1)
30. What has not worked yet, or not been done? (9.5)

---

## Level 1: Digital logic and number representation

### 1.1 Binary, two's complement, sign extension, overflow ✅
**Used:** every operand is signed int8, and every accumulator is signed int32. See `rtl/core/pe.sv` and NOTES §1 and §15.

- **What:** two's complement stores negative numbers so that the same adder works for both signs.
  - An 8-bit value ranges from −128 to +127.
  - To negate a number, invert all bits and add 1.
  - The top bit (MSB) is the sign bit.
- **Why:** neural-network weights and activations are signed. A sign mistake gives wrong answers without any error message.
- **How:** in `pe.sv`, the 16-bit product is widened to 32 bits with `AW'(prod)`. Because `prod` is signed, the widening is a **sign extension**: the MSB is copied into the new upper bits. For example, `FFFB` (−5) becomes `FFFF_FFFB`, not `0000_FFFB`.

**Questions**
- *Write −5 in 8 bits.* Start from 5 = `0000_0101`. Invert to get `1111_1010`, then add 1: `1111_1011` (`FB`).
- *What is −(−128) in int8?* It overflows back to −128, because +128 does not fit in 8 bits.
- *How do you detect overflow when adding?* Overflow happens when both inputs have the same sign and the result has the other sign. Equivalently, the carry into the MSB differs from the carry out of it.
- *How many bits does the product of two int8 values need?* 16. The largest magnitude is (−128) × (−128) = 16,384, which needs 15 magnitude bits plus a sign bit.
- *How many bits does the sum of 64 such products need?* 64 × 16,384 = 1,048,576 = 2²⁰, which needs **22 bits** signed. We use 32 bits, which gives headroom: int32 can hold 131,071 worst-case products, and our K is at most 255.

### 1.2 Combinational logic: gates, multiplexers, adders 🔶
**Used:** indirectly. We write `+` and `case`, and the tool builds the adders and multiplexers.
- The accumulator add (`acc + prod`) is a 32-bit adder.
- The register read path (`always_comb case` in `mm_regs.sv`) is a multiplexer.

- **Ripple-carry adder:** the carry passes through every bit in turn, so the delay grows with the width (O(n)). It is small.
- **Carry-lookahead adder:** computes generate (g = a·b) and propagate (p = a⊕b) for each bit, then works out the carries in parallel. The delay is O(log n), but it uses more area.
- **On FPGAs:** each logic element has a hard-wired **carry chain**. This is a very fast ripple, so FPGAs almost never use carry-lookahead in logic.

**Questions**
- *Ripple vs lookahead: which is faster, and why?* Lookahead. It does not wait for the carry to ripple bit by bit.
- *What adder does your 32-bit accumulator use?* Quartus maps `+` onto the MAX 10 carry chain. We did not hand-design an adder.
- *Build a 4:1 multiplexer from 2:1 multiplexers.* Two 2:1 multiplexers select using `sel[0]`, and a third picks between their outputs using `sel[1]`.

### 1.3 Hardware multipliers, Booth encoding, DSP blocks 🔶
**Used:** the multipliers and DSP blocks yes, Booth no.
- `a_in * b_in` maps to the MAX 10's **embedded multipliers**. The 10M50 has 144 18×18 multipliers, and each can be used as two 9×9 multipliers, giving 288.
- A signed int8 × int8 multiply fits in one 9×9.
- Yosys counted 16, 64 and 256 multipliers for N = 4, 8 and 16, which is one per PE.

- **Booth (radix-4):** recodes the multiplier into digits {−2, −1, 0, +1, +2} by looking at overlapping groups of 3 bits. This halves the number of partial products (8 bits gives 4 instead of 8).
  - The partial products are then added by a tree (Wallace or Dadda) and one final adder.
  - ASIC multipliers are built this way. On an FPGA, the hard multiplier already contains this logic.

**Questions**
- *Why use the hard multiplier instead of LUTs?* It is faster, uses less power, and leaves LUTs free for other logic. An 8×8 multiplier built in LUTs takes dozens of logic elements.
- *What limits how large an N fits?* The multiplier count. 16×16 needs 256 of the 288 9×9 multipliers. The logic and Fmax are still unknown until Quartus runs.
- *How does Booth handle signed numbers?* Recoding works directly on two's complement, so no separate sign correction is needed.

### 1.4 Flip-flops vs latches, registers, sync vs async reset ✅
**Used:**
- Every state element is an edge-triggered flip-flop written in `always_ff @(posedge clk)`.
- There are **no latches**. Verilator `-Wall` lint would flag one.
- Reset is **synchronous, active-low**: `if (!rst_n || clear)` sits inside `always_ff`.
- `rst_n` comes from button KEY[0] through a 2-flip-flop synchronizer (`sync_2ff`, in `top_de10lite.sv`).

- **Latch vs flip-flop:** a latch is level-sensitive and passes data through while its enable is high. A flip-flop captures data only on the clock edge. Latches make timing analysis hard, so avoid them in FPGA design.
- **Sync vs async reset:**
  - A **sync** reset acts only on a clock edge. It is clean to time, but needs the clock running.
  - An **async** reset acts immediately. It must still be *released* in sync with the clock ("async assert, sync deassert"). Otherwise flip-flops can come out of reset on different cycles.

**Questions**
- *Why did you choose a synchronous reset?* It is simpler to time, the button is already synchronized, and it shares logic with our `clear` signal (`!rst_n || clear`).
- *Do the block RAMs get reset?* No. Block RAM cannot be reset. Our X-propagation test uses this: before A and B are written, C reads as X, which proves the 4-state check is working.
- *What creates an unwanted latch?* A combinational block that does not assign a signal on every path. See 2.5.

### 1.5 Timing: setup, hold, critical path, Fmax, slack ✅ (concept and constraint) 🔶 (no numbers yet)
**Used:**
- `quartus/top_de10lite.sdc` sets a 20 ns clock (50 MHz) with `create_clock` and `derive_clock_uncertainty`.
- It marks the buttons, switches, LEDs and UART pins as false paths.
- **The real Fmax and slack are unknown until Quartus compiles the design.**

- **Setup:** data must be stable for t_su *before* the clock edge. The rule is
  `T_clk ≥ t_clk→q + t_logic(max) + t_su` (ignoring clock skew).
- **Hold:** data must stay stable for t_h *after* the edge. The rule is
  `t_clk→q + t_logic(min) ≥ t_h`.
- **Critical path:** the slowest register-to-register path. It sets **Fmax = 1 / (delay of the critical path)**.
- **Slack:** the required time minus the arrival time. Positive slack means timing is met.

**Questions**
- *How do you fix a setup violation?* Pipeline (add a register stage), reduce logic depth, use a hard block (DSP), slow the clock, or change the placement.
- *How do you fix a hold violation?* Add delay on the fast path. The tool does this automatically. **A slower clock does not fix hold**, because the hold rule does not include the period.
- *What is your critical path likely to be?* The PE: an 8×8 multiply followed by a 32-bit add, in one cycle. We will confirm this in the Quartus Timing Analyzer.
- *What is a false path, and why are the UART pins false paths?* A false path is one we tell the tool not to time. The UART RX input is asynchronous and goes through a synchronizer, so timing it is meaningless.

### 1.6 Finite state machines: Moore vs Mealy, one-hot ✅
**Used:** `mm_controller.sv` has five states:
`IDLE → CLEAR → COMPUTE (K cycles) → DRAIN (2N − 1 cycles) → DONE → IDLE`.
- It is written as `typedef enum logic [2:0]` (binary) inside a single `always_ff`.
- The outputs (`busy`, `done`, `clear`, `array_en`, `rd_en`) depend **only on the state**, so it is a **Moore** machine.

- **Moore vs Mealy:**
  - In a Moore machine, the outputs depend on the state only. The outputs are glitch-free and change one cycle after the input.
  - In a Mealy machine, the outputs depend on the state *and* the inputs. It reacts faster and needs fewer states, but adds combinational paths from inputs to outputs.
- **Encoding:**
  - Binary encoding uses log₂(states) flip-flops.
  - **One-hot** uses one flip-flop per state. The next-state logic is simpler and faster, and FPGAs have plenty of flip-flops.
  - Quartus may re-encode a state machine it recognizes (often to one-hot). Check its State Machine report after compiling.

**Questions**
- *Why a CLEAR state?* It zeroes all accumulators and pass-through registers before a job, in one cycle.
- *Why is DRAIN 2N − 1 cycles?* The last A and B values must travel 2(N − 1) PEs to reach PE(N−1, N−1), plus 1 cycle of RAM read latency.
- *What happens if `start` arrives while busy?* It is ignored: `start = ctrl_wr && bit0 && !busy` in `mm_regs.sv`.
- *What protects against an illegal state?* The `default: state <= IDLE` branch, and a formal proof that the state is always ≤ DONE.

### 1.7 Pipelining: latency vs throughput, stage balancing ✅
**Used:** the systolic array *is* a 2-D pipeline. Every PE's `a_out`/`b_out` register is a pipeline stage.
- The **latency** of one job is K + 2N cycles.
- Once the array is full, the **throughput** is N² MACs per cycle.

- **Latency** is the time for one result. **Throughput** is results per unit time. Pipelining raises throughput and Fmax, and costs latency (and registers).
- **Stage balancing:** the clock is set by the slowest stage, so split work evenly between stages.

**Questions**
- *Does adding pipeline stages always help?* No. It costs registers and latency, adds fill and drain time (lower utilization for small K), and only helps if the critical path really is in the stage you split.
- *What is the latency and throughput for 8×8, K = 64?* Latency is 80 cycles = 1.6 µs at 50 MHz. The peak throughput is 64 MACs per cycle.

### 1.8 Metastability and clock-domain crossing 🔶
**Used:**
- The design runs on **one clock** (50 MHz), so there is no multi-clock crossing.
- The *asynchronous inputs* (UART RX and the KEY buttons) pass through `sync_2ff.sv`, a 2-flip-flop synchronizer, in `uart_rx.sv` and `top_de10lite.sv`.

- **Metastability:** when an input changes too close to the clock edge, a flip-flop can sit between 0 and 1 for a while. The second flip-flop gives it a full cycle to settle.
- **MTBF** (mean time between failures) grows exponentially with the settling time:
  `MTBF ≈ e^(t_settle/τ) / (T₀ · f_clk · f_data)`.
- **Multi-bit crossings:** never synchronize a bus bit by bit. Use Gray code, a handshake, or an asynchronous FIFO.

**Questions**
- *Why two flip-flops and not one?* The first may go metastable. The second samples a value that has had a whole cycle to settle.
- *Would you synchronize the 8-bit UART data byte the same way?* No. RX is one serial bit, which we synchronize and then sample in the middle of each bit. A parallel bus crossing clocks needs a FIFO or handshake.
- *Where would CDC appear if you added a PLL?* If the array ran faster than the UART logic, the register bus would cross clock domains and need an asynchronous FIFO or handshake.

---

## Level 2: SystemVerilog RTL design

### 2.1 Modules, ports, wire vs reg vs logic ✅
**Used:** all RTL uses `logic`, with ANSI-style port lists.
- `logic` is a 4-state type that works in both `assign` and procedural blocks, as long as there is one driver.
- `wire` is for multiple drivers, such as tri-state or `inout`.
- The name `reg` does **not** mean "register". It only means "assigned procedurally".

**Questions**
- *When must you use `wire` and not `logic`?* For a net with several drivers, such as a bidirectional pin.
- *Does `reg` create a flip-flop?* No. Flip-flops come from clocked always blocks, whatever the type is called.

### 2.2 always_ff vs always_comb, blocking vs non-blocking ✅
**Used:** `always_ff` with `<=` for all registers, and `always_comb` for the register read multiplexer (`mm_regs.sv`) and `hex7seg.sv`.

- **Non-blocking `<=`** evaluates every right-hand side first, then updates all left-hand sides together. This models flip-flops that all switch on the same edge.
- **Blocking `=`** updates immediately, line by line. This models combinational logic.
- `always_ff` and `always_comb` let the tools check your intent: no latches in `always_comb`, and one clock in `always_ff`.

**Questions**
- *What breaks if the skew buffer uses blocking assignments?* With `sr[0] = din; sr[1] = sr[0];`, `sr[1]` gets the *new* `din` in the same cycle. The delay chain collapses to one stage in simulation, and the result can differ between simulation and synthesis.
- *Can you mix `=` and `<=` in one block?* You can, but don't. Rule: `<=` in sequential blocks and `=` in combinational blocks.

### 2.3 Signed arithmetic, $signed, mixed signed/unsigned pitfalls ✅
**Used:** the ports are declared `logic signed [7:0]`, the product is `logic signed [15:0]`, and `AW'(prod)` makes the sign extension explicit. We don't need `$signed()` because everything is declared signed.

The pitfalls interviewers love:
1. **If one operand is unsigned, the whole expression is unsigned.** Signed × unsigned zero-extends the negative number, which gives a wrong product.
2. **Part-selects and concatenations are always unsigned**, even if taken from a signed signal. `x[7:0]` and `{a, b}` lose the sign.
3. A literal like `8'd5` is unsigned. Use `8'sd5` for a signed literal.
4. `>>` is a logical shift (fills with 0). `>>>` is an arithmetic shift (copies the sign bit, for signed values only).
5. Widths are worked out from the context *before* the operation. Operands are extended to the result width first, so declare the result wide enough.

**Questions**
- *255 × 255 vs (−1) × (−1)?* The bit pattern is the same (`FF × FF`). Unsigned gives 65,025; signed gives 1. This is slide 7 of the PE deck.
- *What does `$signed(x)` do?* It reinterprets the same bits as signed. It does not change any bits.
- *Why the cast `AW'(prod)`?* It makes the sign extension to 32 bits explicit and stops Verilator from giving a `WIDTH` warning.

### 2.4 Parameters and generate loops for the PE grid ✅
**Used:**
- `systolic_array.sv` builds the grid with nested `for (genvar i …) g_row / for (genvar j …) g_col`.
- `skew_buffer.sv` builds lane n with n registers (`g_lane`).
- `mm_core.sv` builds one RAM bank per row and column (`g_bank`).
- N, K_MAX, DW and AW are all parameters.

**Questions**
- *How is a PE named in the hierarchy?* `g_row[i].g_col[j].<instance>`. That name is how you find it in waveforms.
- *Parameter vs localparam?* A parameter can be overridden per instance. A localparam is derived inside the module and cannot be overridden.
- *How do you stop illegal parameter values?* We check them in `mm_regs.sv` with `$fatal`: N and K_MAX must be powers of 2, and they must fit the 4 KB windows and the 8-bit INFO field.

### 2.5 Latch inference and default assignments ✅
**Used:** the read multiplexer's `always_comb` assigns a default, so no latch can form. The `-Wall` lint in `tools/lint.sh` is clean.

- **The rule:** in combinational logic, every output must be assigned on every path. Otherwise the tool has to "remember" the old value, which makes a latch.
- **The fix:** put default assignments at the top of the block, or add a full `case` with a `default` branch.

**Questions**
- *Show code that infers a latch.* `always_comb if (en) y = a;` with no `else`.
- *How do you find latches?* Lint (Verilator `LATCH`), synthesis warnings, or the Quartus report "Inferred latch".

### 2.6 Synthesizable vs simulation-only code ✅
**Used:**
- The parameter `$fatal` checks sit inside `// synthesis translate_off … translate_on` (`mm_regs.sv`), so they exist only in simulation.
- Testbenches use simulation-only constructs: `#` delays, `$display`, classes, DPI and file I/O.

**Questions**
- *Name things that don't synthesize.* `#` delays, `$display`, `fork/join`, dynamic arrays and classes, file I/O, and `initial` blocks for ASIC. On FPGAs, initial values in registers and RAM are allowed.
- *What is a sim/synth mismatch?* When the RTL simulates one way but the netlist behaves another way. See 7.9.

### 2.7 Handshakes: start/done and valid/ready ✅
**Used:**
- **Valid/ready register bus** (`mm_regs.sv`):
  - A transfer happens on an edge where `bus_valid && bus_ready`.
  - Read data arrives with `bus_rvalid` exactly 1 cycle later.
  - `bus_ready` is low for at most one cycle.
- **Start/done:**
  - `start` is a 1-cycle pulse, made from a write to CTRL bit 0.
  - `done` is a 1-cycle pulse from the controller.
  - A **sticky** `done_flag` in STATUS holds it so the host can poll.

**Questions**
- *What is the valid/ready rule?* The source raises `valid` and holds the data and `valid` until `ready`. Our SVA `a_master_holds` checks this. `valid` must not wait for `ready`, or the two sides can deadlock.
- *Why a sticky done flag?* `done` lasts one 20 ns cycle. The host, polling over UART, would miss it.
- *Pulse vs level signals?* A pulse is an event ("start now"). A level is a state ("busy"). Converting between them needs an edge detector or a sticky flag.

---

## Level 3: Matrix multiplication and arithmetic for ML

### 3.1 GEMM and the MAC; counting operations (2·M·N·K) ✅
**Used:**
- GOPS counts 2 operations per MAC (one multiply, one add).
- One job is (N × K) × (K × N), which is N²·K MACs. The `PERF_MACS` register counts them.

- **GEMM:** C = A·B, where A is M×K and B is K×N. That is M·N·K MACs, or **2·M·N·K operations**.
- **Our 8×8 job, K = 64:** 64 × 64 = 4,096 MACs = 8,192 operations.

**Questions**
- *How many MACs to multiply two 64×64 matrices?* 64³ = 262,144 MACs, which is 524,288 operations.
- *Why count 2 per MAC?* That is the industry convention (OPS/FLOPS count the multiply and the add separately).

### 3.2 Why GEMM dominates deep learning (im2col, attention) 🔶
**Used:** background only (NOTES §12). The project multiplies raw int8 matrices, not network layers.
- **Fully-connected layers** are a GEMM: weights × activations.
- **Convolutions** become a GEMM through **im2col**: each input patch is unrolled into a column, and the filters are unrolled into rows.
- **Transformers:** the Q/K/V projections, Q·Kᵀ, attention·V and the MLP layers are all GEMMs.
- So most of the arithmetic in a network is GEMM. Speeding up GEMM speeds up the network.

**Questions**
- *What does im2col cost?* Memory. Overlapping patches are copied many times. Accelerators often do the unrolling on the fly instead.
- *How would your array run a convolution?* Run im2col on the host, then tile the resulting GEMM onto the array (4.7).

### 3.3 Quantization: scale, zero-point, per-channel ❌
**Used:** no. Our inputs are already int8 numbers. This is the bridge to the MNIST step of the roadmap (NOTES §15).

- **Formula:** real value = scale × (q − zero_point).
  - **Symmetric** quantization uses zero_point = 0. It is usual for weights.
  - **Asymmetric** quantization uses a zero_point ≠ 0. It is common for activations after ReLU, which are never negative.
- **Per-tensor** quantization uses one scale for the whole tensor. **Per-channel** uses one scale per output channel of the weights, which gives better accuracy.

**Questions**
- *Can your hardware run quantized networks?* Yes, for symmetric int8. The array computes the int32 Σ qa·qw, and requantization (3.5) happens afterwards.
- *What about non-zero zero-points?* Expand the sum:
  Σ(qa − Za)(qw − Zw) = Σqa·qw − Zw·Σqa − Za·Σqw + K·Za·Zw.
  The correction terms can be computed separately.
  Alternatively, subtract the zero-point *before* the multiply. The result is a 9-bit value, which the MAX 10's 9×9 multipliers can handle.
- *Why int8 at all?* It uses about 4× less memory than fp32, and its multipliers are much cheaper. The accuracy loss is small for inference.

### 3.4 Accumulator bit growth (why int32) ✅
**Used:** int8 × int8 gives an int16 product, accumulated in **int32**. NOTES §15 and `pe.sv`.
- A sum of K products needs 16 + ⌈log₂K⌉ bits in the worst case. For K = 64 that is 22 bits (1.1).
- int32 is the standard width (TPU, ARM and x86 int8 instructions all use it), and it can never overflow for our K ≤ 255.

**Questions**
- *Why not accumulate in 16 bits?* A single (−128)² product is already 16,384. Adding even a few of them overflows 16 bits.
- *What if K were huge?* Accumulate in 64 bits, or split K and add the partial sums wider, as the host tiling does with int32 sums.

### 3.5 Requantization: int32 back to int8, saturation ❌
**Used:** no. We return raw int32 C values to the host. The only saturating logic is the `PERF_IDLE` counter (it stops at its maximum instead of wrapping).

- **What:** q_out = clamp(round(M · acc) + Z_out, −128, 127), where M = (S_a · S_w) / S_out.
  - In hardware, M becomes an integer multiply followed by a right shift (fixed point).
- **Saturation vs wrap-around:** saturation clamps at the limit, which is a small error. Wrap-around turns a large positive into a large negative, which is a disaster for a network.

**Questions**
- *Where would you add requantization?* As a stage after the array, at the output: multiply, shift, round, clamp. Then C goes back as int8, which cuts the readout data by 4×.
- *Why do our accumulators wrap and not saturate?* They can never overflow for K ≤ 255, so the wrap path never runs. The golden model wraps the same way (`matmul_int32`).

### 3.6 Tiling (blocking) ✅ (host software)
**Used:**
- `host/host.py --tile M K P` multiplies any (M×K) by (K×P) on the N×N array.
  - C is split into N×N tiles.
  - K is split into chunks of at most K_MAX.
  - Partial tiles are padded with zeros.
  - The int32 partial sums are added on the host.
- The loop order is **j → k → i**, so one B tile stays loaded while A tiles stream past.
- **Tested against the software fake board only**, not yet on hardware.

**Questions**
- *How many jobs is 64×64 by 64×64 on an 8×8 array with K_MAX = 64?* 8 × 8 = 64 output tiles, with K in 1 chunk, so **64 jobs**.
  - Compute time: 64 × 80 cycles × 20 ns ≈ 102 µs.
- *How much data goes over UART for that?* At least 53 KB, about **4.6 s** at 11,520 bytes/s:
  - B: 8 tiles × 512 B.
  - A: 64 tiles × 512 B.
  - C: 64 tiles × 256 B.
  That is the I/O bound again (5.2).
- *Why the j → k → i loop order?* It reuses the B tile already in RAM, so B is loaded 8 times instead of 64.

### 3.7 Data reuse and arithmetic intensity 🔶
**Used:** the reuse is built into the array, but we did not report an arithmetic-intensity number. Here it is.

- **Reuse:** each A value is used by the N PEs in its row, and each B value by the N PEs in its column. One RAM read feeds N MACs, so memory traffic per MAC falls by a factor of N.
- **Arithmetic intensity** = operations ÷ bytes moved. For one 8×8 job with K = 64:
  - Bytes in: A + B = 2·N·K = 1,024. Bytes out: C = 4·N² = 256.
  - Operations: 8,192.
  - AI = 8,192 / 1,280 ≈ **6.4 operations per byte**.

**Questions**
- *Why does reuse matter?* Moving data costs far more energy and time than computing on it. Reuse means the array needs only 2N bytes per cycle for N² MACs.
- *How does arithmetic intensity change with N?* It grows with N: about N/2 operations per byte when K is large (counting only A and B). Bigger arrays reuse more.

---

## Level 4: Systolic arrays (the core of the project)

### 4.1 What a systolic array is and why it exists (Kung, 1978/1982) ✅
**Used:** this is the project. NOTES §13 and slide decks 01 and 03.
- **What:** a grid of identical PEs. Each PE does a MAC and passes data **only to its neighbours**, in step with the clock, like a heartbeat pumping blood (hence "systolic").
- **History:** H. T. Kung and C. Leiserson (1978). Kung's paper "Why Systolic Architectures?" (IEEE Computer, 1982).
- **Why:**
  - Only local wires, so short connections and a high clock.
  - N² MACs per cycle.
  - High data reuse.
  - One PE design copied many times, so it is easy to build and verify.

**Questions**
- *Why not just use N² independent multipliers with a big bus?* Feeding each one separately needs N² operands per cycle from memory. The systolic array needs only 2N, because operands flow from PE to PE.
- *What is the downside?* Fill and drain time, a fixed dataflow, and poor efficiency for irregular or small problems.

### 4.2 PE design: MAC plus forwarding registers ✅
**Used:** `rtl/core/pe.sv`. Deck 03 draws it step by step.
- Each enabled cycle, the PE does three things:
  1. Multiplies `a_in × b_in` (int8 × int8 → int16).
  2. Adds the product into `acc` (int32).
  3. Passes `a` to the right and `b` down, through registers.
- `clear` or reset zeroes all three registers. When `en` = 0, all registers hold their values.
- **Cost:** 8 + 8 + 32 = **48 flip-flops** per PE. An 8×8 array has 64 PEs, so **3,072 flip-flops**, plus one multiplier per PE.

**Questions**
- *Why register a_out and b_out instead of passing a_in straight through?* Without the registers, a value would travel across the whole row in one cycle. That makes a long combinational path, and the timing (and the systolic idea) would break.
- *What does `en` do?* It freezes the PE. On an FPGA it becomes the flip-flops' clock-enable input.
- *Whiteboard it:* draw two inputs → multiplier → adder with feedback → acc, plus two pass-through registers. Label the widths 8, 16, 32.

### 4.3 Dataflows: output-, weight-, input-, row-stationary 🔶
**Used:** **output-stationary** ✅. The others ❌ are for comparison only (NOTES §13).
- **Output-stationary (OS, ours):**
  - Each PE keeps its own C[i][j]. A flows right, B flows down.
  - 32-bit partial sums never move.
  - Results are read out at the end.
- **Weight-stationary (WS, Google TPU):**
  - Weights are preloaded and stay in place. Activations flow across, and partial sums flow down.
  - Best when the same weights are used for many inputs (large batches, convolution).
- **Input-stationary (IS):** inputs stay; weights and partial sums move.
- **Row-stationary (MIT Eyeriss):** maps rows of filters and inputs onto PEs to maximize reuse of all three operands, saving energy for convolution.

**Questions**
- *Why did you choose OS?*
  - It is the simplest to verify, because each PE owns one output.
  - No partial-sum traffic.
  - Good when K is large compared with N.
- *When is WS better?* When weights are reused across many inputs, as in neural-network inference with batches. The TPU v1 chose it.
- *What does OS cost?* All N² accumulators must be read out at the end, and the next job cannot overlap without extra logic (4.8).

### 4.4 Input skewing and skew buffers ✅
**Used:** `rtl/core/skew_buffer.sv`. Lane n is a shift register n stages long. Lane 0 passes straight through.
- **Why:** A[i][k] must meet B[k][j] in PE(i,j) at the same cycle. A takes j steps to reach column j, and B takes i steps to reach row i. Delaying row i of A by i cycles and column j of B by j cycles lines them up into a diagonal "wavefront".
- **Meeting time in our RTL:** step **k + 1 + i + j**. The +1 is the RAM read latency.
- **Cost:** 0 + 1 + … + (N − 1) = **N(N − 1)/2 registers per buffer**. For N = 8 that is 28 per buffer, or 56 for the A and B buffers together.

**Questions**
- *What if you forget the skew?* Wrong products. PE(i,j) multiplies A[i][k] with B[k′][j] for the wrong k′. The test fails at once for N ≥ 2.
- *Can you avoid skew buffers?* Yes, by storing the data pre-skewed in memory (with padding) or by skewing the read addresses. That trades registers for memory or logic.

### 4.5 Latency derivation: fill, compute, drain (K + 2N) ✅
**Used:** `PERF_TOTAL = K + 2N`, measured in RTL, co-sim and SystemC with **0 cycles of error**.
- **Ideal array:** the last MAC (PE(N−1, N−1), k = K − 1) happens at step (K − 1) + 2(N − 1). That gives **K + 2N − 2** cycles of activity, which is the textbook number in NOTES §13.
- **Our RTL:** the controller adds +1 cycle for CLEAR and +1 cycle of RAM read latency.
  - Total = 1 (CLEAR) + K (COMPUTE) + (2N − 1) (DRAIN) = **K + 2N**.
- **Example:** 8×8 with K = 64 gives 80 cycles = 1.6 µs at 50 MHz.

**Questions**
- *Your notes say K + 2N − 2. Why does the RTL give K + 2N?* The extra 2 cycles are CLEAR and RAM latency. The original plan estimated 78 and the RTL read 80; we documented why (verification report, issue 9).
- *How did you verify the formula?* We checked it against a separate SystemC cycle-approximate model and against the RTL's own counters, over 5 configurations × 1,000 jobs, and found 0 mismatches. The FPGA measurement is still pending.

### 4.6 Utilization and peak GOPS: why 5.12 of 6.4 ✅
**Used:** these are the numbers in `docs/results/phase5_models.md`.
- **Peak** for 8×8 at 50 MHz: 2 × 64 × 50 M = **6.4 GOPS**.
- **Achieved:** 8,192 operations ÷ (80 cycles × 20 ns) = **5.12 GOPS**.
  - 5.12 / 6.4 = 80% = K / (K + 2N).
- **PE utilization** (as the counters define it) = MACS ÷ (N² × COMPUTE cycles) = K / (K + 2N − 1):
  - 8×8 at K = 64: 64/79 = **81.0%**.
  - 4×4 at K = 64: 64/71 = **90.1%**.
- **Why below peak:** fill and drain. All N² PEs are busy together for only K − 2N + 2 steps (50 of 79 for 8×8). The rest is the diagonal wavefront filling and emptying.

**Questions**
- *How do you raise utilization?* Use a larger K (64 → 128 lifts 8×8 from 81% to about 89%). Or overlap jobs so that one job's drain hides the next one's fill (4.8).
- *Why is 4×4 more efficient than 8×8?* Its fill and drain are shorter (2N − 1 = 7 vs 15 cycles). Its *throughput* is still lower: 1.42 vs 5.12 GOPS.
- *Is 5.12 GOPS real?* It is simulated at an assumed 50 MHz. The board's Fmax and timing have not been measured yet.

### 4.7 Tiling large matrices on a fixed-size array ✅ (host software)
Covered in 3.6. **Key line:** "Any matrix size runs on the N×N array by splitting C into N×N tiles and K into chunks, then adding the int32 partial sums."

### 4.8 Overlapping tiles and double buffering ❌
**Used:** no. The README lists it as a stretch goal: over UART there is no benefit, because loading takes about 89 ms and computing about 1.6 µs.
- **Double (ping-pong) buffering:** two copies of the A and B RAMs. The array computes from one while the host fills the other, so loading overlaps compute.
- **Overlapping jobs in OS:** shift the finished C values out (or copy them to shadow registers) while the next job starts filling. This hides the 2N − 1 drain cycles.

**Questions**
- *Why didn't you build double buffering?* The UART link is about 50,000× slower than the compute. Overlap would save 1.6 µs out of 89 ms. Fix the link first.
- *What would it cost?* Twice the A/B RAM (M9K blocks) and a bank-select bit in the controller.

### 4.9 Systolic arrays in industry: TPU, tensor cores, NPUs 🔶
**Used:** background only.
- **Google TPU v1 (2017):** a 256×256 int8 weight-stationary array, 65,536 MACs at 700 MHz, about 92 TOPS. It is the same idea as ours, about 1,000× bigger.
- **NVIDIA tensor cores:** small matrix-multiply units inside each GPU SM, fed from registers by warp-level MMA instructions.
- **NPUs:** in phones and laptops (Apple Neural Engine, Qualcomm Hexagon).
- **Intel AMX:** a tile-matrix unit inside Xeon CPUs.
- **Renesas:** the RZ/V microprocessors include the **DRP-AI** accelerator, built around arrays of MAC units. Read its public overview before the Renesas interview.

---

## Level 5: Memory and system integration

### 5.1 On-chip vs off-chip memory, scratchpads ✅ (on-chip) ❌ (off-chip)
**Used:**
- A and B live in **on-chip block RAM**: `sram_sp.sv`, inferred as M9K.
- There are **N banks for A and N banks for B**, so 2N RAMs (16 for 8×8).
- They are **scratchpads**: the host writes explicit addresses (A at 0x1000, B at 0x2000). There is no cache.
- The DE10-Lite's 64 MB SDRAM is not used.

**Questions**
- *Why N banks?* Every cycle the array needs N A values and N B values at once. A single-port RAM gives one word per cycle, so N banks give N words.
- *Scratchpad vs cache?* A scratchpad is managed by software: it has fixed timing and no tags or misses. Accelerators prefer it because their access pattern is known in advance.
- *What is the read latency of block RAM, and how did you handle it?* 1 cycle, because the address is registered. That is the +1 in K + 2N and in the meeting step k + 1 + i + j.

### 5.2 Bandwidth demand and the roofline model 🔶
**Used:** we measured that the design is **I/O-bound** (NOTES §16). We did not plot a roofline. Here are the numbers.
- **Roofline:** attainable performance = min(peak compute, bandwidth × arithmetic intensity).
- **Our case:**
  - UART at 115,200 baud moves about 11,520 bytes/s. AI ≈ 6.4 operations/byte (3.7).
  - The UART "roof" is 11,520 × 6.4 ≈ 74,000 operations/s, against a 6.4 GOPS compute peak.
  - That is roughly 50,000–90,000× below peak. The design is deeply I/O-bound.
- **On-chip, it is balanced:** the banks supply 2N = 16 bytes per cycle (800 MB/s at 50 MHz), which is exactly what the array uses.

**Questions**
- *How would you fix the I/O bound?* Use a faster link (JTAG UART is not much faster; better are SDRAM with on-chip DMA, PCIe or Ethernet). Keep data on-chip across tiles (reuse). Requantize C to int8 to cut readout by 4×. Then add double buffering.
- *What is the ridge point?* Peak ÷ bandwidth: the arithmetic intensity at which you stop being bandwidth-bound. For UART it is about 555,000 operations/byte, which is unreachable.

### 5.3 Ping-pong (double) buffering ❌
See 4.8.

### 5.4 Bus interfaces (Avalon, AXI) and DMA ❌
**Used:** no. We use our own **valid/ready register bus**, with a UART-to-bus bridge (`uart_bus_bridge.sv`).
- **AXI4-Lite** is the industry version of our register bus.
- **AXI4-Stream** would carry A and B data.
- **Avalon-MM** is Intel's equivalent, connected through Platform Designer.
- **DMA:** a block that copies data from memory to the accelerator without the CPU moving each word.

**Questions**
- *How close is your bus to AXI-Lite?* The same valid/ready idea. AXI splits addresses, data and responses into 5 separate channels (AW, W, B, AR, R).
- *How would you connect your core to a Nios II or RISC-V processor?* Wrap `mm_core` as an Avalon-MM slave in Platform Designer, then have the processor write the registers and poll STATUS. That is the next project on the roadmap.

### 5.5 Host–accelerator interaction: registers, polling, interrupts ✅ (registers, polling) ❌ (interrupts)
**Used:** the register map is in `mm_regs.sv`:
- CTRL (start, soft reset), STATUS (busy, done), CFG_K, INFO (N, K_MAX, version), the 5 performance counters, and the A, B and C windows.
- `host.py` writes A, B and K, sets START, **polls** STATUS until DONE, then reads C and the counters.
- There is no interrupt line.

**Questions**
- *Polling vs interrupts?* Polling is simple but wastes host time. An interrupt lets the CPU do other work, but needs an interrupt controller and a handler.
- *What does soft reset do?* It returns the controller to IDLE without a power cycle. Our formal proof and SVA include it, and a real bug was found here (7.8).

---

## Level 6: FPGA fundamentals and toolflow

### 6.1 FPGA architecture: LUTs, flip-flops, DSP, block RAM ✅
**Used:** the MAX 10 10M50 has:
- **49,760 logic elements.** Each has a 4-input LUT, a flip-flop and a carry chain.
- **182 M9K blocks** of block RAM (9 Kbit each).
- **144 18×18 multipliers** (288 9×9).

**What 8×8 needs (from Yosys and hand counts):** 64 multipliers, 16 RAMs, about 3,072 PE flip-flops plus 448 skew flip-flops, plus control logic. The real numbers will come from the Quartus Fitter report.

**Questions**
- *What is a LUT?* A small memory that holds the truth table of any 4-input function.
- *Where does each part of your design map?* Multiply → hard multiplier. Accumulators and pass-through registers → flip-flops. A and B storage → M9K. Control, adders and multiplexers → LUTs and carry chains.

### 6.2 FPGA vs ASIC vs CPU vs GPU 🔶
**Used:** background (NOTES §2).
- **CPU:** flexible, runs instructions one after another, low parallelism.
- **GPU:** thousands of SIMT threads. High throughput and programmable.
- **FPGA:** custom circuits that can be reconfigured.
  - Clock in the 100–500 MHz range.
  - Low latency, no chip-making cost (NRE).
  - Good for prototypes and small volumes.
- **ASIC:** fastest and most efficient, but costs a lot to make and cannot be changed.

**Questions**
- *Why prototype an accelerator on an FPGA?* It is real hardware at real speed, it can be changed in minutes, and the same RTL can later go to an ASIC flow.

### 6.3 Design flow: synthesis, place and route, timing, bitstream 🔶 (scripted, not yet run)
**Used:**
- `tools/build.sh` and `tools/gen_quartus.py` script the Quartus flow.
- The Yosys pre-estimate has run.
- **Quartus itself has not run yet.** See [FPGA_FLOW_INTERVIEW.md](FPGA_FLOW_INTERVIEW.md).
- The Quartus flow is: Analysis & Synthesis → Fitter (place and route) → Assembler (`.sof`) → Timing Analyzer → Programmer (over USB-Blaster).

**Questions**
- *`.sof` vs `.pof`?* A `.sof` configures the FPGA's SRAM and is lost at power-off. A `.pof` goes into the MAX 10's internal flash and survives power-off.

### 6.4 Timing constraints (SDC) and reading Quartus reports 🔶
**Used:** the SDC is written (shown in 1.5). The reports are pending. When reading them:
- **Fitter:** logic elements, registers, M9K, multipliers, as % used.
- **Timing Analyzer:** setup and hold slack on `clk50`, Fmax, and the worst path.

**Questions**
- *What is in your SDC?*
  - `create_clock -period 20.000` on the 50 MHz pin.
  - `derive_clock_uncertainty`.
  - False paths on the asynchronous inputs and the LED/HEX/UART outputs.

### 6.5 Clocks and PLLs 🔶
**Used:** one 50 MHz clock straight from the board pin. **No PLL.** A PLL for a faster clock is a stretch goal that is not done yet.
- **PLL:** makes other frequencies and phases from the input clock (for example 50 → 100 MHz).

**Questions**
- *What would change if you ran at 100 MHz?* The UART baud divider (`tick_gen` parameter). Timing must still close, which probably needs a pipelined PE (8.1).

### 6.6 On-chip debugging with SignalTap ❌ (planned)
**Used:** not yet. It is planned in the hardware runbook and Lab 10.
- **SignalTap:** a logic analyzer built *inside* the FPGA. It stores samples in M9K blocks, triggers on a condition, and reads the samples out over JTAG.

**Questions**
- *What would you probe first?* `state`, `start`, `done`, `bus_valid`/`bus_ready`, and one PE's `acc`, triggered on `start`.

---

## Level 7: Verification

### 7.1 Fundamentals: DUT, golden model, self-checking testbench ✅
**Used:**
- The DUT (design under test) is each RTL block and `mm_core`.
- The golden model is `model/golden_model.py` (NumPy).
- Every cocotb test **checks itself**: it compares the DUT against the model and fails on a mismatch. No one reads waveforms to decide pass or fail.

**Questions**
- *Why a self-checking testbench?* Thousands of random tests cannot be checked by eye.
- *What if the golden model is wrong?* We cross-checked independent models (NumPy, a bit-accurate C++ model, SystemC) against each other over 3 × 1,000 vectors.

### 7.2 cocotb ✅
**Used:** `tb/`: 37 tests (+1 slow one), run on Icarus by default or with `SIM=verilator`.
- Python coroutines drive and sample the DUT (`await RisingEdge(dut.clk)`).
- Tests cover the PE, skew buffer, array, bridge, UART, FIFO, `mm_core` and the full top level.

**Questions**
- *Why cocotb instead of a SystemVerilog testbench?* You get Python and NumPy for the reference and randomness, it is fast to write, and it runs on free simulators.
- *Its limits?* Slower than compiled SystemVerilog, and no native constrained-random or covergroups (UVM covers those).

### 7.3 NumPy golden model and the int8 overflow trap ✅
**Used:** `matmul_int32` in `model/golden_model.py` converts to **int64** before the `@`, then wraps to int32 exactly as the RTL does.
- **The trap:** `np.int8 @ np.int8` returns int8 and **wraps without warning**. A golden model with this bug produces wrong expected values.

**Questions**
- *How did you avoid it?* Convert inputs to a wide type before the multiply, then apply the hardware's wrap rule explicitly.

### 7.4 Directed vs constrained-random testing ✅
**Used:**
- **Directed:** the named edge cases in `golden_model.edge_cases()`: zeros, all −128 (the largest positive sum), all 127, −128 × 127 (the largest negative sum), and the identity matrix. UVM also has 6 directed tests.
- **Random:** cocotb random jobs, plus the UVM `mm_random_test` and `mm_all_test` with constraints, × 10 seeds per configuration.

**Questions**
- *Why both?* Directed tests hit the corners you know about. Random tests find the ones you didn't think of. Coverage tells you when random has done enough.
- *Which edge case matters most for the sign logic?* All −128: every product is +16,384, which is the largest sum.

### 7.5 Code and functional coverage ✅
**Used:**
- **Code coverage** (Verilator): line 96.9%, branch 100%, toggle 90.7%. All are 100% after 2 structural waivers:
  - The controller's `default:` branch, which is unreachable.
  - The upper bits of the 32-bit performance counters.
- **Functional coverage:** 55 bins, all hit (100%):
  - K ranges, including the 2N − 1 fill/drain boundary.
  - Operand patterns.
  - Corner values −128, 0 and 127.
  - Crosses of these.
- **Coverage found real gaps:**
  - Address bits 10–11 of the buffer windows were never driven.
  - `a_row`/`b_row` were wider than needed.

**Questions**
- *Is 100% code coverage enough?* No. It shows that lines *ran*, not that results were *checked*, and it cannot see missing features. Functional coverage and checkers fill that gap.
- *Why waive toggle coverage on the counter's upper bits?* Flipping bit 31 needs about 2³¹ cycles, and a job lasts at most K_MAX + 2N.

### 7.6 Verilator and C++/SystemC co-simulation ✅
**Used:**
- `cosim/`: Verilator `--sc` turns the RTL into a SystemC module.
- It runs next to the SystemC cycle-approximate model on the same jobs.
- For each job it compares C, every counter, and the START → DONE cycles at the pins.
- **5 configurations × 1,000 jobs, 0 mismatches, 0 cycles of error.**

**Questions**
- *What does co-simulation add over cocotb?* An *independent* timing model. When we injected a bug (changing the "all PEs active" bound by one), C stayed correct, cocotb passed, and **only the co-sim counters caught it**.
- *Why SystemC?* It is the industry language for performance models and virtual platforms (TLM-2.0), which is the Renesas role's own area.

### 7.7 UVM basics ✅ (on Verilator)
**Used:** `uvm/`. It runs the Accellera UVM library on Verilator: **104/104 simulations, 13,828 jobs, 1.89 M scoreboard checks**.
- **Parts:** test → env → agent (driver, monitor, sequencer) + scoreboard + coverage collector. Sequences create transactions (sequence items).
- **Phases:** build → connect → run → report. The factory and `config_db` configure the components.
- **Ours:**
  - A bus agent.
  - A scoreboard that calls the C++ model through **DPI-C**.
  - SVA bound to the DUT.
  - An explicit-bin coverage collector, because Verilator 5.052 does not implement covergroup coverpoints.

**Questions**
- *Why UVM when cocotb works?* Reuse, standard structure, constrained-random and coverage. It is what verification teams use day to day.
- *What is DPI-C?* A way to call C or C++ functions directly from SystemVerilog. We use it to get expected results from the C++ model.
- *What is the limit of UVM on Verilator?* No native covergroups, and limited `dist` constraints. A commercial simulator (Questa/VCS/Xcelium) has not been tried yet.

### 7.8 Assertions (SVA) ✅
**Used:**
- **Simulation SVA:** `uvm/tb/mm_sva.sv`, with checks such as `rd_accept |=> bus_rvalid`, `done |=> !done`, `state == DONE |=> state == IDLE`.
- **Formal:** the same properties, proven by **k-induction** in SymbiYosys for any bus input (`formal/`).
- **Real issue found:** two SVAs fired on a *legal* soft reset during DRAIN. The fix was `disable iff (!rst_n || soft_reset)`.

**Questions**
- *`|->` vs `|=>`?* `|->` checks the consequent in the same cycle. `|=>` checks it in the next cycle.
- *Immediate vs concurrent assertions?* Immediate assertions check once, at that point in procedural code. Concurrent assertions check sequences across clock cycles.
- *Simulation SVA vs formal proof?* Simulation checks only the inputs you drove. A formal proof covers *all* inputs. Cover statements show the proof isn't vacuous, i.e. not passing only because the checked states can never be reached.

### 7.9 Simulation vs synthesis mismatch, X-propagation ✅ (X checks) 🔶 (no gate-level simulation)
**Used:**
- X checks run in the **4-state** Icarus tests. Verilator is 2-state, so it can't see X.
- The control outputs must never be X, even while running on unwritten RAM, whose C value *is* X.
- **No gate-level simulation yet**: it needs the Quartus netlist.

- **Causes of mismatch:**
  - Incomplete sensitivity lists (the old `always @(a)` style).
  - Blocking assignments in sequential logic.
  - `initial` values that the target ignores.
  - X-optimism in `if`/`case`.
  - `translate_off` code.
  - Delays.
  - `casex`/`casez`.
- **X-optimism:** `if (x)` takes the else branch in simulation, while real hardware may go either way. This hides bugs.

**Questions**
- *Why run both Icarus and Verilator?* Icarus is 4-state, so it catches reset and X bugs. Verilator is fast and has strict lint.
- *How would you catch a mismatch for certain?* Gate-level simulation of the post-synthesis netlist, or equivalence checking.

---

## Level 8: Advanced optimization and architecture

### 8.1 Pipelining the MAC and retiming ❌ (exercise only: Lab 9)
**Used:** not in the project RTL. The RTL lab's Lab 9 asks you to build it.
- **2-stage PE:** cycle 1 does `prod_r <= a*b`; cycle 2 does `acc <= acc + prod_r`.
  - The critical path shrinks from multiply + add to the longer of the two. Fmax goes up.
  - The latency grows by 1 cycle, so DRAIN grows too. All counters and models need updating.
  - The MAX 10 multiplier has optional internal input and output registers, so Quartus can absorb `prod_r` into the multiplier block.
- **Retiming:** moving registers across logic without changing what the circuit does, to balance the stages. Quartus can do it as a physical-synthesis option.

**Questions**
- *Which part of the K + 2N formula changes?* The fixed overhead: it becomes K + 2N + 1. Utilization drops slightly. GOPS rises if Fmax rises enough.

### 8.2 Power: dynamic power, clock gating 🔶
**Used:** only the `en` clock enable. No power analysis yet.
- **Dynamic power:** P = α·C·V²·f, where α is the switching activity. Static (leakage) power exists even when idle.
- **Clock gating:** stops the clock to idle logic. On FPGAs, use **clock enables** instead (every flip-flop has one), because gated clocks cause skew and glitches. ASICs use clock-gating cells.

**Questions**
- *How would you estimate power?* Feed the simulation's switching activity (a VCD file) into the Quartus Power Analyzer.
- *Cheap power wins for this design?* Gate the operands when `en` = 0 or an operand is zero (stops toggling). Turn off unused PEs for small jobs.

### 8.3 Sparsity and zero-skipping ❌
- **What:** skip work when an operand is zero.
  - **Zero-gating** saves power, not cycles.
  - **Structured sparsity** (NVIDIA's 2:4 pattern, from Ampere) actually doubles throughput.
- **Why hard for systolic arrays:** every PE moves in lockstep, so skipping one PE's work does not save a cycle unless the data is compressed first.

### 8.4 Precision choices: int4, int8, FP8, bf16 ❌
**Used:** int8 only. `DW` is a parameter, so an int4 PE is a parameter change; the register map (one int8 per byte address) would also need updating.
- **int4:** twice the multipliers per area and half the memory. Popular for LLM weights.
- **FP8:** formats E4M3 and E5M2, for training and inference on newer GPUs.
- **bf16:** the same 8-bit exponent (range) as fp32, with a 7-bit mantissa. The standard for training.
- **Hardware cost:** multiplier area grows roughly with the square of the mantissa width. Floating point also needs alignment and normalization logic, so the PE gets much bigger.

### 8.5 Performance modeling with SCALE-Sim ❌
**Used:** no. We built **our own** analytical model (K + 2N) and a SystemC cycle-approximate model, which match the RTL **exactly** (0% error).
- **SCALE-Sim** (Georgia Tech/ARM): give it an array size, a dataflow (OS/WS/IS), SRAM sizes and a network layer list. It reports cycles, utilization and memory traffic for whole DNN layers.

**Questions**
- *Why your own model instead?* We needed a model that matches our RTL exactly, including CLEAR and RAM latency, to correlate against the counters. SCALE-Sim is for exploring designs before RTL exists.
- *Next step:* run SCALE-Sim with an 8×8 OS configuration and compare its per-tile cycles with K + 2N.

### 8.6 Scaling out: multiple arrays on a NoC ❌ (link to your thesis)
- **What:** several N×N arrays as tiles on a network-on-chip (NoC). Each array computes some output tiles of C.
  - **Splitting C across arrays** needs no communication between them.
  - **Splitting K across arrays** needs a reduction of partial sums over the network.
- **Issues:**
  - Link bandwidth.
  - **Multicast** of shared operands (one B tile to every array that needs it).
  - Load balance and synchronization.
- **Link to this project:** the host-side tiling loop (3.6) is exactly the schedule that a NoC would spread across arrays.
- Fill in one sentence on how your thesis topic connects.

### 8.7 Systolic arrays vs GPU SIMT and tensor cores 🔶
- **GPU SIMT:** many threads run the same instruction on different data, with register files and caches. Flexible, but each operation costs energy for instruction fetch and register access.
- **Systolic array:** a fixed dataflow with operands passed between neighbours. Very efficient for GEMM, poor for irregular work.
- **Tensor cores:** small matrix units inside the GPU. They give the GPU systolic-like efficiency for GEMM while keeping it programmable.

---

## Level 9: Your project story

### 9.1 Two-minute pitch and your exact contribution
Template. Fill in the bracketed parts with only what is true for you.

> "In a group project with a PhD scholar in EE, we built a matrix-multiplication accelerator for FPGA: an N×N
> output-stationary systolic array in SystemVerilog. Each PE does a signed int8 multiply-accumulate into a 32-bit
> register. Skew buffers line up the inputs, and a five-state controller runs CLEAR, COMPUTE and DRAIN.
> I [designed / rebuilt and tested: PE, skew buffer, …]. We derived the latency, K + 2N cycles, and checked it with
> zero error against a SystemC model across 5 configurations × 1,000 jobs. For 8×8 at K = 64 that is 81% PE
> utilization and 5.12 GOPS at 50 MHz, in simulation. Verification used cocotb against a NumPy model, then UVM with
> a DPI-C scoreboard, SVA and coverage, and a formal proof of the bus protocol. Next is bring-up on the DE10-Lite to
> measure real Fmax and cycles. Over UART the design is I/O-bound, so a faster link is the main next step."

**Rule:** say "I" only for what you did yourself, and "we" or "the team" for the rest. Be ready to name which is which.

### 9.2 Your numbers, derived from first principles
Be able to derive each one on a whiteboard:
- int8 × int8 → 16 bits. 64 worst-case products → 22 bits. Hence int32.
- K + 2N = 80 cycles (8×8, K = 64) = 1.6 µs at 50 MHz.
- Utilization K / (K + 2N − 1) = 81.0% (8×8) and 90.1% (4×4).
- 8,192 operations / 1.6 µs = 5.12 GOPS. Peak 6.4 GOPS. Ratio 80%.
- Skew registers: N(N − 1)/2 = 28 per buffer.
- PE flip-flops: 48 each, 3,072 for 8×8. Multipliers: 64 of 288.
- UART: 1 KB in about 89 ms, against 1.6 µs of compute. I/O-bound by about 50,000×.

### 9.3 One module you can whiteboard completely
Start with the **PE** (deck 03). Then the **skew buffer** (a shift register per lane). Then the **controller FSM**
(five states with cycle counts). Practise drawing each in under 3 minutes.

### 9.4 Bugs you hit and how you found them
From the verification report (§6). **Claim only the ones you worked on.** Add your own from the labs.
- An SVA fired on a legal soft reset. Found by the UVM regression. Fixed with `disable iff`.
- An off-by-one error in the "all PEs active" bound. Caught **only** by the co-sim performance counters, while C stayed correct.
- The `to_signed()` test helper did not mask upper bits, causing false mismatches. This was a testbench bug.
- Vectors for K_MAX = 128 were generated only up to K = 64, so K 65–128 was silently untested. Fixed with per-K_MAX vectors.
- The plan said 78 cycles and the RTL gave 80. Explained by CLEAR + RAM latency.
- Tool quirks: Icarus 13 needed a cast for an enum assignment. cocotb tests had to be split into separate files per top-level module.

### 9.5 Limitations and next steps
Say these before the interviewer finds them.
- **The board has not been programmed yet.** Fmax, resources and the FPGA cycle column are pending.
- All performance numbers are **simulated** at an assumed 50 MHz.
- **I/O-bound over UART.** No double buffering, DMA or AXI/Avalon interface.
- No requantization (we return raw int32). int8 only.
- UVM runs on Verilator (no native covergroups). No gate-level simulation.
- **Next:** Quartus compile and timing → board bring-up → measured correlation → pipelined PE / PLL → Avalon wrapper
  with a soft CPU → MNIST with quantization (the roadmap).

---

## The future of this field (for "where is this going?" questions)

- **Matrix engines are everywhere.** TPUs in data centres, NPUs in phones and laptops, tensor cores in GPUs, AMX in
  CPUs, and AI accelerators in microcontrollers and MPUs (such as Renesas DRP-AI). The systolic idea from 1978 is now in
  every AI chip.
- **Lower precision.** int8 → int4, FP8, and block-scaled "microscaling" formats (OCP MX). More operations per mm² and
  per watt.
- **The memory wall.** Compute grows faster than bandwidth. Hence HBM, large on-chip SRAM, near-memory compute and
  data-reuse dataflows. That is exactly our I/O-bound lesson at a larger scale.
- **Sparsity and scale-out.** Structured sparsity, chiplets, and many arrays connected by NoCs.
- **Verification and performance modeling are growing.** Every accelerator needs SystemC/TLM models before RTL, then
  correlation against RTL and silicon, then UVM and formal sign-off. That is the flow this project practises, and the
  role you are applying for.
