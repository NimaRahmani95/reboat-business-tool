"""
ReBoat D2.3 v1.0 — Automated Verification, Regression, Export Audit & Figure Suite.

Run:
    py -3.11 tests/verify_d23.py
    py -3.11 tests/verify_d23.py --export
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import openpyxl  # noqa: E402
from docx import Document  # noqa: E402

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(TEST_DIR)
RELEASE_DIR = os.path.dirname(APP_DIR)
D23_DIR = os.path.join(RELEASE_DIR, "D2.3")
REF_DIR = os.path.join(D23_DIR, "reference_exports")
FIG_DIR = os.path.join(D23_DIR, "figures")

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from backend import (  # noqa: E402
    AVOIDED_DISPOSAL_COST,
    DEFAULT_OPTIONS,
    PRICING_NOTE,
    SEASON_MULTIPLIER,
    TOOL_VERSION,
    ReBoatDigitalBrain,
)
import business_summary_export  # noqa: E402
import charts as ch  # noqa: E402
from ecosystem_sim import DEFAULT_ECO_PARAMS, run_ecosystem_simulation  # noqa: E402
import financial_model_export  # noqa: E402
import pdf_summary_export  # noqa: E402
import plan_labels as PL  # noqa: E402
from stakeholder_data import ARCHIPELAGO_CLUSTERS, get_pilot_profile  # noqa: E402

ISLAND_PRESETS = {
    "Corfu": {"transit_base": 6.5, "berth_base": 300.0, "plastic_base": 5500.0},
    "Paxos": {"transit_base": 2.0, "berth_base": 250.0, "plastic_base": 5040.0},
    "Lipari": {"transit_base": 12.0, "berth_base": 280.0, "plastic_base": 5040.0},
    "Terceira": {"transit_base": 48.0, "berth_base": 400.0, "plastic_base": 8500.0},
}

FINANCING_NAMES = {
    "EU_Grants": "EU / Regional Public Grant",
    "Public_Private_Partnership": "50% grant — Municipal PPP",
    "Private_Investment": "0% grant — Private investment",
}

PRICE_POINT_NAMES = {
    "low": "Low end of each range",
    "mid": "Midpoint of each range",
    "high": "High end of each range",
}


def make_default_scn(island: str, **overrides) -> dict:
    p = ISLAND_PRESETS[island]
    pl = float(p["plastic_base"])
    scn = {
        "target_island": island,
        "capex_scenario": "EU_Grants",
        "op_days": 14,
        "transit_hrs": float(p["transit_base"]),
        "workers": 8,
        "plastic_kg": pl,
        "textile_kg": pl * 0.30,
        "pkg_day": 144,
        "pkg_short": 54,
        "pkg_slow": 24,
        "pkg_med": 6,
        "pkg_deep": 2,
        "price_point": DEFAULT_OPTIONS["price_point"],
        "reboat_share": DEFAULT_OPTIONS["reboat_share_pct"],
        "gate_fee": DEFAULT_OPTIONS["gate_fee_eur_per_t"],
        "prod_share": DEFAULT_OPTIONS["product_operator_share_pct"],
        "commission": DEFAULT_OPTIONS["sales_commission_pct"],
        "vessel": DEFAULT_OPTIONS["vessel_charter_eur_per_day"],
        "insurance": DEFAULT_OPTIONS["insurance_eur_per_year"],
        "collection": DEFAULT_OPTIONS["land_collection_eur_per_t"],
        "overheads": DEFAULT_OPTIONS["overheads_pct"],
        "prod_molded": 300,
        "prod_3d": 72,
        "prod_panel": 18,
        "prod_textile": 40,
        "prod_yarn": 80,
        "proxy_diesel": 1.75,
        "proxy_berth": float(p["berth_base"]),
        "proxy_export": float(AVOIDED_DISPOSAL_COST.get(island, 150.0)),
        "proxy_shore": 0.28,
        "proxy_rpet": 1.50,
        "proxy_yarn": 2.50,
        "proxy_labor": 800.0,
        "proxy_maintenance": 150.0,
        "proxy_capex": 430850.0,
    }
    scn.update(overrides)
    return scn


def run_scn(scn: dict):
    b = ReBoatDigitalBrain(scn["target_island"], "High")
    b.proxies["marine_diesel_eur_per_liter"] = scn["proxy_diesel"]
    b.proxies["daily_berth_and_shore_power_eur"] = scn["proxy_berth"]
    b.proxies["municipal_waste_export_cost_per_tonne"] = scn["proxy_export"]
    b.proxies["shore_power_electricity_eur_per_kwh"] = scn["proxy_shore"]
    b.proxies["rPET_flake_market_value_eur_per_kg"] = scn["proxy_rpet"]
    b.proxies["recycled_yarn_market_value_eur_per_kg"] = scn["proxy_yarn"]
    b.proxies["labor_cost_eur_per_day"] = scn["proxy_labor"]
    b.proxies["maintenance_eur_per_day"] = scn["proxy_maintenance"]
    b.capex_baseline_eur = scn["proxy_capex"]
    cfg = {
        "operational_days": scn["op_days"],
        "campaign_days": scn["op_days"],
        "transit_hours": scn["transit_hrs"],
        "plastic_processed_kg": scn["plastic_kg"],
        "textile_processed_kg": scn["textile_kg"],
        "local_workers_trained": scn["workers"],
        "land_event_mode": False,
        "capex_scenario": scn["capex_scenario"],
        "price_point": scn["price_point"],
        "reboat_share_pct": scn["reboat_share"],
        "gate_fee_eur_per_t": scn["gate_fee"],
        "product_operator_share_pct": scn["prod_share"],
        "sales_commission_pct": scn["commission"],
        "vessel_charter_eur_per_day": scn["vessel"],
        "insurance_eur_per_year": scn["insurance"],
        "land_collection_eur_per_t": scn["collection"],
        "overheads_pct": scn["overheads"],
        "package_sales": {
            "Day_Trip": scn["pkg_day"],
            "Short_Trip": scn["pkg_short"],
            "Slow_Trip": scn["pkg_slow"],
            "Medium_Slow": scn["pkg_med"],
            "Deep_Slow": scn["pkg_deep"],
        },
        "circular_products_sales": {
            "injection_molded_goods": scn["prod_molded"],
            "custom_3d_printed_artifacts": scn["prod_3d"],
            "thermo_pressed_furniture_panel": scn["prod_panel"],
            "artisanal_woven_textiles": scn["prod_textile"],
            "plied_yarn_spools": scn["prod_yarn"],
        },
    }
    return b, b.execute_island_scenario(cfg), b.calculate_annual_business_plan(cfg)


_MLINE = {
    "annual_tourism_revenue_eur": ("revenue_lines", "tourism"),
    "annual_finished_goods_revenue_eur": ("revenue_lines", "products"),
    "annual_bulk_flakes_revenue_eur": ("revenue_lines", "flakes"),
    "annual_bulk_yarn_revenue_eur": ("revenue_lines", "yarn"),
    "annual_gate_fee_revenue_eur": ("revenue_lines", "gate_fee"),
    "annual_labor_cost_eur": ("opex_lines", "crew"),
    "annual_berth_cost_eur": ("opex_lines", "berth"),
    "annual_maintenance_cost_eur": ("opex_lines", "maintenance"),
    "annual_power_cost_eur": ("opex_lines", "power"),
    "annual_fuel_cost_eur": ("opex_lines", "fuel"),
    "annual_vessel_cost_eur": ("opex_lines", "vessel"),
    "annual_insurance_cost_eur": ("opex_lines", "insurance"),
    "annual_land_collection_cost_eur": ("opex_lines", "collection"),
    "annual_commission_cost_eur": ("opex_lines", "commission"),
    "annual_overheads_cost_eur": ("opex_lines", "overheads"),
}


def build_export_payloads(scn: dict, eco_params: dict | None = None):
    b, report, R = run_scn(scn)
    eco = run_ecosystem_simulation(scn, eco_params or DEFAULT_ECO_PARAMS)
    profile = get_pilot_profile(scn["target_island"])
    cap = ReBoatDigitalBrain(scn["target_island"]).capex_financing_scenarios
    ca_cur = report["CapEx_Allocation"]
    grant_pct = ca_cur["coverage_percent"]
    grant_tot = ca_cur["grant_coverage_eur"]
    eq_tot = ca_cur["net_equity_required_eur"]
    grant_ann = grant_tot / 10.0
    wages = R["annual_wages_eur"]
    societal = R["annual_societal_value_eur"]
    kept_others = R["annual_product_sales_total_eur"] - R["annual_finished_goods_revenue_eur"]
    fp = hashlib.sha1(json.dumps(scn, sort_keys=True).encode()).hexdigest()[:12]
    date_str = datetime.now().strftime("%d %B %Y").lstrip("0")

    rev_vis = PL.visible(PL.REVENUE_LINES, R)
    opx_vis = PL.visible(PL.OPEX_LINES, R)
    months = []
    for m in R["monthly_timeseries"]:
        months.append({
            "label": PL.month_label(m),
            "season": m["season"],
            "season_mult": SEASON_MULTIPLIER.get(m["season"], 1.0),
            "days": m["days_active"],
            "rev_lines": [m[_MLINE[k][0]][_MLINE[k][1]] for k, _ in rev_vis],
            "opex_lines": [m[_MLINE[k][0]][_MLINE[k][1]] for k, _ in opx_vis],
            "tourism_rev": m["revenue_lines"]["tourism"],
            "revenue": m["revenue_eur"],
            "opex": m["opex_eur"],
            "amort": m["monthly_amortization_eur"],
            "waste_t": m["waste_diverted_tonnes"],
        })

    routes = []
    for key in ("EU_Grants", "Public_Private_Partnership", "Private_Investment"):
        _, rep_k, r_k = run_scn({**scn, "capex_scenario": key})
        ca = rep_k["CapEx_Allocation"]
        routes.append({
            "name": cap[key]["name"],
            "pct": ca["coverage_percent"],
            "grant": ca["grant_coverage_eur"],
            "equity": ca["net_equity_required_eur"],
            "payback": r_k["annual_payback_years"],
            "npv": r_k["annual_npv_10yr_eur"],
            "npv10": r_k["annual_npv_10yr_eur"],
            "sroi": r_k["annual_sroi_ratio"],
            "sroi_noturn": r_k["annual_sroi_without_turnover"],
            "selected": key == scn["capex_scenario"],
        })

    summary = dict(
        island=scn["target_island"],
        port=profile.get("berth_port", "—"),
        financing_name=FINANCING_NAMES[scn["capex_scenario"]],
        date=date_str,
        fingerprint=fp,
        capex=scn["proxy_capex"],
        equity=eq_tot,
        scenario_note=PL.SCENARIO_NOTE,
        kpi=dict(
            ratio=R["annual_revenue_to_opex_ratio"],
            net=R["annual_net_after_capex_eur"],
            revenue=R["annual_gross_revenue_eur"],
            opex=R["annual_total_opex_eur"],
            margin=R["annual_net_operating_margin_eur"],
            amortisation=R["annual_capex_amortization_eur"],
            payback=R["annual_payback_years"],
            npv5=R["annual_npv_5yr_eur"],
            npv10=R["annual_npv_10yr_eur"],
            waste_t=R["annual_waste_diverted_tonnes"],
            airspace_m3=R["annual_waste_diverted_tonnes"] / 0.35,
            co2_t=R["annual_carbon_avoided_tonnes"],
            co2_value=R["annual_carbon_value_eur"],
            transit_diesel_co2_t=R["annual_transit_diesel_co2_tonnes"],
            diesel_litres=R["annual_diesel_litres"],
            shore_power_kwh=R["annual_shore_power_kwh"],
            freight=R["annual_municipal_savings_eur"],
            avoided=R["annual_avoided_disposal_cost_eur"],
            gate_paid=R["annual_gate_fee_paid_eur"],
            sroi=R["annual_sroi_ratio"],
            sroi_noturn=R["annual_sroi_without_turnover"],
            breakeven=R["breakeven_reboat_share_pct"],
            turnover=R["annual_package_turnover_eur"],
            workers=scn["workers"],
            wages=wages,
            societal=societal,
            grant_annual=grant_ann,
        ),
        revenue_lines=[(lbl, R.get(k, 0)) for k, lbl in rev_vis],
        opex_lines=[(lbl, R.get(k, 0)) for k, lbl in opx_vis],
        routes=routes,
        months=[(PL.month_label(m), m["revenue_eur"], m["opex_eur"], m["rev_opex_ratio"], m["month_name"])
                for m in R["monthly_timeseries"]],
        assumptions=dict(
            days=scn["op_days"],
            active_days=R["annual_active_days"],
            workers=scn["workers"],
            price_point=PRICE_POINT_NAMES[scn["price_point"]].lower(),
            share=scn["reboat_share"],
            gate_fee=scn["gate_fee"],
            textile_rate=b.textile_line_rate_kg_hr(),
        ),
        ecosystem=eco,
    )

    turnover_by_pkg = {
        k: sum(m["package_units"].get(k, 0) * m["package_prices_eur"].get(k, 0) for m in R["monthly_timeseries"])
        for k in R["annual_package_units"]
    }
    pk_rows = []
    for (k, lbl), k2 in zip(PL.PACKAGES, ("pkg_day", "pkg_short", "pkg_slow", "pkg_med", "pkg_deep")):
        units = R["annual_package_units"].get(k, 0)
        turn = turnover_by_pkg.get(k, 0.0)
        pk_rows.append((lbl, scn[k2], units, (turn / units) if units else 0.0))

    F_ = R["material_flows"]
    fl_kg = (R["annual_bulk_flakes_revenue_eur"] / scn["proxy_rpet"]) if scn["proxy_rpet"] else F_["flakes_sold_bulk_t"] * 1000
    yn_kg = (R["annual_bulk_yarn_revenue_eur"] / scn["proxy_yarn"]) if scn["proxy_yarn"] else F_["yarn_sold_bulk_t"] * 1000

    basis = {
        "annual_tourism_revenue_eur": f"{scn['reboat_share']:.1f}% of package turnover",
        "annual_finished_goods_revenue_eur": "Upcycled products",
        "annual_bulk_flakes_revenue_eur": f"Bulk rPET flakes at €{scn['proxy_rpet']:.2f}/kg",
        "annual_bulk_yarn_revenue_eur": f"Bulk yarn at €{scn['proxy_yarn']:.2f}/kg",
        "annual_gate_fee_revenue_eur": f"Gate fee €{scn['gate_fee']:.2f}/t",
        "annual_labor_cost_eur": f"€{scn['proxy_labor']:.2f}/active day × season mult",
        "annual_berth_cost_eur": f"€{scn['proxy_berth']:.2f}/active day × season mult",
        "annual_maintenance_cost_eur": f"€{scn['proxy_maintenance']:.2f}/active day × season mult",
        "annual_power_cost_eur": f"52 kW × 8 h × active day × season mult × €{scn['proxy_shore']:.2f}/kWh",
        "annual_fuel_cost_eur": f"Transit fuel at €{scn['proxy_diesel']:.2f}/L",
        "annual_vessel_cost_eur": f"€{scn['vessel']:.2f}/active day",
        "annual_insurance_cost_eur": f"€{scn['insurance']:.2f}/year",
        "annual_land_collection_cost_eur": f"€{scn['collection']:.2f}/tonne",
        "annual_commission_cost_eur": f"{scn['commission']:.1f}% of tourism rev",
        "annual_overheads_cost_eur": f"{scn['overheads']:.1f}% of other opex",
    }

    model = dict(
        meta=dict(
            island=scn["target_island"],
            port=profile.get("berth_port", "—"),
            financing_name=FINANCING_NAMES[scn["capex_scenario"]],
            date=date_str,
            fingerprint=fp,
            ui_release="6.0.0",
            tool_version=TOOL_VERSION,
            scenario_note=PL.SCENARIO_NOTE,
        ),
        scenario=dict(
            days=scn["op_days"],
            active_days=R["annual_active_days"],
            transit_hrs=scn["transit_hrs"],
            plastic_kg=scn["plastic_kg"],
            textile_kg=scn["textile_kg"],
            workers=scn["workers"],
            capex=scn["proxy_capex"],
            price_point=PRICE_POINT_NAMES[scn["price_point"]],
            share=scn["reboat_share"],
            prod_share=scn["prod_share"],
            gate_fee=scn["gate_fee"],
        ),
        rates=[
            ("Operator crew", scn["proxy_labor"], "€ / active day", "Crew cost, scaled by the season multiplier"),
            ("Berth and port fees", scn["proxy_berth"], "€ / active day", "Berth and shore connection, scaled by the season multiplier"),
            ("Maintenance and consumables", scn["proxy_maintenance"], "€ / active day", "Wear parts, filters, lubricants"),
            ("Shore power", scn["proxy_shore"], "€ / kWh", "Electricity drawn at the berth (52 kW × 8 h per active day)"),
            ("Marine diesel", scn["proxy_diesel"], "€ / litre", "Transit fuel, 45 L per hour"),
            ("Recycled plastic flakes", scn["proxy_rpet"], "€ / kg", "Bulk sale price"),
            ("Recycled yarn", scn["proxy_yarn"], "€ / kg", "Bulk sale price"),
            ("Avoided disposal cost", scn["proxy_export"], "€ / tonne", "Ferry freight or incinerator cost avoided"),
            ("Gate fee", scn["gate_fee"], "€ / tonne", "Paid by municipality to operator"),
            ("ReBoat share of package price", scn["reboat_share"], "%", "Share kept by operator"),
            ("Operator share of product sales", scn["prod_share"], "%", "Share kept by operator"),
            ("Vessel charter", scn["vessel"], "€ / active day", "Optional unquoted line"),
            ("Insurance", scn["insurance"], "€ / year", "Optional unquoted line"),
            ("Collection on land", scn["collection"], "€ / tonne", "Optional unquoted line"),
            ("Sales commissions", scn["commission"], "% of tourism revenue", "Optional unquoted line"),
            ("Overheads", scn["overheads"], "% of other costs", "Optional unquoted line"),
        ],
        constants=[
            ("Textile line rate", b.textile_line_rate_kg_hr(), "kg / h", "textile spinning line limit"),
            ("Electrical load", 52.0, "kW", "Plant engineering baseline Scenario B"),
            ("CO₂ avoided", 0.12, "t CO₂ / t waste", "Gross transport screening factor pre-Task 5.7"),
            ("Carbon price", 80.0, "€ / t CO₂", "Value of CO₂ avoided"),
            ("Landfill density", 0.35, "t / m³", "Landfill space saved"),
            ("Amortisation period", 10.0, "years", "CapEx and grant spread"),
            ("Discount rate", 0.08, "per year", "5- and 10-year NPV"),
        ],
        packages=pk_rows,
        package_turnover=R["annual_package_turnover_eur"],
        products=[
            (lbl, scn[k2], R["annual_product_units"].get(k, 0), b.CIRCULAR_PRODUCTS_CATALOG[k]["unit_price_eur"])
            for (k, lbl), k2 in zip(PL.PRODUCTS, ("prod_molded", "prod_3d", "prod_panel", "prod_textile", "prod_yarn"))
        ],
        materials=[
            ("flakes", "Recycled plastic flakes", fl_kg, scn["proxy_rpet"], "Recovered plastic not used for products"),
            ("yarn", "Recycled yarn", yn_kg, scn["proxy_yarn"], "Recycled yarn not used for products"),
        ],
        flows=F_,
        units_verified=True,
        months_verified=True,
        months=months,
        rev_vis=rev_vis,
        opx_vis=opx_vis,
        annual={
            **{k: R.get(k, 0) for k, _ in PL.REVENUE_LINES + PL.OPEX_LINES},
            "annual_capex_amortization_eur": R["annual_capex_amortization_eur"],
            "annual_tourism_revenue_eur": R["annual_tourism_revenue_eur"],
            "annual_finished_goods_revenue_eur": R["annual_finished_goods_revenue_eur"],
            "annual_product_sales_total_eur": R["annual_product_sales_total_eur"],
            "grant": grant_tot,
            "grant_pct": grant_pct,
        },
        basis=basis,
        capex_items=[],
        capex_itemised=0,
        capex_gap=0,
        routes=routes,
        sustain=dict(
            waste_t=R["annual_waste_diverted_tonnes"],
            co2_t=R["annual_carbon_avoided_tonnes"],
            co2_value=R["annual_carbon_value_eur"],
            avoided=R["annual_avoided_disposal_cost_eur"],
            gate_paid=R["annual_gate_fee_paid_eur"],
            freight=R["annual_municipal_savings_eur"],
            export_rate=scn["proxy_export"],
            workers=scn["workers"],
            wages=wages,
            kept_by_others=kept_others,
            transit_diesel_co2_t=R["annual_transit_diesel_co2_tonnes"],
            diesel_litres=R["annual_diesel_litres"],
            shore_power_kwh=R["annual_shore_power_kwh"],
        ),
        ecosystem=eco,
    )
    json_payload = {
        **report,
        "annual_business_plan": R,
        "ecosystem_dynamics": eco,
        "export_timestamp": datetime.now().isoformat(),
        "tool_version": TOOL_VERSION,
        "ui_release": "6.0.0",
        "scenario_fingerprint": fp,
    }
    return R, eco, summary, model, json_payload


def verify_all():
    print("1. Verifying 4-island baseline numbers...")
    expected = {
        "Corfu": dict(rev=302029.90, opex=251856.63, ratio=1.20, net=7088.27, be=3.50,
                      sroi=15.17, sroi_nt=5.16, waste=76.31, muni=11446.56, pl_not=0.0, diesel_co2=10.69),
        "Paxos": dict(ratio=1.32, net=31946.92, pl_not=0.0),
        "Lipari": dict(ratio=1.21, net=9197.17, pl_not=0.0),
        "Terceira": dict(ratio=1.13, net=-3425.47, pl_not=3.97, diesel_co2=78.98),
    }
    for isl, exp in expected.items():
        b, _, R = run_scn(make_default_scn(isl))
        for k, val in [
            ("rev", R["annual_gross_revenue_eur"]),
            ("opex", R["annual_total_opex_eur"]),
            ("ratio", R["annual_revenue_to_opex_ratio"]),
            ("net", R["annual_net_after_capex_eur"]),
            ("be", R["breakeven_reboat_share_pct"]),
            ("sroi", R["annual_sroi_ratio"]),
            ("sroi_nt", R["annual_sroi_without_turnover"]),
            ("waste", R["annual_waste_diverted_tonnes"]),
            ("muni", R["annual_municipal_savings_eur"]),
            ("pl_not", R["material_flows"]["plastic_not_accepted_t"]),
            ("diesel_co2", R["annual_transit_diesel_co2_tonnes"]),
        ]:
            if k in exp:
                assert abs(val - exp[k]) <= 0.02, f"{isl} {k}: expected {exp[k]}, got {val}"
        # No -0.00 anywhere in material flows
        for fk, fv in R["material_flows"].items():
            assert not (fv == 0.0 and math.copysign(1, fv) < 0), f"{isl} {fk} has negative zero!"
        # Eq. (10) processed mass equals sum of accepted plastic + accepted textile
        fl = R["material_flows"]
        assert abs(R["annual_waste_diverted_tonnes"] - (fl["plastic_accepted_t"] + fl["textile_accepted_t"])) < 0.02
        # Textile accepted respects 0.5 kg/h textile spinning line limit over 191 active days (rounded to 2 d.p.)
        assert fl["textile_accepted_t"] == round(R["annual_active_days"] * 8 * 0.5 / 1000.0, 2)
    print("   [PASS] 4-island baselines, +0.0 guard, Eq. (10), and 0.5 kg/h spinner cap.")

    print("2. Verifying campaign lengths, unwashed flake sensitivity, Table 27 stress test, and lower-volume case...")
    days_out = []
    for L_days, exp_days in ((7, 96), (14, 191), (21, 271), (28, 317)):
        _, _, rL = run_scn(make_default_scn("Corfu", op_days=L_days))
        assert rL["annual_active_days"] == exp_days, f"L={L_days}: {rL['annual_active_days']}"
        days_out.append(rL["annual_waste_diverted_tonnes"])
    assert days_out == sorted(days_out)

    for price, exp_ratio, exp_net in ((1.50, 1.20, 7088.27), (1.34, 1.16, -2996.85),
                                      (1.00, 1.07, -24427.78), (0.60, 0.97, -49640.63)):
        _, _, rp = run_scn(make_default_scn("Corfu", proxy_rpet=price))
        assert rp["annual_revenue_to_opex_ratio"] == exp_ratio
        assert abs(rp["annual_net_after_capex_eur"] - exp_net) <= 0.05

    _, _, r_stress = run_scn(make_default_scn("Corfu", vessel=200.0, insurance=6000.0,
                                             collection=30.0, commission=10.0, overheads=5.0))
    assert abs(r_stress["annual_total_opex_eur"] - 321364.08) <= 0.05
    assert r_stress["annual_revenue_to_opex_ratio"] == 0.94
    assert abs(r_stress["annual_net_after_capex_eur"] - (-62419.18)) <= 0.05
    assert r_stress["breakeven_reboat_share_pct"] == 12.8

    _, _, r_low = run_scn(make_default_scn(
        "Corfu", plastic_kg=4200.0, textile_kg=1260.0,
        pkg_day=120, pkg_short=45, pkg_slow=20, pkg_med=5, pkg_deep=2,
        prod_molded=250, prod_3d=60, prod_panel=15, prod_textile=40, prod_yarn=80,
    ))
    assert r_low["annual_revenue_to_opex_ratio"] == 0.99
    assert abs(r_low["annual_net_after_capex_eur"] - (-45593.38)) <= 0.05

    _, _, r_gf = run_scn(make_default_scn("Corfu", gate_fee=200.0))
    assert r_gf["annual_municipal_savings_eur"] < 0
    fig_wf = ch.waterfall([
        ("Turnover", r_gf["annual_gross_revenue_eur"], ch.S1, "step"),
        ("Municipal saving", r_gf["annual_municipal_savings_eur"], ch.S2, "step"),
        ("Local wages", r_gf["annual_wages_eur"], ch.S5, "step"),
        ("Carbon value", r_gf["annual_carbon_value_eur"], ch.NEUTRAL, "step"),
        ("Societal value", r_gf["annual_societal_value_eur"], ch.S3, "total"),
    ])
    assert len(fig_wf.data) == 1
    print("   [PASS] Sensitivities, Table 27 stress test, lower-volume vector, and negative waterfall bar.")

    print("3. Verifying multi-year ecosystem simulation across all 3 archipelagos...")
    eco_expect = {
        "Corfu": ("Ionian", 3, 3, 50.0, [4, 6]),
        "Lipari": ("Aeolian", 2, 2, 50.0, [4]),
        "Terceira": ("Azores", 2, 2, 50.0, [4]),
    }
    for isl, (arch, fboats, opt, dpp_up, exp_yrs) in eco_expect.items():
        eco = run_ecosystem_simulation(make_default_scn(isl), DEFAULT_ECO_PARAMS)
        assert eco["archipelago_key"] == arch
        assert eco["summary"]["final_boats"] == fboats
        assert eco["summary"]["optimal_boats_needed"] == opt
        assert eco["summary"]["dpp_uplift_artisan_pp"] == dpp_up
        assert eco["summary"]["expansion_years"] == exp_yrs
        fr = eco["tradeoff_frontier"]
        assert fr[0]["final_coverage_ratio"] < max(r["final_coverage_ratio"] for r in fr)
        assert fr[0]["avg_muni_adoption_pct"] > fr[-1]["avg_muni_adoption_pct"]
        assert fr[-1]["final_cumulative_cash_eur"] < fr[0]["final_cumulative_cash_eur"]

    eco_single = run_ecosystem_simulation(make_default_scn("Corfu"), {**DEFAULT_ECO_PARAMS, "scope": "single_island"})
    assert eco_single["islands_in_scope"] == ["Corfu"]
    print("   [PASS] Multi-year ecosystem dynamics across Ionian, Aeolian, Azores & single-island scopes.")

    print("4. Auditing Excel formulas, PDF, Word, and JSON exports across scenarios...")
    cases = [("Corfu", make_default_scn("Corfu")),
             ("Corfu_StressTest_T27", make_default_scn("Corfu", vessel=200.0, insurance=6000.0,
                                                       collection=30.0, commission=10.0, overheads=5.0)),
             ("Paxos", make_default_scn("Paxos")),
             ("Lipari", make_default_scn("Lipari")),
             ("Terceira", make_default_scn("Terceira"))]

    _DISALLOWED_RE = re.compile(
        r"\bsystem dynamics\b|\bagent-based\b|sd\s*\+\s*abm|\bga table 1\.[12]\b|\bfigure 1\.5\b|\bdigiprime\b|\bfibereuse\b",
        re.IGNORECASE,
    )

    for name, scn in cases:
        R, _, summary, model, jdata = build_export_payloads(scn)
        pdf_bytes = pdf_summary_export.generate_business_summary_pdf(summary)
        docx_bytes = business_summary_export.generate_business_summary_docx(summary)
        xlsx_bytes = financial_model_export.generate_financial_model_xlsx(model)
        json_str = json.dumps(jdata, indent=2, default=str)

        assert len(pdf_bytes) > 5000 and pdf_bytes[:4] == b"%PDF"
        assert len(json_str) > 3000

        doc_chk = Document(io.BytesIO(docx_bytes))
        doc_txt = "\n".join(p.text for p in doc_chk.paragraphs)
        assert "European Research Executive Agency (REA)" in doc_txt
        assert "dynamic ecosystem" in doc_txt.lower()
        assert not _DISALLOWED_RE.search(doc_txt), f"{name} DOCX contains disallowed term: {_DISALLOWED_RE.findall(doc_txt)}"

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        req_sheets = ["Summary", "Inputs", "Revenue build-up", "P&L", "Monthly",
                      "Investment & financing", "Sustainability", "Ecosystem dynamics"]
        assert wb.sheetnames == req_sheets, f"{name} sheetnames={wb.sheetnames}"

        inputs_refs = 0
        formula_count = 0
        summary_text = []
        for sname in wb.sheetnames:
            ws = wb[sname]
            for row in ws.iter_rows(values_only=True):
                for val in row:
                    if isinstance(val, str):
                        for err in ("#REF!", "#NAME?", "#DIV/0!", "#VALUE!", "#N/A"):
                            assert err not in val, f"{name} {sname} contains {err}: {val}"
                        assert not _DISALLOWED_RE.search(val), f"{name} {sname} contains disallowed term {val}: {_DISALLOWED_RE.findall(val)}"
                        if val.startswith("="):
                            formula_count += 1
                            if "'Inputs'!" in val or "Inputs!" in val:
                                inputs_refs += 1
                        if sname == "Summary":
                            summary_text.append(val)

        assert inputs_refs >= 20, f"{name} expected >=20 'Inputs'! refs, got {inputs_refs}"
        assert formula_count >= 120, f"{name} expected >=120 formulas, got {formula_count}"
        assert any("European Research Executive Agency (REA)" in t for t in summary_text)

        # Verify Monthly sheet columns & check exact arithmetic parity with backend
        ws_m = wb["Monthly"]
        headers_m = [ws_m.cell(row=6, column=c).value for c in range(1, ws_m.max_column + 1)]
        assert headers_m[2] == "SEASON MULT", f"headers_m={headers_m[:5]}"
        # Recompute monthly OpEx arithmetic independently from season_mult & days & rates
        crew_sum = sum(round(mo["days"] * mo["season_mult"] * scn["proxy_labor"], 2) for mo in model["months"])
        assert abs(crew_sum - R["annual_labor_cost_eur"]) <= 0.10, f"{name} crew parity {crew_sum} vs {R['annual_labor_cost_eur']}"

    print("   [PASS] PDF, Word, 8-sheet formula-linked Excel, and JSON audit passed for all scenarios.")


def export_references_and_figures():
    os.makedirs(REF_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)
    print(f"5. Exporting frozen 4-island reference files to {REF_DIR} ...")
    for isl in ("Corfu", "Paxos", "Lipari", "Terceira"):
        scn = make_default_scn(isl)
        _, _, summary, model, jdata = build_export_payloads(scn)
        slug = f"ReBoat_D23_v1.0_{isl}"
        with open(os.path.join(REF_DIR, f"{slug}_Scenario.json"), "w", encoding="utf-8") as f:
            json.dump(jdata, f, indent=2, default=str)
        with open(os.path.join(REF_DIR, f"{slug}_Model.xlsx"), "wb") as f:
            f.write(financial_model_export.generate_financial_model_xlsx(model))
        with open(os.path.join(REF_DIR, f"{slug}_Summary.pdf"), "wb") as f:
            f.write(pdf_summary_export.generate_business_summary_pdf(summary))
        with open(os.path.join(REF_DIR, f"{slug}_Summary.docx"), "wb") as f:
            f.write(business_summary_export.generate_business_summary_docx(summary))
    print("   [OK] Saved 16 reference files (JSON, XLSX, PDF, DOCX × 4 islands).")

    print(f"6. Generating high-DPI Chapter 5 figures to {FIG_DIR} ...")
    plt.rcParams.update({"font.sans-serif": "DejaVu Sans", "axes.edgecolor": "#C9D3DC", "axes.linewidth": 0.8})

    # Fig 5.1 (Section 5.7): Unwashed rPET flake sensitivity
    prices = [1.50, 1.34, 1.00, 0.60]
    labels = ["€1.50/kg\n(Baseline)", "€1.34/kg\n(OPIS bench.)", "€1.00/kg\n(Unwashed mid)", "€0.60/kg\n(Low grade)"]
    nets, ratios = [], []
    for p in prices:
        _, _, rp = run_scn(make_default_scn("Corfu", proxy_rpet=p))
        nets.append(rp["annual_net_after_capex_eur"])
        ratios.append(rp["annual_revenue_to_opex_ratio"])

    fig, ax1 = plt.subplots(figsize=(7.6, 3.6), dpi=300)
    cols = ["#1A7F5A" if n >= 0 else "#C97A18" for n in nets]
    bars = ax1.bar(labels, nets, color=cols, width=0.46, zorder=2, label="Net result after amortisation (€/yr)")
    ax1.axhline(0, color="#55616D", linewidth=1.0, zorder=1)
    ax1.set_ylabel("Net result after amortisation (€/yr)", color="#1C1C1A", fontsize=9.5, fontweight="bold")
    ax1.yaxis.set_major_formatter(lambda x, pos: (f"−€{abs(x):,.0f}" if x < 0 else f"€{x:,.0f}"))
    ax1.set_ylim(-64000, 26000)
    ax1.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
    for idx_b, (b_bar, val) in enumerate(zip(bars, nets)):
        fmt_v = f"−€{abs(val):,.0f}" if val < 0 else f"€{val:,.0f}"
        y_pos = 1900 if (-5000 < val < 0) else (val + 1900 if val >= 0 else val - 5800)
        ax1.text(b_bar.get_x() + b_bar.get_width() / 2, y_pos, fmt_v, ha="center", va="bottom",
                 fontsize=8.5, fontweight="bold", color="#1C1C1A", zorder=5,
                 bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.82))
    ax2 = ax1.twinx()
    ax2.plot(labels, ratios, color="#1D6FA5", marker="o", linewidth=2.2, markersize=6, label="Coverage ratio (R/C)", zorder=4)
    ax2.axhline(1.0, color="#B3261E", linestyle=":", linewidth=1.2, label="1.00× OpEx breakeven")
    ax2.set_ylabel("Coverage ratio (R/C)", color="#1D6FA5", fontsize=9.5, fontweight="bold")
    ax2.set_ylim(0.84, 1.34)
    ax2.yaxis.set_major_formatter(lambda x, pos: f"{x:.2f}×")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, fontsize=7.6, frameon=False, loc="lower left")
    plt.title("Corfu sensitivity to recycled rPET flake sales price (washed vs. unwashed grades)",
              fontsize=10.5, fontweight="bold", pad=10, color="#1C1C1A")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_ch5_unwashed_flake.png"), dpi=300)
    plt.close(fig)

    # Fig 5.2 (Section 5.11): Multi-year Ionian adoption & fleet scaling
    eco_ion = run_ecosystem_simulation(make_default_scn("Corfu"), DEFAULT_ECO_PARAMS)
    ys = [r["year"] for r in eco_ion["yearly_series"]]
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(9.4, 3.8), dpi=300)
    ax_a.plot(ys, [r["muni_adoption_pct"] for r in eco_ion["yearly_series"]], "-o", color="#1D6FA5", lw=2, label="Municipalities")
    ax_a.plot(ys, [r["dmc_adoption_pct"] for r in eco_ion["yearly_series"]], "-s", color="#B35C1E", lw=2, label="Tour ops / DMCs")
    ax_a.plot(ys, [r["artisan_adoption_pct"] for r in eco_ion["yearly_series"]], "-^", color="#1A7F5A", lw=2, label="Artisans (DPP ON)")
    ax_a.plot(ys, [r["awareness_pct"] for r in eco_ion["yearly_series"]], "--d", color="#6C5B7B", lw=1.8, label="Awareness stock")
    ax_a.set_title("a) Ionian Cluster Stakeholder Adoption", fontsize=9.8, fontweight="bold")
    ax_a.set_xlabel("Year", fontsize=9); ax_a.set_ylabel("Adoption / awareness (%)", fontsize=9)
    ax_a.set_xticks(ys); ax_a.set_ylim(0, 108); ax_a.grid(True, ls="--", alpha=0.35)
    ax_a.legend(fontsize=7.6, frameon=False, loc="lower right")

    div = [r["diverted_waste_t"] for r in eco_ion["yearly_series"]]
    unm = [r["unmet_waste_t"] for r in eco_ion["yearly_series"]]
    cap_t = [r["fleet_capacity_t"] for r in eco_ion["yearly_series"]]
    bts = [r["n_boats"] for r in eco_ion["yearly_series"]]
    ax_b.bar(ys, div, color="#1D6FA5", label="Diverted waste (t/yr)", zorder=3)
    ax_b.bar(ys, unm, bottom=div, color="#C94A38", label="Unmet peak waste (t/yr)", zorder=3)
    ax_b.step(ys, cap_t, where="mid", color="#1A7F5A", lw=2.2, label="Fleet capacity (t/yr)", zorder=4)
    for x_, c_, n_ in zip(ys, cap_t, bts):
        ax_b.text(x_, c_ + 18, f"{n_}B", ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#1A7F5A")
    ax_b.set_title("b) Fleet Scaling (1 → 3 Boats) & Waste Diversion", fontsize=9.8, fontweight="bold")
    ax_b.set_xlabel("Year", fontsize=9); ax_b.set_ylabel("Waste / capacity (t/yr)", fontsize=9)
    ax_b.set_xticks(ys); ax_b.set_ylim(0, max(cap_t) * 1.18); ax_b.grid(axis="y", ls="--", alpha=0.35)
    ax_b.legend(fontsize=7.6, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_ch5_eco_adoption_fleet.png"), dpi=300)
    plt.close(fig)

    # Fig 5.3 (Section 5.12): Gate-fee systemic trade-off across 3 archipelagos
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.7), dpi=300)
    palette = [("Corfu", "Ionian (Corfu + 4)", "#1D6FA5"),
               ("Lipari", "Aeolian (Lipari + 3)", "#1A7F5A"),
               ("Terceira", "Azores (Terceira + 3)", "#B35C1E")]
    for isl, lbl, col in palette:
        fr = run_ecosystem_simulation(make_default_scn(isl), DEFAULT_ECO_PARAMS)["tradeoff_frontier"]
        gfs = [r["gate_fee_eur_per_t"] for r in fr]
        ax1.plot(gfs, [r["final_coverage_ratio"] for r in fr], "-o", color=col, lw=2, label=lbl)
        ax2.plot(gfs, [r["avg_muni_adoption_pct"] for r in fr], "-s", color=col, lw=2, label=lbl)
    ax1.axhline(1.0, color="#B3261E", ls=":", lw=1.2)
    ax1.set_title("a) Year-10 Operator Solvency (R/C)", fontsize=9.8, fontweight="bold")
    ax1.set_xlabel("Municipal gate fee (€/t)"); ax1.set_ylabel("Coverage ratio (R/C)")
    ax1.grid(True, ls="--", alpha=0.35); ax1.legend(fontsize=7.8, frameon=False, loc="lower left")
    ax2.set_title("b) 10-Year Avg Municipal Adoption (%)", fontsize=9.8, fontweight="bold")
    ax2.set_xlabel("Municipal gate fee (€/t)"); ax2.set_ylabel("Avg municipal adoption (%)")
    ax2.set_ylim(0, 108); ax2.grid(True, ls="--", alpha=0.35); ax2.legend(fontsize=7.8, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, "fig_ch5_eco_tradeoff.png"), dpi=300)
    plt.close(fig)
    print("   [OK] Generated 3 Chapter 5 figures (300 DPI PNG).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="Also emit frozen D2.3 reference exports and Chapter 5 figures")
    args = parser.parse_args()
    verify_all()
    if args.export:
        export_references_and_figures()
    print("ALL VERIFICATION CHECKS PASSED.")
