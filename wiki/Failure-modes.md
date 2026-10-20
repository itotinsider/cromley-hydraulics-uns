# Failure modes

Every failure mode can be detected at increasing levels of sophistication, so vendors can show
anything from a threshold to a digital twin on the same data. Real alarm and trip values are
OEM-specific; the ones here are plausible demo values.

## Detection ladder

| Level | Method | Example here |
|---|---|---|
| **L1** | Fixed threshold | PLC pad alarm at 75 °C |
| **L2** | Rate of change, trend | °C per hour on a pad; pump starts per hour |
| **L3** | Model residual: expected vs. measured | Pad temperature vs. MW, cooling water temperature and flow, oil temperature |
| **L4** | Spectral analysis on the waveforms | FFT, orbit, envelope, order tracking |
| **L5** | Multivariate ML or a digital twin | Cumulative erosion, fatigue, remaining useful life |

## The 15 failure modes

| # | Failure mode | Signature in the simulation | Topics (CH tree unless noted) | Detection | Scenario |
|---|---|---|---|---|---|
| 1 | Guide/thrust bearing degradation | One TGB pad creeps, then accelerates; pad-to-pad spread grows; late on, TGB 1X grows | `Bearings/TGB/PadTemp01..04`, `OilTemp` | L1 75/85 °C; L2 °C/h; **L3 pad temp vs. MW, cooling water and oil temp** (flagship demo) | A |
| 2 | Cooling water loss / cooler fouling | Flow drops and all temperatures on it rise together; or flows normal, oil hotter, cooler outlet colder | `Cooling/*`, all pads and oils, `Generator/StatorTemp*`; customer `CoolingWaterFlow` | L1 low flow; L3 heat-transfer trend | B; `cooler_fouling` |
| 3 | Oil contamination / water ingress | TGB oil level rises slowly, temperature creeps | `Bearings/TGB/OilLevel`, `OilTemp` | L1/L2 level trend | `oil_water_ingress` |
| 4 | Mechanical unbalance | 1X up, stable phase, grows with speed² | Shaft waveforms + `keyphasorIdx`, `Overall_um_pp` | L1 overall (alert 140 µm pp); L4 1X vector, orbit | F |
| 5 | Misalignment / bearing clearance | 1X + strong 2X, elliptical orbit | Shaft waveforms | L4 orbit, 2X amplitude | `misalignment` |
| 6 | Hydraulic unbalance | 1X rises with gate opening, not with speed | Shaft waveforms + `Context/GatePosition_pct` | L3/L4 vibration vs. operating point | `hydraulic_unbalance` |
| 7 | Draft-tube vortex rope | Pressure pulsation at 0.28 × 5 Hz = 1.4 Hz, sub-synchronous shaft vibration, MW swings (customer tree) | `Vibration/DraftTube/Pressure/Waveform`, TGB shaft waveforms, `Vel_mm_s_rms` | L4 dominant frequency; L3 time-in-rough-zone counter | C (and every load ramp through the zone) |
| 8 | Cavitation erosion | High-frequency bursts, modulated at blade pass, at high gate, off-design head and low tailwater | `Vibration/Headcover/Accel/Waveform`, `Vel_mm_s_rms`, `Context/TailwaterLevel_m` | L4 band energy / envelope; L5 cumulative erosion | H |
| 9 | Runner crack / blade fatigue | Blade-pass harmonic (130 Hz) and ±1X sidebands grow | Accelerometer, TGB shaft waveforms | L4 order tracking; L5 fatigue twin | `runner_crack` |
| 10 | Wicket-gate shear pin failure | Discrete status, vibration step at constant MW | `Turbine/ShearPinStatus`, `WicketGateBreakawayAlarm`, vibration | L1 event; L3 step detection | E |
| 11 | HPU pump wear / internal leakage | Pump starts per hour rise, faster pressure decay, longer runs | `Governor/HPU/Pump1Running`, `Pump2Running`, `PumpStartsPerHour`, `AccumulatorPressure` | L2 duty trend; L3 leak rate from dP/dt | D |
| 12 | Servomotor seal / oil leak | Sump level drops, servo B lags the setpoint | `Governor/HPU/SumpLevel`, `ServoPositionA/B`, `GateSetpoint` | L2 trend; L3 position error | `servo_seal_leak` |
| 13 | Shaft-seal wear | Seal water flow and sump pump starts rise | `Turbine/ShaftSealWaterFlow`, `HeadcoverSumpPumpStarts`, `HeadcoverPressure` | L2 counter trends | `shaft_seal_wear` |
| 14 | Generator air-gap anomaly | Minimum air gap shrinking | `Generator/AirGapMin_mm` | L1 minimum (10.5 mm); L2 trend | `air_gap` |
| 15 | Sensor failure (teaching case) | Drift, flatline or spike on one RTD while its neighbours are normal; quality stays GOOD | Any pad temperature | L1 range/flatline; L3 cross-sensor consistency | G |

