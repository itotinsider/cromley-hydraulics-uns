# DRWPA-OP-03 Unit Operation and the Rough Zone

| | |
| --- | --- |
| Site | Copper Canyon Dam |
| Revision | C (2026-01-15) |
| Owner | Ray Okafor, Maintenance Superintendent; Priya Nandakumar, Reliability Engineer |
| Approved | Elena Marsh, Plant Manager |
| Change in rev C | Section 4 added after RCA-2025-007 (MOC-2025-019) |

*Fictional document, for training only.*

## 1 Normal operation

- Units run in **PLANT** mode: the plant controller splits the grid operator's plant setpoint (including AGC) over the generating units.
- **LOCAL** mode (a unit's own MW setpoint) is for testing and maintenance only and is logged in the shift log.
- Maximum continuous output per unit: 42 MW at net head of 100 m or more (CH-DOC-OM-0101 section 2). Lower at low head.
- Minimum flow to the river: 10 m³/s at all times, via a running unit or the bottom outlet (AUTO).

## 2 Start and stop

Start permissives: intake gate open, reservoir above 384 m a.s.l., governor oil pressure at least 55 bar, no hardwired I/O fault. A start takes about 100 s to the breaker plus about 3 min to ramp. Normal stop through the Stop command; emergency stop only for the conditions in the unit protection list.

## 3 The rough zone

Each unit has a rough zone between **35 % and 70 % wicket-gate opening** (CH-DOC-OM-0101 section 3). At the usual net head of about 106 m this is about **10.7 to 32.9 MW**. Operation there causes a draft-tube vortex rope: pressure pulsation near 1.4 Hz, high TGB vibration, MW swings, and over time draft tube cracking and runner cavitation.

- The plant controller's rough-zone table keeps units out of the zone. It will rather report the plant setpoint as not reachable (`MWSetpointReachable` false) than park a unit inside the zone.
- Passing through the zone while ramping is acceptable.
- Operators shall not hold a unit inside the rough zone in LOCAL mode.

## 4 Bypass of the rough-zone table (added in rev C)

Any bypass of the rough-zone table, for any reason (including ancillary-services contracts):

1. requires an approved MOC **with a documented sign-off by the reliability engineer** before the bypass is enabled;
2. shall name the unit(s), the maximum duration and a maximum number of hours inside the zone;
3. shall not be applied to a unit with an open draft-tube or runner finding;
4. shall be recorded in the shift log when enabled and when removed.

Background: in summer 2025 a bypass (MOC-2025-012) kept units in the rough zone for an estimated 640 h. Unit 2's draft tube cone cracked and its runner suffered cavitation damage (RCA-2025-007).

## 5 Records

Shift supervisors log mode changes, LOCAL operation and any bypass. The reliability engineer reviews rough-zone hours monthly (KPI to be implemented with CH monitoring PLC data, RCA-2025-007 action A4).
