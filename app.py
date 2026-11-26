"""
ReBoat Digital Tool for Business Plan and Sustainability Evaluation — Task 2.6 / Deliverable D2.3 (UI release 6.0.0)
Horizon Europe Grant Agreement 101182350 · Lead: Politecnico di Milano (POLIMI) · License: All Rights Reserved (see LICENSE)

Presentation layer for ReBoatDigitalBrain (backend.py, engine 4.0.0) and the multi-year
Ecosystem & Archipelago Simulation (ecosystem_sim.py).
All results describe ONE OPERATING YEAR AFTER THE PROJECT (exploitation scenario), not income of the
EU-funded pilots, projected over 5–10 years in View 05 (Ecosystem dynamics).

Release 6.0.0 (D2.3 v1.0 EU Review Readiness):
  • View 05 · Ecosystem dynamics: pure-Python multi-year archipelago & stakeholder simulation
    (T2.4 pipeline mapping, WP7 Clusters C1–C4, fleet scaling, and gate-fee trade-off frontier).
  • Horizon Europe GA Art. 17.2 / 17.3 EU emblem + European Research Executive Agency (REA) disclaimer on all views & exports.
  • Explicit screening CO2 transparency (Gross waste-transport CO2 avoided vs. indicative transit diesel CO2 & 52 kW load).
  • SROI (excl. turnover) surfaced alongside SROI in View 01/02, financing-route comparison, Excel, PDF & Word.
  • Illustrative full-cost stress test toggle (Report Table 27) + live Input-linked Excel formulas & Sheet 8.
"""

import base64
import hashlib
import re
import json
import os
import sys
from datetime import datetime

import streamlit as st

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(APP_DIR)

from backend import (ReBoatDigitalBrain, SEASON_MULTIPLIER, TOOL_VERSION, PRICING_NOTE, PACKAGE_KEYS,  # noqa: E402
                     PACKAGE_DURATIONS, AVOIDED_DISPOSAL_COST, GA_RAAS_GATE_FEE_EUR_PER_T, DEFAULT_OPTIONS)
from stakeholder_data import (get_pilot_profile, PILOT_PROFILES, ARCHIPELAGO_CLUSTERS,  # noqa: E402
                              get_archipelago_for_island)
from ecosystem_sim import DEFAULT_ECO_PARAMS, run_ecosystem_simulation  # noqa: E402
import business_summary_export  # noqa: E402
import financial_model_export  # noqa: E402
import pdf_summary_export  # noqa: E402
import plan_labels as PL  # noqa: E402
import ui  # noqa: E402
import charts as ch  # noqa: E402
import guided_mode as gm  # noqa: E402
from ui import eur, eur_s, nf, x2, pct, esc, chip, tile, tiles, note, show_note, html_block, panel, delta  # noqa: E402
from charts import S1, S2, S3, S4, S5, NEUTRAL, CRIT, SIGNAL  # noqa: E402

UI_RELEASE = "6.0.0"

