# Systolic Array Matrix-Multiply Accelerator — Project Plan

**Board:** Terasic DE10-Lite (Intel MAX 10, 10M50DAF484C7G, 50 MHz clock)
**Duration:** 4 weeks (28 days) at ~2–3 hrs/day (~65 hrs total)
**Companion notes:** [NOTES.md](NOTES.md) — read the listed sections *before* each day's work.

---

## 1. Project Goal

Build a hardware accelerator on the FPGA that computes **C = A × B** using a
systolic array, driven from a Python script on your Mac over UART.

```
  Mac (Python)                          DE10-Lite FPGA
 ┌──────────────┐   UART 115200   ┌──────────────────────────────────────────┐
 │ host.py      │ ──────────────▶ │ UART RX → Cmd Parser → A/B Buffers (M9K) │
 │ - random A,B │                 │                          │               │
 │ - send/recv  │                 │                    Skew Buffers          │
 │ - compare    │                 │                          ▼               │
 │   w/ numpy   │                 │              N×N Systolic Array (PEs)    │
 │ - timing     │ ◀────────────── │ UART TX ← Result Buffer ← Drain logic    │
 └──────────────┘                 │ Controller FSM + Cycle Counter → HEX/LED │
                                  └──────────────────────────────────────────┘
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
| Host link | UART 8N1 @ 115200 baud via a USB-to-UART adapter (3.3 V) on GPIO |
| Status display | HEX0–HEX5 = compute cycle count; LEDR = FSM state / errors |
| Verification | cocotb + Icarus/Verilator on Mac, NumPy golden model |

### Deliverables (what goes on your resume / GitHub)
1. Parameterized, verified RTL (SystemVerilog)
2. Self-checking testbenches with random tests (1000+ random matrices pass)
3. Working hardware demo: Python → FPGA → correct results
4. Results table: resources (LEs, multipliers, M9K), Fmax, cycles, GOPS, utilization
5. README with block diagram, dataflow diagram and performance analysis

---

## 2. Before Day 1 — Setup Checklist

### Buy
- [ ] USB-to-UART adapter, **3.3 V** logic (CP2102 or FT232RL), ~₹200–300
- [ ] 3–4 female-to-female jumper wires

### Mac (write code + simulate)
- [ ] `brew install icarus-verilog verilator gtkwave`
- [ ] `python3 -m venv ~/fpga-venv && source ~/fpga-venv/bin/activate`
- [ ] `pip install cocotb numpy pyserial matplotlib pytest`
- [ ] Editor: VS Code + "Verilog-HDL/SystemVerilog" extension

### Windows/Linux PC (synthesize + program)
- [ ] Install **Quartus Prime Lite** (free) + **MAX 10 device support**
- [ ] Install USB-Blaster driver (bundled with Quartus)
- [ ] Download the **DE10-Lite CD** from Terasic (System Builder, user manual, pin list)
- [ ] Plug in board → Quartus Programmer → "Hardware Setup" should list *USB-Blaster*

> Workflow: code & simulate on Mac → copy/sync (Git or USB drive) → compile & program on PC.

---

## 3. Project Directory Structure

```
Systolic_Array/
├── docs/
│   ├── PLAN.md              ← this file
│   ├── NOTES.md             ← concept notes
│   └── results/             ← screenshots, plots, reports
├── foundations/             ← Week 1 warm-up designs
│   ├── 01_switch_led/
│   ├── 02_blinky/
│   ├── 03_hex_counter/
│   └── 04_uart_echo/
├── rtl/
│   ├── common/   sync_2ff.sv, hex7seg.sv, uart_rx.sv, uart_tx.sv
│   ├── core/     pe.sv, systolic_array.sv, skew_buffer.sv, sram_sp.sv, mm_controller.sv, mm_core.sv
│   └── top/      cmd_parser.sv, top_de10lite.sv
├── tb/                      ← cocotb tests + Makefiles
├── model/                   golden_model.py (NumPy reference)
├── host/                    host.py (pyserial driver + benchmarks)
└── quartus/                 systolic.qpf, systolic.qsf (pins), systolic.sdc (timing)
```

---

## 4. Week-by-Week Plan

### WEEK 1 — Foundations: Tools, Verilog, Board, UART
**Goal:** Become comfortable with the full flow and build a working UART (reused later).
**Read first:** NOTES §1–§8, §10–§11

| Day | Task | Done when… |
|---|---|---|
| 1 | Complete setup checklist. Read NOTES §1–§4 (FPGA basics, board, flow). | Quartus sees USB-Blaster; `iverilog -V` works on Mac |
| 2 | Read NOTES §5–§6 (Verilog, comb vs seq). Write & simulate a mux, adder, 4-bit counter in Icarus; view in GTKWave. | You can explain `=` vs `<=` |
| 3 | **Project 01 – switches → LEDs.** Generate pin file with System Builder, compile, program `.sof`. | Flipping SW[i] lights LEDR[i] |
| 4 | **Project 02 – blinky** (counter + clock-enable tick). **Project 03 – hex counter** (hex7seg decoder on HEX0–HEX3). | LED blinks at 1 Hz; HEX counts up |
| 5 | Read NOTES §7–§8 (timing, FSMs). Add 2-FF synchronizer for KEY; build a small FSM (e.g., KEY0 = start/stop counter). Check Timing Analyzer report. | Slack ≥ 0; you can explain metastability |
| 6 | Read NOTES §10 (UART). Write `uart_tx.sv`, simulate, then send "HELLO\r\n" from FPGA every second. Wire adapter; view on Mac with `screen /dev/tty.usbserial-XXXX 115200`. | "HELLO" appears on Mac |
| 7 | Write `uart_rx.sv` (16× oversampling). **Project 04 – UART echo.** Test with a Python pyserial loopback script sending 10,000 random bytes. | 0 byte errors |

**Week 1 checkpoint — you should be able to answer:**
- What is a LUT? What is inside an FPGA?
- Blocking vs non-blocking assignment — why does it matter?
- What is setup time / slack / Fmax?
- Why do we synchronize asynchronous inputs? What is metastability?
- How does a UART receiver find the middle of a bit?

---

### WEEK 2 — The Compute Engine (mostly simulation on Mac)
**Goal:** A verified, parameterized N×N systolic array.
**Read first:** NOTES §12–§15

| Day | Task | Done when… |
|---|---|---|
| 8 | Read NOTES §12–§14. **On paper:** trace a 2×2 × K=2 example cycle by cycle (fill the table in NOTES §14). | You can predict which PE multiplies what at each cycle |
| 9 | Write `pe.sv` (MAC with pass-through registers, `clear`, `en`). cocotb test: 1,000 random signed int8 pairs incl. −128×−128. | PE test passes |
| 10 | Write `systolic_array.sv` for 2×2 using `generate`. Testbench drives *already-skewed* inputs manually. Study waveform. | 2×2 result matches NumPy |
| 11 | Write `skew_buffer.sv` (row i delayed by i cycles — triangular shift registers). Parameterize array to N. | 4×4 passes with un-skewed inputs |
| 12 | Write `model/golden_model.py`. Random tests: N=4 and 8, random K ∈ [1, 64], edge cases (all −128, all 127, zeros, identity). | 500+ random tests pass |
| 13 | **Synthesis-only check** on PC: compile array for N=4 and N=8. Record LEs, embedded multipliers, Fmax in `docs/results/`. | Fmax > 50 MHz for N=8 |
| 14 | Buffer / catch-up day. Review NOTES §13 dataflows; write 1-page explanation in your own words. | Checkpoint questions answered |

**Week 2 checkpoint:**
- Why is it called "systolic"? Why is it efficient?
- Output-stationary vs weight-stationary — trade-offs?
- Why must inputs be skewed? What does the skew buffer look like?
- How many cycles does an N×N array take for K-length dot products? (K + 2N − 2)
- Why is the accumulator 32 bits when inputs are 8 bits?

---

### WEEK 3 — System Integration: Memory, Control, UART Protocol, Host
**Goal:** Complete design passing full-system simulation + Python host ready.
**Read first:** NOTES §9, §8 (again), §16

| Day | Task | Done when… |
|---|---|---|
| 15 | Write `sram_sp.sv` (inferred M9K RAM, 1-cycle read latency). Instantiate A-buffer (N×K bytes), B-buffer (K×N bytes). Test write-then-read. | Quartus infers M9K (check report) |
| 16 | Write `mm_controller.sv` FSM: `IDLE → CLEAR → COMPUTE → DRAIN → DONE`, plus 32-bit **cycle counter**. | FSM waveform matches your state diagram |
| 17 | Write `mm_core.sv` = buffers + skew + array + controller + result readout. End-to-end sim: preload memories, pulse `start`, check C. | 200 random tests pass |
| 18 | Write `cmd_parser.sv` implementing the **UART protocol** (see §5 below). | Unit test of each command passes |
| 19 | Write `top_de10lite.sv` (clock, reset, UART pins, HEX shows cycle count, LEDs show state). Full-system sim with a cocotb UART driver (use a fast baud parameter in sim). | One matrix multiply works through UART in sim |
| 20 | Write `host/host.py`: open port, send K, A, B, GO, read C + cycle count, compare with NumPy, print PASS/FAIL. | Script runs (hardware test next week) |
| 21 | Buffer day. Clean code, add comments, commit to Git. | Everything committed |

**Week 3 checkpoint:**
- How is Block RAM different from registers? Why the 1-cycle read latency?
- Draw your controller FSM from memory.
- Where is your critical path likely to be?

---

### WEEK 4 — Hardware Bring-up, Scaling, Measurement, Documentation
**Goal:** Working demo on the board with measured results.
**Read first:** NOTES §16–§18

| Day | Task | Done when… |
|---|---|---|
| 22 | Create final Quartus project: `.qsf` pins (incl. GPIO UART pins), `.sdc` (50 MHz). Compile N=4. Fix any timing violations. Program board. | Slack ≥ 0, board programmed |
| 23 | Run `host.py` on hardware for N=4. If failing → SignalTap on UART RX/cmd parser/FSM state. | 100 random hardware tests pass |
| 24 | Scale to **N=8**. Recompile, re-verify in sim and on hardware. (Optional: try N=16.) | 1,000 hardware tests pass |
| 25 | **Benchmarks:** compute cycles vs K; utilization = K/(K+2N−2); GOPS at 50 MHz; UART transfer time vs compute time; compare vs NumPy on Mac. Make plots with matplotlib. | Results table + 2 plots |
| 26 | **Stretch (pick one):** (a) host-side tiling for 32×32 / 64×64 matrices, (b) double buffering (load next B while computing), (c) raise Fmax with a PLL + extra pipelining. | Stretch feature works |
| 27 | Write `README.md`: overview, block diagram, dataflow, how to run, results, lessons learned. Record a short demo video. | README complete |
| 28 | **Interview prep:** go through NOTES §18 questions out loud; explain the project in 2 minutes and in 10 minutes. | You can whiteboard the whole design |

---

## 5. UART Command Protocol (host ↔ FPGA)

All multi-byte values are little-endian.

| Command | Byte sent | Payload (host → FPGA) | Response (FPGA → host) |
|---|---|---|---|
| Ping | `'P'` (0x50) | — | `'K'` + N (1 byte) + K_MAX (1 byte) |
| Set K | `'S'` | K (1 byte) | `'K'` |
| Load A | `'A'` | N×K int8, row-major | `'K'` |
| Load B | `'B'` | K×N int8, row-major | `'K'` |
| Go | `'G'` | — | `'D'` when done |
| Read C | `'R'` | — | N×N int32 (row-major), 4 bytes each |
| Read cycles | `'C'` | — | 4-byte cycle count |

Unknown command → FPGA replies `'E'` and lights an error LED.

---

## 6. Expected Results (sanity targets)

| Metric | Expected (N=8, K=64, 50 MHz) |
|---|---|
| Compute cycles | ≈ K + 2N − 2 = **78** (+ a few control cycles) |
| Peak throughput | 64 MACs/cycle × 50 MHz = **3.2 GMAC/s = 6.4 GOPS** |
| Array utilization | 64 / 78 ≈ **82 %** |
| Embedded multipliers | ~64 (of 144 available) |
| UART time for A + B | 1,024 bytes ÷ 11,520 B/s ≈ **89 ms** vs compute ≈ **1.6 µs** |

> The last row is a key insight for interviews: the design is **I/O-bound**, not
> compute-bound. This is why real accelerators use high-bandwidth memory and
> data reuse (see NOTES §16 Roofline).

---

## 7. Risk List & Mitigations

| Risk | Mitigation |
|---|---|
| No Quartus on Mac | Do all simulation on Mac; only compile/program on the PC |
| UART garbage characters | Check baud divider (50 MHz / 115200 ≈ 434), common GND, TX↔RX crossed, 3.3 V jumper |
| Off-by-one in skew / timing | Trace the 2×2 table on paper (Day 8); compare waveforms cycle by cycle |
| Signed arithmetic wrong | Declare `logic signed`, use `$signed()`, test −128×−128 and −128×127 |
| Timing failure at N=8/16 | Register multiplier output (2-stage PE), reduce N, check critical path in Timing Analyzer |
| Works in sim, fails on HW | Missing synchronizer, uninitialized regs, reset polarity (KEY is active-low) → use SignalTap |

---

## 8. Progress Tracker

- [ ] Week 1 — Foundations complete (UART echo works)
- [ ] Week 2 — N×N array verified in simulation
- [ ] Week 3 — Full system verified in simulation + host script ready
- [ ] Week 4 — Hardware demo, benchmarks, README done
