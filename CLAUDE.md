# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Cromley Hydraulics (CH)** at **Copper Canyon Dam**: the third ITOT.Academy demo environment. A
small fictional hydropower dam (operator: Desert River Water & Power Authority, DRWPA) whose three
CH Francis turbines (3 × 40 MW, 100 m rated head, 300 rpm) publish clean, well-structured data to
one local Mosquitto broker, over MQTT only. The brief is
`Cromley Hydraulics – Demo Environment Design Basis.md` (the "design basis"); keep it as written.

Siblings, same build philosophy:
- **Haltenberg (HCW)**, `../haltenberg-chemische-werke-uns`: DCS + OPC UA. Most conventions here
  (wiki, inventory, tests, ROADMAP, `.env` stacks) come from it.
- **Sweet Harmony (SHT)**, `../sweet-harmony-treats-uns`: plant-owner UNS over MQTT. The payload
  format, Mosquitto, MQTT Explorer seed and Node-RED setup come from it.

**The lesson is the machine-builder view:** an asset-centric OEM tree (`v1.0/CH/Fleet/…/<serial>/…`)
next to the customer's own ISA-95 tree (`v1.0/DRWPA/CopperCanyon/…`), on the same broker. Edge
analytics, transport, buffering, security and device management are deliberately **out of
scope**: they are what the edge / IIoT vendors bring in the next step of the case study.

Keep this file current. It is the main knowledge carrier between sessions.

**Other docs to keep current:**
- **The wiki (`wiki/*.md`):** the user documentation (18 pages). Update the page whose topic you
  change (new topic, scenario, screen, env var), and keep its examples working.
  - **Source in the repo, published by script:** `tools/publish_wiki.py [--dry-run]` copies
    `wiki/*.md` and `wiki/images/*.png` to `<repo>.wiki.git`. `.github/workflows/wiki.yml` runs it
    on every push to `main` that touches `wiki/**`. Never run it from a feature branch. The wiki
    repo only exists after a first page was created on GitHub in the browser.
  - **Links:** between pages by page name (`[Architecture](Architecture)`), to repo files by full
    GitHub URL, images as `images/<file>.png`. `test_wiki_links_resolve` checks pages and images.
  - **README** stays short: pitch, quick start, architecture sketch, links.
- **The design basis** is the brief, not as-built documentation. Deviations are listed below
  ("Deviations from the design basis") and in the wiki where users need them.

**Every component has a tested inventory of its interface, and every change is checked against
it.** `inventory/` lists both topic trees, the commands, the hardwired signals, the scenarios and
the HTTP routes. Look names up there instead of guessing; before renaming, check who uses it;
after a change, run the tests and regenerate it (`docker compose run --rm tests python tools/inventory.py`).

## Layout

```
ROADMAP.md               plans, ideas, claims and progress (read before starting work)
common/namespace.py      BOTH topic trees, commands, assets (serials), hardwired signals, CH context map
                         — single source of truth, copied into every image
common/turbine.py        CH-Francis design data shared by both simulators: efficiency hill, flow,
                         ρgQHη, rough zone, vortex rope intensity, cavitation index
common/mqttio.py         payload format, command parsing, reconnecting paho client (last will)
common/httpd.py          tiny stdlib JSON/static HTTP server + client (http_json)
common/store.py          latest values + ring-buffer trends (SCADA, viewer)
damsim/model.py          dam: reservoir, spillway, bottom outlet, intake, penstock, 3 units (state
                         machine, governor), plant controller, unit protection, dam SCENARIOS — no I/O
damsim/main.py           0.1 s loop, customer tree every 1 s (retained), Cmd subscriber, hardwired poll, HTTP :8123
chplc/model.py           CH turbine: bearings/cooling thermal, HPU, seals, generator, vibration +
                         waveform synthesis, PLC alarm limits, CH SCENARIOS — no I/O
chplc/main.py            one PLC per turbine (thread, MQTT client + LWT, seq), waveforms, HTTP :8125
scada/main.py            dam SCADA server: customer tree only, alarms, journal, trends, Cmd publisher, HTTP :8120
scada/web/index.html     hub (the only page that isn't a persona HMI)
scada/web/scada.html     the dam SCADA HMI (ISA-101, dark grey)
instructor/main.py       instructor station: proxies to the simulators over HTTP, HTTP :8121
instructor/web/index.html
chviewer/main.py         CH asset viewer: CH tree only, nameplates, values, events, raw waveforms, HTTP :8122
chviewer/web/index.html
tools/offline_sim.py     dam + CH models coupled in-process, faster than real time (Sim = test harness)
tools/inventory.py       generates inventory/ from the sources of truth (stdlib only)
tools/publish_wiki.py    copies wiki/ to the GitHub wiki repo and pushes (the Action runs it)
inventory/               GENERATED interface inventory (README.md is hand-written)
tests/                   pytest: test_inventory, test_contracts, test_behaviour, test_e2e (+ Dockerfile)
wiki/                    the GitHub wiki's source; wiki/images/ screenshots
mosquitto/config/        broker config; mosquitto/data/ retained-message persistence (git-ignored)
nodered_data/flows.json  the only tracked file in nodered_data/ (hand-written, 3 tabs)
mqtt_explorer_data/settings.json   the seeded "Copper Canyon Dam" connection (only file tracked there)
data/                    bind mount: ch_plc_counters.json (git-ignored)
exports/                 bind mount: CSVs Node-RED writes (git-ignored)
```