st.set_page_config(
    page_title="ReBoat · Digital Tool for Business Plan and Sustainability Evaluation",
    page_icon="🛳️",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject()
ui.reset_panels()

PLATE = os.path.join(APP_DIR, "assets", "vessel_plate.jpg")
ASSETS = os.path.join(APP_DIR, "assets")

# ─────────────────────────────────────────────────────────────────────────────
# Pilot logistics. Transit hours and berth fees are planning defaults (to be confirmed with T2.4 and the
# pilot partners); the avoided disposal cost comes from the engine (Terceira: local incinerator, €50/t).
# ─────────────────────────────────────────────────────────────────────────────
ISLAND_DATA = {
# plastic_base: plastic processed per 14 active days at the start of each island scenario (high-season value;
# textile = 30% of it). Set per island so the starting operating year covers its running costs and amortisation;
# all values stay within the shredder capacity (100 kg/h × 8 h × 14 days = 11,200 kg).
    "Corfu": {"lat": 39.62, "lon": 19.92, "transit_base": 6.5, "berth_base": 300.0, "plastic_base": 5500.0},
    "Paxos": {"lat": 39.20, "lon": 20.18, "transit_base": 2.0, "berth_base": 250.0, "plastic_base": 5040.0},
    "Lipari": {"lat": 38.47, "lon": 14.95, "transit_base": 12.0, "berth_base": 280.0, "plastic_base": 5040.0},
    "Terceira": {"lat": 38.65, "lon": -27.22, "transit_base": 48.0, "berth_base": 400.0, "plastic_base": 8500.0},
}
for _isl, _d in ISLAND_DATA.items():
    _d["export_base"] = AVOIDED_DISPOSAL_COST.get(_isl, 150.0)

FINANCING_LABELS = {
    "EU_Grants": "70% grant — Horizon Europe",
    "Public_Private_Partnership": "50% grant — Municipal PPP",
    "Private_Investment": "0% grant — Private investment",
}

# Tourism packages: session-key suffix → engine key, with the D4.1 description shown in each package's "?" help.
PKG_KEYS = [("day", "Day_Trip"), ("short", "Short_Trip"), ("slow", "Slow_Trip"), ("med", "Medium_Slow"), ("deep", "Deep_Slow")]
PKG_INFO = {
    "day": ("Day trip", "1.5–3 hours at the plant (D4.1, Table 09): guided tour, short demonstration and a light activity "
            "such as sorting or a mini upcycling demo."),
    "short": ("Short trip", "3–5 hours at the plant, possibly in two sessions: plant visit, workshop and a coastal or "
              "community activity linked to ReBoat outputs."),
    "slow": ("Slow trip", "Half a day to a full day (4–7 hours): guided tour, hands-on workshop, circular-economy lab "
             "activity and reflection session."),
    "med": ("Medium-slow stay", "1–2 full days in split modules: technical workshops, co-creation labs, data collection "
            "and community integration."),
    "deep": ("Deep-slow stay", "2–5 days over the stay: experimentation, prototyping, monitoring and collaborative design "
             "with stakeholders (living lab)."),
}
PRICE_POINTS = {"low": "Low end of each range", "mid": "Midpoint of each range", "high": "High end of each range"}

# ─────────────────────────────────────────────────────────────────────────────
# Session state — identical keys and starting values to v3.3.0.
# ─────────────────────────────────────────────────────────────────────────────
SCENARIO_KEYS = [
    "target_island", "capex_scenario", "op_days", "transit_hrs", "workers",
    "plastic_kg", "textile_kg",
    "pkg_day", "pkg_short", "pkg_slow", "pkg_med", "pkg_deep",
    "price_point", "reboat_share", "gate_fee", "prod_share", "commission", "vessel", "insurance", "collection", "overheads",
    "prod_molded", "prod_3d", "prod_panel", "prod_textile", "prod_yarn",
    "proxy_diesel", "proxy_berth", "proxy_export", "proxy_shore",
    "proxy_rpet", "proxy_yarn", "proxy_labor", "proxy_maintenance", "proxy_capex",
]

if "initialized" not in st.session_state:
    st.session_state.update(
        {
            "target_island": "Corfu",
            "season": "High",
            "op_days": 14,
            "transit_hrs": 6.5,
            "plastic_kg": 4200.0,
            "textile_kg": 1260.0,
            "workers": 8,
            "pkg_day": 120,
            "pkg_short": 45,
            "pkg_slow": 20,
            "pkg_med": 5,
            "pkg_deep": 2,
            # tourism: pricing-note prices and the ReBoat share; neutral defaults for the new business-model inputs
            "price_point": DEFAULT_OPTIONS["price_point"],
            "reboat_share": DEFAULT_OPTIONS["reboat_share_pct"],
            "gate_fee": DEFAULT_OPTIONS["gate_fee_eur_per_t"],
            "prod_share": DEFAULT_OPTIONS["product_operator_share_pct"],
            "commission": DEFAULT_OPTIONS["sales_commission_pct"],
            "vessel": DEFAULT_OPTIONS["vessel_charter_eur_per_day"],
            "insurance": DEFAULT_OPTIONS["insurance_eur_per_year"],
            "collection": DEFAULT_OPTIONS["land_collection_eur_per_t"],
            "overheads": DEFAULT_OPTIONS["overheads_pct"],
            "prod_molded": 250,
            "prod_3d": 60,
            "prod_panel": 15,
            "prod_textile": 40,
            "prod_yarn": 80,
            "capex_scenario": "EU_Grants",
            "proxy_diesel": 1.75,
            "proxy_berth": 300.0,
            "proxy_export": 150.0,
            "proxy_shore": 0.28,
            "proxy_rpet": 1.50,
            "proxy_yarn": 2.50,
            "proxy_labor": 800.0,
            "proxy_maintenance": 150.0,
            "proxy_capex": 430850.0,  # aggregate plant planning budget baseline
            # v4 additions
            "show_audit": True,
            "stress_test": False,
            "launch_mode": "standard",
            "guided_active": False,
            "guided_hints": False,
            "guided_step": 1,
            "started": False,          # 5.5.1: start screen until an island is chosen
            "initialized": True,
        }
    )
    st.session_state["_baseline"] = {k: st.session_state[k] for k in SCENARIO_KEYS}

# Sessions started on an earlier release: add the new keys at their defaults and drop the retired ones.
_NEW_DEFAULTS = {"price_point": DEFAULT_OPTIONS["price_point"], "reboat_share": DEFAULT_OPTIONS["reboat_share_pct"],
                 "gate_fee": 0.0, "prod_share": 100.0, "commission": 0.0, "vessel": 0.0, "insurance": 0.0,
                 "collection": 0.0, "overheads": 0.0}
_ECO_STORE_DEFAULTS = {
    "eco_horizon": DEFAULT_ECO_PARAMS["horizon_years"],
    "eco_scope": DEFAULT_ECO_PARAMS["scope"],
    "eco_tariff_esc": DEFAULT_ECO_PARAMS["tariff_escalation_pct"],
    "eco_epr": DEFAULT_ECO_PARAMS["epr_subsidy_eur_per_t"],
    "eco_cocreation": DEFAULT_ECO_PARAMS["cocreation_intensity"],
    "eco_max_boats": DEFAULT_ECO_PARAMS["max_boats"],
}
st.session_state.setdefault("started", True)   # sessions opened on an earlier release skip the start screen
st.session_state.setdefault("stress_test", False)
st.session_state.setdefault("launch_mode", "standard")
st.session_state.setdefault("guided_active", False)
st.session_state.setdefault("guided_hints", False)
st.session_state.setdefault("guided_step", 1)
for _k, _v in _NEW_DEFAULTS.items():
    st.session_state.setdefault(_k, _v)
    st.session_state["_baseline"].setdefault(_k, _v)
st.session_state.setdefault("_eco", dict(_ECO_STORE_DEFAULTS))
for _k, _v in _ECO_STORE_DEFAULTS.items():
    st.session_state["_eco"].setdefault(_k, _v)
if st.session_state.get("target_island") not in ISLAND_DATA:
    st.session_state["target_island"] = "Terceira" if st.session_state.get("target_island") == "Azores" else "Corfu"
for _k in [k for k in st.session_state["_baseline"] if k not in SCENARIO_KEYS]:
    st.session_state["_baseline"].pop(_k)
if st.session_state["_baseline"].get("target_island") not in ISLAND_DATA:
    st.session_state["_baseline"]["target_island"] = st.session_state["target_island"]


def apply_island_season_presets():
    """Fires when the island selector changes, and when an island is chosen on the start screen."""
    island = st.session_state.target_island
    season = st.session_state.get("season", "High")
    base_data = ISLAND_DATA[island]
    st.session_state.transit_hrs = float(base_data["transit_base"])
    st.session_state.proxy_berth = float(base_data["berth_base"])
    st.session_state.proxy_export = float(base_data["export_base"])

    mult = SEASON_MULTIPLIER.get(season, 1.0)
    st.session_state.plastic_kg = base_data["plastic_base"] * mult / SEASON_MULTIPLIER["High"]
    st.session_state.textile_kg = st.session_state.plastic_kg * 0.30
    st.session_state.pkg_day = int(120 * mult)
    st.session_state.pkg_short = int(45 * mult)
    st.session_state.pkg_slow = int(20 * mult)
    st.session_state.pkg_med = int(5 * mult)
    st.session_state.pkg_deep = int(2 * mult)
    st.session_state.prod_molded = int(250 * mult)
    st.session_state.prod_3d = int(60 * mult)
    st.session_state.prod_panel = int(15 * mult)
    st.session_state["_baseline"] = {k: st.session_state[k] for k in SCENARIO_KEYS}


def _toggle_stress_test():
    """Toggle illustrative unquoted operating costs (Deliverable D2.3 Table 27)."""
    if st.session_state.get("stress_test"):
        st.session_state.vessel = 200.0
        st.session_state.insurance = 6000.0
        st.session_state.collection = 30.0
        st.session_state.commission = 10.0
        st.session_state.overheads = 5.0
    else:
        st.session_state.vessel = 0.0
        st.session_state.insurance = 0.0
        st.session_state.collection = 0.0
        st.session_state.commission = 0.0
        st.session_state.overheads = 0.0


def set_baseline():
    st.session_state["_baseline"] = {k: st.session_state[k] for k in SCENARIO_KEYS}


def reset_to_baseline():
    for k, v in st.session_state["_baseline"].items():
        st.session_state[k] = v
    st.session_state["stress_test"] = (
        st.session_state.get("vessel", 0.0) > 0
        or st.session_state.get("insurance", 0.0) > 0
        or st.session_state.get("collection", 0.0) > 0
        or st.session_state.get("commission", 0.0) > 0
        or st.session_state.get("overheads", 0.0) > 0
    )


def current_scenario() -> dict:
    return {k: st.session_state[k] for k in SCENARIO_KEYS}


def current_eco_params() -> dict:
    _es = st.session_state.get("_eco", {})
    return {
        "horizon_years": int(_es.get("eco_horizon", DEFAULT_ECO_PARAMS["horizon_years"])),
        "scope": _es.get("eco_scope", DEFAULT_ECO_PARAMS["scope"]),
        "tariff_escalation_pct": float(_es.get("eco_tariff_esc", DEFAULT_ECO_PARAMS["tariff_escalation_pct"])),
        "epr_subsidy_eur_per_t": float(_es.get("eco_epr", DEFAULT_ECO_PARAMS["epr_subsidy_eur_per_t"])),
        "dpp_enabled": True,
        "cocreation_intensity": float(_es.get("eco_cocreation", DEFAULT_ECO_PARAMS["cocreation_intensity"])),
        "auto_expand_fleet": True,
        "max_boats": int(_es.get("eco_max_boats", DEFAULT_ECO_PARAMS["max_boats"])),
        "seed": DEFAULT_ECO_PARAMS["seed"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Model runner — exactly the v3.3.0 call sequence on an unmodified ReBoatDigitalBrain.
# ─────────────────────────────────────────────────────────────────────────────
def make_brain(scn: dict) -> ReBoatDigitalBrain:
    b = ReBoatDigitalBrain(target_island=scn["target_island"], season="High")
    # sync_brain_proxies(), v3.3.0
    b.proxies["marine_diesel_eur_per_liter"] = scn["proxy_diesel"]
    b.proxies["daily_berth_and_shore_power_eur"] = scn["proxy_berth"]
    b.proxies["municipal_waste_export_cost_per_tonne"] = scn["proxy_export"]
    b.proxies["shore_power_electricity_eur_per_kwh"] = scn["proxy_shore"]
    b.proxies["rPET_flake_market_value_eur_per_kg"] = scn["proxy_rpet"]
    b.proxies["recycled_yarn_market_value_eur_per_kg"] = scn["proxy_yarn"]
    b.proxies["labor_cost_eur_per_day"] = scn["proxy_labor"]
    b.proxies["maintenance_eur_per_day"] = scn["proxy_maintenance"]
    b.capex_baseline_eur = scn["proxy_capex"]
    return b


def build_config(scn: dict) -> dict:
    """build_config(), v3.3.0."""
    return {
        "operational_days": scn["op_days"],
        "transit_hours": scn["transit_hrs"],
        "plastic_processed_kg": scn["plastic_kg"],
        "textile_processed_kg": scn["textile_kg"],
        "local_workers_trained": scn["workers"],
        # The grant agreement foresees only quayside operation from the boat, so the
        # engine's optional land deployment (drayage to a town square) is always off.
        "land_event_mode": False,
        "capex_scenario": scn["capex_scenario"],
        "campaign_days": scn["op_days"],
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


@st.cache_data(show_spinner=False, max_entries=128)
def run_model(scn_json: str):
    scn = json.loads(scn_json)
    brain = make_brain(scn)
    cfg = build_config(scn)
    report = brain.execute_island_scenario(cfg)
    annual = brain.calculate_annual_business_plan(cfg)
    return report, annual


def model_for(scn: dict):
    return run_model(json.dumps(scn, sort_keys=True))


@st.cache_data(show_spinner=False, max_entries=32)
def run_eco_model(scn_json: str, eco_json: str):
    return run_ecosystem_simulation(json.loads(scn_json), json.loads(eco_json))


def eco_for(scn: dict, eco_params: dict | None = None):
    return run_eco_model(json.dumps(scn, sort_keys=True), json.dumps(eco_params or DEFAULT_ECO_PARAMS, sort_keys=True))


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — the scenario rail. Always visible, whichever view is open.
# ─────────────────────────────────────────────────────────────────────────────
def _logo_html() -> str:
    """The ReBoat project logo, embedded so it needs no static file server.
    Two variants: ink-and-blue for the light theme, white-and-light-blue for dark."""
    out = []
    for cls, fn in (("light", "reboat_logo.png"), ("dark", "reboat_logo_dark.png")):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", fn)
        try:
            with open(path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("ascii")
            out.append(f'<img class="logo {cls}" alt="ReBoat" src="data:image/png;base64,{b64}">')
        except OSError:
            out.append(f'<b class="logo {cls}">ReBoat</b>')
    return "".join(out)


def _eu_logo_html() -> str:
    """Horizon Europe Art. 17.2 EU emblem + 'Funded by the European Union' block."""
    out = []
    for cls, fn in (("light", "eu_funded_en.png"), ("dark", "eu_funded_en_dark.png")):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", fn)
        try:
            with open(path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("ascii")
            out.append(f'<img class="eu-logo {cls}" alt="Funded by the European Union" src="data:image/png;base64,{b64}">')
        except OSError:
            if cls == "light":
                out.append('<b class="eu-logo light">Funded by the European Union</b>')
    return "".join(out)


LOGO_HTML = _logo_html()
EU_LOGO_HTML = _eu_logo_html()


# ─────────────────────────────────────────────────────────────────────────────
# Start screen (5.5.1). Nothing is computed or shown until the user picks a pilot island.
# ─────────────────────────────────────────────────────────────────────────────
def start_with(island: str, guided: bool | None = None) -> None:
    """Same state as choosing that island in the sidebar, respecting standard vs. guided launch mode."""
    st.session_state["target_island"] = island
    apply_island_season_presets()
    for k in SCENARIO_KEYS:               # re-assign so the sidebar widgets are created with these values
        st.session_state[k] = st.session_state[k]
    st.session_state["_baseline"] = {k: st.session_state[k] for k in SCENARIO_KEYS}
    use_guided = (st.session_state.get("launch_mode", "standard") == "guided") if guided is None else bool(guided)
    st.session_state["guided_active"] = use_guided
    st.session_state["guided_hints"] = use_guided
    st.session_state["guided_step"] = 1
    st.session_state["_g_reset_rev"] = int(st.session_state.get("_g_reset_rev", 0)) + 1
    st.session_state["started"] = True


def enter_guided() -> None:
    """Enter the field-by-field walkthrough keeping all current scenario numbers."""
    st.session_state["guided_active"] = True
    st.session_state["guided_hints"] = True
    st.session_state["_g_reset_rev"] = int(st.session_state.get("_g_reset_rev", 0)) + 1


def exit_guided(target_url: str | None = None, keep_hints: bool = True) -> None:
    """Exit the guided walkthrough into the full 5-view dashboard keeping all edited numbers."""
    st.session_state["guided_active"] = False
    st.session_state["guided_hints"] = bool(keep_hints)
    for k in SCENARIO_KEYS:
        st.session_state[k] = st.session_state[k]
    st.session_state["stress_test"] = bool(st.session_state.get("stress_test", False))
    if target_url:
        st.session_state["_goto_url"] = target_url


def reset_all_defaults() -> None:
    """Restore factory defaults for the currently active island and reset multi-year controls."""
    st.session_state.update({
        "op_days": 14,
        "workers": 8,
        "capex_scenario": "EU_Grants",
        "price_point": DEFAULT_OPTIONS["price_point"],
        "reboat_share": DEFAULT_OPTIONS["reboat_share_pct"],
        "gate_fee": DEFAULT_OPTIONS["gate_fee_eur_per_t"],
        "prod_share": DEFAULT_OPTIONS["product_operator_share_pct"],
        "commission": DEFAULT_OPTIONS["sales_commission_pct"],
        "vessel": DEFAULT_OPTIONS["vessel_charter_eur_per_day"],
        "insurance": DEFAULT_OPTIONS["insurance_eur_per_year"],
        "collection": DEFAULT_OPTIONS["land_collection_eur_per_t"],
        "overheads": DEFAULT_OPTIONS["overheads_pct"],
        "prod_textile": 40,
        "prod_yarn": 80,
        "proxy_diesel": 1.75,
        "proxy_shore": 0.28,
        "proxy_rpet": 1.50,
        "proxy_yarn": 2.50,
        "proxy_labor": 800.0,
        "proxy_maintenance": 150.0,
        "proxy_capex": 430850.0,
        "stress_test": False,
        "_eco": dict(_ECO_STORE_DEFAULTS),
    })
    apply_island_season_presets()
    st.session_state["_g_reset_rev"] = int(st.session_state.get("_g_reset_rev", 0)) + 1


def view_start():
    is_guided = st.session_state.get("launch_mode", "standard") == "guided"
    html_block("""<style>
      [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"]{display:none !important}
      .start{max-width:980px; margin:2.5vh auto 0; text-align:left}
      .start .brand-row{display:flex; justify-content:space-between; align-items:center; gap:18px; flex-wrap:wrap; margin-bottom:16px}
      .start img.logo{width:220px; height:auto; display:block}
      .start img.eu-logo{height:58px; width:auto; display:block}
      .start img.logo.dark, .start img.eu-logo.dark{display:none}
      html[data-rb="dark"] .start img.logo.light, html[data-rb="dark"] .start img.eu-logo.light{display:none}
      html[data-rb="dark"] .start img.logo.dark, html[data-rb="dark"] .start img.eu-logo.dark{display:block}
      .start .lead{font-size:16.5px; color:var(--text-2); max-width:780px; margin:14px 0 0; line-height:1.58}
      .start .pick{margin:20px 0 6px; font-family:var(--f-cond); font-size:12px; letter-spacing:.08em; text-transform:uppercase; color:var(--text-3)}
      .mode{font-size:13px; color:var(--text-2); line-height:1.5; min-height:66px; margin:4px 2px 10px}
      .mode b{display:block; font-size:15.5px; color:var(--text); margin-bottom:4px}
      .isl{font-size:12.5px; color:var(--text-2); line-height:1.45; min-height:58px; margin:6px 2px 8px}
      .isl b{display:block; font-size:16px; color:var(--text)}
    </style>"""
               f'<div class="start"><div class="brand-row">{LOGO_HTML}{EU_LOGO_HTML}</div>'
               '<span class="eyebrow">Digital Tool for Business Plan &amp; Ecosystem Analysis · Task 2.6 · D2.3 · Release 6.0.0</span>'
               '<h1 style="margin-top:8px">Plan one operating year and a 10-year island ecosystem.</h1>'
               '<p class="lead">The tool estimates the annual revenue, running costs and investment of the mobile recycling plant, '
               'what the island gains in waste, carbon, local work and SROI, and how fleet scale and stakeholders co-evolve '
               'over 5–10 years across island archipelagos. Every figure can be opened and exported as PDF, Word, Excel or JSON.</p>'
               '<p class="pick">1 · How would you like to use this tool?</p></div>')
    m1, m2 = st.columns(2, gap="medium")
    with m1, st.container(border=True, key="mode_std"):
        html_block(
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
            f'<span class="eyebrow">Option 1 · Direct dashboard</span>'
            f'{chip("Selected", "good", True) if not is_guided else chip("All 5 views", "neutral")}</div>'
            '<div class="mode"><b>Explore directly (Standard mode)</b>'
            'Jump straight into the full 5-view interactive dashboard with every control in the sidebar.</div>'
        )
        st.button(
            "✓ Exploring directly" if not is_guided else "Choose direct exploration",
            key="pick_mode_std",
            on_click=lambda: st.session_state.update(launch_mode="standard"),
            type="secondary" if is_guided else "primary",
            width="stretch",
        )
    with m2, st.container(border=True, key="mode_guided"):
        html_block(
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
            f'<span class="eyebrow">Option 2 · First-time / non-technical</span>'
            f'{chip("Selected", "good", True) if is_guided else chip("Recommended", "neutral")}</div>'
            '<div class="mode"><b>Guided step-by-step walkthrough</b>'
            'Walk through every input field by field with plain-English explanations, live previews, and result stories.</div>'
        )
        st.button(
            "✓ Guided walkthrough selected" if is_guided else "Choose step-by-step guide",
            key="pick_mode_guided",
            on_click=lambda: st.session_state.update(launch_mode="guided"),
            type="primary" if is_guided else "secondary",
            width="stretch",
        )
    html_block('<div class="start" style="margin-top:0"><p class="pick">2 · Choose a pilot island to begin</p></div>')
    cols = st.columns(len(ISLAND_DATA))
    for col, island in zip(cols, ISLAND_DATA):
        p = get_pilot_profile(island)
        with col, st.container(border=True, key=f"start_{island.lower()}"):
            html_block(f'<div class="isl"><b>{esc(island)}</b>{esc(p.get("region", ""))}<br>{esc(p.get("berth_port", ""))}</div>')
            st.button(
                f"Start guided setup · {island}" if is_guided else f"Open {island}",
                key=f"go_{island}",
                on_click=start_with,
                args=(island,),
                type="primary" if island == "Corfu" else "secondary",
                width="stretch",
            )
    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)


if not st.session_state["started"]:
    _start_pages = [st.Page(view_start, title="Start", url_path="overview", default=True)] + [
        st.Page(view_start, title=t, url_path=u) for t, u in
        (("Impact", "impact"), ("Business plan", "business-plan"), ("Deliverables", "deliverables"),
         ("Ecosystem dynamics", "ecosystem"))]
    st.navigation(_start_pages, position="hidden").run()
    st.stop()

if st.session_state.get("guided_active", False):
    SCN_G = current_scenario()
    report_G, R_G = model_for(SCN_G)
    eco_G = eco_for(SCN_G, current_eco_params())
    brain_G = make_brain(SCN_G)
    _step_g = int(st.session_state.get("guided_step", 1))

    gm.render_guided_sidebar(
        step=_step_g,
        island=SCN_G["target_island"],
        on_exit=exit_guided,
        on_change_island=lambda: st.session_state.update(started=False, guided_active=False),
        logo_html=LOGO_HTML,
        ui_release=UI_RELEASE,
    )

    def _fin_name_g(key: str) -> str:
        return brain_G.capex_financing_scenarios.get(key, {}).get("name", FINANCING_LABELS.get(key, key))

    def view_guided():
        gm.render_guided_walkthrough(
            step=_step_g,
            scn=SCN_G,
            report=report_G,
            R=R_G,
            eco=eco_G,
            brain=brain_G,
            meta={
                "island_data": ISLAND_DATA,
                "financing_labels": FINANCING_LABELS,
                "price_points": PRICE_POINTS,
                "pkg_keys": PKG_KEYS,
                "pkg_info": PKG_INFO,
            },
            callbacks={
                "apply_presets": apply_island_season_presets,
                "toggle_stress": _toggle_stress_test,
                "on_exit": exit_guided,
                "on_reset_defaults": reset_all_defaults,
                "fin_name": _fin_name_g,
            },
        )
        ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)

    _guided_pages = [st.Page(view_guided, title="Guided Setup", url_path="overview", default=True)] + [
        st.Page(view_guided, title=t, url_path=u) for t, u in
        (("Impact", "impact"), ("Business plan", "business-plan"), ("Deliverables", "deliverables"),
         ("Ecosystem dynamics", "ecosystem"))]
    st.navigation(_guided_pages, position="hidden").run()
    st.stop()

SCN = current_scenario()
BASE = st.session_state["_baseline"]
DIRTY = SCN != BASE

with st.sidebar:
    html_block(
        f'<div class="brand">{LOGO_HTML}<span class="eyebrow">Digital Tool for Business Plan and Sustainability Evaluation · Task 2.6</span></div>'
        f'<div class="railstate"><span class="eyebrow">Scenario</span>'
        f'{chip("Modified", "warn", True) if DIRTY else chip("Baseline", "neutral", True)}</div>'
    )
    st.button("Step-by-step guided setup", key="sb_enter_guided", on_click=enter_guided, type="primary", width="stretch",
              help="Switch to a field-by-field walkthrough with plain-English explanations.")
    st.button("← Change island", on_click=lambda: st.session_state.update(started=False), width="stretch",
              help="Back to the start screen to choose another pilot island or mode.")
    st.checkbox("Show plain-language page guides", key="guided_hints",
                help="Show a short, jargon-free reading guide at the top of each dashboard view.")
    b1, b2 = st.columns(2)
    b1.button("Set as baseline", on_click=set_baseline, disabled=not DIRTY, type="primary", width="stretch")
    b2.button("Reset", on_click=reset_to_baseline, disabled=not DIRTY, width="stretch")
    html_block('<p class="railhint">Every figure recomputes as you change these. '
               'Deltas are measured against the saved baseline.</p>')

    st.selectbox("Pilot island", list(ISLAND_DATA.keys()), key="target_island",
                 on_change=apply_island_season_presets,
                 help="Changing island loads that island's defaults for transit time, berth fee and volumes.")
    st.selectbox("Financing route", list(FINANCING_LABELS.keys()), key="capex_scenario",
                 format_func=lambda k: FINANCING_LABELS[k])
    st.slider("Campaign length (days)", 1, 60, key="op_days",
              help="Scales the active days of every month: 14 days is the reference calendar of 191 active days a year. "
                   "Waste, visitors, revenue and costs all scale with it. The single-campaign results in the JSON export "
                   "use this length directly.")
    st.slider("Marine transit (hours)", 0.0, 72.0, step=0.5, key="transit_hrs")
    st.slider("Island operators trained", 0, 50, key="workers")

    with st.expander("Waste input · per 14 active days", expanded=True):
        st.number_input("Plastic processed (kg)", min_value=0.0, step=100.0, key="plastic_kg",
                        help="Plastic delivered to the plant. The shredding plant processes at most 100 kg/h × 8 h a day "
                             "(T2.4 machine throughput data); plastic above it is not processed and does not change "
                             "flakes, products, waste diverted or savings.")
        PLASTIC_NOTE = st.empty()   # filled after the model runs (5.5.1)
        st.number_input("Textile processed (kg)", min_value=0.0, step=50.0, key="textile_kg",
                        help="Textile delivered to the plant. The textile line processes at most its capacity "
                             "(spinner 0.5 kg/h × 8 h a day); textile above it is not processed and does not change "
                             "yarn, products, waste diverted or savings.")
        TEXTILE_NOTE = st.empty()   # filled after the model runs (5.5.1)
    with st.expander("Tourism packages · participants and ReBoat share"):
        st.selectbox("Package price (WP4 pricing note)", list(PRICE_POINTS), key="price_point",
                     format_func=lambda k: PRICE_POINTS[k],
                     help="Per-person cost floors of complete packages from the WP4 pricing note, by island and season "
                          "(Value positioning, B&B or 2–3★ hotel, no flights, no accommodation taxes).")
        st.number_input("ReBoat share of the package price (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.1f",
                        key="reboat_share",
                        help="Packages are sold by tour operators or DMCs (GA Tasks 4.2–4.3); the plant operator earns this "
                             "share of the package price. Placeholder pending commercial tourism agreements.")
        for k, _pk in PKG_KEYS:
            name, desc = PKG_INFO[k]
            st.number_input(f"{name} · participants per 14 days", min_value=0, step=1, key=f"pkg_{k}",
                            help=f"**{name}** ({PACKAGE_DURATIONS[_pk]}) — {desc}")
        _isl_note = st.session_state.target_island
        _tab = PRICING_NOTE.get(_isl_note, PRICING_NOTE["Corfu"])
        html_block('<p class="railhint" style="margin-top:4px">Package prices at ' + esc(_isl_note) + ' (€ per person, '
                   'low / mid / high season): ' + " · ".join(
                       f"{PKG_INFO[k][0]} {_tab['Low'][i][0]:,}–{_tab['Low'][i][1]:,} / {_tab['Mid'][i][0]:,}–{_tab['Mid'][i][1]:,} / "
                       f"{_tab['High'][i][0]:,}–{_tab['High'][i][1]:,}" for i, (k, _pk) in enumerate(PKG_KEYS)) + '</p>')
    with st.expander("Upcycled products sold · per campaign"):
        st.number_input("Moulded goods · €12", min_value=0, step=1, key="prod_molded")
        st.number_input("3D-printed artefacts · €35", min_value=0, step=1, key="prod_3d")
        st.number_input("Pressed furniture panels · €95", min_value=0, step=1, key="prod_panel")
        st.number_input("Woven textiles · €45", min_value=0, step=1, key="prod_textile")
        st.number_input("Yarn spools · €8", min_value=0, step=1, key="prod_yarn")
        st.number_input("Operator share of product sales (%)", min_value=0.0, max_value=100.0, step=5.0, format="%.0f",
                        key="prod_share", help="100% = the plant operator sells the products. Lower values model "
                                               "arrangements in which the municipality or a partner keeps part of the sales.")
    with st.expander("Costs and prices"):
        st.number_input("Marine diesel (€/L)", step=0.05, format="%.2f", key="proxy_diesel")
        st.number_input("Berth and port fees (€/day)", step=10.0, key="proxy_berth")
        st.number_input("Avoided disposal cost (€/t)", step=10.0, key="proxy_export",
                        help="What the island no longer pays per tonne: ferry freight to the mainland (GA: 100–250 €/t for "
                             "minor islands) or the local incinerator (Terceira: €50/t).")
        st.number_input("Gate fee charged for treated waste (€/t)", min_value=0.0, step=50.0, key="gate_fee",
                        help=f"Recycling-as-a-Service fee paid by the municipality to the operator. The GA business plan "
                             f"uses €80,000 per 50 t (= €{GA_RAAS_GATE_FEE_EUR_PER_T:,.0f}/t, Part B Table 2.7). 0 = not charged.")
        st.number_input("Shore power (€/kWh)", step=0.01, format="%.2f", key="proxy_shore")
        st.number_input("Operator crew (€/day)", step=50.0, key="proxy_labor")
        st.number_input("Maintenance and consumables (€/day)", step=10.0, key="proxy_maintenance")
        st.number_input("Recycled plastic flakes (€/kg)", step=0.10, format="%.2f", key="proxy_rpet")
        st.number_input("Recycled yarn (€/kg)", step=0.10, format="%.2f", key="proxy_yarn")
        st.number_input("CapEx baseline (€)", step=1000.0, format="%.0f", key="proxy_capex")
    with st.expander("Other operating costs · default 0"):
        st.checkbox("Illustrative full-cost stress test (Table 27)", key="stress_test", on_change=_toggle_stress_test,
                    help="Loads the illustrative unquoted-cost stress test (€200/day charter, €6,000/yr insurance, "
                         "€30/t land collection, 10% sales commission, 5% overheads).")
        st.number_input("Vessel charter (€/active day)", min_value=0.0, step=50.0, key="vessel")
        st.number_input("Insurance (€/year)", min_value=0.0, step=500.0, key="insurance")
        st.number_input("Collection on land (€/t)", min_value=0.0, step=10.0, key="collection")
        st.number_input("Sales commissions (% of ReBoat tourism revenue)", min_value=0.0, max_value=100.0, step=1.0,
                        key="commission")
        st.number_input("Overheads (% of other operating costs)", min_value=0.0, max_value=100.0, step=1.0, key="overheads")
        html_block('<p class="railhint">Optional commercial cost lines; at 0 these lines are omitted from the P&amp;L.</p>')

    html_block(
        '<div class="foot" style="margin-top:14px;padding-top:10px;border-top:1px solid var(--rule)">'
        '<span class="eyebrow">Project</span><dl>'
        '<dt>Task</dt><dd>2.6 · D2.3 (M24)</dd><dt>WP</dt><dd>WP2 · POLIMI</dd>'
        '<dt>Grant</dt><dd>101182350</dd><dt>Call</dt><dd>CL6-2024-CIRCBIO-01</dd>'
        f'<dt>Release</dt><dd>{UI_RELEASE} · MIT</dd></dl></div>'
    )

# ─────────────────────────────────────────────────────────────────────────────
# Run the model for the current scenario and the baseline.
# ─────────────────────────────────────────────────────────────────────────────
SCN = current_scenario()
report, R = model_for(SCN)

# Textile line capacity note under the textile input (5.5.1).
_brain = make_brain(SCN)
_tex_cap14 = _brain.get_textile_capacity_kg(14)
_tex_rate = _brain.textile_line_rate_kg_hr()
_fl = R["material_flows"]
_tex_msg = (f"Line capacity <b>{nf(_tex_cap14)} kg</b> per 14 active days (textile spinning line limit "
            f"{nf(_tex_rate, 1)} kg/h × {nf(_brain.operating_hours_per_day)} h). Textile above it is not processed.")
if _fl["textile_not_accepted_t"] > 0 and _fl["textile_delivered_t"] > 0:
    _share = _fl["textile_not_accepted_t"] / _fl["textile_delivered_t"] * 100
    _tex_msg = (f'<span style="color:var(--warn)"><b>Over capacity:</b> {nf(_fl["textile_not_accepted_t"] * 1000)} kg of '
                f'{nf(_fl["textile_delivered_t"] * 1000)} kg a year ({_share:.0f}%) is not processed.</span> ' + _tex_msg)
_pl_cap14 = _brain.get_plastic_capacity_kg(14)
_pl_msg = (f"Shredding capacity <b>{nf(_pl_cap14)} kg</b> per 14 active days "
           f"({nf(_brain.throughput_bottlenecks['plastics_shredding_kg_hr'])} kg/h × {nf(_brain.operating_hours_per_day)} h). "
           "Plastic above it is not processed.")
if _fl["plastic_not_accepted_t"] > 0 and _fl["plastic_collected_t"] > 0:
    _pshare = _fl["plastic_not_accepted_t"] / _fl["plastic_collected_t"] * 100
    _pl_msg = (f'<span style="color:var(--warn)"><b>Over capacity in the busiest months:</b> '
               f'{nf(_fl["plastic_not_accepted_t"] * 1000)} kg of {nf(_fl["plastic_collected_t"] * 1000)} kg a year '
               f'({_pshare:.0f}%) is not processed.</span> ' + _pl_msg)
with PLASTIC_NOTE.container():
    html_block(f'<p class="railhint">{_pl_msg}</p>')
with TEXTILE_NOTE.container():
    html_block(f'<p class="railhint">{_tex_msg}</p>')
_, RB = model_for(st.session_state["_baseline"])
cfg = build_config(SCN)
profile = get_pilot_profile(SCN["target_island"])
island_profile_data = PILOT_PROFILES.get(SCN["target_island"], {})
_cap = ReBoatDigitalBrain(SCN["target_island"]).capex_financing_scenarios
CAPEX = report["CapEx_Allocation"]                      # backend.calculate_capex_allocation()
GRANT_PCT = CAPEX["coverage_percent"]
GRANT_TOTAL = CAPEX["grant_coverage_eur"]
EQUITY_TOTAL = CAPEX["net_equity_required_eur"]
GRANT_ANNUAL = GRANT_TOTAL / 10.0                       # same divisor backend uses for SROI
WAGES = R["annual_wages_eur"]                           # local wages = operator crew cost (engine)
SOCIETAL = R["annual_societal_value_eur"]                # engine: net municipal saving + wages + carbon + turnover
KEPT_BY_OTHERS = R["annual_product_sales_total_eur"] - R["annual_finished_goods_revenue_eur"]


BASIS = {
    "annual_tourism_revenue_eur": (f"{SCN['reboat_share']:.1f}% of {eur(R['annual_package_turnover_eur'])} package turnover "
                                   f"(WP4 pricing-note prices, {SCN['price_point']} point, by season); packages sold by tour operators"),
    "annual_finished_goods_revenue_eur": ("Moulded goods, printed artefacts, furniture panels, woven textiles and yarn spools"
                                          + (f"; operator keeps {SCN['prod_share']:.0f}% of sales" if SCN["prod_share"] < 100 else "")),
    "annual_bulk_flakes_revenue_eur": f"Recovered plastic not used for products, sold at €{SCN['proxy_rpet']:.2f}/kg",
    "annual_bulk_yarn_revenue_eur": f"Recycled yarn not used for products, sold at €{SCN['proxy_yarn']:.2f}/kg",
    "annual_gate_fee_revenue_eur": f"€{nf(SCN['gate_fee'])} per tonne of waste treated, paid by the municipality",
    "annual_labor_cost_eur": f"€{nf(SCN['proxy_labor'], 2)} per active day × seasonal multiplier",
    "annual_berth_cost_eur": f"€{nf(SCN['proxy_berth'], 2)} per active day × seasonal multiplier at {esc(profile.get('berth_port', 'the port'))}",
    "annual_maintenance_cost_eur": f"€{nf(SCN['proxy_maintenance'], 2)} per active day × seasonal multiplier",
    "annual_power_cost_eur": f"52 kW × 8 h per active day × seasonal multiplier at €{SCN['proxy_shore']:.2f}/kWh",
    "annual_fuel_cost_eur": f"Transit to and from the island at €{SCN['proxy_diesel']:.2f}/L of diesel",
    "annual_vessel_cost_eur": f"€{nf(SCN['vessel'])} per active day",
    "annual_insurance_cost_eur": f"€{nf(SCN['insurance'])} per year",
    "annual_land_collection_cost_eur": f"€{nf(SCN['collection'])} per tonne collected",
    "annual_commission_cost_eur": f"{SCN['commission']:.1f}% of the ReBoat tourism revenue",
    "annual_overheads_cost_eur": f"{SCN['overheads']:.1f}% of the other operating costs",
}

MUNI_DERIV = (f"waste      <b>{nf(R['annual_waste_diverted_tonnes'], 2)} t</b>\n"
              f"× avoided  <b>€{nf(SCN['proxy_export'], 0)}/t</b>\n"
              f"= avoided  <b>{eur(R['annual_avoided_disposal_cost_eur'])}</b>\n"
              f"− gate fee <b>{eur(R['annual_gate_fee_paid_eur'])}</b>\n"
              f"──────────────────\n= <b>{eur_s(R['annual_municipal_savings_eur'])}</b> per year")


def _base_societal():
    return RB["annual_societal_value_eur"]


def _pop(p):
    v = p.get("population_permanent")
    return "—" if v is None else nf(v)


def fin_name(key):
    return _cap.get(key, _cap["EU_Grants"])["name"]


# ─────────────────────────────────────────────────────────────────────────────
# Masthead and ticker — drawn at the top of every view by head().
# ─────────────────────────────────────────────────────────────────────────────
META = [("Port", profile.get("berth_port", "—")),
        ("Population", _pop(profile)),
        ("Peak", profile.get("peak_tourist_multiplier", "—")),
        ("Financing", fin_name(SCN["capex_scenario"]))]
TICKER = [
    (PL.KPI["ratio"], x2(R["annual_revenue_to_opex_ratio"])),
    (PL.NET, eur_s(R["annual_net_after_capex_eur"])),
    (PL.REVENUE, eur(R["annual_gross_revenue_eur"])),
    ("Municipal saving", eur(R["annual_municipal_savings_eur"])),
    ("Waste diverted", f"{nf(R['annual_waste_diverted_tonnes'], 1)} t"),
    (PL.KPI["co2"], f"{nf(R['annual_carbon_avoided_tonnes'], 1)} t"),
    (PL.KPI["diesel_co2"], f"{nf(R['annual_transit_diesel_co2_tonnes'], 1)} t"),
    ("SROI", x2(R["annual_sroi_ratio"]) if R["annual_sroi_ratio"] is not None else "n/a"),
    (PL.KPI["sroi_noturn"], x2(R["annual_sroi_without_turnover"]) if R["annual_sroi_without_turnover"] is not None else "n/a"),
    ("Operators", nf(SCN["workers"])),
]
SECTIONS = {
    "overview": ("01", "Overview"),
    "impact": ("02", "Island & public impact"),
    "business-plan": ("03", "Business plan"),
    "deliverables": ("04", "Deliverables"),
    "ecosystem": ("05", "Ecosystem dynamics"),
}


def head(key: str, title: str) -> None:
    """Section label, display headline, live ticker — the top of every view."""
    ui.page_marker(key)
    n, name = SECTIONS[key]
    ui.masthead(f"{n} · {name} · {SCN['target_island']}", title, META)
    ui.ticker(TICKER)
    html_block(f'<p class="railhint" style="margin:-4px 0 0">{esc(PL.SCENARIO_NOTE)} '
               f'{esc(VIEWPOINT.get(key, ""))}</p>')
    if st.session_state.get("guided_hints", False):
        _eco_arg = eco_for(SCN, current_eco_params()) if key == "ecosystem" else None
        gm.render_view_guide(key, R, SCN, eco=_eco_arg)


VIEWPOINT = {
    "overview": "View: the plant operator.",
    "impact": "View: the municipality and the public funder.",
    "business-plan": "View: the operator and its investors.",
    "deliverables": "",
    "ecosystem": "View: regional operator, municipality, policy maker and fleet investor (multi-year horizon).",
}



# ═════════════════════════════════════════════════════════════════════════════
# VIEW · OVERVIEW
# ═════════════════════════════════════════════════════════════════════════════
def view_overview():
    head("overview", "The whole year, month by month.")
    months = R["monthly_timeseries"]
    solvent = R["annual_revenue_to_opex_ratio"] >= 1.0
    covers = R["annual_net_after_capex_eur"] >= 0
    worst = min(months, key=lambda m: m["rev_opex_ratio"])
    best = max(months, key=lambda m: m["rev_opex_ratio"])
    below = sum(1 for m in months if m["rev_opex_ratio"] < 1.0)
    island = SCN["target_island"]

    headline = (f"The plant covers its own running costs at {island} in all 12 months." if solvent and below == 0
                else f"The plant covers its running costs at {island} over the year." if solvent
                else f"At these settings the plant does not cover its running costs at {island}.")
    show_note(headline,
              f"Full-year revenue of <strong>{eur(R['annual_gross_revenue_eur'])}</strong> against "
              f"<strong>{eur(R['annual_total_opex_eur'])}</strong> of operating cost — a coverage ratio of "
              f"<strong>{x2(R['annual_revenue_to_opex_ratio'])}</strong>, with "
              f"{'no month' if below == 0 else f'{below} month' + ('' if below == 1 else 's')} below the 1.00× breakeven line. "
              f"After {eur(R['annual_capex_amortization_eur'])} of straight-line CapEx amortisation the year closes at "
              f"<strong>{eur_s(R['annual_net_after_capex_eur'])}</strong>."
              + (" Required municipal operating subsidy: <strong>€0.00</strong>." if solvent else ""),
              "good" if solvent and covers else "warn" if solvent else "crit")

    sroi = R["annual_sroi_ratio"]
    sroi_nt = R["annual_sroi_without_turnover"]
    tiles([
        tile("Operating solvency", x2(R["annual_revenue_to_opex_ratio"]), lead=True,
             chip_html=chip("Self-funding" if solvent else "Deficit", "good" if solvent else "crit", True),
             delta_html=delta(R["annual_revenue_to_opex_ratio"], RB["annual_revenue_to_opex_ratio"], lambda v: f"{v:.2f}×"),
             sub=(f"{(R['annual_revenue_to_opex_ratio'] - 1) * 100:.0f}% buffer above breakeven" if R["annual_revenue_to_opex_ratio"] >= 1
                  else f"{(1 - R['annual_gross_revenue_eur'] / R['annual_total_opex_eur']) * 100:.1f}% short of breakeven")
                 + f" · operating margin {eur_s(R['annual_net_operating_margin_eur'])}",
             deriv=(f"revenue        <b>{eur(R['annual_gross_revenue_eur'], 2)}</b>\n"
                    f"operating cost <b>{eur(R['annual_total_opex_eur'], 2)}</b>\n"
                    f"──────────────────\n"
                    f"ratio  = <b>{x2(R['annual_revenue_to_opex_ratio'])}</b>"),
             src="Twelve monthly campaigns over the calendar year."),
        tile(PL.NET, eur_s(R["annual_net_after_capex_eur"]),
             chip_html=chip("Amortised" if covers else "Shortfall", "good" if covers else "warn", True),
             delta_html=delta(R["annual_net_after_capex_eur"], RB["annual_net_after_capex_eur"], eur),
             sub=f"After {eur(R['annual_capex_amortization_eur'])}/yr straight-line depreciation over 10 years",
             deriv=(f"operating margin      <b>{eur(R['annual_net_operating_margin_eur'], 2)}</b>\n"
                    f"− CapEx amortisation  <b>{eur(R['annual_capex_amortization_eur'], 2)}</b>\n"
                    f"──────────────────\n= <b>{eur_s(R['annual_net_after_capex_eur'])}</b>")),
        tile("Municipal saving", eur_s(R["annual_municipal_savings_eur"]), chip_html=chip("Avoided disposal cost"),
             delta_html=delta(R["annual_municipal_savings_eur"], RB["annual_municipal_savings_eur"], eur),
             sub=f"{nf(R['annual_waste_diverted_tonnes'], 1)} t treated on the island at €{nf(SCN['proxy_export'])}/t avoided"
                 + (f", less {eur(R['annual_gate_fee_paid_eur'])} of gate fee" if R["annual_gate_fee_paid_eur"] else ""),
             deriv=MUNI_DERIV),
        tile("Social return (SROI)", x2(sroi) if sroi is not None else "n/a", chip_html=chip(f"{GRANT_PCT}% grant"),
             delta_html=delta(sroi, RB["annual_sroi_ratio"], lambda v: f"{v:.2f}×"),
             sub=(f"{eur(SOCIETAL)} of societal value per {eur(GRANT_ANNUAL)} grant/yr"
                  + (f" · excl. turnover {x2(sroi_nt)}" if sroi_nt is not None else "")
                  if sroi is not None
                  else "No public grant under this financing route, so SROI is undefined"),
             deriv=(f"municipal savings   <b>{eur(R['annual_municipal_savings_eur'], 2)}</b>\n"
                    f"+ local wages       <b>{eur(WAGES, 2)}</b>\n"
                    f"+ carbon value      <b>{eur(R['annual_carbon_value_eur'], 2)}</b>\n"
                    f"+ commercial rev.   <b>{eur(R['annual_gross_revenue_eur'], 2)}</b>\n"
                    + (f"+ products kept by others <b>{eur(KEPT_BY_OTHERS, 2)}</b>\n" if KEPT_BY_OTHERS > 0.005 else "")
                    + f"──────────────────\n"
                    f"÷ annual grant      <b>{eur(GRANT_ANNUAL, 2)}</b>\n"
                    f"= <b>{x2(sroi)}</b>  (excl. turnover: <b>{x2(sroi_nt)}</b>)") if sroi is not None else ""),
    ])

    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        with panel("Annual solvency curve",
                   chip("All 12 months solvent", "good", True) if below == 0
                   else chip(f"{below} month{'s' if below != 1 else ''} below breakeven", "warn", True),
                   sub="Revenue ÷ operating cost for each month against the 1.00× breakeven"):
            ch.plot(ch.step_curve(months), key="ch_solvency")
    with right:
        html_block(
            f'<div class="plain"><span class="eyebrow">Weakest month</span>'
            f'<div class="val" style="font-size:26px">{x2(worst["rev_opex_ratio"])}</div>'
            f'<p style="font-size:12px;color:var(--text-2)">{worst["month_name"]} — {worst["season"]} season, '
            f'{worst["days_active"]} active days. Revenue {eur(worst["revenue_eur"])} against operating cost {eur(worst["opex_eur"])}.</p></div>'
            f'<div class="plain" style="margin-top:12px"><span class="eyebrow">Strongest month</span>'
            f'<div class="val" style="font-size:26px">{x2(best["rev_opex_ratio"])}</div>'
            f'<p style="font-size:12px;color:var(--text-2)">{best["month_name"]} — {best["season"]} season, '
            f'{best["days_active"]} active days.</p></div>'
        )

    with panel("Revenue against operating cost, month by month",
               chip("Bars: revenue and operating cost · line: net result after amortisation")):
        ch.plot(ch.monthly_split_figure(months), key="ch_monthly")
    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)



# ═════════════════════════════════════════════════════════════════════════════
# VIEW · IMPACT — what the island keeps and what the public grant buys
# ═════════════════════════════════════════════════════════════════════════════
def view_impact():
    head("impact", "What the island and the public gain.")
    airspace = R["annual_waste_diverted_tonnes"] / 0.35
    sroi = R["annual_sroi_ratio"]
    show_note("What a mayor and a funder are checking",
              "What the plant keeps on the island — money not spent on ferry freight, waste kept out of landfill, local jobs — "
              "and the value society gains for every euro of public grant. "
              f"<strong>{esc(profile.get('landfill_status', ''))}</strong>")

    html_block(ui.bracket("for the island"))
    tiles([
        tile("Municipal saving", eur_s(R["annual_municipal_savings_eur"]), lead=True,
             chip_html=chip("Budget line", "good" if R["annual_municipal_savings_eur"] >= 0 else "crit", True),
             delta_html=delta(R["annual_municipal_savings_eur"], RB["annual_municipal_savings_eur"], eur),
             sub="Disposal cost the island no longer pays (ferry freight or incinerator), net of any gate fee",
             deriv=MUNI_DERIV),
        tile(PL.KPI["waste"], f"{nf(R['annual_waste_diverted_tonnes'], 1)} t",
             delta_html=delta(R["annual_waste_diverted_tonnes"], RB["annual_waste_diverted_tonnes"], lambda v: f"{nf(v, 1)} t"),
             sub="Plastic and textile waste recycled on the island instead of landfilled or shipped away"),
        tile(PL.KPI["airspace"], f"{nf(airspace)} m³",
             sub="Landfill volume the island no longer has to find",
             deriv=f"{nf(R['annual_waste_diverted_tonnes'], 2)} t ÷ 0.35 t per m³ = <b>{nf(airspace)} m³</b>"),
        tile("Island operators employed", nf(SCN["workers"]),
             delta_html=delta(SCN["workers"], BASE["workers"], nf),
             sub=f"{eur(WAGES)} of wages paid on the island — the operator crew cost in the business plan",
             deriv=(f"Local wages = operator crew cost: €{nf(SCN['proxy_labor'], 2)} per active day "
                    f"× season multiplier, summed over 12 months = <b>{eur(WAGES, 2)}</b>")),
    ])

    html_block(ui.bracket("for the public"))
    sroi_nt = R["annual_sroi_without_turnover"]
    diesel_co2 = R["annual_transit_diesel_co2_tonnes"]
    diesel_l = R["annual_diesel_litres"]
    shore_kwh = R["annual_shore_power_kwh"]
    tiles([
        tile(PL.KPI["sroi"], x2(sroi) if sroi is not None else "n/a", lead=True,
             delta_html=delta(sroi, RB["annual_sroi_ratio"], lambda v: f"{v:.2f}×"),
             sub=(f"Societal value per euro of grant/yr · excl. turnover: {x2(sroi_nt)}"
                  if sroi is not None
                  else "No public grant on this financing route, so there is no return on grant"),
             deriv=(f"societal value  <b>{eur(SOCIETAL, 2)}</b>\n÷ grant per year <b>{eur(GRANT_ANNUAL, 2)}</b>\n"
                    f"──────────────────\n= <b>{x2(sroi)}</b>  (excl. turnover: <b>{x2(sroi_nt)}</b>)")
             if sroi is not None else ""),
        tile(PL.KPI["societal"], eur(SOCIETAL), delta_html=delta(SOCIETAL, _base_societal(), eur),
             sub="Turnover + net municipal saving + local wages + carbon value"),
        tile(PL.KPI["co2"], f"{nf(R['annual_carbon_avoided_tonnes'], 1)} t",
             delta_html=delta(R["annual_carbon_avoided_tonnes"], RB["annual_carbon_avoided_tonnes"], lambda v: f"{nf(v, 1)} t"),
             sub=(f"Valued at {eur(R['annual_carbon_value_eur'])} (€80/t) · "
                  f"indicative transit diesel CO₂ {nf(diesel_co2, 1)} t (pending Task 5.7 LCA)"),
             deriv=(f"{nf(R['annual_waste_diverted_tonnes'], 2)} t × 0.12 t CO₂/t = <b>{nf(R['annual_carbon_avoided_tonnes'], 2)} t</b> gross\n"
                    f"× €80.00/t = <b>{eur(R['annual_carbon_value_eur'], 2)}</b>\n"
                    f"Transit diesel ({nf(diesel_l)} L × 2.68 kg/L) = <b>{nf(diesel_co2, 2)} t</b> CO₂\n"
                    f"Shore power demand (52 kW × 8 h) = <b>{nf(shore_kwh)} kWh/yr</b>")),
        tile("Public grant per year", eur(GRANT_ANNUAL), chip_html=chip(f"{GRANT_PCT}% grant"),
             sub=f"{eur(GRANT_TOTAL)} of grant spread over 10 years"),
    ])
    show_note("Environmental screening boundary (pre-LCA)",
              f"<strong>{nf(R['annual_carbon_avoided_tonnes'], 2)} t CO₂</strong> measures gross waste-transport emissions avoided "
              f"(0.12 t CO₂/t diverted × €80/t). Indicative vessel transit emits <strong>{nf(diesel_co2, 2)} t CO₂</strong> "
              f"({nf(diesel_l)} L marine diesel at 2.68 kg CO₂/L), while on-board reprocessing draws <strong>{nf(shore_kwh)} kWh/yr</strong> "
              "(52 kW Scenario B × 8 h/active day). Gross avoidance is not netted against process energy/grid mix pending the Task 5.7 (D5.3) LCA.")

    left, right = st.columns([1.55, 1], gap="medium")
    with left:
        with panel("How the societal value is built",
                   sub=(f"Divided by the {eur(GRANT_ANNUAL)} grant per year, this total gives the SROI of {x2(sroi)}"
                        if GRANT_ANNUAL > 0 else "No grant under this financing route, so SROI is undefined")):
            ch.plot(ch.waterfall([
                ("Turnover", R["annual_gross_revenue_eur"], S1, "step"),
                ("Municipal saving", R["annual_municipal_savings_eur"], S2, "step"),
                ("Local wages", WAGES, S5, "step"),
                ("Carbon value", R["annual_carbon_value_eur"], NEUTRAL, "step"),
            ] + ([("Products kept by others", KEPT_BY_OTHERS, S4, "step")] if KEPT_BY_OTHERS > 0.005 else []) + [
                ("Societal value", SOCIETAL, S3, "total"),
            ]), key="ch_sroi")
    with right:
        with panel(f"Island context — {esc(SCN['target_island'])}"):
            rows = [
                ("Permanent population", _pop(profile)),
                ("Peak tourism", profile.get("peak_tourist_multiplier", "—")),
                ("Peak waste generation", "—" if profile.get("waste_generation_peak_t_day") is None
                 else f"{nf(profile['waste_generation_peak_t_day'])} t/day"),
                ("Waste management", profile.get("landfill_status", "—")),
                ("Designated port", profile.get("berth_port", "—")),
                ("Governance counterpart", profile.get("tourism_governance", "—")),
            ]
            html_block('<div class="ctxw">' + ui.table([], [([(esc(k), "l"), (esc(v), "ctx")], "") for k, v in rows]) + "</div>")

    F_ = R["material_flows"]
    with panel("Material flows over the year", chip("tonnes per year")):
        frows = [
            ("Plastic delivered", F_["plastic_collected_t"], ""),
            ("   processed by the shredding plant", F_["plastic_accepted_t"], "Plant limited to 100 kg/h over 8 h a day"),
            ("   not processed", F_["plastic_not_accepted_t"], "Stays in the island's existing waste stream"),
            ("Textile delivered", F_["textile_delivered_t"], ""),
            ("   accepted by the textile line", F_["textile_accepted_t"],
             f"Line limited to {ReBoatDigitalBrain().textile_line_rate_kg_hr():.1f} kg/h (textile spinning line limit) over 8 h a day"),
            ("   not accepted", F_["textile_not_accepted_t"], "Stays in the island's existing waste stream"),
            ("Flakes recovered (85% of processed plastic)", F_["flakes_recovered_t"], ""),
            ("   used for products", F_["flakes_to_products_t"], "Moulded goods, printed artefacts, pressed panels"),
            ("   sold in bulk", F_["flakes_sold_bulk_t"], f"at €{SCN['proxy_rpet']:.2f}/kg"),
            ("Yarn recovered (75% of accepted textile)", F_["yarn_recovered_t"], ""),
            ("   used for products", F_["yarn_to_products_t"], "Woven textiles and yarn spools"),
            ("   sold in bulk", F_["yarn_sold_bulk_t"], f"at €{SCN['proxy_yarn']:.2f}/kg"),
            ("Process losses", F_["process_losses_t"], "Fines, moisture and off-cuts not recovered"),
        ]
        html_block(ui.table([("Flow", False), ("t / year", True), ("Note", False)],
                            [([(esc(a), "l"), (nf(b, 2 if b < 10 else 1), "n"), (esc(c), "wrap")], "") for a, b, c in frows]))

    with panel("Social return under each financing route"):
        rows = []
        for key in FINANCING_LABELS:
            alt_rep, alt = model_for({**SCN, "capex_scenario": key})
            ca = alt_rep["CapEx_Allocation"]
            s_ = alt["annual_sroi_ratio"]
            s_nt = alt["annual_sroi_without_turnover"]
            pb = alt["annual_payback_years"]
            rows.append(([
                (esc(ca["scenario_name"]) + (" &nbsp;" + chip("current", "good") if key == SCN["capex_scenario"] else ""), "l"),
                (f"{ca['coverage_percent']}%", "n"), (eur(ca["grant_coverage_eur"]), "n"), (eur(ca["net_equity_required_eur"]), "n"),
                ("n/a — no grant" if s_ is None else x2(s_), "n"),
                ("n/a" if s_nt is None else x2(s_nt), "n"),
                ("—" if pb is None else f"{pb:.2f} yr", "n"),
            ], ""))
        html_block(ui.table([("Financing route", False), ("Grant share", True), ("Public grant", True),
                             ("Equity", True), ("SROI", True), ("SROI (excl. turn.)", True), (PL.KPI["payback"], True)], rows))

    show_note("No operating subsidy needed" if R["annual_net_operating_margin_eur"] >= 0 else "An operating subsidy would be needed",
              f"The plant earns {eur(R['annual_gross_revenue_eur'])} and spends {eur(R['annual_total_opex_eur'])} running itself. "
              f"The {eur_s(R['annual_net_operating_margin_eur'])} difference is what is left before the investment is repaid, so "
              + ("no municipal contribution is required to keep it operating." if R["annual_net_operating_margin_eur"] >= 0
                 else "at these settings a municipal contribution <strong>would</strong> be needed to keep it operating.")
              + (f" The municipality pays a gate fee of €{nf(SCN['gate_fee'])}/t ({eur(R['annual_gate_fee_paid_eur'])} a year) and grants berth space at {esc(profile.get('berth_port', ''))}. "
                 if R["annual_gate_fee_paid_eur"] else
                 f" The municipality's contribution is limited to what it grants in kind — berth space at {esc(profile.get('berth_port', ''))}. ")
              + "Recovering the investment is covered on <em>Business plan</em>.",
              "good" if R["annual_net_operating_margin_eur"] >= 0 else "crit")
    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)


# ═════════════════════════════════════════════════════════════════════════════
# VIEW · BUSINESS PLAN
# ═════════════════════════════════════════════════════════════════════════════
def view_business_plan():
    head("business-plan", "The business plan, line by line.")
    rev_t = max(R["annual_gross_revenue_eur"], 1.0)
    opex_t = max(R["annual_total_opex_eur"], 1.0)
    pb = R["annual_payback_years"]
    BE = R["breakeven_reboat_share_pct"]
    show_note("What an investor or funder is checking",
              "Whether the plant earns more than it costs to run, how quickly the equity comes back, and what the year "
              "looks like once the investment is amortised. Every line below adds up to the totals.")
    if all(SCN.get(k, 0.0) == 0.0 for k in ("vessel", "insurance", "collection", "commission", "overheads")):
        show_note("Unquoted operating costs currently set to €0",
                  "Vessel charter, insurance, land collection, sales commissions, and overheads default to €0 until partner "
                  "local commercial quotations are finalised. Enable <em>Illustrative full-cost stress test (Table 27)</em> "
                  "in the sidebar to evaluate the combined cost impact on coverage and break-even share.",
                  "warn")
    tiles([
        tile(PL.MARGIN, eur_s(R["annual_net_operating_margin_eur"]), lead=True,
             delta_html=delta(R["annual_net_operating_margin_eur"], RB["annual_net_operating_margin_eur"], eur),
             sub=f"{pct(R['annual_net_operating_margin_eur'], rev_t)} of revenue, before amortisation"),
        tile(PL.KPI["payback"], "—" if pb is None else f"{pb:.2f} yr",
             sub=f"{eur(EQUITY_TOTAL)} of equity against {eur_s(R['annual_net_operating_margin_eur'])}/yr",
             deriv=(f"equity invested  <b>{eur(EQUITY_TOTAL, 2)}</b>\n÷ operating margin <b>{eur(R['annual_net_operating_margin_eur'], 2)}</b>\n"
                    f"= <b>{'—' if pb is None else f'{pb:.2f} years'}</b>")),
        tile(PL.KPI["npv"], eur_s(R["annual_npv_5yr_eur"]),
             delta_html=delta(R["annual_npv_5yr_eur"], RB["annual_npv_5yr_eur"], eur),
             sub="Five years of operating margin discounted at 8%, less equity",
             deriv=(f"annuity factor (5 yr, 8%) = <b>3.9927</b>\n{eur(R['annual_net_operating_margin_eur'], 2)} × 3.9927\n"
                    f"− equity {eur(EQUITY_TOTAL, 2)}\n= <b>{eur_s(R['annual_npv_5yr_eur'])}</b>"),
             src="No revenue growth, cost inflation or terminal value — a five-year annuity, not a forecast."),
        tile(PL.KPI["breakeven"], "—" if BE is None else f"{BE:.1f}%",
             chip_html=chip(f"set: {SCN['reboat_share']:.1f}%", "good" if BE is not None and SCN["reboat_share"] >= BE else "warn", True),
             sub=("Share of the package price the operator must receive for revenue to cover operating cost"
                  if BE is None or BE >= 0 else "Operating cost is covered even without tourism revenue"),
             deriv=(f"package turnover <b>{eur(R['annual_package_turnover_eur'], 2)}</b>\n"
                    f"other revenue    <b>{eur(R['annual_gross_revenue_eur'] - R['annual_tourism_revenue_eur'], 2)}</b>\n"
                    f"operating cost   <b>{eur(R['annual_total_opex_eur'], 2)}</b>\n"
                    f"──────────────────\nbreak-even share = <b>{'—' if BE is None else f'{BE:.2f}%'}</b>"),
             src="Commission and overheads that depend on tourism revenue are included."),
    ])
    tiles([
        tile(PL.KPI["npv10"], eur_s(R["annual_npv_10yr_eur"]),
             delta_html=delta(R["annual_npv_10yr_eur"], RB["annual_npv_10yr_eur"], eur),
             sub="Ten years of operating margin discounted at 8%, less equity",
             deriv=(f"annuity factor (10 yr, 8%) = <b>6.7101</b>\n{eur(R['annual_net_operating_margin_eur'], 2)} × 6.7101\n"
                    f"− equity {eur(EQUITY_TOTAL, 2)}\n= <b>{eur_s(R['annual_npv_10yr_eur'])}</b>")),
        tile("CapEx baseline", eur(SCN["proxy_capex"]),
             sub=f"{esc(fin_name(SCN['capex_scenario']))} — {eur(GRANT_TOTAL)} grant / {eur(EQUITY_TOTAL)} equity"),
        tile("Package turnover", eur(R["annual_package_turnover_eur"]),
             sub=f"Paid by participants to tour operators ({PRICE_POINTS[SCN['price_point']].lower()} of the WP4 pricing note); "
                 f"the operator keeps {SCN['reboat_share']:.1f}% = {eur(R['annual_tourism_revenue_eur'])}"),
        tile("Active days", nf(R["annual_active_days"]),
             sub=f"{SCN['op_days']}-day campaign length; 14 days = reference calendar of 191 days"),
    ])

    def r(label, amount, share="", basis="", cls="sub"):
        return ([(label, "" if cls == "grp" else "l"), (amount, "n"), (share, "n"), (basis, "wrap" if cls != "grp" else "")], cls)

    rev_vis, opx_vis = PL.visible(PL.REVENUE_LINES, R), PL.visible(PL.OPEX_LINES, R)
    rows = [r("1 · " + PL.REVENUE, eur(R["annual_gross_revenue_eur"]), "100.0%", "12-month consolidated turnover", "grp")]
    rows += [r(lbl, eur(R.get(k, 0)), pct(R.get(k, 0), rev_t), BASIS[k]) for k, lbl in rev_vis]
    rows += [r("2 · " + PL.OPEX, "−" + eur(R["annual_total_opex_eur"]), "100.0%", "Cash operating cost, before amortisation", "grp")]
    rows += [r(lbl, "−" + eur(R.get(k, 0)), pct(R.get(k, 0), opex_t), BASIS[k]) for k, lbl in opx_vis]
    rows += [
        r("3 · " + PL.MARGIN, eur_s(R["annual_net_operating_margin_eur"]),
          f"{x2(R['annual_revenue_to_opex_ratio'])} coverage", f"Margin on revenue {pct(R['annual_net_operating_margin_eur'], rev_t)}", "grp"),
        r("4 · " + PL.AMORT, "−" + eur(R["annual_capex_amortization_eur"]), "",
          f"{eur(SCN['proxy_capex'])} straight-line over 10 years", "grp"),
        r("5 · " + PL.NET, eur_s(R["annual_net_after_capex_eur"]), "",
          "Annual CapEx amortisation covered (net surplus after depreciation)"
          if R["annual_net_after_capex_eur"] >= 0 else "Shortfall after annual CapEx amortisation",
          "total"),
    ]
    with panel("12-month consolidated profit &amp; loss",
               chip(f"{esc(SCN['target_island'])} · {esc(fin_name(SCN['capex_scenario']))}")):
        html_block(ui.table([("Line item", False), ("Full year", True), ("Share", True), ("Basis", False)], rows))

    with panel("Investment and how it is financed", chip(esc(fin_name(SCN["capex_scenario"])))):
        inv = [("CapEx baseline", eur(SCN["proxy_capex"])),
               (f"Public grant ({GRANT_PCT}%)", eur(GRANT_TOTAL)),
               ("Equity invested", eur(EQUITY_TOTAL)),
               ("Amortisation per year (10 years)", eur(R["annual_capex_amortization_eur"])),
               (PL.KPI["payback"], "—" if pb is None else f"{pb:.2f} yr"),
               (PL.KPI["npv"], eur_s(R["annual_npv_5yr_eur"])),
               (PL.KPI["npv10"], eur_s(R["annual_npv_10yr_eur"]))]
        html_block(ui.table([], [([(esc(k), "l"), (v, "n")], "") for k, v in inv]))
        html_block(
            f'<p class="railhint" style="margin-top:8px">CapEx baseline ({eur(SCN["proxy_capex"])}) reflects indicative partner '
            'aggregate plant planning budget estimates. System boundary excludes '
            'municipal permits &amp; port concessions (~€33,000/yr indicative placeholder evaluated in Table 28/29), '
            'corporate taxes, and financing interest.</p>'
        )

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with panel("Revenue mix"):
            ch.plot(ch.ranked_bars([
                (lbl, R.get(k, 0), col, eur(R.get(k, 0))) for (k, lbl), col in zip(rev_vis, (S1, S2, S3, S5, S4))
            ]), key="ch_revenue")
    with c2:
        with panel("Operating cost drivers"):
            opex_rows = [(lbl, R.get(k, 0), col) for (k, lbl), col in zip(opx_vis, (S1, S2, S3, S5, NEUTRAL, S4, S4, S4, S4, S4))]
            ch.plot(ch.ranked_bars([(a, b, c, eur(b)) for a, b, c in opex_rows]), key="ch_opex")
    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)


# ═════════════════════════════════════════════════════════════════════════════
# VIEW · ECOSYSTEM DYNAMICS
# ═════════════════════════════════════════════════════════════════════════════
def view_ecosystem():
    head("ecosystem", "Multi-year systemic & fleet evolution.")
    arch_key = get_archipelago_for_island(SCN["target_island"])
    arch_cluster = ARCHIPELAGO_CLUSTERS[arch_key]

    show_note(
        f"Multi-Year Archipelago &amp; Fleet Projection — {esc(arch_cluster['name'])}",
        "Projects the validated single-year plant economics across a 5–10 year regional horizon, coupling municipal adoption, "
        "tour-operator/DMC participation, local artisan uptake with material traceability, and mobile fleet scaling "
        "(aligned with T2.4 RIALTO pipeline collections and WP7 Clusters C1–C4). "
        f"<strong>Archipelago context:</strong> {esc(arch_cluster['ga_msw_note'])}"
    )

    with panel("Policy, archipelago & fleet controls",
               chip(f"Cluster: {esc(arch_key)}", "neutral", True),
               sub="Interactive regional scope, policy and fleet-ceiling levers coupled to the single-year sidebar scenario"):
        _es = st.session_state["_eco"]
        _scope_opts = ["archipelago", "single_island"]
        ec1, ec2, ec3 = st.columns(3, gap="medium")
        with ec1:
            _es["eco_scope"] = st.selectbox(
                "Simulation scope", _scope_opts, index=_scope_opts.index(_es["eco_scope"]), key="w_eco_scope",
                format_func=lambda v: "Regional archipelago (multi-island)" if v == "archipelago"
                else f"Single island ({SCN['target_island']} only)")
            _es["eco_horizon"] = st.slider("Horizon (years)", 5, 10, value=int(_es["eco_horizon"]), key="w_eco_horizon")
        with ec2:
            _es["eco_tariff_esc"] = st.slider(
                "Disposal tariff escalation (%/yr)", 0.0, 10.0, value=float(_es["eco_tariff_esc"]), step=0.5,
                key="w_eco_tariff_esc",
                help="Annual escalation in mainland waste shipping / gate-fee avoided disposal costs.")
            _es["eco_epr"] = st.slider(
                "EPR / packaging co-funding (€/t)", 0.0, 200.0, value=float(_es["eco_epr"]), step=10.0,
                key="w_eco_epr",
                help="Extended Producer Responsibility subsidy off-setting municipal gate-fee exposure.")
        with ec3:
            _es["eco_cocreation"] = st.slider(
                "Co-creation & awareness intensity", 0.5, 1.5, value=float(_es["eco_cocreation"]), step=0.1,
                key="w_eco_cocreation",
                help="Intensity of WP2/WP4 local living labs ('The Circus', schools, committees).")
            _es["eco_max_boats"] = st.slider("Fleet ceiling (max boats)", 1, 6, value=int(_es["eco_max_boats"]), key="w_eco_max_boats")

    eco_params = current_eco_params()
    eco = eco_for(SCN, eco_params)
    sm = eco["summary"]
    yr = eco["yearly_series"]
    fr = eco["tradeoff_frontier"]
    horizon = eco_params["horizon_years"]

    html_block(ui.bracket("for ecosystem scale &amp; fleet"))
    tiles([
        tile("Archipelago fleet size",
             f"{sm['initial_boats']} → {sm['final_boats']} boat{'s' if sm['final_boats'] != 1 else ''}",
             lead=True,
             chip_html=chip(f"Optimal: {sm['optimal_boats_needed']} boat{'s' if sm['optimal_boats_needed'] != 1 else ''}",
                            "good" if sm["final_boats"] >= sm["optimal_boats_needed"] else "warn", True),
             sub=(f"2nd boat triggered in Year {sm['second_boat_year']}; "
                  if sm["second_boat_year"] else "Single boat meets archipelago demand; ")
                 + f"expansion years: {', '.join(f'Y{y}' for y in sm['expansion_years']) or 'none'}",
             deriv=(f"Year {horizon} demand   <b>{yr[-1]['requested_days']:.0f} days/yr</b>\n"
                    f"Per-boat cap      <b>300 days/yr</b>\n"
                    f"Initial -> final  <b>{sm['initial_boats']} -> {sm['final_boats']} boats</b>")),
        tile(f"{horizon}-yr waste diverted", f"{nf(sm['total_diverted_t'], 1)} t",
             chip_html=chip(f"Unmet peak: {nf(sm['total_unmet_t'], 1)} t", "good" if sm["total_unmet_t"] < 5 else "warn"),
             sub=f"Across {len(eco['islands_in_scope'])} island(s) ({', '.join(eco['islands_in_scope'])})",
             deriv=(f"Year 1 diverted   <b>{yr[0]['diverted_waste_t']:.1f} t</b>\n"
                    f"Year {horizon} diverted  <b>{yr[-1]['diverted_waste_t']:.1f} t</b>\n"
                    f"Cumulative total  <b>{sm['total_diverted_t']:.1f} t</b>")),
        tile("Fleet operators trained", nf(sm["final_operators"]),
             chip_html=chip("Clusters C1–C2"),
             sub=f"{SCN['workers']} trained island operators × {sm['final_boats']} active vessel(s) in Year {horizon}"),
        tile(f"{horizon}-yr cumulative cash", eur_s(sm["final_cumulative_cash_eur"]),
             chip_html=chip(f"Avg coverage {x2(sm['avg_coverage_ratio'])}",
                            "good" if sm["avg_coverage_ratio"] >= 1.0 else "warn", True),
             sub="Cumulative operating margin less equity outlay for fleet expansion boats"),
    ])

    html_block(ui.bracket("for stakeholder adoption &amp; traceability"))
    tiles([
        tile("Municipal adoption", f"{sm['final_muni_adoption_pct']:.1f}%", lead=True,
             sub=f"{yr[-1]['active_islands']} of {len(eco['islands_in_scope'])} cluster municipalities active by Year {horizon}"),
        tile("Tour operator / DMC uptake", f"{sm['final_dmc_adoption_pct']:.1f}%",
             sub="Share of regional DMCs accepting WP4 co-created packages at current ReBoat share"),
        tile("Local artisan uptake", f"{sm['final_artisan_adoption_pct']:.1f}%",
             chip_html=chip(f"+{sm['dpp_uplift_artisan_pp']:.1f} pp traceability uplift", "good", True),
             sub=f"With Digital Product Passport traceability: {sm['artisan_with_dpp_pct']:.0f}% vs. {sm['artisan_no_dpp_pct']:.0f}% without"),
        tile("Circular awareness &amp; trust", f"{sm['final_awareness_pct']:.1f}%",
             chip_html=chip(f"Material trust {sm['final_trust_pct']:.0f}%"),
             sub=f"Awareness &amp; material provenance trust ({eco_params['cocreation_intensity']:.1f}× co-creation intensity)"),
    ])

    c_left, c_right = st.columns(2, gap="medium")
    with c_left:
        with panel("Stakeholder adoption &amp; awareness trajectories",
                   chip("Regional cohorts")):
            ch.plot(ch.ecosystem_adoption_chart(yr), key="ch_eco_adopt")
    with c_right:
        with panel("Archipelago waste demand vs. mobile fleet capacity",
                   chip(f"{sm['initial_boats']} → {sm['final_boats']} boat{'s' if sm['final_boats'] != 1 else ''}")):
            ch.plot(ch.ecosystem_fleet_chart(yr), key="ch_eco_fleet")
            if eco["expansion_log"]:
                html_block('<p class="railhint" style="margin-top:6px"><strong>Expansion log:</strong> '
                           + " · ".join(esc(x) for x in eco["expansion_log"]) + "</p>")

    with panel("Systemic gate-fee trade-off: operator solvency vs. municipal adoption",
               chip("Counterfactual gate-fee sweep €0–€300/t"),
               sub="High gate fees raise NewCo solvency (R/C) but deter lower-cost municipalities (e.g., Terceira at €50/t incinerator)"):
        ch.plot(ch.ecosystem_tradeoff_chart(fr), key="ch_eco_tradeoff")

    t24 = eco["t24_pipeline_mapping"]
    with panel("Stakeholder participation logic, WP7 clusters &amp; T2.4 pipeline mapping"):
        agent_rows = [
            ("Municipalities (C1, C4)", "Join if avoided disposal cost + EPR + environmental weight ≥ gate fee and awareness exceeds threshold.", t24["waste_inventory"]),
            ("Tour Operators / DMCs (T4.2–4.3)", "Participate when awareness crosses cohort hurdle and ReBoat package share ≤ DMC willingness cap.", t24["mission_params"]),
            ("Local Artisans & SMEs (C3, KARTU)", "Switch to ReBoat rPET/yarn when price discount vs. virgin (€1.90/kg) and DPP provenance trust qualify.", t24["machinery_catalogue"]),
            ("Fleet Operator / NewCo (C1–C2)", "Deploy additional boat when unmet peak waste > 5% and cumulative margin headroom covers expansion equity.", t24["boat_envelope"] + " · " + t24["routes"]),
        ]
        html_block(ui.table(
            [("Stakeholder / WP7 Cluster", False), ("Adoption &amp; Scaling Rule", False), ("T2.4 RIALTO Schema Coupling", False)],
            [([(esc(a), "l"), (esc(b), "wrap"), (esc(c), "wrap")], "") for a, b, c in agent_rows]
        ))

    with panel(f"Year-by-year archipelago trajectory ({horizon} years)", chip("Multi-year projection")):
        y_rows = []
        for r_y in yr:
            y_rows.append(([
                (f"Y{r_y['year']}", "l"),
                (str(r_y["n_boats"]), "n"),
                (str(r_y["trained_operators"]), "n"),
                (str(r_y["active_islands"]), "n"),
                (nf(r_y["demand_waste_t"], 1), "n"),
                (nf(r_y["diverted_waste_t"], 1), "n"),
                (nf(r_y["unmet_waste_t"], 1), "n"),
                (eur(r_y["revenue_eur"]), "n"),
                (eur(r_y["opex_eur"]), "n"),
                (x2(r_y["coverage_ratio"]), "n"),
                (eur_s(r_y["cumulative_cash_eur"]), "n"),
            ], ""))
        html_block(ui.table([
            ("Year", False), ("Boats", True), ("Ops", True), ("Islands", True), ("Demand (t)", True),
            ("Diverted (t)", True), ("Unmet (t)", True), ("Revenue", True), ("OpEx", True),
            ("Coverage", True), ("Cum. cash", True),
        ], y_rows))

    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)


