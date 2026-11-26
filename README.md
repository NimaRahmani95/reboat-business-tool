<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/reboat_logo_dark.png">
    <img alt="ReBoat Project Logo" src="assets/reboat_logo.png" height="58">
  </picture>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/eu_funded_en_dark.png">
    <img alt="Funded by the European Union" src="assets/eu_funded_en.png" height="58">
  </picture>
</p>

# ReBoat — Digital Tool for Business Plan and Sustainability (Deliverable D2.3)

Interactive web application developed under **Work Package 2, Task 2.6** (*Business planning and eco-system analysis tool*, Deliverable D2.3) of the Horizon Europe project **ReBoat** (*Circular systemic solution for sustainable tourism in European islands by movable plant on a boat and co-creation with island stakeholders*, **Grant Agreement No. 101182350**).

## Purpose and Capabilities

The **Digital Tool for Business Plan and Sustainability** evaluates the economic viability and local sustainability impact of deploying a modular mobile recycling facility across European island contexts (**Corfu**, **Paxos**, **Lipari**, and **Terceira – Azores**). Over a steady-state post-project operating year (twelve monthly campaigns), the application computes:

- **Revenue forecasting**: operator share of eco-tourism packages, upcycled circular products, bulk recycled plastic flakes, bulk textile yarn, and optional municipal gate fees.
- **Operating costs & break-even**: seasonal crew, harbour berth, maintenance, shore-power electricity, marine transit fuel, optional commercial cost lines, and the exact break-even tourism revenue share (`s*`).
- **Capital & screening metrics**: three capital-funding routes with screening equity payback and 5- and 10-year net present value.
- **Island & public sustainability indicators**: plastic and textile mass diverted under machine throughput limits (`100 kg/h` plastic shredding, `0.5 kg/h` textile spinning line), uncompacted landfill airspace saved, avoided municipal disposal cost net of gate fees, local crew wages, prudent social return ratio, and separate operational fuel and electricity tracking ahead of the full life cycle assessment.
- **Exploratory regional demonstrator (`View 05`)**: illustrative 5 to 10 year archipelago scenarios exploring municipal, tour-operator, and artisan uptake alongside multi-island fleet scheduling and gate-fee trade-offs.

## Dual-Mode User Experience

From the start screen, users choose between two synchronised modes:
1. **Explore directly (5-View Dashboard)**: direct navigation across `01 · Overview`, `02 · Island & public impact`, `03 · Business plan`, `04 · Deliverables and exports`, and `05 · Ecosystem dynamics`.
2. **Guided step-by-step walkthrough (9 Steps)**: field-by-field onboarding with plain-language explanations and collapsible reading guides tailored for non-technical island stakeholders.

## Traceable Exports (`04 · Deliverables and exports`)

Every configured scenario is stamped with a reproducible scenario code and can be exported as:
- **Two-page PDF summary** (`pdf_summary_export.py`)
- **Editable Word executive summary** (`business_summary_export.py`)
- **Eight-sheet live-formula Excel financial model** (`financial_model_export.py`)
- **Structured JSON scenario dataset**

## Repository Structure

| File / Folder | Role |
| --- | --- |
| `app.py` | Streamlit web application, start screen, sidebar controls, and Views 01–05 |
| `guided_mode.py` | Nine-step guided walkthrough and collapsible plain-language view guides |
| `backend.py` | Deterministic twelve-month business planning and sustainability engine |
| `ecosystem_sim.py` | Exploratory multi-year regional ecosystem and fleet-scheduling module |
| `stakeholder_data.py` | Public pilot island profiles, regional cluster definitions, and stakeholder overview |
| `charts.py`, `ui.py`, `plan_labels.py` | Visualisation charts, styling helpers, and shared labels |
| `pdf_summary_export.py`, `business_summary_export.py`, `financial_model_export.py` | Export generators (PDF, Word, live-formula Excel) |
| `assets/` | ReBoat project logos and official European Union funding emblems |
| `tests/verify_d23.py` | Automated verification and regression test suite |

## Local Execution (Authorised Users)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Acknowledgment and Funding

<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/eu_funded_en_dark.png">
    <img alt="Funded by the European Union" src="assets/eu_funded_en.png" height="46">
  </picture>
</p>

This project has received funding from the **European Union's Horizon Europe research and innovation programme** under **Grant Agreement No. 101182350** (*Call HORIZON-CL6-2024-CIRCBIO-01*).

> **Disclaimer**: Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Executive Agency (REA). Neither the European Union nor the granting authority can be held responsible for them.

## Licence and Permission to Use

**All Rights Reserved — Prior Written Permission Required** (see [`LICENSE`](LICENSE)).

This repository is made publicly viewable solely for transparency and review of Deliverable D2.3. Using, running, copying, modifying, distributing, or deploying the source code or application requires prior written permission from **Politecnico di Milano (POLIMI)** on behalf of the **ReBoat Consortium**, without prejudice to the rights of the European Union and the European Research Executive Agency (REA) under Grant Agreement No. 101182350.
