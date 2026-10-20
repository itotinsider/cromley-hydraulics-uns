# Architecture

```
                            ┌──────────────────── mosquitto :1883 (host 1884) ───────────────────┐
                            │  v1.0/DRWPA/CopperCanyon/...        v1.0/CH/Fleet/DRWPA/...        │
                            │  customer tree (+ Cmd, Plant/Events) CH tree (per serial)          │
                            └──▲────────────▲──────────▲─────────────▲──────────▲────────▲───────┘
                     publish   │   Cmd      │ subscribe│  context    │ publish  │ both   │ CH only
                    customer   │ subscribe  │  + Cmd   │ (subscribe) │ CH tree  │ trees  │
                  ┌────────────┴─┐   ┌──────┴──────┐   │   ┌─────────┴─────┐ ┌──┴─────┐ ┌┴─────────┐
                  │ dam-sim      │   │ dam-scada   │   └───┤ ch-plc-sim    │ │Node-RED│ │ch-viewer │
                  │ reservoir,   │   │ hub + HMI   │       │ 3 CH PLCs     │ │MQTT    │ │ :8122    │
                  │ 3 units,     │   │ :8120       │       │ thermal, HPU, │ │Explorer│ └──────────┘
                  │ plant ctrl   │   └─────────────┘       │ vibration,    │ └────────┘
                  │ :8123 (int.) │◄── hardwired (HTTP) ────┤ waveforms     │
                  └──────▲───────┘   element A sensors     │ :8125 (int.)  │
                         │ HTTP                            └───────▲───────┘
                         └──────────── instructor :8121 ───────────┘ HTTP
                                    (hidden scenarios, never MQTT)

     - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
       next step, the edge / IIoT vendors: edge devices on the broker, analytics, transport,
       buffering, security, data scoping, device management
```

## The containers

| Container | Does | Publishes / subscribes |
|---|---|---|
| `mosquitto` | The one local broker (Eclipse Mosquitto 2.0.22), no auth, retained messages persisted in `mosquitto/data/` | — |
| `dam-sim` | Reservoir, spillway, bottom outlet, intake, three units' hydraulics, governor with droop, unit state machine, unit protection, plant controller | Publishes the customer tree every second (retained) and `Plant/Events`; subscribes the `Cmd` topics |
| `ch-plc-sim` | One simulated CH PLC per turbine: thermal, HPU and vibration models, waveform generation, the PLC's own alarm checks | Subscribes its unit's context in the customer tree; publishes the CH tree |
| `dam-scada` | The customer's dam SCADA: alarm engine, event journal, trends, operator commands; also serves the hub page | Subscribes the customer tree only; publishes `Cmd` |
| `instructor` | Hidden fault scenarios | Talks HTTP to `dam-sim` and `ch-plc-sim`, never MQTT |
| `ch-viewer` | The machine builder's view: nameplates, values, alarms, raw waveforms | Subscribes the CH tree only |
| `nodered`, `mqtt-explorer` | Exploration and flows | Both trees |
| `tests` | Test runner (compose profile `test`) | Its own broker and processes |

The two simulators and the screens each run their own clock. Nothing is lock-stepped: the dam
integrates at 0.1 s and publishes at 1 s; each CH PLC steps and publishes every second, from the
last context it received.

## One broker, two trees

- The **customer tree** `v1.0/DRWPA/CopperCanyon/<Area>/<Module>/<Tag>` belongs to the dam owner.
  It is what the dam SCADA works with, and where commands go (`.../Cmd/...`).
- The **CH tree** `v1.0/CH/Fleet/DRWPA/CopperCanyon/<AssetSerial>/<Subsystem>/<Component>/<Metric>`
  belongs to Cromley Hydraulics. Each CH PLC copies a few context values from the customer tree
  (subscribe only) and never writes into it.

The full reference is the [Namespace](Namespace) page; why there are two trees is on
[Customer data vs. machine-builder data](Customer-data-vs-machine-builder-data).

## The hardwired link

Some sensors on each turbine are **dual-element**: one element is wired to the customer's unit
controller, the other to the CH PLC. Here the turbine physics lives in the CH PLC simulator, so it
serves element A on an internal HTTP endpoint (`GET /api/hardwired` on `ch-plc-sim:8125`). That
endpoint stands for the copper, not for a data interface. The dam simulator polls it every second
and uses the values for start permissives and unit protection, and publishes them in the customer
tree:

| Customer tag (`Powerhouse/<unit>/…`) | Element B in the CH tree |
|---|---|
| `ThrustBearingTemp` | `Bearings/Thrust/PadTemp01` |
| `UpperGuideBearingTemp` | `Bearings/UGB/PadTemp01` |
| `LowerGuideBearingTemp` | `Bearings/LGB/PadTemp01` |
| `TurbineGuideBearingTemp` | `Bearings/TGB/PadTemp01` |
| `CoolingWaterFlow` | sum of `Cooling/WaterFlow_TB`, `_GB`, `_AirCoolers` (one flow meter) |
| `GovernorOilPressure` | `Governor/HPU/AccumulatorPressure` |

If the CH PLC simulator is down, the dam raises `HARDWIRED_IO_FAULT`, stops publishing these six
tags, refuses starts and doesn't trip on stale values.

## Hidden faults

Fault scenarios are started on the [instructor station](Instructor-station). The instructor talks
to the simulators directly over HTTP. Nothing in MQTT says a scenario is active: learners and
vendors diagnose from the data alone. Dam scenarios (operation, reservoir) live in the dam
simulator, machine faults in the CH PLC simulator.

## Compared with Haltenberg and Sweet Harmony

| | HCW | SHT | CH |
|---|---|---|---|
| Field data | Plant is a Modbus TCP I/O rack | One simulator publishes to MQTT | Dam simulator and three CH PLCs publish to MQTT |
| Control | Simulated DCS with loops, alarms, interlocks | — | Unit controllers and plant controller inside the dam simulator; SCADA commands over MQTT |
| Data for IT | OPC UA with history | MQTT topics, HTTP API | Two MQTT trees on one broker, plus raw waveforms |
| Teaching contrast | Raw Modbus vs. modelled OPC UA | `_RAW` feed vs. UNS | Customer tree vs. machine-builder tree |

## Built with

Python 3.12 with the standard library and paho-mqtt only (no numpy: the waveforms are synthesised
sample by sample), Eclipse Mosquitto, vanilla HTML/JS without a build step, the official Node-RED
image, MQTT Explorer's browser build, Docker Compose.