# ═════════════════════════════════════════════════════════════════════════════
# VIEW · DELIVERABLES
# ═════════════════════════════════════════════════════════════════════════════
def _fingerprint(scn: dict) -> str:
    return hashlib.sha1(json.dumps(scn, sort_keys=True).encode()).hexdigest()[:12]


REV_KEYS = [k for k, _ in PL.REVENUE_LINES]
OPX_KEYS = [k for k, _ in PL.OPEX_LINES]
_MLINE = {"annual_tourism_revenue_eur": ("revenue_lines", "tourism"), "annual_finished_goods_revenue_eur": ("revenue_lines", "products"),
          "annual_bulk_flakes_revenue_eur": ("revenue_lines", "flakes"), "annual_bulk_yarn_revenue_eur": ("revenue_lines", "yarn"),
          "annual_gate_fee_revenue_eur": ("revenue_lines", "gate_fee"), "annual_labor_cost_eur": ("opex_lines", "crew"),
          "annual_berth_cost_eur": ("opex_lines", "berth"), "annual_maintenance_cost_eur": ("opex_lines", "maintenance"),
          "annual_power_cost_eur": ("opex_lines", "power"), "annual_fuel_cost_eur": ("opex_lines", "fuel"),
          "annual_vessel_cost_eur": ("opex_lines", "vessel"), "annual_insurance_cost_eur": ("opex_lines", "insurance"),
          "annual_land_collection_cost_eur": ("opex_lines", "collection"), "annual_commission_cost_eur": ("opex_lines", "commission"),
          "annual_overheads_cost_eur": ("opex_lines", "overheads")}


