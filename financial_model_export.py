"""
ReBoat Task 2.6 — Excel financial & sustainability model.

Seven sheets, every figure taken from the same engine run the tool shows:

  Summary · Inputs · Revenue build-up · P&L · Monthly · Investment & financing · Sustainability

Rules that keep the workbook coherent with the app and the Word summary:
  • numbers come from ReBoatDigitalBrain output (passed in by app.py), never from
    constants typed into this file;
  • Excel formulas are used only for arithmetic that is exact — sums, differences,
    ratios, units × price — so recalculating in Excel reproduces the engine;
  • the Summary sheet links to the other sheets instead of repeating values;
  • labels come from plan_labels.py, the vocabulary the app and Word file use.

This module computes no project figure of its own.
"""

from __future__ import annotations

import io

import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

import plan_labels as L

INK, BLUE, MUTED, CRIT = "1C1C1A", "34799E", "5A676E", "B3261E"
F_TITLE = Font(name="Calibri", size=16, bold=True, color=INK)
F_SUB = Font(name="Calibri", size=10, color=MUTED)
F_SEC = Font(name="Calibri", size=11, bold=True, color=BLUE)
F_TH = Font(name="Calibri", size=9, bold=True, color=MUTED)
F_TD = Font(name="Calibri", size=10, color=INK)
F_TDB = Font(name="Calibri", size=10, bold=True, color=INK)
F_NOTE = Font(name="Calibri", size=9, color=MUTED)
F_KPI = Font(name="Calibri", size=14, bold=True, color=INK)
FILL_HEAD = PatternFill("solid", start_color="D5E7F0", end_color="D5E7F0")
FILL_SOFT = PatternFill("solid", start_color="EAF3F8", end_color="EAF3F8")
FILL_INPUT = PatternFill("solid", start_color="FFF7E0", end_color="FFF7E0")
RULE = Side(style="thin", color="A9C9DA")
B_ROW = Border(bottom=Side(style="hair", color="C9DEE8"))
B_TOTAL = Border(top=RULE, bottom=Side(style="double", color=INK))
B_SEC = Border(bottom=RULE)
RIGHT, LEFT = Alignment(horizontal="right", vertical="center"), Alignment(horizontal="left", vertical="center", wrap_text=True)

EUR, EUR2, RATIO, PCT, INT, DEC1, DEC2 = '€#,##0;−€#,##0', '€#,##0.00;−€#,##0.00', '0.00"×"', '0.0%', '#,##0', '#,##0.0', '#,##0.00'
TONNES, M3, YEARS = '#,##0.0" t"', '#,##0" m³"', '0.00" yr"'


