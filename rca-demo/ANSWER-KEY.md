# RCA demo: story bible and answer key (instructor only)

**Do not give this file to the RCA bot.** The bot gets `rca-demo/library/` and the live broker,
nothing else. This file holds the background story, the clues planted in the library, and the
expected outcome per demo scenario, so presenters can check the bot's answer.

Everything here is fictional and made for training only.

## The setting

Copper Canyon Dam is operated by the **Desert River Water & Power Authority (DRWPA)**. The RCA
bot is DRWPA's own tool: it belongs to the plant's maintenance and reliability team. Cromley
Hydraulics (CH) is the supplier of the three turbines; its documents (O&M manual, schematics,
service bulletin) sit in DRWPA's document library as supplier documents.

"Today" in the story is **3 November 2026**.

### People at Copper Canyon Dam

| Name | Role |
| --- | --- |
| Elena Marsh | Plant Manager |
| Ray Okafor | Maintenance Superintendent |
| Priya Nandakumar | Reliability Engineer (since March 2024) |
| Tom Halvorsen | Mechanical Maintenance Engineer (also did reliability work before 2024) |
| Gina Alvarez | Maintenance Planner |
| Dale Whitaker | I&C Lead Technician |
| Luis Ortega, Ben Carver | Mechanical Technicians |
| Nora Fenwick | I&C Technician |
| Marcus Bell, Sofia Reyes, Jake Lindqvist | Shift Supervisors (shifts A, B, C) |
| Karen Doyle | DRWPA System Operations (dispatch and ancillary-services contracts) |

External: **Lars Bergström** (CH field service engineer), **Mesa Lubricant Labs** (oil
analysis), **Desert Bearing Services** (bearing re-babbitting shop).

### Unit history

| Unit | CH serial | Commissioned | Major events |
| --- | --- | --- | --- |
| Unit 1 | CH-FR-1987-0042 | 1987 | Major overhaul 2019; TGB pads re-babbitted by Desert Bearing Services; pad 3 clearance accepted on concession CH-CON-2019-017 |
| Unit 2 | CH-FR-1987-0043 | 1987 | Major overhaul 2014; TGB wipe after cooling loss 2023 (RCA-2023-004); draft-tube cone cracks and runner cavitation 2025 (RCA-2025-007) |
| Unit 3 | CH-FR-1989-0051 | 1989 | Major overhaul 2017; spurious thrust-bearing temperature shutdown 2024 (RCA-2024-011) |

September 2026: CH monitoring PLC retrofit on all three units (dual-element RTDs, vibration,
HPU, cooling). Commissioning punch list partly open.

## Library contents and where the clues are

| File | Clues for |
| --- | --- |
| `supplier/CH-DOC-OM-0101_...O-and-M-Manual_Rev4.pdf` | All: limits, rough zone table, troubleshooting tables |
| `supplier/CH-DOC-DWG-0102_...Schematics_Rev2.pdf` | All: bearing arrangement, cooling circuits (TGB on its own TB circuit), RTD element A/B wiring |
| `supplier/CH-SB-2026-03_...Service-Bulletin.pdf` | G: known moisture issue on CH PLC RTD M12 connectors |
| `drwpa/records/asset-register.csv` | All: hierarchy, serials, maintainable items |
| `drwpa/records/fmeca_ch-francis-unit.csv` | All: hypotheses the bot may test; detection tied to real topics |
| `drwpa/records/pm-plan.csv` | A: TGB oil change 48 months, sampling 6 months (after MOC-2025-004) |
| `drwpa/records/work-orders_2021-2026.csv` | A: deferred U1 TGB resample; G: open U3 gland punch item; C: draft tube repair 2025 |
| `drwpa/records/oil-analysis_2021-2026.csv` | A: U1 TGB tin, TAN and varnish (MPC) trending up, "Caution" Aug 2026 |
| `drwpa/records/moc-register.csv` | A: MOC-2025-004; C: MOC-2026-019 without reliability sign-off |
| `drwpa/records/shift-log_2026-09_2026-11.csv` | G: humid U3 headcover pit; C: regulation-reserve trial on U2 |
| `drwpa/procedures/*.md` | RCA procedure and template; OP-03 rough zone; OP-07 bearing alarm response |
| `drwpa/rca-reports/RCA-2023-004.pdf` | A: earlier TGB event was cooling loss: the bot must rule cooling **out** this time |
| `drwpa/rca-reports/RCA-2024-011.pdf` | G: earlier false alarm from a wiring fault, OP-07 created |
| `drwpa/rca-reports/RCA-2025-007.pdf` | C: same failure mechanism a year earlier, open action |