def annual_detail(scn: dict) -> dict:
    """Monthly lines and units of the year, as returned by the engine; cross-checked against its annual totals."""
    rep_, A = model_for(scn)
    rev_vis, opx_vis = PL.visible(PL.REVENUE_LINES, A), PL.visible(PL.OPEX_LINES, A)
    rows = []
    for m in A["monthly_timeseries"]:
        rl = [m[_MLINE[k][0]][_MLINE[k][1]] for k, _ in rev_vis]
        ol = [m[_MLINE[k][0]][_MLINE[k][1]] for k, _ in opx_vis]
        rows.append(dict(label=PL.month_label(m), season=m["season"],
                         season_mult=SEASON_MULTIPLIER.get(m["season"], 1.0),
                         days=m["days_active"], rev_lines=rl, opex_lines=ol,
                         tourism_rev=m["revenue_lines"]["tourism"],
                         revenue=m["revenue_eur"], opex=m["opex_eur"], amort=m["monthly_amortization_eur"],
                         waste_t=m["waste_diverted_tonnes"]))
    ok = all(abs(sum(r_["rev_lines"]) - r_["revenue"]) < 0.06 and abs(sum(r_["opex_lines"]) - r_["opex"]) < 0.06 for r_ in rows)
    ok &= all(abs(sum(m[_MLINE[k][0]][_MLINE[k][1]] for m in A["monthly_timeseries"]) - A[k]) < 0.06 for k in REV_KEYS + OPX_KEYS)
    turnover_by_pkg = {k: sum(m["package_units"].get(k, 0) * m["package_prices_eur"].get(k, 0) for m in A["monthly_timeseries"])
                       for k in A["annual_package_units"]}
    return dict(months=rows, months_verified=ok, units_verified=ok, package_units=A["annual_package_units"],
                product_units=A["annual_product_units"], turnover_by_pkg=turnover_by_pkg, rev_vis=rev_vis, opx_vis=opx_vis,
                brain=make_brain(scn))