## Commands

```bash
docker compose up -d --build          # REQUIRED after any code/web change (files are copied into images)
docker compose up -d --build --no-deps dam-scada   # one service only (without --no-deps compose also
                                         # rebuilds/recreates its depends_on services: running scenarios are lost)
docker compose down
docker logs -f ch-dam-sim             # / ch-ch-plc-sim, ch-dam-scada, ch-instructor, ch-ch-viewer
curl -s localhost:8120/api/state | python3 -m json.tool | head -40          # SCADA view
curl -s localhost:8122/api/assets | python3 -m json.tool | head -40         # CH viewer: rates, seq gaps
curl -s -X POST -H 'Content-Type: application/json' -d '{"path":"Powerhouse/Unit3/Cmd/Stop","value":true}' localhost:8120/api/cmd
curl -s -X POST -H 'Content-Type: application/json' -d '{"unit":"Unit1"}' localhost:8121/api/scenarios/shear_pin/start
curl -s -X POST localhost:8121/api/reset                                    # stop every scenario
mosquitto_sub -h localhost -p 1884 -t 'v1.0/CH/Fleet/+/+/CH-FR-1987-0042/Bearings/#' -v

# Offline (minutes of plant time in seconds, no containers):
docker run --rm -v "$PWD":/w -w /w python:3.12-slim python tools/offline_sim.py --minutes 30 --every 60 \
  --scenario tgb_bearing_degradation:Unit1@60 --cmd Plant/Cmd/MWSetpoint=90@600 \
  --cols Plant/TotalMW,Unit1:Bearings/TGB/PadTemp03,Powerhouse/Unit1/TurbineGuideBearingTemp

# Tests (compose profile "test": never started by `up`; mounts the working tree, no rebuild)
docker compose run --rm tests                                   # all, ~3 min
docker compose run --rm tests python -m pytest -m "not e2e"     # without the end-to-end processes
docker compose run --rm tests python -m pytest tests/test_contracts.py tests/test_inventory.py   # ~2 s
docker compose run --rm tests python tools/inventory.py         # regenerate inventory/
docker compose run --rm -e CH_TEST_SEED=3 tests python -m pytest tests/test_behaviour.py
docker compose run --rm -e CH_E2E_LOGS=1 tests python -m pytest -s tests/test_e2e.py   # print service logs
```

**MQTT checks from inside the network:** any service image has paho:
`docker run --rm --network cromley-hydraulics-uns_default --entrypoint python ch/dam-scada:latest -c '...'`
(network = compose project (folder) name + `_default`; broker host `mosquitto`, port 1883).

