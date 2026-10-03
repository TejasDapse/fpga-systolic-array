# FPGA Systolic Array Matrix-Multiply Accelerator

An N×N output-stationary systolic array (int8 inputs, int32 accumulators) for the
Terasic **DE10-Lite** (Intel MAX 10), driven from Python over UART, plus a
pre-silicon verification flow: C++/SystemC reference models, Verilator
co-simulation, a UVM testbench, and HW/SW performance correlation.

---

## Project status — honest summary (updated 2026-10-03)

> **Everything so far runs in simulation only. Nothing has been compiled for or run on the FPGA board yet.**

### ✅ Done (simulation)
- **RTL** for the whole design: processing element, N×N array, skew buffers, block-RAM buffers,
  controller FSM, register bus + performance counters, UART-to-bus bridge, board top level.
- **cocotb tests** (Icarus 13): 19 pass, plus 1 slow N = 8 system test (`SLOW=1`).
- **Reference models**: NumPy golden model, bit-accurate C++ model, analytical cycle model,
  SystemC/TLM-2.0 loosely-timed and cycle-approximate models — agree on 2 × 1000 shared vectors.
- **Co-simulation**: Verilator `--sc` RTL vs SystemC CA model — 2 × 1000 jobs, 0 result mismatches,
  0 counter mismatches, 0-cycle timing error.
- **UVM** (on Verilator): 52/52 simulations, 6 914 jobs, 476 k scoreboard checks, 0 assertion failures,
  100 % of the 55 defined functional-coverage bins (N = 4 and 8).
- **Mutation checks**: 3 deliberately injected RTL bugs, each caught (one only by the performance counters).
- **Performance correlation**: analytical vs SystemC vs RTL counters vs RTL pins — 0 % error for every K.
- **Host software**: `host.py` and `mm_host.cpp`, tested against a software model of the board (`--fake`, pty).
- **Learning material**: concept notes and two slide decks (RTL; models + co-simulation).

### ⏳ Not done yet (needs the board / Quartus)
- **Quartus Prime Lite is not installed** on the build machine yet.
- **No design has been compiled** → no resource usage, Fmax or timing-slack numbers exist yet.
- **Pin assignments are unverified** — written from the DE10-Lite manual, not yet checked against
  Terasic's System Builder.
- **The board has never been programmed**: Phase 1 warm-up designs and the UART echo test are untested on hardware.
- **Phase 4 (hardware bring-up, benchmarks on the board)** not started.
- **FPGA column of the performance correlation** is empty ("pending") until the board runs.
- Stretch goals not started: host-side tiling for larger matrices, double buffering, 16×16 array, higher clock via PLL.

### ⚠️ Limitations to be aware of
- **All performance numbers are from simulation** (e.g. 81 % PE utilisation and 5.1 GOPS for N = 8, K = 64
  assume a 50 MHz clock; real Fmax is unknown until Quartus runs).
- **UVM runs on Verilator, not a commercial simulator** (Questa/VCS/Xcelium). Because of Verilator 5.052 limits:
  - functional coverage is an explicit-bin collector with covergroup-like structure, **not native SystemVerilog covergroups**;
  - `dist` constraints are worked around; DPI uses fixed-size arrays (N ≤ 16, K_MAX ≤ 64);
  - Verilator is **2-state**, so X-propagation is not checked.
- The SystemC cycle-approximate model does not model the datapath pipeline or RAM timing; `PERF_IDLE`
  (depends on host polling) is excluded from comparisons.

Details: [docs/results/verification_report.md](docs/results/verification_report.md) ·
plan and tracker: [docs/PLAN.md](docs/PLAN.md) · hardware to-do list: [docs/UBUNTU_HANDOFF.md](docs/UBUNTU_HANDOFF.md).

---

## Phases

| Phase | Content | Simulation | Hardware |
|---|---|---|---|
| 1. Foundations | Tool flow, 7-seg, UART TX/RX, FIFO | ✅ | ⏳ not run on board |
| 2. Compute engine | PE, N×N array, skew buffers | ✅ (N = 2, 4, 8) | ⏳ |
| 3. Integration | BRAM buffers, controller FSM, register bus + perf counters, UART bridge, host | ✅ (N = 4, 8, over UART) | ⏳ |
| 4. Hardware & results | Quartus compile, bring-up, 8×8 on board, benchmarks | — | ⏳ **not started** |
| 5. Models & co-sim | C++ bit-accurate model, SystemC/TLM-2.0, Verilator co-simulation | ✅ [results](docs/results/phase5_models.md) | n/a |
| 6. UVM & correlation | UVM env + DPI-C scoreboard, coverage, SVA, HW↔SW correlation | ✅ [regression](docs/results/uvm_regression.md), [correlation](docs/results/correlation.md) | ⏳ FPGA column pending |

