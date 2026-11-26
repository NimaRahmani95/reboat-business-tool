"""
ReBoat Digital Tool — Step-by-Step Guided Walkthrough & Plain-Language View Guides.

Pure UI presentation helper around the canonical session state (`SCENARIO_KEYS` & `_eco`)
and computed scenario outputs (`report`, `R`, `eco`). Nothing here alters calculation rules
or triggers duplicate Streamlit session-state warnings.
"""

from __future__ import annotations

import streamlit as st

import plan_labels as PL
import ui
from backend import PACKAGE_DURATIONS, PRICING_NOTE
from stakeholder_data import (
    ARCHIPELAGO_CLUSTERS,
    get_archipelago_for_island,
    get_pilot_profile,
)
from ui import chip, esc, eur, eur_s, html_block, nf, panel, show_note, tile, tiles, x2


GUIDED_STEPS = [
    (1, "Island & Funding Route", "Choose which pilot island to model and how the plant is financed."),
    (2, "Sailing Schedule & Jobs", "Set how long campaigns last, boat travel distance, and local operators."),
    (3, "Island Waste Collected", "Choose how much plastic and textile waste the plant processes."),
    (4, "Eco-Tourism Packages", "Set visitor numbers, package price level, and the operator revenue share."),
    (5, "Upcycled Local Products", "Choose how many recycled products are made and who keeps the sales."),
    (6, "Local Costs, Prices & Gate Fee", "Review daily running costs, municipal savings, optional gate fees, and material prices."),
    (7, "Optional Extra Costs", "Safe to keep at zero for baseline, or test full commercial overheads."),
    (8, "5–10 Year Archipelago Scaling", "Explore multi-island expansion, rising disposal tariffs, and fleet sizing."),
    (9, "Your Results & Downloads", "Read a plain-English summary of all results and jump to charts or downloads."),
]

_GUIDED_CSS = """
<style>
.gm-bar{display:flex; flex-wrap:wrap; gap:6px; margin:4px 0 6px}
.gm-pill{font-family:var(--f-cond); font-size:11px; font-weight:600; letter-spacing:.05em;
  text-transform:uppercase; padding:4px 10px; border-radius:999px; border:1px solid var(--rule);
  color:var(--text-3); background:var(--panel)}
.gm-pill.done{color:var(--good); border-color:color-mix(in srgb, var(--good) 40%, transparent); background:var(--good-ghost)}
.gm-pill.cur{background:var(--inv-bg); color:var(--inv-text); border-color:var(--inv-bg)}
.gm-field{background:var(--panel-2); border-left:3px solid var(--signal-dim); border-radius:8px;
  padding:9px 12px; margin:2px 0 8px; font-size:12.5px; line-height:1.5; color:var(--text-2)}
.gm-field b.gm-ft{display:block; font-size:13px; color:var(--text); margin-bottom:2px}
.gm-field .gm-row{margin-top:2px}
.gm-field .gm-k{font-weight:600; color:var(--text)}
.gm-cap{margin:6px 0 4px}
.gm-track{height:8px; width:100%; border-radius:999px; background:var(--panel-3); overflow:hidden}
.gm-fill{height:100%; border-radius:999px}
.gm-story{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:4px}
.gm-card{background:var(--panel); border-radius:10px; padding:14px 16px; box-shadow:var(--shadow-border);
  font-size:13px; line-height:1.58; color:var(--text-2)}
.gm-card h4{font-size:14px; margin:0 0 6px; color:var(--text)}
@media (max-width:900px){.gm-story{grid-template-columns:1fr}}
</style>
"""


# ── Widget / canonical state sync helpers ────────────────────────────────────
def _sync_canon(canon_key: str, widget_key: str) -> None:
    if widget_key in st.session_state:
        st.session_state[canon_key] = st.session_state[widget_key]


def _sync_island(widget_key: str, apply_presets_fn) -> None:
    if widget_key in st.session_state:
        st.session_state["target_island"] = st.session_state[widget_key]
        apply_presets_fn()
        st.session_state["_g_reset_rev"] = int(st.session_state.get("_g_reset_rev", 0)) + 1


def _sync_stress(widget_key: str, toggle_stress_fn) -> None:
    if widget_key in st.session_state:
        st.session_state["stress_test"] = bool(st.session_state[widget_key])
        toggle_stress_fn()
        st.session_state["_g_stress_rev"] = int(st.session_state.get("_g_stress_rev", 0)) + 1


def _sync_eco(eco_key: str, widget_key: str) -> None:
    if widget_key in st.session_state:
        st.session_state["_eco"][eco_key] = st.session_state[widget_key]


def _set_step(step: int) -> None:
    st.session_state["guided_step"] = max(1, min(len(GUIDED_STEPS), int(step)))


def _field_guide(title: str, what: str, default_note: str, effect: str) -> None:
    html_block(
        f'<div class="gm-field">'
        f'<b class="gm-ft">{esc(title)}</b>'
        f'<div class="gm-row"><span class="gm-k">What this is:</span> {what}</div>'
        f'<div class="gm-row"><span class="gm-k">Why this default:</span> {default_note}</div>'
        f'<div class="gm-row"><span class="gm-k">If you change it:</span> {effect}</div>'
        f'</div>'
    )


def _cap_bar(label: str, used: float, cap: float, unit: str = "kg") -> None:
    pct_val = (used / cap * 100.0) if cap > 0 else 0.0
    width_pct = min(100.0, pct_val)
    color = "var(--warn)" if used > cap else "var(--good)"
    status = "Over single-campaign cap — excess stays unprocessed" if used > cap else "Within machine capacity"
    html_block(
        f'<div class="gm-cap">'
        f'<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-2);margin-bottom:4px">'
        f'<span><b>{esc(label)}:</b> {nf(used)} / {nf(cap)} {esc(unit)} ({pct_val:.0f}%)</span>'
        f'<span style="color:{color};font-weight:600">{esc(status)}</span></div>'
        f'<div class="gm-track"><div class="gm-fill" style="width:{width_pct:.1f}%;background:{color}"></div></div>'
        f'</div>'
    )