def _kg(revenue, price, tonnes):
    """Bulk kilograms behind an engine revenue line (exact), falling back to the rounded flow."""
    return revenue / price if price else tonnes * 1000


def model_payload(fp: str, eco: dict | None = None) -> dict:
    """Everything the Excel model prints — the same engine run as the views and the Word summary."""
    det = annual_detail(SCN)
    b = det["brain"]
    F_ = R["material_flows"]
    sp = summary_payload(fp, eco=eco)
    pk_rows = []
    for (k, lbl), k2 in zip(PL.PACKAGES, ("pkg_day", "pkg_short", "pkg_slow", "pkg_med", "pkg_deep")):
        units = det["package_units"].get(k, 0)
        turn = det["turnover_by_pkg"].get(k, 0.0)
        pk_rows.append((lbl, SCN[k2], units, (turn / units) if units else 0.0))
    return dict(
        meta=dict(island=SCN["target_island"], port=profile.get("berth_port", "—"), financing_name=fin_name(SCN["capex_scenario"]),
                  date=datetime.now().strftime("%d %B %Y").lstrip("0"), fingerprint=fp, ui_release=UI_RELEASE,
                  tool_version=TOOL_VERSION, scenario_note=PL.SCENARIO_NOTE),
        scenario=dict(days=SCN["op_days"], active_days=R["annual_active_days"], transit_hrs=SCN["transit_hrs"],
                      plastic_kg=SCN["plastic_kg"], textile_kg=SCN["textile_kg"], workers=SCN["workers"], capex=SCN["proxy_capex"],
                      price_point=PRICE_POINTS[SCN["price_point"]], share=SCN["reboat_share"], prod_share=SCN["prod_share"],
                      gate_fee=SCN["gate_fee"]),
        rates=[("Operator crew", SCN["proxy_labor"], "€ / active day", "Crew cost, scaled by the season multiplier"),
               ("Berth and port fees", SCN["proxy_berth"], "€ / active day", "Berth and shore connection, scaled by the season multiplier"),
               ("Maintenance and consumables", SCN["proxy_maintenance"], "€ / active day", "Wear parts, filters, lubricants"),
               ("Shore power", SCN["proxy_shore"], "€ / kWh", "Electricity drawn at the berth (52 kW × 8 h per active day)"),
               ("Marine diesel", SCN["proxy_diesel"], "€ / litre", "Transit fuel, 45 L per hour"),
               ("Recycled plastic flakes", SCN["proxy_rpet"], "€ / kg", "Bulk sale price"),
               ("Recycled yarn", SCN["proxy_yarn"], "€ / kg", "Bulk sale price"),
               ("Avoided disposal cost", SCN["proxy_export"], "€ / tonne", "Ferry freight or incinerator cost the island avoids"),
               ("Gate fee", SCN["gate_fee"], "€ / tonne", "Paid by the municipality to the operator (GA reference €1,600/t)"),
               ("ReBoat share of package price", SCN["reboat_share"], "%", "Share of the tour-operator package price kept by the operator"),
               ("Operator share of product sales", SCN["prod_share"], "%", "Rest kept by the municipality or partners"),
               ("Vessel charter", SCN["vessel"], "€ / active day", "Not quoted yet (0 = excluded)"),
               ("Insurance", SCN["insurance"], "€ / year", "Not quoted yet (0 = excluded)"),
               ("Collection on land", SCN["collection"], "€ / tonne", "Not quoted yet (0 = excluded)"),
               ("Sales commissions", SCN["commission"], "% of tourism revenue", "0 = excluded"),
               ("Overheads", SCN["overheads"], "% of other costs", "0 = excluded")],
        constants=[("Textile line rate", b.textile_line_rate_kg_hr(), "kg / h", "textile spinning line limit"),
                   ("Electrical load", 52.0, "kW", "Plant engineering baseline Scenario B"),
                   ("CO₂ avoided", 0.12, "t CO₂ / t waste", "Gross waste-transport screening factor, pre-Task 5.7 LCA"),
                   ("Carbon price", 80.0, "€ / t CO₂", "Value of gross CO₂ avoided"),
                   ("Landfill density", 0.35, "t / m³", "Landfill space saved"),
                   ("Amortisation period", 10.0, "years", "CapEx and grant spread"),
                   ("Discount rate", 0.08, "per year", "5- and 10-year NPV")],
        packages=pk_rows, package_turnover=R["annual_package_turnover_eur"],
        products=[(lbl, SCN[k2], det["product_units"].get(k, 0), b.CIRCULAR_PRODUCTS_CATALOG[k]["unit_price_eur"])
                  for (k, lbl), k2 in zip(PL.PRODUCTS, ("prod_molded", "prod_3d", "prod_panel", "prod_textile", "prod_yarn"))],
        materials=[("flakes", "Recycled plastic flakes", _kg(R["annual_bulk_flakes_revenue_eur"], SCN["proxy_rpet"], F_["flakes_sold_bulk_t"]),
                    SCN["proxy_rpet"], "Recovered plastic not used for products"),
                   ("yarn", "Recycled yarn", _kg(R["annual_bulk_yarn_revenue_eur"], SCN["proxy_yarn"], F_["yarn_sold_bulk_t"]),
                    SCN["proxy_yarn"], "Recycled yarn not used for products")],
        flows=F_,
        units_verified=det["units_verified"], months_verified=det["months_verified"], months=det["months"],
        rev_vis=det["rev_vis"], opx_vis=det["opx_vis"],
        annual={**{k: R.get(k, 0) for k, _ in PL.REVENUE_LINES + PL.OPEX_LINES},
                "annual_capex_amortization_eur": R["annual_capex_amortization_eur"],
                "annual_tourism_revenue_eur": R["annual_tourism_revenue_eur"], "annual_finished_goods_revenue_eur": R["annual_finished_goods_revenue_eur"],
                "annual_product_sales_total_eur": R["annual_product_sales_total_eur"],
                "grant": GRANT_TOTAL, "grant_pct": GRANT_PCT},
        basis=BASIS,
        capex_items=[], capex_itemised=0, capex_gap=0,
        routes=[{**r_, "npv": r_["npv10"]} for r_ in sp["routes"]],
        sustain=dict(waste_t=(R["annual_avoided_disposal_cost_eur"] / SCN["proxy_export"] if SCN["proxy_export"]
                              else R["annual_waste_diverted_tonnes"]), co2_t=R["annual_carbon_avoided_tonnes"],
                     co2_value=R["annual_carbon_value_eur"], avoided=R["annual_avoided_disposal_cost_eur"],
                     gate_paid=R["annual_gate_fee_paid_eur"], freight=R["annual_municipal_savings_eur"],
                     export_rate=SCN["proxy_export"], workers=SCN["workers"], wages=WAGES, kept_by_others=KEPT_BY_OTHERS,
                     transit_diesel_co2_t=R["annual_transit_diesel_co2_tonnes"],
                     diesel_litres=R["annual_diesel_litres"],
                     shore_power_kwh=R["annual_shore_power_kwh"]),
        ecosystem=eco,
    )


