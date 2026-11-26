"""
ReBoat Task 2.6 - Pilot Regional Ecosystem, Stakeholder Mapping & Tourism Strategy (Task 4.1 Merged)
Lead Partner: Politecnico di Milano (POLIMI)
Project: ReBoat (HORIZON-CL6-2024-CIRCBIO-01 - Grant Agreement 101182350)
Deliverable: D2.3 & T4.1 Integration
"""

PILOT_PROFILES = {
    "Corfu": {
        "region": "Ionian Islands (Greece)",
        "task_ref": "Task 5.3 Pilot Demonstration",
        "lead_partner": "Ionian Regional Pilot Team",
        "population_permanent": 104371,  # GA Part B Table 1 (2011 census)
        "peak_tourist_multiplier": "3.8x (July-August)",
        "waste_generation_peak_t_day": 340,
        "landfill_status": "Severe saturation; mainland ferry export required",
        "berth_port": "Port of Corfu (Kerkyra)",
        "grid_connection": "400V 3-phase shore connection available at commercial pier",
        "tourism_governance": "Municipality of Central Corfu & Inter-Municipal Port Authority",
        "sustainable_tourism_strategy": "Carrying-capacity management for cruise visitors, promotion of UNESCO cultural routes, and zero-waste port certifications.",
        "protected_areas": "UNESCO World Heritage Old Town, Natura 2000 GR2230002 (Antinioti Lagoon), Paleokastritsa Marine Zone.",
        "tourist_provenance": "UK (38%), Germany (22%), France (14%), Greece Domestic (12%), Italy (8%), Other (6%)",
        "traveler_categories": "Couples (42%), Families with children (34%), Eco-tourists/Youth (16%), Living Lab residencies (8%)",
        "stay_duration": "Day-trippers (22%), Short trip 1-3 days (28%), 4-7 days (38%), >7 days (12%)",
        "key_pois": "Old Fortress Kerkyra, Achilleion Palace, Paleokastritsa Bay, Mon Repos, Canal d'Amour, Gouvia Marina",
        "tourism_taxes_levies": "€1.50 - €4.00/night climate resilience levy, quayside commercial cruise passenger fee",
        "transport_modes": "International flights (74%), Ferry from Igoumenitsa (22%), Private yachts (4%)",
    },
    "Paxos": {
        "region": "Ionian Islands (Greece)",
        "task_ref": "Task 5.3 Satellite Pilot Node",
        "lead_partner": "Ionian Regional Pilot Team",
        "population_permanent": 2300,
        "peak_tourist_multiplier": "7.5x (August)",
        "waste_generation_peak_t_day": 28,
        "landfill_status": "No local landfill; 100% waste shipped to Corfu/mainland",
        "berth_port": "Gaios Port",
        "grid_connection": "Requires portable distribution panel / municipal shore box",
        "tourism_governance": "Municipality of Paxos & Gaios Port Committee",
        "sustainable_tourism_strategy": "Ultra-low-impact boutique yachting and eco-tourism, preservation of ancient olive groves and marine caves.",
        "protected_areas": "Natura 2000 Marine Reserve Paxos-Antipaxos (GR2230004), Monk Seal (Monachus monachus) sanctuary.",
        "tourist_provenance": "Italy (42%), UK (28%), Greece (16%), France (8%), Other (6%)",
        "traveler_categories": "Yacht charters (48%), Couples (32%), Families (15%), Slow-travel researchers (5%)",
        "stay_duration": "Day-trippers from Corfu (45%), 1-3 days (20%), 4-7 days (25%), >7 days (10%)",
        "key_pois": "Gaios Harbor, Lakka Bay, Loggos Fishing Village, Tripitos Arch, Antipaxos Voutoumi Beach",
        "tourism_taxes_levies": "Marina transit docking fee, municipal environmental sanitation surcharge",
        "transport_modes": "Hydrofoil / sea taxi from Corfu (68%), Private sailing yachts (32%)",
    },
    "Lipari": {
        "region": "Aeolian Islands (Sicily, Italy)",
        "task_ref": "Task 5.2 Pilot Demonstration",
        "lead_partner": "Aeolian Regional Pilot Team",
        "population_permanent": 12800,
        "peak_tourist_multiplier": "5.2x (July-August)",
        "waste_generation_peak_t_day": 65,
        "landfill_status": "Restricted maritime transport to Milazzo/mainland Sicily",
        "berth_port": "Marina Lunga / Port of Lipari",
        "grid_connection": "Municipal pier with 63A/125A 400V shore sockets",
        "tourism_governance": "Comune di Lipari & Autorità di Sistema Portuale del Mare di Sicilia Orientale",
        "sustainable_tourism_strategy": "UNESCO Volcanic Heritage preservation, phasing out single-use plastics, and seasonal hiking/marine circuits.",
        "protected_areas": "UNESCO World Heritage Volcanic Archipelago, Isola di Lipari Marine Natura 2000 site.",
        "tourist_provenance": "Italy Domestic (52%), Germany (18%), France (14%), UK (8%), USA/Other (8%)",
        "traveler_categories": "Couples (40%), Outdoor & trekking groups (28%), Families (22%), Sailing tourists (10%)",
        "stay_duration": "Day excursions from Sicily (35%), 1-3 days (30%), 4-7 days (25%), >7 days (10%)",
        "key_pois": "Lipari Castle & Archaeological Museum, Canneto Beach, Valle Muria, Pumice Quarries, Marina Corta",
        "tourism_taxes_levies": "Contributo di sbarco (€5.00 entry fee per disembarking visitor), municipal tourist tax",
        "transport_modes": "Hydrofoil (Aliscafo) from Milazzo/Messina (82%), Ferry/Ship (14%), Private boats (4%)",
    },
    "Terceira": {
        "region": "Autonomous Region of the Azores (Portugal)",
        "task_ref": "Task 5.4 Pilot Demonstration (April–May 2028)",
        "lead_partner": "Azores Regional Pilot Team",
        "population_permanent": 53234,  # Portuguese Census 2021 — Terceira Island (INE)
        "peak_tourist_multiplier": "June–August peak (>100,000 tourists/year, GA §1.2.3)",
        "waste_generation_peak_t_day": 95,  # Estimated island share from archipelago 149,741 t/yr (GA §1.2.3)
        "landfill_status": "On-island treatment (Azores 2022: 32% recycled, 59% incinerated, 7% composted, 2% landfilled; GA)",
        "berth_port": "Angra do Heroísmo (Terceira)",
        "grid_connection": "400V 3-phase shore connection under confirmation with Portos dos Açores",
        "tourism_governance": "Regional Secretariat for Environment & Portos dos Açores",
        "sustainable_tourism_strategy": "Carnival and cultural events from May to October (e.g. Angrajazz) and water sports, used to showcase the co-creation results (GA).",
        "protected_areas": "Angra do Heroísmo historic centre (UNESCO World Heritage); Monte Brasil & coastal protected zones.",
        "tourist_provenance": "Mainland Portugal, Spain, Germany, UK, North America (detailed pilot survey pending T5.4).",
        "traveler_categories": "Eco-tourists, cultural & nature visitors, nautical crews, living-lab participants.",
        "stay_duration": "Short break 1–3 days, 4–7 day stays and working-holiday residencies (WP4 typology).",
        "key_pois": "Angra do Heroísmo historic centre, Monte Brasil",
        "tourism_taxes_levies": "Port berth & municipal concession terms under review with Portos dos Açores.",
        "transport_modes": "Lajes Airport (TER) regional/international flights and inter-island maritime ferries.",
    },
}

