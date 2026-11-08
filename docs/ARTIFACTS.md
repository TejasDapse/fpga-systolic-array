# Artifacts Index

Everything produced for this project, in one place. Paths are relative to this `docs/` folder.

---

## Online docs (claude.ai — open only for your account)

**DE10-Lite Hardware Bring-up Runbook**
Link: https://claude.ai/artifact/8wnABuhqaEKn3ZCAbU6ppf
What it describes: beginner step-by-step for the board — Ubuntu and Quartus setup, pin check, warm-up designs, UART wiring diagram, accelerator 4×4 and 8×8, FPGA cycle measurement, troubleshooting, pass/fail checklist.

**Make the Systolic-Array Project Your Own: Beginner Learning Plan**
Link: https://claude.ai/artifact/QufWp7n82xvTCyhSKAiQhC
What it describes: a 9-step plan (6 Oct – 15 Nov) with skills, tools, topics, practice and a checklist per step, a timeline, YouTube/PDF/blog resources, and an interview readiness checklist.

**4×4 Array on MAX 10: Slide-by-Slide Guide**
Link: https://claude.ai/artifact/Pd2jpWdN1as75f4kvzH7tV
What it describes: a page-by-page explanation of deck 04 in bullets and tables, for readers who know only digital electronics. It starts with the exact flip-flop and register count per PE, for 16 PEs and for the whole core.

---

## Start here

**Project README**
Link: [../README.md](../README.md)
What it describes: project summary and honest status — what is done in simulation, what still needs the board, and the limitations.

**Project Plan**
Link: [PLAN.md](PLAN.md)
What it describes: the full plan by phase and day, register map, UART protocol, expected numbers and progress tracker.

**Ubuntu Handoff Note**
Link: [UBUNTU_HANDOFF.md](UBUNTU_HANDOFF.md)
What it describes: Ubuntu machine setup, daily commands, hardware tasks 1–7, repo rules, issue log and troubleshooting.

**Phase 1 Warm-up Designs Guide**
Link: [../foundations/README.md](../foundations/README.md)
What it describes: the four warm-up designs (switch→LED, blinky, hex counter, UART echo) — how to simulate, compile, program and check each one.

---

## Learning and interview prep

**RTL Design Lab**
Link: [labs/RTL_DESIGN_LAB.md](labs/RTL_DESIGN_LAB.md)
What it describes: hands-on labs to design the project's RTL yourself with the project's tools — Icarus, GTKWave, cocotb, Verilator lint, Yosys and Quartus — graded by the project's own tests.

**Concept Notes**
Link: [NOTES.md](NOTES.md)
What it describes: 27 sections covering digital logic, FPGA, Verilog, timing, UART, systolic arrays, verification, SystemC, TLM, UVM, formal, correlation, interview Q&A and a glossary.

**RTL Slide Deck (24 slides)**
Link: [slides/01_rtl_overview/](slides/01_rtl_overview/)
What it describes: PDF, PowerPoint and LaTeX versions — components, parameter values, file-to-file data flow and a cycle-by-cycle timing walk-through.

**Models and Co-simulation Slide Deck (33 slides)**
Link: [slides/02_models_cosim/](slides/02_models_cosim/)
What it describes: the why and how of the NumPy, C++ and SystemC models and the Verilator co-simulation, including the mutation test.

**Processing Element Basics Deck (13 slides)**
Link: [slides/03_pe_basics/](slides/03_pe_basics/)
What it describes: a beginner's visual guide to the PE for Lab 3 — where it sits, its three jobs, the inside with bit widths, the clock-edge rules, why signed matters, a clock-by-clock example, picture-to-code mapping, tool flow and common mistakes (PDF + LaTeX).

**4×4 Array on MAX 10 Deck (38 slides)**
Link: [slides/04_array4x4_max10/](slides/04_array4x4_max10/)
What it describes: how the 4×4 design maps onto the Intel MAX 10, block by block. It splits every block into combinational logic, flip-flops and hard blocks, shows the LE and LAB, the RAM banks, the gate, the skew buffers, the FSM and the timing, and follows A[1][2] = 3 and C[1][2] = 10 from the PC through the chip and back (PDF + LaTeX).

