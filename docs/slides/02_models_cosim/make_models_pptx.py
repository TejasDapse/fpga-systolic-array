#!/usr/bin/env python3
"""Build models_cosim.pptx -- the PowerPoint twin of models_cosim.tex.

    pip install python-pptx
    python docs/slides/02_models_cosim/make_models_pptx.py [output.pptx]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # docs/slides/slide_kit.py
from slide_kit import *  # noqa: E402,F401,F403
import slide_kit as kit  # noqa: E402


def why_how(sl, why, how, x=0.6, w=5.7, y=1.4, h_why=2.2, h_how=2.9, size=16, gap=0.2):
    panel(sl, x, y, w, h_why, "Why", why, "why", size)
    panel(sl, x, y + h_why + gap, w, h_how, "How", how, "how", size)


# 1 ------------------------------------------------------------- title
sl = new_slide(dark=True, notes=(
    "Section 3 (software models) and Section 4 (co-simulation). Every slide gives the reason a "
    "piece exists (Why) and how the code does it (How)."))
textbox(sl, 0.8, 1.5, 7.8, 1.6, "Software Models and Co-simulation", size=40, color=WHITE, font=HEAD, bold=True)
textbox(sl, 0.8, 3.15, 7.6, 1.0, "Why each model exists, and how it is built: NumPy, C++, SystemC, Verilator",
        size=18, color=ICE)
textbox(sl, 0.8, 4.5, 7.6, 0.5, "Group project  ·  systolic-array accelerator  ·  Phase 5", size=16, color=WHITE)
textbox(sl, 0.8, 5.1, 7.6, 0.8, "Covers `model/` and `cosim/`. Results: Ubuntu 22.04, g++ 11.4, SystemC 3.0.2, Verilator 5.052.",
        size=14, color=ICE)
levels = ["NumPy", "C++", "SystemC LT", "SystemC CA", "RTL", "FPGA"]
for i, lv in enumerate(levels):
    box(sl, 9.2, 1.45 + i * 0.78, 3.2, 0.6, lv, "hot" if lv == "RTL" else "dark", size=15)
    if i < 5:
        line(sl, 10.8, 2.05 + i * 0.78, 10.8, 2.23 + i * 0.78, ICE, 1.5)

# 2 ------------------------------------------------------------- the problem
sl = new_slide("Two questions every chip team must answer", notes=(
    "Correctness and performance must both be shown before fabrication. Models answer them fast, "
    "but only if they are correlated with the RTL."))
panel(sl, 0.6, 1.45, 5.9, 2.0, "1. Is the hardware correct?",
      "Does the RTL give **exactly the same answer** as a trusted reference, bit for bit, for every input we can think of?",
      "why", 16)
panel(sl, 0.6, 3.7, 5.9, 2.0, "2. Is it as fast as predicted?",
      "Does the RTL take **exactly the number of cycles** the architects' model said it would?", "how", 16)
textbox(sl, 7.0, 1.45, 5.7, 0.4, "**Why this matters**", size=18, color=PCB)
textbox(sl, 7.0, 1.95, 5.7, 3.6, [
    "A chip cannot be fixed after fabrication. Bugs must be found in simulation.",
    "RTL simulation is **slow**; software models are 100–1000× faster.",
    "Architects choose array size, buffers and bus widths **from models**, before RTL exists.",
    "So the model must be **trusted** — and trust comes from **correlating** it with the RTL.",
], size=16, kind="char", space=10)
textbox(sl, 7.0, 5.75, 5.7, 0.9, "This is the “functional and performance correlation between HW and SW models” "
        "that verification job descriptions ask for.", size=13, color=MUTED)

# 3 ------------------------------------------------------------- model stack
sl = new_slide("The model stack: six ways to compute the same job", notes=(
    "Each level adds detail. The fast levels are trusted only because they agree with the slow ones."))
stack = [("NumPy golden", "[[golden_model.py]]", "none", "fastest", "mod"),
         ("C++ bit-accurate", "[[cpp/mm_ref.cpp]]", "formula only", "very fast", "mod"),
         ("SystemC LT", "[[systemc/mm_lt.h]]", "annotated delay", "very fast", "mod"),
         ("SystemC CA", "[[systemc/mm_ca.h]]", "cycle by cycle", "fast", "mod"),
         ("RTL (Verilator)", "[[rtl/core/mm_core.sv]]", "exact", "slow", "hot"),
         ("FPGA board", "[[host/host.py]]", "real hardware", "real time", "ext")]
textbox(sl, 3.75, 1.35, 3.0, 0.3, "**file**", size=12, color=MUTED, space=0)
textbox(sl, 7.4, 1.35, 2.5, 0.3, "**timing**", size=12, color=MUTED, space=0)
textbox(sl, 10.2, 1.35, 2.3, 0.3, "**speed**", size=12, color=MUTED, space=0)
for i, (name, f, tm, sp, st) in enumerate(stack):
    y = 1.7 + i * 0.72
    box(sl, 1.2, y, 2.3, 0.56, name, st, size=14)
    textbox(sl, 3.75, y + 0.12, 3.5, 0.34, f, size=13, space=0)
    textbox(sl, 7.4, y + 0.12, 2.6, 0.34, tm, size=13, color=MUTED, space=0)
    textbox(sl, 10.2, y + 0.12, 2.3, 0.34, sp, size=13, color=MUTED, space=0)
line(sl, 0.85, 1.75, 0.85, 5.95, PCBMID)
textbox(sl, 0.3, 3.4, 0.5, 1.0, "more detail", size=10, color=MUTED, align=PP_ALIGN.CENTER)
textbox(sl, 0.6, 6.2, 12.1, 0.7, "Every level runs the **same jobs** and must produce the **same C** and the **same counters**.",
        size=16, align=PP_ALIGN.CENTER)

# 4 ------------------------------------------------------------- file map
sl = new_slide("How the files fit together", notes=(
    "The vector files and the register map are shared by every level. That is what makes the levels comparable."))
box(sl, 0.6, 1.5, 2.6, 0.75, ["[[golden_model.py]]", "expected C + counters"], "mod", 13)
box(sl, 0.6, 2.85, 2.6, 0.75, ["[[model/vectors.py]]", "generates jobs"], "hot", 13)
box(sl, 3.8, 2.85, 2.6, 0.75, ["[[vectors/n4.hex]], [[n8.hex]]", "1000 jobs each"], "mod", 12)
line(sl, 1.9, 2.25, 1.9, 2.85)
line(sl, 3.2, 3.22, 3.8, 3.22); lbl(sl, 3.5, 2.97, "writes", 10, COPPER, 0.6)
targets = [("[[cpp/test_mm_ref.cpp]]", "C++ vs expected", "mod"), ("[[systemc/test_models.cpp]]", "LT + CA vs expected", "mod"),
           ("[[cosim/cosim_main.cpp]]", "RTL vs CA vs expected", "hot"), ("[[tb/test_mm_core.py]]", "cocotb RTL", "mod")]
for i, (a, b, st) in enumerate(targets):
    y = 1.45 + i * 1.05
    box(sl, 7.4, y, 3.1, 0.75, [a, b], st, 12)
    line(sl, 6.4, 3.22, 7.4, y + 0.37, PCBMID)
box(sl, 11.0, 3.55, 1.75, 0.75, ["[[docs/results/]]", "cosim_n{4,8}.csv"], "mod", 11)
line(sl, 10.5, 3.92, 11.0, 3.92)
box(sl, 0.6, 4.4, 5.8, 0.75, ["register map", "[[regmap.py]] · [[mm_regmap.h]] · [[mm_regs.sv]]"], "mod", 13)
textbox(sl, 0.6, 5.6, 12.1, 1.2, "Two things are **shared by every level**: the test-vector files (same inputs, same expected outputs) "
        "and the register map (same addresses). That is what makes the levels comparable at all.", size=16)

# 5 ------------------------------------------------------------- divider A
divider("A", "Shared test vectors and register map", "Before any model: agree on the inputs and the addresses")

# 6 ------------------------------------------------------------- vectors
sl = new_slide("Shared test vectors: model/vectors.py", notes=(
    "One file of jobs with expected results is read by every level, so a mismatch points at one model."))
why_how(sl, "If every model made its own random inputs, a mismatch would not tell you **which** model is wrong. "
        "One shared file means any difference points at exactly one model.",
        ["1000 jobs per N, fixed seed (reproducible).",
         "**20 edge-case jobs**: 5 patterns × K in {1, 2N−2, 2N−1, 64}.",
         "Then random A, B and random **K in [1, 64]**.",
         "Expected C and counters from [[golden_model.py]]."], h_why=1.95, h_how=2.75)
textbox(sl, 6.8, 1.4, 5.9, 0.35, "**File format:** 5 lines per job, all hex", size=15)
code(sl, 6.8, 1.85, 5.9, 1.95, """job 4 2           <- N=4, K=2
a 7f 80 01 ff ..  <- N*K int8, row-major
b 02 fe 7f 00 ..  <- K*N int8, row-major
c xxxxxxxx ..     <- N*N int32: expected C
p a 9 9 20        <- TOTAL=10 COMPUTE=9
                     FILLDRAIN=9 MACS=32""", 13)
textbox(sl, 6.8, 4.05, 5.9, 2.4, [
    "Why K = 2N−2 and 2N−1? They sit exactly on the boundary where `all_active` turns on — the easiest place for an off-by-one bug.",
    "Readers: `read_vectors()` in Python and in [[mm_ref.cpp]].",
], size=14, kind="char", space=8)

# 7 ------------------------------------------------------------- register map
sl = new_slide("One register map, written three times", notes=(
    "The same addresses in Python, C++ and SystemVerilog. One TLM transaction equals one bus transaction."))
why_how(sl, "The same test sequence must run on the SystemC model and on the RTL pins. That only works if both agree "
        "on every address and bit.",
        ["[[model/regmap.py]] — Python (cocotb, host)",
         "[[model/systemc/mm_regmap.h]] — C++ / SystemC",
         "[[rtl/core/mm_regs.sv]] — the hardware",
         "One TLM transaction (4 bytes) = one RTL bus transaction."], h_why=1.7, h_how=2.6)
table(sl, 6.8, 1.4, [1.3, 1.9, 2.7], [
    ["Address", "Name", "Use in the models"],
    ["0x0000", "CTRL", "START / SOFT_RESET"], ["0x0004", "STATUS", "poll BUSY, DONE"],
    ["0x0008", "CFG_K", "set K"], ["0x000C", "INFO", "N, K_MAX, VERSION"],
    ["0x0010", "PERF_TOTAL", "compared"], ["0x0014", "PERF_COMPUTE", "compared"],
    ["0x0018", "PERF_FILLDRAIN", "compared"], ["0x001C", "PERF_IDLE", "**not** compared (host timing)"],
    ["0x0020", "PERF_MACS", "compared"], ["0x1000+", "A_BUF", "i·K_MAX + k"],
    ["0x2000+", "B_BUF", "k·N + j"], ["0x3000+", "C_BUF", "4(i·N + j)"],
], size=12, row_h=0.4, mono_cols=(0,))

# 8 ------------------------------------------------------------- divider B
divider("B", "Reference models", "NumPy golden model, C++ model, analytical performance model")

# 9 ------------------------------------------------------------- numpy
sl = new_slide("NumPy golden model: model/golden_model.py", notes=(
    "Short enough to trust by reading. Multiply in 64-bit and wrap to 32 bits like the hardware."))
why_how(sl, "We need one reference that is **obviously correct**. NumPy's `A @ B` is short enough to trust by "
        "reading it, and Python is easy to use from cocotb and the host script.",
        "Multiply in 64-bit (never overflows at these sizes), then **wrap to 32 bits** the way the hardware "
        "accumulator does. `expected_perf()` gives every counter.", h_why=2.0, h_how=1.9)
code(sl, 6.8, 1.4, 5.9, 1.55, """def matmul_int32(a, b):
    c = (np.asarray(a, np.int64)
         @ np.asarray(b, np.int64))
    # wrap to int32, like the hardware
    return (c + 2**31) % 2**32 - 2**31""", 13)
textbox(sl, 6.8, 3.2, 5.9, 0.35, "**Edge cases** (`edge_cases()`) and why each exists", size=14)
table(sl, 6.8, 3.65, [2.7, 3.2], [
    ["Pattern", "Why"],
    ["zeros", "accumulators must stay 0"],
    ["all_min (−128 · −128)", "largest positive sum"],
    ["all_max (127 · 127)", "large positive sum"],
    ["min_times_max (−128 · 127)", "largest negative sum"],
    ["identity", "C must equal B's rows"],
], size=12, row_h=0.4)

# 10 ------------------------------------------------------------ C++ model
sl = new_slide("C++ bit-accurate model: model/cpp/mm_ref.cpp", notes=(
    "C++ can be linked into SystemC, Verilator and a UVM scoreboard. Same widths and overflow as pe.sv."))
panel(sl, 0.6, 1.4, 5.7, 3.3, "Why", [
    "Python cannot be linked into SystemC, Verilator or a UVM scoreboard; C++ can (UVM calls it through **DPI-C** in Phase 6).",
    "Much faster than Python for thousands of jobs.",
    "**Bit-accurate**: same widths and overflow as [[pe.sv]], so outputs compare bit for bit.",
], "why", 16)
panel(sl, 0.6, 4.9, 5.7, 1.5, "How",
      "int8 × int8 → **int16** product (like `prod` in pe.sv), sign-extended to 32 bits and added in **uint32**.",
      "how", 16)
code(sl, 6.7, 1.4, 6.0, 4.4, """void matmul_ref(int n, int k, const int8_t* a,
                const int8_t* b, int32_t* c) {
  for (int i = 0; i < n; ++i)
    for (int j = 0; j < n; ++j) {
      uint32_t acc = 0;   // unsigned: defined wrap
      for (int kk = 0; kk < k; ++kk) {
        int16_t prod = int16_t(a[i*k + kk])
                     * int16_t(b[kk*n + j]);
        // sign-extend to 32 bits, add mod 2^32
        acc += uint32_t(int32_t(prod));
      }
      c[i*n + j] = int32_t(acc);
    }
}""", 13)

# 11 ------------------------------------------------------------ uint32 trap
sl = new_slide("The C++ trap: why the accumulator is uint32_t", notes=(
    "Signed overflow is undefined behaviour in C++. Unsigned arithmetic wraps modulo 2^32 like a hardware adder."))
why_how(sl, "In C and C++, **signed integer overflow is undefined behaviour**. The compiler may assume it never "
        "happens and produce a **different** answer from hardware, which simply wraps.",
        "Unsigned overflow **is** defined: it wraps modulo 2³², exactly like a 32-bit adder. "
        "So add as `uint32_t`, convert back to `int32_t` at the end.", h_why=2.15, h_how=1.95)
textbox(sl, 6.8, 1.4, 5.9, 0.4, "**Does it ever overflow here?**", size=17, color=PCB)
textbox(sl, 6.8, 1.9, 5.9, 2.2, [
    "Largest product: (−128) × (−128) = 16 384 (fits int16, max 32 767).",
    "K = 64: 64 × 16 384 = 1 048 576 — fits int32 easily.",
    "So with K ≤ 64 it never overflows.",
], size=15, kind="char", space=8)
box(sl, 6.8, 4.25, 5.9, 1.25, ["**Then why bother?** The model follows the **spec** (“32-bit wrap”), not the test sizes. "
                              "Raise K_MAX later and it is still correct."], "hot", 15, align=PP_ALIGN.LEFT)
textbox(sl, 6.8, 5.75, 5.9, 0.9, "Interview line: “the reference model mirrors the spec, not the RTL code — "
        "otherwise both can share the same bug.”", size=13, color=MUTED)

# 12 ------------------------------------------------------------ analytical perf
sl = new_slide("Analytical performance model: predict_perf()", notes=(
    "Count controller states: 1 CLEAR + K COMPUTE + 2N-1 DRAIN. This prediction is the target for CA, RTL and FPGA."))
why_how(sl, "Before running anything, we want a **prediction** of the cycle count. It is the target the CA model, "
        "the RTL and the FPGA are all checked against.",
        "Count the controller states: 1 CLEAR + K COMPUTE + (2N−1) DRAIN. All N² PEs are busy only for steps "
        "2N−1 … K.", w=5.2, h_why=2.0, h_how=2.0)
table(sl, 6.2, 1.4, [1.8, 4.7], [
    ["Counter", "Formula"], ["total", "K + 2N"], ["compute", "K + 2N − 1"],
    ["filldrain", "compute − max(0, K − 2N + 2)"], ["macs", "N² · K"],
    ["utilisation", "macs / (N² · compute)"],
], size=13, row_h=0.38)
table(sl, 6.2, 3.95, [0.6, 0.6, 0.9, 1.15, 1.15, 1.0, 1.1], [
    ["N", "K", "total", "compute", "fill/drain", "util.", "GOPS"],
    ["4", "16", "24", "23", "13", "69.6 %", "1.07"], ["4", "64", "72", "71", "13", "90.1 %", "1.42"],
    ["8", "16", "32", "31", "29", "51.6 %", "3.20"], ["8", "64", "80", "79", "29", "81.0 %", "5.12"],
], size=13, row_h=0.38)
textbox(sl, 6.2, 6.0, 6.5, 0.8, "GOPS = 2·macs / (total / 50 MHz). Full table: [[docs/results/perf_model.csv]] "
        "(from [[perf_table.cpp]]).", size=12, color=MUTED)

# 13 ------------------------------------------------------------ first check
sl = new_slide("First check: C++ model == NumPy (test_mm_ref.cpp)", notes=(
    "Two independent references agree on 2000 jobs before they are used to judge anything else."))
code(sl, 0.6, 1.4, 6.0, 2.4, """for (const mm::Job& j : mm::read_vectors(file)) {
  std::vector<int32_t> c(j.n * j.n);
  mm::matmul_ref(j.n, j.k, j.a.data(),
                 j.b.data(), c.data());
  bool ok = (c == j.c) &&
    (mm::predict_perf(j.n, j.k) == j.perf);
  ...
}""", 13)
card = box(sl, 1.6, 4.2, 4.0, 1.6, ["2000 / 2000", "vectors match (C and counters)"], "hot", 40)
for r in card.text_frame.paragraphs[0].runs:
    r.font.bold, r.font.name = True, HEAD
for r in card.text_frame.paragraphs[1].runs:
    r.font.size = Pt(14)
why_how(sl, "Two references, two languages, two methods. If they agree on 2000 jobs, a bug in either is very "
        "unlikely. Only then do we use them to judge the SystemC models and RTL.",
        "Read every job from `n4.hex` and `n8.hex`, compute C and the predicted counters, compare with what NumPy "
        "wrote: `make -C model/cpp test`.", x=7.0, w=5.7, h_why=2.2, h_how=1.95)

# 14 ------------------------------------------------------------ divider C
divider("C", "SystemC models", "Loosely-timed (LT) and cycle-approximate (CA): the whole accelerator, with registers and time")

# 15 ------------------------------------------------------------ why SystemC
sl = new_slide("Why SystemC, and the TLM-2.0 pieces we use", notes=(
    "SystemC adds modules, ports, clocks and time to C++. TLM-2.0 models bus transactions as function calls."))
panel(sl, 0.6, 1.4, 5.7, 4.0, "Why", [
    "The C++ model only computes C. A real model of the accelerator also needs **registers, a bus, time and a clock**.",
    "SystemC is a C++ library (IEEE 1666) that adds exactly that: modules, ports, clocks, simulated time.",
    "It is the standard language for architecture models and virtual platforms.",
], "why", 16)
box(sl, 6.8, 1.5, 2.3, 0.9, ["**initiator**", "[[BusInitiator]]"], "mod", 14)
box(sl, 10.4, 1.5, 2.3, 0.9, ["**target**", "[[MmLt]] / [[MmCa]]"], "hot", 14)
line(sl, 9.1, 1.95, 10.4, 1.95)
lbl(sl, 9.75, 2.65, "b_transport(trans, delay)", 11, COPPER, 2.4)
panel(sl, 6.8, 3.0, 5.9, 3.6, "How", [
    "**Socket**: initiator socket (bus master) bound to a target socket (the model).",
    "**Generic payload** = one transaction: command, address, 4-byte data pointer, length, response status.",
    "**b_transport**: a blocking call. The target does the access and adds its latency to `delay`.",
], "how", 16)

# 16 ------------------------------------------------------------ mm_state
sl = new_slide("Shared state for both models: mm_state.h", notes=(
    "Register decode is written once for LT and CA. write() only reports START or SOFT_RESET; each model decides when."))
why_how(sl, "LT and CA must decode registers **identically**: same ignored writes, same reset values. Writing it "
        "once means the two models cannot drift apart. Only **timing** differs.",
        ["`MmState` holds buffers, CFG_K, BUSY/DONE and counters.",
         "A/B writes ignored while BUSY; low byte stored.",
         "Bad CFG_K and START-while-BUSY ignored.",
         "Unmapped reads return 0."], h_why=2.0, h_how=2.6)
code(sl, 6.7, 1.4, 6.0, 4.35, """enum class WriteEffect { NONE, START, SOFT_RESET };

