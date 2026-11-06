# Example Unified Namespace

A **Unified Namespace (UNS)** is one place, here one MQTT broker, where every system publishes its
current data under a structured, agreed topic tree, and every other system subscribes to what it
needs instead of building point-to-point links. Copper Canyon Dam is a small but complete example,
with a twist: **two parties share the broker, and each organises the data its own way.**

- **The dam's view** (the owner, DRWPA): the plant as the operator thinks of it. Site, areas,
  equipment, following the ISA-95 equipment hierarchy. Published by the dam's control system.
- **The vendor's view** (the machine builder, Cromley Hydraulics): the turbine as the manufacturer
  thinks of it. A fleet of assets identified by serial number, each with the same subsystems.
  Published by the CH monitoring PLC on each turbine.

This page writes out both trees in full. For payload details, rates and commands see
[Namespace](Namespace); for why the two views differ, see
[Customer data vs. machine-builder data](Customer-data-vs-machine-builder-data).

## The two structures at a glance

| Level | Dam's view (customer tree) | Vendor's view (CH tree) |
|---|---|---|
| 1 | `v1.0`: version of the namespace | `v1.0`: version of the namespace |
| 2 | `DRWPA`: the enterprise | `CH`: the vendor |
| 3 | `CopperCanyon`: the site | `Fleet`: everything CH has installed |
| 4 | Area: `Reservoir`, `Plant`, `Intake`, `Powerhouse`, … | Customer: `DRWPA` |
| 5 | Equipment: `Unit1`, `Gate01`, … (where the area has more than one) | Site: `CopperCanyon` |
| 6 | Tag: `MW`, `GatePosition`, … | Asset serial: `CH-FR-1987-0042` |
| 7 | | Subsystem: `Bearings`, `Cooling`, `Governor`, `Turbine`, `Vibration`, `Generator`, … |
| 8–9 | | Component and metric: `TGB/PadTemp03`, `HPU/AccumulatorPressure`, … |
| Identity | The **position in the plant**: "Unit 1" | The **serial number**: the machine keeps it when it moves or is renamed |
| Size | 82 values + 1 event topic + 27 commands | 74 values + 8 waveforms + 4 status/event topics, per turbine |

