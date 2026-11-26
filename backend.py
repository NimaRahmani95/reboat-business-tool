"""
ReBoat Task 2.6 – calculation engine 4.0.0 (Business planning and ecosystem analysis tool, D2.3)
Lead: Politecnico di Milano (POLIMI) · Horizon Europe GA 101182350

Scope (Task 2.6): revenue streams, cost projections, investment analysis and sustainability
indicators of ONE OPERATING YEAR AFTER THE PROJECT (exploitation scenario), not income of the
EU-funded pilot demonstrations. Paired with ecosystem_sim.py (v4.0.0) for multi-year archipelago dynamics.

Changes in 4.0.0 (M24 D2.3 v1.0 release):
  • Aligned textile spinning line throughput limit (0.5 kg/h, 4 kg per 8h shift) with plant engineering specifications.
  • Benchmark citations added to PROXY_SOURCES (Eurostat, Plastics Europe, OPIS, EU ETS, plant engineering baseline).
  • Clamped -0.00 floating-point display artifacts to +0.00 in material_flows.
  • Added diagnostic annual_diesel_litres, annual_transit_diesel_co2_tonnes, and annual_shore_power_kwh
    to calculate_annual_business_plan() without altering any revenue, cost, margin, or SROI outputs.
"""
import math

SEASON_MULTIPLIER = {
    "High": 1.2,
    "Medium": 1.0,
    "Mid": 1.0,
    "Shoulder": 0.8,
    "Low": 0.5,
}

TOOL_VERSION = "4.0.0"

PACKAGE_KEYS = ["Day_Trip", "Short_Trip", "Slow_Trip", "Medium_Slow", "Deep_Slow"]

# WP4 note "Tourism packages pricing": per-person cost floors of complete packages (Value positioning,
# B&B or 2–3★ hotel, excluding flights and accommodation taxes), by pilot location and season.
PRICING_NOTE = {
    "Corfu": {
        "Low":  [(45, 70), (180, 300), (400, 600), (750, 1150), (1400, 2200)],
        "Mid":  [(55, 85), (220, 360), (500, 750), (900, 1400), (1700, 2700)],
        "High": [(70, 110), (280, 450), (650, 950), (1200, 1800), (2300, 3500)],
    },
    "Paxos": {
        "Low":  [(50, 75), (220, 350), (500, 750), (950, 1400), (1700, 2600)],
        "Mid":  [(65, 95), (280, 430), (650, 950), (1200, 1800), (2200, 3400)],
        "High": [(80, 120), (380, 550), (850, 1250), (1600, 2400), (3000, 4500)],
    },
    "Lipari": {
        "Low":  [(50, 80), (200, 330), (450, 700), (800, 1300), (1500, 2500)],
        "Mid":  [(60, 100), (260, 400), (600, 850), (1050, 1600), (2000, 3200)],
        "High": [(80, 130), (350, 520), (750, 1100), (1400, 2100), (2800, 4200)],
    },
    "Filicudi": {
        "Low":  [(55, 80), (230, 360), (500, 750), (900, 1400), (1600, 2500)],
        "Mid":  [(70, 100), (300, 450), (650, 950), (1200, 1800), (2100, 3300)],
        "High": [(90, 130), (400, 580), (850, 1250), (1600, 2400), (2900, 4300)],
    },
    "Terceira": {
        "Low":  [(45, 75), (190, 320), (420, 650), (800, 1250), (1450, 2400)],
        "Mid":  [(55, 90), (230, 380), (520, 800), (1000, 1550), (1900, 3000)],
        "High": [(70, 115), (300, 470), (680, 1000), (1300, 2000), (2500, 3800)],
    },
}
PACKAGE_DURATIONS = {"Day_Trip": "1 day", "Short_Trip": "1–3 days", "Slow_Trip": "4–7 days",
                     "Medium_Slow": "1–2 weeks", "Deep_Slow": "15–30 days"}

# Avoided disposal cost per tonne by island (municipal saving).
AVOIDED_DISPOSAL_COST = {
    "Corfu": 150.0,      # ferry freight to the mainland; GA: 100–250 €/t for minor islands (p. 131)
    "Paxos": 150.0,
    "Lipari": 150.0,
    "Filicudi": 150.0,
    "Terceira": 50.0,    # local on-island incinerator tariff
}

# GA Part B, Table 2.7 (p. 147): "Recycling as a service", €80,000 per 50 t.
GA_RAAS_GATE_FEE_EUR_PER_T = 1600.0

MONTHLY_SCHEDULE = [
    {"month_code": "Gen", "name": "January", "season": "Low", "mult": 0.5, "days_active": 10, "days_in_month": 31},
    {"month_code": "Feb", "name": "February", "season": "Low", "mult": 0.5, "days_active": 10, "days_in_month": 28},
    {"month_code": "Mar", "name": "March", "season": "Low", "mult": 0.6, "days_active": 12, "days_in_month": 31},
    {"month_code": "Apr", "name": "April", "season": "Mid", "mult": 0.85, "days_active": 15, "days_in_month": 30},
    {"month_code": "Mag", "name": "May", "season": "Mid", "mult": 1.0, "days_active": 18, "days_in_month": 31},
    {"month_code": "Giu", "name": "June", "season": "Mid", "mult": 1.15, "days_active": 20, "days_in_month": 30},
    {"month_code": "Lug", "name": "July", "season": "High", "mult": 1.4, "days_active": 24, "days_in_month": 31},
    {"month_code": "Ago", "name": "August", "season": "High", "mult": 1.5, "days_active": 25, "days_in_month": 31},
    {"month_code": "Set", "name": "September", "season": "High", "mult": 1.25, "days_active": 22, "days_in_month": 30},
    {"month_code": "Ott", "name": "October", "season": "Mid", "mult": 0.85, "days_active": 15, "days_in_month": 31},
    {"month_code": "Nov", "name": "November", "season": "Low", "mult": 0.5, "days_active": 10, "days_in_month": 30},
    {"month_code": "Dic", "name": "December", "season": "Low", "mult": 0.5, "days_active": 10, "days_in_month": 31},
]
REFERENCE_CAMPAIGN_DAYS = 14

