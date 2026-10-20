# Edge vendor brief

For industrial DataOps / IIoT vendors who connect their edge platform to Copper Canyon Dam in the
next step of the case study. The environment stops at the local Mosquitto broker; everything
beyond it is yours. That makes vendors comparable: same data, same faults, your own platform.

## What you get

| | |
|---|---|
| Broker | `mqtt://<host>:1884` (default host port), MQTT 3.1.1/5, anonymous, no TLS. Inside the compose network `mosquitto:1883` |
| Customer tree | `v1.0/DRWPA/CopperCanyon/#`: 82 topics, 1 s, retained; commands under `Cmd` |
| CH tree | `v1.0/CH/Fleet/DRWPA/CopperCanyon/<serial>/#` for three turbines: 74 process topics each at 1 s with quality and seq, 8 raw waveform channels, alarm events, nameplate, last-will status |
| Waveforms | 6 shaft probes at 1 kS/s (4 s every 30 s), draft-tube pressure at 100 S/s (10 s every 30 s), headcover accelerometer at 10 kS/s (0.5 s every 5 min), plus on alarm |
| Load | ~18 KB/s per turbine with the defaults; raise it with `WAVEFORM_*_EVERY_S`, `WAVEFORM_*_SECONDS` and `DETAILED_TURBINES` in `docker-compose.yml` (see [Configuration](Configuration)) |
| Faults | Scenarios A–H and more, started hidden from the [instructor station](Instructor-station) |

Formats: [Namespace](Namespace). Which signal shows which fault: [Failure modes](Failure-modes).

## What you show

| Topic | What the vendor shows |
|---|---|
| Edge analytics | FFT, orbits, envelope analysis and models on the waveform blocks; turning faults A–H into alerts |
| Transport | Getting data from the site to your platform or cloud |
| Buffering | Store-and-forward during link outages, backfill with original timestamps (`seq` shows what was lost) |
| Security | Separating customer control data from machine-builder monitoring; TLS, identities, network segmentation (IEC 62443) |
| Data scoping | Sending only the CH tree (or an agreed subset) off site; respecting customer consent |
| Device management | Onboarding, configuration, firmware updates and health of edge devices across many sites |

The challenges in the original brief — bad connections at customer sites, device management,
cyber security, data privacy — are the questions you answer on top of this environment.

## Suggested demo flow

| Scenario | Show |
|---|---|
| A. TGB bearing degradation | L3: an expected pad temperature from MW, cooling water and oil; the residual of pad 3 grows long before 75 °C, and before the customer's RTD notices anything |
| B. Cooling-water strainer | Correlated rise across circuits; root cause = flow, not bearings |
| C. Rough zone | FFT of the draft-tube block: a peak at ~1.4 Hz; a time-in-rough-zone KPI; the outcome-risk discussion ([Business model](Business-model)) |
| D. HPU pump wear | Leak rate from the accumulator's pressure decay between pump runs; duty trend |
| E. Shear pin | Event handling: alarm-triggered waveforms, a step at constant MW |
| F. Unbalance | 1X amplitude and phase from the keyphasor; orbit before/after |
| G. RTD drift | Sensor validation: one pad diverging from its neighbours while quality says GOOD |
| H. Low head | Efficiency loss vs. head; cavitation band energy in the accelerometer |

Kill your edge device's link for a few minutes during a scenario to show buffering; stop the CH PLC
container (`docker compose stop ch-plc-sim`) to show the last will.

## Rules

- **Never write into the customer tree**, and never publish `Cmd` topics. The customer's control
  data is not yours.
- **Scope = the CH tree.** Customer context is copied into `Context/` by the CH PLC; that is the
  agreed subset.
- **Consent** decides what leaves the site. Make it visible how you would enforce it.
- Don't read the instructor station's API: diagnose from the data.
