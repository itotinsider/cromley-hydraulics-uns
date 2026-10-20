# Cromley Hydraulics – Demo Environment Design Basis

Oct 20, 2026 · @Willem

## Summary

Cromley Hydraulics (CH) is the third ITOT.Academy environment: a small, fictional hydropower dam whose three CH turbines publish clean, well-structured data to one local Mosquitto broker, over MQTT only. Haltenberg teaches DCS + OPC UA; Sweet Harmony teaches a plant-owner UNS over MQTT. CH teaches the machine-builder view: an asset-centric OEM data model next to the customer's own tree, rich enough for edge vendors to show predictive maintenance on it.

**The story.** CH has 75 years of dam hydraulics experience and an engineering-first culture. Its equipment used to be delivered, integrated into the customer's control system and forgotten. CH now fits every major turbine with a modern PLC that speaks MQTT, to move from reactive to proactive maintenance and to explore a new, data-driven business model.

**In scope**

- Dam simulator (reservoir, intake, spillway, bottom outlet, three generating units) publishing the customer tree on the local broker.
- Dam SCADA screens that read from and send commands to the broker over MQTT.
- Simulated CH turbine PLCs publishing the OEM tree: 1 s process data plus periodic raw waveform blocks.
- Instructor station with hidden fault scenarios, Node-RED, MQTT Explorer, hub page, wiki and a tested inventory.

**Out of scope (handled by the edge / IIoT vendors in the next step)**

- Edge devices and their analytics (FFT, orbits, models).
- Transport beyond the local broker, cloud platforms, buffering and store-and-forward.
- Security: TLS, certificates, ACLs, segmentation, data diodes.
- Device and fleet management, consent filtering.

&#91;embedded content: architecture · simulators and tools on one broker, vendor scope dashed\]

The simulators and tools all talk to one Mosquitto broker; the dashed box is what edge vendors add in the next step.

## Fit with the existing environments

