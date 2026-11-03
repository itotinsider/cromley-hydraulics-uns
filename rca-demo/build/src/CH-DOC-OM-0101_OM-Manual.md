---
house: CH
out: supplier/CH-DOC-OM-0101_CH-Francis-Canyon_O-and-M-Manual_Rev4.pdf
title: CH-Francis "Canyon" FC-40/100 Vertical Francis Turbine
subtitle: Operation and Maintenance Manual: Copper Canyon Dam, Units 1–3
doc: CH-DOC-OM-0101
rev: 4
date: 2026-08-14
applies: CH-FR-1987-0042 (Unit 1), CH-FR-1987-0043 (Unit 2), CH-FR-1989-0051 (Unit 3)
owner: Cromley Hydraulics, Product Engineering, Francis Line
status: Issued to Desert River Water & Power Authority (DRWPA)
class: Supplier document. Fictional, for training only.
---

## Revision history

| Rev | Date | Change |
| --- | --- | --- |
| 1 | 1987-05-20 | First issue, Units 1 and 2 |
| 2 | 1989-11-02 | Unit 3 added |
| 3 | 2014-06-30 | Rehabilitation programme: new governor interface, updated limits, oil specification |
| 4 | 2026-08-14 | Chapter 9 added: CH monitoring PLC retrofit (dual-element RTDs, vibration, HPU and cooling monitoring, MQTT data). Alarm tables and troubleshooting updated. Maintenance recommendations updated. |

## 1 Safety and scope

This manual covers the hydraulic turbine, its guide and thrust bearings, the bearing lubrication and cooling systems, the governor hydraulic power unit (HPU) and the CH monitoring PLC. The generator, excitation, unit protection and the plant control system are supplied by others and are referenced only where they interface with CH equipment.

> Work on the unit requires the owner's lock-out / tag-out procedure: intake gate and inlet valve closed and locked, penstock drained where required, HPU depressurised, brakes applied. Never enter the spiral case, headcover pit or draft tube unless the owner's permit is in place.

The owner (DRWPA) remains responsible for unit protection settings. The values in this manual are CH recommendations.

## 2 Design data

| Item | Value |
| --- | --- |
| Type | Vertical-shaft Francis turbine, CH-Francis "Canyon" FC-40/100 |
| Rated output (generator terminals) | 40 MW |
| Maximum continuous output | 42 MW (105 %), only at net head of 100 m or more |
| Rated net head | 100 m (permissible range 80–115 m) |
| Rated speed | 300 rpm (50 Hz, 10 pole pairs); runner frequency 1X = 5 Hz |
| Runaway speed | approx. 2.0 × rated speed |
| Runner | 13 blades; blade-pass frequency 65 Hz |
| Distributor | 20 wicket gates, two servomotors (A and B) on a common regulating ring |
| Flow | approx. 43.5 m³/s at best efficiency (87 % gate, 100 m); 50 m³/s at 100 % gate and 100 m |
| Peak efficiency | 93 % at 87 % gate, rated head |
| Minimum stable load | 3 MW |
| Shaft line | Generator rotor with upper and lower guide bearings, thrust bearing in the upper bracket, turbine guide bearing in the headcover |
| Shaft seal | Water-lubricated carbon segment seal, seal water from the cooling water system |
| Inlet valve | Butterfly valve DN 3,200, hydraulically opened, counterweight closed |

## 3 Operating range and the rough zone

A Francis turbine runs smoothly near its best efficiency point. At part load (roughly 40–80 % of best-efficiency flow) a rotating vortex forms in the draft tube cone. This **vortex rope** causes pressure pulsations at about **0.28 × runner frequency (approx. 1.4 Hz on this machine)**, sub-synchronous shaft vibration, power swings and, over time, fatigue cracking of the draft tube cone and cavitation erosion of the runner.

The **rough zone** of the FC-40/100 is **35 % to 70 % wicket-gate opening**, with the strongest rope near 55 %. In MW it depends on net head:

| Net head (m) | Rough zone (MW) | Maximum output (MW) |
| --- | --- | --- |
| 80 | 6.8 – 21.2 | 31.1 |
| 90 | 8.3 – 25.6 | 37.4 |
| 100 | 9.8 – 30.1 | 42.0 |
| 106 | 10.7 – 32.9 | 42.0 |
| 115 | 12.1 – 37.2 | 42.0 |

**CH requirements for operation in the rough zone:**

