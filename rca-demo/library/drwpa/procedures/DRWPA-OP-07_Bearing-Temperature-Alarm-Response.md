# DRWPA-OP-07 Bearing Temperature Alarm Response

| | |
| --- | --- |
| Site | Copper Canyon Dam |
| Revision | 2 (2026-10-01) |
| Owner | Dale Whitaker, I&C Lead; Priya Nandakumar, Reliability Engineer |
| Approved | Elena Marsh, Plant Manager |
| Change in rev 2 | CH monitoring PLC pad alarms added (retrofit Sep 2026) |

*Fictional document, for training only. Created after RCA-2024-011 (MOC-2024-015).*

## 1 Purpose

Respond to bearing temperature alarms quickly **without** stopping a healthy unit on a faulty measurement, and without ignoring a real bearing problem.

## 2 Alarm sources

| Source | Measured on | Limits |
| --- | --- | --- |
| Unit controller (control room) | Pad 1 of each bearing, element A | Alarm 80 °C; trip 90 °C (5 s delay, automatic) |
| CH monitoring PLC (CH asset viewer, CH tree) | Every pad (pad 1 element B) | H 75 °C; HH 85 °C; oil bath 65 °C |

The control room sees one pad per bearing. Pads 2..n are visible only in the CH PLC data.

## 3 Validation before acting (unless at trip level)

Within 15 minutes of an alarm, the shift supervisor (with I&C or the reliability engineer on call) checks:

1. **Neighbouring pads** of the same bearing: do they move with it? A real pad problem raises its neighbours a little.
2. **Oil bath temperature** of that bearing: rising, even slowly?
3. **Second element** (pad 1 only): element A (control room) against element B (CH PLC). Do they agree within 2 K?
4. **Cooling water**: total flow (control room) and circuit flows (CH PLC). Do all bearings warm up together?
5. **Operating point**: load, gate position (rough zone?), recent start or load rejection.
6. **Vibration** at that bearing: any change?
7. **Recent work**: work orders, open punch items, wiring work in junction boxes.

## 4 Decision

| Finding | Action |
| --- | --- |
| Single channel moves alone; neighbours, oil, element A and vibration flat | **Instrument fault suspected.** Keep the unit running. Raise an I&C work order (priority 2). Watch neighbours and oil hourly. |
| Neighbours and/or oil bath rising with it | **Bearing problem.** Reduce load to 30 MW (above the rough zone where head allows), call the reliability engineer, take an oil sample, prepare a controlled stop if the trend continues or HH (85 °C) is reached. |
| All bearings rising, cooling flow low | **Cooling problem.** Check and change over the strainer immediately. Reduce load. |
| TGB warm with high TGB vibration and draft tube pulsation | **Rough-zone operation.** Move the unit out of the zone. |
| Trip level reached on element A | The unit trips automatically. Do not reset before the bearing has been inspected or the measurement has been proven faulty. |

## 5 Records

Log the alarm, the checks and the decision in the shift log. Any stop on a bearing temperature alarm triggers at least a Level 1 RCA (DRWPA-PRO-REL-01).
