"""
ReBoat Task 2.6 — Multi-Year Archipelago Ecosystem & Fleet Simulation (D2.3 v1.0 / Engine 4.0.0)
Lead: Politecnico di Milano (POLIMI) · Horizon Europe GA 101182350

Wraps ReBoatDigitalBrain (backend.py) as the single-period techno-economic and mass-balance kernel
inside a multi-year (5–10 year) dynamic loop across WP7 Solution Clusters (C1–C4), projecting:
  • Macro state evolution: Circular Awareness, Disposal Tariff Escalation, Secondary Material
    Provenance Trust, Active Fleet Size (N boats), and Cumulative Operating Cash.
  • Stakeholder adoption & scaling logic: Island Municipalities, Tour Operators / DMCs,
    Local Artisans / SMEs, and the Fleet Operator (NewCo).
"""

from __future__ import annotations

import math
import random
from typing import Any

from backend import ReBoatDigitalBrain, PRICING_NOTE
from stakeholder_data import ARCHIPELAGO_CLUSTERS, get_archipelago_for_island

DEFAULT_ECO_PARAMS: dict[str, Any] = {
    "horizon_years": 10,
    "scope": "archipelago",          # "archipelago" or "single_island"
    "tariff_escalation_pct": 4.0,    # %/yr growth in island waste disposal costs
    "epr_subsidy_eur_per_t": 0.0,    # €/t municipal EPR / packaging co-funding
    "dpp_enabled": True,             # Digital Product Passport & quality traceability
    "cocreation_intensity": 1.0,     # 0.5–1.5 multiplier for community co-creation engagement
    "auto_expand_fleet": True,       # Step up fleet size N -> N+1 when unmet demand & cash allow
    "max_boats": 4,
    "seed": 42,
}


def _pricing_key(island_name: str, arch_key: str) -> str:
    if island_name in PRICING_NOTE:
        return island_name
    return {"Ionian": "Corfu", "Aeolian": "Lipari", "Azores": "Terceira"}.get(arch_key, "Corfu")


def _build_agents(islands: list[dict], seed: int) -> dict[str, Any]:
    """Instantiate deterministic, heterogeneous regional stakeholder cohorts."""
    rng = random.Random(seed)

    # 1. Municipality Agents (one per island in cluster / single island)
    muni_agents = []
    sat_idx = 0
    for isl in islands:
        is_anchor = bool(isl.get("is_anchor", False))
        if is_anchor:
            min_aw = 0.0
        else:
            min_aw = min(0.70, 0.24 + 0.11 * sat_idx)
            sat_idx += 1
        muni_agents.append({
            "island": isl["island"],
            "is_anchor": is_anchor,
            "min_awareness": round(min_aw, 3),
            "env_weight": round(1.6 + 1.4 * rng.random(), 2),       # values circularity + CO2 benefit
            "backlog_tolerance": round(0.28 + 0.18 * rng.random(), 2),
        })

    # 2. Tour Operator / DMC Agents (10 heterogeneous regional operators)
    dmc_agents = []
    for k in range(10):
        dmc_agents.append({
            "id": f"DMC_{k + 1:02d}",
            "min_awareness": round(0.14 + 0.052 * k, 3),
            "max_share_pct": round(max(5.0, 7.0 + 1.85 * k + rng.uniform(-0.6, 0.6)), 2),
        })

    # 3. Local Artisan / Circular SME Agents (12 heterogeneous buyers)
    artisan_agents = []
    for j in range(12):
        artisan_agents.append({
            "id": f"ART_{j + 1:02d}",
            "discount_req": round(0.10 + 0.016 * j, 3),    # 10% to 27.6% discount vs. virgin €1.90/kg
            "min_trust": round(0.36 + 0.036 * j, 3),       # 0.36 to 0.756 quality/DPP trust threshold
        })

    return {"municipalities": muni_agents, "dmcs": dmc_agents, "artisans": artisan_agents}


