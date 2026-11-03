# DRWPA-PRO-REL-01 Root Cause Analysis Procedure

| | |
| --- | --- |
| Site | Copper Canyon Dam |
| Revision | 2 (2024-11-04) |
| Owner | Priya Nandakumar, Reliability Engineer |
| Approved | Elena Marsh, Plant Manager |

*Fictional document, for training only.*

## 1 Purpose

Find and remove the causes of significant equipment failures and near misses at Copper Canyon Dam, so they do not recur. An RCA is finished only when its actions are done and shown to work.

## 2 When an RCA is required (triggers)

| Level | Trigger | Who | Due |
| --- | --- | --- | --- |
| 0: Log only | Unplanned downtime under 4 h, no safety or environmental effect | Shift supervisor records it in the shift log and the work order | — |
| 1: Quick RCA | Unplanned downtime 4–24 h, or repair cost USD 10k–50k, or a protection trip | Maintenance engineer with the technician and shift supervisor; 5 Whys and timeline on form DRWPA-FRM-REL-02 | 10 working days |
| 2: Team RCA | Unplanned downtime over 24 h, repair cost over USD 50k, any safety or environmental event, or the **same failure mode on the same unit twice within 24 months** | Reliability engineer leads; team with maintenance, operations, I&C and the OEM where needed; full logic tree | 30 days |
| Any level | Requested by the plant manager, or a finding at inspection that could have caused a Level 2 event | As decided | As decided |

A spurious shutdown (equipment healthy) counts as a failure of the measurement or the decision, and is analysed like any other event.

## 3 Steps

1. **Preserve evidence (first 24 h).** The 5 Ps: Parts (keep failed parts, oil samples, do not clean), Position (photos, where things were found), People (short statements from those present, same shift), Paper (trends, alarm and event logs, CH PLC data, work orders, procedures, shift log), Paradigms (what people assumed). Export the relevant data before it is overwritten: the SCADA keeps 48 h of 1-minute trends.
2. **Define the problem.** What happened, where, when, the impact (MW, hours, cost, safety), and how it was detected. One sentence, no cause in it.
3. **Form the team** (Level 2): reliability engineer (lead), maintenance engineer, I&C, a shift supervisor, and the OEM for OEM equipment.
4. **Build the timeline** from logs and data.
5. **List hypotheses.** Start from the FMECA (DRWPA-FMECA, file `fmeca_ch-francis-unit.csv`): every failure mode that could produce the observed symptoms is a hypothesis. Add any that the FMECA does not cover and flag them.
6. **Verify or rule out each hypothesis with evidence.** Record the evidence for each decision (data, inspection, test, lab result). A hypothesis without evidence stays open; it is never "probably".
7. **Find all roots.** For each verified cause, continue to:
   - the **physical root** (what failed physically and by which mechanism),
   - the **human root** (which action or decision triggered or allowed it), and
   - the **latent root** (which system, procedure, resource or management decision made that action likely).
   "Operator error" or "technician error" is never a root cause; ask what made the error likely.
8. **Recommend actions**, each with an owner and a due date, and how effectiveness will be checked. Prefer actions on latent roots.
9. **Review** with the plant manager (Level 2).
10. **Track** actions in the CMMS (linked work orders) until closed.
11. **Verify effectiveness** after an agreed period (typically 6–12 months): has the failure mode recurred?
12. **Update** the FMECA, the PM plan and failure codes with what was learned.

## 4 Failure coding

Code the work order with ISO 14224 style codes: failure mode (e.g. OHE overheating, VIB vibration, AIR abnormal instrument reading, ELP/ELU external leakage, PLU plugged, STD structural deficiency, UST spurious stop), failure mechanism (e.g. 2.4 wear, 2.6 fatigue, 2.7 overheating, 3.3 faulty signal, 5.1 blockage) and failure cause (e.g. 1.0 design, 2.2 installation error, 3.1 off-design service, 3.2 operating error, 3.3 maintenance error, 3.4 expected wear and tear, 4.2 management error).

## 5 Records

RCA reports are stored as `RCA-YYYY-NNN` in the document library, using template DRWPA-FRM-REL-02.