- Pass through the rough zone only while ramping. Do not hold a setpoint inside it.
- The plant controller's rough-zone table shall not be bypassed without a documented engineering assessment.
- Cumulative operation inside the rough zone of more than **50 hours per year** requires a draft tube cone and runner inspection at the next outage. Owners are advised to record rough-zone hours per unit.
- Signs of rough-zone operation: draft tube pressure pulsation with a dominant frequency near 1.4 Hz, TGB shaft vibration above approx. 100 µm pp with a sub-synchronous component, headcover vibration above 2 mm/s rms, MW swings of ±1 MW.

At low head (below approx. 90 m) and at loads above 90 % gate, cavitation risk increases; see section 8.6.

## 4 Bearings

### 4.1 Arrangement

| Bearing | Location | Type | Pads | Oil system | Cooling circuit |
| --- | --- | --- | --- | --- | --- |
| Thrust bearing | Generator upper bracket | Tilting pad, babbitt | 6 | Own oil pot, 1,600 L, ISO VG 68 | GB |
| Upper guide bearing (UGB) | Generator upper bracket | Segment, babbitt | 4 instrumented | Own oil pot, 350 L, ISO VG 68 | GB |
| Lower guide bearing (LGB) | Generator lower bracket | Segment, babbitt | 4 instrumented | Own oil pot, 400 L, ISO VG 68 | GB |
| Turbine guide bearing (TGB) | Headcover | Segment, babbitt, oil bath | 4 instrumented | Own oil pot, 450 L, ISO VG 68 | TB (own circuit) |

The thrust bearing has a high-pressure oil lift (jacking) system, used during start-up and run-down below 30 % speed.

### 4.2 TGB pad clearance

Design radial clearance of the TGB segments: **0.30 mm ± 0.05 mm**. A segment set tighter than 0.25 mm runs hotter (more shear heating in a thinner film) and has less margin when the oil degrades. Clearances above 0.35 mm reduce damping and raise shaft vibration. Any deviation shall be recorded on a CH concession form and the segment's temperature trended.

### 4.3 Normal temperatures

At rated output, cooling water inlet 10–25 °C:

| Measurement | Normal range |
| --- | --- |
| Thrust pads | 60 – 70 °C |
| UGB / LGB pads | 55 – 66 °C |
| TGB pads | 60 – 68 °C |
| Oil baths (all bearings) | 45 – 58 °C |
| Pad-to-pad spread within one bearing | normally below 3 K; investigate above 5 K |

Temperatures fall with load and rise about 0.7 K per K of cooling water inlet temperature. Pads closer to the oil inlet run slightly cooler; a fixed offset of 1–2 K between pads is normal and stable.

### 4.4 Temperature instrumentation

Pad 1 of every bearing carries a **dual-element Pt100**:

- **Element A** is wired to the owner's unit controller and used for unit protection.
- **Element B** is wired to the CH monitoring PLC.

All other instrumented pads carry a single-element Pt100 wired to the CH monitoring PLC only. The owner's control room therefore sees **one pad per bearing**; the CH PLC sees all pads (see chapter 9).

### 4.5 Bearing temperature limits

| Function | Measured on | Limit | Action |
| --- | --- | --- | --- |
| CH PLC alarm H | Every pad (element B / single element) | 75 °C | Investigate, see 8.1 |
| CH PLC alarm HH | Every pad | 85 °C | Reduce load, prepare controlled stop |
| CH PLC oil alarm | Every oil bath | 65 °C | Check cooling, see 8.2 |
| Owner alarm (recommended) | Pad 1, element A | 80 °C | Per owner procedure |
| Owner trip (recommended) | Pad 1, element A, 5 s delay | 90 °C | Emergency stop |

> Because protection acts on pad 1 only, a problem on another pad may reach high temperatures before the owner's protection responds. CH recommends that the owner brings the CH PLC pad alarms into the control room.

## 5 Lubrication

### 5.1 Oil specification

Bearings: turbine oil ISO VG 68, rust and oxidation inhibited (R&O), new-oil TAN max. 0.10 mg KOH/g. HPU: hydraulic oil ISO VG 46, anti-wear.

### 5.2 Oil condition limits (bearing oil)