## Results at a glance (simulation)

| Check | Result |
|---|---|
| cocotb unit + system tests | 19 pass (+1 slow) |
| C++ model vs NumPy | 2000 / 2000 vectors match |
| SystemC LT and CA models vs expected | 0 mismatches; CA cycle error 0 |
| Verilator co-sim, RTL vs SystemC CA | 2 × 1000 jobs: 0 C / 0 counter mismatches, 0-cycle error |
| UVM regression | 52 / 52 sims, 476 k checks, 100 % of 55 coverage bins, 0 SVA failures |
| Correlation (analytical / SystemC / RTL) | 0 % error for all K, N = 4 and 8 |
| Correlation (FPGA) | **pending — board not run yet** |

## Layout
```
docs/         PLAN.md (plan + tracker), NOTES.md (concept notes), vplan.md, UBUNTU_HANDOFF.md
  results/    phase5_models, uvm_regression, correlation, verification_report, CSVs, plots,
              phase1_hw.md (empty template — hardware not run yet)
  slides/     01_rtl_overview/, 02_models_cosim/ (LaTeX, PDF, PPTX + generators), slide_kit.py
rtl/common/   shared modules: sync_2ff, tick_gen, hex7seg, uart_tx, uart_rx, fifo_sync
rtl/core/     pe, systolic_array, skew_buffer, sram_sp, mm_controller, mm_regs, mm_core
rtl/top/      uart_bus_bridge, top_de10lite
quartus/      accelerator Quartus project (generated, never compiled yet)
foundations/  four warm-up board designs (+ Quartus projects) and a step-by-step README
model/        golden_model.py, regmap.py, vectors.py (shared test vectors)
  cpp/        bit-accurate C++ model + analytical perf model
  systemc/    TLM-2.0 loosely-timed + cycle-approximate models
cosim/        Verilator (--sc) RTL vs SystemC co-simulation
uvm/          UVM env (agent, DPI-C scoreboard, coverage, SVA) on Verilator; regress.py
tb/           cocotb testbenches (pytest; SLOW=1 adds the N=8 full-system sim)
host/         host.py (tests + benchmarks, --fake = no board), mm_host.cpp, fake_serial.py, uart_echo_test.py
tools/        gen_quartus.py (Quartus files + pin table), setup_ubuntu.sh, build.sh, correlate.py
```

## Quick start (Ubuntu 22.04)
```bash
# simulation
sudo apt install iverilog
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd tb && pytest -v

# verification flow (simulation only; tools in the `fpga` conda env, see docs/UBUNTU_HANDOFF.md)
python3 model/vectors.py && make -C model/cpp test && make -C model/systemc test
make -C cosim                  # Verilator RTL vs SystemC cycle-approximate model
python3 uvm/regress.py         # UVM regression + merged coverage
python3 tools/correlate.py     # analytical vs SystemC vs RTL (vs FPGA once measured)

# hardware (NOT done yet — needs Quartus Prime Lite in PATH and the board)
tools/build.sh 04_uart_echo --program       # Phase 1 designs
tools/build.sh quartus --program            # the accelerator
python host/host.py --tests 100             # run on the board (--fake: no board)
```
Board instructions: [foundations/README.md](foundations/README.md) (Phase 1) and
[docs/UBUNTU_HANDOFF.md](docs/UBUNTU_HANDOFF.md) §4 (accelerator).

## Next steps
1. Install Quartus Prime Lite + MAX 10 support on the Ubuntu machine.
2. Verify pins against Terasic System Builder; compile all designs; record resources, Fmax, slack.
3. Program the board: Phase 1 designs, UART echo test, then the accelerator (N = 4, then 8).
4. Run `host/mm_host --csv docs/results/fpga_perf_n{4,8}.csv` and `tools/correlate.py` to fill the FPGA column.
5. Update this status section with the real hardware numbers.
