# Namespace

Every topic on the Copper Canyon broker. The single source of truth is
[`common/namespace.py`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/common/namespace.py);
the generated, tested list of every concrete topic is
[`inventory/topics.csv`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/inventory/topics.csv)
(see [Interface reference](Interface-reference)).

Broker: `mqtt://localhost:1884` from the host, `mosquitto:1883` inside the compose network.
Anonymous, no TLS. All topics start with the version `v1.0/`.

## Customer tree

Prefix `v1.0/DRWPA/CopperCanyon/`. Published by the dam simulator every second, **retained**.

| Area / module | Tags |
|---|---|
| `Reservoir` | `Level` (m a.s.l.), `Inflow` (m³/s), `Volume` (hm³ above 380 m) |
| `River` | `TailwaterLevel` (m a.s.l.), `Flow` (m³/s) |
| `Plant` | `GrossHead` (m), `TotalMW`, `MWSetpoint` (MW, incl. AGC), `MWSetpointReachable`, `AGCEnabled`, `GridFrequency` (Hz) |
| `Intake` | `GatePosition` (%), `TrashRackDP` (m), `RakerRunning` |
| `Penstock` | `Pressure` (bar), `Flow` (m³/s) |
| `Spillway/Gate01`, `/Gate02` | `Position` (%), `Flow` (m³/s), `Mode` (`AUTO`/`MAN`) |
| `BottomOutlet` | `ValvePosition` (%), `Flow` (m³/s), `Mode` (`AUTO`/`MAN`) |
| `Powerhouse/Unit1`…`Unit3` | `State`, `BreakerClosed`, `ControlMode` (`PLANT`/`LOCAL`), `MWSetpoint`, `MW`, `MVAr`, `GatePosition` (%), `GateSetpoint` (%), `Speed` (rpm), `Flow` (m³/s), `NetHead` (m), `InletValveOpen`, `ActiveAlarms` (list of codes) |
| `Powerhouse/Unit1`…`Unit3` (hardwired) | `ThrustBearingTemp`, `UpperGuideBearingTemp`, `LowerGuideBearingTemp`, `TurbineGuideBearingTemp` (°C), `CoolingWaterFlow` (L/s), `GovernorOilPressure` (bar) |