**Screenshots** (headless Chrome; Playwright is not installed). Every view has a deep link:
SCADA `/scada#overview|reservoir|unit/Unit1|governor|alarms|trends` (+ `?trend=a,b&range=60`),
viewer `#<serial>` and `#<serial>/wave/<path>`. Screenshots live in `wiki/images/`.
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1600,1000 --virtual-time-budget=6000 --screenshot=out.png "http://localhost:8120/scada#unit/Unit1"
```
MQTT Explorer needs a click on Connect: drive a `--remote-debugging-port` Chrome over CDP (see SHT's CLAUDE.md).

**Shell gotcha:** in zsh, `echo =====` fails ("= not found"). Pass JSON bodies literally.

## Architecture

**One broker, two trees, one copper link.**
- `dam-sim` owns the water and the units' operation (hydraulics, state machine, governor, plant
  controller, the customer's unit protection) and publishes the **customer tree**.
- `ch-plc-sim` owns the **machine physics** (bearings, cooling, HPU, seals, generator temperatures,
  vibration) and publishes the **CH tree**, one PLC per turbine. It copies its operating point
  (`NS.CH_CONTEXT`: MW, MVAr, gate, net head, speed, state, tailwater, + gate setpoint) from the
  customer tree, subscribe only. It never writes into the customer tree.
- **Hardwired** (`NS.HARDWIRED`): dual-element sensors. Element A (pad 1 of each bearing, total
  cooling flow, accumulator pressure) goes to the customer's unit controller; element B to the CH
  PLC. In the simulation the physics lives in ch-plc-sim, so it serves element A on
  `GET /api/hardwired` and dam-sim polls it every second: that HTTP call *stands for copper*, it is
  not a data interface. dam-sim republishes them as `Powerhouse/<unit>/ThrustBearingTemp`… and trips
  on them. A CH-side sensor fault (scenario G) only touches element B.
  - **Why:** the design basis wants bearings and cooling on the SCADA's unit screen, and real
    protection trips on bearing temperature and governor oil pressure. Duplicating the thermal
    model in dam-sim would let the two views disagree under faults.
  - **Staleness:** element A older than 5 s → `HARDWIRED_IO_FAULT`, the six tags are no longer
    published, protection is held (no trip on stale data), starts are refused.
- **Both simulators import `common/turbine.py`**, so flow, power, rough zone and vortex rope agree.
- **Two clocks.** dam-sim steps at 0.1 s and publishes every 1 s; each CH PLC steps and publishes
  every 1 s on its own thread. Nothing is lock-stepped; the CH PLC uses the last context it got.
- **The instructor** talks to both simulators over HTTP on the compose network (`DAM_URL`, `CH_URL`),
  never through the broker.

**Hidden faults (SHT/HCW rule).** Scenarios live only in the simulators (`SCENARIOS` in
`damsim/model.py` and `chplc/model.py`) and the instructor station. Never publish them, never add
a status topic, never let the SCADA, viewer or Node-RED read ground truth.
`test_hidden_faults_stay_hidden` enforces it (scenario ids, `ground_truth`, simulator ports).

## Namespace and payloads (`common/namespace.py`)

- **Customer tree** `v1.0/DRWPA/CopperCanyon/<Area>/<Module>/<Tag>`, 82 topics, retained, every 1 s,
  SHT payload `{"value", "unit", "timestamp"}` (no quality, no seq: a teaching contrast).
  `Plant/Events` (not retained) carries command results, refusals, state changes and trips.
- **Commands** `…/<Area>/[<Module>/]Cmd/<Command>`, 27 topics. Payload a bare value or
  `{"value": …}`. **Never retained** (a retained Start would replay on every restart). dam-sim
  subscribes `+/Cmd/#` and `+/+/Cmd/#`; unknown command topics produce a refused event.
- **CH tree** `v1.0/CH/Fleet/<CustomerId>/<SiteId>/<AssetSerial>/<Subsystem>/<Component>/<Metric>`:
  74 process topics per asset every 1 s (retained by default, `RETAIN_PROCESS_VALUES`),
  payload adds `quality` (GOOD/UNCERTAIN/BAD) and `seq` (one counter per PLC over every message:
  gaps are detectable). Plus 8 waveform channels, `_meta/Nameplate` (retained), `_meta/Status`
  (retained ONLINE, MQTT last will OFFLINE), `Events/Alarm` (not retained), `Events/ActiveAlarms`
  (retained).
- **Serial is identity:** `CH-FR-1987-0042` = Unit1, `…-0043` = Unit2, `CH-FR-1989-0051` = Unit3.
  The customer's unit name is only in the nameplate.
