# Customer data vs. machine-builder data

This is the core lesson of Cromley Hydraulics. Two parties look at the same turbine, from the same
broker, and need very different data.

## Two trees side by side

| | Customer tree | CH tree |
|---|---|---|
| Owner | DRWPA, the dam owner | Cromley Hydraulics, the machine builder |
| Root | `v1.0/DRWPA/CopperCanyon` | `v1.0/CH/Fleet/DRWPA/CopperCanyon/<AssetSerial>` |
| Organised by | Where things are in the plant (ISA-95: area, module) | Which asset it is (serial number), then subsystem and component |
| Example | `.../Powerhouse/Unit1/MW` | `.../CH-FR-1987-0042/Bearings/TGB/PadTemp03` |
| Published by | The dam simulator (unit controllers, plant controller) | One CH PLC per turbine |
| Used by | The dam SCADA, the grid operator | CH's service engineers, edge devices, analytics |
| Size | 82 measured topics for the whole dam, plus 27 command topics | 74 process topics per turbine, 8 waveform channels, alarms, nameplate, status |
| Rate | 1 s | 1 s process values; waveform blocks every 30 s (accelerometer every 5 min) and on alarm |
| Payload | `{"value", "unit", "timestamp"}` (the Sweet Harmony format) | the same plus `"quality"` and `"seq"` |
| Questions it answers | Is the plant producing what the grid asked? Is anything tripping? Is the dam safe? | How healthy is my machine? What will fail, when? What should the next service visit do? |

**Why by serial number?** A machine builder thinks in assets: the serial
`CH-FR-1987-0042` stays the same when the customer renames "Unit 1" or the unit is refurbished.
The customer's name only lives in `_meta/Nameplate` (`customer.unitName`, `customer.unitTag`).

| Unit (customer) | Serial (CH) | Commissioned |
|---|---|---|
| Unit1 | CH-FR-1987-0042 | 1987 |
| Unit2 | CH-FR-1987-0043 | 1987 |
| Unit3 | CH-FR-1989-0051 | 1989 |

## Context: subscribe only

A bearing temperature means little without the operating point. Each CH PLC subscribes a few
customer topics and republishes them under `Context/`, with its own quality and seq:

| CH `Context/…` | Copied from the customer tree |
|---|---|
| `MW`, `MVAr` | `Powerhouse/<unit>/MW`, `MVAr` |
| `GatePosition_pct` | `Powerhouse/<unit>/GatePosition` |
| `NetHead_m` | `Powerhouse/<unit>/NetHead` |
| `Speed_rpm` | `Powerhouse/<unit>/Speed` |
| `UnitState` | `Powerhouse/<unit>/State` |
| `TailwaterLevel_m` | `River/TailwaterLevel` |

Also `Governor/HPU/GateSetpoint` comes from `Powerhouse/<unit>/GateSetpoint`. A context value
older than 5 s becomes `UNCERTAIN` (last known value), never received `BAD`. The CH PLC **never
writes into the customer tree**.

## The overlap: dual-element sensors

A few sensors are dual-element: element A goes to the customer's unit controller (protection),
element B to the CH PLC. The customer gets one RTD per bearing (pad 1), one cooling water flow
meter and the governor oil pressure; CH gets every pad, every circuit and much more. See the
table on [Architecture](Architecture#the-hardwired-link).

That is why the two parties notice faults at different times:

| Scenario | Customer sees | CH sees |
|---|---|---|
| A. TGB pad 3 degrading | Its pad-1 RTD rises ~3 K: nothing alarms | Pad 3 climbs from ~64 to ~95 °C; pad-to-pad spread grows; PLC alarms at 75 and 85 °C |
| B. Cooling-water strainer | Cooling water flow low within minutes; bearing alarms later; a trip if nobody acts | The same, per circuit, plus the oil cooler outlet and every pad |
| F. Unbalance | Nothing: the customer has no vibration probes | 1X amplitude ~4×, phase shift, PLC vibration alert |
| G. CH RTD drift | Nothing: element A is fine | One pad drifts +20 °C while its neighbours don't, quality still GOOD |

## Payloads, retained messages, last will

- **Customer:** `{"value": 36.65, "unit": "MW", "timestamp": "2026-10-20T12:00:00.000Z"}`, retained.
- **CH:** `{"value": 61.4, "unit": "°C", "timestamp": "...", "quality": "GOOD", "seq": 128734}`,
  retained by default (`RETAIN_PROCESS_VALUES`). `seq` counts every message one PLC sends, so a
  subscriber can detect gaps. Waveforms and alarm events are not retained.
- **Last will:** each CH PLC's MQTT session sets `_meta/Status` to `OFFLINE` if it disappears, and
  publishes `ONLINE` (retained) when it connects. The customer tree has no such status: the SCADA
  detects stale data by age.

Full formats on the [Namespace](Namespace) page.

## Who owns the data?

Notes for discussion, not legal advice:

- Under the **EU Data Act**, users of connected products have data access rights since
  12 September 2025, and products placed on the market after 12 September 2026 must offer access
  by design.
- CH may only use non-personal product data under an agreement with the customer.
- Selling data to third parties needs the customer's consent; anonymised fleet benchmarks are more
  realistic than raw data.

## The question for vendors

Everything is on one broker, with no security. A real site must keep customer control data and
machine-builder monitoring apart, and send off site only what was agreed. Each edge vendor answers:

- How do you **scope** what leaves the site to the CH tree (or an agreed subset)?
- How do you guarantee nothing is ever written into the customer tree?
- How do you respect the customer's consent when it changes?

See the [Edge vendor brief](Edge-vendor-brief) and [Business model](Business-model).