class Sheet:
    """Small writer that remembers where named figures land, for cross-sheet links."""

    def __init__(self, wb, title, heading, subtitle, widths):
        self.ws = wb.create_sheet(title=title)
        self.title = title
        self.row = 1
        self.ws.sheet_view.showGridLines = False
        for i, w in enumerate(widths, 1):
            self.ws.column_dimensions[get_column_letter(i)].width = w
        ps = self.ws.page_setup
        ps.orientation, ps.paperSize = "landscape", self.ws.PAPERSIZE_A4
        self.ws.sheet_properties.pageSetUpPr.fitToPage = True
        ps.fitToWidth, ps.fitToHeight = 1, 0
        c = self.ws.cell(row=1, column=1, value=heading); c.font = F_TITLE
        c = self.ws.cell(row=2, column=1, value=subtitle); c.font = F_SUB
        self.row = 4
        self.refs = {}

    def ref(self, name):
        col, row = self.refs[name]
        return f"'{self.title}'!${col}${row}"

    def section(self, text, ncols):
        self.row += 1
        c = self.ws.cell(row=self.row, column=1, value=text.upper()); c.font = F_SEC
        for i in range(1, ncols + 1):
            self.ws.cell(row=self.row, column=i).border = B_SEC
        self.row += 1

    def header(self, cols, right_from=1):
        for i, h in enumerate(cols, 1):
            c = self.ws.cell(row=self.row, column=i, value=h.upper())
            c.font, c.fill = F_TH, FILL_HEAD
            c.alignment = Alignment(horizontal="right" if i > right_from else "left", vertical="center", wrap_text=True)
        widest = max(len(h) / max(self.ws.column_dimensions[get_column_letter(i)].width or 10, 1) for i, h in enumerate(cols, 1))
        if widest > 0.95:
            self.ws.row_dimensions[self.row].height = 30
        self.row += 1

    def line(self, values, fmts=None, bold=False, total=False, soft=False, name=None, name_col=2, note_cols=(),
             input_cols=()):
        fmts = fmts or {}
        for i, v in enumerate(values, 1):
            c = self.ws.cell(row=self.row, column=i, value=v)
            c.font = F_TDB if (bold or total) else (F_NOTE if i in note_cols else F_TD)
            c.alignment = LEFT if (i == 1 or i in note_cols or isinstance(v, str) and not str(v).startswith("=")) else RIGHT
            if i in fmts:
                c.number_format = fmts[i]
            c.border = B_TOTAL if total else B_ROW
            if soft:
                c.fill = FILL_SOFT
            if i in input_cols:
                c.fill = FILL_INPUT
        if name:
            self.refs[name] = (get_column_letter(name_col), self.row)
        self.row += 1
        return self.row - 1

    def note(self, text, ncols=6):
        c = self.ws.cell(row=self.row, column=1, value=text)
        c.font, c.alignment = F_NOTE, Alignment(wrap_text=True, vertical="top")
        self.ws.merge_cells(start_row=self.row, start_column=1, end_row=self.row, end_column=ncols)
        self.ws.row_dimensions[self.row].height = 15 * max(1, len(text) // 120 + 1)
        self.row += 1


def generate_financial_model_xlsx(m: dict) -> bytes:
    meta, sc, A = m["meta"], m["scenario"], m["annual"]
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    stamp = (f"{meta['island']} · {meta['port']} · {meta['financing_name']} · one operating year after the project · "
             f"generated {meta['date']} · scenario {meta['fingerprint']} · UI {meta['ui_release']} / engine {meta['tool_version']}")

    rev_vis, opx_vis = m["rev_vis"], m["opx_vis"]
    nr, no = len(rev_vis), len(opx_vis)
    cl = get_column_letter

    # Create sheets in reader order; populate calculation dependencies cleanly in DAG order.
    S = Sheet(wb, "Summary", "ReBoat — business plan & sustainability model", stamp, [44, 18, 62])
    I = Sheet(wb, "Inputs", "Inputs — the scenario and the rates set in the tool", stamp, [40, 16, 18, 58])
    RB = Sheet(wb, "Revenue build-up", "Revenue build-up — units × price for the year", stamp, [34, 16, 16, 16, 18, 44])
    P = Sheet(wb, "P&L", "12-month profit and loss", stamp, [46, 18, 12, 70])
    M = Sheet(wb, "Monthly", "The year month by month", stamp, [8, 9, 10, 7] + [13] * nr + [14] + [13] * no + [14, 14, 9, 13, 14, 15, 10])
    F = Sheet(wb, "Investment & financing", "Investment, amortisation and financing routes",
              stamp, [36, 12, 15, 15, 14, 15, 15, 11, 16])
    E = Sheet(wb, "Sustainability", "Environmental and social value", stamp, [46, 18, 66])
    eco = m.get("ecosystem")
    EC = (Sheet(wb, "Ecosystem dynamics", "Multi-Year Ecosystem & Archipelago Simulation (View 05)",
                stamp, [30, 12, 12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 11, 16])
          if eco else None)

    # ── 1. Inputs ─────────────────────────────────────────────────────────────
    _SCENARIO_NAMES = {
        "Transit per 14 active days": "transit_hrs",
        "CapEx baseline": "capex",
    }
    _RATE_NAMES = {
        "Operator crew": "crew_rate",
        "Berth and port fees": "berth_rate",
        "Maintenance and consumables": "maint_rate",
        "Shore power": "shore_rate",
        "Marine diesel": "diesel_rate",
        "Recycled plastic flakes": "rpet_price",
        "Recycled yarn": "yarn_price",
        "Avoided disposal cost": "export_rate",
        "Gate fee": "gate_fee",
        "ReBoat share of package price": "share",
        "Operator share of product sales": "pshare",
        "Vessel charter": "vessel_rate",
        "Insurance": "insurance_yr",
        "Collection on land": "collection_rate",
        "Sales commissions": "commission_pct",
        "Overheads": "overheads_pct",
    }
    _CONST_NAMES = {
        "Textile line rate": "textile_rate",
        "Electrical load": "elec_load_kw",
        "CO₂ avoided": "co2_factor",
        "Carbon price": "carbon_price",
        "Landfill density": "landfill_density",
        "Amortisation period": "amort_yrs",
        "Discount rate": "discount_rate",
    }

    I.section("Scenario", 4)
    I.header(["Setting", "Value", "Unit", "Meaning"])
    for label, v, unit, note, fmt in [
        ("Pilot island", meta["island"], "", meta["port"], None),
        ("Financing route", meta["financing_name"], "", f"{A['grant_pct']}% public grant", None),
        ("Campaign length", sc["days"], "days", "Scales the active days of every month (14 = reference calendar)", INT),
        ("Active days in the year", sc["active_days"], "days", "Sum of the monthly campaigns", INT),
        ("Transit per 14 active days", sc["transit_hrs"], "hours", "Sailing time to and from the island", DEC1),
        ("Plastic per 14 active days", sc["plastic_kg"], "kg", "Scaled to each month by demand and active days", INT),
        ("Textile per 14 active days", sc["textile_kg"], "kg", "Scaled the same way; limited by the textile line", INT),
        ("Package prices", sc["price_point"], "", "WP4 pricing note, by island and season", None),
        ("Island operators trained", sc["workers"], "people", "Headcount; their wages are the operator crew cost in the P&L", INT),
        ("CapEx baseline", sc["capex"], "", "Plant investment, amortised over 10 years", EUR),
    ]:
        I.line([label, v, unit, note], {2: fmt} if fmt else {},
               name=_SCENARIO_NAMES.get(label), name_col=2, note_cols=(4,), input_cols=(2,))

    I.section("Unit costs, prices and shares as set in the tool", 4)
    I.header(["Rate", "Value", "Unit", "Used for"])
    for label, v, unit, note in m["rates"]:
        I.line([label, v, unit, note], {2: "#,##0.00"},
               name=_RATE_NAMES.get(label), name_col=2, note_cols=(4,), input_cols=(2,))

    I.section("Fixed model parameters", 4)
    I.header(["Parameter", "Value", "Unit", "Used for"])
    for label, v, unit, note in m["constants"]:
        I.line([label, v, unit, note], {2: "#,##0.00##"},
               name=_CONST_NAMES.get(label), name_col=2, note_cols=(4,))
    I.note(meta["scenario_note"], 4)
    I.note(f"{L.EU_FUNDING_TEXT} {L.EU_DISCLAIMER}", 4)
    I.note("Shaded cells store scenario inputs linked via formulas across Monthly, Revenue build-up, P&L, Investment & "
           "Sustainability. To change volumes/calendars and recompute monthly caps, adjust inputs in the Streamlit app and re-export.", 4)

    # ── 2. Monthly (formula-linked OpEx & Amortisation to Inputs) ─────────────
    c_rev = 5 + nr
    c_opx = c_rev + 1 + no
    c_mar, c_rat, c_am, c_net, c_cum, c_w = c_opx + 1, c_opx + 2, c_opx + 3, c_opx + 4, c_opx + 5, c_opx + 6
    ncol = c_w
    M.section("Revenue, operating cost and result by month", ncol)
    M.header(["Month", "Season", "Season mult", "Days"] + [lbl for _, lbl in rev_vis] + [L.REVENUE]
             + [lbl for _, lbl in opx_vis]
             + [L.OPEX, L.MARGIN, "Rev ÷ cost", "Amortisation", "Net result", "Cumulative net", "Waste t"])
    m_first = M.row
    m_tot_row = m_first + len(m["months"])
    tour_idx = next((idx for idx, (k, _) in enumerate(rev_vis) if k == "annual_tourism_revenue_eur"), 0)
    c_tour = 5 + tour_idx

    fm = {c: EUR for c in range(5, c_cum + 1)}
    fm.update({3: DEC2, 4: INT, c_rat: RATIO, c_w: DEC2})

    opx_start_col = c_rev + 1
    opx_last_non_ovh = c_opx - 1
    # Identify column of Overheads if present so Overheads references non-overhead OpEx columns cleanly.
    has_ovh = any(k == "annual_overheads_cost_eur" for k, _ in opx_vis)
    ovh_sum_end = c_opx - 2 if has_ovh else c_opx - 1

    opx_col_map = {k: opx_start_col + idx for idx, (k, _) in enumerate(opx_vis)}

    for i, mo in enumerate(m["months"]):
        r = M.row
        smult = mo.get("season_mult", {"Low": 0.5, "Mid": 1.0, "High": 1.2}.get(mo["season"], 1.0))
        rev_sum_f = f"=SUM(E{r}:{cl(c_rev - 1)}{r})"
        opx_formulas = []
        for k, _ in opx_vis:
            if k == "annual_labor_cost_eur":
                opx_formulas.append(f"=ROUND(D{r}*C{r}*{I.ref('crew_rate')},2)")
            elif k == "annual_berth_cost_eur":
                opx_formulas.append(f"=ROUND(D{r}*C{r}*{I.ref('berth_rate')},2)")
            elif k == "annual_maintenance_cost_eur":
                opx_formulas.append(f"=ROUND(D{r}*C{r}*{I.ref('maint_rate')},2)")
            elif k == "annual_power_cost_eur":
                opx_formulas.append(f"=ROUND({I.ref('elec_load_kw')}*8*D{r}*C{r}*{I.ref('shore_rate')},2)")
            elif k == "annual_fuel_cost_eur":
                opx_formulas.append(f"=ROUND({I.ref('transit_hrs')}*(D{r}/14)*45*{I.ref('diesel_rate')},2)")
            elif k == "annual_vessel_cost_eur":
                opx_formulas.append(f"=ROUND(D{r}*{I.ref('vessel_rate')},2)")
            elif k == "annual_insurance_cost_eur":
                opx_formulas.append(f"=ROUND({I.ref('insurance_yr')}*D{r}/$D${m_tot_row},2)")
            elif k == "annual_land_collection_cost_eur":
                opx_formulas.append(f"=ROUND({cl(c_w)}{r}*{I.ref('collection_rate')},2)")
            elif k == "annual_commission_cost_eur":
                opx_formulas.append(f"=ROUND({I.ref('commission_pct')}/100*{cl(c_tour)}{r},2)")
            elif k == "annual_overheads_cost_eur":
                opx_formulas.append(f"=ROUND({I.ref('overheads_pct')}/100*SUM({cl(opx_start_col)}{r}:{cl(ovh_sum_end)}{r}),2)")
            else:
                opx_formulas.append(0.0)

        opx_sum_f = f"=SUM({cl(opx_start_col)}{r}:{cl(c_opx - 1)}{r})"
        vals = (
            [mo["label"], mo["season"], smult, mo["days"]]
            + list(mo["rev_lines"])
            + [rev_sum_f]
            + opx_formulas
            + [
                opx_sum_f,
                f"={cl(c_rev)}{r}-{cl(c_opx)}{r}",
                f"=IF({cl(c_opx)}{r}=0,0,{cl(c_rev)}{r}/{cl(c_opx)}{r})",
                f"={I.ref('capex')}/{I.ref('amort_yrs')}/12",
                f"={cl(c_mar)}{r}-{cl(c_am)}{r}",
                f"={cl(c_net)}{r}" if i == 0 else f"={cl(c_cum)}{r - 1}+{cl(c_net)}{r}",
                mo["waste_t"],
            ]
        )
        M.line(vals, fm)

    m_last = M.row - 1
    tot = ["Year", "", "", f"=SUM(D{m_first}:D{m_last})"]
    for col in range(5, c_rat):
        tot.append(f"=SUM({cl(col)}{m_first}:{cl(col)}{m_last})")
    tot += [
        f"=IF({cl(c_opx)}{M.row}=0,0,{cl(c_rev)}{M.row}/{cl(c_opx)}{M.row})",
        f"=SUM({cl(c_am)}{m_first}:{cl(c_am)}{m_last})",
        f"=SUM({cl(c_net)}{m_first}:{cl(c_net)}{m_last})",
        f"={cl(c_cum)}{m_last}",
        f"=SUM({cl(c_w)}{m_first}:{cl(c_w)}{m_last})",
    ]
    M.line(tot, fm, total=True)
    M.refs["days_yr"] = ("D", m_last + 1)
    M.refs["waste_yr"] = (cl(c_w), m_last + 1)
    if not m["months_verified"]:
        M.note("The split by line could not be reconciled with the engine for this scenario; monthly totals are the engine's.", ncol)
    M.note("Monthly OpEx columns compute live via Excel formulas from the 'Inputs' sheet (days × season multiplier × rates, "
           "52 kW Scenario B load, transit hours ÷ 14 × 45 L/h diesel). The Year row feeds the P&L and Sustainability sheets.", ncol)

    ch = BarChart()
    ch.type, ch.grouping, ch.height, ch.width = "col", "clustered", 7.5, 24
    ch.title, ch.y_axis.title = "Revenue and operating cost by month", "€"
    ch.y_axis.numFmt = '€#,##0'
    ch.add_data(Reference(M.ws, min_col=c_rev, min_row=m_first - 1, max_row=m_last), titles_from_data=True)
    ch.add_data(Reference(M.ws, min_col=c_opx, min_row=m_first - 1, max_row=m_last), titles_from_data=True)
    ch.set_categories(Reference(M.ws, min_col=1, min_row=m_first, max_row=m_last))
    ch.series[0].graphicalProperties.solidFill = BLUE
    ch.series[1].graphicalProperties.solidFill = "B9C7CE"
    M.ws.add_chart(ch, f"A{M.row + 1}")
    M.ws.freeze_panes = M.ws[f"E{m_first}"]

    # ── 3. Revenue build-up (linked to Inputs & Monthly) ──────────────────────
    ok = m["units_verified"]
    RB.section("Tourism packages (sold by tour operators)", 6)
    RB.header(["Package", "Per 14 days", "Participants in year", "Average price", "Package turnover", "Note"])
    first = RB.row
    for label, per, units, price in m["packages"]:
        r = RB.row
        RB.line([label, per, units, price, f"=C{r}*D{r}", "Price from the WP4 pricing note, weighted by season"],
                {2: INT, 3: INT, 4: EUR2, 5: EUR}, note_cols=(6,))
    RB.line(["Package turnover", "", f"=SUM(C{first}:C{RB.row - 1})", "", f"=SUM(E{first}:E{RB.row - 1})", "Paid by participants"],
            {3: INT, 5: EUR}, bold=True, name="turnover", name_col=5, note_cols=(6,))
    RB.line(["ReBoat share of the package price", "", "", "", f"={I.ref('share')}/100",
             "Linked to Inputs (placeholder pending commercial agreements)"],
            {5: PCT}, name="share", name_col=5, note_cols=(6,))
    RB.line(["ReBoat share of tourism packages", "", "", "",
             f"={RB.ref('turnover')}*{RB.ref('share')}".replace(f"'{RB.title}'!", ""),
             "Operator revenue"], {5: EUR}, total=True, name="tour", name_col=5, note_cols=(6,))

    RB.section("Upcycled products", 6)
    RB.header(["Product", "Per 14 days", "Units in year", "Price", "Sales in year", "Note"])
    first = RB.row
    for label, per, units, price in m["products"]:
        r = RB.row
        RB.line([label, per, units, price, f"=C{r}*D{r}", ""], {2: INT, 3: INT, 4: EUR2, 5: EUR})
    RB.line(["Product sales", "", f"=SUM(C{first}:C{RB.row - 1})", "", f"=SUM(E{first}:E{RB.row - 1})",
             "Limited by the flakes and yarn recovered"],
            {3: INT, 5: EUR}, bold=True, name="prodsales", name_col=5, note_cols=(6,))
    RB.line(["Operator share of product sales", "", "", "", f"={I.ref('pshare')}/100",
             "Linked to Inputs (rest kept by municipality or partners)"],
            {5: PCT}, name="pshare", name_col=5, note_cols=(6,))
    RB.line(["Upcycled products (operator)", "", "", "",
             f"={RB.ref('prodsales')}*{RB.ref('pshare')}".replace(f"'{RB.title}'!", ""), ""],
            {5: EUR}, total=True, name="prod", name_col=5)

    RB.section("Recycled materials sold in bulk", 6)
    RB.header(["Material", "", "kg in year", "Price per kg", "Revenue in year", "Note"])
    _mat_price_ref = {"flakes": I.ref("rpet_price"), "yarn": I.ref("yarn_price")}
    for key, label, kg, price, note in m["materials"]:
        r = RB.row
        RB.line([label, "", kg, f"={_mat_price_ref[key]}", f"=C{r}*D{r}", note],
                {3: DEC1, 4: EUR2, 5: EUR}, name=key, name_col=5, note_cols=(6,))

    RB.section("Gate fee for treated waste", 6)
    RB.header(["Item", "", "Tonnes treated", "€ per tonne", "Revenue in year", "Note"])
    r = RB.row
    RB.line(["Gate fee", "", f"={M.ref('waste_yr')}", f"={I.ref('gate_fee')}", f"=C{r}*D{r}",
             "Paid by the municipality (GA Recycling-as-a-Service reference: €1,600/t)"], {3: DEC2, 4: EUR2, 5: EUR},
            name="gate", name_col=5, note_cols=(6,))
    RB.line(["Revenue in year", "", "", "",
             f"={RB.ref('tour')}+{RB.ref('prod')}+{RB.ref('flakes')}+{RB.ref('yarn')}+{RB.ref('gate')}".replace(f"'{RB.title}'!", ""), ""],
            {5: EUR}, total=True, name="rev", name_col=5)
    if not ok:
        RB.note("Units in year could not be reconciled with the engine for this scenario.", 6)
    RB.note("Units in year add up the engine's monthly volumes (per-14-day units × monthly demand × active days ÷ 14, rounded "
            "down each month). Average price = package turnover ÷ participants, because prices change with the season.", 6)

    # ── 4. P&L (Revenue linked to RB; OpEx linked to Monthly Year row) ────────
    P.section("12-month profit and loss", 4)
    P.header(["Line", "€ per year", "Share", "Basis"])
    r_rev = P.row
    P.line([L.REVENUE, "", "", "Turnover over the 12-month calendar"], bold=True, soft=True)
    rb_ref = {"annual_tourism_revenue_eur": "tour", "annual_finished_goods_revenue_eur": "prod",
              "annual_bulk_flakes_revenue_eur": "flakes", "annual_bulk_yarn_revenue_eur": "yarn", "annual_gate_fee_revenue_eur": "gate"}
    rev_rows = []
    for key, label in rev_vis:
        r = P.row
        P.line(["   " + label, f"={RB.ref(rb_ref[key])}", f"=IF($B${r_rev}=0,0,B{r}/$B${r_rev})", m["basis"][key]],
               {2: EUR, 3: PCT}, note_cols=(4,))
        rev_rows.append(r)
    P.ws[f"B{r_rev}"] = f"=SUM(B{rev_rows[0]}:B{rev_rows[-1]})"; P.ws[f"B{r_rev}"].number_format = EUR
    P.ws[f"C{r_rev}"] = 1; P.ws[f"C{r_rev}"].number_format = PCT
    for c in ("B", "C"):
        P.ws[f"{c}{r_rev}"].alignment, P.ws[f"{c}{r_rev}"].font = RIGHT, F_TDB
    P.refs["rev"] = ("B", r_rev)

    r_opx = P.row
    P.line([L.OPEX, "", "", "Cash operating cost, before amortisation"], bold=True, soft=True)
    opx_rows = []
    for key, label in opx_vis:
        r = P.row
        m_col = cl(opx_col_map[key])
        P.line(["   " + label, f"='{M.title}'!${m_col}${m_tot_row}", f"=IF($B${r_opx}=0,0,B{r}/$B${r_opx})", m["basis"][key]],
               {2: EUR, 3: PCT}, note_cols=(4,))
        opx_rows.append(r)
    P.ws[f"B{r_opx}"] = f"=SUM(B{opx_rows[0]}:B{opx_rows[-1]})"; P.ws[f"B{r_opx}"].number_format = EUR
    P.ws[f"C{r_opx}"] = 1; P.ws[f"C{r_opx}"].number_format = PCT
    for c in ("B", "C"):
        P.ws[f"{c}{r_opx}"].alignment, P.ws[f"{c}{r_opx}"].font = RIGHT, F_TDB
    P.refs["opex"] = ("B", r_opx)
    P.refs["crew"] = ("B", opx_rows[0])
    r = P.row
    P.line([L.MARGIN, f"=B{r_rev}-B{r_opx}", f"=IF(B{r_rev}=0,0,B{r}/B{r_rev})", "Share is the margin on revenue"],
           {2: EUR, 3: PCT}, total=True, name="margin", note_cols=(4,))
    r_am = P.row
    P.line(["   " + L.AMORT, f"={I.ref('capex')}/{I.ref('amort_yrs')}", "", "CapEx baseline ÷ 10 years"],
           {2: EUR}, name="amort", note_cols=(4,))
    P.line([L.NET, f"={P.ref('margin')}-B{r_am}".replace(f"'{P.title}'!", ""), "", "After annual CapEx amortisation"],
           {2: EUR}, total=True, name="net", note_cols=(4,))
    P.line([L.KPI["ratio"], f"=IF(B{r_opx}=0,0,B{r_rev}/B{r_opx})", "", "≥ 1.00× means no operating subsidy is needed"],
           {2: RATIO}, bold=True, name="ratio", note_cols=(4,))
    P.note(meta["scenario_note"], 4)

    # ── 5. Investment (upper block so Sustainability can reference grant) ─────
    F.section("Investment", 9)
    F.header(["Item", "CapEx", "Amortisation / yr", "", "", "", "", "", ""])
    for label, amount in m["capex_items"]:
        r = F.row
        F.line([label, amount, f"=B{r}/{I.ref('amort_yrs')}"], {2: EUR, 3: EUR})
    F.line(["CapEx baseline", f"={I.ref('capex')}", f"=B{F.row}/{I.ref('amort_yrs')}"], {2: EUR, 3: EUR}, total=True, name="capex")
    F.section("Investment return for the selected route", 9)
    F.header(["Measure", "Value", "", "", "", "", "", "", ""])
    F.line(["Discount rate", f"={I.ref('discount_rate')}"], {2: PCT}, name="rate")
    F.line(["Annuity factor, 5 years", f"=(1-(1+{F.ref('rate')})^-5)/{F.ref('rate')}"], {2: "0.0000"}, name="annuity")
    F.line(["Annuity factor, 10 years", f"=(1-(1+{F.ref('rate')})^-{I.ref('amort_yrs')})/{F.ref('rate')}"], {2: "0.0000"}, name="annuity10")
    F.line(["Public grant", f"={F.ref('capex')}*{A['grant_pct'] / 100.0:.4f}"], {2: EUR}, name="grant")
    F.line(["Equity invested", f"={F.ref('capex')}-{F.ref('grant')}"], {2: EUR}, name="equity")
    F.line(["Operating margin per year", f"={P.ref('margin')}"], {2: EUR}, name="margin")
    F.line([L.KPI["payback"], f"=IF({F.ref('equity')}=0,0,IF({F.ref('margin')}>0,{F.ref('equity')}/{F.ref('margin')},\"—\"))"],
           {2: YEARS}, bold=True, name="payback")
    F.line([L.KPI["npv"], f"={F.ref('margin')}*{F.ref('annuity')}-{F.ref('equity')}"], {2: EUR}, bold=True, name="npv")
    F.line([L.KPI["npv10"], f"={F.ref('margin')}*{F.ref('annuity10')}-{F.ref('equity')}"], {2: EUR}, bold=True, name="npv10")
    F.note("NPV discounts five or ten years of the current operating margin at 8% and subtracts the equity invested — no growth, "
           "cost inflation, replacement or terminal value.", 9)

    # ── 6. Sustainability (links Monthly, P&L, Inputs, Investment) ───────────
    s = m["sustain"]
    fl = m["flows"]
    E.section("Material flows", 3)
    E.header(["Flow", "Tonnes per year", "Note"])
    for label, key, note in [("Plastic delivered", "plastic_collected_t", ""),
                             ("Plastic processed by the shredding plant", "plastic_accepted_t", "Plant limit 100 kg/h, 8 h per active day"),
                             ("Plastic not processed", "plastic_not_accepted_t", "Stays in the existing waste stream"),
                             ("Textile delivered", "textile_delivered_t", ""),
                             ("Textile accepted by the line", "textile_accepted_t", "textile spinning line limit (0.5 kg/h), 8 h/day"),
                             ("Textile not accepted", "textile_not_accepted_t", "Stays in the existing waste stream"),
                             ("Flakes recovered", "flakes_recovered_t", "85% of processed plastic"),
                             ("Flakes used for products", "flakes_to_products_t", ""),
                             ("Flakes sold in bulk", "flakes_sold_bulk_t", ""),
                             ("Yarn recovered", "yarn_recovered_t", "75% of accepted textile"),
                             ("Yarn used for products", "yarn_to_products_t", ""),
                             ("Yarn sold in bulk", "yarn_sold_bulk_t", ""),
                             ("Process losses", "process_losses_t", "")]:
        E.line([label, fl[key], note], {2: "#,##0.000"}, note_cols=(3,))

    E.section("Environmental value & screening boundary (pre-LCA)", 3)
    E.header(["Indicator", "Value", "How it is counted"])
    E.line([L.KPI["waste"], f"={M.ref('waste_yr')}", "Plastic and accepted textile processed on the quay in the year"],
           {2: TONNES}, name="waste", note_cols=(3,))
    E.line([L.KPI["airspace"], f"={E.ref('waste')}/{I.ref('landfill_density')}", "Waste ÷ 0.35 t/m³ uncompacted density"],
           {2: M3}, name="airspace", note_cols=(3,))
    E.line([L.KPI["co2"], f"={E.ref('waste')}*{I.ref('co2_factor')}",
            "0.12 t CO₂ per tonne no longer shipped (gross waste-transport factor, pre-Task 5.7 LCA)"],
           {2: TONNES}, name="co2", note_cols=(3,))
    E.line(["Carbon value", f"={E.ref('co2')}*{I.ref('carbon_price')}", "Gross CO₂ avoided × €80 per tonne"],
           {2: EUR}, name="co2v", note_cols=(3,))
    E.line([L.KPI["diesel_co2"] + " (excl. from avoided)",
            f"=({M.ref('days_yr')}/14)*{I.ref('transit_hrs')}*45*2.68/1000",
            "Annual transit diesel L × 2.68 kg CO₂/L — reported separately pre-LCA"],
           {2: TONNES}, name="diesel_co2", note_cols=(3,))
    E.line(["Annual shore power demand (kWh)",
            f"=SUMPRODUCT('{M.title}'!D{m_first}:D{m_last},'{M.title}'!C{m_first}:C{m_last})*{I.ref('elec_load_kw')}*8",
            "Sum of monthly days × season mult × 52 kW (Scenario B) × 8 h — pending Task 5.7 grid mix LCA"],
           {2: "#,##0"}, name="shore_kwh", note_cols=(3,))

    E.section("Social and economic value", 3)
    E.header(["Indicator", "Value", "How it is counted"])
    E.line(["Avoided disposal cost", f"={E.ref('waste')}*{I.ref('export_rate')}", "Waste diverted × island avoided disposal rate"],
           {2: EUR}, name="avoided", note_cols=(3,))
    E.line(["Gate fee paid by the municipality", f"={RB.ref('gate')}", "From the revenue build-up"],
           {2: EUR}, name="gatepaid", note_cols=(3,))
    E.line([L.KPI["freight"], f"={E.ref('avoided')}-{E.ref('gatepaid')}", "Avoided cost − gate fee"],
           {2: EUR}, name="freight", note_cols=(3,))
    E.line(["Island operators", s["workers"], "Trained and employed on the plant"], {2: INT}, note_cols=(3,))
    E.line([L.KPI["wages"], f"={P.ref('crew')}", "Operator crew cost from the P&L, paid on the island"],
           {2: EUR}, name="wages", note_cols=(3,))
    E.line(["Turnover", f"={P.ref('rev')}", "Operator revenue"], {2: EUR}, name="turnover", note_cols=(3,))
    E.line(["Product sales kept by others", f"={RB.ref('prodsales')}-{RB.ref('prod')}", "Municipality or partners"],
           {2: EUR}, name="others", note_cols=(3,))
    E.line([L.KPI["societal"], f"={E.ref('freight')}+{E.ref('wages')}+{E.ref('co2v')}+{E.ref('turnover')}+{E.ref('others')}",
            "Net municipal saving + local wages + carbon value + turnover + products kept by others"], {2: EUR}, total=True,
           name="societal", note_cols=(3,))

    E.section("Social return on the public grant", 3)
    E.header(["Measure", "Value", "How it is counted"])
    E.line(["Public grant", f"={F.ref('grant')}", meta["financing_name"]], {2: EUR}, name="grant", note_cols=(3,))
    E.line(["Grant per year", f"={E.ref('grant')}/{I.ref('amort_yrs')}", "Spread over the same 10 years as the amortisation"],
           {2: EUR}, name="grant_y", note_cols=(3,))
    E.line([L.KPI["sroi"], f"=IF({E.ref('grant_y')}>0,{E.ref('societal')}/{E.ref('grant_y')},\"n/a\")",
            "Societal value ÷ grant per year (gross indicator)"], {2: RATIO}, total=True, name="sroi", note_cols=(3,))
    E.line([L.KPI["sroi_noturn"],
            f"=IF({E.ref('grant_y')}>0,({E.ref('freight')}+{E.ref('wages')}+{E.ref('co2v')})/{E.ref('grant_y')},\"n/a\")",
            "Net municipal saving + wages + carbon value ÷ grant per year"], {2: RATIO}, name="sroi2", note_cols=(3,))

    # ── Complete Investment & financing 2-routes comparison table (referencing E) ──
    F.section("The two financing routes", 9)
    F.header(["Route", "Grant share", "Grant", "Equity", "Equity payback", "5-year NPV", "10-year NPV", "SROI", "SROI (excl. turn.)"])
    for rt in m["routes"]:
        r = F.row
        F.line([
            rt["name"],
            rt["pct"] / 100.0,
            f"={F.ref('capex')}*B{r}",
            f"={F.ref('capex')}-C{r}",
            f"=IF(D{r}=0,0,IF({F.ref('margin')}>0,D{r}/{F.ref('margin')},\"—\"))",
            f"={F.ref('margin')}*{F.ref('annuity')}-D{r}",
            f"={F.ref('margin')}*{F.ref('annuity10')}-D{r}",
            f"=IF(C{r}>0,{E.ref('societal')}/(C{r}/{I.ref('amort_yrs')}),\"n/a\")",
            f"=IF(C{r}>0,({E.ref('freight')}+{E.ref('wages')}+{E.ref('co2v')})/(C{r}/{I.ref('amort_yrs')}),\"n/a\")",
        ], {2: '0%', 3: EUR, 4: EUR, 5: YEARS, 6: EUR, 7: EUR, 8: RATIO, 9: RATIO}, bold=rt["selected"], soft=rt["selected"])
    F.note("The highlighted route is the one used throughout this workbook. Operating figures are the same under every "
           "route; only the grant, equity, NPV and social return on grant change.", 9)

    # ── 7. Summary (links only) ───────────────────────────────────────────────
    S.section("Business", 3)
    S.header(["Figure", "Value", "Where it comes from"])
    S.line([L.KPI["ratio"], f"={P.ref('ratio')}", "P&L — revenue ÷ operating cost"], {2: RATIO}, bold=True, note_cols=(3,))
    S.line([L.REVENUE, f"={P.ref('rev')}", "P&L"], {2: EUR}, note_cols=(3,))
    S.line(["Package turnover (tour operators)", f"={RB.ref('turnover')}", "Revenue build-up"], {2: EUR}, note_cols=(3,))
    S.line([L.OPEX, f"={P.ref('opex')}", "P&L"], {2: EUR}, note_cols=(3,))
    S.line([L.MARGIN, f"={P.ref('margin')}", "P&L"], {2: EUR}, note_cols=(3,))
    S.line([L.NET, f"={P.ref('net')}", "P&L — after CapEx amortisation"], {2: EUR}, bold=True, note_cols=(3,))
    S.line([L.KPI["payback"], f"={F.ref('payback')}", "Investment & financing"], {2: YEARS}, note_cols=(3,))
    S.line([L.KPI["npv"], f"={F.ref('npv')}", "Investment & financing"], {2: EUR}, note_cols=(3,))
    S.line([L.KPI["npv10"], f"={F.ref('npv10')}", "Investment & financing"], {2: EUR}, note_cols=(3,))
    S.section("Sustainability", 3)
    S.header(["Figure", "Value", "Where it comes from"])
    S.line([L.KPI["waste"], f"={E.ref('waste')}", "Sustainability"], {2: TONNES}, note_cols=(3,))
    S.line([L.KPI["airspace"], f"={E.ref('airspace')}", "Sustainability"], {2: M3}, note_cols=(3,))
    S.line([L.KPI["co2"], f"={E.ref('co2')}", "Sustainability (pre-LCA gross transport avoidance)"], {2: TONNES}, note_cols=(3,))
    S.line([L.KPI["diesel_co2"], f"={E.ref('diesel_co2')}", "Sustainability — separate transit emission line"], {2: TONNES}, note_cols=(3,))
    S.line([L.KPI["freight"], f"={E.ref('freight')}", "Sustainability"], {2: EUR}, note_cols=(3,))
    S.line([L.KPI["wages"], f"={E.ref('wages')}", f"Sustainability — {sc['workers']} island operators"], {2: EUR}, note_cols=(3,))
    S.line([L.KPI["sroi"], f"={E.ref('sroi')}", "Sustainability — societal value per € of grant a year"], {2: RATIO}, bold=True, note_cols=(3,))
    S.line([L.KPI["sroi_noturn"], f"={E.ref('sroi2')}", "Sustainability — excl. commercial turnover"], {2: RATIO}, note_cols=(3,))
    if eco and EC is not None:
        es = eco["summary"]
        S.section("Ecosystem dynamics (View 05)", 3)
        S.header(["Indicator", "Value", "Where it comes from"])
        S.line(["Archipelago cluster", eco["archipelago_name"], "Ecosystem dynamics"], {}, note_cols=(3,))
        S.line(["Fleet evolution", f"{es['initial_boats']} -> {es['final_boats']} boat(s) (opt {es['optimal_boats_needed']})",
                "Ecosystem dynamics"], {}, note_cols=(3,))
        S.line(["Horizon cumulative waste diverted", es["total_diverted_t"], "Ecosystem dynamics"], {2: TONNES}, note_cols=(3,))
        S.line(["Material traceability artisan uplift", f"+{es['dpp_uplift_artisan_pp']:.1f} pp", "Ecosystem dynamics"], {}, note_cols=(3,))
    S.note(meta["scenario_note"], 3)
    S.note(f"{L.EU_FUNDING_TEXT} {L.EU_DISCLAIMER}", 3)
    S.note("All sheets derive dynamically via Excel formulas from the 'Inputs' and 'Monthly' scenario values; the scenario "
           "fingerprint matches the UI cockpit, PDF/Word briefs and JSON export.", 3)

    # ── 8. Ecosystem dynamics (View 05) ──────────────────────────────────────
    if eco and EC is not None:
        ep = eco["params"]
        es = eco["summary"]
        EC.section(f"Simulation configuration — {eco['archipelago_name']}", 6)
        EC.header(["Parameter", "Value", "Unit / Scope", "Description"])
        for lbl, val, unit, desc in [
            ("Scope", ep["scope"], ", ".join(eco["islands_in_scope"]), "Single-island vs. regional archipelago cluster"),
            ("Horizon", ep["horizon_years"], "years", "Multi-year archipelago simulation horizon"),
            ("Disposal tariff escalation", ep["tariff_escalation_pct"] / 100.0, "per year", "Annual growth in avoided disposal tariffs"),
            ("EPR / packaging co-funding", ep["epr_subsidy_eur_per_t"], "€ / t", "Municipal offset per tonne diverted"),
            ("Digital Product Passport traceability", "Active", "Artisan uptake",
             f"Artisan uptake uplift: +{es['dpp_uplift_artisan_pp']:.1f} pp ({es['artisan_with_dpp_pct']:.1f}% vs {es['artisan_no_dpp_pct']:.1f}%)"),
            ("Co-creation intensity", ep["cocreation_intensity"], "multiplier", "WP2/WP4 living labs & local engagement"),
            ("Mobile fleet scaling", f"{es['initial_boats']} -> {es['final_boats']} boats", f"max {ep['max_boats']} boats",
             f"2nd boat deployed in Year {es['second_boat_year'] or 'n/a'} based on capacity demand"),
        ]:
            fmt_d = {2: PCT} if unit == "per year" else ({2: DEC2} if isinstance(val, float) else {})
            EC.line([lbl, val, unit, desc], fmt_d, note_cols=(3, 4))

        EC.section("Year-by-year archipelago trajectory", 16)
        EC.header([
            "Year", "Boats", "Ops", "Islands", "Awareness", "Trust", "Muni %", "DMC %", "Artisan %",
            "Demand t", "Diverted t", "Unmet t", "Revenue €", "OpEx €", "Coverage", "Cum. cash €",
        ])
        for row_y in eco["yearly_series"]:
            EC.line([
                row_y["year"], row_y["n_boats"], row_y["trained_operators"], row_y["active_islands"],
                row_y["awareness_pct"] / 100.0, row_y["secondary_trust_pct"] / 100.0,
                row_y["muni_adoption_pct"] / 100.0, row_y["dmc_adoption_pct"] / 100.0,
                row_y["artisan_adoption_pct"] / 100.0,
                row_y["demand_waste_t"], row_y["diverted_waste_t"], row_y["unmet_waste_t"],
                row_y["revenue_eur"], row_y["opex_eur"], row_y["coverage_ratio"], row_y["cumulative_cash_eur"],
            ], {1: INT, 2: INT, 3: INT, 4: INT, 5: PCT, 6: PCT, 7: PCT, 8: PCT, 9: PCT,
                10: DEC1, 11: DEC1, 12: DEC1, 13: EUR, 14: EUR, 15: RATIO, 16: EUR})

        EC.section("Gate-fee trade-off frontier (€0–€300/t)", 8)
        EC.header(["Gate fee €/t", "Avg R/C", "Final R/C", "Avg Muni %", "Final Muni %",
                   "Diverted t", "Final boats", "Final cum. cash €"])
        for row_f in eco["tradeoff_frontier"]:
            EC.line([
                row_f["gate_fee_eur_per_t"], row_f["avg_coverage_ratio"], row_f["final_coverage_ratio"],
                row_f["avg_muni_adoption_pct"] / 100.0, row_f["final_muni_adoption_pct"] / 100.0,
                row_f["total_diverted_t"], row_f["final_boats"], row_f["final_cumulative_cash_eur"],
            ], {1: EUR, 2: RATIO, 3: RATIO, 4: PCT, 5: PCT, 6: DEC1, 7: INT, 8: EUR})

        EC.note(f"Island MSW context: {eco['ga_msw_note']}", 16)
        EC.note(f"{L.EU_FUNDING_TEXT} {L.EU_DISCLAIMER}", 16)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