- **Context quality:** copied context older than 5 s is `UNCERTAIN` (last known value), never
  received is `BAD`. The PLC's own sensors stay GOOD (also during scenario G: the PLC doesn't know).
- **Rules (tested):** segments `[A-Za-z0-9_]`; no topic is both a value and a parent; no duplicates.
- **Waveforms** all sit under `Vibration/…/Waveform`: shaft X/Y at UGB/LGB/TGB (1 kS/s × 4 s, every
  30 s), draft tube (`Vibration/DraftTube/Pressure/Waveform`, 100 S/s × 10 s, every 30 s), headcover
  accelerometer (`Vibration/Headcover/Accel/Waveform`, 10 kS/s × 0.5 s, every 300 s). Defaults in
  `NS.ch_waveforms()`, overrides `WAVEFORM_<GROUP>_EVERY_S/_SECONDS`, `DETAILED_TURBINES`. Plus a full
  set on a vibration/shear-pin alarm (`trigger: "alarm"`, 30 s hold-off) and on
  `POST :8125/api/waveforms/<unit>` (`"manual"`). Payload keys in order: timestamp, seq, sampleRate,
  samples, unit, speedRpm, keyphasorIdx, trigger, values.

## Dam model (`damsim/model.py`)

- **Hydraulics:** reservoir area 8 km² at 385 m → 15 km² at 420 m; tailwater rating
  `303 + 0.08·Q^0.6` (304.5 m at ~135 m³/s), lag 120 s; penstock loss `1e-4·Q²`, branch `2e-4·Qu²`,
  trash rack DP (m) adds directly; penstock pressure = static + water hammer `-0.15·dQ/dt` (lag 1 s).
  The level moves a few cm/h in real time: realistic, and why scenarios H and flood compress it.
- **Spillway:** crest 410 m, `31.6·pos·(h-410)^1.5` per gate (~1,000 m³/s at 420 m), AUTO opens
  linearly 419 → 420 m at 0.5 %/s. **Bottom outlet AUTO** opens when units + spillway < 10 m³/s
  (target 12), closes above 15 (hysteresis). **Raker** runs when the trash rack DP ≥ 0.35 m.
- **Unit mechanics:** `dω/dt = T/2H`, 2H = 8 s; turbine torque `P_hyd·(2-ω)` (runaway at 2 pu),
  losses `0.015·ω²`, churning `0.15·ω²` once the gates are shut (≈2 min coastdown), brakes 0.10 pu
  below 30 % speed. Gate servo 15 s open / 6 s close per full stroke. On the grid, speed = f/50 and
  MW = `shaft_mw(gate, head)` + vortex-rope swing (±1.2 MW × rope intensity).
- **Governor:** online, gate = feed-forward `gate_for_mw(Pref)` + slow integral, Pref = ramped MW
  setpoint + 5 % droop on frequency; offline, a speed PI around the speed-no-load gate.
- **Sequence:** Starting (CoolingWater check after 10 s → InletValve 15 s → Breakaway gate 20 %) →
  SpeedNoLoad at 95 % speed (excite 5 s) → Synchronising (8 s, |Δf| < 1 %) → Generating (ramp
  12 MW/min up, 20 down). Stopping: unload at 40 MW/min, breaker, close gates, coast, brakes, inlet
  valve, Stopped. Tripped: breaker opens at once (load rejection peaks ~123 % speed), gates close,
  inlet valve closes, latched; Reset only at standstill with the inlet closed and no cause active.
  Start ≈ 100 s to the breaker + ~3 min ramp.
- **Permissives:** intake ≥ 99.5 %, level ≥ 384 m, hardwired OK, governor oil ≥ 55 bar.
- **Protection** (on element A, 5 s delay): bearing ≥ 90 °C trip, ≥ 80 alarm; governor oil < 48 trip,
  < 52 alarm; cooling flow < 56 L/s alarm; overspeed 145 % trip. Codes in `TRIP_CODES`/`WARN_CODES`,
  published as `ActiveAlarms`; the SCADA's `UNIT_CODES` must list exactly these (tested).