def summary_payload(fp: str, eco: dict | None = None) -> dict:
    """Everything the two-page Word and PDF summaries print — the same figures the views show."""
    rev_lines = [(lbl, R.get(k, 0)) for k, lbl in PL.visible(PL.REVENUE_LINES, R)]
    opex_lines = [(lbl, R.get(k, 0)) for k, lbl in PL.visible(PL.OPEX_LINES, R)]
    routes = []
    for key in ("EU_Grants", "Public_Private_Partnership", "Private_Investment"):
        rep_k, r_k = model_for({**SCN, "capex_scenario": key})
        ca = rep_k["CapEx_Allocation"]
        routes.append(dict(name=_cap[key]["name"], pct=ca["coverage_percent"], grant=ca["grant_coverage_eur"],
                           equity=ca["net_equity_required_eur"], payback=r_k["annual_payback_years"],
                           npv10=r_k["annual_npv_10yr_eur"],
                           sroi=r_k["annual_sroi_ratio"], sroi_noturn=r_k["annual_sroi_without_turnover"],
                           selected=key == SCN["capex_scenario"]))
    return dict(
        island=SCN["target_island"], port=profile.get("berth_port", "—"), financing_name=fin_name(SCN["capex_scenario"]),
        date=datetime.now().strftime("%d %B %Y").lstrip("0"), fingerprint=fp,
        capex=SCN["proxy_capex"], equity=EQUITY_TOTAL, scenario_note=PL.SCENARIO_NOTE,
        kpi=dict(ratio=R["annual_revenue_to_opex_ratio"], net=R["annual_net_after_capex_eur"],
                 revenue=R["annual_gross_revenue_eur"], opex=R["annual_total_opex_eur"],
                 margin=R["annual_net_operating_margin_eur"], amortisation=R["annual_capex_amortization_eur"],
                 payback=R["annual_payback_years"], npv5=R["annual_npv_5yr_eur"], npv10=R["annual_npv_10yr_eur"],
                 waste_t=R["annual_waste_diverted_tonnes"], airspace_m3=R["annual_waste_diverted_tonnes"] / 0.35,
                 co2_t=R["annual_carbon_avoided_tonnes"], co2_value=R["annual_carbon_value_eur"],
                 transit_diesel_co2_t=R["annual_transit_diesel_co2_tonnes"],
                 diesel_litres=R["annual_diesel_litres"],
                 shore_power_kwh=R["annual_shore_power_kwh"],
                 freight=R["annual_municipal_savings_eur"], avoided=R["annual_avoided_disposal_cost_eur"],
                 gate_paid=R["annual_gate_fee_paid_eur"], sroi=R["annual_sroi_ratio"],
                 sroi_noturn=R["annual_sroi_without_turnover"], breakeven=R["breakeven_reboat_share_pct"],
                 turnover=R["annual_package_turnover_eur"],
                 workers=SCN["workers"], wages=WAGES, societal=SOCIETAL, grant_annual=GRANT_ANNUAL),
        revenue_lines=rev_lines, opex_lines=opex_lines, routes=routes,
        months=[(PL.month_label(m), m["revenue_eur"], m["opex_eur"], m["rev_opex_ratio"], m["month_name"])
                for m in R["monthly_timeseries"]],
        assumptions=dict(days=SCN["op_days"], active_days=R["annual_active_days"], workers=SCN["workers"],
                         price_point=PRICE_POINTS[SCN["price_point"]].lower(), share=SCN["reboat_share"],
                         gate_fee=SCN["gate_fee"], textile_rate=make_brain(SCN).textile_line_rate_kg_hr()),
        ecosystem=eco,
    )