| Parameter | Normal | Caution: resample within 30 days, find cause | Action: change oil, inspect bearing |
| --- | --- | --- | --- |
| Viscosity at 40 °C | 61 – 75 cSt | ±10 % from new | ±15 % from new |
| TAN (mg KOH/g) | below 0.25 | 0.25 – 0.40 | above 0.40 |
| Water (ppm) | below 200 | 200 – 500 | above 500 |
| Tin, Sn (ppm), babbitt wear indicator | below 5 | 5 – 15 | above 15 |
| Iron, Fe (ppm) | below 10 | 10 – 25 | above 25 |
| Particle count ISO 4406 | 17/15/12 or cleaner | 18/16/13 | 19/17/14 or worse |
| Varnish potential, MPC ΔE | below 20 | 20 – 30 | above 30 |

A rising tin trend together with rising TAN and MPC indicates oil oxidation and babbitt distress. Oxidised oil loses film strength; the most loaded or widest-clearance segment is affected first.

### 5.3 Oil change

Change bearing oil on condition (section 5.2). Without condition data, change at the latest every **36 months**.

## 6 Cooling water system

Cooling water is taken from the penstock through one **unit strainer** (duplex basket, manual changeover, differential pressure gauge PDI-x01) and one **total flowmeter** (owner's, FT-x01). It then splits into three circuits:

| Circuit | Serves | Nominal flow | CH PLC low-flow alarm |
| --- | --- | --- | --- |
| TB | TGB oil cooler | 8 L/s | below 5.6 L/s (70 %) |
| GB | Thrust, UGB and LGB oil coolers | 12 L/s | below 8.4 L/s (70 %) |
| AirCoolers | Generator air coolers | 60 L/s | below 42 L/s (70 %) |
| Total | Owner flowmeter | 80 L/s | Owner alarm recommended below 56 L/s |

Shaft seal water is taken downstream of the strainer (approx. 35–45 L/min). Cooling water returns to the tailrace.

Clean the strainer when the differential pressure exceeds 0.3 bar, and at least monthly during the high-silt season (spring runoff). A blocked strainer reduces **all** circuits at the same time; every bearing and the generator warm up together.

## 7 Governor hydraulic power unit (HPU)

| Item | Value |
| --- | --- |
| Oil | ISO VG 46 anti-wear, sump 2,500 L |
| Accumulator | Air-oil, working pressure 58–63 bar |
| Pumps | 2 × 4 L/s; lead pump on at 58 bar, off at 63 bar; lag pump on at 54 bar, off at 61 bar |
| Normal pump duty | 5–8 starts per hour in steady operation |
| Servomotor stroke | approx. 40 L per full stroke; opening 15 s, closing 6 s |
| CH PLC alarms | Pressure below 52 bar; more than 15 starts/h; filter ΔP above 2.5 bar; sump below 55 % |
| Owner protection (recommended) | Start permissive 55 bar; alarm 52 bar; trip 48 bar |

Rising pump starts per hour with normal gate activity indicate internal leakage or pump wear. A falling sump level with a drifting servomotor indicates an external (servomotor seal) leak.

## 8 Troubleshooting

### 8.1 Bearing pad temperature high

Always compare the pad with its neighbours, its oil bath, the other bearings and the cooling water before acting.

| Pattern | Likely cause | Check |
| --- | --- | --- |
| One pad rising, neighbours rising a little, oil bath rising slowly | Developing oil-film loss on that pad: clearance, oil condition, contamination, babbitt damage | Oil sample (Sn, TAN, MPC, water), pad clearance records, vibration at that bearing; reduce load |
| One pad changing while neighbours, oil bath and pad 1 element A stay flat | **Measurement fault**: RTD, cable, connector, terminal | Compare element A and B on pad 1; check connectors and glands (see CH-SB-2026-03); measure loop resistance |
| All pads of one bearing and its oil bath rising | Cooling circuit of that bearing, oil level, oil cooler fouling | Circuit flow, cooler outlet temperature, oil level |
| All bearings and generator rising together | Cooling water: strainer, valve, supply | Total flow, strainer ΔP |
| TGB pads warmer, with high TGB vibration and draft tube pulsation | Rough-zone operation (TGB load increases with the vortex rope) | Gate position against the rough zone table; draft tube waveform |
| Rise after maintenance | Clearance, alignment, oil level or wrong oil | Maintenance records |

### 8.2 Oil bath temperature high

Check circuit flow, cooler outlet temperature (fouling), oil level and cooling water inlet temperature. A slow rise over weeks at constant load and inlet temperature points to oil cooler fouling.

### 8.3 Shaft vibration high

| Pattern | Likely cause |
| --- | --- |
| 1X dominant, rises with speed, stable phase | Mechanical unbalance |
| 1X rises with gate opening rather than speed | Hydraulic unbalance (runner) |
| 2X present, elliptical orbit | Misalignment, bearing clearance |
| Sub-synchronous component near 0.28 × 1X, with draft tube pulsation | Vortex rope (rough zone) |
| Step change at constant load | Shear pin failure, loose part |
| Blade-pass (13X) sidebands, 2X growth on headcover | Runner crack |

Shaft vibration (shaft relative, peak-to-peak): normal 35–70 µm at full load; **alert 140 µm**, **danger 220 µm**. Headcover velocity: normal approx. 1 mm/s rms; alarm 4.5 mm/s.

### 8.4 Pump starts high / accumulator pressure low

See chapter 7. Compare decay rate after the pump stops: faster decay at the same gate activity means internal leakage.

### 8.5 Shear pin broken

A broken shear pin frees one wicket gate. The CH PLC raises the shear pin and breakaway alarms. Expect a vibration step on TGB and headcover. Do not continue to operate; stop the unit in a controlled way.

### 8.6 Cavitation

Cavitation increases at loads above 90 % gate, at heads far from 100 m and at low tailwater. Signs: rising high-frequency energy on the headcover accelerometer. Inspect the runner band and blades at each annual inspection; record areas and depths.

## 9 CH monitoring PLC (retrofit 2026)

### 9.1 Purpose

From 2026 every FC-40/100 is fitted with a CH monitoring PLC. It reads all bearing pad RTDs (element B on pad 1), oil temperatures and levels, cooling circuit flows, HPU pressure, pumps and filter, turbine pressures, shaft proximity probes (X/Y at UGB, LGB and TGB) with a keyphasor, a headcover accelerometer, a draft tube pressure sensor, generator stator RTDs and air gap. It copies the operating point (MW, gate, net head, speed, unit state) from the owner's system as read-only context. **It never writes into the owner's control system.**

### 9.2 Data

The PLC publishes to the site MQTT broker under `v1.0/CH/Fleet/DRWPA/CopperCanyon/<serial>/…`: process values every second (with `quality` and `seq`), raw vibration and pressure waveform blocks, a nameplate, alarm events and active alarms. The owner's tag names are listed in the site's interface inventory.

> The `quality` field reports the PLC's knowledge of the signal path (GOOD, UNCERTAIN for stale context, BAD for missing context). It does **not** detect a sensor that reads wrong but plausible values. Plausibility checks (pad versus neighbours and oil bath) are recommended in the owner's analytics.

### 9.3 Alarms

The PLC alarm limits are those given in sections 4.5, 6, 7 and 8.3, plus stator winding above 120 °C and minimum air gap below 10.5 mm (nominal 12.0 mm at standstill, approx. 11.6 mm running).

### 9.4 Installation notes

RTD extension cables to the CH PLC (pad 1 element B and pads 2..n) run from each bearing to local junction boxes (JB-x-01 upper bracket, JB-x-02 lower bracket, JB-x-04 headcover pit) and from there to the PLC cabinet. Connectors are M12, IP67 when fully mated and with the cable gland fully tightened. The headcover pit is a wet area; see service bulletin CH-SB-2026-03.

## 10 Maintenance recommendations

| Task | Interval | Notes |
| --- | --- | --- |
| Bearing oil sample (all pots) | Quarterly | Sn, Fe, TAN, water, viscosity, particle count, MPC; trend per pot |
| Bearing oil change | On condition, at the latest 36 months | Flush pot when MPC above 30 |
| Unit strainer cleaning | On ΔP above 0.3 bar; monthly in high-silt season | Record ΔP before and after |
| Oil cooler inspection / cleaning | 2 years or on fouling trend | |
| HPU oil sample | 6 months | |
| HPU filter element | On ΔP alarm or 12 months | |
| Accumulator pre-charge check | 12 months | |
| Shear pin and gate linkage inspection | Annual inspection | |
| Draft tube cone and runner inspection | Annual inspection | Required after more than 50 h/year in the rough zone |
| TGB clearance check | Major overhaul, or after any TGB temperature event | |
| Shaft seal segments | Annual inspection; replace on wear | Trend seal water flow and headcover sump pump starts |
| CH PLC: RTD connector and gland check | 6 months, and after any work in wet areas | See CH-SB-2026-03 |

## 11 Contacts

Cromley Hydraulics Field Service: Lars Bergström, field service engineer for Copper Canyon Dam. Product Engineering, Francis Line, for concessions and engineering assessments.
