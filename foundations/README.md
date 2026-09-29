# Phase 1 — Foundations (Week 1)

Four small designs that teach the whole flow and build the UART reused by the
systolic array. Read NOTES §1–§8, §10–§11 alongside.

| # | Design | Teaches | Day |
|---|---|---|---|
| 01 | `switch_led_top` | Pins, compile, program | 3 |
| 02 | `blinky_top` | Counters, clock enable, reset | 4 |
| 03 | `hex_counter_top` | 7-segment decoding, button edges, FSM | 4–5 |
| 04 | `uart_echo_top` | UART TX/RX, FIFO, talking to the Mac | 6–7 |

Shared building blocks live in `rtl/common/`:
`sync_2ff.sv`, `tick_gen.sv`, `hex7seg.sv`, `uart_tx.sv`, `uart_rx.sv`, `fifo_sync.sv`.

---

## Step 1 — Mac: install simulation tools (one time)

```bash
brew install icarus-verilog
cd Systolic_Array
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional waveform viewer: `brew install --cask gtkwave` (or the Surfer viewer).

## Step 2 — Mac: run all simulations

```bash
source .venv/bin/activate
cd tb
pytest -v                        # all tests
pytest -v test_uart_rx.py        # just one
WAVES=1 pytest test_uart_tx.py   # also dump waveforms to tb/sim_build/uart_tx/
```

Every test prints PASS/FAIL by itself. **Only go to the board once everything passes.**

| Test file | What it checks |
|---|---|
| `test_hex7seg.py` | All 16 digits give the right segments |
| `test_uart_tx.py` | Idle high, random bytes decode correctly, `ready` low while busy |
| `test_uart_rx.py` | Exact baud, ±3 % baud error, framing-error detection |
| `test_fifo_sync.py` | 3,000 random cycles vs. a Python deque, full/empty flags |
| `test_top_01..04_*.py` | Each board design end to end |

## Step 3 — PC: Quartus setup (one time)

1. Install **Quartus Prime Lite** + **MAX 10 device support** (includes the USB-Blaster driver).
2. Copy the whole `Systolic_Array` folder to the PC (Git or USB drive).
3. **Check the pins once:** download the *DE10-Lite CD* from Terasic, run
   *DE10-Lite System Builder*, tick CLOCK, LED, Button, Switch, 7-Segment, and
   generate. Compare its `.qsf` pin numbers with `tools/gen_quartus.py`. If any
   differ, fix `gen_quartus.py` and re-run `python tools/gen_quartus.py`.

## Step 4 — PC: compile and program (every design)

1. Quartus → **File → Open Project** → `foundations/<nn_name>/quartus/<name>.qpf`
2. **Processing → Start Compilation** (Ctrl+L). Wait for "Full Compilation was successful".
3. Check timing: **Tools → Timing Analyzer** → *Report Fmax Summary*: Fmax must be **> 50 MHz**.
4. Plug the board into USB. **Tools → Programmer** → *Hardware Setup* → select **USB-Blaster**.
5. *Mode: JTAG* → **Add File** → `output_files/<name>.sof` → tick *Program/Configure* → **Start**.
6. Progress bar reaches 100% → the design is running.

`.sof` is lost when power is removed. That's fine for development.

## Step 5 — Check each design on the board

**01 switch_led:** flip any SW → the LED above it lights.

**02 blinky:** LEDR0 blinks once per second, LEDR9..1 count in binary. Hold KEY0 → reset.

**03 hex_counter:** HEX displays count up in hex at 10 per second. KEY1 pauses/resumes
(LEDR0 = running). Hold KEY0 → back to 000000.

**04 uart_echo:** needs the USB-UART adapter:

```
 DE10-Lite GPIO header (JP1)            USB-UART adapter (set to 3.3 V!)
   pin 1  GPIO[0]  UART_TXD  ───────────▶  RXD
   pin 2  GPIO[1]  UART_RXD  ◀───────────  TXD
   pin 12 GND                ────────────  GND
                                           (leave VCC / 5V unconnected)
```

Then on the Mac:

```bash
ls /dev/tty.*                                   # find the adapter, e.g. /dev/tty.usbserial-0001
screen /dev/tty.usbserial-0001 115200           # type -> characters echo back (quit: Ctrl-A, K)
python host/uart_echo_test.py --count 10000     # automated test -> expect "0 errors, PASS"
```

On the board: HEX1:HEX0 = last byte (hex), HEX5..HEX2 = bytes received,
LEDR9 = heartbeat, LEDR0/LEDR1 = error flags (should stay off).

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Programmer shows "No Hardware" | USB-Blaster driver installed? Try another USB cable/port |
| Nothing happens after programming | Pins wrong (step 3), or KEY0 held (it's the reset) |
| HEX shows garbage segments | HEX pin order wrong in the `.qsf` |
| Timing Analyzer: negative slack | Tell me the failing path from the report |
| No echo at all | TX/RX swapped? GND connected? Right design loaded? |
| Garbage characters | Adapter set to 5 V, or baud mismatch in the terminal |
| LEDR0 lights (framing error) | Loose wire or noisy ground |

## Week 1 checkpoint

Before starting Phase 2, answer these without looking (answers are in NOTES §18):
- What is inside an FPGA? What is a LUT?
- `=` vs `<=`: when do you use each, and why?
- Why does `tick_gen` produce an enable instead of a slow clock?
- What is metastability, and where does this design use a synchronizer?
- How does `uart_rx` find the middle of each bit?
- Why does the echo design need a FIFO?