## Scenario A: TGB bearing degradation (Unit 1, pad 3)

**Instructor station:** `tgb_bearing_degradation`, unit **Unit1**, pad **3** (default),
duration 1,200 s (weeks compressed to ~20 min).

**What the data shows:** CH `Bearings/TGB/PadTemp03` rises from ~64 °C past the CH alarms (75, 85 °C)
to ~98 °C; pads 2 and 4 rise a few K (neighbours, ~18 % coupling); TGB oil rises ~2 K; the customer's
element A (`Powerhouse/Unit1/TurbineGuideBearingTemp`, pad 1) only rises ~4 K and never reaches the
customer alarm (80 °C) or trip (90 °C). TGB shaft vibration rises slightly late in the ramp.
Cooling flows, draft tube and gate position stay normal.

**How the shift found out (recorded history, `history/scenario-A/`):** not from the SCADA. The control
room's U1 TGB indication stayed at ~70 °C with no SCADA alarm. The CH PLC alarms show only in the CH
viewer on a second screen in the control room: no horn, no acknowledge, nobody assigned to watch it.
The pad 3 H alarm (23:54 on 2 Nov) went unseen by shift C and shift A; the 07:13 shift log entry
"No alarms" was written while the viewer listed it. At 09:03 the shift A supervisor saw the red HH
badge while checking Unit 2's vibration for the trial, did the OP-07 checks with I&C on call, reduced
to 34 MW (09:14) and stopped the unit (09:48–09:51). Shift log 09:03–09:55 records this.
- **Planted clue:** the 9 h unseen H alarm and the "No alarms" entry. They point to the latent root
  "CH alarms not in the control room's alarm system", not to operator blame. The HH was found by
  chance (the U2 trial), not by design.

**Expected RCA:**

- **Event:** Unit 1 turbine guide bearing pad 3 overheating (CH PLC alarms TGB_PAD03_H/HH), developing failure.
- **Ruled out (with evidence):** cooling loss (TB flow ~8 L/s, inlet temperature normal; unlike
  RCA-2023-004); sensor fault (neighbouring pads and oil temperature move with it; OP-07 check passes);
  rough-zone operation (gate ~75 %, outside 35–70 %; no draft-tube pulsation); misalignment/unbalance
  (no 2X, 1X stable).
- **Physical root:** loss of oil film on TGB pad 3 (babbitt distress starting), on a pad set
  tighter than tolerance (0.24 mm, concession CH-CON-2019-017) running in oxidising oil (TAN 0.38,
  MPC 28, tin 14 ppm in August 2026, all at "Caution" per the CH manual).
- **Human root:** U1 TGB oil has been at "Caution" since February 2025; each result was handled as
  "monitor" (one resample in September 2025, no oil change). The August 2026 result asked for a
  resample in 30 days; WO-2026-0672 was deferred during the CH retrofit outages and never rescheduled.
- **Latent roots:** MOC-2025-004 extended TGB oil change and sampling intervals for cost reasons and
  cancelled the U1 TGB oil change due in January 2025; it was raised and approved by the same person
  (Ray Okafor), and the reliability engineer's conditional sign-off (keep TGB sampling quarterly) was not
  incorporated; the PM interval now deviates from the CH recommendation (quarterly, max 36 months); no rule to
  escalate "Caution" lab results; customer protection only sees pad 1, so pad 3 is invisible to the
  control room, and the CH viewer that does show it has no annunciation and no owner (the H alarm
  stood unseen for 9 h).
