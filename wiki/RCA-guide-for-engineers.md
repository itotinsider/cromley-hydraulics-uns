# RCA with Claude: a guide for engineers

> **Disclaimer.** This code is part of the [IT/OT Academy](https://itot.academy), offered by
> [The IT/OT Insider](https://itotinsider.com). It is a generated, vibe-coded system made **only for
> demo purposes**. It may not be used for anything other than demonstration or training: not in
> production, not connected to real equipment, and not as the basis for any real control, quality
> or maintenance decision.
>
> **Important: using your own company's data. This demo runs on public cloud services (Claude,
> GitHub). Before you repeat the exercise with real data from your own company, check that your
> company allows the service you want to use, and under which plan or contract. Know which data you
> may take out of company systems, and how to export, transfer and store it securely. Never upload
> or publish documents, data or results you are not authorised to share, such as confidential,
> personal, customer or export-controlled information. When in doubt, ask your IT, data or
> information security team before you start.**

The [RCA demo walkthrough](RCA-demo-walkthrough) shows a scripted run: `run_rca.sh` builds a
workspace and lets the bot go. This page is for a maintenance or reliability engineer who starts
from scratch, with only the documents and the historian export, and wants to do the same kind of
analysis by hand in Claude. It uses the Copper Canyon scenario A material as the example; the steps
are the same for a real plant.

## Before you start

- **Tool:** [Claude Code](https://claude.com/claude-code) (desktop app or terminal). It reads the
  PDFs and analyses the CSVs with Python. The scenario A historian is 13 MB of gzipped CSV: far too
  much to paste into a chat. Python 3 must be on the machine.
- **Real plant data:** check your organisation's rules for sending documents to an AI service, and
  which Claude plan or contract covers it. The Copper Canyon material is fictional.
- **Material for the example:** the document library
  [`rca-demo/library/`](https://github.com/itotinsider/cromley-hydraulics-uns/tree/main/rca-demo/library)
  and the historian export
  [`rca-demo/history/scenario-A/historian/`](https://github.com/itotinsider/cromley-hydraulics-uns/tree/main/rca-demo/history/scenario-A/historian).
  Never the `ANSWER-KEY.md` or `run.json`: they hold the answer.

## Step 1: one folder per case

```
RCA-2026-001/
  library/      manuals, schematics, bulletins, FMECA, PM plan, work orders, oil analysis,
                MOC register, shift log, procedures, previous RCA reports
  historian/    the data export for THIS event only, with a README and a tag list
  work/         empty: Claude's analysis scripts
  reports/      empty: the draft report
```

- **Only what a real investigator would have.** No answer key, no notes with a conclusion in them.
- **Describe the data** in `historian/README.md`: what each file is, the time zone, the sample
  rates, what the columns mean (`tags.csv` does part of this). A wrong time zone or a misread tag
  name causes more wrong conclusions than anything else.

## Step 2: the ground rules in a `CLAUDE.md`

Claude reads `CLAUDE.md` at the top of the folder at the start of every session. Copy
[`rca-demo/bot/CLAUDE.md`](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/rca-demo/bot/CLAUDE.md)
and adapt it. The rules that matter most:

1. **Role:** you are a co-analyst; the reliability engineer decides and signs off.
2. **Sources:** only this folder. If something is missing, list it as missing evidence; never fill
   the gap from general knowledge.
3. **Hypotheses** come from the FMECA; flag any that is not in it.
4. **Every claim cites its source:** file and row, document and section, or historian column and
   time window with the values. No citation, no claim.
5. **Check the measurement before blaming the machine** (OP-07): neighbouring pads, oil
   temperature, the second sensor element, cooling, operating point.
6. **Keep physical, human and latent roots apart.** "Operator error" is never a root cause. Where
   only an interview would tell, write the question to ask.
7. **Output** in the site's template (FRM-REL-02), following the RCA procedure (PRO-REL-01).

## Step 3: lock the folder down

Add `.claude/settings.json`, so nothing comes in from the web:

```json
{ "permissions": { "deny": ["WebFetch", "WebSearch"] } }
```

Open the folder in Claude Code. Leave the permission prompts on the first time: you see every file
Claude reads and every script it runs.

## Step 4: let Claude find its way around first

> Read library/README.md and historian/README.md. Tell me what documents and data you have, which
> unit and period the data covers, and what you think is missing for an RCA.

Check the answer against what you know. If Claude has misunderstood the folder now, the rest will be
wrong too.

## Step 5: the problem statement, nothing more

The prompt the demo uses:

> Start the Copper Canyon Dam RCA process for Unit 1 (CH-FR-1987-0042): CH PLC alarm TGB pad 3
> high-high at 3 Nov 2026 09:00, unit unloaded and stopped by the shift per OP-07.

Don't add your own theory. Write "probably the cooling again" and Claude goes looking for evidence
that confirms it.

## Step 6: work in stages, and check each one

The demo's headless run does everything in one go. By hand, stop after each stage:

| Stage | Ask for | What you check (scenario A) |
|---|---|---|
| 1. Timeline | Historian, CH PLC alarm log, SCADA journal and shift log merged into one timeline | The times agree; the 07:13 "No alarms" entry while the H alarm stood since 23:54 |
| 2. Hypotheses | Every FMECA failure mode that fits the symptoms | Nothing obvious missing: cooling loss, sensor fault, rough zone, misalignment |
| 3. Testing | One hypothesis at a time: data, numbers, verified or ruled out | The scripts in `work/` read the right columns and the right time window |
| 4. Measurement check | The OP-07 checks: neighbouring pads, oil, element A vs. element B | A real fault shows in the neighbours too; a sensor fault does not |
| 5. History | Oil analysis trend, work orders, MOCs, PM plan, previous RCAs | The deferred resample, MOC-2025-004, and why this is not a repeat of RCA-2023-004 |
| 6. Roots | Physical, human and latent roots, each with evidence | No blame on people; the systems behind the decisions are named |
| 7. Report | A draft in the template under `reports/` | Recommendations are concrete and each has an owner |

Two questions help at every stage: **"Show me the values and the script"** and **"What evidence
would prove this wrong?"**

## Step 7: review it like a colleague's draft

- **Spot-check citations:** open three or four of the cited work orders, lab results or manual
  sections and check they say what the report claims.
- **Ask what is missing:** "What evidence would you want that isn't in the folder?" That gives the
  list of interviews, inspections and samples to do next.
- **Ask about the blind spots.** The demo's bot run
  ([example](https://github.com/itotinsider/cromley-hydraulics-uns/tree/main/rca-demo/bot/example-scenario-A))
  scored 16/18 against the answer key and invented nothing, but missed that MOC-2025-004 was raised
  and approved by the same person, and the H alarm nobody saw for 9 hours. Expect a run to be solid
  but not complete.

## Step 8: close it out with the team

- **Interviews:** Claude prepares the questions, people answer them. In scenario A: the shift
  supervisors, whoever handled the oil results, and the MOC approver.
- **Sign-off:** the reliability engineer edits and signs the report, and it goes into
  `library/drwpa/rca-reports/`, so the next RCA can compare against it.

**Effort:** the demo's headless run took about 6 minutes and about USD 3. Working in stages with
checks takes an hour or two, instead of the days a manual RCA spends gathering evidence.

See also [RCA demo walkthrough](RCA-demo-walkthrough) and [Failure modes](Failure-modes).
