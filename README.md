# FPGA Systolic Array Matrix-Multiply Accelerator

An N×N output-stationary systolic array (int8 inputs, int32 accumulators) on the
Terasic **DE10-Lite** (Intel MAX 10), driven from Python over UART.

Planned verification flow (Phases 5–6): C++/SystemC reference models, Verilator
co-simulation and a UVM testbench, with performance correlated across model, RTL and FPGA.

**Status:** all simulation work done — RTL (Phases 1–3), C++/SystemC models + Verilator co-simulation (Phase 5), UVM with 100 % functional coverage (Phase 6). Hardware bring-up (Phase 4) and the FPGA column of the performance correlation are next. Summary: [docs/results/verification_report.md](docs/results/verification_report.md).

**Ubuntu build machine:** start with [docs/UBUNTU_HANDOFF.md](docs/UBUNTU_HANDOFF.md).

| Phase | Content | Status |
|---|---|---|
| 1. Foundations | Tool flow, 7-seg, UART TX/RX, FIFO | ✅ simulated, ⏳ hardware |
| 2. Compute engine | PE, N×N array, skew buffers | ✅ simulated |
| 3. Integration | BRAM buffers, controller FSM, register bus + perf counters, UART bridge, host | ✅ simulated, ⏳ hardware |
| 4. Hardware & results | Bring-up, 8×8, benchmarks | ⏳ |
| 5. Models & co-sim | C++ bit-accurate model, SystemC/TLM-2.0, Verilator co-simulation | ✅ [results](docs/results/phase5_models.md) |
| 6. UVM & correlation | UVM env + DPI-C scoreboard, coverage, HW↔SW performance correlation | ✅ simulated ([regression](docs/results/uvm_regression.md), [correlation](docs/results/correlation.md)), ⏳ FPGA column |

## Layout
```
docs/         PLAN.md (7-week plan), NOTES.md (concept notes), vplan.md, UBUNTU_HANDOFF.md, results/
rtl/common/   shared modules: sync_2ff, tick_gen, hex7seg, uart_tx, uart_rx, fifo_sync
rtl/core/     pe, systolic_array, skew_buffer, sram_sp, mm_controller, mm_regs, mm_core
rtl/top/      uart_bus_bridge, top_de10lite
quartus/      accelerator Quartus project (generated)
foundations/  four warm-up board designs (+ Quartus projects) and a step-by-step README
model/        golden_model.py, regmap.py, vectors.py (shared test vectors)
  cpp/        bit-accurate C++ model + analytical perf model
  systemc/    TLM-2.0 loosely-timed + cycle-approximate models
cosim/        Verilator (--sc) RTL vs SystemC co-simulation
uvm/          UVM env (agent, DPI-C scoreboard, coverage, SVA) on Verilator; regress.py
tb/           cocotb testbenches (pytest; SLOW=1 adds the N=8 full-system sim)
host/         host.py (tests + benchmarks, --fake = no board), mm_host.cpp (C++ host), fake_serial.py, uart_echo_test.py
tools/        gen_quartus.py (Quartus files + pin table), setup_ubuntu.sh, build.sh, correlate.py
```

## Quick start (Ubuntu 22.04 or macOS)
```bash
# simulation
sudo apt install iverilog         # macOS: brew install icarus-verilog
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd tb && pytest -v

# build + program (Quartus Prime Lite in PATH)
tools/build.sh 04_uart_echo --program       # Phase 1 designs
tools/build.sh quartus --program            # the accelerator
python host/host.py --tests 100             # run on the board (--fake: no board)
```
Verification flow (simulation only, see [docs/results/verification_report.md](docs/results/verification_report.md)):
```bash
python3 model/vectors.py && make -C model/cpp test && make -C model/systemc test
make -C cosim                  # Verilator RTL vs SystemC cycle-approximate model
python3 uvm/regress.py         # UVM regression + merged coverage
python3 tools/correlate.py     # analytical vs SystemC vs RTL (vs FPGA)
```
Board instructions: [foundations/README.md](foundations/README.md) (Phase 1) and
[docs/UBUNTU_HANDOFF.md](docs/UBUNTU_HANDOFF.md) §4 Task 6 (accelerator).