## Normal values (demo, ~37 MW per unit)

| Signal | Typical |
|---|---|
| Thrust pads / oil bath | ~64–68 / ~51 °C |
| Guide bearing pads | ~55–65 °C |
| Cooling water inlet | 14 °C ± 0.8 (daily) |
| Cooling flows TB / GB / air coolers | 8 / 12 / 60 L/s |
| Accumulator pressure | 58–63 bar (lead pump on at 58, off at 63; lag pump on at 54) |
| Pump starts | ~6–7 per hour |
| Shaft displacement overall | ~40–60 µm pp |
| Headcover velocity | ~1 mm/s RMS |
| Stator temperatures | ~65 °C |
| Minimum air gap | ~11.6 mm |
| Draft-tube pressure | ~0.6 bar (gauge) |

## CH PLC alarm limits

The PLC's own limit checks, published on `Events/Alarm` (ids in brackets, `<b>` a bearing, `<n>`
a pad or RTD number, `<ax>` X or Y). They clear with a 1 % deadband.

| Alarm | Limit | Severity |
|---|---|---|
| Pad temperature (`<b>_PAD<n>_H`, `_HH`) | > 75 / > 85 °C | WARNING / CRITICAL |
| Oil temperature (`<b>_OIL_H`) | > 65 °C | WARNING |
| Cooling water flow (`COOLING_TB_L`, `_GB_L`, `_AIRCOOLERS_L`) | < 70 % of nominal, while running | WARNING |
| Accumulator pressure (`HPU_PRESSURE_L`) | < 52 bar | WARNING |
| Pump starts (`HPU_STARTS_H`) | > 15 per hour | WARNING |
| Filter ΔP (`HPU_FILTER_H`) | > 2.5 bar | WARNING |
| Sump level (`HPU_SUMP_L`) | < 55 % | WARNING |
| Shear pin (`SHEAR_PIN_BROKEN`) | `BROKEN` | CRITICAL |
| Headcover vibration (`HEADCOVER_VIB_H`) | > 4.5 mm/s RMS, while running | WARNING |
| Shaft vibration (`VIB_<b>_<ax>_ALERT`, `_DANGER`) | > 140 / > 220 µm pp, while running (in the spirit of ISO 20816-5 zones B/C and C/D) | WARNING / CRITICAL |
| Air gap (`AIRGAP_L`) | < 10.5 mm, while running | WARNING |
| Stator temperature (`STATOR_<n>_H`) | > 120 °C | WARNING |

The customer's unit protection has its own, higher limits on its own sensors: see
[Copper Canyon Dam](Copper-Canyon-Dam#unit-protection).

Sources: vibration limits per [ISO 20816-5](https://www.iso.org/standard/67919.html); hydro
condition monitoring guidance in [ISO 19283](https://cdn.standards.iteh.ai/samples/64262/c80c276ce28a4731b51e4a9b3f304c9d/ISO-19283-2020.pdf);
governor values from [Reclamation FIST 2-3](<https://www.usbr.gov/power/data/fist/FIST_2-3_(1-2021).pdf>).