- **Plant controller:** plant SP = grid operator SP (`Plant/Cmd/MWSetpoint`, default 110) + AGC
  (±5 MW random targets every 2–5 min, ramp 3 MW/min). Split over PLANT-mode generating units:
  k units above the rough zone, n-k below (≥ 3 MW), max k that can make the total; **k is kept
  while it still works** (hysteresis, no chatter). Between two splits it takes the **nearest
  makeable total** and sets `MWSetpointReachable` false: it never parks a unit in the rough zone.
  - **Gotcha found while tuning:** at ~106 m net head the rough zone is ~10–33.3 MW, so 100 MW
    (3 × 33.3) is in the gap between "3 high" (≥ 100.4) and "2 high + 1 low" (≤ 94.3). Hence the
    default of 110 MW; at 100 the controller delivers 100.4 and flags it.
  - Units starting up are not counted until Generating, so the plant dips while one ramps (no
    AGC compensation). Accepted.
- **Noise** comes from `self.noise`, separate from `self.rng` (the process), so calling `values()`
  more or less often never changes the process.

## CH turbine model (`chplc/model.py`)

- **Bearings:** heat `q·speed^1.5·(load terms)·radial factors`, removed by cooling water
  (`UA·(flow/nominal)^0.8`, less with `cooler_fouling`) and 10 % to the powerhouse air (20 °C).
  Oil τ ≈ 900 s (longer with less cooling), pads τ 150 s, fixed per-pad offsets. Thrust + UGB + LGB
  on the GB circuit (12 L/s), TGB on the TB circuit (8 L/s), air coolers 60 L/s: 80 L/s total =
  the customer's flowmeter. Full load: pads ~60–70 °C, thrust oil ~52 °C.
- **Warm start:** on the first complete context a PLC `settle()`s to the steady state of the
  current operating point (a PLC retrofitted on a running unit measures a warm machine). Without
  it a fresh stack drifts for an hour.
- **HPU:** accumulator `ACC_K` 0.115 bar/L (a 40 L stroke = 4.6 bar, 5 strokes 63 → 40), pumps
  4 L/s, lead 58/63 bar, lag 54/61 bar, leak 0.08 L/s → ~6.6 starts/h normally. The start history
  is seeded with an hour of normal duty so `PumpStartsPerHour` (rolling hour) is right from boot.
- **Vibration:** runout 3 µm + 1X (mechanical ∝ speed², plus hydraulic ∝ gate, as vectors) + 2X
  (misalignment, ellipticity) + rope at 0.28 × 1X (TGB 30 µm × intensity) + blade pass 13 × 1X +
  noise. Overall pp is computed every second from 1 s of the same synthesiser at 250 S/s, so the
  overall values and the raw blocks always agree. Keyphasor indices mark each revolution.
- **Headcover:** velocity RMS from component amplitudes (blade pass, rope, cavitation, shear pin,
  crack); the accelerometer block has blade pass, 2× (crack), ±1X sidebands and cavitation bursts
  (high-passed noise modulated at blade pass).
- **PLC alarms** (`alarm_defs()`, 1 % deadband on clearing, some only while running): pads H 75 /
  HH 85, oil 65, cooling < 70 % nominal, HPU < 52 bar, starts > 15/h, filter > 2.5 bar, sump < 55 %,
  vibration 140 / 220 µm pp, headcover 4.5 mm/s, air gap < 10.5 mm, stator 120 °C, shear pin.
- **Counters** (Starts, RunHours, EmergencyStops, LoadRejections) follow the customer's
  `UnitState` transitions and persist in `data/ch_plc_counters.json` every 60 s.

## Scenarios

