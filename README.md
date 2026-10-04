# FPGA Systolic Array Matrix-Multiply Accelerator

An N×N output-stationary systolic array (int8 inputs, int32 accumulators) for the
Terasic **DE10-Lite** (Intel MAX 10), driven from Python over UART, plus a
pre-silicon verification flow: C++/SystemC reference models, Verilator
co-simulation, a UVM testbench, and HW/SW performance correlation.

---

## Project status

> **Everything so far runs in simulation only. Nothing has been compiled for or run on the FPGA board yet.**

### ✅ Done (simulation)
- **RTL** for the whole design: processing element, N×N array, skew buffers, block-RAM buffers,
  controller FSM, register bus + performance counters, UART-to-bus bridge, board top level.
  Verified for **(N, K_MAX) = (4, 64), (8, 64), (16, 64), (4, 16), (8, 128)**; illegal parameters stop simulation.
- **cocotb tests** (Icarus 13, 4-state): 37 pass, plus 1 slow N = 8 system test (`SLOW=1`); includes
  **X-propagation checks** (control/bus/board outputs never X after reset).
- **Reference models**: NumPy golden model, bit-accurate C++ model, analytical cycle model,
  SystemC/TLM-2.0 loosely-timed and cycle-approximate models — agree on 3 × 1000 shared vectors (N = 4, 8, 16).
- **Co-simulation**: Verilator `--sc` RTL vs SystemC CA model — 5 configurations × 1000 jobs, 0 result
  mismatches, 0 counter mismatches, 0-cycle timing error.
- **UVM** (on Verilator): 104/104 simulations over 4 configurations, 13 828 jobs, 1.89 M scoreboard checks,
  0 assertion failures, 100 % of the 55 functional-coverage bins in every configuration.
- **RTL code coverage** (Verilator): line 96.9 %, branch 100 %, toggle 90.7 % raw — **100 % after 2 documented
  waivers** (unreachable FSM default, upper bits of 32-bit counters).
- **Mutation checks**: 3 deliberately injected RTL bugs, each caught (one only by the performance counters).
- **Performance correlation**: analytical vs SystemC vs RTL counters vs RTL pins — 0 % error for every K (N = 4, 8, 16).
- **Host software**: `host.py` and `mm_host.cpp`, tested against a software model of the board (`--fake`, pty).
- **Stretch goal — host-side tiling**: `host.py --tile M K P` runs any (M×K)·(K×P) on the N×N array
  (N×N output tiles, K chunks ≤ K_MAX, B tiles reused); tested against NumPy incl. int32 wrap.
- **CI**: GitHub Actions runs the whole simulation flow on every push (`.github/workflows/sim.yml`,
  toolchain pinned in `environment.yml`).
- **Learning material**: concept notes and two slide decks (RTL; models + co-simulation).

### ⏳ Not done yet (needs the board / Quartus)
- **Quartus Prime Lite is not installed** on the build machine yet.
- **No design has been compiled** → no resource usage, Fmax or timing-slack numbers exist yet
  (also unknown: whether N = 16 fits — 256 multipliers needed vs 144 18×18 / 288 9×9 on the MAX 10).
- **Pin assignments are unverified** — written from the DE10-Lite manual, not yet checked against
  Terasic's System Builder.
- **The board has never been programmed**: Phase 1 warm-up designs and the UART echo test are untested on hardware.
- **Phase 4 (hardware bring-up, benchmarks on the board)** not started.
- **FPGA column of the performance correlation** is empty ("pending") until the board runs.
- Stretch goals not done: double buffering (no benefit over UART: load ≈ 89 ms vs compute ≈ 1.6 µs),
  higher clock via PLL (needs Quartus timing).

### ⚠️ Limitations to be aware of
- **All performance numbers are from simulation** (e.g. 81 % PE utilisation and 5.1 GOPS for N = 8, K = 64
  assume a 50 MHz clock; real Fmax is unknown until Quartus runs).
- **UVM runs on Verilator, not a commercial simulator** (Questa/VCS/Xcelium). Because of Verilator 5.052 limits:
  - functional coverage is an explicit-bin collector with covergroup-like structure, **not native SystemVerilog covergroups**;
  - `dist` constraints are worked around; DPI uses fixed-size arrays (N·K_MAX ≤ 1024);
  - Verilator is **2-state**; X-propagation is checked only in the 4-state Icarus/cocotb tests.
- No gate-level (post-synthesis) simulation — needs a Quartus netlist.
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
# toolchain (no sudo): Icarus, Verilator, SystemC, z3 + Python packages
conda env create -f environment.yml && conda activate fpga
git clone --depth 1 https://github.com/accellera-official/uvm-core ~/tools/uvm-core   # for UVM

# simulation + verification flow (what CI runs)
(cd tb && pytest -q)           # cocotb (SLOW=1 adds the N=8 system sim)
python3 model/vectors.py && make -C model/cpp test && make -C model/systemc test
make -C cosim                  # Verilator RTL vs SystemC cycle-approximate model, 5 configurations
python3 uvm/regress.py         # UVM regression + merged functional coverage
python3 uvm/code_coverage.py   # RTL line / branch / toggle coverage
python3 tools/correlate.py     # analytical vs SystemC vs RTL (vs FPGA once measured)
python3 host/host.py --fake --tile 64 200 48   # tiled multiply on the software board

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