# Archipelago clusters grounded in GA Part B §1.2.3 (pp. 130–131) & WP4 pricing note
ARCHIPELAGO_CLUSTERS = {
    "Ionian": {
        "name": "Ionian Islands (Greece)",
        "ga_msw_note": "140,394 t/yr regional MSW across the Ionian archipelago (207,855 residents); ~18% recycled, ~80% landfilled.",
        "islands": [
            {"island": "Corfu", "population": 104371, "annual_msw_t": 70496, "plastic_base": 5500.0,
             "disposal_cost": 150.0, "berth_fee": 300.0, "transit_hrs": 6.5, "is_anchor": True},
            {"island": "Paxos", "population": 2300, "annual_msw_t": 2100, "plastic_base": 5040.0,
             "disposal_cost": 150.0, "berth_fee": 250.0, "transit_hrs": 2.0, "is_anchor": False},
            {"island": "Lefkada", "population": 23693, "annual_msw_t": 16003, "plastic_base": 4200.0,
             "disposal_cost": 150.0, "berth_fee": 270.0, "transit_hrs": 8.0, "is_anchor": False},
            {"island": "Kefalonia-Ithaki", "population": 39032, "annual_msw_t": 26363, "plastic_base": 4800.0,
             "disposal_cost": 150.0, "berth_fee": 280.0, "transit_hrs": 10.0, "is_anchor": False},
            {"island": "Zakynthos", "population": 40759, "annual_msw_t": 27530, "plastic_base": 5000.0,
             "disposal_cost": 150.0, "berth_fee": 290.0, "transit_hrs": 11.0, "is_anchor": False},
        ],
    },
    "Aeolian": {
        "name": "Aeolian Islands (Sicily, Italy)",
        "ga_msw_note": "7 volcanic islands, 15,021 permanent residents, up to 450,000 visitors/yr; minor islands ship waste at 100–250 €/t.",
        "islands": [
            {"island": "Lipari", "population": 12800, "annual_msw_t": 4280, "plastic_base": 5040.0,
             "disposal_cost": 150.0, "berth_fee": 280.0, "transit_hrs": 12.0, "is_anchor": True},
            {"island": "Salina", "population": 2221, "annual_msw_t": 1100, "plastic_base": 3200.0,
             "disposal_cost": 180.0, "berth_fee": 240.0, "transit_hrs": 1.5, "is_anchor": False},
            {"island": "Vulcano", "population": 1200, "annual_msw_t": 850, "plastic_base": 2800.0,
             "disposal_cost": 200.0, "berth_fee": 230.0, "transit_hrs": 1.0, "is_anchor": False},
            {"island": "Filicudi", "population": 250, "annual_msw_t": 300, "plastic_base": 1800.0,
             "disposal_cost": 220.0, "berth_fee": 200.0, "transit_hrs": 3.0, "is_anchor": False},
        ],
    },
    "Azores": {
        "name": "Azores Archipelago (Portugal)",
        "ga_msw_note": "149,741 t archipelago MSW (2022): 32% recycled, 59% incinerated, 7% composted, 2% landfilled.",
        "islands": [
            {"island": "Terceira", "population": 53234, "annual_msw_t": 42000, "plastic_base": 8500.0,
             "disposal_cost": 50.0, "berth_fee": 400.0, "transit_hrs": 48.0, "is_anchor": True},
            {"island": "Faial", "population": 14334, "annual_msw_t": 11500, "plastic_base": 4200.0,
             "disposal_cost": 90.0, "berth_fee": 300.0, "transit_hrs": 6.5, "is_anchor": False},
            {"island": "Pico", "population": 13883, "annual_msw_t": 10800, "plastic_base": 4000.0,
             "disposal_cost": 100.0, "berth_fee": 280.0, "transit_hrs": 5.5, "is_anchor": False},
            {"island": "São Jorge", "population": 8373, "annual_msw_t": 6500, "plastic_base": 3000.0,
             "disposal_cost": 110.0, "berth_fee": 250.0, "transit_hrs": 4.0, "is_anchor": False},
        ],
    },
}


