# Development

Developer knowledge (how each part works, why, and the gotchas) lives in
[CLAUDE.md](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/CLAUDE.md).
Plans and work in progress are in
[ROADMAP.md](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/ROADMAP.md):
propose an idea there, or claim an item before you start, so people and agents working in parallel
don't collide.

## Repository layout

| Path | What |
|---|---|
| `common/` | Shared by every image: `namespace.py` (both topic trees, the single source of truth), `turbine.py` (turbine design data), `mqttio.py`, `httpd.py`, `store.py` |
| `damsim/` | Dam simulator: `model.py` (physics, plant controller, dam scenarios), `main.py` (MQTT, hardwired polling, HTTP) |
| `chplc/` | CH PLC simulator: `model.py` (thermal, HPU, vibration, waveforms, PLC alarms, machine-fault scenarios), `main.py` (one PLC per turbine, MQTT, HTTP) |
| `scada/` | Dam SCADA server and pages (`web/index.html` hub, `web/scada.html`) |
| `instructor/` | Instructor station |
| `chviewer/` | CH asset viewer |
| `tools/` | `offline_sim.py` (both models coupled, faster than real time), `inventory.py` (generates `inventory/`), `publish_wiki.py` |
| `inventory/` | Generated interface inventory |
| `tests/` | The test suite |
| `wiki/` | The source of this wiki |
| `nodered_data/flows.json` | The Node-RED flows |
| `mqtt_explorer_data/settings.json` | The seeded MQTT Explorer connection |
| `mosquitto/config/` | Broker configuration |

After any code or web change: `docker compose up -d --build` (files are copied into the images).

## Offline simulation

`tools/offline_sim.py` couples the dam model and the three CH turbine models directly, without
broker or HTTP, and runs about 100× faster than real time:

```bash
docker run --rm -v "$PWD":/w -w /w python:3.12-slim python tools/offline_sim.py \
  --minutes 30 --every 60 --scenario tgb_bearing_degradation:Unit1@60 \
  --cols Unit1:Bearings/TGB/PadTemp03,Powerhouse/Unit1/TurbineGuideBearingTemp
```

- `--scenario id[:unit]@seconds` starts a dam or CH scenario;
- `--cmd <command path>=<value>@seconds` sends a command, e.g. `--cmd Plant/Cmd/MWSetpoint=80@600`;
- `--cols` takes customer paths, or `<unit>:<CH path>` for a CH tag;
- `--seed 7` makes a run repeatable.

## Tests

The model will keep growing, and the systems around it must keep agreeing. The tests guard stable
interfaces and consistent behaviour: no topic goes missing or changes without anyone noticing.

```bash
docker compose run --rm tests                                   # everything (builds the test image once)
docker compose run --rm tests python -m pytest -m "not e2e"     # without the end-to-end part
docker compose run --rm tests python tools/inventory.py         # after an intended interface change
```

The test container mounts the working tree, so nothing needs a rebuild after a code change, and it
doesn't touch the running stack.

| File | What it checks |
|---|---|
| `tests/test_inventory.py` | The committed [interface inventory](Interface-reference) still matches the code |
| `tests/test_contracts.py` | Every topic a component, page, flow or wiki page names exists in the namespace; hidden faults never reach MQTT |
| `tests/test_behaviour.py` | Both models coupled offline, faster than real time: steady state without alarms, start/stop, the plant controller, a signature for every instructor scenario |
| `tests/test_e2e.py` | The real programs with an embedded Mosquitto: every topic of the inventory is published, commands round-trip, waveform blocks have the right shape, the last will works |

**When a test fails:** an inventory diff means an interface changed; if you meant it, regenerate
the inventory and commit it with the change, and name every added, renamed or removed topic in the
PR. A new instructor scenario needs its expected signature in `tests/test_behaviour.py`.

## Editing this wiki

The wiki's source is the [`wiki/`](https://github.com/itotinsider/cromley-hydraulics-uns/tree/main/wiki)
folder in the repository, reviewed in pull requests like code. Don't edit pages on GitHub: the next
publish overwrites them. Screenshots live in `wiki/images/`, so image links work in the repo and in
the wiki alike.

Publishing is automatic: when a change to `wiki/` is merged into `main`, a GitHub Action
(`.github/workflows/wiki.yml`) runs `tools/publish_wiki.py`. By hand, from an up-to-date `main`:

```bash
python tools/publish_wiki.py --dry-run    # show what would change
python tools/publish_wiki.py              # copy wiki/ (pages and images) to the wiki repo, commit, push
```

Pages link to each other by page name (`[Architecture](Architecture)`), and to repository files by
full GitHub URL.