DEFAULT_OPTIONS = {
    "price_point": "mid",              # low / mid / high point of each pricing-note range
    "reboat_share_pct": 10.0,          # ReBoat share of the package price (placeholder pending T4.3 protocols)
    "gate_fee_eur_per_t": 0.0,         # Recycling-as-a-Service gate fee (0 = not charged)
    "product_operator_share_pct": 100.0,
    "sales_commission_pct": 0.0,       # % of the operator's tourism revenue
    "vessel_charter_eur_per_day": 0.0,
    "insurance_eur_per_year": 0.0,
    "land_collection_eur_per_t": 0.0,
    "overheads_pct": 0.0,              # % of all other operating costs
}


def season_key(season):
    return "Mid" if season in ("Mid", "Medium") else season


class ReBoatDigitalBrain:
    """Task 2.6 business planning and ecosystem analysis engine (D2.3)."""

    PROXY_SOURCES = {
        "marine_diesel_eur_per_liter": "Med bunker index proxy (mid-2026 baseline)",
        "daily_berth_and_shore_power_eur": "Transient commercial port rate (island-specific default)",
        "municipal_waste_export_cost_per_tonne": "Avoided disposal cost: ferry freight to mainland (GA p. 131: 100–250 €/t) or local incinerator (Terceira €50/t local incinerator)",
        "rPET_flake_market_value_eur_per_kg": "Recycled polymer flake bulk price proxy (OPIS rPET benchmark €1.34/kg; Plastics Europe 15% loss / 85% flake yield)",
        "recycled_yarn_market_value_eur_per_kg": "Circular textile yarn bulk price proxy",
        "shore_power_electricity_eur_per_kwh": "Regional commercial utility tariff (Eurostat benchmark €0.28/kWh; Plant engineering baseline Scenario B 52 kW)",
        "labor_cost_eur_per_day": "Operator crew proxy; cross-check GA Table 2.7: 3 FTE × €50,000",
        "maintenance_eur_per_day": "Consumables, preventive servicing and spare parts allocation",
        "drayage_and_event_logistics_eur": "Land deployment (switched off: quayside operation only)",
    }

    # Kept for compatibility with earlier releases; tourism revenue now comes from PRICING_NOTE.
    PRICING_MATRIX = {"Day_Trip": 50.0, "Short_Trip": 120.0, "Slow_Trip": 250.0, "Medium_Slow": 600.0, "Deep_Slow": 1200.0}

    CIRCULAR_PRODUCTS_CATALOG = {
        "injection_molded_goods": {"name": "Injection-Molded Design Goods (Carabiners, Handles, Coasters)",
                                   "unit_price_eur": 12.0, "unit_weight_kg": 0.08, "stream": "Thermoplastics"},
        "custom_3d_printed_artifacts": {"name": "FGF/FDM 3D Printed Custom Artifacts and Living Lab Pieces",
                                        "unit_price_eur": 35.0, "unit_weight_kg": 0.25, "stream": "Thermoplastics"},
        "thermo_pressed_furniture_panel": {"name": "Hot-Pressed Upcycled Furniture and Architectural Panels",
                                           "unit_price_eur": 95.0, "unit_weight_kg": 2.50, "stream": "Mixed Composites"},
        "artisanal_woven_textiles": {"name": "Hand-Woven Artisanal Textile Goods (Scarves, Bags, Tapestry)",
                                     "unit_price_eur": 45.0, "unit_weight_kg": 0.35, "stream": "Textiles"},
        "plied_yarn_spools": {"name": "Premium Plied ReBoat Yarn Spools (500g)",
                              "unit_price_eur": 8.0, "unit_weight_kg": 0.50, "stream": "Textiles"},
    }

    def __init__(self, target_island="Corfu", season="High"):
        self.project_name = "ReBoat"
        self.grant_id = "101182350"
        self.project_duration_months = 42
        self.target_island = target_island
        self.season = season

        # Plant engineering baseline: installed power per container and Scenario B (non-simultaneous operation).
        self.container_panel_kw = {"C1_Input_Management": 9.4, "C2_Demanufacturing": 34.1,
                                   "C3_Textile_Reprocessing": 13.6, "C4_Plastic_Reprocessing": 40.6}
        self.scenario_b_load_kw = {"C1_Input_Management": 6.8, "C2_Demanufacturing": 21.8,
                                   "C3_Textile_Reprocessing": 5.4, "C4_Plastic_Reprocessing": 18.3}
        self.coincident_power_kw = 52.0
        self.coincident_factor = round(self.coincident_power_kw / sum(self.container_panel_kw.values()), 2)
        self.operating_hours_per_day = 8.0

        self.throughput_bottlenecks = {
            "sorting_hub_pcs_hr": 700.0,
            "packaging_sorting_kg_hr": 17.5,
            "plastics_shredding_kg_hr": 100.0,    # Plant engineering baseline (soft thermoplastics)
            "textile_fraying_kg_hr": 50.0,        # Plant engineering baseline
            "textile_carding_kg_hr": 4.0,         # Plant engineering baseline
            "textile_coiler_drawing_kg_hr": 0.5,  # Plant engineering baseline: coiler/drawing 0.5 kg/h
            "textile_spinning_kg_hr": 0.5,        # Spinning line operational throughput limit: 0.5 kg/h (4 kg/8h shift)
            "textile_twisting_kg_hr": 2.5,
            "plastic_pellet_extrusion_kg_hr": 15.0,
            "plastic_injection_molding_kg_hr": 1.0,
            "plastic_heat_press_kg_hr": 10.0,
            "plastic_3d_printing_kg_hr": 0.5,
        }

        self.visit_durations_hr = {
            "Day_Trip": {"min": 1.5, "max": 3.0, "format": "Introductory / Awareness"},
            "Short_Trip": {"min": 3.0, "max": 5.0, "format": "Interactive / Workshop"},
            "Slow_Trip": {"min": 4.0, "max": 7.0, "format": "Immersive Lab Activity"},
            "Medium_Slow": {"min": 8.0, "max": 16.0, "format": "Co-Creation / Data Collection"},
            "Deep_Slow": {"min": 16.0, "max": 40.0, "format": "Living Lab Prototyping"},
        }

        self.proxies = {
            "marine_diesel_eur_per_liter": 1.75,
            "daily_berth_and_shore_power_eur": 300.0,
            "municipal_waste_export_cost_per_tonne": AVOIDED_DISPOSAL_COST.get(target_island, 150.0),
            "rPET_flake_market_value_eur_per_kg": 1.50,
            "recycled_yarn_market_value_eur_per_kg": 2.50,
            "shore_power_electricity_eur_per_kwh": 0.28,
            "labor_cost_eur_per_day": 800.0,
            "maintenance_eur_per_day": 150.0,
            "drayage_and_event_logistics_eur": 1200.0,
        }

        self.machinery_capex_eur = 370_850
        self.container_conversion_capex_eur = 45_000
        self.exhibition_package_capex_eur = 15_000
        self.capex_baseline_eur = self.machinery_capex_eur + self.container_conversion_capex_eur + self.exhibition_package_capex_eur
        self.capex_amortization_years = 10

        self.capex_financing_scenarios = {
            "Public_Private_Partnership": {"name": "Municipal Public-Private Partnership (PPP)",
                                           "description": "50% Regional/Municipal green public procurement, 50% private operator equity",
                                           "probability": 0.60, "coverage_percent": 50},
            "Private_Investment": {"name": "Private Operator Commercial Investment",
                                   "description": "100% Private equity / impact debt financing with commercial return targets",
                                   "probability": 0.35, "coverage_percent": 0},
        }

        # Indicative placeholders, NOT in the baseline (used only in the D2.3 sensitivity analysis).
        self.compliance_costs = {"Maritime_Port_Concession": 8000, "Municipal_Public_Space_Concession": 5000,
                                 "Electrical_Safety_Class_A_Certification": 4500, "Waste_Processing_Authorization": 12000,
                                 "Annual_Environmental_Audit": 3500}

    # ------------------------------------------------------------------ helpers
    def get_season_multiplier(self):
        return SEASON_MULTIPLIER.get(self.season, 1.0)

    def textile_line_rate_kg_hr(self):
        t = self.throughput_bottlenecks
        return min(t["textile_carding_kg_hr"], t["textile_coiler_drawing_kg_hr"], t["textile_spinning_kg_hr"])

    def get_plastic_capacity_kg(self, operational_days, operating_hours_per_day=None):
        h = self.operating_hours_per_day if operating_hours_per_day is None else operating_hours_per_day
        return self.throughput_bottlenecks["plastics_shredding_kg_hr"] * h * operational_days

    def get_textile_capacity_kg(self, operational_days, operating_hours_per_day=None):
        h = self.operating_hours_per_day if operating_hours_per_day is None else operating_hours_per_day
        return self.textile_line_rate_kg_hr() * h * operational_days

    def package_prices(self, season, point="mid", island=None):
        """€ per participant for each package from the WP4 pricing note."""
        isl = island or self.target_island
        table = PRICING_NOTE.get(isl, PRICING_NOTE["Corfu"])[season_key(season)]
        out = {}
        for key, (lo, hi) in zip(PACKAGE_KEYS, table):
            out[key] = float(lo if point == "low" else hi if point == "high" else (lo + hi) / 2.0)
        return out

    # ------------------------------------------------------------------ campaign blocks
    def calculate_campaign_opex(self, operational_days, transit_hours=0.0, land_event_mode=False, opts=None,
                                waste_tonnes=0.0, tourism_revenue=0.0, insurance_share=0.0):
        o = {**DEFAULT_OPTIONS, **(opts or {})}
        season_mult = self.get_season_multiplier()
        daily_energy_kwh = self.coincident_power_kw * self.operating_hours_per_day
        utility_cost = daily_energy_kwh * self.proxies["shore_power_electricity_eur_per_kwh"] * operational_days * season_mult
        berthing_cost = self.proxies["daily_berth_and_shore_power_eur"] * operational_days * season_mult
        labor_cost = self.proxies["labor_cost_eur_per_day"] * operational_days * season_mult
        maintenance_cost = self.proxies["maintenance_eur_per_day"] * operational_days * season_mult
        transit_fuel_cost = transit_hours * 45.0 * self.proxies["marine_diesel_eur_per_liter"]
        land_logistics_cost = self.proxies["drayage_and_event_logistics_eur"] if land_event_mode else 0.0
        vessel_cost = o["vessel_charter_eur_per_day"] * operational_days
        insurance_cost = o["insurance_eur_per_year"] * insurance_share
        collection_cost = o["land_collection_eur_per_t"] * waste_tonnes
        commission_cost = o["sales_commission_pct"] / 100.0 * tourism_revenue
        before_overheads = (utility_cost + berthing_cost + labor_cost + maintenance_cost + transit_fuel_cost
                            + land_logistics_cost + vessel_cost + insurance_cost + collection_cost + commission_cost)
        overheads_cost = o["overheads_pct"] / 100.0 * before_overheads
        total_opex = before_overheads + overheads_cost
        return {
            "utility_shore_power_costs_eur": round(utility_cost, 2),
            "berthing_and_port_costs_eur": round(berthing_cost, 2),
            "labor_costs_eur": round(labor_cost, 2),
            "maintenance_costs_eur": round(maintenance_cost, 2),
            "transit_fuel_costs_eur": round(transit_fuel_cost, 2),
            "land_event_logistics_eur": round(land_logistics_cost, 2),
            "vessel_charter_costs_eur": round(vessel_cost, 2),
            "insurance_costs_eur": round(insurance_cost, 2),
            "land_collection_costs_eur": round(collection_cost, 2),
            "sales_commission_costs_eur": round(commission_cost, 2),
            "overheads_costs_eur": round(overheads_cost, 2),
            "coincident_power_kw": self.coincident_power_kw,
            "daily_energy_kwh": daily_energy_kwh,
            "season_multiplier_applied": season_mult,
            "total_operational_opex_eur": round(total_opex, 2),
        }

    def simulate_commercial_yields(self, package_sales_volume, plastic_processed_kg, textile_processed_kg=0.0,
                                   circular_products_sales=None, operational_days=14, opts=None, season=None):
        o = {**DEFAULT_OPTIONS, **(opts or {})}
        prices = self.package_prices(season or self.season, o["price_point"])
        package_turnover = sum(prices.get(k, 0.0) * int(v) for k, v in package_sales_volume.items())
        tourism_revenue = package_turnover * o["reboat_share_pct"] / 100.0

        # Material available for products: flakes (85% of plastic) and yarn (75% of the textile the line accepts).
        textile_capacity_kg = self.get_textile_capacity_kg(operational_days)
        textile_input_kg = min(textile_processed_kg, textile_capacity_kg)
        plastic_capacity_kg = self.get_plastic_capacity_kg(operational_days)
        plastic_input_kg = min(plastic_processed_kg, plastic_capacity_kg)
        flakes_available_kg = plastic_input_kg * 0.85
        yarn_available_kg = textile_input_kg * 0.75

        requested, need = {}, {"plastic": 0.0, "textile": 0.0}
        for item_key, quantity in (circular_products_sales or {}).items():
            spec = self.CIRCULAR_PRODUCTS_CATALOG.get(item_key)
            if spec is None:
                continue
            pool = "textile" if spec["stream"] == "Textiles" else "plastic"
            q = max(int(quantity), 0)
            requested[item_key] = (q, spec, pool)
            need[pool] += spec["unit_weight_kg"] * q
        available = {"plastic": flakes_available_kg, "textile": yarn_available_kg}
        scale = {k: (1.0 if need[k] <= available[k] or need[k] == 0 else available[k] / need[k]) for k in need}

        product_sales_total = 0.0
        plastic_used, textile_used = 0.0, 0.0
        products_sold_units = {}
        for item_key, (q, spec, pool) in requested.items():
            sold = q if scale[pool] >= 1.0 else int(math.floor(q * scale[pool]))
            products_sold_units[item_key] = sold
            product_sales_total += spec["unit_price_eur"] * sold
            if pool == "textile":
                textile_used += spec["unit_weight_kg"] * sold
            else:
                plastic_used += spec["unit_weight_kg"] * sold
        finished_goods_revenue = product_sales_total * o["product_operator_share_pct"] / 100.0

        bulk_flakes_kg = max(flakes_available_kg - plastic_used, 0.0)
        bulk_yarn_kg = max(yarn_available_kg - textile_used, 0.0)
        plastic_revenue = bulk_flakes_kg * self.proxies["rPET_flake_market_value_eur_per_kg"]
        textile_revenue = bulk_yarn_kg * self.proxies["recycled_yarn_market_value_eur_per_kg"]

        waste_tonnes = (plastic_input_kg + textile_input_kg) / 1000.0
        gate_fee_revenue = o["gate_fee_eur_per_t"] * waste_tonnes
        total = tourism_revenue + finished_goods_revenue + plastic_revenue + textile_revenue + gate_fee_revenue

        return {
            "package_prices_eur": prices,
            "package_turnover_eur": round(package_turnover, 2),
            "tourism_package_gross_revenue_eur": round(tourism_revenue, 2),
            "product_sales_total_eur": round(product_sales_total, 2),
            "finished_upcycled_goods_revenue_eur": round(finished_goods_revenue, 2),
            "recycled_material_sales_revenue_eur": round(plastic_revenue, 2),
            "textile_yarn_sales_revenue_eur": round(textile_revenue, 2),
            "gate_fee_revenue_eur": round(gate_fee_revenue, 2),
            "total_gross_revenue_eur": round(total, 2),
            "net_flakes_produced_kg": round(flakes_available_kg, 2),
            "net_yarn_produced_kg": round(yarn_available_kg, 2),
            "flakes_used_for_products_kg": round(plastic_used, 3),
            "yarn_used_for_products_kg": round(textile_used, 3),
            "bulk_flakes_kg": round(bulk_flakes_kg, 3),
            "bulk_yarn_kg": round(bulk_yarn_kg, 3),
            "plastic_capacity_kg": round(plastic_capacity_kg, 2),
            "plastic_input_capped_kg": round(plastic_input_kg, 2),
            "plastic_bottleneck_exceeded": plastic_processed_kg > plastic_capacity_kg,
            "textile_capacity_kg": round(textile_capacity_kg, 2),
            "textile_input_capped_kg": round(textile_input_kg, 2),
            "textile_bottleneck_exceeded": textile_processed_kg > textile_capacity_kg,
            "waste_processed_tonnes": round(waste_tonnes, 4),
            "products_sold_units": products_sold_units,
            "products_capped_by_material": any(v < 1.0 for v in scale.values()),
        }

    def evaluate_ecosystem_impact(self, total_waste_diverted_tonnes, local_workers_trained, operational_days,
                                  grant_equity_annual_share=0.0, commercial_revenue=0.0, local_wages_eur=None,
                                  gate_fee_paid_eur=0.0, product_sales_kept_by_others_eur=0.0):
        avoided = total_waste_diverted_tonnes * self.proxies["municipal_waste_export_cost_per_tonne"]
        municipal_net = avoided - gate_fee_paid_eur
        wages = (local_wages_eur if local_wages_eur is not None
                 else self.proxies["labor_cost_eur_per_day"] * operational_days * self.get_season_multiplier())
        co2 = total_waste_diverted_tonnes * 0.12
        carbon_value = co2 * 80.0
        societal = municipal_net + wages + carbon_value + commercial_revenue + product_sales_kept_by_others_eur
        sroi = round(societal / grant_equity_annual_share, 2) if grant_equity_annual_share > 0 else None
        return {
            "avoided_disposal_cost_eur": round(avoided, 2),
            "municipal_landfill_export_savings_eur": round(municipal_net, 2),
            "socio_economic_value_retained_eur": round(wages, 2),
            "logistics_co2_emissions_avoided_tonnes": round(co2, 3),
            "carbon_economic_value_eur": round(carbon_value, 2),
            "total_societal_value_generated_eur": round(societal, 2),
            "sroi_ratio": sroi,
        }

    def calculate_capex_allocation(self, scenario_key):
        scenario = self.capex_financing_scenarios.get(scenario_key)
        if scenario is None:
            scenario_key = "Public_Private_Partnership"
            scenario = self.capex_financing_scenarios[scenario_key]
        gross = self.capex_baseline_eur
        grant = gross * scenario["coverage_percent"] / 100.0
        return {
            "scenario_key": scenario_key, "scenario_name": scenario["name"], "scenario_description": scenario["description"],
            "gross_capex_eur": round(gross, 2), "grant_coverage_eur": round(grant, 2),
            "net_equity_required_eur": round(max(gross - grant, 0.0), 2),
            "annual_amortization_eur": round(gross / self.capex_amortization_years, 2),
            "coverage_percent": scenario["coverage_percent"],
            "machinery_share_eur": self.machinery_capex_eur, "container_conversion_share_eur": self.container_conversion_capex_eur,
            "exhibition_materials_share_eur": self.exhibition_package_capex_eur,
        }

    def calculate_investment_metrics(self, net_margin_eur, operational_days, net_equity, discount_rate=0.08):
        if operational_days <= 0:
            operational_days = 1
        campaigns_per_year = max(round(120.0 / operational_days, 1), 1.0)
        annualized_margin = net_margin_eur * campaigns_per_year
        payback = None
        if annualized_margin > 0 and net_equity > 0:
            payback = net_equity / annualized_margin
        elif net_equity == 0:
            payback = 0.0
        npv_5yr = None
        if annualized_margin != 0 or net_equity > 0:
            npv_5yr = annualized_margin * sum(1 / ((1 + discount_rate) ** t) for t in range(1, 6)) - net_equity
        irr = None
        if net_equity > 0 and annualized_margin > 0:
            lo, hi = 0.0, 1.0
            for _ in range(50):
                mid = (lo + hi) / 2
                if sum(annualized_margin / ((1 + mid) ** t) for t in range(1, 6)) - net_equity > 0:
                    lo = mid
                else:
                    hi = mid
            irr = lo * 100
        elif net_equity == 0 and annualized_margin > 0:
            irr = 100.0
        return {"annualized_net_margin_eur": round(annualized_margin, 2), "campaigns_per_year_circuit": campaigns_per_year,
                "payback_years": round(payback, 2) if payback is not None else None,
                "npv_5yr_eur": round(npv_5yr, 2) if npv_5yr is not None else None,
                "irr_percent": round(irr, 2) if irr is not None else None, "discount_rate_used": discount_rate}

    def build_assumptions_dict(self, capex_scenario, opts=None):
        return {
            "scenario_type": "Operating year after the project (exploitation scenario) – not income of the EU-funded pilots",
            "target_island": self.target_island, "season": self.season,
            "season_multiplier": self.get_season_multiplier(), "coincident_power_kw": self.coincident_power_kw,
            "textile_line_rate_kg_hr": self.textile_line_rate_kg_hr(),
            "capex_scenario": capex_scenario, "capex_baseline_eur": self.capex_baseline_eur,
            "options": {**DEFAULT_OPTIONS, **(opts or {})},
            "proxies": dict(self.proxies), "proxy_sources": dict(self.PROXY_SOURCES),
        }

    # ------------------------------------------------------------------ annual plan
    @staticmethod
    def _opts(config_dict):
        return {k: config_dict.get(k, v) for k, v in DEFAULT_OPTIONS.items()}

    def calculate_annual_business_plan(self, config_dict):
        """Twelve monthly campaigns of one operating year after the project. Volumes scale with the monthly demand
        multiplier and active days; day-based costs with the season class. Campaign length scales active days."""
        opts = self._opts(config_dict)
        capex_scenario = config_dict.get("capex_scenario", "Public_Private_Partnership")
        capex_res = self.calculate_capex_allocation(capex_scenario)
        monthly_amort = capex_res["annual_amortization_eur"] / 12.0
        campaign_days = float(config_dict.get("campaign_days", REFERENCE_CAMPAIGN_DAYS) or REFERENCE_CAMPAIGN_DAYS)
        day_scale = campaign_days / REFERENCE_CAMPAIGN_DAYS

        base_plastic = config_dict.get("plastic_processed_kg", 4200.0)
        base_textile = config_dict.get("textile_processed_kg", base_plastic * 0.30)
        base_pkg = config_dict.get("package_sales", {})
        base_circ = config_dict.get("circular_products_sales", {})
        transit_base = config_dict.get("transit_hours", 6.5)

        A = {k: 0.0 for k in ["revenue", "opex", "waste", "wages", "turnover", "tour", "prod", "prod_total", "flakes", "yarn",
                              "gate", "power", "berth", "labor", "fuel", "maint", "land", "vessel", "insur", "collect",
                              "commission", "overheads", "plastic_kg", "plastic_acc_kg", "textile_kg", "textile_acc_kg", "flakes_kg",
                              "yarn_kg", "flakes_prod_kg", "yarn_prod_kg", "flakes_bulk_kg", "yarn_bulk_kg", "days",
                              "diesel_litres", "shore_kwh"]}
        units_pkg = {k: 0 for k in base_pkg}
        units_prod = {k: 0 for k in base_circ}
        orig_season = self.season
        monthly = []
        total_days = sum(min(round(m["days_active"] * day_scale), m["days_in_month"]) for m in MONTHLY_SCHEDULE)
        for m in MONTHLY_SCHEDULE:
            self.season = m["season"]
            days = int(min(round(m["days_active"] * day_scale), m["days_in_month"]))
            sf = m["mult"] * (days / 14.0)
            pkg = {k: int(v * sf) for k, v in base_pkg.items()}
            circ = {k: int(v * sf) for k, v in base_circ.items()} if base_circ else None
            plastic, textile = base_plastic * sf, base_textile * sf
            rv = self.simulate_commercial_yields(pkg, plastic, textile, circ, operational_days=days, opts=opts, season=m["season"])
            waste_t = rv["waste_processed_tonnes"]
            transit_m = transit_base * (days / 14.0)
            op = self.calculate_campaign_opex(operational_days=days, transit_hours=transit_m,
                                              land_event_mode=config_dict.get("land_event_mode", False), opts=opts,
                                              waste_tonnes=waste_t, tourism_revenue=rv["tourism_package_gross_revenue_eur"],
                                              insurance_share=(days / total_days if total_days else 0.0))
            rev, cost = rv["total_gross_revenue_eur"], op["total_operational_opex_eur"]
            for k, v in pkg.items():
                units_pkg[k] += v
            for k, v in rv["products_sold_units"].items():
                units_prod[k] = units_prod.get(k, 0) + v
            adds = dict(revenue=rev, opex=cost, waste=waste_t, wages=op["labor_costs_eur"], turnover=rv["package_turnover_eur"],
                        tour=rv["tourism_package_gross_revenue_eur"], prod=rv["finished_upcycled_goods_revenue_eur"],
                        prod_total=rv["product_sales_total_eur"], flakes=rv["recycled_material_sales_revenue_eur"],
                        yarn=rv["textile_yarn_sales_revenue_eur"], gate=rv["gate_fee_revenue_eur"],
                        power=op["utility_shore_power_costs_eur"], berth=op["berthing_and_port_costs_eur"],
                        labor=op["labor_costs_eur"], fuel=op["transit_fuel_costs_eur"], maint=op["maintenance_costs_eur"],
                        land=op["land_event_logistics_eur"], vessel=op["vessel_charter_costs_eur"], insur=op["insurance_costs_eur"],
                        collect=op["land_collection_costs_eur"], commission=op["sales_commission_costs_eur"],
                        overheads=op["overheads_costs_eur"], plastic_kg=plastic,
                        plastic_acc_kg=rv["plastic_input_capped_kg"], textile_kg=textile,
                        textile_acc_kg=rv["textile_input_capped_kg"], flakes_kg=rv["net_flakes_produced_kg"],
                        yarn_kg=rv["net_yarn_produced_kg"], flakes_prod_kg=rv["flakes_used_for_products_kg"],
                        yarn_prod_kg=rv["yarn_used_for_products_kg"], flakes_bulk_kg=rv["bulk_flakes_kg"],
                        yarn_bulk_kg=rv["bulk_yarn_kg"], days=days,
                        diesel_litres=transit_m * 45.0,
                        shore_kwh=op["daily_energy_kwh"] * days * op["season_multiplier_applied"])
            for k, v in adds.items():
                A[k] += v
            monthly.append({
                "month_code": m["month_code"], "month_name": m["name"], "season": m["season"], "days_active": days,
                "season_multiplier": self.get_season_multiplier(),
                "demand_multiplier": m["mult"], "volume_scale": round(sf, 4),
                "revenue_eur": round(rev, 2), "opex_eur": round(cost, 2),
                "rev_opex_ratio": round(rev / cost, 2) if cost > 0 else 0.0,
                "operating_margin_eur": round(rev - cost, 2), "monthly_amortization_eur": round(monthly_amort, 2),
                "net_after_amortization_eur": round(rev - cost - monthly_amort, 2),
                "waste_diverted_tonnes": round(waste_t, 2),
                "package_units": pkg, "package_prices_eur": rv["package_prices_eur"],
                "package_turnover_eur": rv["package_turnover_eur"],
                "products_sold_units": rv["products_sold_units"],
                "revenue_lines": {"tourism": rv["tourism_package_gross_revenue_eur"], "products": rv["finished_upcycled_goods_revenue_eur"],
                                  "flakes": rv["recycled_material_sales_revenue_eur"], "yarn": rv["textile_yarn_sales_revenue_eur"],
                                  "gate_fee": rv["gate_fee_revenue_eur"]},
                "opex_lines": {"crew": op["labor_costs_eur"], "berth": op["berthing_and_port_costs_eur"],
                               "maintenance": op["maintenance_costs_eur"], "power": op["utility_shore_power_costs_eur"],
                               "fuel": op["transit_fuel_costs_eur"], "vessel": op["vessel_charter_costs_eur"],
                               "insurance": op["insurance_costs_eur"], "collection": op["land_collection_costs_eur"],
                               "commission": op["sales_commission_costs_eur"], "overheads": op["overheads_costs_eur"]},
            })
        self.season = orig_season

        revenue, opex = A["revenue"], A["opex"]
        margin = round(revenue - opex, 2)
        net = round(margin - capex_res["annual_amortization_eur"], 2)
        ratio = round(revenue / opex, 2) if opex > 0 else 0.0
        waste_t = A["waste"]
        avoided = round(waste_t * self.proxies["municipal_waste_export_cost_per_tonne"], 2)
        municipal_net = round(avoided - A["gate"], 2)
        co2_t = round(waste_t * 0.12, 2)
        carbon_val = round(co2_t * 80.0, 2)
        grant_y = capex_res["grant_coverage_eur"] / self.capex_amortization_years
        kept_by_others = A["prod_total"] - A["prod"]
        societal = municipal_net + A["wages"] + carbon_val + revenue + kept_by_others
        sroi = round(societal / grant_y, 2) if grant_y > 0 else None
        sroi_noturn = round((municipal_net + A["wages"] + carbon_val) / grant_y, 2) if grant_y > 0 else None
        equity = capex_res["net_equity_required_eur"]
        payback = (round(equity / margin, 2) if margin > 0 and equity > 0 else (0.0 if equity == 0 else None))
        ann5 = sum(1 / 1.08 ** t for t in range(1, 6))
        ann10 = sum(1 / 1.08 ** t for t in range(1, 11))

        # Break-even ReBoat share: revenue(s) = opex(s), with commission and overheads depending on s.
        o = opts
        T = A["turnover"]
        R0 = revenue - A["tour"]
        Cnc = opex - A["commission"] - A["overheads"]
        c, ov = o["sales_commission_pct"] / 100.0, o["overheads_pct"] / 100.0
        breakeven_share = None
        if T > 0 and (1 - (1 + ov) * c) > 0:
            breakeven_share = round(((1 + ov) * Cnc - R0) / (T * (1 - (1 + ov) * c)) * 100.0, 2)

        flows = {
            "plastic_collected_t": round(A["plastic_kg"] / 1000, 2) + 0.0,
            "plastic_accepted_t": round(A["plastic_acc_kg"] / 1000, 2) + 0.0,
            "plastic_not_accepted_t": round(max(A["plastic_kg"] - A["plastic_acc_kg"], 0.0) / 1000, 2) + 0.0,
            "textile_delivered_t": round(A["textile_kg"] / 1000, 2) + 0.0,
            "textile_accepted_t": round(A["textile_acc_kg"] / 1000, 2) + 0.0,
            "textile_not_accepted_t": round(max(A["textile_kg"] - A["textile_acc_kg"], 0.0) / 1000, 2) + 0.0,
            "flakes_recovered_t": round(A["flakes_kg"] / 1000, 2) + 0.0,
            "flakes_to_products_t": round(A["flakes_prod_kg"] / 1000, 3) + 0.0,
            "flakes_sold_bulk_t": round(A["flakes_bulk_kg"] / 1000, 2) + 0.0,
            "yarn_recovered_t": round(A["yarn_kg"] / 1000, 3) + 0.0,
            "yarn_to_products_t": round(A["yarn_prod_kg"] / 1000, 3) + 0.0,
            "yarn_sold_bulk_t": round(A["yarn_bulk_kg"] / 1000, 3) + 0.0,
            "process_losses_t": round(max(A["plastic_acc_kg"] - A["flakes_kg"] + A["textile_acc_kg"] - A["yarn_kg"], 0.0) / 1000, 2) + 0.0,
        }
        capex_breakdown = {
            "machinery_capex_eur": self.machinery_capex_eur,
            "machinery_annual_amortization_eur": round(self.machinery_capex_eur / self.capex_amortization_years, 2),
            "conversion_capex_eur": self.container_conversion_capex_eur,
            "conversion_annual_amortization_eur": round(self.container_conversion_capex_eur / self.capex_amortization_years, 2),
            "exhibition_capex_eur": self.exhibition_package_capex_eur,
            "exhibition_annual_amortization_eur": round(self.exhibition_package_capex_eur / self.capex_amortization_years, 2),
            "total_capex_eur": self.capex_baseline_eur,
            "total_annual_amortization_eur": capex_res["annual_amortization_eur"],
            "basis": "Aggregate plant planning budget baseline (machinery, container conversion, exhibition)",
        }
        return {
            "scenario_type": "Operating year after the project (exploitation scenario)",
            "annual_active_days": int(A["days"]),
            "campaign_days": campaign_days,
            "annual_gross_revenue_eur": round(revenue, 2),
            "annual_total_opex_eur": round(opex, 2),
            "annual_net_operating_margin_eur": margin,
            "annual_capex_amortization_eur": capex_res["annual_amortization_eur"],
            "annual_net_after_capex_eur": net,
            "annual_revenue_to_opex_ratio": ratio,
            "annual_waste_diverted_tonnes": round(waste_t, 2),
            "annual_avoided_disposal_cost_eur": avoided,
            "annual_gate_fee_paid_eur": round(A["gate"], 2),
            "annual_municipal_savings_eur": municipal_net,
            "annual_carbon_avoided_tonnes": co2_t,
            "annual_carbon_value_eur": carbon_val,
            "annual_diesel_litres": round(A["diesel_litres"], 1),
            "annual_transit_diesel_co2_tonnes": round(A["diesel_litres"] * 2.68 / 1000.0, 2),
            "annual_shore_power_kwh": round(A["shore_kwh"], 1),
            "annual_sroi_ratio": sroi,
            "annual_sroi_without_turnover": sroi_noturn,
            "annual_societal_value_eur": round(societal, 2),
            "annual_grant_per_year_eur": round(grant_y, 2),
            "annual_wages_eur": round(A["wages"], 2),
            "annual_payback_years": payback,
            "annual_npv_5yr_eur": round(margin * ann5 - equity, 2),
            "annual_npv_10yr_eur": round(margin * ann10 - equity, 2),
            "breakeven_reboat_share_pct": breakeven_share,
            "monthly_timeseries": monthly,
            "annual_package_turnover_eur": round(A["turnover"], 2),
            "annual_tourism_revenue_eur": round(A["tour"], 2),
            "annual_product_sales_total_eur": round(A["prod_total"], 2),
            "annual_finished_goods_revenue_eur": round(A["prod"], 2),
            "annual_bulk_flakes_revenue_eur": round(A["flakes"], 2),
            "annual_bulk_yarn_revenue_eur": round(A["yarn"], 2),
            "annual_gate_fee_revenue_eur": round(A["gate"], 2),
            "annual_power_cost_eur": round(A["power"], 2),
            "annual_berth_cost_eur": round(A["berth"], 2),
            "annual_labor_cost_eur": round(A["labor"], 2),
            "annual_fuel_cost_eur": round(A["fuel"], 2),
            "annual_maintenance_cost_eur": round(A["maint"], 2),
            "annual_land_logistics_cost_eur": round(A["land"], 2),
            "annual_vessel_cost_eur": round(A["vessel"], 2),
            "annual_insurance_cost_eur": round(A["insur"], 2),
            "annual_land_collection_cost_eur": round(A["collect"], 2),
            "annual_commission_cost_eur": round(A["commission"], 2),
            "annual_overheads_cost_eur": round(A["overheads"], 2),
            "annual_package_units": units_pkg,
            "annual_product_units": units_prod,
            "material_flows": flows,
            "options": opts,
            "capex_breakdown": capex_breakdown,
        }

    def execute_island_scenario(self, config_dict):
        """Single campaign at the island in high season (format of a pilot stay); results go to the JSON export."""
        opts = self._opts(config_dict)
        capex_scenario = config_dict.get("capex_scenario", "Public_Private_Partnership")
        textile_kg = config_dict.get("textile_processed_kg", config_dict["plastic_processed_kg"] * 0.30)
        operational_days = config_dict["operational_days"]
        rev_res = self.simulate_commercial_yields(config_dict["package_sales"], config_dict["plastic_processed_kg"], textile_kg,
                                                  config_dict.get("circular_products_sales"), operational_days, opts, self.season)
        waste_t = rev_res["waste_processed_tonnes"]
        opex_res = self.calculate_campaign_opex(operational_days, config_dict.get("transit_hours", 6.5),
                                                config_dict.get("land_event_mode", False), opts, waste_t,
                                                rev_res["tourism_package_gross_revenue_eur"], operational_days / 365.0)
        capex_res = self.calculate_capex_allocation(capex_scenario)
        grant_y = capex_res["grant_coverage_eur"] / self.capex_amortization_years
        eco = self.evaluate_ecosystem_impact(waste_t, config_dict.get("local_workers_trained", 8), operational_days,
                                             grant_y, rev_res["total_gross_revenue_eur"], opex_res["labor_costs_eur"],
                                             rev_res["gate_fee_revenue_eur"],
                                             rev_res["product_sales_total_eur"] - rev_res["finished_upcycled_goods_revenue_eur"])
        margin = rev_res["total_gross_revenue_eur"] - opex_res["total_operational_opex_eur"]
        net_after = margin - capex_res["annual_amortization_eur"] * (operational_days / 365.0)
        ratio = rev_res["total_gross_revenue_eur"] / opex_res["total_operational_opex_eur"] if opex_res["total_operational_opex_eur"] > 0 else 0.0
        inv = self.calculate_investment_metrics(margin, operational_days, capex_res["net_equity_required_eur"])
        return {
            "Target_Island": self.target_island, "Campaign_Season": self.season, "Tool_Version": TOOL_VERSION,
            "Scenario_Type": "Single campaign after the project (exploitation scenario)",
            "Financial_Performance": {
                "Gross_Revenue_EUR": rev_res["total_gross_revenue_eur"], "Total_OPEX_EUR": opex_res["total_operational_opex_eur"],
                "Net_Campaign_Margin_EUR": round(margin, 2), "Revenue_to_Cost_Ratio_F5": round(ratio, 2),
                "Operating_Status": "Operating Surplus" if ratio >= 1.0 else "Operating Deficit",
                "CapEx_Status": "Profitable (Covers CapEx Amort.)" if net_after >= 0 else f"Deficit (-€{abs(net_after):,.0f} after Amort.)",
                "CapEx_Net_Equity_EUR": capex_res["net_equity_required_eur"],
                "Annual_Amortization_EUR": capex_res["annual_amortization_eur"], "Net_After_CapEx_EUR": round(net_after, 2),
            },
            "OPEX_Breakdown": opex_res, "Revenue_Breakdown": rev_res, "CapEx_Allocation": capex_res, "Investment_Metrics": inv,
            "Ecosystem_Sustainability_KPIs": {
                "Avoided_Disposal_Cost_EUR": eco["avoided_disposal_cost_eur"],
                "Municipal_Savings_F1": eco["municipal_landfill_export_savings_eur"],
                "Social_Value_S3": eco["socio_economic_value_retained_eur"],
                "Carbon_Avoided_E2_Tonnes": eco["logistics_co2_emissions_avoided_tonnes"],
                "Carbon_Economic_Value_EUR": eco["carbon_economic_value_eur"],
                "Total_Societal_Value_EUR": eco["total_societal_value_generated_eur"], "SROI_Ratio": eco["sroi_ratio"],
                "Material_Recycled_E1_KG": rev_res["net_flakes_produced_kg"], "Textile_Yarn_KG": rev_res["net_yarn_produced_kg"],
            },
            "Assumptions": self.build_assumptions_dict(capex_scenario, opts),
        }