def get_archipelago_for_island(island_name: str) -> str:
    if island_name in ("Corfu", "Paxos"):
        return "Ionian"
    if island_name in ("Lipari", "Filicudi"):
        return "Aeolian"
    if island_name == "Terceira":
        return "Azores"
    return "Ionian"

STAKEHOLDER_ROWS = [
    {
        "stakeholder_group": "Island Municipalities & Mayors",
        "primary_interest": "Landfill mitigation, zero-waste compliance, and local green job creation",
        "reboat_touchpoint": "Quayside mobile demanufacturing concessions and educational Living Labs",
        "value_exchange": "Municipal savings on mainland waste shipping fees; local material valorization",
        "reboat_kpi": "Annual Municipal Savings (EUR), Waste Diverted (Tonnes), and Public SROI",
    },
    {
        "stakeholder_group": "Port & Maritime Authorities",
        "primary_interest": "Port circularity, green berth infrastructure, and clean harbor waters",
        "reboat_touchpoint": "Quayside container footprint allocation, 125A shore power, and vessel berthing",
        "value_exchange": "Enhanced green port credentials, maritime litter reduction, and plant-compliant port utilities",
        "reboat_kpi": "Coincident Power Load (52 kW, Plant engineering Scenario B), Safe Floor Loading, and Zero Discharges",
    },
    {
        "stakeholder_group": "Local Tourism Operators & Hoteliers",
        "primary_interest": "Differentiating tourism offering with authentic eco-experiences and branded circular products",
        "reboat_touchpoint": "D4.1 Tourism Packages (Day, Short, Slow, Deep Slow) and Upcycled Design Goods Catalog",
        "value_exchange": "High-margin experiential tourist ticket commissions and branded circular interior panels",
        "reboat_kpi": "Tourism Package Revenue, Passenger Capacity, and High-Season Operating Margins",
    },
    {
        "stakeholder_group": "Marine Leisure & Fishing Communities",
        "primary_interest": "Responsible disposal of end-of-life nets, ropes, and boating composites without penalties",
        "reboat_touchpoint": "Port collection bins, C1 intake sorting, and C3 textile sliver reprocessing",
        "value_exchange": "Free/discounted drop-off for maritime gear; circular recycled marine wear returned",
        "reboat_kpi": "Kilograms of End-of-Life Gear Recovered, Polymer Flake Purity, and Net Yarn Output",
    },
    {
        "stakeholder_group": "European Commission & Horizon Europe",
        "primary_interest": "Scalable circular bioeconomy solutions, systemic island decarbonization, and bankability",
        "reboat_touchpoint": "Deliverable D2.3 Digital Decision Tool, Aggregate Plant Planning Baselines, and Task 2.6 SROI Engine",
        "value_exchange": "Demonstration of scalable mobile bioeconomy solutions; measurable decarbonization",
        "reboat_kpi": "SROI Ratio, Avoided CO2e (Tonnes), and CapEx Grant-to-Equity Leverage",
    },
]


def get_pilot_profile(island_name):
    return PILOT_PROFILES.get(island_name, PILOT_PROFILES["Corfu"])


def get_stakeholders_for_island(island_name):
    profile = get_pilot_profile(island_name)
    rows = []
    for row in STAKEHOLDER_ROWS:
        entry = dict(row)
        entry["pilot_region"] = profile["region"]
        entry["local_lead"] = profile["lead_partner"]
        rows.append(entry)
    return rows
