# RCA demo: Copper Canyon Dam document set

A document library for building and demonstrating a **root cause analysis (RCA) bot** for
maintenance and reliability engineers on top of the Copper Canyon Dam environment. The bot belongs
to Copper Canyon Dam's own team (DRWPA); the turbine manuals come from the supplier, Cromley
Hydraulics. Everything is fictional and for training only.

## Folders

| Folder | For | Give it to the bot? |
| --- | --- | --- |
| `library/` | The documents and records the bot reads: supplier manual, schematics and service bulletin; DRWPA asset register, FMECA, PM plan, work orders, oil analysis, MOC register, shift log, procedures and three previous RCA reports | **Yes** (plus the live broker) |
| `history/<scenario>/historian/` | Recorded historian export for one scenario: weeks of both trees up to and after the failure | **Yes**, only the one being investigated |
| `history/<scenario>/run.json` | What the recorder did: timeline, fault profile, event time, the prompt | **No**, presenters only |
| `bot/` | The bot's instructions (`CLAUDE.md`), the grading prompt and an example run (`example-scenario-A/`: chat answer, report, grade) | Its `CLAUDE.md` only |
| `run_rca.sh` | Builds an isolated workspace and runs the bot, optionally grades the report | No |
| `replay.sh` | Replays a recorded history on the running stack: the operator's view in the SCADA and the CH viewer | No |
| `ANSWER-KEY.md` | Story, people, planted clues and the expected RCA per demo scenario | **No**, presenters only |
| `../Maintenance & Reliability Engineering – Background for the CH RCA Bot.md` | The brief this demo was built from: M&R background and design rules for the bot (kept as written) | No |
| `build/` | Generators and Markdown sources for the PDFs, CSVs and the historian | No |

Start with `library/README.md`, the library index.

## Demo scenarios

The library is built around three instructor scenarios (settings in `ANSWER-KEY.md`):

| Scenario | Unit | What the bot should conclude, in short |
| --- | --- | --- |
| A, bearing degradation | Unit 1, TGB pad 3 | Real developing bearing failure; cooling and sensor fault ruled out; latent roots in maintenance decisions |
| G, sensor fault | Unit 3, TGB pad 2 | Measurement fault, not the bearing; do not stop the unit |
| C, rough-zone operation | Unit 2 | Operating decision, not a broken part; latent root in the change process |

The bot must never see the instructor station or this folder's answer key: hidden faults stay hidden.

## Rebuilding

```bash
python3 rca-demo/build/generate_records.py   # CSVs in library/drwpa/records/ (deterministic)
python3 rca-demo/build/render_pdf.py         # PDFs from build/src/*.md (ReportLab)
python3 rca-demo/build/draw_schematics.py    # CH-DOC-DWG-0102 schematic sheets
```

Requires Python 3 with `reportlab` and `pypdf` (without `pypdf` the PDFs get the build date and
ReportLab as producer instead of the document date and author). Without installing anything:
`docker run --rm -v "$PWD":/w -w /w python:3.12-slim sh -c "pip install -q reportlab pypdf && python rca-demo/build/render_pdf.py"`.
Values (limits, normal ranges, rough zone) match the
simulators (`common/turbine.py`, `chplc/model.py`, `damsim/model.py`); change them together.

## Historian data

`build/record_history.py` runs the dam and CH models coupled in-process (`tools/offline_sim.py`,
~8 s per plant hour) along the story the library tells: Unit 2's annual inspection 18–22 Oct, the
Unit 3 strainer after rain on 21 Oct, weekday evening peaks at 120 MW, the Unit 2 rough-zone trial
from 06:00 on 3 Nov. On top of that it plays one failure and the shift's response.

| Scenario folder | Period (plant time, MST) | Failure | Event |
| --- | --- | --- | --- |
| `history/scenario-A/` | 13 Oct – 3 Nov 2026 11:30 | Unit 1 TGB pad 3 loses its oil film: slow creep from 14 Oct, faster from 1 Nov | CH H alarm unseen overnight; HH 09:00 on 3 Nov; OP-07: load to 34 MW at 09:14, controlled stop 09:48 |

The fault follows a severity profile (`SEV_A`, a P-F curve) instead of the scenario's linear ramp.
Output: 1-minute averages for the whole period and 1-second values from 08:00 on the event day,
per tree (`customer_*`, `<serial>_*`), gzipped, plus the SCADA event journal, the CH PLC alarm log
and `tags.csv`. Deterministic for a given `--seed`; `--start 2026-11-02` records only the last day
(about 5 minutes, for tuning the timing).

