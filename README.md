# FPGA Systolic Array Matrix-Multiply Accelerator

An N×N output-stationary systolic array (int8 inputs, int32 accumulators) on the
Terasic **DE10-Lite** (Intel MAX 10), driven from Python over UART.

**Status:** Phase 1 (Foundations) — RTL + tests done, passing in simulation; hardware bring-up next.

| Phase | Content | Status |
|---|---|---|
| 1. Foundations | Tool flow, 7-seg, UART TX/RX, FIFO | ✅ simulated, ⏳ hardware |
| 2. Compute engine | PE, N×N array, skew buffers | ⏳ |
| 3. Integration | BRAM buffers, controller FSM, UART protocol, host | ⏳ |
| 4. Hardware & results | Bring-up, 8×8, benchmarks | ⏳ |

## Layout
```
docs/         PLAN.md (4-week plan), NOTES.md (concept notes)
rtl/common/   shared modules: sync_2ff, tick_gen, hex7seg, uart_tx, uart_rx, fifo_sync
foundations/  four warm-up board designs (+ Quartus projects) and a step-by-step README
tb/           cocotb testbenches (pytest)
host/         Python scripts that talk to the board
tools/        gen_quartus.py — generates .qpf/.qsf/.sdc with the DE10-Lite pin table
```

## Quick start (Ubuntu 22.04 or macOS)
```bash
# simulation
sudo apt install iverilog         # macOS: brew install icarus-verilog
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd tb && pytest -v

# build + program (Ubuntu/Windows with Quartus Prime Lite)
cd foundations/04_uart_echo/quartus
quartus_sh --flow compile uart_echo_top
quartus_pgm -m jtag -o "p;output_files/uart_echo_top.sof"
```
Full board instructions: [foundations/README.md](foundations/README.md).
