# RCA demo: Copper Canyon Dam document set

A document library for building and demonstrating a **root cause analysis (RCA) bot** for
maintenance and reliability engineers on top of the Copper Canyon Dam environment. The bot belongs
to Copper Canyon Dam's own team (DRWPA); the turbine manuals come from the supplier, Cromley
Hydraulics. Everything is fictional and for training only.

## Folders

| Folder | For | Give it to the bot? |
| --- | --- | --- |
| `library/` | The documents and records the bot reads: supplier manual, schematics and service bulletin; DRWPA asset register, FMECA, PM plan, work orders, oil analysis, MOC register, shift log, procedures and three previous RCA reports | **Yes** (plus the live broker) |
| `ANSWER-KEY.md` | Story, people, planted clues and the expected RCA per demo scenario | **No**, presenters only |
| `build/` | Generators and Markdown sources for the PDFs and CSVs | No |

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

## Not included yet

**Historian data.** The broker has live values and the SCADA keeps 48 h of trends in memory;
an RCA needs the weeks before an event. A recorded dataset (for example from
`tools/offline_sim.py`) or a small historian service is the next step.