# ── Focused sidebar & header ─────────────────────────────────────────────────
def render_guided_sidebar(step: int, island: str, on_exit, on_change_island, logo_html: str, ui_release: str) -> None:
    """Focused 1–9 progress rail shown instead of the technical 30-field sidebar."""
    with st.sidebar:
        html_block(
            f'<div class="brand">{logo_html}'
            f'<span class="eyebrow">Guided Setup · Task 2.6</span></div>'
            f'<div class="railstate"><span class="eyebrow">Active island</span>{chip(esc(island), "neutral", True)}</div>'
        )
        for num, name, _ in GUIDED_STEPS:
            prefix = "● " if num == step else ("✓ " if num < step else f"{num}. ")
            st.button(
                f"{prefix}{name}",
                key=f"gs_nav_{num}",
                on_click=_set_step,
                args=(num,),
                type="primary" if num == step else "secondary",
                width="stretch",
            )
        html_block('<div style="margin-top:8px;padding-top:10px;border-top:1px solid var(--rule)"></div>')
        if step < 9:
            st.button("Skip to Results (Step 9)", key="gs_skip_end", on_click=_set_step, args=(9,), width="stretch")
        st.button(
            "Open full dashboard",
            key="gs_open_dash",
            on_click=on_exit,
            kwargs={"target_url": "overview", "keep_hints": True},
            type="primary" if step == 9 else "secondary",
            width="stretch",
        )
        st.button(
            "← Change island / mode",
            key="gs_change_isl",
            on_click=on_change_island,
            width="stretch",
        )
        html_block(
            '<p class="railhint" style="margin-top:6px">Every number you adjust is saved automatically and carried into all '
            '5 dashboard views and downloadable files.</p>'
            f'<p class="railhint">Release {esc(ui_release)} · All Rights Reserved (see LICENSE)</p>'
        )


def _render_live_strip(R: dict, SCN: dict, eco: dict) -> None:
    ratio = R["annual_revenue_to_opex_ratio"]
    net = R["annual_net_after_capex_eur"]
    waste = R["annual_waste_diverted_tonnes"]
    muni = R["annual_municipal_savings_eur"]

    if ratio >= 1.0 and net >= 0:
        kind = "good"
        verdict = (f"Financially healthy: annual revenue covers running costs by {x2(ratio)}, and still leaves "
                   f"{eur_s(net)}/yr after equipment depreciation.")
    elif ratio >= 1.0:
        kind = "warn"
        verdict = (f"Covers day-to-day running costs ({x2(ratio)}), but annual net result after 10-year equipment "
                   f"depreciation is {eur_s(net)}/yr.")
    else:
        kind = "crit"
        verdict = (f"Running costs exceed revenue ({x2(ratio)}, {eur_s(net)}/yr). Try raising tourism share, campaign "
                   f"days, or waste/product sales.")

    tiles([
        tile("Revenue / running cost", x2(ratio), lead=True,
             chip_html=chip("Above 1.00× = covers costs", "good" if ratio >= 1.0 else "warn", True),
             sub="Must be above 1.00× for the boat to pay its daily bills"),
        tile("Annual net result", eur_s(net),
             sub="Profit or shortfall left each year after equipment depreciation"),
        tile("Waste kept out of landfill", f"{nf(waste, 1)} t/yr",
             sub=f"On {esc(SCN['target_island'])} across ~{nf(R['annual_active_days'])} active operating days/yr"),
        tile("Municipal net saving", eur_s(muni),
             sub="What the municipality avoids paying for waste shipping or disposal, minus any gate fee"),
    ])
    show_note("Live check on your scenario", verdict, kind)


def _render_progress_header(step: int, scn: dict, fin_name_fn) -> None:
    _, title, subtitle = GUIDED_STEPS[step - 1]
    ui.masthead(
        f"GUIDED WALKTHROUGH · STEP {step} OF {len(GUIDED_STEPS)} · {scn['target_island'].upper()}",
        title,
        [("Island", scn["target_island"]), ("Financing", fin_name_fn(scn["capex_scenario"])),
         ("Campaign", f"{scn['op_days']} days"), ("Share", f"{scn['reboat_share']:.1f}%")],
    )
    pills = []
    for n, name, _ in GUIDED_STEPS:
        cls = "cur" if n == step else ("done" if n < step else "")
        pills.append(f'<span class="gm-pill {cls}">{n}. {esc(name)}</span>')
    html_block(f'{_GUIDED_CSS}<div class="gm-bar">{"".join(pills)}</div>'
               f'<p style="color:var(--text-2);font-size:14px;margin:4px 0 2px">{esc(subtitle)}</p>')


