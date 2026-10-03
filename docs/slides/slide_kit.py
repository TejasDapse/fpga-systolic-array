"""slide_kit.py -- shared look and drawing helpers for the project slide decks.

Same palette and shapes as 01_rtl_overview/make_rtl_pptx.py.
Used by 02_models_cosim/make_models_pptx.py (and future decks).
"""
import math
import re
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




# ------------------------------------------------------------------ extra helpers
CODE_BG = RGBColor(0xF4, 0xF7, 0xF7)


def code(sl, x, y, w, h, text, size=11, name="Code"):
    """Monospace code block (text: multi-line string)."""
    s = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.adjustments[0] = 0.03
    s.fill.solid()
    s.fill.fore_color.rgb = CODE_BG
    s.line.color.rgb = PCBMID
    s.line.width = Pt(1)
    s.shadow.inherit = False
    s.name = name
    tf = s.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.1)
    tf.margin_top = tf.margin_bottom = Inches(0.06)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for i, ln in enumerate(text.strip("\n").split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = ln if ln else " "
        r.font.size, r.font.name = Pt(size), MONO
        is_comment = ln.lstrip().startswith(("//", "#"))
        r.font.color.rgb = MUTED if is_comment else INK
    return s


def panel(sl, x, y, w, h, heading, items, kind="why", size=14, bullets=True):
    """Why/How card: coloured heading bar + tinted body. items: str or list of str."""
    fill, edge = (COPPER_T, COPPER) if kind == "why" else (TINT, PCBMID)
    body = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    body.adjustments[0] = 0.06
    body.fill.solid()
    body.fill.fore_color.rgb = fill
    body.line.color.rgb = edge
    body.line.width = Pt(1.25)
    body.shadow.inherit = False
    body.name = f"{heading} panel"
    bar = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.42))
    bar.adjustments[0] = 0.3
    bar.fill.solid()
    bar.fill.fore_color.rgb = edge
    bar.line.fill.background()
    bar.shadow.inherit = False
    bar.name = f"{heading} heading"
    tf = bar.text_frame
    tf.margin_left = Inches(0.15)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    runs(tf.paragraphs[0], f"**{heading}**", 15, WHITE)
    textbox(sl, x + 0.12, y + 0.52, w - 0.24, h - 0.6, items, size=size,
            kind=("char" if bullets and not isinstance(items, str) else None), space=6,
            name=f"{heading} text")


def divider(letter, title_text, subtitle, notes=None):
    sl = new_slide(dark=True, notes=notes)
    textbox(sl, 0.8, 2.3, 11.7, 1.0, letter, size=54, color=COPPER, font=HEAD, bold=True)
    textbox(sl, 0.8, 3.35, 11.7, 1.0, title_text, size=34, color=WHITE, font=HEAD, bold=True)
    textbox(sl, 0.8, 4.4, 11.7, 0.8, subtitle, size=18, color=ICE)
    return sl