WriteEffect write(uint16_t addr, uint32_t d) {
  int region = addr >> 12, off = addr & 0xFFF;
  if (region == 0) {
    if (addr == CTRL) {
      if (d & SOFT_RESET) return SOFT_RESET;
      if ((d & START) && !busy) return START;
    } else if (addr == CFG_K && d >= 1
               && d <= k_max)
      cfg_k = d;
  } else if (!busy && region == 1
             && off < n * k_max)
    a[off] = int8_t(d & 0xFF);
  ...                       // B: region 2
  return NONE;
}""", 12)
textbox(sl, 6.7, 5.95, 6.0, 0.7, "The **model** decides when START or SOFT_RESET takes effect; `write()` only reports it.",
        size=13, color=MUTED)

# 17 ------------------------------------------------------------ LT
sl = new_slide("Loosely-timed model: mm_lt.h", notes=(
    "No clock. START computes C at once and records when the hardware would finish. The initiator syncs rarely."))
why_how(sl, "The fastest model that still looks like the accelerator from outside: good for many jobs, for software, "
        "and as the first check of register behaviour.",
        ["No clock. On START: compute C **at once**, counters from `predict_perf()`, `done_at = now + total·20 ns`.",
         "STATUS reads BUSY until time passes `done_at`.",
         "Each access adds one bus cycle to `delay`."], w=5.5, h_why=1.85, h_how=3.0)
X1, X2 = 6.9, 10.3
line(sl, X1, 1.45, X1, 5.25, PCBMID, 2, arrow=False)
line(sl, X2, 1.45, X2, 5.25, COPPER, 2, arrow=False)
textbox(sl, X1 - 0.6, 5.3, 1.2, 0.3, "initiator", 12, color=PCBMID, align=PP_ALIGN.CENTER, space=0)
textbox(sl, X2 - 0.6, 5.3, 1.2, 0.3, "MmLt", 12, color=COPPER, align=PP_ALIGN.CENTER, space=0)
msgs = ["write CFG_K", "write A and B bytes", "write CTRL.START", "read STATUS: BUSY", "read STATUS: BUSY",
        "read STATUS: DONE", "read C and counters"]
for i, m in enumerate(msgs):
    y = 1.75 + i * 0.5
    line(sl, X1, y, X2, y, COPPER if "START" in m else PCBMID, 1.5)
    lbl(sl, (X1 + X2) / 2, y - 0.17, m, 11, MUTED, 2.6, BODY)
box(sl, 10.45, 2.45, 2.3, 0.75, ["C computed now", "done_at = now + total·T"], "hot", 11)
textbox(sl, 10.45, 3.5, 2.3, 0.6, "each access: delay += 20 ns", 11, color=MUTED)
textbox(sl, 6.4, 5.75, 6.3, 0.9, "**Temporal decoupling:** the LT test thread never waits per access; it accumulates "
        "`delay` and syncs **once** at the end. That is what makes LT fast.", size=13)

# 18 ------------------------------------------------------------ CA
sl = new_slide("Cycle-approximate model: mm_ca.h", notes=(
    "A clocked thread runs the same FSM and counter rules as the RTL, so a wrong formula shows up as a disagreement."))
why_how(sl, "LT only predicts cycles from a formula. CA **counts** them, running the same FSM as "
        "[[mm_controller.sv]] and the counter rules of [[mm_regs.sv]].",
        ["`SC_THREAD` wakes on every rising edge.",
         "Counters use the state **before** the edge.",
         "START takes effect at the **next edge**.",
         "C is computed functionally at DONE."], w=5.4, h_why=2.0, h_how=2.5)
code(sl, 6.3, 1.4, 6.4, 5.3, """for (;;) {
  wait();                        // rising edge
  bool en  = (st == COMPUTE || st == DRAIN);
  bool all = en && t >= 2*n-1 && t <= K;
  // counters: same rules as mm_regs.sv
  if (busy && st != DONE) ++total;
  if (en)                 ++compute;
  if (en && !all)         ++filldrain;
  if (st == COMPUTE)      macs += n*n;
  // FSM: same as mm_controller.sv
  switch (st) {
  case IDLE:    if (start) st = CLEAR; break;
  case CLEAR:   t = 0; st = COMPUTE;   break;
  case COMPUTE: if (t == K-1) st = DRAIN;
                ++t;                   break;
  case DRAIN:   if (t == K+2*n-2) {
                  compute_c(); st = DONE;
                } else ++t;            break;
  case DONE:    done = true; st = IDLE;
  }
}""", 12)

# 19 ------------------------------------------------------------ comparison
sl = new_slide("LT vs CA vs RTL: what each one models", notes=(
    "Knowing what a model does not model matters as much as what it does."))
table(sl, 0.9, 1.4, [3.9, 2.4, 2.4, 2.8], [
    ["", "SystemC LT", "SystemC CA", "RTL"],
    ["Register map and access rules", "yes", "yes", "yes"],
    ["Result C", "yes (at START)", "yes (at DONE)", "yes (accumulates)"],
    ["Clock", "no", "yes", "yes"],
    ["Controller FSM, cycle by cycle", "no", "yes", "yes"],
    ["Counters", "from the formula", "counted each cycle", "counted each cycle"],
    ["Datapath pipeline (skew, PEs)", "no", "no", "yes"],
    ["RAM contents over time", "no", "no", "yes"],
    ["Reading C in the middle of a job", "old result", "old result", "partial sums"],
    ["PERF_IDLE", "approximate", "approximate", "exact"],
    ["Speed", "fastest", "fast", "slow"],
], size=13, row_h=0.4)
box(sl, 0.9, 6.0, 11.5, 0.7, "**Why this matters:** knowing what a model does **not** model is as important as what it does. "
    "That is why PERF_IDLE (host timing) is excluded from comparisons.", "hot", 14, align=PP_ALIGN.LEFT)

# 20 ------------------------------------------------------------ run_job
sl = new_slide("One job sequence for every level: run_job()", notes=(
    "A template drives either a TLM socket or the RTL pins with the same sequence of accesses."))
code(sl, 0.6, 1.4, 6.6, 3.6, """// simplified from bus_initiator.h
template <class Bus, class Tick>
void run_job(Bus& bus, const Job& j, ..., Tick tick) {
  bus.write(CFG_K, j.k);              tick();
  for (i, kk)  bus.write(a_addr(i, kk), A[i][kk]);
  for (kk, jj) bus.write(b_addr(kk, jj), B[kk][jj]);
  bus.write(CTRL, CTRL_START);        tick();
  while (!(bus.read(STATUS) & DONE))  tick();
  for (idx)    c[idx] = bus.read(C_BUF + 4*idx);
  p = { bus.read(PERF_TOTAL), bus.read(PERF_COMPUTE),
        bus.read(PERF_FILLDRAIN), bus.read(PERF_MACS) };
}""", 12)
textbox(sl, 0.6, 5.2, 6.6, 1.4, "In [[model/systemc/bus_initiator.h]]. Used by the SystemC test and by the co-simulation.",
        size=13, color=MUTED)
why_how(sl, "If each level had its own test sequence, a difference could come from the **test**, not the design. "
        "One sequence removes that doubt.",
        ["`Bus` is anything with `write()` / `read()`:",
         "`BusInitiator` → TLM socket → LT or CA model",
         "`RtlBus` → the pins of the verilated RTL",
         "`Tick` sets how time passes between accesses (nothing for LT, one clock for CA)."],
        x=7.5, w=5.2, h_why=1.85, h_how=3.2)

# 21 ------------------------------------------------------------ second check
sl = new_slide("Second check: SystemC models (test_models.cpp)", notes=(
    "Both models run all jobs; CA also times a bare restart with the clock and matches the formula exactly."))
panel(sl, 0.6, 1.4, 5.9, 4.3, "How", [
    "One SystemC top: a 20 ns `sc_clock`, one LT model, one CA model, two initiators.",
    "Two threads run all 1000 jobs: `run_lt` (no waiting) and `run_ca` (drives on the falling edge).",
    "Each job: C and the 4 counters must equal the vector file.",
    "CA also **times a bare restart** with the clock, independently of the counters.",
], "how", 16)
textbox(sl, 0.6, 5.85, 5.9, 0.8, "Measured − 2 = PERF_TOTAL: START is seen one edge later, and the DONE cycle is not counted.",
        size=12, color=MUTED)
table(sl, 7.0, 1.4, [3.8, 1.9], [
    ["Check (2 × 1000 jobs)", "Result"],
    ["LT: C + counters", "0 mismatches"], ["CA: C + counters", "0 mismatches"],
    ["CA: measured vs predicted cycles", "**0 cycles** error"],
], size=14, row_h=0.45)
panel(sl, 7.0, 3.6, 5.7, 2.1, "Why", "Target was ±2 cycles. Getting **0** shows the CA model reproduces the controller "
      "exactly, so it can now be the reference for the RTL.", "why", 16)

# 22 ------------------------------------------------------------ divider D
divider("D", "Co-simulation", "The RTL and the SystemC model running side by side: cosim/cosim_main.cpp + Verilator")

# 23 ------------------------------------------------------------ why co-sim
sl = new_slide("Why co-simulation?", notes=(
    "Co-sim checks timing and counters against an independent model, and times the pins without the counters."))
panel(sl, 0.6, 1.4, 5.9, 4.4, "Why", [
    "cocotb already checks the RTL's **answers**. Co-sim also checks its **timing and counters** against an independent model, job by job.",
    "It proves the model and the RTL describe the **same machine**, so the model can be trusted for performance studies.",
    "It catches bugs where the answer is right but the behaviour is wrong (see the mutation test).",
], "why", 16)
textbox(sl, 7.0, 1.45, 5.7, 0.4, "**What is compared, every job**", size=17, color=PCB)
textbox(sl, 7.0, 1.95, 5.7, 3.0, [
    "**C**: RTL = CA model = expected",
    "**Counters**: RTL = CA model = analytical prediction",
    "**START → DONE at the pins**: measured from the `done` signal, without using the counters",
], size=16, kind="num", space=10)
box(sl, 7.0, 5.05, 5.7, 1.3, "Item 3 matters: if the counters themselves had a bug, comparing counters with counters "
    "could hide it. Timing the pins is an independent check.", "hot", 14, align=PP_ALIGN.LEFT)

# 24 ------------------------------------------------------------ verilator
sl = new_slide("Verilator: turning RTL into a SystemC module", notes=(
    "verilator --sc compiles the RTL into an sc_module, so RTL and model share one simulation and clock."))
why_how(sl, "SystemC cannot read SystemVerilog. Verilator **compiles** the RTL into C++; with `--sc` it becomes an "
        "`sc_module`, so RTL and model live in the **same simulation** and share one clock.",
        ["Cycle-based and 2-state (no X/Z) → very fast.",
         "`-GN=4` / `-GN=8` sets the top parameter: one harness, both sizes.",
         "Output: class `Vmm_core` with the same ports as [[mm_core.sv]]."], h_why=2.2, h_how=2.6)
textbox(sl, 6.8, 1.4, 5.9, 0.35, "**From** [[cosim/Makefile]] (simplified)", size=14)
code(sl, 6.8, 1.85, 5.9, 3.65, """verilator --sc --exe --build -j 0 \\
  -GN=$(N) -GK_MAX=64 \\
  --top-module mm_core --Mdir build/n$(N) \\
  rtl/core/pe.sv \\
  rtl/core/systolic_array.sv \\
  rtl/core/skew_buffer.sv \\
  rtl/core/sram_sp.sv \\
  rtl/core/mm_controller.sv \\
  rtl/core/mm_regs.sv rtl/core/mm_core.sv \\
  cosim_main.cpp model/cpp/mm_ref.cpp""", 12)
textbox(sl, 6.8, 5.7, 5.9, 0.9, "Only [[rtl/core/]] is compiled: the co-sim drives `mm_core`'s register bus directly, "
        "without the UART.", size=13, color=MUTED)

# 25 ------------------------------------------------------------ architecture
sl = new_slide("Co-simulation architecture (cosim_main.cpp)", notes=(
    "One SC_MODULE holds the clock, the verilated RTL, the CA model, both bus drivers and the job list."))
box(sl, 0.6, 2.35, 2.2, 1.0, ["`run_job()`", "same job, from n4/n8.hex"], "hot", 13)
box(sl, 3.5, 1.5, 2.1, 0.8, ["`RtlBus`", "pin driver"], "mod", 13)
box(sl, 3.5, 3.4, 2.1, 0.8, ["`BusInitiator`", "TLM socket"], "mod", 13)
box(sl, 6.6, 1.45, 2.3, 0.9, ["`Vmm_core`", "verilated RTL"], "hot", 13)
box(sl, 6.6, 3.35, 2.3, 0.9, ["`MmCa`", "SystemC CA model"], "mod", 13)
box(sl, 6.95, 2.5, 1.6, 0.65, ["`sc_clock`", "20 ns"], "ext", 12)
box(sl, 9.6, 2.3, 1.7, 1.1, ["**compare**", "C, counters, pin cycles"], "mod", 12)
box(sl, 11.65, 2.45, 1.1, 0.8, ["[[cosim_nN.csv]]", "1 row/job"], "mod", 10)
path(sl, [(1.7, 2.35), (1.7, 1.9), (3.5, 1.9)])
path(sl, [(1.7, 3.35), (1.7, 3.8), (3.5, 3.8)])
line(sl, 5.6, 1.9, 6.6, 1.9); lbl(sl, 6.1, 1.65, "sc_signals", 10, COPPER, 1.0)
line(sl, 5.6, 3.8, 6.6, 3.8); lbl(sl, 6.1, 3.55, "b_transport", 10, COPPER, 1.0)
line(sl, 7.75, 2.5, 7.75, 2.35, PCBMID, 1.25, dash=True)
line(sl, 7.75, 3.15, 7.75, 3.35, PCBMID, 1.25, dash=True)
path(sl, [(8.9, 1.9), (10.45, 1.9), (10.45, 2.3)], PCBMID)
path(sl, [(8.9, 3.8), (10.45, 3.8), (10.45, 3.4)], PCBMID)
line(sl, 11.3, 2.85, 11.65, 2.85)
textbox(sl, 0.6, 4.75, 12.1, 2.0, [
    "One `SC_MODULE Cosim` holds everything: the clock, the RTL with its signals, the CA model, both bus drivers, the job list.",
    "One `SC_THREAD run()`: reset the RTL for 3 cycles; then for each job run it on the RTL, run it on the model, "
    "time a restart at the pins, compare, write a CSV row.",
], size=16, kind="char", space=10)

# 26 ------------------------------------------------------------ RtlBus
sl = new_slide("Driving the RTL pins: RtlBus", notes=(
    "Drive on the falling edge and sample mid-cycle to avoid races. Reads must see rvalid one cycle later."))
code(sl, 0.6, 1.4, 6.1, 5.2, """void request(bool wr, uint16_t a, uint32_t d) {
  valid.write(true); write_en.write(wr);
  addr.write(a);     wdata.write(d);
  for (;;) {
    wait(SC_ZERO_TIME);         // settle
    bool rdy = ready.read();
    wait(clk.negedge_event());  // next fall
    if (rdy) break;             // accepted
  }
  valid.write(false);
}
uint32_t read(uint16_t a) {
  request(false, a, 0);
  if (!rvalid.read())           // 1 cycle
    throw std::runtime_error(...);
  return rdata.read();
}""", 13)
why_how(sl, "Signals driven exactly at a rising edge race with the RTL's flip-flops. Driving on the **falling** edge "
        "and sampling mid-cycle avoids the race.",
        ["Drive on the falling edge; the RTL samples on the rising edge.",
         "Hold `bus_valid` until `bus_ready` was seen.",
         "A read **must** see `bus_rvalid` one cycle later, so the protocol is checked too (same rule as cocotb)."],
        x=7.1, w=5.6, h_why=1.9, h_how=2.8)

# 27 ------------------------------------------------------------ pin timing
sl = new_slide("Measuring cycles at the pins", notes=(
    "t0 is the falling edge where START is driven; subtract half a cycle at each end."))
X0, CW = 1.6, 0.48
rows = {"clk": 2.0, "START": 3.0, "done": 4.0}
for name, yv in rows.items():
    textbox(sl, 0.4, yv - 0.17, 1.1, 0.34, name, 12, font=MONO, align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, space=0)
A = 0.2
for t in range(9):
    x = X0 + t * CW
    pts = [(x, 2.0 + A), (x, 2.0 - A), (x + CW / 2, 2.0 - A), (x + CW / 2, 2.0 + A), (x + CW, 2.0 + A)]
    for k in range(4):
        line(sl, *pts[k], *pts[k + 1], PCBMID, 1.25, arrow=False)
for yv, (t0, t1) in [(3.0, (0.5, 1.5)), (4.0, (7, 8))]:
    segs = [(X0, yv + A, X0 + t0 * CW, yv + A), (X0 + t0 * CW, yv + A, X0 + t0 * CW, yv - A),
            (X0 + t0 * CW, yv - A, X0 + t1 * CW, yv - A), (X0 + t1 * CW, yv - A, X0 + t1 * CW, yv + A),
            (X0 + t1 * CW, yv + A, X0 + 9 * CW, yv + A)]
    for sg in segs:
        line(sl, *sg, COPPER, 2, arrow=False)
for t, txt, dx in [(0.5, "t0", -0.25), (1.0, "accept", 0.35), (7.5, "seen", 0)]:
    line(sl, X0 + t * CW, 1.55, X0 + t * CW, 4.55, MUTED, 1, arrow=False, dash=True)
    lbl(sl, X0 + t * CW + dx, 1.4, txt, 11, MUTED, 0.8, BODY)
line(sl, X0 + 1.0 * CW, 4.75, X0 + 7 * CW, 4.75, MUTED, 1.25)
lbl(sl, X0 + 4 * CW, 5.0, "measured", 11, MUTED, 1.2, BODY)
why_how(sl, "Counters are themselves hardware under test. Timing the `done` pin gives a number that does **not** "
        "depend on the counter logic.",
        ["t0 = falling edge where START is driven.",
         "START accepted at the next rising edge: −T/2.",
         "`done` seen at a falling edge: −T/2.",
         "`pin_cycles = (now − t0 − T) / T`, compared with `predict_perf().total`."],
        x=6.6, w=6.1, h_why=1.75, h_how=3.0)

# 28 ------------------------------------------------------------ results
sl = new_slide("Results: cosim_n4.csv, cosim_n8.csv", notes=(
    "2000 jobs: zero mismatches in C and counters, zero cycles of pin-timing error."))
stats = [("2000", "jobs (2 × 1000)"), ("0", "C mismatches"), ("0", "counter mismatches"), ("0", "cycles of error")]
for i, (big, small) in enumerate(stats):
    x, y = 0.6 + (i % 2) * 2.95, 1.5 + (i // 2) * 2.05
    c = box(sl, x, y, 2.7, 1.8, [big, small], "hot", 44)
    for r in c.text_frame.paragraphs[0].runs:
        r.font.bold, r.font.name = True, HEAD
    for r in c.text_frame.paragraphs[1].runs:
        r.font.size = Pt(14)
textbox(sl, 6.7, 1.45, 6.0, 0.35, "**Sample rows** (RTL = CA = predicted)", size=14)
table(sl, 6.7, 1.9, [0.6, 0.7, 0.95, 1.2, 1.2, 1.35], [
    ["N", "K", "total", "compute", "fill/drain", "pin cycles"],
    ["8", "1", "17", "16", "16", "17"], ["8", "64", "80", "79", "29", "80"], ["4", "64", "72", "71", "13", "72"],
], size=13, row_h=0.42)
textbox(sl, 6.7, 3.85, 6.0, 1.4, "CSV columns: job, N, K, predicted_total, rtl/ca total, compute, filldrain, macs, "
        "rtl_pin_cycles, cycle_error, c_match.", size=14)
textbox(sl, 6.7, 5.3, 6.0, 1.2, "K = 1 shows the extreme: with K < 2N−1 the array is never fully busy, so every "
        "enabled cycle is fill/drain.", size=13, color=MUTED)

# 29 ------------------------------------------------------------ mutation
sl = new_slide("Proving the harness works: a mutation test", notes=(
    "Inject a bug, confirm it is caught, undo it. Here only the counters caught it; C stayed correct."))
why_how(sl, "“0 mismatches” is only meaningful if the harness **can** find a mismatch. A broken checker that "
        "always says PASS would also report 0.",
        "Inject one deliberate RTL bug, rerun, confirm it is caught, then undo it: in [[mm_controller.sv]] the "
        "“all PEs active” bound `2N-1` → `2N-2`.", h_why=1.85, h_how=1.95)
textbox(sl, 6.8, 1.45, 5.9, 0.4, "**What happened**", size=17, color=PCB)
textbox(sl, 6.8, 1.95, 5.9, 1.6, [
    "C was still **correct** (the bug only affects a status signal).",
    "Co-sim immediately reported **PERF_FILLDRAIN mismatches**.",
], size=16, kind="char", space=10)
box(sl, 6.8, 3.75, 5.9, 1.4, "A check of answers alone would have **passed**. Performance correlation caught a real "
    "bug that functional checking missed.", "hot", 16, align=PP_ALIGN.LEFT)
textbox(sl, 6.8, 5.4, 5.9, 0.6, "Good interview story: “how do you know your checker works?”", size=13, color=MUTED)

# 30 ------------------------------------------------------------ limits
sl = new_slide("What co-simulation does not prove (yet)", notes=(
    "Limits of the current flow and the phases that close them."))
textbox(sl, 0.6, 1.45, 5.9, 0.4, "**Limits**", size=18, color=PCB)
textbox(sl, 0.6, 1.95, 5.9, 4.6, [
    "The CA model does not model the **datapath** (skew, PE pipeline, RAM timing); the RTL's C is checked against expected values instead.",
    "Verilator is **2-state**: uninitialised (X) values are not visible.",
    "**PERF_IDLE** is excluded: it depends on how fast the host polls.",
    "Simulation says nothing about **FPGA timing** (Fmax, slack) or the real UART link.",
], size=15, kind="char", space=10)
textbox(sl, 7.0, 1.45, 5.7, 0.4, "**Next steps that close these gaps**", size=18, color=PCB)
for i, (h, t) in enumerate([("Phase 4 — FPGA", "read the same counters from the board → model vs RTL vs **real hardware**"),
                            ("Phase 6 — UVM", "4-state simulator (Questa), constrained-random jobs, DPI-C scoreboard calling `matmul_ref()`, coverage"),
                            ("Correlation report", "predicted vs RTL vs FPGA cycles, error %")]):
    box(sl, 7.0, 2.0 + i * 1.5, 5.7, 1.3, [f"**{h}**", t], "hot" if i == 1 else "mod", 15, align=PP_ALIGN.LEFT)

# 31 ------------------------------------------------------------ run + reading
sl = new_slide("Running it on Ubuntu, and the reading order", notes=(
    "Run on Ubuntu in the fpga conda environment. Read the files in this order."))
code(sl, 0.6, 1.4, 5.6, 2.3, """conda activate fpga         # tools
python3 model/vectors.py    # n4/n8.hex
make -C model/cpp test      # C++ == NumPy
make -C model/systemc test  # LT + CA
make -C cosim               # RTL vs CA
# results: docs/results/cosim_n{4,8}.csv""", 13)
textbox(sl, 0.6, 3.9, 5.6, 0.8, "Run these on Ubuntu (the toolchain lives in the `fpga` conda environment).", size=13, color=MUTED)
box(sl, 0.6, 5.0, 5.6, 1.1, "**Exercise:** redo the mutation test yourself, then undo it.", "hot", 15, align=PP_ALIGN.LEFT)
table(sl, 6.6, 1.4, [0.45, 3.0, 2.65], [
    ["#", "Read", "Focus"],
    ["1", "golden_model.py", "matmul_int32, expected_perf"], ["2", "vectors.py", "file format, edge cases"],
    ["3", "cpp/mm_ref.cpp", "uint32 wrap, predict_perf"], ["4", "systemc/mm_state.h", "register decode"],
    ["5", "systemc/mm_lt.h", "b_transport, done_at"], ["6", "systemc/mm_ca.h", "clocked FSM, counters"],
    ["7", "systemc/bus_initiator.h", "run_job template"], ["8", "systemc/test_models.cpp", "two threads, timing check"],
    ["9", "cosim/cosim_main.cpp", "RtlBus, compare, CSV"], ["10", "results/phase5_models.md", "numbers + limits"],
], size=12, row_h=0.42, mono_cols=(1,))