# ── Step renderers (1–9) ─────────────────────────────────────────────────────
def _step_1(scn: dict, report: dict, meta: dict, cbs: dict) -> None:
    isl_opts = list(meta["island_data"].keys())
    fin_labels = meta["financing_labels"]
    fin_opts = list(fin_labels.keys())
    profile = get_pilot_profile(scn["target_island"])
    capex = report["CapEx_Allocation"]

    with panel("Step 1 · Choose your island & funding route", chip("Core context", "neutral", True)):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            _field_guide(
                "Pilot island",
                "Selects the island cluster you want to evaluate.",
                f"Each island comes pre-loaded with validated port fees, sailing hours, local waste volumes, and disposal tariffs (e.g. {esc(profile.get('berth_port', ''))}).",
                "Switches all port, distance, disposal cost, and baseline volume defaults automatically.",
            )
            st.selectbox(
                "Pilot island",
                isl_opts,
                index=isl_opts.index(scn["target_island"]),
                key="g_target_island",
                on_change=_sync_island,
                args=("g_target_island", cbs["apply_presets"]),
            )
            pop = profile.get("population_permanent")
            show_note(
                f"{esc(scn['target_island'])} snapshot",
                f"<b>Berth port:</b> {esc(profile.get('berth_port', '—'))} · "
                f"<b>Residents:</b> {'—' if pop is None else nf(pop)} · "
                f"<b>Disposal context:</b> {esc(profile.get('landfill_status', '—'))}",
            )
        with c2:
            _field_guide(
                "Financing route (how the boat is bought)",
                "Determines what share of the upfront equipment cost is covered by public grants vs. paid back by the operator.",
                "EU / Regional Public Grant is the reference public co-funding route; Municipal PPP (50%) and Private Investment (0% grant) test commercial bankability.",
                "Changes the equity you must recover (payback & NPV) and the Social Return on Investment (SROI) per public euro.",
            )
            st.selectbox(
                "Financing route",
                fin_opts,
                index=fin_opts.index(scn["capex_scenario"]),
                format_func=lambda k: fin_labels[k],
                key="g_capex_scenario",
                on_change=_sync_canon,
                args=("capex_scenario", "g_capex_scenario"),
            )
            show_note(
                "What this means for upfront capital",
                f"Total CapEx baseline: <b>{eur(scn['proxy_capex'])}</b> → "
                f"Public grant pays <b>{eur(capex['grant_coverage_eur'])} ({capex['coverage_percent']}%)</b> · "
                f"Operator / investors fund <b>{eur(capex['net_equity_required_eur'])}</b>.",
                "good" if capex["coverage_percent"] >= 50 else "warn",
            )


def _step_2(scn: dict, R: dict) -> None:
    with panel("Step 2 · Operating schedule, boat travel & local jobs", chip("Operations", "neutral", True)):
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            _field_guide(
                "Campaign length (days per cycle)",
                "How many active recycling days ReBoat spends on the island in each visit cycle.",
                "14 days is the validated reference calendar, giving 191 active days/year across low, mid, and peak seasons.",
                "Longer stays process proportionally more waste and visitors per year, raising both revenue and daily crew/berth bills.",
            )
            st.slider(
                "Campaign length (days)", 1, 60,
                value=int(scn["op_days"]),
                key="g_op_days",
                on_change=_sync_canon,
                args=("op_days", "g_op_days"),
            )
        with c2:
            _field_guide(
                "Marine transit (hours per round-trip)",
                "Sailing time for the boat to arrive at and depart from the island.",
                f"Pre-set to the island's sea leg ({scn['transit_hrs']:.1f} h on {esc(scn['target_island'])}).",
                "More transit hours increase marine diesel fuel expenses and add screening transit CO₂ emissions.",
            )
            st.slider(
                "Marine transit (hours)", 0.0, 72.0, step=0.5,
                value=float(scn["transit_hrs"]),
                key="g_transit_hrs",
                on_change=_sync_canon,
                args=("transit_hrs", "g_transit_hrs"),
            )
        with c3:
            _field_guide(
                "Island operators trained (local jobs)",
                "Number of local crew and island technicians trained to operate the recycling plant.",
                "8 operators is the baseline crew target per vessel across shifts.",
                "Updates local job creation metrics; crew wage cost uses the fixed daily crew budget set in Step 6.",
            )
            st.slider(
                "Island operators trained", 0, 50,
                value=int(scn["workers"]),
                key="g_workers",
                on_change=_sync_canon,
                args=("workers", "g_workers"),
            )
    show_note(
        "Annual operating calendar check",
        f"At <b>{scn['op_days']} days</b> per campaign, the model simulates <b>{nf(R['annual_active_days'])} active working days per year</b> "
        f"and spends <b>{eur(R['annual_fuel_cost_eur'])}/yr</b> on marine transit fuel.",
    )


def _step_3(scn: dict, R: dict, brain) -> None:
    pl_cap = brain.get_plastic_capacity_kg(14)
    tx_cap = brain.get_textile_capacity_kg(14)
    fl = R["material_flows"]
    with panel("Step 3 · Island waste collected per 14 active days", chip("Material throughput", "neutral", True)):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            _field_guide(
                "Plastic delivered (kg per 14 days)",
                "Clean sorted plastic waste (bottles, packaging, HDPE/PET) brought to the boat every two active weeks.",
                "Set to match the island's typical coastal & hospitality recovery rate within boat shredding limits.",
                "Increases recycled flakes, avoided disposal savings, and CO₂ avoided—up to the shredder cap of 11,200 kg (100 kg/h × 8 h/day).",
            )
            st.number_input(
                "Plastic processed (kg)", min_value=0.0, step=100.0,
                value=float(scn["plastic_kg"]),
                key="g_plastic_kg",
                on_change=_sync_canon,
                args=("plastic_kg", "g_plastic_kg"),
            )
            _cap_bar("Plastic vs. shredder capacity (14 days)", scn["plastic_kg"], pl_cap)
            if fl["plastic_not_accepted_t"] > 0:
                show_note("Peak-season plastic overflow",
                          f"Because high-season months scale up by 1.4×, <b>{nf(fl['plastic_not_accepted_t'] * 1000)} kg/yr</b> "
                          f"exceeds shredder capacity in peak months and stays unprocessed.", "warn")
        with c2:
            _field_guide(
                "Textile delivered (kg per 14 days)",
                "End-of-life marine ropes, hotel linens, or coastal textiles delivered for mechanical recycling.",
                "Set at 30% of plastic weight as a collection benchmark; actual yarn output is limited by the on-board spinning bottleneck.",
                f"Textiles above {nf(tx_cap)} kg (0.5 kg/h spinner × 8 h × 14 days) cannot be spun and do not increase yarn output or revenue.",
            )
            st.number_input(
                "Textile processed (kg)", min_value=0.0, step=50.0,
                value=float(scn["textile_kg"]),
                key="g_textile_kg",
                on_change=_sync_canon,
                args=("textile_kg", "g_textile_kg"),
            )
            _cap_bar("Textile vs. spinning line cap (14 days)", scn["textile_kg"], tx_cap)
            if fl["textile_not_accepted_t"] > 0:
                show_note("Why excess textile is capped",
                          f"Annual delivered textile ({nf(fl['textile_delivered_t'] * 1000)} kg) exceeds the spinner line's "
                          f"0.5 kg/h rate; <b>{nf(fl['textile_accepted_t'] * 1000)} kg/yr</b> is recycled into yarn while "
                          f"{nf(fl['textile_not_accepted_t'] * 1000)} kg/yr is left unaccepted.", "warn")