- **Good recommendations:** reduce load and plan a stop for TGB inspection; take an oil sample now;
  restore quarterly TGB sampling; escalation rule for lab "Caution"; bring CH pad-level alarms into
  the control room; review MOC-2025-004 against the FMECA.

## Scenario G: RTD sensor fault (Unit 3, TGB pad 2, drift)

**Instructor station:** `rtd_fault`, unit **Unit3**, tag **Bearings/TGB/PadTemp02**, mode **drift**.

**What the data shows:** CH `Bearings/TGB/PadTemp02` on CH-FR-1989-0051 drifts up to +20 °C, crossing
the CH 75 °C alarm, with quality still GOOD. Pads 1, 3, 4, TGB oil temperature, the customer's element
A and vibration stay flat.

**Expected RCA:**

- **Event:** CH PLC alarm TGB_PAD02_H on Unit 3; no corroborating signals.
- **Key reasoning:** a real pad problem raises its neighbours and the oil (compare scenario A);
  one channel moving alone points to the measurement. OP-07 says: validate before stopping.
- **Physical root:** moisture in the M12 connector / cable gland of the TGB RTD cable to the CH PLC in the humid headcover
  pit junction box (CH-SB-2026-03 describes this).
- **Human root:** retrofit punch item WO-2026-0753 (gland not fully tightened, Unit 3 headcover pit)
  left open at handover.
- **Latent roots:** retrofit acceptance allowed open punch items in wet areas; data quality flag
  only reflects communication, not plausibility; no automatic cross-check of RTD elements.
- **Good recommendations:** do **not** stop the unit (avoid a repeat of RCA-2024-011's 14 h outage);
  dry and reseal the connector, close WO-2026-0753; add a plausibility check (pad vs. neighbours and
  oil) in the CH PLC or edge; check all CH PLC RTD connectors and glands in wet areas.

## Scenario C: AGC parks Unit 2 in the rough zone

**Instructor station:** `agc_rough_zone`, unit **Unit2** (default).

**What the data shows:** Unit 2 parked at ~55 % gate, ~22–23 MW (inside the rough zone ~10–33 MW
at ~106 m net head); draft-tube pulsation at ~1.4 Hz (0.28 × 5 Hz) in the draft-tube waveform;
TGB shaft vibration ~130 µm pp (close to the 140 µm alert); headcover ~2.1 mm/s (normal ~1);
MW swings; TGB pads a few K warmer. Units 1 and 3 carry the rest at ~42 MW, the 105 % limit.
`Plant/MWSetpointReachable` toggles.

**Expected RCA:**

- **Event:** Unit 2 operating in the vortex-rope zone with high vibration and pressure pulsation.
- **Ruled out:** mechanical unbalance (the dominant component is sub-synchronous, not 1X),
  shear pin (status OK), runner crack (no blade-pass change).
- **Physical root:** draft-tube vortex rope from sustained part-load operation.
- **Human root:** the rough-zone bypass was enabled for a regulation-reserve trial (shift log
  2 Nov 2026) on Unit 2, the unit that was damaged by the same mechanism in 2025.
- **Latent roots:** MOC-2026-019 was approved without the reliability sign-off required by OP-03
  rev C (an action from RCA-2025-007); the commercial action from RCA-2025-007 (renegotiate the
  regulation band) is still open; no rough-zone-hours KPI exists yet.
- **Good recommendations:** stop the bypass or move the parked load to a unit outside the rough
  zone; enforce the OP-03 sign-off; implement the rough-zone hours KPI from CH data; close the
  commercial action; inspect Unit 2 draft tube at the next outage.

## Red herrings and noise (on purpose)

- About a third of the corrective work orders have missing or vague failure codes and free-text descriptions.
- Unit 1 TGB pad 4 reads 1–3 K above the other pads (noted at retrofit commissioning and accepted):
  true in the data, normal per the CH manual (fixed pad offsets), and not related to A.
- Unit 3 had a real cooling-water strainer clean in October 2026; irrelevant to G.
- Unit 3's annual inspection is in March, so the open gland punch item ("next U3 outage") has had no
  outage to be done in.
- The 2023 TGB event (cooling loss) is the "obvious" explanation for A; the data rules it out.
