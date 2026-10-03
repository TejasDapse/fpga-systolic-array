#!/usr/bin/env python3
"""Build rtl_overview.pptx -- the PowerPoint twin of rtl_overview.tex.

    pip install python-pptx
    python docs/slides/01_rtl_overview/make_rtl_pptx.py [output.pptx]

Every diagram is drawn with native shapes, so it stays editable in PowerPoint.
"""
import math
import re
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from lxml import etree

# ------------------------------------------------------------------ palette
PCB = RGBColor(0x0B, 0x2E, 0x33)      # dark board green (titles, dark slides)
PCBMID = RGBColor(0x1F, 0x5C, 0x61)   # module borders, b-wires
TINT = RGBColor(0xE6, 0xF0, 0xEF)     # module fill
COPPER = RGBColor(0xB5, 0x65, 0x1D)   # accent: files, a-wires, hot blocks
COPPER_T = RGBColor(0xF6, 0xE8, 0xDC) # hot-block fill
INK = RGBColor(0x1F, 0x2A, 0x2E)
MUTED = RGBColor(0x5B, 0x6B, 0x70)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ICE = RGBColor(0xCF, 0xE3, 0xE1)

HEAD, BODY, MONO = "Cambria", "Calibri", "Courier New"
W, H = 13.333, 7.5

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]
_count = [0]


# ------------------------------------------------------------------ text helpers
TOKEN = re.compile(r"(\*\*.+?\*\*|`.+?`|\[\[.+?\]\])")


def runs(par, text, size, color=INK, font=BODY, bold=False):
    """Add runs to a paragraph. Markup: **bold**, `code`, [[file]] (copper mono)."""
    for part in TOKEN.split(text):
        if not part:
            continue
        r = par.add_run()
        f, c, b, t = font, color, bold, part
        if part.startswith("**"):
            t, b = part[2:-2], True
        elif part.startswith("`"):
            t, f = part[1:-1], MONO
        elif part.startswith("[["):
            t, f, c = part[2:-2], MONO, COPPER
        r.text = t
        r.font.size, r.font.name, r.font.bold = Pt(size), f, b
        r.font.color.rgb = c


def bullet(par, kind="char", color=COPPER, level=0):
    pPr = par._p.get_or_add_pPr()
    indent = 0.28 + 0.3 * level
    pPr.set("marL", str(int(Inches(indent))))
    pPr.set("indent", str(-int(Inches(0.26))))
    clr = etree.SubElement(pPr, qn("a:buClr"))
    etree.SubElement(clr, qn("a:srgbClr")).set("val", str(color))
    if kind == "num":
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", BODY)
        etree.SubElement(pPr, qn("a:buAutoNum")).set("type", "arabicPeriod")
    else:
        etree.SubElement(pPr, qn("a:buFont")).set("typeface", "Arial")
        etree.SubElement(pPr, qn("a:buChar")).set("char", "▸")


