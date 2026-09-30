# Systolic Array Project — Concept Notes

Study notes for the DE10-Lite systolic array project. Each section is referenced
from [PLAN.md](PLAN.md). Read a section *before* doing the matching day's work.

**Contents**
1. Number Systems & Two's Complement
2. What is an FPGA?
3. The DE10-Lite Board
4. The FPGA Design Flow
5. Verilog / SystemVerilog Essentials
6. Combinational vs Sequential Logic, Clock, Reset
7. Timing: Setup, Hold, Slack, Fmax, Metastability
8. Finite State Machines (FSMs)
9. Memory on FPGAs (M9K Block RAM)
10. UART Serial Communication
11. Verification & Testbenches (cocotb)
12. Matrix Multiplication Fundamentals
13. Systolic Arrays & Dataflows
14. Our Architecture — Walk-through
15. Fixed-Point, int8 & Bit Growth
16. Performance Metrics & the Roofline Model
17. Hardware Debugging
18. Interview Questions (with short answers)
19. Glossary

*Phases 5–6 — verification & performance modeling*

20. Verification Methodology
21. C/C++ Reference Models & DPI-C
22. SystemC Basics
23. TLM-2.0 Transaction-Level Modeling
24. Verilator & RTL/SystemC Co-simulation
25. UVM (Universal Verification Methodology)
26. SystemVerilog for Verification: Classes, Constraints, Coverage, SVA
27. Performance Modeling & HW/SW Correlation (+ interview questions)

---

## 1. Number Systems & Two's Complement

### Binary and hex
- A bit is 0/1; `N` bits represent 2ᴺ values.
- Hex is shorthand for 4 bits: `8'hA5` = `1010_0101`.
- Verilog literals: `<width>'<base><value>` → `8'd255`, `4'b1010`, `16'hBEEF`.