Both trees are generated from one source,
[`common/namespace.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/common/namespace.py),
and every topic below exists on the broker (`test_docs_name_existing_topics` checks the names in
this wiki).

## The dam's view: the customer tree

Every value is retained and published every second as `{"value", "unit", "timestamp"}`.
`Cmd/` branches sit next to the values they act on and are never retained; `Plant/Events` is a
stream of events, not a value. Units 2 and 3 have exactly the same structure as Unit 1.

```
v1.0/DRWPA/CopperCanyon/
├── Reservoir/
│   ├── Level                                 [m a.s.l.] Reservoir water level
│   ├── Inflow                                [m³/s] River inflow into the reservoir (estimated)
│   └── Volume                                [hm³] Stored volume above the dead storage at 380 m a.s.l.
├── River/
│   ├── TailwaterLevel                        [m a.s.l.] Tailwater level below the powerhouse
│   └── Flow                                  [m³/s] Total release to the river (units + spillway + bottom outlet)
├── Plant/
│   ├── GrossHead                             [m] Reservoir level - tailwater level
│   ├── TotalMW                               [MW] Sum of the unit outputs
│   ├── MWSetpoint                            [MW] Plant MW setpoint from the grid operator (incl. AGC)
│   ├── MWSetpointReachable                   False when the online units can't make the setpoint
│   ├── AGCEnabled                            The grid operator's AGC adds small setpoint changes
│   ├── GridFrequency                         [Hz] Grid frequency at the 150 kV busbar
│   ├── Events                                (not retained) Plant events: commands accepted/refused, state changes, trips
│   └── Cmd/
│       ├── MWSetpoint                        [MW] (cmd) Grid operator: plant MW setpoint, split over the units in PLANT mode
│       └── AGC                               (cmd) Grid operator: AGC on/off (small automatic setpoint changes)
├── Intake/
│   ├── GatePosition                          [%] Intake (emergency) gate position, 100 = open
│   ├── TrashRackDP                           [m] Head loss across the trash rack (clogging)
│   ├── RakerRunning                          Trash rack raker cleaning cycle active
│   └── Cmd/
│       └── GatePosition                      [%] (cmd) Intake gate position; closing is refused while a unit is not stopped
├── Penstock/
│   ├── Pressure                              [bar] Penstock pressure at the powerhouse manifold
│   └── Flow                                  [m³/s] Total penstock flow (all three units)
├── Spillway/
│   ├── Gate01/
│   │   ├── Position                          [%] Spillway radial gate 01 position
│   │   ├── Flow                              [m³/s] Flow over spillway gate 01
│   │   ├── Mode                              AUTO (opens near 420 m a.s.l.) or MAN
│   │   └── Cmd/
│   │       ├── Mode                          (cmd) AUTO or MAN
│   │       └── Position                      [%] (cmd) Gate position (switches the gate to MAN)
│   └── Gate02/
│       ├── Position                          [%] Spillway radial gate 02 position
│       ├── Flow                              [m³/s] Flow over spillway gate 02
│       ├── Mode                              AUTO (opens near 420 m a.s.l.) or MAN
│       └── Cmd/
│           ├── Mode                          (cmd) AUTO or MAN
│           └── Position                      [%] (cmd) Gate position (switches the gate to MAN)
├── BottomOutlet/
│   ├── ValvePosition                         [%] Fixed-cone valve position
│   ├── Flow                                  [m³/s] Bottom outlet flow
│   ├── Mode                                  AUTO (keeps the minimum river flow) or MAN
│   └── Cmd/
│       ├── Mode                              (cmd) AUTO or MAN
│       └── Position                          [%] (cmd) Valve position (switches the outlet to MAN)
└── Powerhouse/
    ├── Unit1/
    │   ├── State                             Unit state: Stopped, Starting, SpeedNoLoad, Synchronising, Generating, Stopping, Tripped
    │   ├── BreakerClosed                     Generator breaker closed
    │   ├── ControlMode                       PLANT (plant controller) or LOCAL (own MW setpoint)
    │   ├── MWSetpoint                        [MW] Unit MW setpoint (from the plant controller or local)
    │   ├── MW                                [MW] Active power
    │   ├── MVAr                              [MVAr] Reactive power
    │   ├── GatePosition                      [%] Wicket gate position
    │   ├── GateSetpoint                      [%] Governor gate setpoint
    │   ├── Speed                             [rpm] Shaft speed
    │   ├── Flow                              [m³/s] Turbine flow
    │   ├── NetHead                           [m] Net head at the unit (gross head - penstock losses)
    │   ├── InletValveOpen                    Butterfly inlet valve fully open
    │   ├── ActiveAlarms                      Unit controller alarms and trip causes (list of codes)
    │   ├── ThrustBearingTemp                 [°C] Thrust bearing pad 1 temperature (customer RTD element)
    │   ├── UpperGuideBearingTemp             [°C] Upper guide bearing pad 1 temperature (customer RTD element)
    │   ├── LowerGuideBearingTemp             [°C] Lower guide bearing pad 1 temperature (customer RTD element)
    │   ├── TurbineGuideBearingTemp           [°C] Turbine guide bearing pad 1 temperature (customer RTD element)
    │   ├── CoolingWaterFlow                  [L/s] Total unit cooling water flow
    │   ├── GovernorOilPressure               [bar] Governor HPU accumulator pressure
    │   └── Cmd/
    │       ├── Start                         (cmd) Start sequence to Generating (permissives checked)
    │       ├── Stop                          (cmd) Normal shutdown: unload, open breaker, close gates, brakes
    │       ├── EmergencyStop                 (cmd) Emergency stop (latched, needs Reset at standstill)
    │       ├── Reset                         (cmd) Reset a trip once the unit is at standstill and no cause is active
    │       ├── ControlMode                   (cmd) PLANT or LOCAL
    │       └── MWSetpoint                    [MW] (cmd) Local MW setpoint (switches the unit to LOCAL)
    ├── Unit2/                                same structure as Unit1
    └── Unit3/                                same structure as Unit1
```

What stands out:

- **Organised for running the plant.** The operator looks for "the reservoir" or "Unit 1", not for
  a serial number, so the tree follows the plant layout.
- **Only what the dam's own control system knows.** One temperature per bearing (pad 1, wired
  to the unit protection), one cooling flow, one oil pressure. Nothing about vibration, the other
  bearing pads or the HPU's pumps: that is the machine builder's monitoring.
- **Commands live in the same tree**, under `Cmd/` beside the values they change. The result shows
  up on the value topics, so a client never needs a reply channel.

## The vendor's view: the CH tree

Every process value is retained and published every second as
`{"value", "unit", "timestamp", "quality", "seq"}`. Waveforms are raw sample blocks (not retained),
`_meta/` describes the asset, `Events/` carries the PLC alarms. Only the first turbine is written
out; the other two have the same structure.

```
v1.0/CH/Fleet/
└── DRWPA/                                                customer (one branch per customer that shares data with CH)
    └── CopperCanyon/                                     site
        ├── CH-FR-1987-0042/                              turbine serial (Unit1 in the customer's naming)
        │   ├── _meta/
        │   │   ├── Nameplate                             digital nameplate (JSON): serial, model, ratings, customer unit name
        │   │   └── Status                                ONLINE / OFFLINE (last will)
        │   ├── Context/
        │   │   ├── MW                                    [MW] Active power (copied from the customer tree)
        │   │   ├── MVAr                                  [MVAr] Reactive power (copied from the customer tree)
        │   │   ├── GatePosition_pct                      [%] Wicket gate position (copied)
        │   │   ├── NetHead_m                             [m] Net head (copied)
        │   │   ├── Speed_rpm                             [rpm] Shaft speed (copied)
        │   │   ├── UnitState                             Customer unit state (copied)
        │   │   └── TailwaterLevel_m                      [m a.s.l.] Tailwater level (copied)
        │   ├── Bearings/
        │   │   ├── Thrust/
        │   │   │   ├── PadTemp01                         [°C] Thrust bearing pad 1 temperature
        │   │   │   ├── PadTemp02                         [°C] Thrust bearing pad 2 temperature
        │   │   │   ├── PadTemp03                         [°C] Thrust bearing pad 3 temperature
        │   │   │   ├── PadTemp04                         [°C] Thrust bearing pad 4 temperature
        │   │   │   ├── PadTemp05                         [°C] Thrust bearing pad 5 temperature
        │   │   │   ├── PadTemp06                         [°C] Thrust bearing pad 6 temperature
        │   │   │   ├── OilBathTemp                       [°C] Thrust bearing oil bath temperature
        │   │   │   ├── OilLevel                          [%] Thrust bearing oil level
        │   │   │   └── HPLiftPressure                    [bar] High-pressure oil lift (jacking) pressure
        │   │   ├── UGB/
        │   │   │   ├── PadTemp01                         [°C] UGB pad 1 temperature
        │   │   │   ├── PadTemp02                         [°C] UGB pad 2 temperature
        │   │   │   ├── PadTemp03                         [°C] UGB pad 3 temperature
        │   │   │   ├── PadTemp04                         [°C] UGB pad 4 temperature
        │   │   │   ├── OilTemp                           [°C] UGB oil temperature
        │   │   │   └── OilLevel                          [%] UGB oil level
        │   │   ├── LGB/
        │   │   │   ├── PadTemp01                         [°C] LGB pad 1 temperature
        │   │   │   ├── PadTemp02                         [°C] LGB pad 2 temperature
        │   │   │   ├── PadTemp03                         [°C] LGB pad 3 temperature
        │   │   │   ├── PadTemp04                         [°C] LGB pad 4 temperature
        │   │   │   ├── OilTemp                           [°C] LGB oil temperature
        │   │   │   └── OilLevel                          [%] LGB oil level
        │   │   └── TGB/
        │   │       ├── PadTemp01                         [°C] TGB pad 1 temperature
        │   │       ├── PadTemp02                         [°C] TGB pad 2 temperature
        │   │       ├── PadTemp03                         [°C] TGB pad 3 temperature
        │   │       ├── PadTemp04                         [°C] TGB pad 4 temperature
        │   │       ├── OilTemp                           [°C] TGB oil temperature
        │   │       └── OilLevel                          [%] TGB oil level
        │   ├── Cooling/
        │   │   ├── WaterInletTemp                        [°C] Cooling water inlet temperature (seasonal)
        │   │   ├── WaterFlow_TB                          [L/s] Cooling water flow, turbine bearing circuit
        │   │   ├── WaterFlow_GB                          [L/s] Cooling water flow, generator bearing circuit
        │   │   ├── WaterFlow_AirCoolers                  [L/s] Cooling water flow, generator air coolers
        │   │   └── OilCoolerOutletTemp                   [°C] Cooling water outlet temperature, oil coolers
        │   ├── Governor/
        │   │   └── HPU/
        │   │       ├── AccumulatorPressure               [bar] Accumulator pressure
        │   │       ├── SumpLevel                         [%] HPU sump oil level
        │   │       ├── OilTemp                           [°C] HPU oil temperature
        │   │       ├── Pump1Running                      Pump 1 (lead) running
        │   │       ├── Pump2Running                      Pump 2 (lag) running
        │   │       ├── PumpStartsPerHour                 [1/h] Pump starts in the last hour (both pumps)
        │   │       ├── FilterDP                          [bar] Pressure filter differential pressure
        │   │       ├── ServoPositionA                    [%] Servomotor A position
        │   │       ├── ServoPositionB                    [%] Servomotor B position
        │   │       └── GateSetpoint                      [%] Governor gate setpoint (from the customer's governor)
        │   ├── Turbine/
        │   │   ├── SpiralCasePressure                    [bar] Spiral case pressure
        │   │   ├── HeadcoverPressure                     [bar] Headcover pressure (behind the runner crown)
        │   │   ├── DraftTubePressure                     [bar] Draft tube cone pressure, 1 s mean (gauge)
        │   │   ├── ShaftSealWaterFlow                    [L/min] Shaft seal water flow
        │   │   ├── HeadcoverSumpPumpStarts               Headcover sump pump starts (counter)
        │   │   ├── ShearPinStatus                        Wicket gate shear pins: OK or BROKEN
        │   │   └── WicketGateBreakawayAlarm              A wicket gate lags its servo ring (breakaway link)
        │   ├── Vibration/
        │   │   ├── UGB/
        │   │   │   ├── ShaftX/
        │   │   │   │   ├── Overall_um_pp                 [µm] UGB shaft displacement X, overall peak-to-peak
        │   │   │   │   └── Waveform                      [µm] (not retained) UGB shaft displacement X: 1000 S/s × 4.0 s
        │   │   │   └── ShaftY/
        │   │   │       ├── Overall_um_pp                 [µm] UGB shaft displacement Y, overall peak-to-peak
        │   │   │       └── Waveform                      [µm] (not retained) UGB shaft displacement Y: 1000 S/s × 4.0 s
        │   │   ├── LGB/
        │   │   │   ├── ShaftX/
        │   │   │   │   ├── Overall_um_pp                 [µm] LGB shaft displacement X, overall peak-to-peak
        │   │   │   │   └── Waveform                      [µm] (not retained) LGB shaft displacement X: 1000 S/s × 4.0 s
        │   │   │   └── ShaftY/
        │   │   │       ├── Overall_um_pp                 [µm] LGB shaft displacement Y, overall peak-to-peak
        │   │   │       └── Waveform                      [µm] (not retained) LGB shaft displacement Y: 1000 S/s × 4.0 s
        │   │   ├── TGB/
        │   │   │   ├── ShaftX/
        │   │   │   │   ├── Overall_um_pp                 [µm] TGB shaft displacement X, overall peak-to-peak
        │   │   │   │   └── Waveform                      [µm] (not retained) TGB shaft displacement X: 1000 S/s × 4.0 s
        │   │   │   └── ShaftY/
        │   │   │       ├── Overall_um_pp                 [µm] TGB shaft displacement Y, overall peak-to-peak
        │   │   │       └── Waveform                      [µm] (not retained) TGB shaft displacement Y: 1000 S/s × 4.0 s
        │   │   ├── Headcover/
        │   │   │   ├── Vel_mm_s_rms                      [mm/s] Headcover vibration velocity, RMS 2-1000 Hz
        │   │   │   └── Accel/
        │   │   │       └── Waveform                      [m/s²] (not retained) Headcover accelerometer (cavitation): 10000 S/s × 0.5 s
        │   │   └── DraftTube/
        │   │       └── Pressure/
        │   │           └── Waveform                      [bar] (not retained) Draft tube cone pressure (gauge): 100 S/s × 10.0 s
        │   ├── Generator/
        │   │   ├── AirGapMin_mm                          [mm] Minimum air gap (rotor to stator)
        │   │   ├── StatorTemp01                          [°C] Stator winding RTD 1
        │   │   ├── StatorTemp02                          [°C] Stator winding RTD 2
        │   │   ├── StatorTemp03                          [°C] Stator winding RTD 3
        │   │   ├── StatorTemp04                          [°C] Stator winding RTD 4
        │   │   ├── StatorTemp05                          [°C] Stator winding RTD 5
        │   │   └── StatorTemp06                          [°C] Stator winding RTD 6
        │   ├── Counters/
        │   │   ├── Starts                                Unit starts since commissioning
        │   │   ├── RunHours                              [h] Generating hours since commissioning
        │   │   ├── EmergencyStops                        Emergency stops (trips) since commissioning
        │   │   └── LoadRejections                        Breaker openings under load
        │   └── Events/
        │       ├── Alarm                                 (not retained) PLC alarm events
        │       └── ActiveAlarms                          Active PLC alarm ids
        ├── CH-FR-1987-0043/                              same structure (Unit2)
        └── CH-FR-1989-0051/                              same structure (Unit3)
```

What stands out:

- **Organised for a fleet.** CH builds the same turbine for many customers. Under `Fleet/` every
  installed machine has the same subtree, so one analytics model or dashboard works on all of them.
  The customer and site levels exist so CH can tell installations apart and filter by contract.
- **The serial is the identity.** "Unit1" appears only in the nameplate. If the dam renumbers its
  units, or the turbine is refurbished and moved, the history stays with the serial.
- **Much richer machine data:** every bearing pad, oil levels, cooling per circuit, the HPU, vibration
  overall values and raw waveforms, generator temperatures, counters. This is what condition
  monitoring and an RCA need.
- **Data quality is part of the payload.** `quality` says whether a value can be trusted, `seq`
  lets a subscriber detect lost messages, `_meta/Status` (with an MQTT last will) says whether the
  PLC is online.

## Where the two views meet

The trees describe the same three turbines, so they overlap in two ways:

| Link | Direction | Example |
|---|---|---|
| **Context** | The CH PLC copies the operating point from the customer tree (subscribe only, it never writes there) | `Powerhouse/Unit1/MW` → `CH-FR-1987-0042/Context/MW`, also MVAr, gate, net head, speed, state, tailwater |
| **Dual-element sensors** | One physical sensor, two elements: A wired to the dam's protection, B to the CH PLC | `Powerhouse/Unit1/TurbineGuideBearingTemp` (A) and `Bearings/TGB/PadTemp01` (B); the same for the other bearings and the governor oil pressure |
| **Unit ↔ serial** | Only in the CH nameplate | `CH-FR-1987-0042/_meta/Nameplate` → `"unitTag": "Unit1"` |

Everything else exists in only one tree. That is the lesson of the
[RCA demo](RCA-demo-walkthrough): the overheating TGB pad 3 was visible only in the CH tree, while
the control room's screens, built on the customer tree, showed nothing wrong.

## What is deliberately not in the namespace

- **The faults the instructor injects.** The scenarios live only in the simulators. No topic
  carries the ground truth, so the screens and tools see what a real system would see.
- **Analytics results.** No health scores, spectra or predictions: that is what the edge and IIoT
  vendors add in the next step (see [Edge vendor brief](Edge-vendor-brief)).
- **Security and device management.** Anonymous, no TLS, no ACLs: out of scope for the demo, not a
  recommendation.

## Things to try

```bash
mosquitto_sub -h localhost -p 1884 -t 'v1.0/DRWPA/CopperCanyon/Powerhouse/Unit1/#' -v   # the dam's view of Unit 1
mosquitto_sub -h localhost -p 1884 -t 'v1.0/CH/Fleet/+/+/CH-FR-1987-0042/Bearings/#' -v  # the vendor's view of the same turbine
mosquitto_sub -h localhost -p 1884 -t 'v1.0/CH/Fleet/+/+/+/Bearings/TGB/PadTemp03' -v   # one metric across the fleet
```

Or open MQTT Explorer (see [Node-RED and MQTT Explorer](Node-RED-and-MQTT-Explorer)) and fold out
both trees side by side.