def _step_4(scn: dict, R: dict, meta: dict) -> None:
    price_pts = meta["price_points"]
    price_opts = list(price_pts.keys())
    pkg_keys = meta["pkg_keys"]
    pkg_info = meta["pkg_info"]
    be = R["breakeven_reboat_share_pct"]

    with panel("Step 4 · Circular eco-tourism packages", chip("Main revenue driver", "good", True)):
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            _field_guide(
                "Package price tier",
                "Whether visitors pay the low, midpoint, or high end of the island's validated tourism package price range.",
                "Low end ('Value' B&B / 2–3★ positioning) keeps revenue projections conservative.",
                "Moving from Low to Midpoint or High increases total package turnover and operator revenue immediately.",
            )
            st.selectbox(
                "Package price tier",
                price_opts,
                index=price_opts.index(scn["price_point"]),
                format_func=lambda k: price_pts[k],
                key="g_price_point",
                on_change=_sync_canon,
                args=("price_point", "g_price_point"),
            )
        with c2:
            _field_guide(
                "ReBoat share of package price (%)",
                "Percentage of the total holiday package price that goes to the ReBoat plant operator (the rest stays with tour operators, hotels, and guides).",
                "10.0% is the planning baseline until commercial Destination Management Company (DMC) contracts finalize it.",
                "Directly raises or lowers the operator's largest income stream.",
            )
            st.number_input(
                "ReBoat share of the package price (%)",
                min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                value=float(scn["reboat_share"]),
                key="g_reboat_share",
                on_change=_sync_canon,
                args=("reboat_share", "g_reboat_share"),
            )
            if be is not None:
                be_ok = scn["reboat_share"] >= be
                show_note(
                    "Break-even tourism share",
                    f"To cover all operating expenses, ReBoat needs at least <b>{be:.1f}%</b> of package prices. "
                    f"Your current setting is <b>{scn['reboat_share']:.1f}%</b> "
                    f"({'above break-even ✓' if be_ok else 'below break-even — consider raising share or visitors'}).",
                    "good" if be_ok else "warn",
                )

    with panel("Visitors per 14-day campaign (by experience length)"):
        _field_guide(
            "How the 5 visit tiers work",
            "ReBoat hosts 5 types of eco-tourism visits ranging from a 2-hour boat tour up to a 5-day circular living-lab stay.",
            "Baseline assumes mostly short Day Trips (120 visitors) and progressively fewer multi-day stays.",
            "Adding multi-day stays generates much higher per-person package turnover than short tours.",
        )
        cols = st.columns(len(pkg_keys), gap="small")
        for col, (k, pk) in zip(cols, pkg_keys):
            name, desc = pkg_info[k]
            with col:
                st.number_input(
                    f"{name}",
                    min_value=0, step=1,
                    value=int(scn[f"pkg_{k}"]),
                    key=f"g_pkg_{k}",
                    on_change=_sync_canon,
                    args=(f"pkg_{k}", f"g_pkg_{k}"),
                    help=f"{PACKAGE_DURATIONS[pk]} — {desc}",
                )
                html_block(f'<p class="railhint">{esc(PACKAGE_DURATIONS[pk])}<br>{esc(desc)}</p>')

        tab = PRICING_NOTE.get(scn["target_island"], PRICING_NOTE["Corfu"])
        html_block(
            '<p class="railhint" style="margin-top:8px"><b>Package price floors on '
            + esc(scn["target_island"]) + ' (€/person · low / mid / high season):</b> '
            + " · ".join(f"{esc(pkg_info[k][0])}: €{tab['Low'][i][0]}–{tab['Low'][i][1]} / "
                         f"€{tab['Mid'][i][0]}–{tab['Mid'][i][1]} / €{tab['High'][i][0]}–{tab['High'][i][1]}"
                         for i, (k, _pk) in enumerate(pkg_keys))
            + "</p>"
        )