### Unsigned vs signed
- **Unsigned N-bit:** 0 … 2ᴺ − 1 → 8-bit: 0 … 255.
- **Signed (two's complement) N-bit:** −2ᴺ⁻¹ … 2ᴺ⁻¹ − 1 → 8-bit: **−128 … 127**.
- MSB is the sign bit (1 = negative).
- To negate: invert all bits and add 1 → `−5` = `~0000_0101 + 1` = `1111_1011`.
- Same adder hardware works for signed and unsigned — only the *interpretation* differs.

### Sign extension
- To widen a signed number, **copy the sign bit** into the new upper bits.
  - `1111_1011` (−5, 8-bit) → `1111_1111_1111_1011` (−5, 16-bit).
- Zero-extending a negative number (padding with 0s) is a classic bug — it turns −5 into 251.

### Bit growth (very important for this project)
- **Addition:** N-bit + N-bit → needs **N+1** bits.
- **Multiplication:** N-bit × M-bit → needs **N+M** bits.
  - int8 × int8 → 16 bits. Worst case: −128 × −128 = +16,384 (fits in signed 16-bit, max 32,767).
- **Summing K values:** adds ⌈log₂K⌉ bits.
  - Sum of 64 int8×int8 products → 16 + 6 = **22 bits**. We use 32 bits for safety.

---

## 2. What is an FPGA?

### Definition
- **Field-Programmable Gate Array:** a chip whose *hardware circuit* you define after manufacturing.
- You don't write a program that runs on it — you **describe a circuit** that it becomes.
- Reprogrammable: load a new configuration → new circuit.

### Building blocks
- **LUT (Look-Up Table):** a tiny memory (MAX 10: 4-input LUT = 16 bits) that implements *any* 4-input Boolean function. The basic logic element.
- **Flip-Flop (FF/register):** stores 1 bit, updates on the clock edge. Each LUT is paired with an FF.
- **LE (Logic Element):** 1 LUT + 1 FF + carry logic (MAX 10 terminology). **LAB** = group of 16 LEs.
- **Routing fabric:** programmable wires + switches connecting everything. Often the biggest delay.
- **Block RAM (M9K on MAX 10):** dedicated memory blocks, 9 Kbits each.
- **Embedded multipliers / DSP blocks:** hard-wired fast multipliers (18×18 or 2 × 9×9 on MAX 10).
- **PLL (Phase-Locked Loop):** generates new clock frequencies from an input clock.
- **I/O blocks:** connect internal logic to physical pins; configurable voltage standard.

### FPGA vs CPU vs GPU vs ASIC
| | CPU | GPU | FPGA | ASIC |
|---|---|---|---|---|
| Execution | Sequential instructions | Massively parallel SIMT threads | Custom circuit, true parallel | Custom circuit, fixed |
| Clock | ~3–5 GHz | ~1–2 GHz | ~50–500 MHz | ~1–3 GHz |
| Flexibility | Highest | High | Reconfigurable hardware | None after fab |
| Dev cost/time | Low | Low | Medium | Very high |
| Best for | Control, general code | Dense float math | Custom pipelines, low latency, prototyping | Mass production (e.g., TPU) |

- FPGAs win by **parallelism + custom datapaths**, not clock speed.
- FPGAs are used to **prototype ASICs** (e.g., accelerators like TPUs are validated on FPGAs first).

---

## 3. The DE10-Lite Board

### Main chip — Intel MAX 10 `10M50DAF484C7G`
- ~50,000 LEs (49,760).
- 182 M9K blocks ≈ 1,638 Kbits (~200 KB) of on-chip RAM.
- 144 embedded 18×18 multipliers (each usable as two 9×9 → 288 int8-sized multipliers).
- 4 PLLs.
- Non-volatile: has internal configuration flash (design can survive power-off via `.pof`).
- Note: MAX 10 has **no LUT-RAM** — all inferred RAMs go to M9K (or plain FFs).

### On-board peripherals you'll use
- **Clocks:** `MAX10_CLK1_50`, `MAX10_CLK2_50` (50 MHz), `ADC_CLK_10` (10 MHz).
- **LEDR[9:0]:** 10 red LEDs, **active-high** (1 = on).
- **SW[9:0]:** 10 slide switches.
- **KEY[1:0]:** 2 push buttons, **active-low** (0 when pressed). Hardware-debounced, but still need synchronizing.
- **HEX0–HEX5:** six 7-segment displays, **active-low** segments (0 = segment on), 8 bits each incl. decimal point.
- **GPIO[35:0]:** 2×20 header, **3.3 V** — the UART adapter connects here.
- Also: 64 MB SDRAM, VGA (12-bit color), ADXL345 accelerometer, Arduino header, ADC.

### USB port
- The USB-B port is a **USB-Blaster (JTAG)** used for programming only.
- **There is no USB-to-serial chip** → buy an external 3.3 V USB-to-UART adapter.

### UART adapter wiring
- Adapter **TX → FPGA RX pin** (a GPIO pin you choose).
- Adapter **RX → FPGA TX pin**.
- Adapter **GND → board GND** (mandatory common ground).
- **Do NOT** connect the adapter's 5 V/VCC pin. Set the adapter jumper to **3.3 V**.
- On Mac the port appears as `/dev/tty.usbserial-XXXX` or `/dev/tty.SLAB_USBtoUART`.

---

## 4. The FPGA Design Flow

### Steps
1. **Specification** — what the block does, ports, timing, throughput.
2. **RTL design** — describe hardware in Verilog/SystemVerilog (Register Transfer Level).
3. **Functional simulation** — run testbenches (Icarus/Verilator + cocotb). Fix bugs *here*.
4. **Synthesis** — Quartus converts RTL → netlist of LUTs, FFs, RAMs, multipliers.
5. **Fitter (Place & Route)** — assigns logic to physical locations and routes wires.
6. **Timing analysis** — Timing Analyzer checks every path meets the clock period.
7. **Assembler** — generates the programming file.
8. **Programming** — load onto the FPGA via USB-Blaster.
9. **Hardware test/debug** — LEDs, HEX, UART, SignalTap.

### Important Quartus files
| File | Purpose |
|---|---|
| `.qpf` | Quartus project file |
| `.qsf` | Settings: device, source files, **pin assignments**, I/O standards |
| `.sdc` | **Timing constraints** (clock definitions) |
| `.sof` | SRAM Object File — programs FPGA, **lost on power-off**; use during development |
| `.pof` | Programmer Object File — writes internal flash, **persists** |
| `.mif` / `.hex` | Memory initialization files for RAM/ROM |

### Minimal `.sdc`
```tcl
create_clock -name clk50 -period 20.000 [get_ports MAX10_CLK1_50]
derive_clock_uncertainty
```
- 20 ns period = 50 MHz. Without this, Quartus doesn't know your target speed.

### Pin assignment
- Use **DE10-Lite System Builder** (from Terasic CD) → generates `.qsf` with correct pin names.
- Top-level port names must match the names in the `.qsf` (e.g., `LEDR`, `SW`, `KEY`, `HEX0`).

---

## 5. Verilog / SystemVerilog Essentials

### Mindset
- You are describing **hardware that all exists at once and runs in parallel**, not steps executed in order.
- Before writing code, **draw the circuit** (registers, muxes, adders). Then write code that describes the drawing.

### Module structure
```systemverilog
module counter #(parameter int WIDTH = 8) (
    input  logic             clk,
    input  logic             rst_n,     // active-low reset
    input  logic             en,
    output logic [WIDTH-1:0] count
);
    always_ff @(posedge clk) begin
        if (!rst_n)   count <= '0;
        else if (en)  count <= count + 1'b1;
    end
endmodule
```

### Data types
- `logic` — SystemVerilog 4-state type; use for almost everything (replaces `reg`/`wire`).
- `logic [7:0] x;` — 8-bit vector, `x[7]` is MSB.
- `logic signed [7:0] a;` — signed interpretation (two's complement).
- `typedef enum logic [2:0] {IDLE, LOAD, RUN} state_t;` — named states.
- Arrays: `logic signed [31:0] acc [N][N];` — 2-D array of 32-bit values.

### Three kinds of blocks
- `assign y = a & b;` — continuous combinational logic.
- `always_comb begin ... end` — combinational logic (muxes, decoders, next-state logic).
- `always_ff @(posedge clk) begin ... end` — sequential logic (registers).

### Blocking (`=`) vs non-blocking (`<=`) — the #1 rule
- **Use `<=` in `always_ff`** (registers). All right-hand sides are sampled first, then updated together → models real flip-flops.
- **Use `=` in `always_comb`** (combinational).
- Never mix them in the same block.
- Example — swap works with `<=`, fails with `=`:
  ```systemverilog
  always_ff @(posedge clk) begin a <= b; b <= a; end   // correct swap
  ```

### Parameters and generate
- `parameter` / `localparam` make designs reusable (`N`, `DATA_W`, `ACC_W`).
- `generate for` creates multiple hardware instances — this is how we build the N×N PE grid:
  ```systemverilog
  for (genvar i = 0; i < N; i++) begin : g_row
      for (genvar j = 0; j < N; j++) begin : g_col
          pe u_pe ( ... );
      end
  end
  ```

### Signed arithmetic rules
- An expression is signed **only if every operand is signed**. One unsigned operand → whole expression unsigned.
- Use `$signed(x)` to reinterpret. Declare ports `signed` explicitly.
- Widths are extended to the widest operand/destination **before** the operation.

### Common pitfalls
- **Latch inference:** in `always_comb`, if a signal isn't assigned in every branch → latch. Fix: assign defaults at the top.
- **Multiple drivers:** assigning one signal from two `always` blocks → error/undefined.
- **Width mismatch:** silent truncation. Read synthesis warnings!
- **Uninitialized registers:** simulation shows `X`; hardware powers up to 0 (MAX 10) — don't rely on it, use reset.
- `initial` blocks are for testbenches (and RAM init), not general logic.

---

## 6. Combinational vs Sequential Logic, Clock, Reset

### Combinational logic
- Output depends **only on current inputs** (gates, muxes, adders, multipliers).
- No memory. Has a propagation delay.

### Sequential logic
- Output depends on inputs **and stored state** (registers).
- Flip-flop captures D on the **rising clock edge** → Q.
- Almost every real design = registers + combinational logic between them (**RTL**).

### Clock
- One global 50 MHz clock drives all registers → **single clock domain** (keep it that way in this project).
- **Never** make your own clock with a counter output (`clk_slow`). Instead use a **clock enable**:
  ```systemverilog
  // tick is high for 1 cycle every 50,000,000 cycles (1 Hz)
  always_ff @(posedge clk) if (tick) led <= ~led;
  ```

### Reset
- **Synchronous reset:** checked only on clock edge — simple, recommended here.
- **Asynchronous reset:** acts immediately — must be *de-asserted synchronously*.
- KEY is active-low → name it `rst_n` and synchronize it.

### Pipelining
- Insert registers in a long combinational path → shorter path per stage → **higher clock frequency**.
- Costs: extra latency (cycles) and registers. Throughput stays one result per cycle.
- The systolic array is essentially a **2-D pipeline**.

---

## 7. Timing: Setup, Hold, Slack, Fmax, Metastability

### Setup and hold
- **Setup time (Tsu):** data must be stable *before* the clock edge.
- **Hold time (Th):** data must stay stable *after* the clock edge.
- Violating either → the FF may capture a wrong or unstable value.

### Critical path and Fmax
- Path delay = Tclk→Q + Tlogic + Trouting + Tsetup.
- **Critical path** = the slowest register-to-register path.
- **Fmax = 1 / (critical path delay).**
- For 50 MHz, every path must be < 20 ns.

### Slack
- **Slack = required time − arrival time.**
- Slack ≥ 0 → timing met. **Negative slack → design will fail on hardware**, even if simulation passes.
- Check in Quartus: *Timing Analyzer → Report Setup Summary / Fmax Summary*.

### Fixing timing
- Add pipeline registers (e.g., register the multiplier output inside the PE).
- Reduce logic depth / fan-out, use embedded multipliers instead of LUT logic.
- Lower the clock or reduce N.

### Metastability & synchronizers
- Signals from outside the clock domain (UART RX pin, buttons) change at any time → can violate setup/hold.
- The FF can go **metastable** (neither 0 nor 1 for a while) → random failures.
- **Fix: 2-flip-flop synchronizer** — pass the async signal through two FFs before using it.
  ```systemverilog
  always_ff @(posedge clk) begin s1 <= async_in; s2 <= s1; end   // use s2
  ```
- Never use an unsynchronized external input in more than one place.

---

## 8. Finite State Machines (FSMs)

### Concept
- A circuit that is in one of a finite set of **states**; moves between them based on inputs.
- Used for **control**: the controller of our accelerator is an FSM.

### Types
- **Moore:** outputs depend only on the state → glitch-free, one cycle slower.
- **Mealy:** outputs depend on state + inputs → faster reaction, possible glitches.

### Recommended coding style (2-block)
```systemverilog
typedef enum logic [2:0] {IDLE, CLEAR, COMPUTE, DRAIN, DONE} state_t;
state_t state, next;

always_ff @(posedge clk)                  // 1) state register
    if (!rst_n) state <= IDLE; else state <= next;

always_comb begin                         // 2) next-state + outputs
    next = state;                         // default → no latches
    case (state)
        IDLE:    if (start) next = CLEAR;
        CLEAR:              next = COMPUTE;
        COMPUTE: if (cnt == LAST) next = DRAIN;
        DRAIN:              next = DONE;
        DONE:               next = IDLE;
        default:            next = IDLE;
    endcase
end
```

### Good practices
- Draw the state diagram **before** coding.
- Always have a `default` branch and a reset state.
- Display the current state on LEDs during debugging.

---

## 9. Memory on FPGAs (M9K Block RAM)

### Storage options
- **Registers (FFs):** fastest, any width, but expensive — use for small data (PE accumulators).
- **M9K Block RAM:** 9 Kbits per block, dense and cheap — use for matrix buffers.
  - Configurable: 8K×1, 4K×2, 2K×4, 1K×8 (or ×9), 512×16 (×18), 256×32 (×36).
  - Single-port, simple dual-port, true dual-port modes.

### Synchronous read (key behavior)
- M9K has **registered inputs** → read data appears **one clock cycle after** the address.
- Your controller must account for this 1-cycle latency (a common off-by-one bug).

### Inferring RAM from RTL (Quartus recognizes this pattern)
```systemverilog
logic [7:0] mem [0:DEPTH-1];
always_ff @(posedge clk) begin
    if (we) mem[addr] <= wdata;
    rdata <= mem[addr];            // registered read → maps to M9K
end
```
- Asynchronous read (`assign rdata = mem[addr]`) **cannot** map to M9K → becomes huge FF logic.
- Initialize with `$readmemh("file.hex", mem);` or a `.mif` file.
- Check "Total memory bits" in the Quartus Fitter report to confirm inference.

### Memory for this project (N=8, K=64)
- A buffer: 8 × 64 = 512 bytes; B buffer: 64 × 8 = 512 bytes → tiny compared to ~200 KB available.
- Organize memory **per row of A / per column of B** so all N rows can be read in parallel each cycle.

---

## 10. UART Serial Communication

### What it is
- **Universal Asynchronous Receiver-Transmitter:** simple 2-wire serial link (TX, RX) + GND.
- "Asynchronous" → no shared clock; both sides agree on a **baud rate** in advance.

### Frame format (8N1)
```
 idle  start  D0 D1 D2 D3 D4 D5 D6 D7  stop  idle
  1  |  0   | ← 8 data bits, LSB first →| 1  |  1
```
- Line idles **high**. Start bit = 0. 8 data bits **LSB first**. Stop bit = 1.
- 10 bits per byte → at 115,200 baud: **11,520 bytes/s**.

### Baud rate generation
- Clocks per bit = 50,000,000 / 115,200 ≈ **434** (error 0.007%, fine).
- UART tolerates roughly ±2–3% total clock mismatch.

### Transmitter (TX)
- FSM: `IDLE → START → DATA(×8) → STOP`.
- Hold each bit for 434 clock cycles; shift the data register right each bit.
- Output a `busy`/`done` signal so upstream logic knows when to send the next byte.

### Receiver (RX)
- Synchronize the RX pin with a 2-FF synchronizer first.
- Detect the falling edge (start bit).
- Wait **half a bit** (217 cycles) → you're at the middle of the start bit; confirm it's still 0.
- Then sample every 434 cycles (middle of each data bit) → 8 bits.
- Check stop bit = 1 (else framing error). Pulse `valid` for 1 cycle with the byte.
- Alternative method: **16× oversampling** (tick at 16 × baud, sample at tick 8 of each bit).

### Testing on Mac
- Terminal: `screen /dev/tty.usbserial-XXXX 115200` (exit: Ctrl-A then K).
- Python:
  ```python
  import serial
  s = serial.Serial('/dev/tty.usbserial-XXXX', 115200, timeout=1)
  s.write(b'P'); print(s.read(3))
  ```

---

## 11. Verification & Testbenches (cocotb)

### Why verification matters
- In industry, verification takes **more than half** of chip development effort.
- Bugs found on hardware are 10–100× harder to fix than in simulation.

### Vocabulary
- **DUT:** Design Under Test.
- **Testbench:** code that drives inputs and checks outputs; not synthesized.
- **Golden / reference model:** trusted software implementation (NumPy `A @ B`).
- **Scoreboard:** compares DUT output vs golden model.
- **Directed test:** hand-picked inputs (identity matrix, all −128).
- **Random test:** random inputs, many iterations → finds unexpected bugs.
- **Corner cases:** extremes — min/max values, K=1, zeros, overflow boundaries.
- **Regression:** re-running all tests after every change.

### Self-checking testbench
- Never verify by staring at waveforms only — the testbench must **automatically print PASS/FAIL**.
- Waveforms (GTKWave, `.vcd`/`.fst`) are for **debugging** a failure.

### cocotb basics (Python testbenches)
```python
import cocotb, random
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

@cocotb.test()
async def test_pe(dut):
    cocotb.start_soon(Clock(dut.clk, 20, units="ns").start())
    dut.clear.value = 1
    await RisingEdge(dut.clk)
    dut.clear.value = 0
    a, b = random.randint(-128, 127), random.randint(-128, 127)
    dut.a_in.value = a; dut.b_in.value = b; dut.en.value = 1
    await RisingEdge(dut.clk); await RisingEdge(dut.clk)
    assert dut.acc.value.signed_integer == a * b
```
- `await RisingEdge(dut.clk)` = wait one clock.
- `.value.signed_integer` reads a signal as signed.
- Run with a `Makefile` that sets `SIM=icarus` (or `verilator`), `TOPLEVEL`, `MODULE`.

### Verification strategy for this project (bottom-up)
1. PE alone → 2. 2×2 array (hand-skewed) → 3. N×N with skew buffers → 4. core with memories + FSM → 5. full top with UART → 6. hardware with host script.

---

## 12. Matrix Multiplication Fundamentals

### Definition
- A is N×K, B is K×M → C is N×M.
- **C[i][j] = Σₖ A[i][k] · B[k][j]** — dot product of row i of A and column j of B.

### Cost
- MAC (multiply-accumulate) count = **N · M · K**.
- Operations (1 MAC = 2 ops: multiply + add) = **2 · N · M · K**.
- For square n×n: **O(n³) compute** but only **O(n²) data**.

### Data reuse — the key insight
- Every element of A is used M times; every element of B is used N times.
- Fetching each value once and **reusing it many times** is what makes accelerators fast.
- **Arithmetic intensity** = operations / bytes moved. Higher → more compute-bound (good).

### Naive CPU code
```python
for i in range(N):
    for j in range(M):
        for k in range(K):
            C[i][j] += A[i][k] * B[k][j]
```
- A CPU does ~1–a few MACs per cycle per core; our 8×8 array does **64 MACs per cycle**.

### Tiling (blocking)
- Large matrices are split into tiles that fit the array (e.g., 8×8 output tiles).
- C_tile = Σ A_tile × B_tile over the K dimension.
- Used by CPUs (cache blocking), GPUs (shared memory), and TPUs.

### Why it matters
- Neural networks are dominated by matrix multiplication (fully-connected layers, convolutions via im2col, attention in transformers).

---

## 13. Systolic Arrays & Dataflows

### Origin & name
- Proposed by **H. T. Kung and Charles Leiserson (1978)**; H. T. Kung, "Why Systolic Architectures?" (1982).
- "Systolic" — like the heart pumping blood: data is **pumped rhythmically** through a grid of cells each clock cycle.

### Core idea
- A 2-D grid of identical **Processing Elements (PEs)**.
- Each PE does a **MAC** and passes data to its **neighbors** only.
- Data enters from edges and flows across the array; each value is reused by every PE it passes.

### Why it's efficient
- **Local connections only** → short wires → high clock frequency, easy to scale.
- **Massive parallelism:** N² MACs per cycle.
- **Data reuse:** each operand is read from memory once but used N times → low memory bandwidth.
- **Regular structure:** one PE design replicated → simple to design and verify.
- **No central control per PE** — control is simple.

### Dataflows (what stays still inside a PE)
- **Output-stationary (OS)** — *our choice*:
  - Each PE(i,j) holds and accumulates **C[i][j]**.
  - A values flow **left → right**, B values flow **top → bottom**.
  - Simple; results read out at the end.
- **Weight-stationary (WS)** — Google TPU:
  - Each PE holds one **weight** (B element) permanently; inputs flow across, partial sums flow down.
  - Great for neural nets: weights are reused across many inputs.
- **Input-stationary (IS):** input values stay; weights and partial sums move.
- **Row-stationary:** used by MIT Eyeriss for CNNs; optimizes energy for convolution.

### Skewing
- For PE(i,j) to receive A[i][k] and B[k][j] **at the same cycle**, inputs must be staggered:
  - Row i of A is delayed by **i** cycles.
  - Column j of B is delayed by **j** cycles.
- This forms a diagonal "wavefront" moving across the array.

### Latency & utilization (output-stationary, N×N array)
- PE(i,j) performs its k-th MAC at cycle **t = i + j + k**.
- Last MAC (PE(N−1,N−1), k=K−1) at t = K − 1 + 2(N − 1) → total **K + 2N − 2 cycles**.
- **Fill / drain overhead:** 2N − 2 cycles when not all PEs are busy.
- **Utilization = K / (K + 2N − 2)**. For N=8, K=64: 64/78 ≈ 82%. Larger K → closer to 100%.

### Real-world example — Google TPU v1 (2017)
- 256×256 = **65,536** 8-bit MACs, weight-stationary, 700 MHz → ~92 TOPS.
- Same concept as your project, just much bigger.

---

## 14. Our Architecture — Walk-through

### Processing Element (PE)
```
                 b_in
                  │
                  ▼
   a_in ──▶ ┌──────────┐ ──▶ a_out   (registered: a_out <= a_in)
            │ acc +=   │
            │ a_in*b_in│
            └──────────┘
                  │
                  ▼
                 b_out                (registered: b_out <= b_in)
```
- Inputs: `a_in`, `b_in` (int8), `en`, `clear`.
- Registers: `a_out`, `b_out` (int8), `acc` (int32).
- Behavior per clock: if `clear` → acc = 0; else if `en` → `acc <= acc + a_in * b_in`.
- Optional: 2-stage PE (register the product first) for higher Fmax.

### Array (N=3 example)
```
            B col0   B col1   B col2
              ▼        ▼        ▼
 A row0 ──▶ PE00 ──▶ PE01 ──▶ PE02
              ▼        ▼        ▼
 A row1 ──▶ PE10 ──▶ PE11 ──▶ PE12
              ▼        ▼        ▼
 A row2 ──▶ PE20 ──▶ PE21 ──▶ PE22
```

### Skew buffer
- Row i of A passes through a shift register of length i (row 0: none, row 1: 1 FF, row 2: 2 FFs…).
- Same for column j of B.
- Result: a triangle of registers — N(N−1)/2 registers per side.

### Full data path
```
A buffer (M9K) ─▶ A skew ─▶ ┐
                            ├─▶ N×N PE array ─▶ result mux ─▶ UART TX
B buffer (M9K) ─▶ B skew ─▶ ┘
          ▲                       ▲
      controller FSM (address counter k, en, clear, done, cycle counter)
```

### Cycle table — 2×2 array, K = 2
`a[i][k]` = A row i, col k; `b[k][j]` = B row k, col j. PE(i,j) at cycle t uses k = t − i − j.

| Cycle t | PE(0,0) | PE(0,1) | PE(1,0) | PE(1,1) |
|---|---|---|---|---|
| 0 | a00·b00 | — | — | — |
| 1 | a01·b10 | a00·b01 | a10·b00 | — |
| 2 | — | a01·b11 | a11·b10 | a10·b01 |
| 3 | — | — | — | a11·b11 |

- After cycle 3: PE(0,0) = a00·b00 + a01·b10 = **C[0][0]** ✓, and so on.
- Total = K + 2N − 2 = 2 + 4 − 2 = **4 cycles** ✓.

### Exercise (Day 8) — fill in for a 3×3 array, K = 3
- Total cycles should be 3 + 6 − 2 = 7 (t = 0…6).

| t | PE00 | PE01 | PE02 | PE10 | PE11 | PE12 | PE20 | PE21 | PE22 |
|---|---|---|---|---|---|---|---|---|---|
| 0 | | | | | | | | | |
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |
| 6 | | | | | | | | | |

### Readout
- After compute, all N² accumulators hold C.
- Simple approach: a mux selects `acc[i][j]` by index, and the UART sends it byte by byte.
- Alternative: shift accumulators out through the array (fewer wires, better for large N).

---

## 15. Fixed-Point, int8 & Bit Growth

### Why int8 instead of float32
- **4× less memory and bandwidth** than float32.
- Multiplier area grows roughly with **bits²** → an int8 multiplier is ~16× smaller than int32.
- Neural-network inference works well in int8 (TPU, NVIDIA Tensor Cores, mobile NPUs).

### Quantization (preview for the MNIST project)
- `q = clamp(round(x / scale), −128, 127)` — maps floats to int8.
- Result of integer matmul is rescaled: `y ≈ scale_A · scale_B · (A_q × B_q)`.

### Accumulator sizing
- Product: 8 + 8 = 16 bits. Sum over K: +⌈log₂K⌉ bits.
- K = 64 → 22 bits. We use **int32** → safe for K up to 65,536.
- If the accumulator is too small → **overflow (wrap-around)** → silently wrong results.
- **Saturation** (clamp to max/min) is an alternative when narrowing output widths.

### Signed multiply in hardware
- MAX 10 embedded multipliers support signed operands directly.
- Make sure both operands are declared `signed` so Quartus uses a signed multiplier.

---

## 16. Performance Metrics & the Roofline Model

### Metrics to report
- **Latency:** time for one operation (cycles or µs) — e.g., 78 cycles for N=8, K=64.
- **Throughput:** operations per second — GOPS = 2 · N² · f_clk · utilization.
  - Peak for N=8 @ 50 MHz: 2 × 64 × 50 M = **6.4 GOPS**.
- **Utilization:** fraction of PEs doing useful work = K / (K + 2N − 2).
- **Fmax:** from Timing Analyzer.
- **Resources:** LEs, registers, M9K bits, embedded multipliers (% used).
- **Efficiency:** GOPS per multiplier, or GOPS/W (if you estimate power with Quartus Power Analyzer).

### Compute-bound vs memory/I/O-bound
- **Compute-bound:** the math units are the bottleneck.
- **I/O- or memory-bound:** waiting on data is the bottleneck.
- Our design: UART moves ~11.5 KB/s → sending A and B (1 KB) takes ~89 ms, compute takes ~1.6 µs → **I/O-bound by ~50,000×**.

### Roofline model
- **Attainable performance = min(peak compute, bandwidth × arithmetic intensity).**
- Low arithmetic intensity or low bandwidth → you hit the "memory roof".
- Fixes: higher-bandwidth links (PCIe, DDR), on-chip data reuse, tiling, double buffering.

### Amdahl's law
- Speedup_total = 1 / ((1 − p) + p / s), where p = fraction accelerated, s = speedup of that part.
- Accelerating compute 1000× gives little if data transfer dominates.

### Double buffering (stretch goal)
- Two buffers: compute on one while loading the other → overlaps I/O and compute.

---

## 17. Hardware Debugging

### Golden rule
- **Simulate first.** Go to hardware only after tests pass in simulation.

### Tools on the board
- **LEDs:** show FSM state, error flags, "heartbeat" blink (proves clock + design are alive).
- **HEX displays:** show counters, received byte values, cycle count.
- **UART loopback:** echo test proves the link works before adding complexity.
- **SignalTap II Logic Analyzer (Quartus):**
  - Embeds a logic analyzer inside the FPGA using M9K memory.
  - Choose signals, sampling clock, **trigger condition** (e.g., `state == COMPUTE`), sample depth.
  - Recompile, program, then view real waveforms from the running hardware.

### Common symptoms → causes
| Symptom | Likely cause |
|---|---|
| Nothing happens at all | Wrong pins in `.qsf`, reset stuck active (KEY is active-low), wrong clock pin |
| UART prints garbage | Wrong baud divider, TX/RX not crossed, no common GND, 5 V adapter setting |
| Works in sim, random failures on HW | Missing synchronizer, negative slack, uninitialized state |
| Results off by one row/column | Skew or memory read-latency off-by-one |
| Wrong sign / large values | Unsigned arithmetic somewhere, missing `signed` |
| Correct for small values only | Accumulator overflow / width truncation |

---

## 18. Interview Questions (with short answers)

1. **What is an FPGA and how is it different from a CPU?**
   Reconfigurable hardware (LUTs, FFs, BRAM, DSPs, routing). A CPU executes instructions sequentially; an FPGA *becomes* a custom parallel circuit.
2. **What is a LUT?**
   A small memory that implements any Boolean function of its inputs (4 inputs on MAX 10).
3. **Blocking vs non-blocking assignments?**
   `<=` updates all registers simultaneously at the clock edge (use in sequential logic); `=` updates immediately (use in combinational logic).
4. **How do you avoid latches?**
   Assign every output in every branch of `always_comb`; use default assignments.
5. **Setup and hold time? What is slack?**
   Data must be stable before/after the clock edge. Slack = required − arrival time; negative slack = timing failure.
6. **How do you improve Fmax?**
   Pipelining, reducing logic depth/fan-out, using hard DSP blocks, better floorplanning.
7. **What is metastability and how do you handle it?**
   An FF sampling a changing signal may enter an undefined state; use a 2-FF synchronizer for async inputs.
8. **What is a systolic array?**
   A grid of PEs that each perform a MAC and pass data only to neighbors; data is pumped rhythmically, giving high parallelism and data reuse.
9. **Why are systolic arrays good for matrix multiplication?**
   O(n³) compute on O(n²) data → each operand reused N times; local wiring enables high clocks and scaling.
10. **Output-stationary vs weight-stationary?**
    OS keeps partial sums in PEs (simple, good when K is large); WS keeps weights in PEs (TPU; good when weights are reused across many inputs).
11. **Why skew the inputs?**
    So PE(i,j) receives A[i][k] and B[k][j] in the same cycle — creates a diagonal wavefront.
12. **Latency of an N×N output-stationary array?**
    K + 2N − 2 cycles; utilization K / (K + 2N − 2).
13. **Why is the accumulator 32 bits?**
    int8×int8 = 16 bits; summing K products adds log₂K bits; 32 bits avoids overflow.
14. **What limits your design's performance?**
    UART I/O bandwidth — it's I/O-bound. Fix with a faster interface, on-chip reuse, double buffering.
15. **How did you verify your design?**
    Bottom-up cocotb testbenches, NumPy golden model, directed + random tests, corner cases; then hardware tests with a Python host comparing against NumPy.
16. **How does a UART receiver work?**
    Synchronize input, detect start bit, wait half a bit to sample the middle, then sample every bit period; check stop bit.
17. **What's the difference between BRAM and registers?**
    BRAM is dense memory with synchronous read (1-cycle latency) and limited ports; registers are fast, individually accessible, but costly.
18. **How would you scale this design?**
    Larger N (limited by multipliers), tiling in software for bigger matrices, double buffering, DDR/PCIe for bandwidth, 2-stage PEs for higher clocks.
19. **How does this relate to Google's TPU?**
    TPU v1 is a 256×256 weight-stationary int8 systolic array — same principle, much larger scale.
20. **Explain your project in 2 minutes.** (Practice this!)
    Goal → architecture (PE, array, skew, buffers, FSM, UART) → verification → results (resources, Fmax, cycles, GOPS) → bottleneck insight → future work.

---

## 19. Glossary

| Term | Meaning |
|---|---|
| RTL | Register Transfer Level — describing hardware as registers + logic between them |
| HDL | Hardware Description Language (Verilog, SystemVerilog, VHDL) |
| LE / LAB | Logic Element (LUT+FF) / Logic Array Block (16 LEs) — Intel terms |
| LUT | Look-Up Table |
| FF | Flip-flop (1-bit register) |
| BRAM / M9K | Block RAM; M9K = 9-Kbit block on MAX 10 |
| DSP / embedded multiplier | Hard multiplier block |
| PLL | Phase-Locked Loop — clock generator |
| PE | Processing Element |
| MAC | Multiply-Accumulate: acc += a × b |
| GOPS / TOPS | Giga / Tera operations per second |
| Fmax | Maximum clock frequency the design can run at |
| Slack | Timing margin; negative = failure |
| CDC | Clock Domain Crossing |
| DUT | Design Under Test |
| Golden model | Trusted reference implementation used to check the DUT |
| JTAG / USB-Blaster | Programming/debug interface of the board |
| SignalTap | Quartus on-chip logic analyzer |
| Baud | Symbols (bits) per second on a UART line |
| 8N1 | 8 data bits, No parity, 1 stop bit |
| Arithmetic intensity | Operations per byte of data moved |
| Roofline | Performance model: min(peak compute, bandwidth × intensity) |
| Tiling | Splitting a big matrix into array-sized blocks |
| Double buffering | Loading the next data set while computing the current one |

---

# Part 2 — Verification & Performance Modeling (Phases 5–6)

---

## 20. Verification Methodology

### Pre-silicon verification
- Chips cost months and millions to fabricate → bugs must be found **before** tape-out.
- Levels: unit (one block) → subsystem → SoC → emulation / FPGA prototype → post-silicon validation.
- **Shift-left:** find bugs as early as possible (models + simulation), where fixing is cheapest.

### The verification plan (vplan)
- A document listing **features → how each is tested → how completion is measured**.
- Example rows for this project:
  | Feature | Test | Coverage |
  |---|---|---|
  | Correct C for any K | random_job_seq | K bins 1, 2–7, 8–63, 64 |
  | Signed extremes | corner_values_test | A/B values −128, −1, 0, 1, 127 |
  | Back-to-back jobs | b2b_test | cross(job_count, K) |
  | Reset during compute | reset_mid_test | FSM state at reset |
- Interviewers love asking "how do you know you're done?" → **the vplan + coverage goals**.

### Directed vs constrained-random
- **Directed:** hand-written scenario (identity matrix). Precise, but only tests what you think of.
- **Constrained-random:** random stimulus within legal rules (constraints). Finds bugs you didn't imagine.
- Industry uses both: random for breadth, directed for specific corner cases coverage misses.

### Coverage-driven verification (CDV) loop
```
 write vplan → build TB → run random regression → measure coverage
      ▲                                                  │
      └──── add constraints / directed tests for holes ◀─┘
```

### Two kinds of coverage
- **Code coverage** (automatic, from the simulator): line, branch, condition, toggle, FSM state/transition.
  - Answers: "did the code *execute*?"
- **Functional coverage** (written by you: covergroups): "did we test the *features* in the vplan?"
  - 100 % code coverage does **not** mean the design is correct.

### Checking
- **Scoreboard:** compares DUT outputs with a **reference model** automatically.
- **Assertions (SVA):** check protocol/timing rules every cycle (e.g., "ready never drops while valid is held").
- **Self-checking:** every test ends in PASS/FAIL — no manual waveform inspection.

### Regression
- Run all tests with many random **seeds** every change. A failing seed must be **reproducible**.
- Track pass rate, coverage trend, bugs found per week.

---

## 21. C/C++ Reference Models & DPI-C

### Types of models
- **Bit-accurate (functional) model:** produces exactly the same output bits as the RTL, no timing.
- **Cycle-approximate model:** also predicts roughly how many cycles.
- **Cycle-accurate model:** matches the RTL cycle for cycle (expensive to write; the RTL itself is one).

### Writing a bit-accurate C++ model
- Use fixed-width types: `int8_t`, `int16_t`, `int32_t`, `int64_t` (`<cstdint>`).
- **Careful:** signed integer overflow is **undefined behaviour in C/C++**. If the RTL wraps at 32 bits,
  accumulate in `int64_t` and then truncate, or do the arithmetic in `uint32_t`:
  ```cpp
  int32_t wrap_add(int32_t acc, int32_t p) {
      return (int32_t)((uint32_t)acc + (uint32_t)p);   // two's-complement wrap, like hardware
  }
  ```
- The model must mirror the RTL **spec**, not the RTL **code** — otherwise both share the same bug.

### Shared test vectors
- Store inputs/expected outputs in simple files (e.g., `.hex`, one value per line).
- NumPy, C++, SystemC, cocotb and UVM all read the **same files** → any mismatch points to one model.

### DPI-C (Direct Programming Interface)
- Standard SystemVerilog feature to call C functions from SV (and vice versa).
- SV side:
  ```systemverilog
  import "DPI-C" function void mm_ref(input int n, input int k,
                                      input byte a[], input byte b[], output int c[]);
  ```
- C/C++ side (open arrays arrive as handles):
  ```cpp
  #include "svdpi.h"
  extern "C" void mm_ref(int n, int k, const svOpenArrayHandle a,
                         const svOpenArrayHandle b, const svOpenArrayHandle c) {
      auto* A = static_cast<const int8_t*>(svGetArrayPtr(a));
      auto* B = static_cast<const int8_t*>(svGetArrayPtr(b));
      auto* C = static_cast<int32_t*>(svGetArrayPtr(c));
      // ... bit-accurate matmul ...
  }
  ```
- Type mapping: `byte ↔ char/int8_t`, `int ↔ int32_t`, `longint ↔ int64_t`, `bit ↔ svBit`.
- `export "DPI-C"` lets C code call an SV function/task (used less often).
- Questa flow: `vlog -dpiheader dpi.h tb.sv` → compile C into a shared library → `vsim -sv_lib libref ...`.

---

## 22. SystemC Basics

### What it is
- A **C++ class library** (IEEE 1666) that adds hardware concepts to C++: modules, ports, signals, clocks, time, concurrency.
- Used for **architecture exploration, performance models, virtual platforms** (running software before silicon exists).
- Much faster than RTL simulation; written by architects and modeling/verification engineers.

### Building blocks
- `SC_MODULE(Name)` — a hardware block (a C++ class).
- `SC_CTOR(Name)` — constructor; registers processes.
- Ports: `sc_in<T>`, `sc_out<T>`; channels: `sc_signal<T>`, `sc_fifo<T>`.
- `sc_clock clk("clk", 20, SC_NS);` — a 50 MHz clock.
- `sc_main()` — replaces `main()`; instantiate, bind ports, call `sc_start()`.

### Processes
- **`SC_METHOD`**: runs to completion each time a signal in its sensitivity list changes; **cannot `wait()`**. Like `always_comb`/`always_ff`.
- **`SC_THREAD`**: started once, can **`wait()`** for time or events. Natural for sequential behaviour and cycle-approximate models.
- `wait(10, SC_NS)`, `wait(clk.posedge_event())`, `wait(ev)`.

### Example — a MAC PE
```cpp
SC_MODULE(pe) {
    sc_in<bool>          clk, clear, en;
    sc_in<sc_int<8>>     a_in, b_in;
    sc_out<sc_int<32>>   acc;
    sc_int<32> acc_r = 0;

    void step() {
        if (clear.read())      acc_r = 0;
        else if (en.read())    acc_r += a_in.read() * b_in.read();
        acc.write(acc_r);
    }
    SC_CTOR(pe) { SC_METHOD(step); sensitive << clk.pos(); }
};
```

### Delta cycles
- Like Verilog, SystemC updates signals in **delta cycles**: a write becomes visible after the current evaluation, at the same simulation time. This is how non-blocking-like behaviour is modelled.

### Data types
- `sc_int<W>`, `sc_uint<W>` (≤ 64 bits), `sc_bigint<W>`, `sc_bv<W>` (bit vector), `sc_lv<W>` (4-state logic).
- Plain C++ types are faster; use `sc_int` when exact width matters.

---

## 23. TLM-2.0 Transaction-Level Modeling

### Idea
- Instead of modelling every wire and cycle, model **transactions**: "write 64 bytes to address 0x1000".
- 100–1000× faster than RTL → can simulate software running on a whole SoC.

### Key pieces (part of IEEE 1666)
- **Initiator** (e.g., CPU model, test) sends transactions; **target** (e.g., accelerator, memory) receives them.
- **Sockets:** `tlm_utils::simple_initiator_socket`, `tlm_utils::simple_target_socket`.
- **Generic payload** `tlm::tlm_generic_payload`: command (READ/WRITE), address, data pointer, length, byte enables, response status.

### Coding styles
- **Loosely-timed (LT):** blocking call `b_transport(trans, delay)`. The target adds its latency to `delay`.
  - Fast; used for software development / functional models.
  - **Temporal decoupling:** an initiator runs ahead of simulation time up to a **quantum**, then syncs.
- **Approximately-timed (AT):** non-blocking `nb_transport_fw/bw` with 4 phases
  `BEGIN_REQ → END_REQ → BEGIN_RESP → END_RESP`. Models pipelining and contention; slower, more accurate.
- **DMI (Direct Memory Interface):** initiator gets a raw pointer to target memory → even faster.

### Target example (our register map)
```cpp
void b_transport(tlm::tlm_generic_payload& t, sc_time& delay) {
    uint64_t addr = t.get_address();
    uint8_t* ptr  = t.get_data_ptr();
    if (t.is_write()) write_reg(addr, ptr, t.get_data_length());
    else              read_reg(addr, ptr, t.get_data_length());
    delay += sc_time(20, SC_NS);                 // model 1 bus cycle
    t.set_response_status(tlm::TLM_OK_RESPONSE);
}
```

### Modeling levels — speed vs accuracy
| Level | Speed | Timing accuracy | Used for |
|---|---|---|---|
| Untimed / functional | fastest | none | algorithm, reference model |
| TLM LT | very fast | approximate latency | virtual platforms, SW bring-up |
| TLM AT | fast | pipeline/contention | architecture & performance studies |
| Cycle-accurate | slow | exact | detailed perf, RTL correlation |
| RTL | slowest | exact (it *is* the design) | implementation, sign-off |

---

## 24. Verilator & RTL/SystemC Co-simulation

### Verilator
- Open-source tool that **compiles SystemVerilog RTL into C++ (or SystemC) classes**.
- Very fast (cycle-based, 2-state: no `X`/`Z`), used by many companies for large regressions.
- Verilator ≥ 5 supports `--timing` (delays, `@` events in testbenches).
- `verilator --sc` generates a **SystemC module** — the RTL becomes an `sc_module` with `sc_in`/`sc_out` ports.

### Co-simulation harness
```
                 same stimulus (from .hex vectors)
        ┌───────────────┴────────────────┐
        ▼                                ▼
  Vmm_core (RTL via Verilator)    mm_ca (SystemC model)
        │  C matrix + perf counters      │
        └────────────► compare ◄─────────┘
                         │
                  mismatch → dump both states + waveform
```
- Build example:
  ```bash
  verilator --sc --exe --build -Wall --top-module mm_core \
      rtl/core/*.sv cosim/sc_main.cpp -o cosim
  ```
- Checks both **function** (same C) and **performance** (same/near cycle counters).

### Why this matters
- Proves the **software model matches the hardware** → the model can then be trusted for early performance studies and software development.
- Exactly the "co-simulation in SystemC environment to verify software models and RTL" task in verification JDs.

---

## 25. UVM (Universal Verification Methodology)

### What it is
- A **SystemVerilog class library** (IEEE 1800.2) that standardizes how testbenches are built.
- Goals: **reuse** (agents reused across projects), **scalability**, constrained-random + coverage.
- Needs a full simulator: Questa, VCS, Xcelium, Riviera (Icarus can't run UVM).

### Architecture
```
 uvm_test (base_test, random_test ...)
  └── uvm_env (mm_env)
       ├── uvm_agent (bus_agent)          ← active: drives the DUT
       │    ├── uvm_sequencer  ◀── sequences (random_job_seq ...)
       │    ├── uvm_driver     ──▶ virtual interface ──▶ DUT pins
       │    └── uvm_monitor    ◀── virtual interface ◀── DUT pins
       │          └── analysis_port ──┬──▶ uvm_scoreboard (DPI-C → C++ model)
       │                              └──▶ coverage collector (uvm_subscriber)
       └── env config
```

### Components (static, built once — `uvm_component`)
- **Driver:** takes sequence items, wiggles DUT pins through a **virtual interface**.
- **Monitor:** passively watches pins, reconstructs transactions, broadcasts them (`analysis_port.write()`).
- **Sequencer:** arbitrates and hands items from sequences to the driver.
- **Agent:** bundles driver + sequencer + monitor. *Active* (drives) or *passive* (monitor only).
- **Scoreboard:** receives transactions, computes expected results (reference model), compares.
- **Env:** contains agents, scoreboards, coverage. **Test:** configures the env and starts sequences.

### Objects (dynamic, created and destroyed — `uvm_object`)
- **Sequence item** (`uvm_sequence_item`): one transaction (e.g., bus read/write), `rand` fields + constraints.
- **Sequence** (`uvm_sequence`): generates a stream of items in its `body()` task.

### Key mechanisms
- **Factory:** create with `type_id::create("name", this)` → tests can **override** types without editing the env.
- **`uvm_config_db`:** pass configuration and the **virtual interface** from top module to components.
  ```systemverilog
  uvm_config_db#(virtual mm_bus_if)::set(null, "*", "vif", bus_if);     // in tb_top
  if (!uvm_config_db#(virtual mm_bus_if)::get(this, "", "vif", vif))    // in driver
      `uvm_fatal("NOVIF", "virtual interface not set")
  ```
- **Phases:** `build_phase` → `connect_phase` → `end_of_elaboration` → `start_of_simulation`
  → **`run_phase`** (the only time-consuming task phase) → `extract` → `check` → `report` → `final`.
- **Objections:** `phase.raise_objection(this)` / `drop_objection` — simulation ends when all objections drop.
- **TLM ports:** driver ↔ sequencer via `seq_item_port`; monitor → subscribers via `uvm_analysis_port`.
- **Reporting:** `` `uvm_info(ID, msg, UVM_LOW) ``, `` `uvm_error ``, `` `uvm_fatal ``.

### Driver sketch
```systemverilog
class bus_driver extends uvm_driver #(bus_item);
  `uvm_component_utils(bus_driver)
  virtual mm_bus_if vif;
  function new(string name, uvm_component parent); super.new(name, parent); endfunction

  task run_phase(uvm_phase phase);
    forever begin
      seq_item_port.get_next_item(req);
      vif.cb.bus_valid <= 1;
      vif.cb.bus_write <= req.write;
      vif.cb.bus_addr  <= req.addr;
      vif.cb.bus_wdata <= req.data;
      do @(vif.cb); while (!vif.cb.bus_ready);
      vif.cb.bus_valid <= 0;
      seq_item_port.item_done();
    end
  endtask
endclass
```

### Sequence sketch
```systemverilog
class random_job_seq extends uvm_sequence #(bus_item);
  `uvm_object_utils(random_job_seq)
  rand int unsigned k;
  constraint c_k { k inside {[1:64]}; }
  task body();
    // write CFG_K, write A/B buffers, write CTRL.START, poll STATUS.DONE, read C
  endtask
endclass
```

---

## 26. SystemVerilog for Verification: Classes, Constraints, Coverage, SVA

### Classes & randomization
- OOP: `class`, `extends`, `virtual` methods, `new()`, handles (like pointers).
- `rand` (any value) and `randc` (cycles through all values before repeating).
- Constraints:
  ```systemverilog
  class mm_job;
    rand int unsigned k;
    rand byte a[], b[];
    constraint c_k    { k dist { 1 := 5, [2:63] :/ 80, 64 := 15 }; }   // weighted
    constraint c_size { a.size() == 8 * k; b.size() == k * 8; }
    constraint c_vals { foreach (a[i]) a[i] dist { -128 := 5, 127 := 5, [-127:126] :/ 90 }; }
  endclass
  ```
- `obj.randomize() with { k == 1; }` — inline constraints for a directed-random test.
- `solve a before b` — control the probability distribution.

### Interfaces & clocking blocks
- `interface` bundles signals; `modport` defines directions per user.
- **Clocking block** defines *when* the TB samples and drives relative to the clock → avoids races.
  ```systemverilog
  interface mm_bus_if(input logic clk);
    logic bus_valid, bus_ready, bus_write, bus_rvalid;
    logic [15:0] bus_addr; logic [31:0] bus_wdata, bus_rdata;
    clocking cb @(posedge clk);
      default input #1step output #1;
      output bus_valid, bus_write, bus_addr, bus_wdata;
      input  bus_ready, bus_rvalid, bus_rdata;
    endclocking
  endinterface
  ```

### Functional coverage
```systemverilog
covergroup cg_job with function sample(int k, byte a0);
  cp_k   : coverpoint k  { bins one = {1}; bins small = {[2:7]}; bins mid = {[8:63]}; bins max = {64}; }
  cp_val : coverpoint a0 { bins min = {-128}; bins neg = {[-127:-1]}; bins zero = {0};
                           bins pos = {[1:126]}; bins max = {127}; }
  x_k_val: cross cp_k, cp_val;
endgroup
```
- `bins` = buckets you want to hit; `cross` = combinations; `ignore_bins`/`illegal_bins` exclude values.

### SystemVerilog Assertions (SVA)
- **Immediate:** `assert (x == y) else $error(...)` — checked when executed (procedural).
- **Concurrent:** checked every clock, describe behaviour over time.
  ```systemverilog
  // Once valid is raised, it stays high with stable address until accepted
  a_hold: assert property (@(posedge clk) disable iff (!rst_n)
            bus_valid && !bus_ready |=> bus_valid && $stable(bus_addr));

  // START while idle leads to DONE within K+2N+10 cycles
  a_done: assert property (@(posedge clk) disable iff (!rst_n)
            start && !busy |-> ##[1:MAX_LAT] done);
  ```
- Operators: `|->` (same cycle), `|=>` (next cycle), `##n` (delay), `[*n]` (repeat), `$rose`, `$fell`, `$stable`, `$past`.
- `cover property` counts how often a scenario happened (functional coverage from assertions).

---

## 27. Performance Modeling & HW/SW Correlation

### Why model performance
- Architects decide array size, buffer sizes, bus widths **before RTL exists** using models.
- Later, the model must be **correlated** with RTL/silicon so its predictions can be trusted for the next design.

### Levels in this project
| Level | What predicts cycles | Speed |
|---|---|---|
| Analytical | `K + 2N − 2 + overhead` formula | instant |
| SystemC cycle-approximate | `mm_ca` model, counters | fast |
| RTL simulation | `PERF_*` counters in Verilator/Questa | slow |
| FPGA hardware | same `PERF_*` counters read over UART | real |

### Correlation methodology
1. **Same workloads** everywhere (shared `.hex` vectors, same N/K sweep).
2. **Same metrics** — identical counter definitions (register map §6 of PLAN).
3. Measure all levels, compute **error % = (model − measured) / measured × 100**.
4. Plot model vs measured (should lie on the y = x line). Report mean and max error.
5. Investigate outliers → find the **missing effect** (control overhead, BRAM latency, pipeline bubbles, bus handshakes).
6. **Calibrate** the model (add the missing overhead), then re-run → error shrinks.
7. Keep correlation in the regression so the model doesn't drift as RTL changes.

### Performance counters (hardware side)
- Cheap to add, invaluable for debug and correlation: cycles busy/idle, stalls, events (MACs issued).
- Real SoCs have PMUs (Performance Monitoring Units) for exactly this.

### Functional correlation
- Same inputs → **bit-identical** outputs across NumPy, C++, SystemC, RTL and FPGA.
- Any mismatch is triaged: which model is wrong? (spec ambiguity, model bug, RTL bug).

### Interview questions (verification & modeling)
1. **What is UVM and why use it?** Standard SV class library for reusable, constrained-random, coverage-driven testbenches.
2. **Explain the UVM testbench components.** Test → env → agent (sequencer, driver, monitor) + scoreboard + coverage.
3. **Component vs object?** Components are static (built in build_phase, live whole sim); objects are dynamic (sequence items, sequences).
4. **What are UVM phases? Which consume time?** build, connect, …, run, extract, check, report; only `run_phase` (and its sub-phases) consume time.
5. **What is the factory for?** Creating objects by type so tests can override them without changing the env.
6. **How does the driver get the interface?** Virtual interface passed via `uvm_config_db`.
7. **What are objections?** They keep the run phase alive until all components/sequences finish.
8. **Code vs functional coverage?** Code = what RTL executed; functional = which spec features/scenarios were exercised.
9. **What is DPI-C?** SV ↔ C function calls; used to plug C/C++ reference models into scoreboards.
10. **LT vs AT in TLM-2.0?** LT: blocking `b_transport`, fast, approximate timing; AT: non-blocking 4-phase, models pipelining.
11. **SC_METHOD vs SC_THREAD?** METHOD runs to completion, can't wait; THREAD can `wait()`.
12. **How do you correlate a performance model with RTL?** Same workloads + counters, compute error, find missing effects, calibrate, keep in regression.
13. **`|->` vs `|=>`?** Overlapping (same cycle) vs non-overlapping (next cycle) implication.
14. **How do you know verification is done?** vplan items all tested, functional coverage goals met, code coverage reviewed, regression stable, bug rate near zero.
15. **Your project in one line:** "C++/SystemC models + UVM with DPI-C scoreboard verified my systolic array RTL; SystemC-predicted cycles matched RTL and FPGA counters within X %."

### Glossary (verification)
| Term | Meaning |
|---|---|
| vplan | Verification plan: features → tests → coverage |
| CDV | Coverage-driven verification |
| DUT / TB | Design under test / testbench |
| Scoreboard | Component that checks DUT output against expected |
| DPI-C | SystemVerilog Direct Programming Interface to C |
| SVA | SystemVerilog Assertions |
| TLM | Transaction-Level Modeling |
| LT / AT | Loosely-timed / approximately-timed TLM styles |
| Virtual platform | Software model of a whole SoC that runs real software |
| Co-simulation | Running two models/simulators together on the same stimulus |
| Correlation | Quantifying how closely a model matches RTL / hardware |
| PMU | Performance Monitoring Unit (hardware counters) |