def _simulate_core(base_scn: dict, params: dict) -> dict:
    horizon = int(params["horizon_years"])
    scope = params["scope"]
    arch_key = get_archipelago_for_island(base_scn["target_island"])
    cluster = ARCHIPELAGO_CLUSTERS[arch_key]
    raw_islands = [dict(x) for x in cluster["islands"]]

    # Override anchor island with current user scenario values so sidebar edits propagate directly
    anchor_name = base_scn["target_island"]
    found_anchor = False
    for isl in raw_islands:
        if isl["island"] == anchor_name:
            isl["is_anchor"] = True
            isl["plastic_base"] = float(base_scn["plastic_kg"])
            isl["disposal_cost"] = float(base_scn["proxy_export"])
            isl["berth_fee"] = float(base_scn["proxy_berth"])
            isl["transit_hrs"] = float(base_scn["transit_hrs"])
            found_anchor = True
        else:
            isl["is_anchor"] = False
    if not found_anchor:
        raw_islands[0]["is_anchor"] = True

    if scope == "single_island":
        islands = [x for x in raw_islands if x["is_anchor"]] or [raw_islands[0]]
    else:
        # Order anchor first, then satellites
        islands = sorted(raw_islands, key=lambda x: (0 if x["is_anchor"] else 1))

    agents = _build_agents(islands, int(params["seed"]))

    # CapEx & financing parameters for fleet expansion loop
    brain_ref = ReBoatDigitalBrain(target_island=anchor_name, season="High")
    brain_ref.capex_baseline_eur = float(base_scn["proxy_capex"])
    capex_alloc = brain_ref.calculate_capex_allocation(base_scn["capex_scenario"])
    equity_per_boat = float(capex_alloc["net_equity_required_eur"])
    amort_per_boat = float(capex_alloc["annual_amortization_eur"])

    # Initial awareness, trust and fleet state
    awareness = 0.28
    secondary_trust = 0.48
    n_boats = 1
    cumulative_cash = -equity_per_boat
    prev_unmet_ratio = 0.0
    expansion_years: list[int] = []
    expansion_log: list[str] = []

    monthly_seasons = [
        0.5, 0.5, 0.6, 0.85, 1.0, 1.15, 1.4, 1.5, 1.25, 0.85, 0.5, 0.5
    ]

    base_op_days = int(base_scn["op_days"])
    # Practical maximum active operating days per boat per year (coastal deployment cap)
    boat_days_cap = max(191, int(round(191 * (base_op_days / 14.0))))

    yearly_series: list[dict[str, Any]] = []
    tot_diverted = 0.0
    tot_unmet = 0.0

    for year in range(1, horizon + 1):
        # Compute year-start stakeholder participation from current awareness and net utility
        active_munis: list[dict] = []
        for isl, m_ag in zip(islands, agents["municipalities"]):
            disp_y = isl["disposal_cost"] * ((1.0 + float(params["tariff_escalation_pct"]) / 100.0) ** (year - 1))
            env_premium = m_ag["env_weight"] * 15.0  # €24–€45/t circularity & eco-tourism co-benefit
            backlog_pen = max(0.0, prev_unmet_ratio - m_ag["backlog_tolerance"]) * 120.0
            net_util_per_t = disp_y + float(params["epr_subsidy_eur_per_t"]) + env_premium - float(base_scn["gate_fee"]) - backlog_pen
            joins = (awareness >= m_ag["min_awareness"]) and (net_util_per_t >= 0.0)
            if joins:
                active_munis.append({**isl, "disposal_y": disp_y, "net_util_per_t": net_util_per_t})

        muni_adoption_pct = round(len(active_munis) / len(islands) * 100.0, 1)

        # DMC / Tour Operator agent decisions
        active_dmcs = sum(
            1 for d in agents["dmcs"]
            if awareness >= d["min_awareness"] and float(base_scn["reboat_share"]) <= d["max_share_pct"]
        )
        dmc_adoption_pct = round(active_dmcs / len(agents["dmcs"]) * 100.0, 1)

        # Artisan / SME agent decisions (DPP quality traceability & -20% virgin price discount rule)
        virgin_polymer_eur_kg = 1.90
        eff_flake_price = float(base_scn["proxy_rpet"]) * (0.92 if params["dpp_enabled"] else 1.00)
        active_artisans = sum(
            1 for a in agents["artisans"]
            if eff_flake_price <= (1.0 - a["discount_req"]) * virgin_polymer_eur_kg
            and secondary_trust >= a["min_trust"]
        )
        artisan_adoption_pct = round(active_artisans / len(agents["artisans"]) * 100.0, 1)

        # Multi-year uptake multipliers coupled into ReBoatDigitalBrain
        waste_awareness_mult = 0.85 + 0.35 * awareness
        tourism_mult = (0.65 + 0.60 * (dmc_adoption_pct / 100.0)) * (0.88 + 0.22 * awareness)
        product_mult = 0.70 + 0.55 * (artisan_adoption_pct / 100.0)
        flake_price_realised = float(base_scn["proxy_rpet"]) * (1.06 if params["dpp_enabled"] else 0.96)

        # Evaluate requested annual operations across active islands in the cluster
        requested_days = 0.0
        demand_waste_t = 0.0
        pot_rev = 0.0
        pot_opex = 0.0
        pot_avoided = 0.0
        pot_gate = 0.0
        pot_wages = 0.0

        textile_ratio = (float(base_scn["textile_kg"]) / float(base_scn["plastic_kg"])) if base_scn["plastic_kg"] > 0 else 0.30

        for isl in active_munis:
            # In archipelago mode, each participating island schedules a subset of annual boat-months
            # (anchor ~65% share of a single-boat calendar, satellites ~45% each)
            isl_weight = 1.0 if scope == "single_island" else (0.65 if isl["is_anchor"] else 0.45)

            b = ReBoatDigitalBrain(target_island=_pricing_key(isl["island"], arch_key), season="High")
            b.proxies["marine_diesel_eur_per_liter"] = float(base_scn["proxy_diesel"])
            b.proxies["daily_berth_and_shore_power_eur"] = float(isl["berth_fee"])
            b.proxies["municipal_waste_export_cost_per_tonne"] = float(isl["disposal_y"])
            b.proxies["shore_power_electricity_eur_per_kwh"] = float(base_scn["proxy_shore"])
            b.proxies["rPET_flake_market_value_eur_per_kg"] = flake_price_realised
            b.proxies["recycled_yarn_market_value_eur_per_kg"] = float(base_scn["proxy_yarn"])
            b.proxies["labor_cost_eur_per_day"] = float(base_scn["proxy_labor"])
            b.proxies["maintenance_eur_per_day"] = float(base_scn["proxy_maintenance"])
            b.capex_baseline_eur = float(base_scn["proxy_capex"])

            # Stationed island uses inter-island transit once active in archipelago (except Year 1 anchor mobilization)
            tr_hrs = float(isl["transit_hrs"])
            if scope == "archipelago" and isl["island"] == "Terceira" and year > 1:
                tr_hrs = 6.0

            pl_kg = float(isl["plastic_base"]) * waste_awareness_mult
            cfg = {
                "operational_days": base_op_days,
                "campaign_days": base_op_days,
                "transit_hours": tr_hrs,
                "plastic_processed_kg": pl_kg,
                "textile_processed_kg": pl_kg * textile_ratio,
                "local_workers_trained": int(base_scn["workers"]),
                "land_event_mode": False,
                "capex_scenario": base_scn["capex_scenario"],
                "price_point": base_scn["price_point"],
                "reboat_share_pct": float(base_scn["reboat_share"]),
                "gate_fee_eur_per_t": float(base_scn["gate_fee"]),
                "product_operator_share_pct": float(base_scn["prod_share"]),
                "sales_commission_pct": float(base_scn["commission"]),
                "vessel_charter_eur_per_day": float(base_scn["vessel"]),
                "insurance_eur_per_year": float(base_scn["insurance"]),
                "land_collection_eur_per_t": float(base_scn["collection"]),
                "overheads_pct": float(base_scn["overheads"]),
                "package_sales": {
                    "Day_Trip": int(round(base_scn["pkg_day"] * tourism_mult)),
                    "Short_Trip": int(round(base_scn["pkg_short"] * tourism_mult)),
                    "Slow_Trip": int(round(base_scn["pkg_slow"] * tourism_mult)),
                    "Medium_Slow": int(round(base_scn["pkg_med"] * tourism_mult)),
                    "Deep_Slow": max(1, int(round(base_scn["pkg_deep"] * tourism_mult))) if base_scn["pkg_deep"] > 0 else 0,
                },
                "circular_products_sales": {
                    "injection_molded_goods": int(round(base_scn["prod_molded"] * product_mult)),
                    "custom_3d_printed_artifacts": int(round(base_scn["prod_3d"] * product_mult)),
                    "thermo_pressed_furniture_panel": int(round(base_scn["prod_panel"] * product_mult)),
                    "artisanal_woven_textiles": int(round(base_scn["prod_textile"] * product_mult)),
                    "plied_yarn_spools": int(round(base_scn["prod_yarn"] * product_mult)),
                },
            }
            res = b.calculate_annual_business_plan(cfg)
            requested_days += res["annual_active_days"] * isl_weight
            demand_waste_t += res["annual_waste_diverted_tonnes"] * isl_weight
            pot_rev += res["annual_gross_revenue_eur"] * isl_weight
            pot_opex += res["annual_total_opex_eur"] * isl_weight
            pot_avoided += res["annual_avoided_disposal_cost_eur"] * isl_weight
            pot_gate += res["annual_gate_fee_paid_eur"] * isl_weight
            pot_wages += res["annual_wages_eur"] * isl_weight

        # Apply fleet capacity constraint across n_boats
        fleet_days_cap = n_boats * boat_days_cap
        served_ratio = min(1.0, fleet_days_cap / requested_days) if requested_days > 0 else 0.0
        fleet_utilization_pct = min(100.0, (requested_days / fleet_days_cap) * 100.0) if fleet_days_cap > 0 else 0.0

        diverted_t = demand_waste_t * served_ratio
        unmet_t = max(0.0, demand_waste_t - diverted_t)
        unmet_ratio = (unmet_t / demand_waste_t) if demand_waste_t > 0 else 0.0
        prev_unmet_ratio = unmet_ratio

        # Physical capacity equivalent of n_boats (100 kg/h plastic + 0.5 kg/h textile over boat_days_cap * 8h)
        per_boat_cap_t = (100.5 * 8.0 * boat_days_cap) / 1000.0
        fleet_capacity_t = n_boats * per_boat_cap_t

        rev_y = pot_rev * served_ratio
        opex_y = pot_opex * served_ratio
        margin_y = rev_y - opex_y
        coverage_y = (rev_y / opex_y) if opex_y > 0 else 0.0
        muni_savings_y = (pot_avoided - pot_gate) * served_ratio
        wages_y = pot_wages * served_ratio
        amort_y = n_boats * amort_per_boat
        net_after_amort_y = margin_y - amort_y

        cumulative_cash += margin_y
        tot_diverted += diverted_t
        tot_unmet += unmet_t

        boats_start = n_boats
        trained_ops = int(base_scn["workers"]) * n_boats

        # Record end-of-year metrics BEFORE expansion takes effect for Year y+1
        yearly_series.append({
            "year": year,
            "n_boats": boats_start,
            "trained_operators": trained_ops,
            "active_islands": len(active_munis),
            "awareness_pct": round(awareness * 100.0, 1),
            "secondary_trust_pct": round(secondary_trust * 100.0, 1),
            "muni_adoption_pct": muni_adoption_pct,
            "dmc_adoption_pct": dmc_adoption_pct,
            "artisan_adoption_pct": artisan_adoption_pct,
            "requested_days": round(requested_days, 1),
            "fleet_days_cap": fleet_days_cap,
            "fleet_utilization_pct": round(fleet_utilization_pct, 1),
            "demand_waste_t": round(demand_waste_t, 2),
            "diverted_waste_t": round(diverted_t, 2),
            "unmet_waste_t": round(unmet_t, 2),
            "fleet_capacity_t": round(fleet_capacity_t, 1),
            "revenue_eur": round(rev_y, 2),
            "opex_eur": round(opex_y, 2),
            "operating_margin_eur": round(margin_y, 2),
            "net_after_amort_eur": round(net_after_amort_y, 2),
            "coverage_ratio": round(coverage_y, 2),
            "municipal_savings_eur": round(muni_savings_y, 2),
            "wages_eur": round(wages_y, 2),
            "cumulative_cash_eur": round(cumulative_cash, 2),
        })

        # Multi-year awareness and trust evolution into Year y+1
        act_share = max(0.2, len(active_munis) / len(islands))
        for m_mult in monthly_seasons:
            inflow = (0.048 * float(params["cocreation_intensity"]) * act_share * (0.65 + 0.35 * m_mult)
                      * awareness * (1.0 - awareness / 0.95)
                      + 0.012 * float(params["cocreation_intensity"]) * (1.0 - awareness / 0.95))
            outflow = 0.013 * awareness
            awareness = min(0.95, max(0.15, awareness + inflow - outflow))

        target_trust = 0.92 if params["dpp_enabled"] else 0.54
        secondary_trust = secondary_trust + (target_trust - secondary_trust) / 2.2

        # Fleet Sizing & Expansion Rule (Cluster C1 NewCo investment trigger)
        if (params["auto_expand_fleet"] and year < horizon and n_boats < int(params["max_boats"])
                and (unmet_ratio > 0.05 or requested_days > fleet_days_cap * 1.02)
                and margin_y > 0 and (cumulative_cash >= -0.35 * equity_per_boat or year >= 3)):
            n_boats += 1
            cumulative_cash -= equity_per_boat
            expansion_years.append(year + 1)
            expansion_log.append(
                f"Year {year + 1}: deployed Boat #{n_boats} (unmet peak waste {unmet_ratio * 100:.0f}%, "
                f"utilisation {fleet_utilization_pct:.0f}%)"
            )

    last = yearly_series[-1]
    optimal_boats = max(1, min(int(params["max_boats"]), math.ceil(last["requested_days"] / boat_days_cap))) if last["requested_days"] > 0 else 1
    second_boat_year = expansion_years[0] if expansion_years else None
    avg_cov = sum(y["coverage_ratio"] for y in yearly_series) / len(yearly_series) if yearly_series else 0.0

    return {
        "archipelago_key": arch_key,
        "archipelago_name": cluster["name"],
        "ga_msw_note": cluster["ga_msw_note"],
        "islands_in_scope": [isl["island"] for isl in islands],
        "params": dict(params),
        "yearly_series": yearly_series,
        "expansion_log": expansion_log,
        "summary": {
            "initial_boats": 1,
            "final_boats": last["n_boats"],
            "optimal_boats_needed": optimal_boats,
            "final_operators": last["trained_operators"],
            "second_boat_year": second_boat_year,
            "expansion_years": expansion_years,
            "total_diverted_t": round(tot_diverted, 1),
            "total_unmet_t": round(tot_unmet, 1),
            "final_muni_adoption_pct": last["muni_adoption_pct"],
            "final_dmc_adoption_pct": last["dmc_adoption_pct"],
            "final_artisan_adoption_pct": last["artisan_adoption_pct"],
            "final_awareness_pct": last["awareness_pct"],
            "final_trust_pct": last["secondary_trust_pct"],
            "final_cumulative_cash_eur": last["cumulative_cash_eur"],
            "avg_coverage_ratio": round(avg_cov, 2),
        },
        "t24_pipeline_mapping": {
            "waste_inventory": "Monthly & annual island plastic/textile demand (t/yr) aligned with T2.3 RIALTO feed",
            "routes": "Archipelago island nodes & inter-island marine transit hours (D2.2 scheduler)",
            "machinery_catalogue": "100 kg/h plastic shredder & 0.5 kg/h textile line constraints (plant engineering baseline)",
            "boat_envelope": f"Fleet size N={last['n_boats']} boats ({boat_days_cap} active days/boat-year cap)",
            "mission_params": "Gate fee (€/t), ReBoat package share (%), traceability flag, and tariff escalation (%/yr)",
        },
    }