# 32 ------------------------------------------------------------ interview Qs
sl = new_slide("Interview questions on this part", notes="Practise answering each in one or two sentences.")
qs = [("Why a C++ model if you have NumPy?", "It links into SystemC, Verilator and a UVM scoreboard (DPI-C), and it is fast."),
      ("What does bit-accurate mean?", "Same widths and overflow as the RTL, so outputs match bit for bit."),
      ("Why uint32_t for the accumulator?", "Signed overflow is undefined in C++; unsigned wraps like hardware."),
      ("LT vs CA?", "LT: no clock, blocking calls, annotated latency, fastest. CA: clocked, counts cycles."),
      ("What is temporal decoupling?", "The initiator runs ahead, accumulating delay, and syncs rarely."),
      ("How do you co-simulate RTL with SystemC?", "verilator --sc makes the RTL an sc_module; one clock, same jobs, compare."),
      ("Why drive on the falling edge?", "It avoids races with flip-flops at the rising edge."),
      ("How do you measure cycles independently?", "Time START → done at the pins."),
      ("How do you know the checker works?", "Mutation test: inject a bug, see it caught."),
      ("What does your CA model not model?", "The datapath pipeline and RAM timing; PERF_IDLE is excluded.")]
for i, (q, a) in enumerate(qs):
    col, row = i // 5, i % 5
    x, y = 0.6 + col * 6.2, 1.4 + row * 1.07
    textbox(sl, x, y, 0.5, 0.4, f"{i + 1}.", 15, color=COPPER, bold=True, space=0)
    textbox(sl, x + 0.45, y, 5.4, 1.0, [f"**{q}**", a], 13, space=2)

