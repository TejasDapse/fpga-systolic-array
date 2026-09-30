# FPGA Systolic Array Matrix-Multiply Accelerator

An N×N output-stationary systolic array (int8 inputs, int32 accumulators) on the
Terasic **DE10-Lite** (Intel MAX 10), driven from Python over UART.

Planned verification flow (Phases 5–6): C++/SystemC reference models, Verilator
co-simulation and a UVM testbench, with performance correlated across model, RTL and FPGA.

**Status:** Phase 1 (Foundations) — RTL + tests done, passing in simulation; hardware bring-up next.

**Ubuntu build machine:** start with [docs/UBUNTU_HANDOFF.md](docs/UBUNTU_HANDOFF.md).

| Phase | Content | Status |
|---|---|---|
| 1. Foundations | Tool flow, 7-seg, UART TX/RX, FIFO | ✅ simulated, ⏳ hardware |
| 2. Compute engine | PE, N×N array, skew buffers | ⏳ |
| 3. Integration | BRAM buffers, controller FSM, UART protocol, host | ⏳ |
| 4. Hardware & results | Bring-up, 8×8, benchmarks | ⏳ |
| 5. Models & co-sim | C++ bit-accurate model, SystemC/TLM-2.0, Verilator co-simulation | ⏳ |
| 6. UVM & correlation | UVM env + DPI-C scoreboard, coverage, HW↔SW performance correlation | ⏳ |

## Layout
```
docs/         PLAN.md (7-week plan), NOTES.md (concept notes), UBUNTU_HANDOFF.md, results/
rtl/common/   shared modules: sync_2ff, tick_gen, hex7seg, uart_tx, uart_rx, fifo_sync
foundations/  four warm-up board designs (+ Quartus projects) and a step-by-step README
tb/           cocotb testbenches (pytest)
host/         Python scripts that talk to the board
tools/        gen_quartus.py (Quartus files + pin table), setup_ubuntu.sh, build.sh
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