def compute_tradeoff_frontier(
    base_scn: dict,
    eco_params: dict | None = None,
    gate_fees: tuple[float, ...] = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0),
) -> list[dict[str, Any]]:
    """Evaluate systemic operator-vs-municipality trade-off across gate fees at end of horizon."""
    params = {**DEFAULT_ECO_PARAMS, **(eco_params or {})}
    rows = []
    for gf in gate_fees:
        scn_gf = {**base_scn, "gate_fee": float(gf)}
        sim = _simulate_core(scn_gf, params)
        last = sim["yearly_series"][-1]
        avg_muni = sum(y["muni_adoption_pct"] for y in sim["yearly_series"]) / len(sim["yearly_series"])
        rows.append({
            "gate_fee_eur_per_t": float(gf),
            "avg_coverage_ratio": sim["summary"]["avg_coverage_ratio"],
            "final_coverage_ratio": last["coverage_ratio"],
            "avg_muni_adoption_pct": round(avg_muni, 1),
            "final_muni_adoption_pct": last["muni_adoption_pct"],
            "final_cumulative_cash_eur": last["cumulative_cash_eur"],
            "total_diverted_t": sim["summary"]["total_diverted_t"],
            "final_boats": sim["summary"]["final_boats"],
        })
    return rows


def run_ecosystem_simulation(base_scn: dict, eco_params: dict | None = None) -> dict[str, Any]:
    """Run multi-year ecosystem simulation plus DPP counterfactual and gate-fee trade-off frontier."""
    params = {**DEFAULT_ECO_PARAMS, **(eco_params or {})}
    res = _simulate_core(base_scn, params)

    # Counterfactual: quantify traceability uplift on artisan secondary-material adoption
    no_dpp = _simulate_core(base_scn, {**params, "dpp_enabled": False})
    with_dpp = res if params["dpp_enabled"] else _simulate_core(base_scn, {**params, "dpp_enabled": True})
    dpp_uplift = round(with_dpp["summary"]["final_artisan_adoption_pct"] - no_dpp["summary"]["final_artisan_adoption_pct"], 1)
    res["summary"]["dpp_uplift_artisan_pp"] = dpp_uplift
    res["summary"]["artisan_no_dpp_pct"] = no_dpp["summary"]["final_artisan_adoption_pct"]
    res["summary"]["artisan_with_dpp_pct"] = with_dpp["summary"]["final_artisan_adoption_pct"]

    res["tradeoff_frontier"] = compute_tradeoff_frontier(base_scn, params)
    return res