A–H from the design basis plus 11 more. Ramp scenarios take `options.duration_s` (the
instructor's "compression" input); clearing a scenario is the repair.

| | id | where | what the data shows |
|---|---|---|---|
| A | `tgb_bearing_degradation` | CH | one TGB pad (default 3) +32 K × sev^2.2; customer RTD (pad 1) sees ~+2 K |
| B | `cooling_strainer` | CH | all circuits → 30 % flow in 8 min; customer flow alarm; bearings head for a trip |
| C | `agc_rough_zone` | dam | one unit parked at 55 % gate; rope in draft tube and TGB, MW swings |
| D | `hpu_pump_wear` | CH | pump output −55 %, leak ×4: starts/h up, faster decay |
| E | `shear_pin` | CH | status BROKEN, TGB/headcover step, breakaway alarm while gates move |
| F | `unbalance` | CH | 1X ×4.2 UGB / ×3.4 LGB / ×1.8 TGB, +60° phase |
| G | `rtd_fault` | CH | one CH element drifts / flatlines / spikes, quality GOOD |
| H | `low_reservoir` | dam | level → 386.5 m at 1.5 m/min, head ~82 m, setpoint unreachable |

Further: `flood`, `generator_trip`, `trash_debris` (dam); `cooler_fouling`, `oil_water_ingress`,
`misalignment`, `hydraulic_unbalance`, `runner_crack`, `servo_seal_leak`, `shaft_seal_wear`,
`air_gap` (CH). Scenario ids must be unique across both simulators (the instructor merges them).

## Services

- **Dam SCADA (`scada/main.py`):** customer tree only (`test_scada_never_reads_the_ch_tree`). Alarm
  engine ISA-18.2-style (`ALARMS` limits with on-delays + unit codes + `COMM_DAM` stale), an alarm
  stays listed until cleared *and* acked. Journal: SCADA events + `Plant/Events`. Trends in memory
  (`common/store.py`: 2 h at 1 s, 48 h at 1 min); a restart starts empty. Commands: `POST /api/cmd`
  → MQTT with `source: "SCADA operator"`.
- **CH viewer (`chviewer/main.py`):** CH tree only. Counts msgs/s, KB/s and seq gaps per asset
  (retained messages are excluded from the gap count). No analytics on waveforms, on purpose.
- **Instructor (`instructor/main.py`):** merges both simulators' scenarios, proxies start/stop,
  `POST /api/reset` stops everything everywhere.
- **Node-RED** (`nodered/node-red:4.1.4`, core nodes only, `FLOWS=flows.json`): three hand-written
  tabs with numbered comments: *Data rate per tree*; *Bearing pads → 1-min CSV*
  (`exports/ch_bearings_1min.csv`, GOOD quality only: L3 model training data); *Draft tube block →
  dominant frequency (example)*, a plain DFT that flags the vortex rope. The third is labelled as
  edge-vendor territory. Regenerate by hand-editing `flows.json`; the contract test checks every
  `mqtt in` topic matches the inventory and every CH path in the functions exists.
- **MQTT Explorer** (`browser-1.0.3`): `mqtt_explorer_data/settings.json` seeds one connection
  (`mosquitto:1883`, `v1.0/DRWPA/#` + `v1.0/CH/#`). Never commit connections added in the UI
  (`git update-index --skip-worktree mqtt_explorer_data/settings.json` locally).
- **Mosquitto** `2.0.22`, anonymous, persistence on (retained values survive a broker restart; delete
  `mosquitto/data/mosquitto.db` to start clean).

## Tests and the interface inventory

**Goal (as in HCW):** consistent behaviour and stable interfaces as the model grows, not a perfect
training simulator. One trusted inventory per component, checked by tests; the inventory is
generated, never edited.

| File | What | Time |
|---|---|---|
| `test_inventory` | committed `inventory/` == code (full diff on failure) | 1 s |
| `test_contracts` | namespace rules; dam/CH publish exactly their trees; hardwired, context, commands, SCADA alarms, PLC alarms; scenario ids/letters; hidden faults; pages, Node-RED, MQTT Explorer seed and docs only name existing paths/topics; wiki links | 1 s |
| `test_behaviour` | `Sim`: steady state 30 min (no alarms, at setpoint, out of the rough zone), ranges, typical values, repeatability, stop/start, ESD + reset, minimum flow, plant controller sweep, LOCAL mode, refusals, hardwired loss, waveform shape, **one signature per scenario** (`SIGNATURES`; a new scenario fails `test_every_scenario_has_a_signature`), repair | ~140 s |
| `test_e2e` | mosquitto + all five services as processes: every inventory topic on the broker with the right payload keys and units, nothing extra, waveforms, hardwired, HTTP routes, SCADA command round trip, bare-value MQTT command, viewer, instructor + a hidden scenario, killing the CH PLCs (last will, hardwired fault, no trip) | ~20 s |

**Workflow per change:** run the tests before every commit; an interface change means a
regenerated inventory in the same commit and a sentence in the PR; a new scenario needs a
signature; after retuning, try another seed (`CH_TEST_SEED`).

**Gotchas found while building:**
- `httpd.http_json` must return `(None, …)` on connection errors: it used to raise `URLError`,
  which killed dam-sim's hardwired poll thread for good when ch-plc-sim started later.
- A last will forwarded to a *live* subscriber carries no retain flag (MQTT 3.1.1); check the last
  message, not only the retained store.
- Retained process values mean a new subscriber sees a full tree at once, including from a
  stopped simulator: always look at `timestamp` (the SCADA marks values stale after 5 s).

## Deviations from the design basis (decided while building)

- **Data rate:** ~12 KB/s process + ~6 KB/s waveforms per turbine (≈18 KB/s, 74 msg/s), not ~7 KB/s:
  long topics at 1 s dominate. Kept; it is itself a lesson (topic overhead, report by exception).
- **Waveform rounding:** shaft µm 1 decimal as specified; draft tube bar 3 and accelerometer m/s² 2
  decimals (1 decimal would erase the signal).
- **Additions** to the customer tree: `Reservoir/Volume`, `Plant/MWSetpointReachable`,
  `Plant/AGCEnabled`, `Intake/RakerRunning`, `Penstock/Flow`, `…/Mode`, and per unit `ControlMode`,
  `MWSetpoint`, `MVAr`, `GateSetpoint`, `NetHead` and the six hardwired tags. To the CH tree:
  `_meta/Status`, `Events/ActiveAlarms`. All waveforms under `Vibration/`.
- **Threads, not processes:** "one process per CH turbine" is one thread per PLC with its own MQTT
  client, session, last will and seq, in one container.
- **Customer protection** is fed by the hardwired element A (see Architecture).

## Conventions carried over from HCW/SHT

- **Packaging:** one `docker compose up -d --build`; Python 3.12-slim, `USER nobody`, one pinned
  `requirements.txt` (paho-mqtt 2.1.0 only; everything else is the standard library). Images
  pinned (`eclipse-mosquitto:2.0.22`, `nodered/node-red:4.1.4`, `smeagolworms4/mqtt-explorer:browser-1.0.3`).
- **Compose:** build context is the repo root so every image copies `common/`. `.env` (git-ignored)
  sets `CH_STACK` and `CH_*_PORT` for a second stack (see the compose header).
- **Ports:** host 8120 hub + SCADA, 8121 instructor, 8122 viewer, 1884 MQTT, 1881 Node-RED,
  4001 MQTT Explorer; internal only 8123 dam-sim, 8125 ch-plc-sim.
- **Networking:** services reach each other by compose service name (`mosquitto`, `dam-sim`,
  `ch-plc-sim`), never localhost.
- **Settings:** env vars with code defaults, documented in the wiki's Configuration page.
- **Web:** self-contained `web/*.html`, vanilla JS, no build, no CDN. The hub is navigation; persona
  pages link back with `⌂ All systems`. Reference data from `/api/config`, not hardcoded. SCADA:
  ISA-101 dark grey, saturated colour only for alarms (P1 red, P2 amber, P3 violet, stale magenta).
  Instructor: dark violet ("simulator side of the glass"). Viewer: CH teal brand. Never rebuild an
  open form on a poll; no browser dialogs (inline arm-then-confirm).

## Not built yet / open

Ideas are tracked in `ROADMAP.md`. Deliberately not built (vendor scope): edge analytics, transport
off site, buffering, TLS/ACLs, device management, consent filtering. Not modelled: the Kaplan and
Pelton lines, excitation/switchyard detail, the intake raker and gate hoists as CH assets, seasons
beyond the cooling-water diurnal swing. The vortex-rope calibration still needs a confirmed citation
(design basis caveat).

## Roadmap and parallel work

Plans, ideas and progress live in **`ROADMAP.md`**. Several people and agents work in parallel:
work in your own git worktree on your own branch (and your own `.env` stack), check `ROADMAP.md` on
`main` and the other branches first, claim the item in your branch's first commit, and never move
an idea to Planned or take someone else's item without Willem or David. Lasting knowledge from a
finished item belongs in this file; `ROADMAP.md` keeps only a summary.
