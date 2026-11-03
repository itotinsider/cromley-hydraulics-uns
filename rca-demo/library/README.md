# Copper Canyon Dam: maintenance and reliability document library

Desert River Water & Power Authority (DRWPA), Copper Canyon Dam. Fictional, for training only.

This library holds the documents and records the maintenance and reliability team uses for
root cause analysis on the three generating units. Live and recent process data is on the site
MQTT broker (customer tree `v1.0/DRWPA/CopperCanyon/…`, CH monitoring PLC tree
`v1.0/CH/Fleet/DRWPA/CopperCanyon/<serial>/…`).

| Unit | Functional location | CH serial |
| --- | --- | --- |
| Unit 1 | CCD-U1 | CH-FR-1987-0042 |
| Unit 2 | CCD-U2 | CH-FR-1987-0043 |
| Unit 3 | CCD-U3 | CH-FR-1989-0051 |

## Supplier documents (Cromley Hydraulics)

| File | What it is |
| --- | --- |
| `supplier/CH-DOC-OM-0101_CH-Francis-Canyon_O-and-M-Manual_Rev4.pdf` | Turbine O&M manual: design data, rough zone, bearings, oil limits, cooling, HPU, troubleshooting, CH monitoring PLC, maintenance recommendations |
| `supplier/CH-DOC-DWG-0102_CH-Francis-Canyon_Unit-Schematics_Rev2.pdf` | Three schematic sheets: unit arrangement and sensors, cooling water system, bearing RTD wiring |
| `supplier/CH-SB-2026-03_Service-Bulletin_RTD-Element-B-Connectors.pdf` | Service bulletin on element-B RTD connectors in humid locations |

## DRWPA records (`drwpa/records/`, CSV)

| File | What it is |
| --- | --- |
| `asset-register.csv` | Functional locations (ISO 14224 style hierarchy), serials, criticality, notes |
| `fmeca_ch-francis-unit.csv` | FMECA of the generating unit: failure modes, mechanisms, effects, detection signals (topics), S/O/D, tasks |
| `pm-plan.csv` | Preventive and condition-based maintenance tasks and intervals |
| `work-orders_2021-2026.csv` | CMMS work order history, ISO 14224 failure codes where entered |
| `oil-analysis_2021-2026.csv` | Bearing oil laboratory results per unit and oil pot |
| `moc-register.csv` | Management of change register |
| `shift-log_2026-09_2026-11.csv` | Control room shift log, Sep–Nov 2026 |

## DRWPA procedures (`drwpa/procedures/`, Markdown)

| File | What it is |
| --- | --- |
| `DRWPA-PRO-REL-01_Root-Cause-Analysis-Procedure.md` | RCA triggers, steps, failure coding |
| `DRWPA-FRM-REL-02_RCA-Report-Template.md` | RCA report template |
| `DRWPA-OP-03_Unit-Operation-and-Rough-Zone.md` | Unit operation, rough zone, bypass rules |
| `DRWPA-OP-07_Bearing-Temperature-Alarm-Response.md` | Bearing temperature alarm validation and response |

## Previous RCA reports (`drwpa/rca-reports/`, PDF)

| File | Event |
| --- | --- |
| `RCA-2023-004_U2-TGB-trip-cooling-water-loss.pdf` | Unit 2 TGB trip and pad wipe, March 2023 |
| `RCA-2024-011_U3-thrust-bearing-spurious-temperature-stop.pdf` | Unit 3 stopped on a false thrust temperature, August 2024 |
| `RCA-2025-007_U2-draft-tube-cracks-runner-cavitation.pdf` | Unit 2 draft tube cone cracks and runner cavitation, October 2025 |