def _step_5(scn: dict, R: dict) -> None:
    prod_defs = [
        ("prod_molded", "Moulded goods · €12 each", "Small souvenirs, trays, or clips made using the on-board injection moulder."),
        ("prod_3d", "3D-printed artefacts · €35 each", "Custom marine/coastal design objects printed from recycled plastic filament."),
        ("prod_panel", "Furniture panels · €95 each", "Sturdy thermo-pressed architectural or café tabletop sheets."),
        ("prod_textile", "Woven textiles · €45 each", "Artisanal bags or fabric pieces crafted from recycled rope & linen yarn."),
        ("prod_yarn", "Yarn spools · €8 each", "Spools of spun recycled textile yarn sold to local weavers or studios."),
    ]
    with panel("Step 5 · Upcycled circular products sold per campaign", chip("Secondary revenue", "neutral", True)):
        _field_guide(
            "Made on board from your recycled plastic & textile",
            "Units crafted and sold each 14-day campaign. Any recycled flakes or yarn NOT used in these finished products are automatically sold in bulk at market price.",
            "Conservative starter volumes based on pilot workshop capacity.",
            "Shifting material from raw flakes into finished products raises earnings per kilogram of waste.",
        )
        cols = st.columns(5, gap="small")
        for col, (key, label, desc) in zip(cols, prod_defs):
            with col:
                st.number_input(
                    label, min_value=0, step=1,
                    value=int(scn[key]),
                    key=f"g_{key}",
                    on_change=_sync_canon,
                    args=(key, f"g_{key}"),
                )
                html_block(f'<p class="railhint">{esc(desc)}</p>')

        _field_guide(
            "Operator share of product sales (%)",
            "What percentage of finished-goods revenue goes to ReBoat if local artisan shops or the municipality sell the items on commission.",
            "100% means the ReBoat operator sells directly and keeps all product sales.",
            "Lowering below 100% leaves the remainder with island shops and co-selling partners.",
        )
        st.number_input(
            "Operator share of product sales (%)",
            min_value=0.0, max_value=100.0, step=5.0, format="%.0f",
            value=float(scn["prod_share"]),
            key="g_prod_share",
            on_change=_sync_canon,
            args=("prod_share", "g_prod_share"),
        )
        show_note(
            "Combined product & bulk material sales",
            f"Your current mix generates <b>{eur(R['annual_finished_goods_revenue_eur'])}/yr</b> from finished products plus "
            f"<b>{eur(R['annual_bulk_flakes_revenue_eur'] + R['annual_bulk_yarn_revenue_eur'])}/yr</b> from leftover recycled flakes & yarn.",
        )


def _step_6(scn: dict, R: dict) -> None:
    left, right = st.columns(2, gap="medium")
    with left:
        with panel("Plant running & equipment costs", chip("Keep defaults if unsure", "neutral", True)):
            _field_guide(
                "Core vessel, crew & equipment assumptions",
                "Daily crew wages, port berthing, electricity, maintenance, transit fuel price, and initial CapEx.",
                "Pre-filled from port benchmarks, supplier equipment budgets, and shore power tariffs.",
                "Higher daily rates or diesel price reduce annual profit margin; CapEx drives depreciation and payback.",
            )
            c_a, c_b = st.columns(2, gap="small")
            with c_a:
                st.number_input("Marine diesel (€/L)", step=0.05, format="%.2f",
                                value=float(scn["proxy_diesel"]), key="g_proxy_diesel",
                                on_change=_sync_canon, args=("proxy_diesel", "g_proxy_diesel"))
                st.number_input("Berth & port fees (€/day)", step=10.0,
                                value=float(scn["proxy_berth"]), key="g_proxy_berth",
                                on_change=_sync_canon, args=("proxy_berth", "g_proxy_berth"))
                st.number_input("Shore power (€/kWh)", step=0.01, format="%.2f",
                                value=float(scn["proxy_shore"]), key="g_proxy_shore",
                                on_change=_sync_canon, args=("proxy_shore", "g_proxy_shore"))
            with c_b:
                st.number_input("Operator crew (€/day)", step=50.0,
                                value=float(scn["proxy_labor"]), key="g_proxy_labor",
                                on_change=_sync_canon, args=("proxy_labor", "g_proxy_labor"))
                st.number_input("Maintenance & consumables (€/day)", step=10.0,
                                value=float(scn["proxy_maintenance"]), key="g_proxy_maintenance",
                                on_change=_sync_canon, args=("proxy_maintenance", "g_proxy_maintenance"))
                st.number_input("CapEx baseline (€)", step=1000.0, format="%.0f",
                                value=float(scn["proxy_capex"]), key="g_proxy_capex",
                                on_change=_sync_canon, args=("proxy_capex", "g_proxy_capex"))

    with right:
        with panel("Municipal savings, gate fee & material prices", chip("Policy & market prices", "neutral", True)):
            _field_guide(
                "Avoided disposal cost vs. optional Municipal Gate Fee",
                "<b>Avoided disposal cost</b> is money the island automatically saves because ReBoat recycles waste instead of shipping it to the mainland (€150/t) or burning it (Terceira €50/t). "
                "<b>Gate fee</b> is an optional service charge paid by the municipality to ReBoat per tonne.",
                "Gate fee defaults to €0/t (municipalities get 100% of disposal savings); recycled plastic flakes default to €1.50/kg (note: unwashed mixed flakes can trade lower at €0.60–€1.34/kg).",
                "Raising the gate fee shifts value from municipal budgets to boat revenue; lowering flake price tests market discounts.",
            )
            st.number_input("Avoided disposal cost (€/t)", step=10.0,
                            value=float(scn["proxy_export"]), key="g_proxy_export",
                            on_change=_sync_canon, args=("proxy_export", "g_proxy_export"))
            st.number_input("Gate fee charged to municipality (€/t)", min_value=0.0, step=50.0,
                            value=float(scn["gate_fee"]), key="g_gate_fee",
                            on_change=_sync_canon, args=("gate_fee", "g_gate_fee"))
            m1, m2 = st.columns(2, gap="small")
            with m1:
                st.number_input("Recycled plastic flakes (€/kg)", step=0.10, format="%.2f",
                                value=float(scn["proxy_rpet"]), key="g_proxy_rpet",
                                on_change=_sync_canon, args=("proxy_rpet", "g_proxy_rpet"))
            with m2:
                st.number_input("Recycled yarn (€/kg)", step=0.10, format="%.2f",
                                value=float(scn["proxy_yarn"]), key="g_proxy_yarn",
                                on_change=_sync_canon, args=("proxy_yarn", "g_proxy_yarn"))
            show_note(
                "Net effect for the municipality",
                f"Avoided disposal saving <b>{eur(R['annual_avoided_disposal_cost_eur'])}/yr</b> − "
                f"gate fee <b>{eur(R['annual_gate_fee_paid_eur'])}/yr</b> = "
                f"<b>{eur_s(R['annual_municipal_savings_eur'])}/yr</b> net municipal gain.",
                "good" if R["annual_municipal_savings_eur"] >= 0 else "warn",
            )


