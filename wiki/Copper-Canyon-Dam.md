# Copper Canyon Dam

Copper Canyon Dam is a small, fictional hydropower dam operated by the fictional **Desert River
Water & Power Authority (DRWPA)**: one reservoir, one intake, one penstock, three CH turbines, one
spillway and one bottom outlet. That is the minimum needed to explain how a dam works. All figures
are demo assumptions, in metric units; real values are OEM- and site-specific.

The model is in [`damsim/model.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/damsim/model.py),
the turbine design data shared by both simulators in
[`common/turbine.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/common/turbine.py).

## The site

| Component | Copper Canyon (as built) | CH equipment? |
|---|---|---|
| Dam | Concrete gravity dam, crest at 425 m a.s.l. | No |
| Reservoir | Operating range 385–420 m a.s.l., starts at 412 m. Surface 8 km² at 385 m, 15 km² at 420 m | No |
| Inflow | ~115 m³/s with a slow random walk | — |
| Intake | 1 intake with trash rack (raker starts at 0.35 m head loss) and intake gate | Gate, rack |
| Penstock | 1 steel penstock to the powerhouse manifold at 300 m a.s.l.; ~1.8 m loss at 135 m³/s; ~10.9 bar | No |
| Inlet valves | 1 butterfly valve per unit, 15 s to open or close | Yes |
| Generating units | 3 × 40 MW vertical Francis (Unit1–3), 100 m rated net head, 300 rpm (1X = 5 Hz), 45 m³/s rated, 13 runner blades (blade pass 65 Hz), 20 wicket gates | Yes (turbine, governor, HPU) |
| Tailwater | Rating curve: ~304.5 m a.s.l. at 135 m³/s, ~310.6 m at 2,000 m³/s. Gross head 80–115 m | No |
| Spillway | Ogee crest at 410 m, 2 radial gates, ~1,000 m³/s each at 420 m. In AUTO they open from 419 m and are fully open at 420 m | Gates and hoists |
| Bottom outlet | 1 fixed-cone valve, 50 m³/s at rated head. In AUTO it keeps the river at ≥ 10 m³/s when the units don't | Yes |
| Grid | 1 line at 150 kV, 50 Hz; frequency wanders ±0.02 Hz | No |

Only the three generating units carry a **CH PLC** that publishes into the CH tree. Everything else
exists only in the customer tree.

## How it is operated

- **Grid operator:** sends a plant MW setpoint, default **110 MW** (`Plant/Cmd/MWSetpoint`).
  With **AGC** on (default), it adds a slowly changing offset of up to **±5 MW** every 2–5 minutes.
- **Plant controller:** splits the plant setpoint over the units in **PLANT** mode that are
  generating. Units in **LOCAL** mode keep their own setpoint; the rest is split over the others.
- **Rough zone:** each unit has a part-load band it must avoid, from 35 % to 70 % gate opening.
  At ~106 m net head that is **~10–33 MW** per unit (with a 0.5 MW margin each side). The plant
  controller puts every unit either above it or below it (at most ~10 MW):
  - it uses as many units above the rough zone as possible, and keeps that number while it still
    works (hysteresis), so units don't jump between the two sides with every AGC step;
  - when the setpoint falls between two possible splits, it never parks a unit in the rough zone:
    it takes the nearest total the units can make and sets `Plant/MWSetpointReachable` to false.
  - Examples at ~106 m: 110 MW → 3 × 36.7; 80 MW → 34.7 + 34.7 + 10.1; 60 MW → 39.3 + 10.6 + 10.6.
- **Minimum river flow:** 10 m³/s, always. The bottom outlet (AUTO) opens when the units and the
  spillway release less, and aims for 12 m³/s.
- **Floods:** the spillway gates only open when the reservoir approaches 420 m a.s.l. (AUTO from
  419 m). With the default inflow and setpoint the level is nearly steady; it moves a few
  centimetres per hour.

## Unit state machine

`Powerhouse/<unit>/State` is one of `Stopped`, `Starting`, `SpeedNoLoad`, `Synchronising`,
`Generating`, `Stopping`, `Tripped`.

| State | What happens | Time (demo) |
|---|---|---|
| Stopped | Gates closed, inlet valve closed, brakes on | — |
| Starting | Cooling water pump on and checked after 10 s (≥ 56 L/s, else the start is aborted); inlet valve opens (15 s); brakes off; gates to break-away (20 %) until 95 % speed | ~90 s |
| SpeedNoLoad | Governor in speed control at 300 rpm; field flash and excitation | 5 s |
| Synchronising | Auto-synchroniser matches speed to the grid, then closes the breaker | 8 s |
| Generating | Governor in power control (with 5 % droop), ramps to the setpoint at 12 MW/min | ~3 min to full load |
| Stopping | Unload at 40 MW/min → breaker opens below 1 MW → gates close → de-excite → coast (~2 min; brakes below 30 % speed) → inlet valve closes | ~3.5 min |
| Tripped | Emergency stop: breaker opens at once, gates close at full rate (6 s full stroke), inlet valve closes, brakes below 30 % speed. **Latched** | until Reset |

**Start permissives:** unit Stopped, intake gate open, reservoir ≥ 384 m a.s.l., the hardwired
signals from the turbine present, governor oil pressure ≥ 55 bar. A refused command is reported
on `Plant/Events`.

**Reset** of a trip is only accepted at standstill with the inlet valve closed and no bearing
temperature still above the trip limit.

## Unit protection

The customer's unit controller protects the unit with **its own** sensors on the turbine: element A
of the dual-element RTDs (pad 1 of each bearing), one cooling water flow meter and the governor oil
pressure (see [Customer data vs. machine-builder data](Customer-data-vs-machine-builder-data)). It
reports codes in `Powerhouse/<unit>/ActiveAlarms`:

| Code | Condition |
|---|---|
| `TRIP_BEARING_TEMP` | Any customer bearing RTD ≥ 90 °C for 5 s while running |
| `TRIP_GOV_OIL_PRESSURE` | Governor oil pressure < 48 bar (two servo strokes left) for 5 s while running |
| `TRIP_OVERSPEED` | Speed > 145 % (a normal load rejection peaks at ~123 %) |
| `TRIP_EMERGENCY_STOP` | Operator emergency stop |
| `TRIP_GENERATOR_PROTECTION` | Electrical protection (instructor scenario) |
| `BEARING_TEMP_HIGH` | Any customer bearing RTD ≥ 80 °C |
| `GOV_OIL_PRESSURE_LOW` | Governor oil pressure < 52 bar |
| `COOLING_WATER_FLOW_LOW` | Cooling water < 56 L/s while running (not during Starting) |
| `HARDWIRED_IO_FAULT` | No signals from the turbine for 5 s; the six hardwired tags are then not published |

## Simplifications

- Flow is proportional to gate opening and √head; efficiency is a hill-chart-like surface
  (peak 0.93 at 87 % gate and 100 m). Unit power = ρgQHη − 0.6 MW losses.
- Mechanics: one inertia constant (2H = 8 s), turbine torque falling linearly to runaway at 2 ×
  rated speed, a churning loss when the gates are closed.
- Penstock: one static pressure with a first-order water-hammer term; no travelling waves.
- Reservoir: a storage–elevation curve with inflow and release. In real time it barely moves, so
  the instructor's reservoir scenarios compress time.
- MVAr follows MW; there is no voltage, excitation or switchyard model.
- The MW of a unit in the rough zone swings with the vortex rope (±1.2 MW at peak intensity).
