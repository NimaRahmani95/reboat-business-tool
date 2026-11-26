"""
One vocabulary for the cockpit, the Word summary and the Excel model, so a line
called "Operator crew" on screen is "Operator crew" in both files.

Each entry maps an output key of ReBoatDigitalBrain.calculate_annual_business_plan()
to the label every deliverable uses.
"""

REVENUE_LINES = [
    ("annual_tourism_revenue_eur", "ReBoat share of tourism packages"),
    ("annual_finished_goods_revenue_eur", "Upcycled products"),
    ("annual_bulk_flakes_revenue_eur", "Recycled plastic flakes"),
    ("annual_bulk_yarn_revenue_eur", "Recycled yarn"),
    ("annual_gate_fee_revenue_eur", "Gate fee for treated waste"),
]

OPEX_LINES = [
    ("annual_labor_cost_eur", "Operator crew"),
    ("annual_berth_cost_eur", "Berth and port fees"),
    ("annual_maintenance_cost_eur", "Maintenance and consumables"),
    ("annual_power_cost_eur", "Shore power"),
    ("annual_fuel_cost_eur", "Transit fuel"),
    ("annual_vessel_cost_eur", "Vessel charter"),
    ("annual_insurance_cost_eur", "Insurance"),
    ("annual_land_collection_cost_eur", "Collection on land"),
    ("annual_commission_cost_eur", "Sales commissions"),
    ("annual_overheads_cost_eur", "Overheads"),
]

# Lines that are shown only when they are not zero (new cost lines and the gate fee default to zero).
OPTIONAL_LINES = {"annual_gate_fee_revenue_eur", "annual_vessel_cost_eur", "annual_insurance_cost_eur",
                  "annual_land_collection_cost_eur", "annual_commission_cost_eur", "annual_overheads_cost_eur"}

SCENARIO_NOTE = ("Operating year after the project (exploitation scenario) — steady-state planning figures; "
                 "not income of the EU-funded pilot demonstrations.")

EU_FUNDING_TEXT = "Funded by the European Union (Horizon Europe Grant Agreement No. 101182350)."
EU_DISCLAIMER = (
    "Funded by the European Union. Views and opinions expressed are however those of the author(s) only "
    "and do not necessarily reflect those of the European Union or the European Research Executive Agency (REA). "
    "Neither the European Union nor the granting authority can be held responsible for them."
)

REVENUE = "Revenue"
OPEX = "Operating cost"
MARGIN = "Operating margin"
AMORT = "CapEx amortisation (10-year straight line)"
NET = "Net result after amortisation"

KPI = {
    "ratio": "Revenue ÷ operating cost",
    "net": NET,
    "payback": "Equity payback",
    "npv": "5-year NPV at 8%",
    "npv10": "10-year NPV at 8%",
    "breakeven": "ReBoat share needed to break even",
    "waste": "Waste diverted",
    "co2": "Gross waste-transport CO₂ avoided",
    "diesel_co2": "Indicative transit diesel CO₂",
    "freight": "Municipal saving (avoided disposal cost, net of gate fee)",
    "sroi": "Social return (SROI)",
    "sroi_noturn": "SROI (excl. turnover)",
    "airspace": "Landfill space saved",
    "wages": "Local wages",
    "societal": "Societal value",
}

PACKAGES = [
    ("Day_Trip", "Day trip"),
    ("Short_Trip", "Short trip"),
    ("Slow_Trip", "Slow trip"),
    ("Medium_Slow", "Medium-slow stay"),
    ("Deep_Slow", "Deep-slow stay"),
]

PRODUCTS = [
    ("injection_molded_goods", "Injection-moulded goods"),
    ("custom_3d_printed_artifacts", "3D-printed artefacts"),
    ("thermo_pressed_furniture_panel", "Pressed furniture panels"),
    ("artisanal_woven_textiles", "Woven textiles"),
    ("plied_yarn_spools", "Yarn spools"),
]


def month_label(m: dict) -> str:
    """English three-letter month, used by every chart and table."""
    return m["month_name"][:3]


def visible(lines, values):
    """Drop optional lines whose value is zero."""
    return [(k, lbl) for k, lbl in lines if k not in OPTIONAL_LINES or abs(values.get(k, 0) or 0) > 0.005]