def textbox(sl, x, y, w, h, items, size=16, color=INK, font=BODY, kind=None,
            align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6, bold=False, name=None):
    """items: str or list of str. kind: None | 'char' | 'num'."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = anchor
    items = [items] if isinstance(items, str) else items
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space)
        if kind:
            bullet(p, kind)
        runs(p, it, size, color, font, bold)
    return tb


def title(sl, text, dark=False):
    textbox(sl, 0.6, 0.32, 12.1, 0.8, text, size=30, color=WHITE if dark else PCB,
            font=HEAD, bold=True, anchor=MSO_ANCHOR.MIDDLE, name="Title")


def new_slide(title_text=None, dark=False, notes=None):
    sl = prs.slides.add_slide(BLANK)
    _count[0] += 1
    bg = sl.background.fill
    bg.solid()
    bg.fore_color.rgb = PCB if dark else WHITE
    if title_text:
        title(sl, title_text, dark)
    textbox(sl, 12.15, 7.02, 0.6, 0.3, str(_count[0]), size=10,
            color=ICE if dark else MUTED, align=PP_ALIGN.RIGHT, name="Slide number")
    if notes:
        sl.notes_slide.notes_text_frame.text = notes
    return sl


# ------------------------------------------------------------------ shape helpers
def box(sl, x, y, w, h, lines, style="mod", size=13, align=PP_ALIGN.CENTER, name=None):
    """Rounded module block. lines: list of str (first line full size, rest smaller)."""
    fill, line = {"mod": (TINT, PCBMID), "hot": (COPPER_T, COPPER),
                  "ext": (WHITE, MUTED), "dark": (PCBMID, PCBMID)}[style]
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.12
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    s.line.color.rgb = line
    s.line.width = Pt(1.5)
    if style == "ext":
        s.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    s.shadow.inherit = False
    if name:
        s.name = name
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = [lines] if isinstance(lines, str) else lines
    col = WHITE if style == "dark" else INK
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        runs(p, ln, size if i == 0 else size - 2, col)
    return s


def circle(sl, cx, cy, d, label, hot=False, size=12):
    s = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cx - d / 2), Inches(cy - d / 2), Inches(d), Inches(d))
    s.fill.solid()
    s.fill.fore_color.rgb = COPPER_T if hot else TINT
    s.line.color.rgb = COPPER if hot else PCBMID
    s.line.width = Pt(1.75)
    s.shadow.inherit = False
    s.name = f"State {label}"
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.02)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, ln in enumerate(label.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        runs(p, ln, size, INK, BODY, True)
    return (cx, cy, d / 2)


def line(sl, x1, y1, x2, y2, color=COPPER, width=1.75, arrow=True, dash=False):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    if arrow:
        ln = c.line._get_or_add_ln()
        t = etree.SubElement(ln, qn("a:tailEnd"))
        t.set("type", "triangle")
        t.set("w", "med")
        t.set("len", "med")
    return c


def path(sl, pts, color=COPPER, width=1.75):
    """Polyline through points; arrowhead on the last segment."""
    for i in range(len(pts) - 1):
        line(sl, *pts[i], *pts[i + 1], color=color, width=width, arrow=(i == len(pts) - 2))


def link(sl, a, b, color=PCBMID, label=None, dx=0.0, dy=-0.22, size=11, off=0.0):
    """Arrow between two circles (cx, cy, r), trimmed to their edges."""
    (x1, y1, r1), (x2, y2, r2) = a, b
    ang = math.atan2(y2 - y1, x2 - x1)
    nx, ny = -math.sin(ang) * off, math.cos(ang) * off
    sx, sy = x1 + r1 * math.cos(ang) + nx, y1 + r1 * math.sin(ang) + ny
    ex, ey = x2 - r2 * math.cos(ang) + nx, y2 - r2 * math.sin(ang) + ny
    line(sl, sx, sy, ex, ey, color=color)
    if label:
        mx, my = (sx + ex) / 2 + dx, (sy + ey) / 2 + dy
        lbl(sl, mx, my, label, size=size)


def lbl(sl, cx, cy, text, size=11, color=MUTED, w=1.4, font=MONO):
    textbox(sl, cx - w / 2, cy - 0.15, w, 0.3, text, size=size, color=color, font=font,
            align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=0)


def table(sl, x, y, widths, rows, size=12, row_h=0.36, header=True, mono_cols=()):
    nr, nc = len(rows), len(widths)
    gs = sl.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(sum(widths)), Inches(row_h * nr))
    gs.name = "Table"
    tbl = gs.table
    tbl.first_row = header
    tbl.horz_banding = False
    for j, wv in enumerate(widths):
        tbl.columns[j].width = Inches(wv)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            is_head = header and i == 0
            cell.fill.fore_color.rgb = PCB if is_head else (TINT if i % 2 == 0 else WHITE)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            txt = str(row[j]) if j < len(row) else ""
            font = MONO if (j in mono_cols and not is_head) else BODY
            runs(p, txt, size, WHITE if is_head else INK, font, is_head)
    return gs


# ================================================================== slides
# 1 -------------------------------------------------------------- title
sl = new_slide(dark=True, notes=(
    "This deck explains only the RTL in rtl/. All values are for the default Quartus build: "
    "N = 4, K_MAX = 64. The target configuration is N = 8."))
textbox(sl, 0.8, 1.6, 7.6, 1.6, "RTL of the Systolic-Array Accelerator", size=40,
        color=WHITE, font=HEAD, bold=True, name="Deck title")
textbox(sl, 0.8, 3.25, 7.4, 1.0,
        "How the hardware works: components, values, and how data moves from file to file",
        size=18, color=ICE)
textbox(sl, 0.8, 4.6, 7.4, 0.5, "Group project  ·  DE10-Lite (Intel MAX 10)", size=16, color=WHITE)
textbox(sl, 0.8, 5.2, 7.4, 0.8, "Covers only the RTL in `rtl/`. Default build: **N = 4**, K_MAX = 64 (target N = 8).",
        size=14, color=ICE)
for i in range(4):          # motif: the 4x4 PE grid
    for j in range(4):
        hot = (i == j)
        s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(9.0 + j * 0.88),
                                Inches(1.7 + i * 0.88), Inches(0.68), Inches(0.68))
        s.adjustments[0] = 0.15
        s.fill.solid()
        s.fill.fore_color.rgb = COPPER if hot else PCBMID
        s.line.fill.background()
        s.shadow.inherit = False
        s.name = f"PE {i}{j}"
textbox(sl, 9.0, 5.35, 3.4, 0.4, "4 × 4 grid of processing elements", size=12, color=ICE,
        align=PP_ALIGN.CENTER)

# 2 -------------------------------------------------------------- how to learn
sl = new_slide("How to learn RTL (the method behind these slides)", notes=(
    "RTL is learned by drawing hardware, not by reading code like software. Follow one job "
    "through the design, then zoom into one module at a time and confirm it with its test."))
textbox(sl, 0.6, 1.45, 7.0, 5.4, [
    "**Think in hardware, not code.** Every `always_ff` is flip-flops; every `assign` is wires and gates. Draw it first.",
    "**Big picture first:** which blocks exist and what connects them.",
    "**Follow one piece of data** end to end (this deck: one matrix job).",
    "**Then zoom into one module** at a time, bottom to top.",
    "**Run its test, open the waveform,** match each signal to your drawing.",
    "**Break one line on purpose** and see which test catches it.",
], size=17, kind="num", space=10)
steps = [("1. Overview", "slides 3–7", "mod"), ("2. Data coming in", "slides 8–12", "mod"),
         ("3. Compute core", "slides 13–17", "hot"), ("4. Timing & results", "slides 18–21", "mod"),
         ("5. Learning path", "slides 22–24", "mod")]
for i, (a, b, st) in enumerate(steps):
    box(sl, 8.6, 1.5 + i * 1.08, 3.9, 0.72, [f"**{a}**", b], st, size=15)
    if i < 4:
        line(sl, 10.55, 2.22 + i * 1.08, 10.55, 2.58 + i * 1.08, PCBMID)

# 3 -------------------------------------------------------------- big picture
sl = new_slide("The big picture: what happens in one job", notes=(
    "The PC talks UART. uart_rx turns serial bits into bytes, the bridge turns command bytes into "
    "register-bus reads and writes, and mm_core is the accelerator. Replies go back through a "
    "FIFO and uart_tx."))
frame = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(4.15), Inches(1.35), Inches(8.6), Inches(3.05))
frame.adjustments[0] = 0.05
frame.fill.background()
frame.line.color.rgb = PCB
frame.line.width = Pt(2)
frame.shadow.inherit = False
frame.name = "FPGA boundary"
textbox(sl, 4.3, 1.4, 4.5, 0.3, "[[top_de10lite.sv]] **(the FPGA)**", size=12)
box(sl, 0.6, 1.75, 1.35, 0.85, ["PC", "[[host.py]]"], "ext")
box(sl, 2.3, 1.75, 1.35, 0.85, ["USB–UART", "adapter"], "ext")
box(sl, 4.5, 1.8, 1.95, 0.8, ["[[uart_rx.sv]]", "bits → bytes"])
box(sl, 7.1, 1.8, 2.45, 0.8, ["[[uart_bus_bridge.sv]]", "bytes → bus"])
box(sl, 10.15, 1.7, 2.35, 1.0, ["[[mm_core.sv]]", "the accelerator"], "hot")
box(sl, 4.5, 3.3, 1.95, 0.8, ["[[uart_tx.sv]]", "bytes → bits"])
box(sl, 7.4, 3.3, 1.95, 0.8, ["[[fifo_sync.sv]]", "TX queue"])
line(sl, 1.95, 2.18, 2.3, 2.18)
line(sl, 3.65, 2.18, 4.5, 2.18); lbl(sl, 3.88, 1.95, "RXD", 10, COPPER, 0.5)
line(sl, 6.45, 2.2, 7.1, 2.2); lbl(sl, 6.78, 1.95, "rx_data", 10, COPPER, 0.8)
line(sl, 9.55, 2.2, 10.15, 2.2); lbl(sl, 9.85, 1.95, "bus", 10, COPPER, 0.6)
path(sl, [(11.3, 2.7), (11.3, 2.98), (9.0, 2.98), (9.0, 2.6)], PCBMID); lbl(sl, 10.3, 3.18, "rdata", 10, PCBMID, 0.8)
line(sl, 7.85, 2.6, 7.85, 3.3, PCBMID); lbl(sl, 7.45, 2.95, "reply", 10, PCBMID, 0.7)
line(sl, 7.4, 3.7, 6.45, 3.7, PCBMID)
path(sl, [(4.5, 3.7), (2.97, 3.7), (2.97, 2.6)], PCBMID); lbl(sl, 3.6, 3.92, "TXD", 10, PCBMID, 0.5)
textbox(sl, 0.6, 4.75, 12.1, 2.2, [
    "PC sends matrices **A** and **B** as UART bytes → the bridge turns them into **register-bus writes**.",
    "PC writes `CTRL.START` → the core multiplies: **C = A × B**.",
    "PC reads **C** and the **performance counters** back the same way.",
], size=17, kind="num", space=10)

# 4 -------------------------------------------------------------- hierarchy
sl = new_slide("Module hierarchy: which file instantiates which", notes=(
    "top_de10lite instantiates the UART blocks, the bridge and mm_core. mm_core instantiates the "
    "register block, controller, 2N RAMs, two skew buffers and the array; the array instantiates "
    "N squared PEs."))
tree = [(0, "**top_de10lite**", "board top level: pins ↔ modules", PCB),
        (1, "sync_2ff", "synchronize KEY buttons", INK), (1, "uart_rx", "serial bits → bytes", INK),
        (2, "sync_2ff", "synchronize UART_RXD", INK), (1, "fifo_sync", "16-byte reply queue", INK),
        (1, "uart_tx", "bytes → serial bits", INK), (1, "uart_bus_bridge", "UART commands → bus", INK),
        (1, "**mm_core**", "**the accelerator**", COPPER), (2, "mm_regs", "register map + counters", INK),
        (2, "mm_controller", "job state machine", INK), (2, "sram_sp ×2N", "A and B RAM banks", INK),
        (2, "skew_buffer ×2", "delay lane n by n cycles", INK), (2, "systolic_array", "N × N grid", COPPER),
        (3, "pe ×N²", "multiply-accumulate", COPPER), (1, "tick_gen", "1 Hz heartbeat tick", INK),
        (1, "hex7seg ×6", "7-segment digits", INK)]
Y0, DY, X0, DX = 1.4, 0.335, 0.7, 0.42
for r, (lev, name, role, col) in enumerate(tree):
    y = Y0 + r * DY
    textbox(sl, X0 + lev * DX, y, 3.0, 0.3, name, size=13, color=col, font=MONO, space=0)
    textbox(sl, 4.3, y + 0.02, 3.4, 0.3, role, size=11, color=MUTED, space=0)
    if lev:
        tx = X0 + (lev - 1) * DX + 0.12
        line(sl, tx, y + 0.15, X0 + lev * DX - 0.02, y + 0.15, PCBMID, 1.25, arrow=False)
for lev, r0, r1 in [(0, 0, 15), (1, 2, 3), (1, 7, 12), (2, 12, 13)]:
    tx = X0 + lev * DX + 0.12
    line(sl, tx, Y0 + r0 * DY + 0.3, tx, Y0 + r1 * DY + 0.15, PCBMID, 1.25, arrow=False)
textbox(sl, 8.2, 1.4, 4.5, 0.4, "**Where the files are**", size=17, color=PCB)
textbox(sl, 8.2, 1.9, 4.5, 3.3, [
    "[[rtl/top/]] board level: top_de10lite, uart_bus_bridge",
    "[[rtl/core/]] the accelerator: mm_core, mm_regs, mm_controller, sram_sp, skew_buffer, systolic_array, pe",
    "[[rtl/common/]] helpers: uart_rx/tx, fifo_sync, sync_2ff, tick_gen, hex7seg",
], size=14, kind="char", space=10)
box(sl, 8.2, 5.3, 4.5, 1.15, ["For N = 4: **16** PEs, **8** RAMs, **2** skew buffers",
                              "For N = 8: **64** PEs, **16** RAMs"], "hot", size=14)

# 5 -------------------------------------------------------------- parameters
sl = new_slide("Parameters: the values that size everything", notes=(
    "These parameters are set once at the top and passed down. 434 clocks per bit comes from "
    "50 MHz divided by 115200 baud."))
table(sl, 0.6, 1.45, [2.3, 1.9, 2.3, 5.6], [
    ["Parameter", "Value", "Set in", "What it controls"],
    ["N", "4 (target 8)", "top_de10lite", "array is N×N; C is N×N"],
    ["K_MAX", "64", "top_de10lite", "longest dot product; RAM depth"],
    ["DW", "8", "systolic_array", "operand width: signed int8 (−128 … 127)"],
    ["AW", "32", "systolic_array", "accumulator width: signed int32"],
    ["CLK_HZ", "50 000 000", "top_de10lite", "board clock (20 ns period)"],
    ["BAUD", "115 200", "top_de10lite", "UART speed → 434 clocks per bit"],
    ["TIMEOUT_CLKS", "5 000 000", "uart_bus_bridge", "100 ms: abandon a half-sent command"],
    ["DEPTH (TX FIFO)", "16", "fifo_sync", "reply bytes waiting for the UART"],
    ["VERSION", "0x0001", "mm_core", "read back through the INFO register"],
], size=13, row_h=0.42, mono_cols=(0,))
textbox(sl, 0.6, 5.95, 12.1, 0.9,
        "Parameters flow **down** the hierarchy: `top_de10lite #(.N(4))` → `mm_core #(.N(N))` → "
        "`systolic_array #(.N(N))`. Change N once at the top and every width below follows.", size=15)

# 6 -------------------------------------------------------------- derived widths
sl = new_slide("Derived widths: $clog2 turns parameters into bit counts", notes=(
    "$clog2 gives the number of bits needed to count to a value. Flat vectors pack N lanes into "
    "one bus; lane n is the slice [n*W +: W]."))
table(sl, 0.6, 1.45, [1.5, 2.9, 1.1, 1.1, 5.5], [
    ["Name", "Formula", "N = 4", "N = 8", "Used for"],
    ["KW", "$clog2(K_MAX)", "6", "6", "RAM address (k = 0..63)"],
    ["KL", "$clog2(K_MAX+1)", "7", "7", "k_len (1..64 needs 7 bits)"],
    ["LW", "$clog2(N)", "2", "3", "which lane (row / column)"],
    ["c_idx", "$clog2(N·N)", "4", "6", "which C element to read"],
    ["TW", "$clog2(K_MAX+2N)", "7", "7", "controller step counter t"],
    ["a_in, b_in", "N·8", "32", "64", "one column of A / one row of B"],
    ["c_out", "N·N·32", "512", "2048", "all accumulators, flattened"],
], size=13, row_h=0.45, mono_cols=(0, 1))
box(sl, 0.6, 5.35, 12.1, 1.1, [
    "**Flat vectors:** lane n of a bus is `[n*W +: W]`.  Example: `a_in[2*8 +: 8]` = bits 23:16 = row 2.",
    "Element C(i, j) is `c_out[(i*N+j)*32 +: 32]`."], "mod", size=15, align=PP_ALIGN.LEFT)

# 7 -------------------------------------------------------------- signals
sl = new_slide("Signals that cross file boundaries (N = 4)", notes=(
    "This is the map of every connection between files. Widths are for N = 4."))
table(sl, 0.6, 1.3, [2.2, 2.55, 5.2, 2.15], [
    ["From", "To", "Signals [width]", "Meaning"],
    ["pin UART_RXD", "uart_rx", "rx [1]", "serial bits from the PC"],
    ["uart_rx", "uart_bus_bridge", "rx_data [8], rx_valid", "one received byte"],
    ["uart_bus_bridge", "mm_regs", "bus_valid, bus_write, bus_addr [16], bus_wdata [32]", "bus request"],
    ["mm_regs", "uart_bus_bridge", "bus_ready, bus_rvalid, bus_rdata [32]", "accept / read data"],
    ["uart_bus_bridge", "fifo_sync → uart_tx", "tx_data [8], tx_push / tx_full", "reply bytes"],
    ["mm_regs", "mm_controller", "start, k_len [7]", "begin a job of length K"],
    ["mm_regs", "sram_sp (8×)", "wr_en, wr_sel, wr_lane [2], wr_addr [6], wr_data [8]", "load A / B"],
    ["mm_controller", "sram_sp", "rd_addr [6] (when busy)", "read column k"],
    ["mm_controller", "skew, array", "clear, array_en", "zero / run the array"],
    ["mm_controller", "mm_regs", "busy, done, all_active, rd_en", "status + counter events"],
    ["sram_sp", "skew_buffer", "a_col, b_row [32] (zero when not valid)", "A[.][k], B[k][.]"],
    ["skew_buffer", "systolic_array", "a_skew, b_skew [32]", "diagonal wavefront"],
    ["systolic_array", "pe (16×)", "a_in, b_in [8] per PE", "operands"],
    ["systolic_array", "mm_core → mm_regs", "c_out [512] → c_data [32] via c_idx [4]", "result C"],
    ["mm_core", "top_de10lite", "busy, done, state [3], perf_compute [32]", "LEDs and HEX"],
], size=11, row_h=0.355, mono_cols=(0, 1, 2))

# 8 -------------------------------------------------------------- uart_rx
sl = new_slide("Step 1 — a byte arrives: uart_rx.sv", notes=(
    "The receiver samples each bit in its middle: half a bit after the falling edge, then every "
    "full bit period. 434 clocks per bit at 50 MHz and 115200 baud."))
textbox(sl, 0.6, 1.45, 6.6, 5.4, [
    "The pin is **asynchronous**: it first goes through [[sync_2ff.sv]] (2 flip-flops) to avoid metastability.",
    "Line idles at 1. A **falling edge** = start bit.",
    "Wait **217** clocks (half a bit) → middle of the start bit; check it is still 0.",
    "Sample every **434** clocks → middle of each of the 8 data bits (LSB first).",
    "Stop bit = 1 → pulse `valid` for one cycle with `data`. Otherwise pulse `frame_err` (LEDR5).",
], size=16, kind="char", space=12)
I = circle(sl, 8.4, 2.3, 1.15, "IDLE")
S = circle(sl, 11.1, 2.3, 1.15, "START")
D = circle(sl, 11.1, 4.6, 1.15, "DATA\n×8")
P = circle(sl, 8.4, 4.6, 1.15, "STOP")
link(sl, I, S, label="rx = 0", dy=-0.22)
link(sl, S, D, label="217 clk", dx=0.55, dy=0)
link(sl, D, P, label="8 bits", dy=0.22)
link(sl, P, I, label="valid", dx=-0.5, dy=0)
link(sl, S, I, label="glitch", off=-0.25, dy=0.2)
textbox(sl, 7.6, 5.6, 5.1, 0.9, "50 000 000 / 115 200 = 434.03 → 434 clocks per bit. "
        "One byte = 10 bits ≈ 4 340 clocks ≈ 87 µs.", size=13, color=MUTED)

# 9 -------------------------------------------------------------- bridge
sl = new_slide("Step 2 — UART bytes to bus: uart_bus_bridge.sv", notes=(
    "Each UART command becomes one or more bus transactions. Block write B performs one bus "
    "write per payload byte. A 100 ms stall abandons the command."))
table(sl, 0.6, 1.45, [0.8, 2.9, 1.6], [
    ["Cmd", "Bytes in", "Reply"],
    ["W", "addr(2) data(4)", "K"], ["R", "addr(2)", "data(4)"],
    ["B", "addr(2) len(2) + len bytes", "K"], ["D", "addr(2) len(2)", "len bytes"],
    ["P", "—", "K  N  K_MAX"], ["other", "—", "E  (LEDR6)"],
], size=13, row_h=0.42, mono_cols=(0,))
textbox(sl, 0.6, 4.6, 5.3, 2.0, [
    "All fields **little-endian**.",
    "Block write `B` sends one bus write per byte at addr + n.",
    "PC stops mid-command for 100 ms → command abandoned (LEDR7).",
], size=14, kind="char", space=8)
gx, gy, d = [7.5, 9.5, 11.5], [1.95, 3.75, 5.55], 1.2
CMD = circle(sl, gx[0], gy[0], d, "S_CMD", size=11)
ARG = circle(sl, gx[1], gy[0], d, "S_ARGS", size=11)
BLK = circle(sl, gx[2], gy[0], d, "S_BLK_W", size=11)
RRQ = circle(sl, gx[0], gy[1], d, "S_RREQ", size=11)
WRQ = circle(sl, gx[2], gy[1], d, "S_WREQ", size=11)
RWT = circle(sl, gx[0], gy[2], d, "S_RWAIT", size=11)
SND = circle(sl, gx[1], gy[2], d, "S_SEND", size=11)
link(sl, CMD, ARG, label="cmd")
link(sl, ARG, BLK, label="B")
link(sl, ARG, WRQ, label="W", dx=0.25, dy=-0.2)
link(sl, ARG, RRQ, label="R, D", dx=-0.25, dy=-0.2)
link(sl, CMD, RRQ, label="P", dx=-0.25, dy=0)
link(sl, BLK, WRQ, label="byte", off=0.18, dx=0.45, dy=0)
link(sl, WRQ, BLK, label="next", off=0.18, dx=-0.55, dy=0)
link(sl, RRQ, RWT, label="ready", dx=-0.45, dy=0)
link(sl, RWT, SND, label="rvalid", dy=0.22)
link(sl, WRQ, SND, label="reply K", dx=0.35, dy=0.2)
path(sl, [(gx[1], gy[2] + d / 2), (gx[1], 6.5), (6.55, 6.5), (6.55, gy[0]), (gx[0] - d / 2, gy[0])], PCBMID)
lbl(sl, 6.22, 4.4, "done", 11, MUTED, 0.5)

# 10 ------------------------------------------------------------- bus handshake
sl = new_slide("Step 3 — the register bus (valid/ready handshake)", notes=(
    "A request is accepted on the clock edge where valid and ready are both high. Write data takes "
    "effect on that edge; read data comes back with rvalid exactly one cycle later."))
X0, CW = 2.1, 0.58
rows = {"clk": 2.1, "bus_valid": 3.0, "bus_ready": 3.9, "bus_rvalid": 4.8, "bus_rdata": 5.7}
for name, yv in rows.items():
    textbox(sl, 0.45, yv - 0.17, 1.55, 0.34, name, size=12, color=INK, font=MONO,
            align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, space=0)
A = 0.22
yc = rows["clk"]
for t in range(8):
    x = X0 + t * CW
    path_pts = [(x, yc + A), (x, yc - A), (x + CW / 2, yc - A), (x + CW / 2, yc + A), (x + CW, yc + A)]
    for k in range(len(path_pts) - 1):
        line(sl, *path_pts[k], *path_pts[k + 1], PCBMID, 1.25, arrow=False)


def wave(yv, highs, color):
    """highs: list of (t0, t1) in cycles where the signal is 1."""
    edges = []
    for t0, t1 in highs:
        edges += [(t0, 1), (t1, 0)]
    segs, y_now, x_now = [], yv + A, X0
    for t, lv in edges:
        x = X0 + t * CW
        segs.append((x_now, y_now, x, y_now))
        y_new = yv - A if lv else yv + A
        segs.append((x, y_now, x, y_new))
        x_now, y_now = x, y_new
    segs.append((x_now, y_now, X0 + 8 * CW, y_now))
    for s in segs:
        line(sl, *s, color, 2.0, arrow=False)


wave(rows["bus_valid"], [(1, 2)], COPPER)
line(sl, X0, rows["bus_ready"] - A, X0 + 8 * CW, rows["bus_ready"] - A, PCBMID, 2.0, arrow=False)
wave(rows["bus_rvalid"], [(2, 3)], COPPER)
yr = rows["bus_rdata"]
line(sl, X0, yr, X0 + 2 * CW, yr, INK, 1.25, arrow=False)
box(sl, X0 + 2 * CW, yr - 0.2, CW, 0.4, "D", "mod", size=12)
line(sl, X0 + 3 * CW, yr, X0 + 8 * CW, yr, INK, 1.25, arrow=False)
for t, txt, shift in [(2, "accept", -0.42), (3, "data used", 0.55)]:
    line(sl, X0 + t * CW, 1.6, X0 + t * CW, 6.1, MUTED, 1.0, arrow=False, dash=True)
    lbl(sl, X0 + t * CW + shift, 1.45, txt, 11, MUTED, 0.95, BODY)
textbox(sl, 7.05, 1.5, 5.7, 5.3, [
    "A request is **accepted** on the clock edge where `bus_valid && bus_ready`.",
    "**Write:** takes effect at that same edge.",
    "**Read:** `bus_rdata` arrives with `bus_rvalid` **exactly 1 cycle later**.",
    "`bus_ready` drops only for the one cycle of a soft reset.",
    "The same bus is used by the UART bridge (board), the cocotb tests, the SystemC model and the UVM driver (Phase 6).",
], size=16, kind="char", space=12)

# 11 ------------------------------------------------------------- mm_regs
sl = new_slide("Step 4 — address decode and register map: mm_regs.sv", notes=(
    "The top 4 address bits pick the region; the low 12 bits are the offset. A writes go to bank "
    "= row, address = k; B writes go to bank = column, address = k."))
table(sl, 0.6, 1.45, [2.35, 1.25, 3.1], [
    ["Address", "Name", "Meaning"],
    ["0x0000", "CTRL", "bit0 START, bit1 SOFT_RESET"],
    ["0x0004", "STATUS", "bit0 BUSY, bit1 DONE"],
    ["0x0008", "CFG_K", "K, 1..64"],
    ["0x000C", "INFO", "N, K_MAX, VERSION"],
    ["0x0010–0x0020", "PERF_*", "5 counters (slide 12)"],
    ["0x1000 + i·64 + k", "A_BUF", "A[i][k], one byte"],
    ["0x2000 + k·N + j", "B_BUF", "B[k][j], one byte"],
    ["0x3000 + 4(i·N + j)", "C_BUF", "C[i][j], int32"],
], size=12, row_h=0.4, mono_cols=(0,))
box(sl, 0.6, 5.35, 6.7, 1.2, ["**Try it:** 0x1083 → region 1, offset 131",
                              "row = 131 >> 6 = 2,  k = 131 & 63 = 3  →  **A[2][3]**"], "hot", size=15,
    align=PP_ALIGN.LEFT)
textbox(sl, 7.8, 1.45, 4.9, 0.4, "**How an address is split**", size=17, color=PCB)
box(sl, 7.8, 1.95, 1.35, 0.8, ["[15:12]", "region"], "hot", size=14)
box(sl, 9.15, 1.95, 3.3, 0.8, ["[11:0]", "offset"], "mod", size=14)
textbox(sl, 7.8, 3.05, 4.9, 3.8, [
    "region 0 = registers: `reg_sel = offset[7:2]`",
    "region 1 (A): lane = offset >> 6 = row i, addr = offset[5:0] = k",
    "region 2 (B): lane = offset[1:0] = col j, addr = offset >> 2 = k",
    "region 3 (C): `c_idx = offset[5:2]`",
    "A/B writes are **ignored while BUSY**.",
], size=15, kind="char", space=10)

# 12 ------------------------------------------------------------- perf counters
sl = new_slide("Performance counters (inside mm_regs.sv)", notes=(
    "These are the hardware side of the HW/SW comparison. The same counters exist in the "
    "SystemC model and are compared in co-simulation."))
table(sl, 0.6, 1.45, [2.4, 2.9, 3.2, 1.8, 1.8], [
    ["Counter", "Counts when", "Formula", "N = 4, K = 64", "N = 8, K = 64"],
    ["PERF_TOTAL", "busy and not done", "K + 2N", "72", "80"],
    ["PERF_COMPUTE", "array_en", "K + 2N − 1", "71", "79"],
    ["PERF_FILLDRAIN", "array_en, not all_active", "compute − max(0, K−2N+2)", "13", "29"],
    ["PERF_MACS", "+ N² per rd_en", "N² · K", "1 024", "4 096"],
    ["PERF_IDLE", "not busy (saturates)", "depends on the host", "—", "—"],
], size=14, row_h=0.48, mono_cols=(0,))
textbox(sl, 0.6, 4.55, 7.6, 2.4, [
    "All counters except IDLE reset to 0 on `START`, so each job is measured on its own.",
    "HEX5..HEX0 on the board show `PERF_COMPUTE` of the last job.",
    "The same counters exist in the SystemC model → that is how HW and SW are compared.",
], size=16, kind="char", space=10)
box(sl, 8.6, 4.55, 4.1, 2.1, ["**Utilisation**", "MACS / (N² × COMPUTE)",
                              "**90.1 %** (N = 4)   **81.0 %** (N = 8)"], "hot", size=18)

# 13 ------------------------------------------------------------- banked RAM
sl = new_slide("Step 5 — banked operand RAM: sram_sp.sv", notes=(
    "Each row of A and each column of B has its own small RAM so a whole column of A and a whole "
    "row of B can be read in one cycle at the same address k."))
box(sl, 0.6, 1.5, 5.6, 0.6, "`addr = busy ? rd_addr : wr_addr`", "hot", size=14)
for i in range(4):
    box(sl, 0.6, 2.55 + i * 0.66, 2.6, 0.5, f"A bank {i}: row {i}", "mod", size=14)
    box(sl, 3.6, 2.55 + i * 0.66, 2.6, 0.5, f"B bank {i}: col {i}", "mod", size=14)
line(sl, 1.9, 2.1, 1.9, 2.55)
line(sl, 4.9, 2.1, 4.9, 2.55)
textbox(sl, 0.6, 5.25, 5.6, 0.4, "each RAM: 64 entries × 8 bits", size=13, color=MUTED, align=PP_ALIGN.CENTER)
textbox(sl, 6.8, 1.45, 5.9, 5.4, [
    "The array needs **a whole column of A and a whole row of B every cycle**.",
    "So each row of A and each column of B gets its **own RAM** (N + N = 8 banks), all read at the **same address k**.",
    "`sram_sp` uses the coding pattern Quartus maps to **M9K block RAM**.",
    "**1-cycle read latency:** data appears the cycle after `rd_en`, so `rd_valid` is `rd_en` delayed by one flip-flop.",
    "When `rd_valid = 0`, **zeros** are fed, so the accumulators do not change while the array fills and drains.",
], size=15, kind="char", space=10)

# 14 ------------------------------------------------------------- controller
sl = new_slide("Step 6 — the controller FSM: mm_controller.sv", notes=(
    "Five states. CLEAR zeroes the array, COMPUTE reads K columns, DRAIN lets the last wavefront "
    "reach the bottom-right PE, DONE pulses for one cycle."))
cI = circle(sl, 1.2, 2.2, 1.1, "IDLE", size=11)
cC = circle(sl, 3.5, 2.2, 1.1, "CLEAR", size=11)
cK = circle(sl, 5.8, 2.2, 1.1, "COMPUTE", hot=True, size=10)
cD = circle(sl, 5.8, 4.0, 1.1, "DRAIN", hot=True, size=11)
cN = circle(sl, 3.5, 4.0, 1.1, "DONE", size=11)
link(sl, cI, cC, label="start")
link(sl, cC, cK, label="1 clk")
link(sl, cK, cD, label="K clk", dx=0.5, dy=0)
link(sl, cD, cN, label="2N−1 clk", dy=0.25)
link(sl, cN, cI, label="1 clk", dx=-0.45, dy=0.15)
table(sl, 0.6, 4.95, [2.6, 3.9], [
    ["Output", "High when"],
    ["busy", "state ≠ IDLE"], ["clear", "CLEAR: zero array + skew"],
    ["rd_en, rd_addr = t", "COMPUTE: read column t"], ["array_en", "COMPUTE or DRAIN"],
    ["all_active", "2N−1 ≤ t ≤ K"],
], size=11, row_h=0.33, mono_cols=(0,))
textbox(sl, 7.2, 1.45, 5.5, 5.4, [
    "One step counter `t` runs 0 … K + 2N − 2 across COMPUTE and DRAIN.",
    "**COMPUTE** (t < K): read address t from all 8 RAMs.",
    "**DRAIN**: no reads; zeros flow in while the last values travel to the bottom-right PE.",
    "Last product reaches PE(N−1, N−1) at t = K − 1 + 1 (RAM) + 2(N−1) = **K + 2N − 2**, the last DRAIN step. So C is complete when DONE is entered.",
    "LEDR[2:0] show the state number (0..4).",
], size=15, kind="char", space=10)

# 15 ------------------------------------------------------------- skew
sl = new_slide("Step 7 — skewing the inputs: skew_buffer.sv", notes=(
    "Lane n is delayed by n cycles so that A and B values meet in the right PE on the same cycle."))
for n in range(4):
    yv = 2.0 + n * 0.95
    textbox(sl, 0.6, yv - 0.17, 0.9, 0.34, f"lane {n}", size=13, font=MONO, anchor=MSO_ANCHOR.MIDDLE, space=0)
    line(sl, 1.55, yv, 5.3, yv)
    for r in range(n):
        box(sl, 1.95 + r * 0.72, yv - 0.24, 0.48, 0.48, "R", "hot", size=13)
    textbox(sl, 5.4, yv - 0.17, 1.3, 0.34, f"+{n} cycles", size=13, color=MUTED, anchor=MSO_ANCHOR.MIDDLE, space=0)
textbox(sl, 7.0, 1.45, 5.7, 5.4, [
    "The RAMs give A[0..3][k] all **in the same cycle**.",
    "But PE(i, j) must get A[i][k] and B[k][j] **at the same moment**, and A takes j hops, B takes i hops to get there.",
    "Fix: delay **lane n by n cycles** (a triangle of registers). Everything now meets on a diagonal “wavefront”.",
    "N·(N−1)/2 = **6** registers per buffer for N = 4 (28 for N = 8).",
    "Two copies: one for A (rows), one for B (columns).",
], size=15, kind="char", space=10)

# 16 ------------------------------------------------------------- array
sl = new_slide("Step 8 — the grid: systolic_array.sv", notes=(
    "Two genvar loops create the grid. a moves right, b moves down; each PE accumulates one "
    "element of C."))
GX, GY, PS, SP = 1.85, 2.1, 0.66, 0.92
for i in range(4):
    for j in range(4):
        box(sl, GX + j * SP, GY + i * SP, PS, PS, ["PE", f"{i}{j}"], "mod", size=12)
for i in range(4):
    yv = GY + i * SP + PS / 2
    textbox(sl, 0.45, yv - 0.15, 1.0, 0.3, f"a_in[{i}]", size=11, color=COPPER, font=MONO,
            align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE, space=0)
    line(sl, 1.48, yv, GX, yv)
    for j in range(3):
        line(sl, GX + j * SP + PS, yv, GX + (j + 1) * SP, yv)
for j in range(4):
    xv = GX + j * SP + PS / 2
    lbl(sl, xv, 1.45, f"b_in[{j}]", 11, PCBMID, 0.95)
    line(sl, xv, 1.62, xv, GY, PCBMID)
    for i in range(3):
        line(sl, xv, GY + i * SP + PS, xv, GY + (i + 1) * SP, PCBMID)
textbox(sl, 6.1, 1.45, 6.6, 5.4, [
    "Two `for (genvar …)` loops create **N × N = 16** `pe` instances.",
    "**a** values move **left → right** along a row (wires `a_h[i][j]`).",
    "**b** values move **top → bottom** along a column (wires `b_v[i][j]`).",
    "Each PE keeps its own sum: PE(i, j) **is** C[i][j] (output-stationary).",
    "Only neighbour-to-neighbour wires → short wires → easy to meet 50 MHz.",
    "All 16 accumulators leave on one flat bus `c_out[511:0]`.",
], size=15, kind="char", space=10)

# 17 ------------------------------------------------------------- pe
sl = new_slide("Step 9 — one processing element: pe.sv", notes=(
    "Signed 8x8 multiply into 16 bits, sign-extended to 32 and added into the accumulator. "
    "a and b are also registered and passed to the neighbours."))
textbox(sl, 0.6, 1.35, 4.0, 0.35, "**Compute path**", size=15, color=PCB)
box(sl, 1.35, 2.3, 1.25, 0.9, ["×", "8×8 → 16"], "hot", size=16)
box(sl, 3.05, 2.3, 1.35, 0.9, ["sign ext.", "16 → 32"], "mod", size=13)
box(sl, 4.85, 2.3, 1.05, 0.9, ["+", "32 bit"], "hot", size=16)
box(sl, 4.85, 3.75, 1.05, 0.75, ["acc", "reg [32]"], "mod", size=13)
textbox(sl, 0.45, 2.6, 0.8, 0.3, "a_in", size=12, color=COPPER, font=MONO, space=0)
line(sl, 0.95, 2.75, 1.35, 2.75)
lbl(sl, 2.45, 2.0, "b_in", 12, PCBMID, 0.7)
line(sl, 1.98, 1.85, 1.98, 2.3, PCBMID)
line(sl, 2.6, 2.75, 3.05, 2.75); lbl(sl, 2.83, 2.5, "prod", 10, COPPER, 0.6)
line(sl, 4.4, 2.6, 4.85, 2.6)
line(sl, 5.38, 3.2, 5.38, 3.75)
path(sl, [(4.85, 4.12), (4.6, 4.12), (4.6, 2.98), (4.85, 2.98)])
textbox(sl, 4.7, 4.55, 1.4, 0.3, "= C[i][j]", size=12, color=MUTED, align=PP_ALIGN.CENTER, space=0)
textbox(sl, 0.6, 5.0, 5.5, 0.35, "**Pass-through path (to the neighbours)**", size=15, color=PCB)
textbox(sl, 0.45, 5.48, 0.8, 0.3, "a_in", size=12, color=COPPER, font=MONO, space=0)
line(sl, 1.0, 5.62, 1.6, 5.62)
box(sl, 1.6, 5.4, 1.9, 0.45, "a_out reg [8]", "mod", size=13)
line(sl, 3.5, 5.62, 4.2, 5.62); textbox(sl, 4.25, 5.48, 1.6, 0.3, "PE(i, j+1)", size=12, color=MUTED, space=0)
textbox(sl, 0.45, 6.15, 0.8, 0.3, "b_in", size=12, color=PCBMID, font=MONO, space=0)
line(sl, 1.0, 6.3, 1.6, 6.3, PCBMID)
box(sl, 1.6, 6.08, 1.9, 0.45, "b_out reg [8]", "mod", size=13)
line(sl, 3.5, 6.3, 4.2, 6.3, PCBMID); textbox(sl, 4.25, 6.16, 1.6, 0.3, "PE(i+1, j)", size=12, color=MUTED, space=0)
textbox(sl, 6.6, 1.45, 6.1, 5.4, [
    "`prod = a_in * b_in`: both signed → a signed multiplier (one 9×9 hard multiplier on MAX 10).",
    "Every enabled clock edge: `acc <= acc + 32'(prod);` and `a_out <= a_in; b_out <= b_in;`",
    "`clear` or reset → all three registers = 0.",
    "Worst case: (−128) × (−128) = 16 384 fits in 16 bits; 64 of them fit easily in 32 bits.",
    "Per PE: 32 + 8 + 8 = **48 flip-flops**.",
], size=15, kind="char", space=10)

# 18 ------------------------------------------------------------- timing
sl = new_slide("Timing: when does each value reach each PE?", notes=(
    "A read at step k reaches PE(i, j) at step k + 1 + i + j for both A and B, so the operands "
    "always meet. For N = 4 and K = 64 the job takes 72 cycles."))
textbox(sl, 0.6, 1.4, 12.1, 1.2, [
    "Read issued at step **t = k** → RAM data at **k + 1** → skew adds **i** (A) or **j** (B) → hops add **j** or **i**.",
    "So A[i][k] and B[k][j] **both** arrive at PE(i, j) at step **t = k + 1 + i + j**: they always meet.",
], size=16, kind="char", space=8)
table(sl, 0.9, 2.85, [1.7, 1.6, 1.5, 3.3, 3.4], [
    ["step t", "state", "RAM read", "PE(0,0) gets", "PE(3,3) gets"],
    ["—", "CLEAR", "—", "cleared to 0", "cleared to 0"],
    ["0", "COMPUTE", "k = 0", "0 (zeros fed)", "0"],
    ["1", "COMPUTE", "k = 1", "A[0][0]·B[0][0]", "0"],
    ["7", "COMPUTE", "k = 7", "A[0][6]·B[6][0]", "A[3][0]·B[0][3]"],
    ["64", "DRAIN", "—", "A[0][63]·B[63][0]  (last)", "A[3][57]·B[57][3]"],
    ["70 = K+2N−2", "DRAIN", "—", "0", "A[3][63]·B[63][3]  (last)"],
    ["—", "DONE", "—", "C[0][0] final", "C[3][3] final"],
], size=13, row_h=0.4)
box(sl, 0.9, 6.25, 11.5, 0.55, "N = 4, K = 64:  CLEAR (1) + COMPUTE (64) + DRAIN (7) = **72 cycles = PERF_TOTAL** = 1.44 µs at 50 MHz",
    "hot", size=15)

# 19 ------------------------------------------------------------- read C
sl = new_slide("Step 10 — reading C back", notes=(
    "c_idx selects one accumulator; its 32 bits go back over the bus and the bridge sends them as "
    "4 UART bytes. Reading C over UART takes far longer than computing it."))
box(sl, 0.6, 1.6, 1.4, 0.8, ["16 PEs", "acc"], "hot", size=14)
box(sl, 2.75, 1.6, 2.7, 0.8, ["mux", "`c_out[c_idx*32 +: 32]`"], "mod", size=14)
box(sl, 6.15, 1.6, 2.4, 0.8, ["mm_regs", "bus_rdata (+1 clk)"], "mod", size=14)
box(sl, 9.25, 1.6, 2.8, 0.8, ["bridge", "S_RWAIT → S_SEND"], "mod", size=14)
box(sl, 9.65, 3.1, 2.0, 0.8, ["fifo_sync", "16 bytes"], "mod", size=14)
box(sl, 6.6, 3.1, 2.0, 0.8, ["uart_tx", "434 clk/bit"], "mod", size=14)
box(sl, 3.85, 3.1, 1.7, 0.8, ["PC", "host.py"], "ext", size=14)
line(sl, 2.0, 2.0, 2.75, 2.0); lbl(sl, 2.38, 1.75, "512 bits", 10, COPPER, 0.8)
line(sl, 5.45, 2.0, 6.15, 2.0); lbl(sl, 5.8, 1.75, "32 bits", 10, COPPER, 0.8)
line(sl, 8.55, 2.0, 9.25, 2.0)
line(sl, 10.65, 2.4, 10.65, 3.1); lbl(sl, 11.0, 2.75, "byte", 10, COPPER, 0.6)
line(sl, 9.65, 3.5, 8.6, 3.5)
line(sl, 6.6, 3.5, 5.55, 3.5); lbl(sl, 6.08, 3.25, "TXD", 10, COPPER, 0.6)
textbox(sl, 0.6, 4.4, 12.1, 2.5, [
    "The host reads address `0x3000 + 4(i·N + j)` → `c_idx = i·N + j` selects one 32-bit accumulator.",
    "The bridge sends the 4 bytes little-endian through the 16-byte TX FIFO to `uart_tx`.",
    "16 results × 4 bytes = 64 bytes ≈ 5.6 ms over UART, compared with 1.44 µs of compute → the design is **I/O-bound**.",
], size=16, kind="char", space=10)

# 20 ------------------------------------------------------------- board I/O
sl = new_slide("Board I/O: top_de10lite.sv", notes=(
    "top_de10lite is mostly wiring. Use the LEDs and HEX displays to see what the core is doing "
    "on the real board."))
table(sl, 0.6, 1.45, [1.9, 4.8], [
    ["Pin", "Meaning"],
    ["KEY0", "hold = reset (through sync_2ff)"], ["HEX5..HEX0", "PERF_COMPUTE of last job (hex)"],
    ["LEDR[2:0]", "controller state (0..4)"], ["LEDR3", "busy"],
    ["LEDR5", "UART framing error (sticky)"], ["LEDR6", "unknown command (sticky)"],
    ["LEDR7", "host stalled mid-command"], ["LEDR8", "a job finished since reset"],
    ["LEDR9", "heartbeat, 1 Hz (tick_gen)"], ["GPIO[0] / [1]", "UART_TXD / UART_RXD"],
], size=13, row_h=0.42, mono_cols=(0,))
textbox(sl, 7.7, 1.45, 5.0, 3.6, [
    "`top_de10lite` has **no logic of its own** beyond wiring and a few sticky flags: pins → UART → bridge → core.",
    "Its port names (`MAX10_CLK1_50`, `KEY`, `LEDR`, `HEX0` …) must match the pin file [[quartus/top_de10lite.qsf]].",
    "Quartus builds it with `N = 4, K_MAX = 64` (set in [[tools/gen_quartus.py]]).",
], size=15, kind="char", space=10)
box(sl, 7.7, 5.2, 5.0, 1.15, ["Expected after one job with K = 64:", "HEX shows **000047** (= 71 = PERF_COMPUTE)"],
    "hot", size=15)

# 21 ------------------------------------------------------------- one job
sl = new_slide("One complete job, as the host sees it", notes=(
    "This is exactly what host.py does, and the same sequence drives the SystemC model through "
    "bus_initiator.h."))
cmds = [("W 0x0008 K", "set CFG_K"),
        ("B 0x1000+i·64, K bytes (once per row i)", "load A (N block writes)"),
        ("B 0x2000, K·N bytes", "load B"),
        ("W 0x0000 1", "CTRL.START → controller leaves IDLE"),
        ("R 0x0004 until bit1 = 1", "poll STATUS.DONE"),
        ("D 0x3000, 4·N² bytes", "read C"),
        ("R 0x0010 … 0x0020", "read the 5 performance counters")]
for i, (c, m) in enumerate(cmds):
    yv = 1.45 + i * 0.52
    textbox(sl, 0.6, yv, 0.5, 0.4, f"{i + 1}.", size=16, color=COPPER, bold=True, space=0)
    textbox(sl, 1.1, yv, 6.4, 0.4, c, size=15, font=MONO, space=0)
    textbox(sl, 7.8, yv, 4.9, 0.4, m, size=15, color=MUTED, space=0)
flow = ["load A", "load B", "START", "compute", "poll", "read C", "counters"]
for i, f in enumerate(flow):
    box(sl, 0.6 + i * 1.77, 5.4, 1.45, 0.7, f, "hot" if f == "compute" else "mod", size=14)
    if i < 6:
        line(sl, 0.6 + i * 1.77 + 1.45, 5.75, 0.6 + (i + 1) * 1.77, 5.75)
textbox(sl, 0.6, 6.3, 12.1, 0.4, "Code: [[host/host.py]].  Same sequence in the SystemC model: [[model/systemc/bus_initiator.h]]",
        size=13, color=MUTED, align=PP_ALIGN.CENTER)

# 22 ------------------------------------------------------------- cheat sheet
sl = new_slide("RTL patterns used in this project (cheat sheet)", notes=(
    "Recognising these ten patterns lets you read any file in rtl/."))
table(sl, 0.6, 1.45, [3.4, 3.7], [
    ["Pattern", "Example file"],
    ["Register (always_ff, <=)", "pe.sv accumulator"], ["Wires / mux (assign, ?:)", "mm_core addr mux"],
    ["Combinational case (always_comb)", "mm_regs read mux"], ["FSM with typedef enum", "mm_controller, uart_rx, bridge"],
    ["Replication (for genvar)", "systolic_array grid, RAM banks"], ["Parameters + $clog2", "every core file"],
    ["Part-select [n*W +: W]", "flat lane buses"], ["Valid/ready handshake", "register bus, uart_tx"],
    ["2-FF synchronizer", "sync_2ff (KEY, UART_RXD)"], ["Inferred block RAM", "sram_sp"],
], size=13, row_h=0.43)
textbox(sl, 8.1, 1.45, 4.6, 0.4, "**Rules the code follows**", size=17, color=PCB)
textbox(sl, 8.1, 1.95, 4.6, 4.9, [
    "One clock (50 MHz), synchronous active-low reset.",
    "`<=` only in `always_ff`; `=` only in `always_comb`.",
    "Every `case` has a `default` → no latches.",
    "External inputs are synchronized before use.",
    "Pulses (`start`, `done`, `valid`) last exactly one cycle.",
    "No clock is made from logic: slow events use a **tick enable**.",
], size=15, kind="char", space=10)

# 23 ------------------------------------------------------------- learning path
sl = new_slide("Your learning path through the RTL", notes=(
    "Read one file per session, run its test on Ubuntu and look at the waveform before moving on."))
table(sl, 0.6, 1.4, [0.5, 2.6, 4.3, 4.7], [
    ["#", "Read", "Look for", "Try (on Ubuntu)"],
    ["1", "pe.sv", "multiply, accumulate, pass-through regs", "pytest tb/test_pe.py, open waves"],
    ["2", "systolic_array.sv", "how genvar loops wire 16 PEs", "draw the 4×4 grid yourself"],
    ["3", "skew_buffer.sv", "lane n delayed n cycles", "pytest tb/test_skew_buffer.py"],
    ["4", "sram_sp.sv", "1-cycle read latency", "explain why rd_valid exists"],
    ["5", "mm_controller.sv", "5 states, counter t, all_active", "derive K + 2N on paper"],
    ["6", "mm_regs.sv", "address split, counters", "decode 0x2017 by hand (= B[5][3])"],
    ["7", "mm_core.sv", "how files 1–6 connect", "trace one value from RAM to PE(3,3)"],
    ["8", "uart_rx.sv / uart_tx.sv", "434 clocks per bit", "pytest tb/test_uart_rx.py"],
    ["9", "uart_bus_bridge.sv", "command FSM", "send a P command in the test"],
    ["10", "top_de10lite.sv", "board wiring, LEDs, HEX", "tools/build.sh, program the board"],
], size=12, row_h=0.4, mono_cols=(1,))
box(sl, 0.6, 6.05, 12.1, 0.75, "**Exercise:** change `2N-1` to `2N-2` in [[mm_controller.sv]], run the tests, see which one fails, "
    "then undo it. (Answer: the FILLDRAIN counter check.)", "hot", size=15, align=PP_ALIGN.LEFT)

# 24 ------------------------------------------------------------- key numbers
sl = new_slide("Key numbers to remember", dark=True, notes=(
    "If you remember only one formula: a value read at step k meets in PE(i, j) at step k + 1 + i + j."))
stats = [("16", "PEs at N = 4 (64 at N = 8)"), ("72", "cycles for one job, N = 4, K = 64"),
         ("90.1 %", "PE utilisation, N = 4, K = 64"), ("434", "clocks per UART bit")]
for i, (big, small) in enumerate(stats):
    x = 0.6 + i * 3.1
    card = box(sl, x, 1.55, 2.8, 1.85, [big, small], "dark", size=40)
    p0 = card.text_frame.paragraphs[0]
    for r in p0.runs:
        r.font.bold, r.font.name = True, HEAD
    for r in card.text_frame.paragraphs[1].runs:
        r.font.size, r.font.color.rgb = Pt(13), ICE
textbox(sl, 0.6, 3.95, 12.1, 3.0, [
    "**Data path:** UART → bridge → bus → mm_regs → RAM banks → skew → 16 PEs → mux → bus → bridge → UART.",
    "**Control path:** mm_regs (START) → mm_controller → clear / rd_en / array_en → counters.",
    "**One formula:** a value from read step k meets in PE(i, j) at step **k + 1 + i + j**.",
], size=18, color=WHITE, kind="char", space=14)

# ------------------------------------------------------------------ save
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("rtl_overview.pptx")
prs.core_properties.title = "RTL of the Systolic-Array Accelerator"
prs.core_properties.subject = "RTL walkthrough, DE10-Lite systolic array"
prs.save(out)
print(f"wrote {out} ({_count[0]} slides)")