**Core Register Placement Figure**
Link: [figures/core_register_placement/](figures/core_register_placement/)
What it describes: one picture of every flip-flop in mm_core, drawn inside the block that owns it: 16 PEs, skew buffers A and B, controller FSM, mm_regs and rd_valid. It shows which flip-flops Quartus removes, a count table (74 registers, 1,084 FF in RTL, about 1,020 on the chip) and how LEs and LABs hold them. It is a logical map; the Quartus Fitter picks the real LAB positions. PNG, PDF and LaTeX. Rebuild: `cd docs/figures/core_register_placement && tectonic core_register_placement.tex`.

**SoC Architecture, Block by Block (14 pages)**
Link: [figures/soc_architecture/](figures/soc_architecture/)
What it describes: a contents page plus 13 detailed figures in the same style as the register placement figure. They cover the whole SoC, a CPU pipeline register by register, caches and the MMU, the GPU, a full NPU around a systolic array, AXI / APB / NoC, DRAM, one AI job end to end (DMA, interrupts, cache coherence), clocks / power / CDC, boot / security / debug, and peripherals. The last two are a plan for a RISC-V + `mm_core` mini SoC on the DE10-Lite, and a floorplan with a cheat sheet. One combined PDF (`soc_architecture.pdf`), one PNG per page and the LaTeX sources. Rebuild on Ubuntu: `cd docs/figures/soc_architecture && ./build.sh`.

**Slides README**
Link: [slides/README.md](slides/README.md)
What it describes: how to rebuild all four slide decks.

**Resume Defense Guide**
Link: [interview/RESUME_DEFENSE.md](interview/RESUME_DEFENSE.md)
What it describes: every claim in your resume entry, one by one — what to know, where it is in the project, an exercise that proves it, likely interview questions with answers, suggested resume fixes, and a final self-test.

**Concept Question Bank**
Link: [interview/CONCEPT_QUESTION_BANK.md](interview/CONCEPT_QUESTION_BANK.md)
What it describes: about 60 concepts in nine levels, from two's complement to NoC scale-out. Each is marked as used / partly / not used in the project, with what, why, how we did it, likely interview questions with answers, the 30 most likely questions, and where the field is going.

**FPGA Flow Interview Guide**
Link: [interview/FPGA_FLOW_INTERVIEW.md](interview/FPGA_FLOW_INTERVIEW.md)
What it describes: the answer to "walk me through your FPGA flow" — a 30-second answer, 15 steps (done vs pending), design decisions, 15 likely questions and a 2-minute script.

---

## Verification results

**Verification Report**
Link: [results/verification_report.md](results/verification_report.md)
What it describes: one-page summary of every verification layer, mutation checks, issues found, formal proof, synthesis estimate and open items.

**Verification Plan**
Link: [vplan.md](vplan.md)
What it describes: features mapped to tests and coverage, plus tool notes.

**Models and Co-simulation Results**
Link: [results/phase5_models.md](results/phase5_models.md)
What it describes: the model stack, cycle formulas, co-simulation results and what the models leave out.

**UVM Regression Results**
Link: [results/uvm_regression.md](results/uvm_regression.md)
What it describes: pass counts per test and configuration, and the functional coverage bins.

**Code Coverage Results**
Link: [results/code_coverage.md](results/code_coverage.md)
What it describes: RTL line, branch and toggle coverage, and the two documented waivers.

**Performance Correlation**
Link: [results/correlation.md](results/correlation.md)
What it describes: cycle counts from the analytical model, SystemC, RTL and FPGA side by side (FPGA column pending), with plots for N = 4, 8 and 16.

**Co-simulation Data**
Link: `results/cosim_*.csv`
What it describes: one row per co-simulation job (N = 4, 8, 16 and K_MAX variants) with predicted and measured counters.

**Performance Model Table**
Link: `results/perf_model.csv`
What it describes: analytical cycles, utilisation and GOPS for N = 4, 8 and 16 at every K.

**Hardware Results Template**
Link: [results/phase1_hw.md](results/phase1_hw.md)
What it describes: an empty template for the board results, to fill in during bring-up.

---

## Tools and setup

**Tool List**
Link: [TOOLS.md](TOOLS.md)
What it describes: every tool — installed, needs a login, or licensed only — and its industry equivalent.

**Toolchain Definition**
Link: `../environment.yml`
What it describes: the pinned conda toolchain (`conda env create -f environment.yml`).

**Helper Scripts**
Link: `../tools/`
What it describes: `setup_ubuntu.sh`, `build.sh` (Quartus compile and program), `gen_quartus.py` (pins), `lint.sh`, `synth_estimate.sh` and `correlate.py`.
