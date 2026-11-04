# Maintenance & Reliability Engineering – Background for the CH RCA Bot

Nov 3, 2026 · @Willem

## Summary

Maintenance and reliability (M&R) engineers will judge an RCA bot on one thing: does it follow their process and back every claim with evidence? Fluent explanations without verification are exactly what they are trained to distrust.

- **What they do.** Maintenance engineers keep assets running today; reliability engineers stop failures from coming back. Both think in failure modes, evidence and consequences, not in data models.
- **RCA is a process, not an answer.** It runs from a trigger, through preserved evidence and verified hypotheses, to physical, human and latent root causes, actions and an effectiveness check. A bot that names one cause and stops is doing what practitioners call shallow cause analysis.
- **FMEA is the bot's map.** An FMEA (or the RCM-style FMECA used in power and process plants) lists every credible failure mode with its effects and how it is detected. It bounds what the bot is allowed to suggest, which is the main defence against hallucination.
- **The Copper Canyon data is a good start, but not yet enough for RCA.** The broker has rich live data and 19 hidden fault scenarios, but no history: no historian, no work orders, no manuals, no previous RCAs. Those are what we generate next.

**Where the bot fits:** it is strong at the evidence half of RCA (timeline, trends, matching symptoms to failure modes, finding similar past events). It is weak at the human and latent roots (procedures, decisions, training), which need people and documents. Position it as an evidence-gathering co-analyst with a human sign-off, not as an automatic root-cause finder.

Note on naming: the repo calls the site **Copper Canyon Dam**; this doc uses that name.

## Maintenance vs. reliability engineers

