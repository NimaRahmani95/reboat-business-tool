"""
ReBoat Task 2.6 — two-page business plan & sustainability summary (Word).

A short decision document for municipalities, operators and funders. It carries
only the Task 2.6 outputs: viability, the 12-month consolidated P&L with the
investment write-off, the financing routes, and the environmental and social
value of the plant. No engineering or other work-package detail.

This module computes nothing. Every figure arrives in the `summary` dict that
app.py builds from the same engine run that is on screen, so the document and
the tool always agree.
"""

from __future__ import annotations

import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401

from docx import Document  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

import plan_labels as L  # noqa: E402

INK = RGBColor(0x1C, 0x1C, 0x1A)
BLUE = RGBColor(0x34, 0x79, 0x9E)
MUTED = RGBColor(0x5A, 0x67, 0x6E)
GOOD = RGBColor(0x16, 0x70, 0x4E)
CRIT = RGBColor(0xB3, 0x26, 0x1E)
FILL_SOFT = "EAF3F8"
FILL_HEAD = "D5E7F0"
RULE = "A9C9DA"
FONT = "Calibri"

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "reboat_logo.png")
EU_LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "eu_funded_en.png")


# ─────────────────────────────────────────────────────────────────────────────
# Formatting
# ─────────────────────────────────────────────────────────────────────────────
def eur(v, signed=False) -> str:
    if v is None:
        return "—"
    s = f"€{abs(v):,.0f}"
    if v < 0:
        return "−" + s
    return ("+" + s) if signed and v > 0 else s


def x2(v) -> str:
    return "n/a" if v is None else f"{v:.2f}×"


def nf(v, dp=0) -> str:
    return "—" if v is None else f"{v:,.{dp}f}"


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────
_ORDER = {
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
              "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd", "noWrap", "tcMar", "textDirection",
             "tcFitText", "vAlign", "hideMark"],
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
            "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
            "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd", "snapToGrid",
            "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc", "textDirection",
            "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"],
}


def _put(parent, child):
    """Insert `child` into a *Pr element at its schema position (Word rejects out-of-order children)."""
    order = _ORDER[parent.tag.split("}")[1]]
    name = child.tag.split("}")[1]
    for old in parent.findall(child.tag):
        parent.remove(old)
    idx = order.index(name)
    for i, existing in enumerate(list(parent)):
        en = existing.tag.split("}")[1]
        if en in order and order.index(en) > idx:
            existing.addprevious(child)
            return child
    parent.append(child)
    return child


def _shade(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    _put(tc_pr, shd)


def _cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tc_pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side, v in (("top", top), ("start", left), ("bottom", bottom), ("end", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(v))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    _put(tc_pr, mar)


def _borders(table, color=RULE, inside_h=True, outer=True, size=4):
    tbl_pr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        show = (edge in ("top", "bottom") and outer) or (edge == "insideH" and inside_h)
        el.set(qn("w:val"), "single" if show else "nil")
        if show:
            el.set(qn("w:sz"), str(size))
            el.set(qn("w:color"), color)
        b.append(el)
    _put(tbl_pr, b)


def _keep_together(table):
    for i, row in enumerate(table.rows):
        tr_pr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); tr_pr.append(cs)
        if i < len(table.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


def _widths(table, cms):
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    _put(tbl_pr, layout)
    grid = table._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), cms):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), str(int(Cm(sum(cms)).twips))); tbl_w.set(qn("w:type"), "dxa")
    _put(tbl_pr, tbl_w)
    for row in table.rows:
        for cell, w in zip(row.cells, cms):
            cell.width = Cm(w)


def _para(container, text="", size=9.5, bold=False, color=INK, align=None, before=0, after=2, italic=False):
    p = container.add_paragraph()
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), 1.08
    if align is not None:
        p.alignment = align
    if text:
        _run(p, text, size=size, bold=bold, color=color, italic=italic)
    return p


def _run(p, text, size=9.5, bold=False, color=INK, italic=False):
    r = p.add_run(text)
    r.font.name, r.font.size, r.font.bold, r.font.italic = FONT, Pt(size), bold, italic
    r.font.color.rgb = color
    r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    return r


def _cell_text(cell, text, size=9, bold=False, color=INK, align=None, after=0):
    cell.paragraphs[0].text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(0), Pt(after)
    p.paragraph_format.line_spacing = 1.0
    if align is not None:
        p.alignment = align
    _run(p, text, size=size, bold=bold, color=color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    return p


def _heading(doc, text, before=8):
    p = _para(doc, "", before=before, after=3)
    _run(p, text.upper(), size=9, bold=True, color=BLUE)
    p_pr = p._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "4"), ("space", "1"), ("color", RULE)):
        bottom.set(qn(f"w:{k}"), v)
    bdr.append(bottom)
    _put(p_pr, bdr)
    p.paragraph_format.keep_with_next = True
    return p


