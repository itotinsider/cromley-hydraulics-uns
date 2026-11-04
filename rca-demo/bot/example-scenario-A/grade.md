# RCA-2026-001 (Scenario A): grading

The report scores **16 out of 18**. It misses one latent root: the same person raised and approved MOC-2025-004. It also says the overnight H alarm was invisible in the control room, but the CH viewer screen was in the control room and nobody looked at it.

| # | Item | Score | Reason |
|---|---|---|---|
| 1 | Event and problem statement | 2 | It states the CH PLC TGB_PAD03_HH alarm (85 °C) at 09:00, the load cut to 34 MW at 09:14 and the controlled stop at 09:48–09:51, with no cause in it. |
| 2 | Timeline | 2 | It covers the 2019 concession, the oil trend, the MOC, WO-2025-0022 and WO-2026-0672, the retrofit and the daily dP3 rise, and gives exact times for the H alarm (23:54:22), the HH alarm and the stop. It leaves out the 07:13 "No alarms" shift-log entry. It also doesn't note that the Feb 2025 "resample within 30 days" was never done. |
| 3 | Ruled-out hypotheses | 2 | **Cooling:** TB flow 8.0 L/s, all circuits at nominal, compared with RCA-2023-004. **Sensor fault:** neighbouring pads and oil rose too, pad 1 elements A and B agree, no spikes, and the offset went to about 0 at standstill, which is a strong test. **Rough zone:** gate 70–86 %. **Unbalance:** overall vibration flat. It leaves misalignment "Open" because the export has no waveforms or 1X/2X tags (historian README). That is the right call for this data. |
| 4 | Physical root | 2 | Oil-film breakdown on pad 3: a tight segment (0.24 mm, CH-CON-2019-017) running in oxidised oil (TAN 0.38, MPC 28, Sn 14.2). It is correctly called a working statement until the bearing is inspected. |
| 5 | Human root | 2 | Five Caution results with no oil change, "monitor" after the Sept 2025 resample (WO-2025-0691), and WO-2026-0672 deferred for the retrofit with no new date. Framed as decisions, not blame. |
| 6 | Latent roots | 1 | **Found:** the MOC-2025-004 cost extension that cancelled the Jan 2025 oil change; the conditional sign-off not incorporated; the PM plan below the CH recommendation; no escalation rule for lab Caution results; protection that sees pad 1 only, with CH alarms only in the viewer and no annunciation. **Missed:** MOC-2025-004 was raised *and* approved by Ray Okafor (`moc-register.csv`). The "no owner" point is also only weakly made: the report says the viewer is outside the control room, when it is a second screen in the room that nobody is assigned to watch. |
| 7 | Recommendations | 2 | All six good recommendations are there: inspect before restart (A1), sample the oil before draining (A1), quarterly sampling (A5), an escalation rule for Caution results (A6), CH pad alarms into SCADA plus an interim viewer check on rounds (A4), and re-opening MOC-2025-004 with a review of FMECA FM-01 (A5). |
| 8 | Evidence discipline | 2 | Claims cite files, tags, IDs and time windows, and missing evidence is listed separately. Every figure I recomputed from the historian matched (details below). One overstatement, listed under the unsupported claims. |
| 9 | Red herrings | 2 | The 2023 cooling-loss explanation is ruled out with data. The pad 4 offset is recognised as a fixed offset that was accepted at commissioning (WO-2026-0714). The U2 trial is treated as affecting timing, not as a root cause. The U3 strainer and the vague work orders are not chased. |
| | **Total** | **16 / 18** | |

## Claims the library and historian don't support

I found nothing invented. These are overstatements or omissions:

1. **"Not visible in the control room" (timeline row at 23:54) and "no one in the control room could see it" (§7, human root (c)).** The shift log for 2026-11-03 09:03 shows the CH viewer is a *second screen in the control room*, and that it had listed "TGB pad 3 H since 23:54". The alarm was visible but had no horn and nobody watching it. The historian README line "CH PLC alarms are not shown in the control room" refers to SCADA, and the bot read it too broadly. This shifts the latent root from "no annunciation and no owner" to "can't be seen".
2. **The 07:13 "No alarms" shift-log entry is not mentioned.** It was written while the viewer was listing the H alarm, and it is the planted clue for that latent root.
3. **The Feb 2025 Caution result (MLL-2025-00196)** asked for a resample within 30 days. No resample work order exists. The report flags the missing Feb 2026 resample but not this one.
4. **Minor:** "U2 has 5.6 h in the rough zone". The CH gate tag gives 331 minutes (5.5 h). The difference is probably the tag used or how ramp time is counted, so it doesn't matter.

## What I checked

- **Historian, by recomputing the figures:**
  - the U1 daily dP3 series (−0.21 to +5.76 K)
  - pad and oil temperature means
  - headcover sump pump starts (71 per day)
  - the constant U2 and U3 pad 3 offsets (+2.09 and +2.29 K)
  - U2 TGB vibration on 11-03 (93.5 against 63.8 µm on earlier days)
- **Alarm log:** the H/HH alarm and clear times in `ch_plc_alarms.csv`.
- **Records:**
  - work orders WO-2025-0022, WO-2025-0691, WO-2026-0672, WO-2026-0714, WO-2026-0115 and WO-2026-0856
  - the oil-analysis rows and the MOC register
  - FMECA FM-01 (the D=3 note) and the PM plan (182 / 1,461 days, PM-JB proposed)
- **Supplier and procedure documents:**
  - CH manual sections 4.2, 4.3, 4.5, 5.2, 5.3, 8.1, 8.3 and 10
  - service bulletin CH-SB-2026-03 items 3.3 and 3.5
  - the 15-minute check in OP-07 and the Level 2 trigger in PRO-REL-01
  - OP-03 rev C §4 and the action statuses in all three earlier RCAs

All of these matched what the report says. I didn't open the `grade.md` already in the run folder, so this grade is independent of it.