def _step_7(scn: dict, cbs: dict) -> None:
    with panel("Step 7 · Optional extra commercial costs (Stress test)", chip("Optional — safe at €0", "neutral", True)):
        _field_guide(
            "Why these 5 lines default to €0",
            "Vessel charter, annual insurance, land waste transport, tour-operator sales commissions, and general overheads are kept at €0 in the core reference scenario until partner quotes are finalized.",
            "Switching on the Illustrative Stress Test loads conservative commercial benchmarks (€200/day charter, €6,000/yr insurance, €30/t land collection, 10% commission, 5% overheads) so you can check worst-case resilience.",
            "Increases operating expenses and shows how much tourism revenue share is needed under full commercial overheads.",
        )
        rev = int(st.session_state.get("_g_stress_rev", 0)) + int(st.session_state.get("_g_reset_rev", 0)) * 1000
        st.checkbox(
            "Enable illustrative full-cost stress test",
            value=bool(st.session_state.get("stress_test", False)),
            key=f"g_stress_test_{rev}",
            on_change=_sync_stress,
            args=(f"g_stress_test_{rev}", cbs["toggle_stress"]),
        )
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            st.number_input("Vessel charter (€/active day)", min_value=0.0, step=50.0,
                            value=float(scn["vessel"]), key=f"g_vessel_{rev}",
                            on_change=_sync_canon, args=("vessel", f"g_vessel_{rev}"))
            st.number_input("Insurance (€/year)", min_value=0.0, step=500.0,
                            value=float(scn["insurance"]), key=f"g_insurance_{rev}",
                            on_change=_sync_canon, args=("insurance", f"g_insurance_{rev}"))
        with c2:
            st.number_input("Land collection transport (€/t)", min_value=0.0, step=10.0,
                            value=float(scn["collection"]), key=f"g_collection_{rev}",
                            on_change=_sync_canon, args=("collection", f"g_collection_{rev}"))
            st.number_input("Tour operator commissions (%)", min_value=0.0, max_value=100.0, step=1.0,
                            value=float(scn["commission"]), key=f"g_commission_{rev}",
                            on_change=_sync_canon, args=("commission", f"g_commission_{rev}"))
        with c3:
            st.number_input("General overheads (% of costs)", min_value=0.0, max_value=100.0, step=1.0,
                            value=float(scn["overheads"]), key=f"g_overheads_{rev}",
                            on_change=_sync_canon, args=("overheads", f"g_overheads_{rev}"))


def _step_8(scn: dict, eco: dict) -> None:
    arch_key = get_archipelago_for_island(scn["target_island"])
    cluster = ARCHIPELAGO_CLUSTERS[arch_key]
    es = st.session_state["_eco"]
    scope_opts = ["archipelago", "single_island"]
    sm = eco["summary"]
    horizon = int(es["eco_horizon"])

    with panel(f"Step 8 · Multi-year regional scaling — {esc(cluster['name'])}", chip(f"Cluster: {esc(arch_key)}", "neutral", True)):
        _field_guide(
            "From one pilot island to a 5–10 year regional fleet",
            "Projects how municipalities, tour operators, and local artisans join over time across neighboring islands, and when growing waste demand triggers adding extra ReBoat vessels.",
            "Defaults to the full regional archipelago over 10 years, 4%/yr rising mainland waste tariffs, and up to 4 boats.",
            "Lower horizons or single-island scope restrict scale; adding EPR packaging subsidies helps municipalities stay on board.",
        )
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            st.selectbox(
                "Simulation scope",
                scope_opts,
                index=scope_opts.index(es["eco_scope"]),
                format_func=lambda v: "Regional archipelago (multi-island)" if v == "archipelago" else f"Single island ({scn['target_island']} only)",
                key="g_eco_scope",
                on_change=_sync_eco,
                args=("eco_scope", "g_eco_scope"),
            )
            st.slider(
                "Horizon (years)", 5, 10,
                value=int(es["eco_horizon"]),
                key="g_eco_horizon",
                on_change=_sync_eco,
                args=("eco_horizon", "g_eco_horizon"),
            )
        with c2:
            st.slider(
                "Disposal tariff escalation (%/yr)", 0.0, 10.0, step=0.5,
                value=float(es["eco_tariff_esc"]),
                key="g_eco_tariff_esc",
                on_change=_sync_eco,
                args=("eco_tariff_esc", "g_eco_tariff_esc"),
            )
            st.slider(
                "EPR / packaging co-funding (€/t)", 0.0, 200.0, step=10.0,
                value=float(es["eco_epr"]),
                key="g_eco_epr",
                on_change=_sync_eco,
                args=("eco_epr", "g_eco_epr"),
            )
        with c3:
            st.slider(
                "Co-creation & awareness intensity", 0.5, 1.5, step=0.1,
                value=float(es["eco_cocreation"]),
                key="g_eco_cocreation",
                on_change=_sync_eco,
                args=("eco_cocreation", "g_eco_cocreation"),
            )
            st.slider(
                "Fleet ceiling (max boats)", 1, 6,
                value=int(es["eco_max_boats"]),
                key="g_eco_max_boats",
                on_change=_sync_eco,
                args=("eco_max_boats", "g_eco_max_boats"),
            )

    tiles([
        tile("Archipelago fleet", f"{sm['initial_boats']} → {sm['final_boats']} boat{'s' if sm['final_boats'] != 1 else ''}",
             lead=True, sub=(f"2nd boat triggered in Year {sm['second_boat_year']}" if sm["second_boat_year"] else "Single boat fits demand")),
        tile(f"{horizon}-yr waste diverted", f"{nf(sm['total_diverted_t'], 1)} t",
             sub=f"Across {len(eco['islands_in_scope'])} island(s) in scope"),
        tile("Municipal participation", f"{sm['final_muni_adoption_pct']:.0f}%",
             sub=f"Artisan uptake: {sm['final_artisan_adoption_pct']:.0f}% (with product traceability)"),
        tile(f"{horizon}-yr cumulative cash", eur_s(sm["final_cumulative_cash_eur"]),
             sub=f"Average revenue/cost coverage {x2(sm['avg_coverage_ratio'])}"),
    ])


