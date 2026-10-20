# Cromley Hydraulics — Copper Canyon Dam demo environment

> **Disclaimer.** This code is part of the [IT/OT Academy](https://itot.academy), offered by
> [The IT/OT Insider](https://itotinsider.com). It is a generated, vibe-coded system made **only for
> demo purposes**. It may not be used for anything other than demonstration or training: not in
> production, not connected to real equipment, and not as the basis for any real control, quality
> or maintenance decision.

**Cromley Hydraulics (CH)** is a fictional machine builder with 75 years of dam hydraulics
experience. It now fits every major turbine with a modern PLC that speaks MQTT, to move from
reactive to proactive maintenance. This environment is a small, fictional hydropower dam,
**Copper Canyon Dam**, whose three CH Francis turbines publish clean, well-structured data to one
local Mosquitto broker.

It teaches the **machine-builder view**: an asset-centric OEM data model (the CH tree, keyed by
serial number) next to the customer's own ISA-95 tree, rich enough for edge vendors to show
predictive maintenance on it. It is the third ITOT.Academy environment, after
[Haltenberg](https://github.com/itotinsider/haltenberg-chemische-werke-uns) (DCS + OPC UA) and
[Sweet Harmony](https://github.com/itotinsider/sweet-harmony-treats-uns) (plant-owner UNS over MQTT).

![Dam SCADA overview](wiki/images/scada-overview.png)

**📖 Documentation: [the wiki](https://github.com/itotinsider/cromley-hydraulics-uns/wiki).**
New to dams? Start with
[Dams and turbines in brief](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Dams-and-turbines-in-brief).
The lesson in one page:
[Customer data vs. machine-builder data](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Customer-data-vs-machine-builder-data).

## Quick start

Needs Docker Desktop (or Docker Engine + Compose v2) and free ports 8120, 8121, 8122, 1884, 1881,
4001 (chosen so Haltenberg and Sweet Harmony can run alongside).

```bash
docker compose up -d --build
```

| What | Where |
|---|---|
| Hub (all systems) | http://localhost:8120 |
| Dam SCADA | http://localhost:8120/scada |
| Instructor station (hidden fault scenarios) | http://localhost:8121 |
| CH asset viewer (the machine builder's view) | http://localhost:8122 |
| MQTT broker (both trees, no auth) | `mqtt://localhost:1884` |
| Node-RED | http://localhost:1881 |
| MQTT Explorer | http://localhost:4001 |

Or open Claude Code in this folder and ask: `read the CLAUDE.md file and README.md file and set up the environment`.

Then take the [15-minute first tour](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Getting-started#a-first-tour-15-minutes).

## Architecture

```
 dam-sim ──────── customer tree  v1.0/DRWPA/CopperCanyon/…  ──────┐      ┌── dam-scada (:8120)
 (reservoir, spillway,                                            │      │   reads the customer tree,
  bottom outlet, 3 units,  ◄── Cmd topics ───────────────────────┤      │   sends Cmd topics
  plant controller)                                               ▼      │
      ▲  hardwired (element A, "copper")                   ┌────────────┐├── ch-viewer (:8122)
      │                                                    │ Mosquitto  ││   reads the CH tree
 ch-plc-sim ───── CH tree  v1.0/CH/Fleet/DRWPA/…/<serial>/… │   :1884    │├── Node-RED (:1881)
 (one CH PLC per turbine:  1 s values + raw waveforms ───► └────────────┘└── MQTT Explorer (:4001)
  thermal, HPU, vibration)   context ◄── (subscribe only)        ┊
                                                                 ┊  next step: edge / IIoT vendors
 instructor (:8121) ── HTTP, never MQTT ──► dam-sim, ch-plc-sim   ┊  (analytics, transport, buffering,
                                                                    security, device management)
```

More: [Architecture](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Architecture),
[Namespace](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Namespace),
[Edge vendor brief](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Edge-vendor-brief).

## For developers

```bash
docker compose run --rm tests                                   # all tests, ~3 min
docker compose run --rm tests python -m pytest -m "not e2e"     # without the end-to-end part
docker compose run --rm tests python tools/inventory.py         # after an intended interface change
```

- [CLAUDE.md](CLAUDE.md): how everything works, and the gotchas.
- [inventory/](inventory/README.md): every topic, command, hardwired signal, scenario and HTTP route, tested against the code.
- [ROADMAP.md](ROADMAP.md): plans and work in progress. Claim an item before you start.
- [wiki/](wiki/): the source of the wiki, published to GitHub on every merge to `main`.
  See [Development](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/Development).
- The original brief: [Cromley Hydraulics – Demo Environment Design Basis.md](<Cromley Hydraulics – Demo Environment Design Basis.md>).