CH reuses the conventions of [Haltenberg](https://github.com/itotinsider/haltenberg-chemische-werke-uns) and [Sweet Harmony](https://github.com/itotinsider/sweet-harmony-treats-uns), but shifts the lesson from plant data to machine-builder data.

| Aspect | Haltenberg (HCW) | Sweet Harmony (SHT) | Cromley Hydraulics (CH) |
| --- | --- | --- | --- |
| Story | Air separation unit run by a DCS | Industrial bakery, many PLCs/HMIs/SCADAs | Machine builder monitoring its turbines at a customer dam |
| Connectivity | Modbus TCP plant to DCS, OPC UA out | MQTT (Mosquitto) | MQTT only, one local Mosquitto |
| Namespace | OPC UA address space | ISA-95 `v1.0/SHT/Munich/...` + `_RAW` feed | Customer ISA-95 tree + CH asset-centric tree on the same broker |
| Payload | OPC UA nodes | `{value, unit, timestamp}` | Same, plus `quality` and `seq`; waveform blocks for vibration |
| Training hook | Instructor station, hidden faults | Hidden anomaly injection | Instructor station, hidden machine faults on slow and fast timescales |

**Conventions to reuse:** demo-only disclaimer, one-command `docker compose up -d --build`, hub page grouped by ISA-95 level, ISA-101 grey HMI, hidden fault injection, Node-RED and MQTT Explorer pre-configured, code-tested `inventory/`, `CLAUDE.md` and wiki, `v1.0/` versioned topic roots.

**Ports** (so all three environments can run side by side):

| Service | Port |
| --- | --- |
| Hub page + dam SCADA | 8120 |
| Instructor station | 8121 |
| CH asset viewer (optional) | 8122 |
| Mosquitto | 1884 |
| Node-RED | 1881 |
| MQTT Explorer | 4001 |

## CH product portfolio

CH is modelled on real hydro OEMs (Andritz, Voith, GE Vernova, Litostroj) and covers both electromechanical and hydromechanical equipment. The Francis turbines are the focus of the environment; the other lines add context and optional data.

| CH product line | Role in the dam | Monitoring value in the demo |
| --- | --- | --- |
| CH-Francis "Canyon" vertical Francis turbines (20–700 m head) | Main generating units, flow set by wicket gates | Flagship: bearings, vibration, draft-tube pulsation, efficiency |
| CH-Kaplan "Riverline" (low head) | Run-of-river and re-regulating dams | Blade/gate cam, hub oil leaks (optional second site) |
| CH-Pelton "Highpeak" (high head) | Station-service units | Needle and deflector position, erosion |
| CH-Gov governors + hydraulic power units (HPUs) | Speed/load control through servomotors | Pump duty, pressure decay, oil condition |
| CH-Valve spherical and butterfly inlet valves | Isolation upstream of each spiral case | Open/close times, seal leakage |
| CH-Gate spillway gates (drum, radial, vertical lift, flap) and intake gates | Flood passage, unit isolation | Position, hoist load and skew |
| CH-Hoist gate hoists and hydraulic cylinders | Drive intake, spillway and emergency gates | Cylinder drift, travel time, pump wear |
| CH-Release jet-flow gates and dispersion valves | Outlet works that bypass the turbines | Position, cavitation, vibration |
| CH-Rake trash racks and rakers | Intake towers | Rack differential pressure (clogging) |
| CH-Aux lube oil, cooling water, brakes/jacking, shaft-seal water | Unit auxiliaries | The richest predictive-maintenance data |

Generator protection, excitation and the switchyard come from other vendors and stay in the customer tree only.

## Copper Canyon Dam

Copper Canyon Dam is a small, fictional hydropower dam with one reservoir, one intake, one penstock, three CH turbines, one spillway and one bottom outlet. That is the minimum needed to explain how a dam works. It is operated by the fictional Desert River Water & Power Authority (DRWPA). All figures are demo assumptions, in metric units.

**Water path:** reservoir → intake (trash rack, intake gate) → penstock → inlet valve → spiral case → wicket gates → runner → draft tube → river. Gross head = reservoir level − tailwater level. Power ≈ ρ · g · Q · H · η.

&#91;embedded content: Copper Canyon water paths · spillway, powerhouse, bottom outlet\]

| Component | Copper Canyon | What it does | CH equipment? |
| --- | --- | --- | --- |
| Dam | Concrete gravity dam, crest at 425 m a.s.l. | Holds back the reservoir | No |
| Reservoir | Operating range 385–420 m a.s.l. | Stores water for generation and flood control | No |
| Intake | 1 intake with trash rack and intake gate | Lets water into the penstock; the gate closes it in an emergency | Gate, rack |
| Penstock | 1 steel penstock, 5.5 m diameter, branching to 3 units | Carries water to the powerhouse | No |
| Inlet valves | 1 butterfly valve per unit | Isolates a unit from the penstock | Yes |
| Generating units | 3 × 40 MW vertical Francis (Unit 1–3), 300 rpm, \~45 m³/s each | Turns water into electricity | Yes (turbine, governor, HPU) |
| Tailwater | \~305 m a.s.l. | Gives 80–115 m gross head, 100 m rated | No |
| Spillway | 1 spillway with 2 radial gates, \~2,000 m³/s | Releases flood water so the dam is never overtopped | Gates and hoists |
| Bottom outlet | 1 fixed-cone valve, \~50 m³/s | Keeps the minimum river flow when the units are stopped | Yes |
| Grid | 1 line at 150 kV, 50 Hz | Exports power; the grid operator sends MW setpoints | No |

**How it is operated**

- The plant has two purposes: generating power at peak hours and keeping room in the reservoir for floods.
- The grid operator sends a plant MW setpoint; the plant controller splits it over Units 1–3 and avoids each unit's rough zone.
- At least 10 m³/s must always flow to the river: through a running unit or the bottom outlet.
- The spillway gates only open when the reservoir approaches 420 m a.s.l.

The CH column shows CH-supplied equipment. Only the three generating units get the new CH PLC that publishes into the CH tree; everything else exists only in the customer tree.

## Turbine operation, control and instrumentation

A Francis turbine's power is set by the wicket-gate opening, which the governor moves through hydraulic servomotors fed by an HPU. The simulator needs a simple governor (PID with droop), a unit state machine and a thermal and vibration model per unit.

**Turbine types**

- **Francis** (medium to high head): flow enters radially through spiral case and wicket gates, leaves axially into the draft tube. Efficiency falls quickly below \~50% gate.
- **Kaplan** (low head): adjustable runner blades on a cam with the wicket gates; flat efficiency curve.
- **Pelton** (high head): needles set the flow; deflectors cut the jet on load rejection.

**Governor (Reclamation FIST 2-3)**

- Permanent speed droop usually 5%: a 1% speed change gives a 20% gate change.
- Gate closing time is set per site from a transient study; faster closure lowers overspeed but raises penstock pressure.
- HPU accumulator sized for 5 full servo strokes; low-pressure trip at 2 strokes left.
- On the grid the governor follows MW setpoints; a plant controller splits AGC setpoints across units and avoids rough zones.

**Start-up sequence**

1. Permissives: HPU pressure OK, oil levels OK, cooling water flowing, brakes released, inlet valve open.
2. Open gates to break-away, governor brings the unit to speed-no-load.
3. Field flash and excitation to rated voltage.
4. Auto-synchronise (voltage, frequency, phase) and close the breaker.
5. Ramp to the MW setpoint.

**Shutdown:** unload → open breaker → close gates → de-excite → brakes at low speed → standstill. **Emergency stop** (latched, manual reset) on overspeed, electrical protection, low governor oil pressure or high bearing temperature.

**Operating zones (Francis):** best efficiency at \~80–90% of rated flow. At part load (\~40–80% of BEP flow) a draft-tube vortex rope forms, with pressure pulsations at 0.2–0.4 × runner frequency. Cavitation risk rises at low tailwater, high head and off-design operation.

**Instrumentation per unit** (demo values; real setpoints are OEM- and site-specific)

| Group | Measurements | Typical / demo range |
| --- | --- | --- |
| Speed | Shaft speed, keyphasor | 300 rpm (demo assumption, 1X = 5 Hz) |
| Governor / HPU | Gate position and setpoint, accumulator pressure, sump level, pump status and starts, oil temp, filter ΔP | 0–100% gate; 40–64 bar; 30–50 °C |
| Bearings | Thrust, upper/lower generator guide and turbine guide pad temps, oil temps and levels | Pads normally ≤ 80 °C, oil bath 50–60 °C |
| Cooling | Cooling water flow per circuit, inlet/outlet temps | Inlet 10–25 °C, seasonal |
| Vibration | Shaft displacement X/Y per guide bearing, headcover acceleration | Tens to a few hundred µm p-p |
| Hydraulics | Spiral case, headcover and draft-tube pressure, tailwater | Draft-tube pulsation is the key signal |
| Generator | MW, MVAr, V, I, Hz, stator winding temps, air gap | Stator \~60–110 °C under load |
| Seals | Shaft-seal water flow, headcover sump pump starts | — |

Vibration limits per [ISO 20816-5](https://www.iso.org/standard/67919.html); hydro condition monitoring guidance in [ISO 19283](https://cdn.standards.iteh.ai/samples/64262/c80c276ce28a4731b51e4a9b3f304c9d/ISO-19283-2020.pdf). Governor values from [Reclamation FIST 2-3](<https://www.usbr.gov/power/data/fist/FIST_2-3_(1-2021).pdf>).

## Dam SCADA over MQTT

The dam SCADA is a web HMI that subscribes to the customer tree on the local broker and sends operator commands back as MQTT command topics. Real dams use IEC 61850, DNP3 or IEC 60870-5-104 here; in this environment everything, including the grid operator's MW setpoint, is an MQTT topic.

**Screen set** (ISA-101 style, like Sweet Harmony's modern HMI)

1. Plant overview: reservoir and tailwater level, head, total MW, river flow, status of Units 1–3, spillway and bottom outlet.
2. Reservoir and spillway: level against operating limits, inflow, spillway gate positions and flow.
3. Unit detail (Unit 1–3): mimic from inlet valve to draft tube, start/stop state, gate position, MW, bearings, cooling.
4. Governor and HPU.
5. Alarms and events, trends.

**Customer tree** (prefix `v1.0/DRWPA/CopperCanyon/`)

| Area / module | Tags |
| --- | --- |
| `Reservoir` | `Level` (m a.s.l.), `Inflow` (m³/s) |
| `River` | `TailwaterLevel` (m a.s.l.), `Flow` (m³/s) |
| `Plant` | `GrossHead` (m), `TotalMW`, `MWSetpoint`, `GridFrequency` (Hz) |
| `Intake` | `GatePosition` (%), `TrashRackDP` (m) |
| `Penstock` | `Pressure` (bar) |
| `Spillway/Gate01..02` | `Position` (%), `Flow` (m³/s) |
| `BottomOutlet` | `ValvePosition` (%), `Flow` (m³/s) |
| `Powerhouse/Unit1..3` | `State`, `BreakerClosed`, `MW`, `GatePosition` (%), `Speed` (rpm), `Flow` (m³/s), `InletValveOpen`, `ActiveAlarms` |

**Commands** use a `Cmd` branch next to the measured values, for example `v1.0/DRWPA/CopperCanyon/Powerhouse/Unit1/Cmd/Start`, `.../Unit1/Cmd/MWSetpoint`, `.../Spillway/Gate01/Cmd/Position`, and `.../Plant/Cmd/MWSetpoint` for the simulated grid operator. The simulator subscribes to `Cmd` and publishes the result on the measured topics.

## CH turbine PLC data model

Each CH turbine has its own simulated CH PLC that publishes an asset-centric tree to the same local broker, at about 7 KB/s per turbine. It reads a few context values from the customer tree (subscribe only) and never writes into it.

**CH tree:** `v1.0/CH/Fleet/<CustomerId>/<SiteId>/<AssetSerial>/<Subsystem>/<Component>/<Metric>`

```
v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/Bearings/TGB/PadTemp01
v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/Vibration/TGB/ShaftX/Overall_um_pp
v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/Vibration/TGB/ShaftX/Waveform
v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/_meta/Nameplate        (retained)
v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/Events/Alarm
```

The tree is organised by serial number because that is how a machine builder thinks: the serial stays the same when the customer renames "Unit 1" or the unit is refurbished. The customer's unit name lives in `_meta/Nameplate`.

**Process payload** (Sweet Harmony format plus quality and sequence):

```json
{"value": 61.4, "unit": "°C", "timestamp": "2026-10-20T12:00:00.000Z", "quality": "GOOD", "seq": 128734}
```

**Process tags per turbine** (published every 1 s)

| Subsystem | Tags |
| --- | --- |
| `Context` (copied from customer tree) | `MW`, `MVAr`, `GatePosition_pct`, `NetHead_m`, `Speed_rpm`, `UnitState`, `TailwaterLevel_m` |
| `Bearings/Thrust` | `PadTemp01..06`, `OilBathTemp`, `OilLevel`, `HPLiftPressure` |
| `Bearings/UGB`, `/LGB`, `/TGB` | `PadTemp01..04`, `OilTemp`, `OilLevel` |
| `Cooling` | `WaterInletTemp`, `WaterFlow_TB`, `WaterFlow_GB`, `WaterFlow_AirCoolers`, `OilCoolerOutletTemp` |
| `Governor/HPU` | `AccumulatorPressure`, `SumpLevel`, `OilTemp`, `Pump1Running`, `Pump2Running`, `PumpStartsPerHour`, `FilterDP`, `ServoPositionA`, `ServoPositionB`, `GateSetpoint` |
| `Turbine` | `SpiralCasePressure`, `HeadcoverPressure`, `DraftTubePressure` (mean), `ShaftSealWaterFlow`, `HeadcoverSumpPumpStarts`, `ShearPinStatus`, `WicketGateBreakawayAlarm` |
| `Vibration` (simple overall values only) | Per bearing X/Y `Overall_um_pp`; headcover `Vel_mm_s_rms` |
| `Generator` | `StatorTemp01..06`, `AirGapMin_mm` |
| `Counters` | `Starts`, `RunHours`, `EmergencyStops`, `LoadRejections` |

**Waveform blocks (reduced for the demo)**

The PLC does no spectral analysis; it publishes raw blocks so edge vendors can run FFT, orbit and envelope analysis themselves. Window lengths are long enough to resolve 1X (5 Hz) and the vortex rope (1–2 Hz).

| Signal | Block | Published | Size (approx.) |
| --- | --- | --- | --- |
| Shaft displacement X/Y at UGB, LGB, TGB (6 channels) | 4 s at 1 kS/s = 4,000 samples | Every 30 s + on alarm | \~30 KB per channel |
| Draft-tube pressure (1 channel) | 10 s at 100 Hz = 1,000 samples | Every 30 s + on alarm | \~8 KB |
| Headcover accelerometer (cavitation) | 0.5 s at 10 kS/s = 5,000 samples | Every 5 min + on alarm | \~40 KB |

```json
{"timestamp": "2026-10-20T09:24:00.000Z", "sampleRate": 1000, "samples": 4000,
 "unit": "µm", "speedRpm": 300.2, "keyphasorIdx": [0, 200, 400], "trigger": "periodic",
 "values": [12.4, 13.1]}
```

- `keyphasorIdx` marks the sample of each shaft revolution, so orbits and phase work without a separate channel.
- `trigger` is `periodic` or `alarm`; values are rounded to 1 decimal.
- Interval, block length and number of detailed turbines are environment variables in `docker-compose.yml`, so the load can be raised for vendors who want to show streaming.

## Failure modes and instructor scenarios

Every failure mode can be detected at increasing levels of sophistication, so vendors can show anything from a threshold to a digital twin on the same data. Real alarm and trip values are OEM-specific; the ones below are plausible demo values.

**Detection ladder:** L1 fixed threshold · L2 rate of change / trend · L3 model residual (expected vs. measured) · L4 spectral analysis on the waveforms (FFT, orbit, envelope, order tracking) · L5 multivariate ML or digital twin.

| # | Failure mode | Signature to simulate | Signals | Detection | Timescale |
| --- | --- | --- | --- | --- | --- |
| 1 | Guide/thrust bearing degradation | One pad temp creeps up 0.1–0.5 °C/day then accelerates; pad-to-pad spread grows | Pad temps, oil temp | L1 alarm \~75–80 °C, trip \~85–90 °C; L2 °C/h; **L3 pad temp vs. MW, cooling water and oil temp** (flagship demo) | Days–weeks |
| 2 | Cooling water loss / cooler fouling | Flow drops; all temps on that circuit rise together | Flow, inlet/outlet temps | L1 low flow; L3 heat-transfer trend | Minutes to months |
| 3 | Oil contamination / water ingress | Oil level rises slowly, temps creep | Oil level | L1/L2 level trend | Weeks |
| 4 | Mechanical unbalance | 1X amplitude up, stable phase, grows with speed | Shaft waveforms + keyphasor | L1 overall per ISO 20816-5; L4 1X vector, orbit | Step or slow |
| 5 | Misalignment / bearing clearance | 1X + 2X, elliptical orbit | Shaft waveforms | L4 orbit, 2X amplitude | Slow |
| 6 | Hydraulic unbalance | 1X rises with gate opening, not speed | Shaft waveforms + gate position | L3/L4 vibration vs. operating point | Slow |
| 7 | Draft-tube vortex rope | Pressure pulsation at 0.2–0.4 × runner frequency, sub-synchronous shaft vibration, MW swings | Draft-tube waveform | L4 FFT dominant frequency; L3 time-in-rough-zone counter | Seconds (live) |
| 8 | Cavitation erosion | High-frequency energy rises at low tailwater / high load | Headcover accelerometer, tailwater | L4 band energy / envelope; L5 cumulative erosion | Months |
| 9 | Runner crack / blade fatigue | Change in blade-pass harmonics | Accelerometer, shaft waveforms | L4 order tracking; L5 fatigue twin | Months |
| 10 | Wicket-gate shear pin failure | Discrete event, vibration step at constant MW | Shear pin status, vibration | L1 event; L3 step detection | Instant |
| 11 | HPU pump wear / internal leakage | Pump starts/hour rise, faster pressure decay | Pump status, accumulator pressure | L2 duty trend; L3 leak rate from dP/dt | Weeks |
| 12 | Servomotor seal / oil leak | Sump level drops, gate drifts | Sump level, servo position vs. setpoint | L2 trend; L3 position error | Days |
| 13 | Shaft-seal wear | Seal water flow and sump pump starts up | Flow, counters | L2 counter trends | Weeks |
| 14 | Generator air-gap anomaly | Minimum air gap shrinking | Air gap | L1 minimum; L2 trend | Weeks |
| 15 | Sensor failure (teaching case) | Flatline, spike or drift on one RTD while neighbours are normal | Any | L1 range/flatline; L3 cross-sensor consistency | Any |

**Instructor scenarios** (hidden; learners and vendors diagnose from data alone)

| Scenario | Failure mode | Speed in demo |
| --- | --- | --- |
| A. Turbine guide bearing degradation | #1 | Weeks compressed to minutes |
| B. Cooling-water strainer blockage | #2 | Minutes |
| C. AGC parks a unit in the rough zone | #7 | Live |
| D. HPU pump wear | #11 | Compressed |
| E. Shear pin break | #10 | Instant |
| F. Unbalance after maintenance | #4 | Step |
| G. RTD sensor drift | #15 | Compressed |
| H. Low reservoir, low head | #8 + efficiency loss | Compressed |

## What the edge and IIoT vendors bring

The environment stops at the local Mosquitto broker. In the next step of the case study, industrial DataOps / IIoT vendors connect their edge devices to it and handle everything beyond it. This makes vendors comparable: same data, same faults, their own platform.

| Topic | What the vendor shows |
| --- | --- |
| Edge analytics | FFT, orbits, envelope analysis and models on the waveform blocks; turning faults A–H into alerts |
| Transport | Getting data from the site to their platform or cloud |
| Buffering | Store-and-forward during link outages, backfill with original timestamps |
| Security | Separating customer control data from machine-builder monitoring; TLS, identities, network segmentation (IEC 62443) |
| Data scoping | Sending only the CH tree (or an agreed subset) off site; respecting customer consent |
| Device management | Onboarding, configuration, firmware updates and health of edge devices across many sites |

The challenges in the original brief (bad connections at customer sites, device management, cyber security, data privacy) become the questions each vendor has to answer on top of this environment.

## Business model and teaching themes

CH must learn to sell outcomes, not just equipment; the data in this environment is what makes those offers possible. Real hydro OEMs already do this, which gives the case study credible anchors.

| OEM | Offering | Signal for CH |
| --- | --- | --- |
| [Andritz Hydro](https://www.andritz.com/hydro-en/hydronews/hn33/intelligent-monitoring) | Metris DiOMera monitoring; long-term O&M with KPI guarantees (Cerro del Águila, Peru) | Outcome-based contracts are possible in hydro |
| [Voith Hydro](https://voith.com/corp-de/products-services/automation-digital-solutions/oncare.html) | OnCare.Health, OnCare.Acoustic, expert health assessments | Product + platform + expert subscription |
| [GE Vernova](https://www.gevernova.com/hydropower/digital-solutions/digital-hydro-plant/edp-digital) | Hydro APM with edge analytics on the most critical plants (EDP: 23 plants, \~5.5 GW) | Tiered coverage by asset criticality |

**Possible CH tiers**

1. **CH Connect** (bundled with new units): remote visibility, digital nameplate, data export.
2. **CH Monitor** (subscription per unit): alarms, monthly health report, expert review.
3. **CH Predict** (subscription + expert retainer): vibration analytics, residual models, remaining useful life, spare-parts forecast.
4. **CH Assure** (outcome-based): availability or rough-zone KPIs with bonus/malus, on-site smart spares, field-service SLAs.

**Discussion themes for the Academy**

- **Data ownership:** under the EU Data Act, users of connected products have data access rights (since 12 Sept 2025), and products placed on the market after 12 Sept 2026 must offer access by design. CH may only use non-personal product data under an agreement with the customer.
- **Third-party data sales:** only with customer consent; anonymised fleet benchmarks are more realistic than raw data.
- **Servitization paradox:** service investments often raise costs before returns arrive.
- **Outcome risk:** CH's KPIs depend on how the customer operates, for example a dispatcher parking units in the rough zone (scenario C).
- **Culture:** an engineering-first company must learn service delivery, and sales incentives tied to equipment sales must change.

## Build plan

| Container | Does | Publishes / subscribes |
| --- | --- | --- |
| `mosquitto` | Local broker on :1884 | — |
| `dam-sim` | Reservoir, spillway, bottom outlet, three units' hydraulics, governor PID with droop, unit state machine | Publishes customer tree; subscribes `Cmd` topics |
| `dam-scada` | Web HMI with the screen set above (:8120) | Subscribes customer tree; publishes `Cmd` |
| `ch-plc-sim` | One process per CH turbine: thermal, HPU and vibration models, waveform generation | Subscribes context from customer tree; publishes CH tree |
| `instructor` | Hidden fault injection (:8121) | Talks to the simulators directly, not via published topics |
| `node-red`, `mqtt-explorer` | Exploration and flows (:1881, :4001) | Both trees |

**Simple but credible physics**

- Unit power = ρgQHη, with a hill-chart-like efficiency surface peaking at \~85–90% gate.
- First-order bearing thermal model driven by load, cooling water temperature and flow.
- Shaft waveform = baseline + 1X (unbalance) + 2X (misalignment) + 0.2–0.4 × runner frequency (rough zone) + noise.
- HPU = accumulator mass balance with leak and pump-wear terms.
- Reservoir = storage–elevation curve with inflow and release.

**Documentation:** wiki page "Dams and turbines in brief", a tested `inventory/` of every topic, and a page "Customer data vs. machine-builder data".

## Caveats

- Copper Canyon Dam and all its figures (levels, head, flows, 300 rpm unit speed, alarm and trip values) are demo assumptions; real values are OEM- and site-specific.
- The vortex-rope magnitude used for calibration (a 600 MW prototype study) still needs a confirmed citation.
- OEM benefit figures are vendor marketing claims; the Data Act summary is not legal advice.

## Sources

- [Reclamation FIST 2-3: Governor maintenance](<https://www.usbr.gov/power/data/fist/FIST_2-3_(1-2021).pdf>)
- [FM Global data sheet 5-3: Hydroelectric power plants](https://www.fm.com/-/media/project/publicwebsites/fmglobal/documentum-new/data-sheet-individual/05-electrical/fmds0503.pdf)
- [ISO 20816-5: vibration of hydraulic machine sets](https://www.iso.org/standard/67919.html)
- [ISO 19283: condition monitoring of hydroelectric machines](https://cdn.standards.iteh.ai/samples/64262/c80c276ce28a4731b51e4a9b3f304c9d/ISO-19283-2020.pdf)
- [Iris Power: hydrogenerator loose rim detection](https://irispower.com/learning-centre/hydrogenerator-loose-rim-detection/)
- [Andritz: intelligent monitoring](https://www.andritz.com/hydro-en/hydronews/hn33/intelligent-monitoring)
- [Voith OnCare](https://voith.com/corp-de/products-services/automation-digital-solutions/oncare.html)
- [Voith and Landsvirkjun cavitation monitoring pilot](https://www.waterpowermagazine.com/news/voith-and-landsvirkjun-launch-pilot-project-on-cavitation-monitoring-7922288/)
- [GE Vernova: EDP digital hydro](https://www.gevernova.com/hydropower/digital-solutions/digital-hydro-plant/edp-digital)
- [Travers Smith: EU Data Act and connected products](https://www.traverssmith.com/knowledge/knowledge-container/the-eu-data-act-compliance-countdown-for-connected-products/)
- [Haltenberg Chemische Werke repo](https://github.com/itotinsider/haltenberg-chemische-werke-uns) · [Sweet Harmony Treats repo](https://github.com/itotinsider/sweet-harmony-treats-uns)