def _step_9(scn: dict, report: dict, R: dict, eco: dict, cbs: dict) -> None:
    capex = report["CapEx_Allocation"]
    pb = R["annual_payback_years"]
    be = R["breakeven_reboat_share_pct"]
    sroi = R["annual_sroi_ratio"]
    sroi_nt = R["annual_sroi_without_turnover"]
    sm = eco["summary"]
    horizon = st.session_state["_eco"]["eco_horizon"]
    airspace = R["annual_waste_diverted_tonnes"] / 0.35

    pb_txt = "does not pay back within one operating year" if pb is None else f"pays back in <b>{pb:.2f} years</b>"
    be_txt = (
        "requires tourism package visitors"
        if be is None
        else (
            "even without tourism income"
            if be <= 0
            else f"if ReBoat keeps at least <b>{be:.1f}%</b> of tourism packages (set to <b>{scn['reboat_share']:.1f}%</b>)"
        )
    )
    sroi_txt = "n/a (zero public grant under Private Investment)" if sroi is None else f"<b>{x2(sroi)}</b> social value per €1 of public grant (or <b>{x2(sroi_nt)}</b> excluding tour-operator turnover)"

    html_block(
        '<div class="gm-story">'
        '<div class="gm-card">'
        '<h4>1 · Can the mobile boat pay for itself?</h4>'
        f'<p>On <b>{esc(scn["target_island"])}</b>, annual income is <b>{eur(R["annual_gross_revenue_eur"])}</b> against '
        f'<b>{eur(R["annual_total_opex_eur"])}</b> in daily running costs (<b>{x2(R["annual_revenue_to_opex_ratio"])}</b> coverage).</p>'
        f'<p style="margin-top:8px">After setting aside 10-year equipment depreciation ({eur(R["annual_capex_amortization_eur"])}/yr), '
        f'the annual net result is <b>{eur_s(R["annual_net_after_capex_eur"])}</b>. The operator/loan share of '
        f'{eur(capex["net_equity_required_eur"])} {pb_txt}, and costs break even {be_txt}.</p>'
        '</div>'
        '<div class="gm-card">'
        '<h4>2 · What does the island &amp; society gain?</h4>'
        f'<p>Every year, the plant keeps <b>{nf(R["annual_waste_diverted_tonnes"], 1)} tonnes</b> of plastic and textile out of '
        f'landfills—saving <b>{nf(airspace)} m³</b> of landfill space and employing <b>{nf(scn["workers"])} trained island operators</b>.</p>'
        f'<p style="margin-top:8px">The municipality saves a net <b>{eur_s(R["annual_municipal_savings_eur"])}/yr</b> in avoided '
        f'shipping/disposal costs. Gross transport CO₂ avoided is <b>{nf(R["annual_carbon_avoided_tonnes"], 1)} t/yr</b> '
        f'(compared to {nf(R["annual_transit_diesel_co2_tonnes"], 1)} t/yr boat transit diesel), yielding {sroi_txt}.</p>'
        '</div>'
        '<div class="gm-card">'
        f'<h4>3 · How does it scale over {horizon} years?</h4>'
        f'<p>Across <b>{len(eco["islands_in_scope"])} island(s)</b>, rising municipal adoption (<b>{sm["final_muni_adoption_pct"]:.0f}%</b>) '
        f'and artisan uptake (<b>{sm["final_artisan_adoption_pct"]:.0f}%</b>) grow cumulative recycled waste to '
        f'<b>{nf(sm["total_diverted_t"], 1)} tonnes</b>.</p>'
        f'<p style="margin-top:8px">The fleet expands from <b>{sm["initial_boats"]} to {sm["final_boats"]} boat(s)</b>'
        + (f' (2nd vessel deployed in Year {sm["second_boat_year"]})' if sm["second_boat_year"] else '')
        + f', generating <b>{eur_s(sm["final_cumulative_cash_eur"])}</b> in cumulative cash over {horizon} years.</p>'
        '</div></div>'
    )

    with panel("Explore charts or download your custom report", chip("Everything stays synced", "good", True)):
        html_block('<p style="font-size:13px;color:var(--text-2);margin-bottom:8px">'
                   'Open any analytical view below (with plain-language reading guides switched on) or download '
                   'ready-to-share PDF, Word, Excel, and JSON files carrying these exact numbers.</p>')
        b1, b2, b3, b4, b5 = st.columns(5, gap="small")
        b1.button("View 01 · Overview", key="gm_go_ov", on_click=cbs["on_exit"],
                  kwargs={"target_url": "overview", "keep_hints": True}, width="stretch")
        b2.button("View 02 · Island Impact", key="gm_go_im", on_click=cbs["on_exit"],
                  kwargs={"target_url": "impact", "keep_hints": True}, width="stretch")
        b3.button("View 03 · Business Plan", key="gm_go_bp", on_click=cbs["on_exit"],
                  kwargs={"target_url": "business-plan", "keep_hints": True}, width="stretch")
        b4.button("View 05 · Ecosystem", key="gm_go_ec", on_click=cbs["on_exit"],
                  kwargs={"target_url": "ecosystem", "keep_hints": True}, width="stretch")
        b5.button("View 04 · Downloads", key="gm_go_dl", on_click=cbs["on_exit"],
                  kwargs={"target_url": "deliverables", "keep_hints": True}, type="primary", width="stretch")

        r1, _ = st.columns([1.4, 2.6])
        r1.button("↺ Reset all values to island defaults", key="gm_reset_def",
                  on_click=cbs["on_reset_defaults"], width="stretch")