```bash
docker run --rm -v "$PWD":/w -w /w python:3.12-slim python rca-demo/build/record_history.py   # ~75 min
```

## Walkthrough: what the control room saw (scenario A)

The full walkthrough with screenshots, documents and the bot's answer is the wiki page
[RCA demo walkthrough](https://github.com/itotinsider/cromley-hydraulics-uns/wiki/RCA-demo-walkthrough).

```bash
docker compose up -d --build     # if the stack is not running
rca-demo/replay.sh               # ~19 min; Ctrl-C stops, the simulators start again either way
```

`replay.sh` stops dam-sim and ch-plc-sim and publishes the recorded history instead
(`build/replay_history.py`): every wall second the latest recorded values of both trees, plus the
SCADA events and CH PLC alarms. Default: 2 Nov 22:00 to 3 Nov 10:15 at 120× (two plant minutes per
second), 08:55–10:00 at 5×. Payload timestamps are the wall clock, so the SCADA's clock, trends and
journal agree; the terminal prints the plant time (MST), the alarms and the shift log entries as they
come up. Open the SCADA on Unit 1 (`http://localhost:8120/scada#unit/Unit1`) and the CH viewer on
`CH-FR-1987-0042` (`http://localhost:8122/#CH-FR-1987-0042`) side by side.

| Plant time | SCADA (control room) | CH viewer (second screen, no horn) | Shift log |
| --- | --- | --- | --- |
| 2 Nov 23:54 | U1 TGB 65.5 °C, no alarm | Pad 3 H alarm (75 °C), red badge | nothing: unseen |
| 3 Nov 06:00 | Unit 2 trial: U1 to ~42 MW, TGB to ~70 °C | Pad 3 ~80 °C | 06:05 trial started |
| 07:13 | no alarm | H alarm still standing | "No alarms" |
| 09:00:29 | U1 TGB 70.3 °C, no alarm | Pad 3 HH (85 °C) | |
| 09:03–09:14 | | the supervisor checks pads 2/4, oil, element A/B, cooling, gate, vibration | HH found by chance, OP-07 checks |
| 09:14:30 | U1 to 34 MW (journal: local MW setpoint) | pad 3 falls slowly, HH clears 09:16 | reduced to 34 MW |
| 09:48–09:51 | U1 stopping → stopped | pad 3 drops to its neighbours | controlled stop |

The point: the control room's only TGB reading is pad 1, which never left the normal band. Everything
that mattered was on a screen nobody was assigned to watch.

Options: `--from/--to` (plant time), `--speed`, `--slow-from/--slow-to/--slow-speed`, e.g.
`rca-demo/replay.sh --from "2026-11-03 08:50" --slow-speed 1` for the event in real time. `--pause-at
"2026-11-03 09:01,2026-11-03 09:52" --pause-s 60` holds the screens at those moments. Not
replayed: waveforms (the viewer shows the last live blocks) and the CH nameplates (retained from the
live stack). SCADA trends mix the live data from before the replay with the replay's.

## Running the RCA bot (Claude Code)

```bash
rca-demo/run_rca.sh scenario-A --interactive   # build the workspace, then chat yourself
rca-demo/run_rca.sh scenario-A --grade         # headless run, report + score against the answer key
```

The script copies `library/`, the scenario's `historian/` and `bot/CLAUDE.md` into a new folder
under `~/ccd-rca/` (outside the repo, so the repo's `CLAUDE.md` with the scenario list is never
loaded), with a `.claude/settings.json` that denies reading the repo and the web. In it, Claude
Code reads the PDFs, analyses the CSVs with `python3` and writes `reports/RCA-2026-xxx.md` in
the DRWPA template. The prompt names only the unit, the alarm and the time (from `run.json`).
Headless runs also keep `transcript.jsonl` (every tool call) and `answer.md`. `--grade` scores the
report in a separate call that sees the answer key; the bot's run never does.

The isolation is a convention plus permission rules, not a sandbox: Bash `python3` could still
read files elsewhere. Check `transcript.jsonl` when a result looks too good.

## Not included yet

- Histories for scenarios G and C (same recorder, another failure and response).
- Live broker access for the bot (an MQTT MCP server), and waveform snapshots at the event.
