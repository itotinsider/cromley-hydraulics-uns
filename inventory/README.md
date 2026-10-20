# Interface inventory

Everything one CH component exposes to another, in one place: the customer tree, the command
topics, the CH asset tree (process values, waveforms, nameplate, status, events), the hardwired
signals, the instructor scenarios and every HTTP route.

**Generated, never edited by hand.** Each component keeps its own source of truth (table below).
`tools/inventory.py` reads them all and writes these files. The tests fail as soon as the code and
this folder disagree, so every interface change shows up as a diff in the PR:

```bash
docker compose run --rm tests python tools/inventory.py           # regenerate after a change
docker compose run --rm tests python tools/inventory.py --check   # only compare
```

## Who owns what

| Interface | Source of truth (the only place to change it) | Written by → read by | File |
|---|---|---|---|
| Customer tree | `common/namespace.py` `customer_tags()` | dam-sim → dam SCADA, CH PLCs (context), Node-RED, MQTT Explorer | `customer.json` |
| Command topics | `common/namespace.py` `customer_commands()` | dam SCADA, any client → dam-sim | `commands.json` |
| CH asset tree | `common/namespace.py` `ch_tags()`, `ch_waveforms()`, `ASSETS` | CH PLCs → CH viewer, Node-RED, edge devices | `ch.json` |
| CH PLC alarms | `chplc/model.py` `Turbine.alarm_defs()` | CH PLCs → `Events/Alarm` | `ch.json` (`plc_alarms`) |
| Hardwired signals | `common/namespace.py` `HARDWIRED` | CH PLC sim (`/api/hardwired`) → dam-sim | `hardwired.json` |
| Instructor scenarios | `damsim/model.py`, `chplc/model.py` `SCENARIOS` | simulators → instructor station only | `scenarios.json` |
| HTTP routes | each service's `main.py` | services → pages, instructor, scripts | `api.json` |
| Every concrete topic | (joined from the above) | for people looking up a topic | `topics.csv` |

A component only uses names that exist where they come from, for example:

- the dam simulator publishes exactly the customer tree, the CH PLC exactly the CH tree;
- the context the CH PLC copies exists in the customer tree, and it never writes there;
- every hardwired signal has a CH element and a customer topic;
- the SCADA's alarm limits and the unit controller codes exist;
- every path the SCADA and viewer pages, the Node-RED flow and the docs name exists.

`tests/test_contracts.py` checks all of these.

**Hidden faults stay hidden:** scenario ids and ground truth never appear in a topic, in the
SCADA, the CH viewer or the Node-RED flow. The instructor station talks to the simulators over
HTTP, never over MQTT.

## Changing an interface

1. Change the source of truth, plus everything that uses the name: pages, flows, docs.
2. Regenerate the inventory, run the tests, and commit both together.
3. In the PR, say what was added, renamed or removed. A rename or removal breaks whatever reads
   the old name: edge devices, Node-RED, MQTT Explorer bookmarks, saved trends.
4. **Topic segments** are `[A-Za-z0-9_]` only, and a topic that carries a value never has children
   (`test_no_leaf_is_also_a_branch`).

## Files

- `customer.json`: every customer tag (unit, type, decimals, range, source: model or hardwired),
  the payload, the events topic, the unit states and modes.
- `commands.json`: every command topic with its payload type, range and enum values.
- `ch.json`: assets (serial → customer unit), the payload with quality and seq, every process tag,
  the copied context, the waveform channels (rate, default length and interval, decimals), meta
  and event topics, and the PLC's alarm limits.
- `hardwired.json`: the dual-element signals, their CH element and customer topic.
- `scenarios.json`: dam and CH scenarios (letter, group, kind, duration, options) and the A–H map.
- `api.json`: per service its port, whether it is on the host, its pages and GET/POST routes.
- `topics.csv`: one row per concrete topic on the broker: tree, topic, unit, type, retained,
  publisher, rate, description.
