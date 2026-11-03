# Copper Canyon Dam historian export

Desert River Water & Power Authority (DRWPA). Fictional, for training only.

Export from the site historian, which records both trees on the site MQTT broker. Times are plant
local time (MST, UTC-07:00, no daylight saving). Period: 2026-10-13 00:00 to 2026-11-03 11:30.

| File | Asset | Content |
| --- | --- | --- |
| `customer_1min.csv.gz`, `customer_1s.csv.gz` | Plant | DRWPA SCADA tree (`v1.0/DRWPA/CopperCanyon/…`) |
| `CH-FR-1987-0042_1min.csv.gz`, `CH-FR-1987-0042_1s.csv.gz` | Unit1 | CH monitoring PLC tree |
| `CH-FR-1987-0043_1min.csv.gz`, `CH-FR-1987-0043_1s.csv.gz` | Unit2 | CH monitoring PLC tree |
| `CH-FR-1989-0051_1min.csv.gz`, `CH-FR-1989-0051_1s.csv.gz` | Unit3 | CH monitoring PLC tree |
| `scada_events.csv` | Plant | SCADA event journal: commands, sequence steps, trips, refusals |
| `ch_plc_alarms.csv` | All units | CH monitoring PLC alarm log (raised and cleared) |
| `tags.csv` | | Every column: topic, engineering unit, description |

- `*_1min` files hold 1-minute averages (states, flags and alarm lists: last value in the minute)
  for the whole period. `*_1s` files hold raw 1-second values from 2026-11-03 08:00 to the end.
- One column per tag, named by its path below the tree prefix; `tags.csv` gives the full topic.
  CH columns are the same for every turbine.
- Waveforms are not archived; the overall vibration values (µm pp) are.
- CH PLC alarms are not shown in the control room; the SCADA journal only has the customer's own
  alarms and events.