# ── Main entrypoints called from app.py ──────────────────────────────────────
def render_guided_walkthrough(
    step: int,
    scn: dict,
    report: dict,
    R: dict,
    eco: dict,
    brain,
    meta: dict,
    callbacks: dict,
) -> None:
    """Render the active guided step (1..9), live preview strip, and step controls."""
    step = max(1, min(len(GUIDED_STEPS), int(step)))
    _render_progress_header(step, scn, callbacks["fin_name"])
    if step < 9:
        _render_live_strip(R, scn, eco)

    if step == 1:
        _step_1(scn, report, meta, callbacks)
    elif step == 2:
        _step_2(scn, R)
    elif step == 3:
        _step_3(scn, R, brain)
    elif step == 4:
        _step_4(scn, R, meta)
    elif step == 5:
        _step_5(scn, R)
    elif step == 6:
        _step_6(scn, R)
    elif step == 7:
        _step_7(scn, callbacks)
    elif step == 8:
        _step_8(scn, eco)
    else:
        _step_9(scn, report, R, eco, callbacks)

    # Bottom navigation row
    c_prev, c_mid, c_next = st.columns([1, 1.5, 1], gap="medium")
    with c_prev:
        if step > 1:
            st.button("← Previous step", key=f"gm_prev_{step}", on_click=_set_step, args=(step - 1,), width="stretch")
    with c_mid:
        if 4 <= step <= 7:
            st.button("Skip cost details → Jump to Results", key=f"gm_skip_{step}",
                      on_click=_set_step, args=(9,), width="stretch")
    with c_next:
        if step < 9:
            st.button("Next step →", key=f"gm_next_{step}", on_click=_set_step,
                      args=(step + 1,), type="primary", width="stretch")
        else:
            st.button("Open Full Dashboard →", key="gm_done_dash", on_click=callbacks["on_exit"],
                      kwargs={"target_url": "overview", "keep_hints": True}, type="primary", width="stretch")


def render_view_guide(view_key: str, R: dict, scn: dict, eco: dict | None = None) -> None:
    """Collapsible plain-language reading guide shown inside each dashboard view when hints are enabled."""
    be = R["breakeven_reboat_share_pct"]
    be_note = (
        "no minimum share (set tourism visitors above 0 to calculate)"
        if be is None
        else ("already covered without tourism income" if be <= 0 else f"{be:.1f}%")
    )
    guides = {
        "overview": (
            f"Operating solvency ({x2(R['annual_revenue_to_opex_ratio'])}) shows whether annual income pays daily running bills "
            f"(anything above 1.00× means positive cash margin before equipment depreciation). The monthly curves below reveal "
            f"winter low-season months versus summer peak months on {esc(scn['target_island'])}. Remember: all figures show "
            "one post-project commercial year, not grant-funded pilot income."
        ),
        "impact": (
            f"Shows what the island community and public funders receive: {nf(R['annual_waste_diverted_tonnes'], 1)} t/yr "
            f"of waste kept out of landfills, net municipal savings ({eur_s(R['annual_municipal_savings_eur'])}/yr = avoided disposal "
            "minus any optional gate fee), local operator jobs, screening CO₂ saved vs. boat diesel transit, and Social Return on "
            "Investment (both including and excluding external tour-operator turnover)."
        ),
        "business-plan": (
            f"Breaks down every euro earned and spent over 12 months. Payback measures how quickly the operator/investor equity "
            f"is recovered; 5-yr / 10-yr NPV tests multi-year returns at an 8% discount rate; and Break-even share shows the "
            f"minimum percentage of tourism packages ReBoat must retain ({be_note}) to pay running bills."
        ),
        "deliverables": (
            "Download everything on screen into four synchronized formats: a 2-page PDF summary for quick sharing, an editable Word "
            "brief, a full formula-linked 8-sheet Excel workbook (where yellow shaded Inputs update all tabs live), and the raw JSON "
            "dataset including multi-year projections."
        ),
        "ecosystem": (
            "Projects how the business scales over 5–10 years across a whole island archipelago as municipalities, tour operators, "
            "and local artisans adopt circular practices. Use the 6 controls below to test regional vs. single-island scope, rising "
            "mainland disposal tariffs, EPR co-funding, and fleet size caps (1 to 6 boats)."
            + (f" Current projection reaches {eco['summary']['final_boats']} boat(s) and {nf(eco['summary']['total_diverted_t'], 1)} t diverted." if eco else "")
        ),
    }
    text = guides.get(view_key)
    if not text:
        return
    with st.expander("How to read this page — Plain-language guide", expanded=True):
        st.markdown(text)