def view_deliverables():
    head("deliverables", "What leaves the tool.")
    fp = _fingerprint(SCN)
    stamp = datetime.now().strftime("%Y%m%d")
    island = SCN["target_island"]
    eco = eco_for(SCN, current_eco_params())

    show_note("What leaves this tool",
              "Four files, each carrying the scenario on screen and the same figures: a two-page business plan and "
              "sustainability summary as PDF (for sharing) and Word (for editing), the full formula-linked financial &amp; "
              "ecosystem model in Excel, and the underlying JSON dataset (including 10-year View 05 outputs) for review.")

    def export_card(col, kind, title, ext, body, builder, mime, blocked_reason=None):
        with col:
            with st.container(border=True, key=f"panel_export_{kind}"):
                html_block(f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
                           f'<span class="eyebrow">{ext}</span>{chip(kind.upper())}</div>'
                           f'<h3 style="margin:6px 0 4px">{title}</h3>'
                           f'<p style="font-size:12.5px;color:var(--text-2);min-height:62px">{body}</p>')
                slot = f"_export_{kind}"
                cached = st.session_state.get(slot)
                if blocked_reason:
                    st.button(f"Generate {ext}", key=f"gen_{kind}", disabled=True, width="stretch")
                    st.caption(blocked_reason)
                    return
                if st.button(f"Generate {ext}", key=f"gen_{kind}", type="primary", width="stretch"):
                    with st.spinner(f"Building {ext}…"):
                        try:
                            st.session_state[slot] = (fp, builder())
                        except Exception as e:  # surface the exporter's own error rather than crash the page
                            st.session_state.pop(slot, None)
                            st.error(f"The {ext} exporter raised {type(e).__name__}: {e}")
                    cached = st.session_state.get(slot)
                if cached and cached[0] == fp:
                    st.download_button(f"Download {ext}", data=cached[1],
                                       file_name=f"ReBoat_{'Financial_Model' if kind == 'xlsx' else 'Business_Plan_Summary'}_{island}_{stamp}.{kind}",
                                       mime=mime, key=f"dl_{kind}", width="stretch")
                elif cached:
                    st.caption("The scenario changed since this file was built — generate it again.")

    c0, c1 = st.columns(2, gap="medium")
    export_card(c0, "pdf", "Business plan summary", "PDF",
                "Two pages for decision makers, ready to share: the verdict, headline figures, 12-month P&amp;L, "
                "the year month by month, financing routes, SROI (with &amp; excl. turnover) and ecosystem sizing.",
                lambda: pdf_summary_export.generate_business_summary_pdf(summary_payload(fp, eco=eco)), "application/pdf")
    export_card(c1, "docx", "Business plan summary", "Word",
                "The same two pages as an editable Word file, for partners who want to reuse the text and tables.",
                lambda: business_summary_export.generate_business_summary_docx(summary_payload(fp, eco=eco)),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    c2, c3 = st.columns(2, gap="medium")
    export_card(c2, "xlsx", "Financial &amp; sustainability model", "Excel",
                "Eight formula-linked sheets rebuilding every figure on screen: summary, inputs, revenue build-up, P&amp;L, "
                "monthly table, investment &amp; financing, environmental &amp; SROI values, and Ecosystem dynamics.",
                lambda: financial_model_export.generate_financial_model_xlsx(model_payload(fp, eco=eco)),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                blocked_reason=None)
    with c3:
        with st.container(border=True, key="panel_export_json"):
            html_block(f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px">'
                       f'<span class="eyebrow">JSON</span>{chip("DATA")}</div>'
                       f'<h3 style="margin:6px 0 4px">Scenario dataset</h3>'
                       f'<p style="font-size:12.5px;color:var(--text-2);min-height:62px">All results of this scenario '
                       f'(including View 05 multi-year archipelago trajectory) in one machine-readable file for reviewers.</p>')
            payload = {**report, "annual_business_plan": R, "ecosystem_dynamics": eco,
                       "export_timestamp": datetime.now().isoformat(),
                       "tool_version": TOOL_VERSION, "ui_release": UI_RELEASE, "scenario_fingerprint": fp}
            st.download_button("Download JSON", data=json.dumps(payload, indent=2, default=str),
                               file_name=f"ReBoat_Scenario_Data_{island}_{stamp}.json", mime="application/json",
                               key="dl_json", width="stretch")

    with panel("Scenario stamped into these files", chip("Built on demand", "good", True)):
        rows = [
            ("Pilot island", f"{island} — {profile.get('berth_port', '')}"),
            ("Financing route", fin_name(SCN["capex_scenario"])),
            ("Campaign length / active days / transit", f"{SCN['op_days']} days · {nf(R['annual_active_days'])} days a year · {SCN['transit_hrs']:.1f} h"),
            ("Waste per 14 active days (plastic / textile)", f"{nf(SCN['plastic_kg'])} kg · {nf(SCN['textile_kg'])} kg"),
            ("Package prices / ReBoat share", f"{PRICE_POINTS[SCN['price_point']]} · {SCN['reboat_share']:.1f}%"),
            ("Gate fee", f"€{nf(SCN['gate_fee'])} per tonne"),
            ("Island operators", nf(SCN["workers"])),
            (f"{PL.REVENUE} / {PL.OPEX.lower()}", f"{eur(R['annual_gross_revenue_eur'])} · {eur(R['annual_total_opex_eur'])}"),
            (f"{PL.KPI['ratio']} · SROI (excl. turn.)",
             f"{x2(R['annual_revenue_to_opex_ratio'])} · {x2(R['annual_sroi_ratio'])} ({x2(R['annual_sroi_without_turnover'])})"),
            ("Scenario code", fp),
        ]
        html_block(ui.table([], [([(esc(k), "l"), (v if "chip" in str(v) else esc(v), "n wrap")], "") for k, v in rows]))
    ui.eu_footer(EU_LOGO_HTML, PL.EU_DISCLAIMER)


# ═════════════════════════════════════════════════════════════════════════════
# Navigation — each view has its own URL.
# ═════════════════════════════════════════════════════════════════════════════
pages = [
    st.Page(view_overview, title="Overview", icon=":material/speed:", url_path="overview", default=True),
    st.Page(view_impact, title="Impact", icon=":material/public:", url_path="impact"),
    st.Page(view_business_plan, title="Business plan", icon=":material/finance:", url_path="business-plan"),
    st.Page(view_deliverables, title="Deliverables", icon=":material/download:", url_path="deliverables"),
    st.Page(view_ecosystem, title="Ecosystem dynamics", icon=":material/hub:", url_path="ecosystem"),
]
_pg = st.navigation(pages, position="top")
_page_map = {
    "overview": pages[0],
    "impact": pages[1],
    "business-plan": pages[2],
    "deliverables": pages[3],
    "ecosystem": pages[4],
}
_goto = st.session_state.pop("_goto_url", None)
if _goto in _page_map and _page_map[_goto] is not _pg:
    st.switch_page(_page_map[_goto])
_pg.run()