82 topics. `State` is one of `Stopped`, `Starting`, `SpeedNoLoad`, `Synchronising`, `Generating`,
`Stopping`, `Tripped`; the `ActiveAlarms` codes are listed on [Copper Canyon Dam](Copper-Canyon-Dam#unit-protection).

**Payload** (the Sweet Harmony format):

```json
{"value": 36.65, "unit": "MW", "timestamp": "2026-10-20T12:00:00.000Z"}
```

Booleans are `true`/`false`, states and modes strings, `ActiveAlarms` a JSON list, e.g.
`{"value": ["TRIP_BEARING_TEMP", "BEARING_TEMP_HIGH"], "unit": "", ...}`.

**Events** `v1.0/DRWPA/CopperCanyon/Plant/Events` (not retained): commands accepted or refused,
state changes, trips, raker starts.

```json
{"timestamp": "2026-10-20T12:00:01.200Z", "source": "Unit1", "kind": "refused",
 "text": "Unit1: start refused, governor oil pressure below 55.0 bar"}
```

`kind` is `command`, `refused`, `state`, `trip` or `info`.

### Commands

A `Cmd` branch next to the measured values. The dam simulator subscribes; the result shows up on
the measured topics. Payload: a bare value (`42`, `true`, `PLANT`) or JSON `{"value": ...}`
(optionally with `"source"`). For a trigger any payload works. **Never retain a command**: a
retained `Start` would replay on every simulator restart.

| Topic (after the prefix) | Value |
|---|---|
| `Plant/Cmd/MWSetpoint` | 0–130 MW (the grid operator) |
| `Plant/Cmd/AGC` | `true` / `false` |
| `Intake/Cmd/GatePosition` | 0–100 %; closing is refused while a unit is not stopped |
| `Spillway/Gate01/Cmd/Mode`, `Gate02/Cmd/Mode` | `AUTO` / `MAN` |
| `Spillway/Gate01/Cmd/Position`, `Gate02/Cmd/Position` | 0–100 % (switches the gate to MAN) |
| `BottomOutlet/Cmd/Mode` | `AUTO` / `MAN` |
| `BottomOutlet/Cmd/Position` | 0–100 % (switches to MAN) |
| `Powerhouse/<unit>/Cmd/Start` | trigger |
| `Powerhouse/<unit>/Cmd/Stop` | trigger |
| `Powerhouse/<unit>/Cmd/EmergencyStop` | trigger |
| `Powerhouse/<unit>/Cmd/Reset` | trigger (at standstill) |
| `Powerhouse/<unit>/Cmd/ControlMode` | `PLANT` / `LOCAL` |
| `Powerhouse/<unit>/Cmd/MWSetpoint` | 0–42 MW (switches the unit to LOCAL) |

```bash
mosquitto_pub -h localhost -p 1884 -t 'v1.0/DRWPA/CopperCanyon/Plant/Cmd/MWSetpoint' -m '{"value": 90}'
```

## CH tree

`v1.0/CH/Fleet/<CustomerId>/<SiteId>/<AssetSerial>/<Subsystem>/<Component>/<Metric>`, here
`v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/...` (Unit1), `CH-FR-1987-0043` (Unit2),
`CH-FR-1989-0051` (Unit3). The component level is left out where there is only one.

### Process values (every second, retained by default)

| Subsystem | Tags |
|---|---|
| `Context` (copied from the customer tree) | `MW`, `MVAr`, `GatePosition_pct`, `NetHead_m`, `Speed_rpm`, `UnitState`, `TailwaterLevel_m` |
| `Bearings/Thrust` | `PadTemp01..06`, `OilBathTemp`, `OilLevel` (%), `HPLiftPressure` (bar) |
| `Bearings/UGB`, `/LGB`, `/TGB` | `PadTemp01..04`, `OilTemp`, `OilLevel` (%) |
| `Cooling` | `WaterInletTemp`, `WaterFlow_TB`, `WaterFlow_GB`, `WaterFlow_AirCoolers` (L/s), `OilCoolerOutletTemp` |
| `Governor/HPU` | `AccumulatorPressure` (bar), `SumpLevel` (%), `OilTemp`, `Pump1Running`, `Pump2Running`, `PumpStartsPerHour`, `FilterDP` (bar), `ServoPositionA`, `ServoPositionB`, `GateSetpoint` (%) |
| `Turbine` | `SpiralCasePressure`, `HeadcoverPressure`, `DraftTubePressure` (bar, gauge, 1 s mean), `ShaftSealWaterFlow` (L/min), `HeadcoverSumpPumpStarts` (counter), `ShearPinStatus` (`OK`/`BROKEN`), `WicketGateBreakawayAlarm` |
| `Vibration/UGB`, `/LGB`, `/TGB` | `ShaftX/Overall_um_pp`, `ShaftY/Overall_um_pp` (µm peak-to-peak) |
| `Vibration/Headcover` | `Vel_mm_s_rms` (mm/s) |
| `Generator` | `StatorTemp01..06`, `AirGapMin_mm` |
| `Counters` | `Starts`, `RunHours`, `EmergencyStops`, `LoadRejections` (kept in `data/ch_plc_counters.json`) |

74 topics per turbine. **Payload:**

```json
{"value": 61.4, "unit": "°C", "timestamp": "2026-10-20T12:00:00.000Z", "quality": "GOOD", "seq": 128734}
```

- `quality` is `GOOD`, `UNCERTAIN` or `BAD`. Only the context values use the other two (stale or
  never received customer data). A failing sensor (scenario G) stays `GOOD`: the PLC doesn't know.
- `seq` is one counter per PLC over every message it sends (process, waveform, events), so gaps
  are detectable. The CH asset viewer counts them.

### Waveform blocks (not retained)

The PLC does no spectral analysis. It publishes raw blocks so edge devices can run FFT, orbit and
envelope analysis themselves.

| Topic (after the serial) | Unit | Rate | Block | Every | Size |
|---|---|---|---|---|---|
| `Vibration/UGB/ShaftX/Waveform`, `ShaftY`, same for `LGB`, `TGB` (6 channels) | µm | 1 kS/s | 4 s = 4,000 samples | 30 s | ~25 KB each |
| `Vibration/DraftTube/Pressure/Waveform` | bar (gauge) | 100 S/s | 10 s = 1,000 samples | 30 s | ~8 KB |
| `Vibration/Headcover/Accel/Waveform` | m/s² | 10 kS/s | 0.5 s = 5,000 samples | 5 min | ~35 KB |

Plus every block of the turbine right away when a vibration or shear-pin alarm is raised (at most
once per 30 s). Interval, length and the number of detailed turbines are environment variables
(see [Configuration](Configuration)).

```json
{"timestamp": "2026-10-20T09:24:00.000Z", "seq": 22197, "sampleRate": 1000, "samples": 4000,
 "unit": "µm", "speedRpm": 300.2, "keyphasorIdx": [13, 213, 413], "trigger": "periodic",
 "values": [12.4, 13.1, ...]}
```

- `timestamp` is the time of the first sample; sample *i* is at `timestamp + i / sampleRate`.
- `keyphasorIdx` lists the sample index of each shaft revolution mark, so orbits and phase work
  without a separate channel. Empty when the shaft stands still.
- `trigger` is `periodic`, `alarm` or `manual`.
- **Rounding:** shaft displacement 1 decimal (µm), draft-tube pressure 3 decimals (bar),
  accelerometer 2 decimals (m/s²). The design basis says 1 decimal; bar and m/s² need more.

### Events, nameplate, status

| Topic (after the serial) | Retained | Content |
|---|---|---|
| `Events/Alarm` | no | One message per PLC alarm raised or cleared |
| `Events/ActiveAlarms` | yes | The list of active PLC alarm ids, after every change |
| `_meta/Nameplate` | yes | The digital nameplate |
| `_meta/Status` | yes | `ONLINE`, or `OFFLINE` (MQTT last will) — a plain string, not JSON |

```json
{"timestamp": "2026-10-20T12:14:03.000Z", "seq": 130211, "serial": "CH-FR-1987-0042",
 "alarmId": "TGB_PAD03_H", "state": "ACTIVE", "severity": "WARNING",
 "tag": "Bearings/TGB/PadTemp03", "value": 75.12, "limit": 75.0, "text": "TGB pad 3 temperature high"}
```

`state` is `ACTIVE` or `CLEARED`, `severity` `WARNING` or `CRITICAL`. The alarm ids and limits are
on [Failure modes](Failure-modes#ch-plc-alarm-limits).

The nameplate carries the serial, manufacturer, product line, model `CH-FR-V40-100`, rated power,
head, flow and speed, runner blades and wicket gates, the commissioning year, the PLC retrofit year
and firmware, the data model version, the customer (`id`, `name`, `site`, `unitName`, `unitTag`)
and the list of waveform channels with their rate, samples and interval.

## Data rates

About **18 KB/s per turbine** with the defaults (~74 messages/s): ~12 KB/s of process values (the
long topics count) and ~6 KB/s of waveforms. The customer tree adds ~7 KB/s. The live figures per
turbine are in the CH asset viewer, or:

```bash
curl -s localhost:8122/api/assets | python3 -m json.tool | grep -E '"(kbytes|msgs)_per_s"'
```

## Subscribing

```bash
mosquitto_sub -h localhost -p 1884 -t 'v1.0/CH/#' -v                       # the CH tree (busy)
mosquitto_sub -h localhost -p 1884 -t 'v1.0/DRWPA/CopperCanyon/Plant/#' -v  # plant values + events
mosquitto_sub -h localhost -p 1884 -t 'v1.0/CH/Fleet/+/+/+/Events/Alarm' -v # every CH alarm
```

Python ([paho-mqtt](https://pypi.org/project/paho-mqtt/) 2.x):

```python
import json, paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    p = json.loads(msg.payload)
    print(msg.topic, p["value"], p.get("quality"), p.get("seq"))

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="my-edge-device")
c.on_message = on_message
c.connect("localhost", 1884)
c.subscribe("v1.0/CH/Fleet/DRWPA/CopperCanyon/CH-FR-1987-0042/Bearings/#")
c.loop_forever()
```

Inside the compose network use host `mosquitto`, port 1883.