The maintenance engineer restores and sustains; the reliability engineer analyses and prevents. In small plants one person does both, and the boundary is blurry everywhere ([Reliabilityweb](https://reliabilityweb.com/en/articles/what-is-the-difference-between-a-maintenance-engineer-and-a-reliability-engineer), [Accendo](https://accendoreliability.com/differences-between-maintenance-and-reliability-engineers-a-brief-literature-review/)).

|  | Maintenance engineer | Reliability engineer |
| --- | --- | --- |
| Core question | How do we get it running and keep it running? | Why does it fail, and how do we stop it recurring? |
| Horizon | Today to next shutdown | Months to asset life |
| Typical work | Troubleshooting breakdowns, job plans and procedures, PM execution, spares, shutdown scope, supporting technicians | RCA, FMEA/RCM, maintenance strategy, PM interval optimisation, condition-monitoring programme, bad-actor lists, Weibull/life analysis, spares strategy |
| Main tools | CMMS (work orders, PM plans), manuals, drawings, SCADA screens | CMMS history, historian trends, condition-monitoring data, FMEA/RCM software, RCA software, statistics |
| Measured on | MTTR, PM compliance, backlog, planned-maintenance % | MTBF, availability, repeat failures, cost of unreliability |

A common practice is to protect the reliability engineer from day-to-day firefighting, so the long-term work actually happens ([Plant Services](https://www.plantservices.com/management/leadership-skills/podcast/55274176/podcast-maintenance-vs-reliability-engineers-key-differences-and-how-they-work-together)). The reliability engineer typically owns the strategy, the maintenance engineer its execution ([Accendo, Isenhour](https://accendoreliability.com/podcast/rir/108-maintenance-engineer-vs-reliability-engineer-shon-isenhour/)).

**Other roles in an RCA:** technicians and operators (first-hand evidence), the maintenance planner (work orders, parts), the maintenance supervisor, and the OEM's service engineer. At Copper Canyon that last role is CH, which is exactly the new business model.

**KPIs they live by**

| KPI | Formula | Commonly cited target |
| --- | --- | --- |
| MTBF | Operating time ÷ number of failures | Rising trend (lagging indicator) |
| MTTR | Repair time ÷ number of repairs | Falling trend |
| Availability | MTBF ÷ (MTBF + MTTR) | Site-specific |
| PM compliance | PMs done on time ÷ PMs scheduled | ≥ 90% |
| Planned maintenance % | Planned hours ÷ total maintenance hours | ≥ 85% |

Targets are the SMRP-style values commonly quoted in industry guides ([Reliable Media](https://reliamag.com/guides/maintenance-reliability-kpi-reference/), [eWorkOrders](https://eworkorders.com/?p=68637)); they vary by industry and should be checked against the SMRP Best Practices document itself.

## Maintenance strategies and the P-F curve

M&R teams choose a strategy per failure mode, not per machine. RCA sits on top of all of them: it is how a team learns from the failures the strategy did not prevent.

| Strategy | When it fits | Example on a CH turbine |
| --- | --- | --- |
| Run to failure | Cheap, non-critical, no safety effect | Indicator lamp |
| Preventive (time-based) | Clear wear-out with age | Filter element change, cooling strainer cleaning |
| Condition-based / predictive | Failure gives warning that can be measured | Bearing pad temperature, shaft vibration, HPU pump starts per hour |
| Failure-finding | Hidden failures of protective devices | Testing the overspeed trip |
| Redesign / defect elimination | None of the above works, or RCA finds a design root | Upgrading a bearing, changing a procedure |

**Why condition monitoring matters:** the airline studies behind RCM (Nowlan & Heap, 1978) found that most items showed no clear wear-out age. Only about 11% of items had an age-related failure pattern, and only about 6% a pronounced wear-out zone ([Reliable Media](https://reliamag.com/topics/guides/six-failure-patterns-nowlan-heap)). Time-based replacement therefore helps a minority of failure modes; the rest need condition monitoring. Treat the percentages as illustrative: they come from 1960s aircraft data, and reliability statisticians have criticised how they were derived ([Accendo](https://accendoreliability.com/no-89-percent-of-failures-are-not-random/)).

**The P-F curve** describes one failure mode. P is the earliest point where a developing failure can be detected; F is when the asset can no longer do its job. The time between them, the P-F interval, is the window to plan and act ([Tractian](https://tractian.com/en/glossary/p-f-curve-potential-failure-curve)). Better detection moves P to the left and lengthens the window, which is the whole argument for CH's PLCs.

&#91;embedded content: P-F curve · turbine guide bearing, detection points P to F\]

For the RCA bot the curve matters in reverse: after a failure, the investigator walks back along the curve and asks when P was, which signals showed it, and why nobody acted.

## The RCA process

Root cause analysis (RCA, or RCFA for equipment failures) is a structured investigation that ends only when corrective actions are in place and proven to work. The common thread across methods is the same: define the event, preserve evidence, test hypotheses against facts, find all root causes, act, and verify.

&#91;embedded content: RCA process · 8 steps and a feedback loop\]

The FMEA feeds the hypothesis list at the start; what the RCA learns goes back into the FMEA at the end.

**Three kinds of root cause (PROACT, Reliability Center Inc.)**

- **Physical roots:** the tangible failure, e.g. a wiped bearing pad, a clogged strainer.
- **Human roots:** decisions or actions that triggered the physical root, e.g. a skipped strainer clean, a start before the bearing had cooled.
- **Latent roots:** the organisational systems behind those decisions, e.g. no written procedure, a PM interval stretched to save cost, no training ([PROACT reference guide](https://www.perlego.com/book/1639691/the-proact-root-cause-analysis-quick-reference-guide-pdf), [Plant Services case](https://www.plantservices.com/home/article/11332074/human-capital-how-one-team-used-the-proact-method-to-identify-the-real-root-causes-of-a-catastrophic-failure)).

Stopping at the physical root is failure analysis, not RCA. Stopping at "operator error" is blame, and kills participation in future RCAs.

**When to do an RCA (triggers).** Plants set explicit triggers, so effort matches the loss. A typical tiered policy from a mining operation: under 4 h unplanned downtime goes in a variance log; 4–24 h gets a quick 5 Whys by the tradesperson and supervisor; over 24 h gets a team RCA within 4 weeks with a reliability engineer, operator and OEM specialist where needed ([example policy](https://www.slideshare.net/slideshow/sirfrt-op-ex-rca2015b/59106322)). Other common triggers: safety or environmental events, repair cost above a threshold, and repeat failures of the same asset ([Isenhour](https://shonisenhour.blogspot.com/2011/07/triggering-success-with-root-cause.html)).

**Evidence: the 5 Ps.** Parts, Position, People, Paper and Paradigms ([Reliability Center](https://reliability.com/?p=1883)). For a turbine bearing that means the failed pads and oil samples, where things were found, interviews with operators and technicians, records (trends, alarms, work orders, procedures), and the beliefs that shaped decisions ("we always restart after a trip").

**Methods and when to use them**

| Method | Good for | Watch out |
| --- | --- | --- |
| 5 Whys | Simple, single-chain problems; quick triage | Follows one path; easily ends at opinion |
| Fishbone (Ishikawa) | Brainstorming many possible causes by category | Lists possibilities, proves nothing |
| Logic tree / cause-and-effect tree | Main tool for equipment RCA: event → modes → hypotheses, each verified or ruled out | Needs discipline to verify every branch |
| Fault tree analysis | Failures that need a combination of conditions (AND/OR) | Heavy; best for safety-critical systems |
| Timeline / sequence of events | Reconstructing what happened when | Depends on time-synced data |
| Is / is-not | Intermittent problems: why Unit 1 and not Unit 2? | Needs good comparison data |

A common sequence is fishbone to open up the cause space, then 5 Whys or a logic tree on the branches the evidence supports ([Learn Lean Sigma](https://www.learnleansigma.com/?p=17831), [Reliable Plant](https://www.reliableplant.com/Articles/Print/31171)).

**Typical RCA report contents:** event description and impact, timeline, team, evidence collected, logic tree with each hypothesis marked verified or ruled out (and how), physical / human / latent roots, recommendations with owners and dates, and how effectiveness will be checked. There is no return on an RCA until the actions are done and the result is proven ([Isenhour](https://shonisenhour.blogspot.com/2011/07/triggering-success-with-root-cause.html)).

## FMEA, FMECA and RCM

FMEA looks forward ("how could this fail?"), RCA looks back ("why did this fail?"). They feed each other: an RCA that finds a failure mode the FMEA missed should update the FMEA, and the FMEA tells the RCA team which hypotheses to test first.

**FMEA in one line per failure mode:** item and function → failure mode → effect → cause/mechanism → current prevention and detection controls → risk rating → recommended action.

**Risk rating.** Each failure mode is scored 1–10 on Severity (S), Occurrence (O) and Detection (D, where 10 means it cannot be detected). The classic Risk Priority Number is RPN = S × O × D. Its weakness: very different risks get the same number (S10·O2·D5 and S2·O5·D10 both give 100). The 2019 AIAG-VDA handbook therefore replaced RPN with Action Priority (High/Medium/Low from lookup tables that weigh severity first) and a 7-step approach ([Reliable Media](https://reliamag.com/topics/guides/how-to-perform-fmea), [Quality-One](https://quality-one.com/aiag-vda-fmea/)). AIAG-VDA is an automotive standard; asset-heavy industries still use RPN or a risk matrix, but the RPN critique is worth showing.

**FMECA and RCM in asset-heavy industries.** Power and process plants usually do FMEA inside Reliability-Centred Maintenance. SAE JA1011 (current revision 2024) says a process is only RCM if it answers seven questions in order ([Reliable Media](https://reliamag.com/guides/how-to-perform-rcm/)):

1. What are the functions and performance standards of the asset?
2. In what ways can it fail to fulfil its functions (functional failures)?
3. What causes each functional failure (failure modes)?
4. What happens when each failure occurs (effects)?
5. In what way does each failure matter (consequences: hidden, safety/environment, operational, non-operational)?
6. What should be done to predict or prevent each failure (proactive tasks)?
7. What if no suitable proactive task is found (default actions: failure-finding, redesign, run to failure)?

Questions 1–4 are the FMEA; questions 5–7 turn it into a maintenance plan ([RCM handbook](https://rcm-site-9f664.web.app/decision-logic)).

**Example row for a CH-Francis turbine guide bearing (TGB)** (illustrative; scores are a first proposal for the generated FMEA):

| Field | Value |
| --- | --- |
| Function | Keep the shaft centred at the runner, radial load at rated speed |
| Functional failure | Bearing cannot carry load without overheating |
| Failure mode | Babbitt pad wiping |
| Mechanism / cause | Loss of oil film from oil degradation, cooling loss, misalignment, overload at transients |
| Local / plant effect | Pad temperature rises → customer trip at 90 °C → forced outage, possible shaft damage |
| Detection | Pad RTDs (CH alarm 75 / 85 °C), TGB oil temperature, shaft vibration, oil analysis |
| S / O / D | 8 / 3 / 3 → RPN 72 |
| Task | Condition-based: pad-temperature residual vs. load and cooling; quarterly oil analysis |

The detection column is what connects the FMEA to the CH tree: every detection method should name a real topic, so the bot can go from a hypothesis straight to the data that tests it.

## The documents and data M&R teams work with

An RCA pulls evidence from a dozen sources that rarely live in one system. In real life the hardest part is not the analysis but assembling this evidence; that is where a bot earns its place.

| Source | Typical owner | What it gives the RCA |
| --- | --- | --- |
| Asset register / hierarchy | Maintenance | Which unit, sub-unit and maintainable item failed; serials |
| OEM O&M manual | OEM (CH) | Design limits, alarm/trip settings, troubleshooting tables, procedures |
| Drawings, P&IDs, bearing and cooling schematics | Engineering / OEM | How the system is built; what can affect what |
| CMMS work orders | Maintenance | What was done, when, by whom; failure codes; parts used |
| PM plans and inspection records | Maintenance / reliability | Whether the strategy was followed (e.g. strainer cleaning on time?) |
| Historian trends | Operations / IT-OT | What the process and machine did before, during and after |
| Alarm and event logs | Operations | Sequence of events, operator actions, trips |
| Shift logs | Operations | Context nobody recorded elsewhere ("unit restarted after short cool-down") |
| Oil analysis and vibration survey reports | Reliability / contractors | Slow degradation evidence |
| FMEA / RCM records | Reliability | Known failure modes and expected detection |
| Previous RCAs | Reliability | Repeat failures, earlier actions and whether they worked |
| Management of change records | Engineering | Recent modifications that could be the latent root |

**Failure coding (ISO 14224).** Work orders only become analysable when each failure is coded on three separate layers ([Fabrico](https://www.fabrico.io/blog/iso-14224-failure-taxonomy-codes/)):

- **Failure mode:** what was observed, e.g. high vibration (VIB), overheating (OHE), external leakage (ELP).
- **Failure mechanism:** the physical process, e.g. wear, fatigue, cavitation.
- **Failure cause:** why the mechanism happened, grouped as design, fabrication/installation, operation or maintenance.

ISO 14224 comes from oil and gas but its taxonomy works for any rotating equipment. In practice coding discipline is poor and much history is free text. For the demo this is useful: generated work orders should include some missing or wrong codes and free text, so the bot has to interpret them, as it would in a real plant.

## Where AI helps, and where it doesn't

The audience's first question will be "how do I know it's right?" Recent industrial research makes the same point: unconstrained LLM agents produce fluent but unsupported explanations, and the systems that work bound the model with FMEA knowledge, structured evidence and verification steps ([arXiv 2603.08171](https://arxiv.org/html/2603.08171v1)).

| The bot is good at | The bot is weak at |
| --- | --- |
| Building the event timeline from alarms, events and trends in minutes | Physical evidence: it cannot look at a wiped pad or smell burnt oil |
| Matching symptoms to FMEA failure modes and listing hypotheses to test | Latent roots: budgets, procedures, culture; these come from interviews |
| Querying the data that tests each hypothesis (e.g. cooling flow vs. pad temperature) | Knowing what nobody wrote down |
| Finding similar past work orders and RCAs, including free text | Judging consequences and making the call on actions |
| Drafting the report in the house template | Taking responsibility |

**Design rules for a credible RCA bot**

1. **Hypotheses only from the FMEA (plus an explicit "not in FMEA" flag).** This bounds the answer space and makes FMEA gaps visible, which is itself an RCA output.
2. **Every claim cites evidence:** a topic and time window, a work order number, a manual section. No citation, no claim.
3. **Verify or rule out each hypothesis,** and show how. A logic tree with crossed-out branches convinces reliability engineers far more than a confident paragraph.
4. **Separate physical, human and latent roots,** and ask for human input on the latter two instead of inventing them.
5. **Human sign-off** before actions go into the CMMS.

**Critical points for the demo itself**

- **The bot must not see ground truth.** The repo's rule that scenario ids never reach a topic is exactly right; the bot gets the two trees and the documents, never the instructor station.
- **Sensor fault vs. machine fault is the best demo moment.** Scenario G (one CH RTD drifts while the customer's element A is fine) next to scenario A (real TGB degradation) shows whether the bot checks data quality before blaming the machine. Reliability engineers lose many hours to exactly this.
- **Don't oversell the root cause.** For the CH data, the bot can usually reach the physical root and mechanism. If the demo claims a latent root, it must come from a generated document (e.g. a work order showing the strainer PM was postponed), not from the model's imagination.
- **Who is the user?** Decided: Copper Canyon's own reliability team (DRWPA). The O&M manuals and schematics are supplier documents from CH in their document library; everything else is DRWPA's own records.

## What the Copper Canyon data gives the bot, and what to generate next

The [cromley-hydraulics-uns](https://github.com/itotinsider/cromley-hydraulics-uns) repo provides the live evidence layer; the history and knowledge layers are missing and are the next step.

**Already there** (from the repo's [CLAUDE.md](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/CLAUDE.md))

- Three CH-Francis turbines: `CH-FR-1987-0042` (Unit 1), `CH-FR-1987-0043` (Unit 2), `CH-FR-1989-0051` (Unit 3).
- CH tree: 74 process topics per turbine every 1 s with quality and sequence numbers, 8 waveform channels, nameplate, PLC alarms and active alarms.
- Customer tree: 82 topics, plant events (commands, state changes, trips), unit protection on hardwired element A.
- 19 hidden scenarios: A–H plus flood, generator trip, trash debris, cooler fouling, oil/water ingress, misalignment, hydraulic unbalance, runner crack, servo seal leak, shaft seal wear and air gap. These are the "events" the bot investigates.
- An offline simulator that runs hours of plant time in seconds.

**Gaps for RCA**

- **No history.** SCADA trends live in memory (2 h at 1 s, 48 h at 1 min) and are lost on restart; Node-RED only exports bearing pads to CSV. An RCA needs the weeks before the event. Fix: a recorded historian dataset generated with the offline simulator (normal months plus the scenario lead-up), or a small historian service.
- **No maintenance records, documents or past RCAs.** These carry the human and latent roots, so without them the bot can only do failure analysis.

**Documents to generate next** (proposal)

| # | Document | Owner | Purpose in the demo |
| --- | --- | --- | --- |
| 1 | CH-Francis "Canyon" O&M manual (bearings, cooling, HPU, governor, alarm and trip table, troubleshooting) | CH | Design limits and troubleshooting steps the bot cites |
| 2 | Unit schematics: bearing arrangement, lube oil and cooling water circuits, HPU | CH | Which components can affect which signals |
| 3 | Asset hierarchy (ISO 14224 style) with serials and maintainable items | DRWPA | Lets the bot name the failed item correctly |
| 4 | FMECA for the CH-Francis unit, one row per failure mode (≈19, matching the scenarios), detection tied to real topics | CH + DRWPA | Bounds the bot's hypotheses |
| 5 | Maintenance strategy / PM plan | DRWPA | Shows what should have been done |
| 6 | CMMS work-order history, 3–5 years, ISO 14224 coded, with realistic noise (missing codes, free text) | DRWPA | Repeat failures and human/latent clues |
| 7 | Three previous RCA reports (e.g. a TGB wipe after cooling loss, HPU pump wear, a shear-pin break after debris) | DRWPA | "Have we seen this before?" and actions that did or didn't work |
| 8 | Oil analysis and vibration survey reports | Contractors | Slow-degradation evidence |
| 9 | Shift log excerpts | Operations | Unrecorded context |
| 10 | RCA procedure with triggers, plus the RCA report template | DRWPA | The process and format the bot follows |
| 11 | Historian dataset (recorded runs) | IT-OT | Weeks of pre-event trends |

**Open questions for you**

- Decided: the bot belongs to Copper Canyon Dam's internal team (DRWPA); CH supplies the manuals and schematics.
- Which 2–3 scenarios will you demo live? I would pick A (bearing degradation, with a latent root planted in the work orders), G (sensor fault, to show the bot checks data quality) and C (rough-zone operation, where the root cause is an operating decision, not a broken part).

## Sources

- [Reliabilityweb: maintenance engineer vs. reliability engineer](https://reliabilityweb.com/en/articles/what-is-the-difference-between-a-maintenance-engineer-and-a-reliability-engineer)
- [Accendo Reliability: differences between maintenance and reliability engineers](https://accendoreliability.com/differences-between-maintenance-and-reliability-engineers-a-brief-literature-review/)
- [Accendo Reliability podcast with Shon Isenhour](https://accendoreliability.com/podcast/rir/108-maintenance-engineer-vs-reliability-engineer-shon-isenhour/)
- [Plant Services podcast: maintenance vs. reliability engineers](https://www.plantservices.com/management/leadership-skills/podcast/55274176/podcast-maintenance-vs-reliability-engineers-key-differences-and-how-they-work-together)
- [Reliable Media: maintenance and reliability KPI reference](https://reliamag.com/guides/maintenance-reliability-kpi-reference/)
- [eWorkOrders: preventive maintenance KPIs](https://eworkorders.com/?p=68637)
- [Reliable Media: the six failure patterns (Nowlan & Heap)](https://reliamag.com/topics/guides/six-failure-patterns-nowlan-heap)
- [Accendo Reliability: "No, 89 percent of failures are not random"](https://accendoreliability.com/no-89-percent-of-failures-are-not-random/)
- [Tractian: P-F curve](https://tractian.com/en/glossary/p-f-curve-potential-failure-curve)
- [The PROACT RCA quick reference guide](https://www.perlego.com/book/1639691/the-proact-root-cause-analysis-quick-reference-guide-pdf)
- [Reliability Center: PROACT RCA course (5 Ps)](https://reliability.com/?p=1883)
- [Plant Services: PROACT case on physical, human and latent roots](https://www.plantservices.com/home/article/11332074/human-capital-how-one-team-used-the-proact-method-to-identify-the-real-root-causes-of-a-catastrophic-failure)
- [Example RCA trigger and escalation policy (mining)](https://www.slideshare.net/slideshow/sirfrt-op-ex-rca2015b/59106322)
- [Shon Isenhour: triggering success with RCA](https://shonisenhour.blogspot.com/2011/07/triggering-success-with-root-cause.html)
- [Learn Lean Sigma: fishbone vs. 5 Whys](https://www.learnleansigma.com/?p=17831)
- [Reliable Plant: RCA tools](https://www.reliableplant.com/Articles/Print/31171)
- [Reliable Media: how to perform FMEA](https://reliamag.com/topics/guides/how-to-perform-fmea)
- [Quality-One: AIAG-VDA FMEA](https://quality-one.com/aiag-vda-fmea/)
- [Reliable Media: how to perform RCM (SAE JA1011)](https://reliamag.com/guides/how-to-perform-rcm/)
- [RCM handbook: decision logic](https://rcm-site-9f664.web.app/decision-logic)
- [Fabrico: ISO 14224 failure codes](https://www.fabrico.io/blog/iso-14224-failure-taxonomy-codes/)
- [arXiv 2603.08171: evidence-grounded LLM reasoning for industrial maintenance](https://arxiv.org/html/2603.08171v1)
- [POWER: generator bearing failures, RCA and integrated data](https://www.powermag.com/generator-bearing-failures-root-cause-analysis-and-the-role-of-integrated-data/) (real hydro thrust-bearing RCA cases, useful as models for the generated RCA reports)
- [cromley-hydraulics-uns repo](https://github.com/itotinsider/cromley-hydraulics-uns) and its [CLAUDE.md](https://github.com/itotinsider/cromley-hydraulics-uns/blob/main/CLAUDE.md)