def _field(p, instr, size=8, color=MUTED):
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, "1"), ("end", None)):
        r = p.add_run()
        r.font.name, r.font.size = FONT, Pt(size)
        r.font.color.rgb = color
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            r._r.append(fc)
        elif text == instr:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = f" {instr} "
            r._r.append(it)
        else:
            r.text = text


# ─────────────────────────────────────────────────────────────────────────────
# Building blocks
# ─────────────────────────────────────────────────────────────────────────────
def _kpi_row(doc, items, width_cm):
    """items: [(label, value, sub, tone)] — one row of figure cards."""
    t = doc.add_table(rows=1, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, outer=False, inside_h=False)
    w = width_cm / len(items)
    _widths(t, [w] * len(items))
    for cell, (label, value, sub, tone) in zip(t.rows[0].cells, items):
        _shade(cell, FILL_SOFT)
        _cell_margins(cell, 80, 80, 110, 110)
        _cell_text(cell, label.upper(), size=7, bold=True, color=MUTED, after=1)
        p = cell.add_paragraph()
        p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing = Pt(0), Pt(1), 1.0
        _run(p, value, size=15, bold=True, color={"good": GOOD, "crit": CRIT}.get(tone, INK))
        p2 = cell.add_paragraph()
        p2.paragraph_format.space_before, p2.paragraph_format.space_after, p2.paragraph_format.line_spacing = Pt(0), Pt(0), 1.0
        _run(p2, sub, size=7.5, color=MUTED)
    # thin white gutters between cards
    for cell in t.rows[0].cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        b = OxmlElement("w:tcBorders")
        for edge in ("start", "end"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "24"); el.set(qn("w:color"), "FFFFFF")
            b.append(el)
        _put(tc_pr, b)
    return t


def _ledger(doc, rows, widths, header=None, right_cols=(1, 2)):
    """rows: [(cells…, style)] where style is '', 'grp', 'total' or 'sub'."""
    n = len(widths)
    t = doc.add_table(rows=0, cols=n)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, inside_h=True)
    if header:
        cells = t.add_row().cells
        for i, h in enumerate(header):
            _shade(cells[i], FILL_HEAD)
            _cell_margins(cells[i], 40, 40, 90, 90)
            _cell_text(cells[i], h.upper(), size=7, bold=True, color=MUTED,
                       align=WD_ALIGN_PARAGRAPH.RIGHT if i in right_cols else None)
    for *vals, style in rows:
        cells = t.add_row().cells
        for i, v in enumerate(vals):
            _cell_margins(cells[i], 28, 28, 90, 90)
            bold = style in ("grp", "total")
            if style == "grp":
                _shade(cells[i], FILL_SOFT)
            txt = ("    " + v) if (style == "sub" and i == 0) else v
            color = INK
            if style == "total" and i == 1 and isinstance(v, str) and v.startswith("−"):
                color = CRIT
            _cell_text(cells[i], txt, size=8.5, bold=bold, color=color,
                       align=WD_ALIGN_PARAGRAPH.RIGHT if i in right_cols else None)
    _widths(t, widths)
    _keep_together(t)
    return t


def _season_chart(months, width_cm=17.0, height_cm=4.4) -> io.BytesIO:
    labels = [m[0] for m in months]
    rev = [m[1] for m in months]
    opx = [m[2] for m in months]
    fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54), dpi=220)
    xs = range(len(months))
    w = 0.38
    ax.bar([x - w / 2 for x in xs], rev, w, color="#34799E", label="Revenue")
    ax.bar([x + w / 2 for x in xs], opx, w, color="#B9C7CE", label="Operating cost")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(labels, fontsize=7, color="#1C1C1A")
    ax.tick_params(axis="y", labelsize=6.5, colors="#5A676E", length=0)
    ax.tick_params(axis="x", length=0)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v/1000:.0f}k"))
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#A9C9DA")
    ax.grid(axis="y", color="#E3ECF1", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.5, frameon=False, loc="upper left", ncol=2, handlelength=1.2)
    fig.tight_layout(pad=0.2)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=220)
    plt.close(fig)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# The document