# 33 ------------------------------------------------------------ takeaways
sl = new_slide("Key takeaways", dark=True, notes="Same inputs, same map, same sequence; references, then models, then RTL.")
for i, (big, small) in enumerate([("6", "levels: NumPy → FPGA"), ("2000", "shared jobs"),
                                  ("0", "mismatches"), ("0", "cycles, RTL vs model")]):
    c = box(sl, 0.6 + i * 3.1, 1.5, 2.8, 1.85, [big, small], "dark", 44)
    for r in c.text_frame.paragraphs[0].runs:
        r.font.bold, r.font.name = True, HEAD
    for r in c.text_frame.paragraphs[1].runs:
        r.font.size, r.font.color.rgb = Pt(14), ICE
textbox(sl, 0.6, 3.9, 12.1, 3.0, [
    "**Same inputs, same map, same sequence** at every level — otherwise a mismatch means nothing.",
    "**References first** (NumPy = C++), then the **models** (LT, CA), then the **RTL** against the model.",
    "**Check timing, not only answers**: the mutation test was caught only by the counters.",
], size=18, color=WHITE, kind="char", space=14)

# ------------------------------------------------------------------ save
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("models_cosim.pptx")
kit.prs.core_properties.title = "Software Models and Co-simulation"
kit.prs.core_properties.subject = "Why and how: NumPy, C++, SystemC, Verilator co-simulation"
kit.prs.save(out)
print(f"wrote {out} ({kit._count[0]} slides)")
