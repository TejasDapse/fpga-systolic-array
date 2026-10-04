# Tools — what is installed, what needs a login, what needs a licence

Status as of 2026-10-05 on the Ubuntu 22.04 build machine. Everything in section 1 runs without sudo:
conda env `fpga` (`conda env create -f environment.yml`) plus a few binaries in `~/tools`.

## 1. Installed and used in this repo

| Tool | Version | Industry role | Command in this repo |
|---|---|---|---|
| Icarus Verilog | 13.0 | 4-state event-driven simulator (cf. VCS / Xcelium / Questa) | `cd tb && pytest -q` |
| cocotb | 2.1.0 | Python testbenches | `cd tb && pytest -q` |
| Verilator | 5.052 | fast 2-state cycle simulator; lint; code coverage; SystemC export | `make -C cosim`, `tools/lint.sh` |
| Accellera UVM (uvm-core) | IEEE 1800.2 2020.3.1 (git 78c0654) | UVM base-class library | `python3 uvm/regress.py` |
| Z3 | 5.1.0 | SMT solver: `randomize()` in Verilator, formal engine | (used automatically) |
| SystemC + TLM-2.0 | 3.0.2 | transaction-level / cycle-approximate models (cf. Platform Architect, Virtualizer) | `make -C model/systemc test` |
| Yosys | 0.69 | open-source synthesis (cf. Quartus/DC front-end) — pre-Quartus estimate | `tools/synth_estimate.sh` |
| SymbiYosys (sby) | git b1a1e98 (2026-08-04) | formal verification (cf. JasperGold, VC Formal, Questa Formal) | `make -C formal` |
| sv2v | 0.0.13 | SystemVerilog → Verilog-2005 (feeds Yosys) | used by the two lines above |
| Verible | 0.0-3667 | SystemVerilog style lint / formatter (cf. SpyGlass lint, Questa Lint) | `tools/lint.sh` |
| GTKWave | 3.3.121 | waveform viewer (cf. Verdi, SimVision, Visualizer) | `gtkwave <file>.vcd` (`WAVES=1 pytest ...`, formal counterexamples) |
| g++ (system) | 11.4.0 | C++ for models, DPI-C, host | all Makefiles |
| Python libs | numpy 2.5, matplotlib 3.11, pyserial 3.5, pytest 9.1, click, PyYAML | models, plots, UART host | — |

What each one produced: see [results/verification_report.md](results/verification_report.md)
(formal proof, lint, synthesis estimate are in sections 9–10).

## 2. Free, but needs your browser / account (cannot be scripted)

| Tool | Why | How |
|---|---|---|
| **Quartus Prime Lite (latest Lite release) + MAX 10 device file** | **required** — compile, timing (Fmax/slack), SignalTap, program the board | Intel FPGA Download Center → Lite → Linux; [UBUNTU_HANDOFF.md](UBUNTU_HANDOFF.md) §2 |
| **Questa – Intel FPGA Starter Edition** | a commercial simulator: native covergroups, the UVM env on Questa | tick it in the same Quartus installer; free licence from the Intel FPGA Self-Service Licensing Center (tied to the PC's NIC/MAC address) |
| **EDA Playground** (edaplayground.com) | runs **Synopsys VCS, Cadence Xcelium, Siemens Questa, Aldec Riviera-PRO** in the browser | free account (sign in with Google/GitHub); paste design + testbench; pick "UVM 1.2" |
| AMD Vivado ML Standard (optional) | the other big FPGA vendor flow — not needed for the DE10-Lite (Intel) | AMD account; ~100 GB |

## 3. Commercial, licensed — cannot be installed here

These are sold under per-seat licences with a licence server; there is no public download.
Access comes through a university programme or an employer.

| Industry tool | Vendor | Category | What we use instead |
|---|---|---|---|
| VCS | Synopsys | simulator | Icarus, Verilator |
| Xcelium | Cadence | simulator | Icarus, Verilator |
| Questa (full) | Siemens | simulator | Questa Starter (§2), Verilator |
| Verdi | Synopsys | debug / coverage viewer | GTKWave, our coverage scripts |
| vManager / Xcelium IMC | Cadence | coverage + regression management | `uvm/regress.py`, `uvm/code_coverage.py` |
| JasperGold | Cadence | formal | SymbiYosys |
| VC Formal | Synopsys | formal | SymbiYosys |
| SpyGlass / Questa Lint & CDC | Synopsys / Siemens | lint, CDC | Verilator lint, Verible (single clock: no CDC needed) |
| Platform Architect / Virtualizer | Synopsys | SystemC virtual prototypes | Accellera SystemC |
| Catapult / Stratus | Siemens / Cadence | high-level synthesis | — (not in the plan) |
| Palladium, ZeBu, Veloce | Cadence / Synopsys / Siemens | hardware emulation | — (the FPGA board plays this role) |
| Design Compiler / Genus | Synopsys / Cadence | ASIC synthesis | Yosys (estimate only) |

**How students usually get them:** Indian institutes commonly have Cadence / Synopsys / Siemens tools
through university programmes (for example the MeitY Chips-to-Startup (C2S) programme) on a lab licence
server — ask your department's VLSI lab. Synopsys/Cadence also run limited student/trial programmes.
The UVM, SystemVerilog and SystemC code in this repo is standard and is intended to run on those tools
with little change (only `uvm/env/mm_coverage.svh` would become a native covergroup).