# ─────────────────────────────────────────────────────────────────────────────
def generate_business_summary_docx(s: dict) -> bytes:
    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    sec.top_margin = sec.bottom_margin = Cm(1.6)
    sec.left_margin = sec.right_margin = Cm(1.9)
    sec.header_distance = sec.footer_distance = Cm(0.8)
    body_w = 21.0 - 2 * 1.9

    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(9.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    # footer
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _run(fp, f"ReBoat · Horizon Europe GA 101182350 · Task 2.6 business plan summary · {s['island']} · page ", size=8, color=MUTED)
    _field(fp, "PAGE")
    _run(fp, " of ", size=8, color=MUTED)
    _field(fp, "NUMPAGES")

    # ── title block ───────────────────────────────────────────────
    hdr = doc.add_table(rows=1, cols=3)
    _borders(hdr, outer=False, inside_h=False)
    _widths(hdr, [3.6, 4.2, body_w - 7.8])
    lc, ec, rc = hdr.rows[0].cells
    if os.path.exists(LOGO):
        lc.paragraphs[0].add_run().add_picture(LOGO, width=Cm(3.4))
    else:
        _cell_text(lc, "ReBoat", size=18, bold=True)
    if os.path.exists(EU_LOGO):
        ec.paragraphs[0].add_run().add_picture(EU_LOGO, width=Cm(3.9))
    else:
        _cell_text(ec, "Funded by the EU", size=8, bold=True)
    lc.vertical_alignment = ec.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    _cell_text(rc, "Business plan & sustainability summary", size=15, bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT, after=2)
    p = rc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_after = Pt(1)
    _run(p, f"{s['island']} · {s['port']}", size=10, bold=True, color=BLUE)
    p = rc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _run(p, f"{s['financing_name']} · one operating year after the project · {s['date']}", size=8, color=MUTED)

    # ── perspective note ──────────────────────────────────────────
    p = _para(doc, "", before=4, after=0)
    _run(p, s["scenario_note"], size=8.5, italic=True, color=MUTED)

    # ── verdict ────────────────────────────────────────────────────
    k = s["kpi"]
    ratio, net = k["ratio"], k["net"]
    if ratio >= 1 and net >= 0:
        v1 = (f"At {s['island']} the plant earns {x2(ratio)} its operating costs over the year, so it needs no "
              f"municipal operating subsidy. After amortising the {eur(s['capex'])} investment over ten years, "
              f"the year closes at {eur(net)}.")
    elif ratio >= 1:
        v1 = (f"At {s['island']} the plant covers its operating costs ({x2(ratio)}) but does not yet recover the "
              f"CapEx amortisation: the year closes at {eur(net)}.")
    else:
        v1 = (f"At these settings the plant does not cover its operating costs at {s['island']} ({x2(ratio)}). "
              f"It would need {eur(k['opex'] - k['revenue'])} of operating support a year.")
    sroi_txt = (f" and returns {x2(k['sroi'])} in societal value ({x2(k.get('sroi_noturn'))} excl. turnover) per euro of annual public grant"
                if k["sroi"] is not None else "; with no public grant on this financing route, a return on grant is not defined")
    v2 = (f" It keeps {nf(k['waste_t'], 1)} t of island waste out of the existing disposal route each year, "
          f"avoids {nf(k['co2_t'], 1)} t gross of waste-transport CO₂{sroi_txt}.")
    be = k.get("breakeven")
    a_ = s["assumptions"]
    v3 = (f" Tourism revenue is the operator's {a_['share']:g}% share of the {eur(k['turnover'])} of packages sold by "
          f"tour operators; the plant breaks even at a share of {be:.1f}%." if be is not None else "")
    p = _para(doc, "", before=6, after=4)
    _run(p, v1, size=10.5, bold=True)
    _run(p, v2, size=10.5)
    if v3:
        _run(p, v3, size=10.5)

    # ── headline figures ──────────────────────────────────────────
    _heading(doc, "Headline figures", before=4)
    pb = k["payback"]
    _kpi_row(doc, [
        (L.KPI["ratio"], x2(ratio), "≥ 1.00× needs no operating subsidy", "good" if ratio >= 1 else "crit"),
        (L.NET, eur(net), "per year, after 10-year straight-line CapEx amortisation", "good" if net >= 0 else "crit"),
        ("Equity payback", "—" if pb is None else f"{pb:.2f} yr", f"on {eur(s['equity'])} of equity", ""),
        ("10-year NPV at 8%", eur(k["npv10"]), f"5-year: {eur(k['npv5'])}", "good" if k["npv10"] >= 0 else "crit"),
    ], body_w)
    _para(doc, "", after=2, size=4)
    _kpi_row(doc, [
        ("Waste diverted", f"{nf(k['waste_t'], 1)} t", f"{nf(k['airspace_m3'])} m³ of landfill space saved", ""),
        ("Gross CO₂ avoided", f"{nf(k['co2_t'], 1)} t",
         f"worth {eur(k['co2_value'])} (€80/t) · transit diesel {nf(k.get('transit_diesel_co2_t', 0), 1)} t", ""),
        ("Municipal saving", eur(k["freight"]), "avoided disposal cost, net of any gate fee", "crit" if k["freight"] < 0 else ""),
        ("Social return (SROI)", x2(k["sroi"]),
         f"excl. turnover: {x2(k.get('sroi_noturn'))}" if k["sroi"] is not None
         else "no public grant on this route", ""),
    ], body_w)

    # ── P&L ───────────────────────────────────────────────────────
    _heading(doc, "12-month profit and loss")
    rev_t, opx_t = k["revenue"], k["opex"]
    share = lambda v, t: f"{v / t * 100:.1f}%" if t else "—"  # noqa: E731
    rows = [(L.REVENUE, eur(rev_t), "100.0%", "grp")]
    rows += [(lbl, eur(v), share(v, rev_t), "sub") for lbl, v in s["revenue_lines"]]
    rows += [(L.OPEX, "−" + eur(opx_t), "100.0%", "grp")]
    rows += [(lbl, "−" + eur(v), share(v, opx_t), "sub") for lbl, v in s["opex_lines"]]
    rows += [
        (L.MARGIN, eur(k["margin"]), f"{share(k['margin'], rev_t)} of revenue", "total"),
        (L.AMORT, "−" + eur(k["amortisation"]), "", "sub"),
        (L.NET, eur(net), "", "total"),
    ]
    _ledger(doc, rows, [10.2, 3.4, body_w - 13.6], header=["Line", "€ per year", "Share"])

    # ── the year month by month (flows on; nothing forces a page break) ──
    _heading(doc, "Through the year")
    months = s["months"]
    below = [m for m in months if m[3] < 1.0]
    weak = min(months, key=lambda m: m[3]); strong = max(months, key=lambda m: m[3])
    _para(doc, (f"Every month is shown with its revenue and operating cost. The weakest month is {weak[4]} "
                f"({x2(weak[3])}) and the strongest is {strong[4]} ({x2(strong[3])}). "
                + ("No month falls below breakeven." if not below else
                   "Every month falls below breakeven." if len(below) == len(months) else
                   f"{len(below)} month{'s' if len(below) != 1 else ''} fall{'s' if len(below) == 1 else ''} below breakeven"
                   + (": " + ", ".join(m[4] for m in below) + "." if len(below) <= 4 else "."))), size=9, after=3).paragraph_format.keep_with_next = True
    doc.add_picture(_season_chart(months, width_cm=body_w), width=Cm(body_w))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER

    _heading(doc, "Financing routes")
    _para(doc, ("The same plant and operating year under the two financing routes the tool models. "
                "This summary uses the highlighted route."), size=9, after=3).paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=7)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, inside_h=True)
    heads = ["Route", "Grant %", "Grant", "Equity", "Payback", "SROI", "SROI excl."]
    for i, h in enumerate(heads):
        c = t.rows[0].cells[i]; _shade(c, FILL_HEAD); _cell_margins(c, 40, 40, 70, 70)
        _cell_text(c, h.upper(), size=7, bold=True, color=MUTED, align=WD_ALIGN_PARAGRAPH.RIGHT if i else None)
    for r in s["routes"]:
        cells = t.add_row().cells
        vals = [r["name"], f"{r['pct']}%", eur(r["grant"]), eur(r["equity"]),
                "—" if r["payback"] is None else f"{r['payback']:.2f} yr", x2(r["sroi"]), x2(r.get("sroi_noturn"))]
        for i, v in enumerate(vals):
            _cell_margins(cells[i], 28, 28, 70, 70)
            if r["selected"]:
                _shade(cells[i], FILL_SOFT)
            _cell_text(cells[i], v, size=8, bold=r["selected"], align=WD_ALIGN_PARAGRAPH.RIGHT if i else None)
    _widths(t, [4.8, 1.7, 2.2, 2.2, 2.1, 2.0, body_w - 15.0])
    _keep_together(t)

    _heading(doc, "Environmental and social value")
    sv = [
        ("Island waste diverted", f"{nf(k['waste_t'], 1)} t/yr", "processed on the quay instead of landfilled or shipped away"),
        ("Landfill space saved", f"{nf(k['airspace_m3'])} m³/yr", "volume the island's landfill no longer has to take"),
        (L.KPI["co2"], f"{nf(k['co2_t'], 1)} t/yr", f"valued at {eur(k['co2_value'])} (€80/t) · gross pre-Task 5.7 LCA"),
        (L.KPI["diesel_co2"], f"{nf(k.get('transit_diesel_co2_t', 0), 1)} t/yr",
         f"indicative vessel transit ({nf(k.get('diesel_litres', 0))} L at 2.68 kg/L), separate"),
        ("Shore power demand", f"{nf(k.get('shore_power_kwh', 0))} kWh/yr", "52 kW plant engineering Scenario B × 8 h/active day"),
        ("Avoided disposal cost", f"{eur(k['avoided'])}/yr", "ferry freight or incineration the municipality no longer pays"),
        ("Gate fee paid", f"{eur(k['gate_paid'])}/yr", "paid by the municipality to the operator for treated waste"),
        ("Municipal saving", f"{eur(k['freight'])}/yr", "avoided disposal cost net of the gate fee"),
        ("Local jobs", f"{nf(k['workers'])} operators", f"{eur(k['wages'])} of wages paid on the island a year"),
        ("Societal value", f"{eur(k['societal'])}/yr", "net municipal saving + local wages + carbon value + turnover + products kept by others"),
        ("Social return on grant", x2(k["sroi"]),
         (f"societal value ÷ {eur(k['grant_annual'])} of grant a year (grant spread over ten years)"
          if k["sroi"] is not None else "not defined: this financing route has no public grant")),
        ("SROI without turnover", x2(k.get("sroi_noturn")), "net municipal saving + wages + carbon value only"),
    ]
    _ledger(doc, [(a, b, c, "") for a, b, c in sv], [4.6, 3.2, body_w - 7.8], header=["Indicator", "Value", "What it means"],
            right_cols=(1,))

    eco = s.get("ecosystem")
    if eco:
        es = eco["summary"]
        ep = eco["params"]
        _heading(doc, "Dynamic ecosystem & archipelago sizing (View 05)")
        eco_rows = [
            ("Archipelago scope", f"{eco['archipelago_name']} ({ep['scope']})", f"{len(eco['islands_in_scope'])} islands simulated over {ep['horizon_years']} yr", ""),
            ("Fleet & operators", f"{es['initial_boats']} -> {es['final_boats']} boat(s) (opt {es['optimal_boats_needed']})",
             f"2nd boat Year {es['second_boat_year'] or 'n/a'} · {es['final_operators']} operators trained", ""),
            ("Horizon waste diverted", f"{nf(es['total_diverted_t'], 1)} t", f"unmet peak waste {nf(es['total_unmet_t'], 1)} t · avg coverage {x2(es['avg_coverage_ratio'])}", ""),
            ("Stakeholder & DPP uptake", f"Muni {es['final_muni_adoption_pct']:.0f}% · Art {es['final_artisan_adoption_pct']:.0f}%",
             f"DMC {es['final_dmc_adoption_pct']:.0f}% · DPP artisan uplift +{es['dpp_uplift_artisan_pp']:.1f} pp", ""),
        ]
        _ledger(doc, eco_rows, [4.6, 4.4, body_w - 9.0], header=["Dimension", "Outcome", "Key ecosystem insight"], right_cols=())

    _heading(doc, "Basis & EU funding disclaimer")
    a = s["assumptions"]
    _para(doc, (f"One operating year of the scenario set in the ReBoat Task 2.6 Digital Tool for Business Plan and Sustainability Evaluation on {s['date']}: "
                f"{s['island']}, {s['financing_name']}, {a['days']}-day campaigns ({a['active_days']} active days in the year) "
                f"with {a['workers']} trained operators. Package prices: {a['price_point']} of the WP4 pricing note "
                f"for the island and season; the operator keeps a {a['share']:g}% share of the package price (placeholder until the "
                f"WP4 agreements); gate fee €{a['gate_fee']:,.0f}/t; textile line {a['textile_rate']:g} kg/h. Other prices and unit "
                f"costs are those set in the tool. CapEx is amortised evenly over ten years and NPV is discounted at 8%. "
                f"These figures describe an operating year after the project; they are not income of the EU-funded pilots. "
                f"Scenario fingerprint {s['fingerprint']} links this summary to the PDF, Excel and JSON exports."),
          size=8, color=MUTED, after=3)
    _para(doc, f"{L.EU_FUNDING_TEXT} {L.EU_DISCLAIMER}", size=7.5, italic=True, color=MUTED, after=0)

    zoom = doc.settings.element.find(qn("w:zoom"))   # python-docx's template omits the required percent
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()
