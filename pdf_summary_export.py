"""
ReBoat Task 2.6 — two-page business plan & sustainability summary (PDF).

The same content as the Word summary (business_summary_export.py), laid out for
sharing and printing. This module computes nothing: every figure arrives in the
`summary` dict that app.py builds from the engine run that is on screen.
"""

from __future__ import annotations

import io
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import plan_labels as L
from business_summary_export import EU_LOGO, LOGO, _season_chart, eur, nf, x2

INK, BLUE, MUTED = colors.HexColor("#1C1C1A"), colors.HexColor("#34799E"), colors.HexColor("#5A676E")
GOOD, CRIT = colors.HexColor("#16704E"), colors.HexColor("#B3261E")
SOFT, HEAD, RULE = colors.HexColor("#EAF3F8"), colors.HexColor("#D5E7F0"), colors.HexColor("#A9C9DA")

# DejaVu ships with matplotlib and covers €, −, ×, ≥ and CO₂.
_TTF = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
try:
    pdfmetrics.registerFont(TTFont("RB", os.path.join(_TTF, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("RB-Bold", os.path.join(_TTF, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("RB-Italic", os.path.join(_TTF, "DejaVuSans-Oblique.ttf")))
    FONT, BOLD, ITAL = "RB", "RB-Bold", "RB-Italic"
except Exception:  # pragma: no cover — fall back to the core fonts
    FONT, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def _st(size=8.5, bold=False, color=INK, align=None, italic=False, leading=None, after=0, before=0):
    return ParagraphStyle("x", fontName=BOLD if bold else (ITAL if italic else FONT), fontSize=size,
                          leading=leading or size * 1.28, textColor=color, alignment=align or 0,
                          spaceAfter=after, spaceBefore=before)


def _esc(t: str) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _heading(text):
    t = Table([[Paragraph(_esc(text.upper()), _st(8.5, True, BLUE))]], colWidths=[17.2 * cm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.6, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
    return t


def _kpi_row(items, width):
    w = width / len(items)
    cells = []
    for label, value, sub, tone in items:
        cells.append([Paragraph(_esc(label.upper()), _st(6.5, True, MUTED)),
                      Paragraph(_esc(value), _st(13.5, True, {"good": GOOD, "crit": CRIT}.get(tone, INK), leading=17)),
                      Paragraph(_esc(sub), _st(6.8, color=MUTED))])
    t = Table([cells], colWidths=[w] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEAFTER", (0, 0), (-2, -1), 3, colors.white),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _ledger(rows, widths, header, right_cols=(1, 2)):
    """rows: [(cells…, style)] with style '', 'grp', 'total' or 'sub'."""
    data, styles = [], [("LINEABOVE", (0, 0), (-1, 0), 0.5, RULE), ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
                        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    data.append([Paragraph(_esc(h.upper()), _st(6.5, True, MUTED, TA_RIGHT if i in right_cols else None))
                 for i, h in enumerate(header)])
    styles.append(("BACKGROUND", (0, 0), (-1, 0), HEAD))
    for r, (*vals, style) in enumerate(rows, 1):
        bold = style in ("grp", "total")
        row = []
        for i, v in enumerate(vals):
            txt = (" " + v) if style == "sub" and i == 0 else v
            col = CRIT if (style == "total" and i == 1 and str(v).startswith("−")) else INK
            row.append(Paragraph(_esc(txt), _st(8, bold, col, TA_RIGHT if i in right_cols else None)))
        data.append(row)
        styles.append(("LINEBELOW", (0, r), (-1, r), 0.25, colors.HexColor("#C9DEE8")))
        if style == "grp":
            styles.append(("BACKGROUND", (0, r), (-1, r), SOFT))
        if style == "total":
            styles.append(("LINEABOVE", (0, r), (-1, r), 0.6, INK))
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(styles))
    return t


def generate_business_summary_pdf(s: dict) -> bytes:
    buf = io.BytesIO()
    W = 17.2 * cm
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.9 * cm, rightMargin=1.9 * cm, topMargin=1.5 * cm,
                            bottomMargin=1.6 * cm, title=f"ReBoat business plan summary — {s['island']}",
                            author="ReBoat Task 2.6", subject="Business plan and sustainability summary")

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(A4[0] / 2, 0.9 * cm,
                                 f"ReBoat · Horizon Europe GA 101182350 · Task 2.6 business plan summary · {s['island']} · "
                                 f"page {d.page} · scenario {s['fingerprint']}")
        canvas.restoreState()

    k, a = s["kpi"], s["assumptions"]
    story = []

    # ── title block
    logo = Image(LOGO, width=3.4 * cm, height=3.4 * cm * 0.32) if os.path.exists(LOGO) else Paragraph("ReBoat", _st(18, True))
    if os.path.exists(LOGO):
        try:
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(LOGO).getSize()
            logo = Image(LOGO, width=3.4 * cm, height=3.4 * cm * ih / iw)
        except Exception:
            pass
    eu_logo = Paragraph("Funded by the EU", _st(8, True))
    if os.path.exists(EU_LOGO):
        try:
            from reportlab.lib.utils import ImageReader
            ew, eh = ImageReader(EU_LOGO).getSize()
            eu_logo = Image(EU_LOGO, width=3.9 * cm, height=3.9 * cm * eh / ew)
        except Exception:
            eu_logo = Image(EU_LOGO, width=3.9 * cm, height=3.9 * cm * 0.27)
    right = [Paragraph("Business plan &amp; sustainability summary", _st(14, True, align=TA_RIGHT, leading=17)),
             Paragraph(_esc(f"{s['island']} · {s['port']}"), _st(9.5, True, BLUE, TA_RIGHT)),
             Paragraph(_esc(f"{s['financing_name']} · one operating year after the project · {s['date']}"),
                       _st(7.8, color=MUTED, align=TA_RIGHT))]
    t = Table([[logo, eu_logo, right]], colWidths=[3.7 * cm, 4.1 * cm, W - 7.8 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [t, Spacer(1, 4), Paragraph(_esc(s["scenario_note"]), _st(8, italic=True, color=MUTED, after=4))]

    # ── verdict
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
    v3 = (f" Tourism revenue is the operator's {a['share']:g}% share of the {eur(k['turnover'])} of packages sold by "
          f"tour operators; the plant breaks even at a share of {be:.1f}%." if be is not None else "")
    story.append(Paragraph(f"<font name='{BOLD}'>{_esc(v1)}</font>{_esc(v2 + v3)}", _st(9.5, leading=13, after=4)))

    # ── headline figures
    pb = k["payback"]
    story += [_heading("Headline figures"), Spacer(1, 3), _kpi_row([
        (L.KPI["ratio"], x2(ratio), "≥ 1.00× needs no operating subsidy", "good" if ratio >= 1 else "crit"),
        (L.NET, eur(net), "per year, after 10-year CapEx amortisation", "good" if net >= 0 else "crit"),
        ("Equity payback", "—" if pb is None else f"{pb:.2f} yr", f"on {eur(s['equity'])} of equity", ""),
        ("10-year NPV at 8%", eur(k["npv10"]), f"5-year: {eur(k['npv5'])}", "good" if k["npv10"] >= 0 else "crit"),
    ], W), Spacer(1, 3), _kpi_row([
        ("Waste diverted", f"{nf(k['waste_t'], 1)} t", f"{nf(k['airspace_m3'])} m³ of landfill space saved", ""),
        ("Gross CO₂ avoided", f"{nf(k['co2_t'], 1)} t",
         f"worth {eur(k['co2_value'])} (€80/t) · transit diesel {nf(k.get('transit_diesel_co2_t', 0), 1)} t", ""),
        ("Municipal saving", eur(k["freight"]), "avoided disposal cost, net of any gate fee", "crit" if k["freight"] < 0 else ""),
        ("Social return (SROI)", x2(k["sroi"]),
         f"excl. turnover: {x2(k.get('sroi_noturn'))}" if k["sroi"] is not None
         else "no public grant on this route", ""),
    ], W)]

    # ── P&L
    rev_t, opx_t = k["revenue"], k["opex"]
    share = lambda v, t: f"{v / t * 100:.1f}%" if t else "—"  # noqa: E731
    rows = [(L.REVENUE, eur(rev_t), "100.0%", "grp")]
    rows += [(lbl, eur(v), share(v, rev_t), "sub") for lbl, v in s["revenue_lines"]]
    rows += [(L.OPEX, "−" + eur(opx_t), "100.0%", "grp")]
    rows += [(lbl, "−" + eur(v), share(v, opx_t), "sub") for lbl, v in s["opex_lines"]]
    rows += [(L.MARGIN, eur(k["margin"]), f"{share(k['margin'], rev_t)} of revenue", "total"),
             (L.AMORT, "−" + eur(k["amortisation"]), "", "sub"),
             (L.NET, eur(net), "", "total")]
    story += [KeepTogether([_heading("12-month profit and loss"), Spacer(1, 3),
                            _ledger(rows, [10.2 * cm, 3.4 * cm, W - 13.6 * cm], ["Line", "€ per year", "Share"])])]

    # ── through the year
    months = s["months"]
    below = [m for m in months if m[3] < 1.0]
    weak, strong = min(months, key=lambda m: m[3]), max(months, key=lambda m: m[3])
    txt = (f"Every month is shown with its revenue and operating cost. The weakest month is {weak[4]} ({x2(weak[3])}) and "
           f"the strongest is {strong[4]} ({x2(strong[3])}). "
           + ("No month falls below breakeven." if not below else
              "Every month falls below breakeven." if len(below) == len(months) else
              f"{len(below)} month{'s' if len(below) != 1 else ''} fall{'s' if len(below) == 1 else ''} below breakeven"
              + (": " + ", ".join(m[4] for m in below) + "." if len(below) <= 4 else ".")))
    story += [CondPageBreak(7 * cm), KeepTogether([_heading("Through the year"),
              Paragraph(_esc(txt), _st(8.5, after=3, before=3)),
              Image(_season_chart(months, width_cm=17.0), width=W, height=W * 4.4 / 17.0)])]

    # ── financing routes
    data = [["Route", "Grant %", "Grant", "Equity", "Payback", "SROI", "SROI excl."]]
    sel = []
    for i, r in enumerate(s["routes"], 1):
        data.append([r["name"], f"{r['pct']}%", eur(r["grant"]), eur(r["equity"]),
                     "—" if r["payback"] is None else f"{r['payback']:.2f} yr",
                     x2(r["sroi"]), x2(r.get("sroi_noturn"))])
        if r["selected"]:
            sel.append(i)
    rws = [(*d, "grp" if i in sel else "") for i, d in enumerate(data[1:], 1)]
    story += [KeepTogether([_heading("Financing routes"),
              Paragraph("The same plant and operating year under the two financing routes the tool models. "
                        "This summary uses the highlighted route.", _st(8.5, after=3, before=3)),
              _ledger(rws, [4.8 * cm, 1.7 * cm, 2.2 * cm, 2.2 * cm, 2.1 * cm, 2.0 * cm, W - 15.0 * cm], data[0],
                      right_cols=(1, 2, 3, 4, 5, 6))])]

    # ── environmental and social value
    sv = [
        ("Island waste diverted", f"{nf(k['waste_t'], 1)} t/yr", "processed on the quay instead of the existing disposal route"),
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
    story += [KeepTogether([_heading("Environmental and social value"), Spacer(1, 3),
              _ledger([(x, y, z, "") for x, y, z in sv], [4.6 * cm, 3.2 * cm, W - 7.8 * cm],
                      ["Indicator", "Value", "What it means"], right_cols=(1,))])]

    eco = s.get("ecosystem")
    if eco:
        es = eco["summary"]
        ep = eco["params"]
        eco_rows = [
            ("Archipelago scope", f"{eco['archipelago_name']} ({ep['scope']})",
             f"{len(eco['islands_in_scope'])} islands simulated over {ep['horizon_years']} yr", ""),
            ("Fleet & operators", f"{es['initial_boats']} -> {es['final_boats']} boat(s) (opt {es['optimal_boats_needed']})",
             f"2nd boat Year {es['second_boat_year'] or 'n/a'} · {es['final_operators']} operators trained", ""),
            ("Horizon waste diverted", f"{nf(es['total_diverted_t'], 1)} t",
             f"unmet peak waste {nf(es['total_unmet_t'], 1)} t · avg coverage {x2(es['avg_coverage_ratio'])}", ""),
            ("Stakeholder & DPP uptake", f"Muni {es['final_muni_adoption_pct']:.0f}% · Art {es['final_artisan_adoption_pct']:.0f}%",
             f"DMC {es['final_dmc_adoption_pct']:.0f}% · DPP artisan uplift +{es['dpp_uplift_artisan_pp']:.1f} pp", ""),
        ]
        story += [KeepTogether([_heading("Dynamic ecosystem & archipelago sizing (View 05)"), Spacer(1, 3),
                  _ledger(eco_rows, [4.6 * cm, 4.4 * cm, W - 9.0 * cm],
                          ["Dimension", "Outcome", "Key ecosystem insight"], right_cols=())])]

    # ── basis & EU disclaimer
    basis = (f"One operating year of the scenario set in the ReBoat Task 2.6 Digital Tool for Business Plan and Sustainability "
             f"Evaluation on {s['date']}: {s['island']}, {s['financing_name']}, {a['days']}-day campaigns ({a['active_days']} active "
             f"days in the year) with {a['workers']} trained operators. Package prices: {a['price_point']} of the WP4 "
             f"pricing note, for the island and season; the operator keeps a {a['share']:g}% share of the package price (placeholder "
             f"until the WP4 agreements); gate fee €{a['gate_fee']:,.0f}/t; textile line {a['textile_rate']:g} kg/h. Other prices and "
             f"unit costs are those set in the tool. CapEx is amortised evenly over ten years and NPV is discounted at 8%. These "
             f"figures describe an operating year after the project; they are not income of the EU-funded pilots. Scenario "
             f"fingerprint {s['fingerprint']} links this summary to the Word summary, the Excel model and the JSON dataset.")
    story += [KeepTogether([
        _heading("Basis & EU funding disclaimer"),
        Paragraph(_esc(basis), _st(7.6, color=MUTED, before=3, after=3)),
        Paragraph(_esc(f"{L.EU_FUNDING_TEXT} {L.EU_DISCLAIMER}"), _st(7.2, italic=True, color=MUTED)),
    ])]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
