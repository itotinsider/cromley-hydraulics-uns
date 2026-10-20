"""Behaviour: the dam model and the three CH turbine models coupled in-process (tools/offline_sim.Sim),
faster than real time, fixed seed. Bands, not traces: limits are ranges (preferably the configured
alarm limits) so retuning stays possible, and they must hold for any seed (CH_TEST_SEED).
"""

import math

import pytest

import namespace as NS
import turbine as T
from conftest import SEED


@pytest.fixture
def sim(models):
    return models[2].Sim(seed=SEED)


def ch_alarm_ids(win, unit=None, state="ACTIVE"):
    return {e["alarmId"] for u, e in win.ch_events if (unit is None or u == unit) and e["state"] == state}


# ----------------------------------------------------------------------------- steady state
def test_steady_state(sim):
    win = sim.run(1800)
    assert not win.unit_alarms, win.unit_alarms
    assert not ch_alarm_ids(win), ch_alarm_ids(win)
    assert not [e for e in win.events if e["kind"] in ("trip", "refused")]
    sp = sim.v("Plant/MWSetpoint")
    assert abs(sim.v("Plant/TotalMW") - sp) < 3.0
    assert sim.v("Plant/MWSetpointReachable") is True
    for u in NS.UNITS:
        assert sim.v(f"Powerhouse/{u}/State") == "Generating"
        assert not T.in_rough_zone(win.min[f"Powerhouse/{u}/GatePosition"] / 100) or \
            win.min[f"Powerhouse/{u}/GatePosition"] > T.ROUGH_GATE_HI * 100
    assert win.min["River/Flow"] >= 10.0


def test_every_tag_stays_in_its_range(sim):
    win = sim.run(900)
    for t in NS.customer_tags():
        p = t["path"]
        if p in win.min and t["lo"] is not None:
            assert t["lo"] <= win.min[p] and win.max[p] <= t["hi"], (p, win.min[p], win.max[p])
    for u in NS.UNITS:
        for t in NS.ch_tags():
            k = (u, t["path"])
            if k in win.min and t["lo"] is not None:
                assert t["lo"] <= win.min[k], (k, win.min[k])
                assert t["hi"] is None or win.max[k] <= t["hi"], (k, win.max[k])


def test_normal_values(sim):
    """The design basis' typical ranges at full load."""
    sim.run(120)
    for u in NS.UNITS:
        for b in ("Thrust", "UGB", "LGB", "TGB"):
            n = 6 if b == "Thrust" else 4
            pads = [sim.v((u, f"Bearings/{b}/PadTemp{i:02d}")) for i in range(1, n + 1)]
            assert 45 < min(pads) and max(pads) < 75, (u, b, pads)
        assert 45 <= sim.v((u, "Bearings/Thrust/OilBathTemp")) <= 60
        assert 58 <= sim.v((u, "Governor/HPU/AccumulatorPressure")) <= 64 or \
            52 < sim.v((u, "Governor/HPU/AccumulatorPressure"))
        for ax in ("X", "Y"):
            assert 20 < sim.v((u, f"Vibration/TGB/Shaft{ax}/Overall_um_pp")) < 120
        assert 3 <= sim.v((u, "Governor/HPU/PumpStartsPerHour")) <= 12
        assert 60 <= sim.v((u, "Generator/StatorTemp01")) <= 110
        assert sim.v((u, "Context/UnitState")) == "Generating"
    assert 80 <= sim.v("Plant/GrossHead") <= 115
    assert 9 < sim.v("Penstock/Pressure") < 12.5


def test_repeatable(models):
    a, b = models[2].Sim(seed=SEED), models[2].Sim(seed=SEED)
    a.run(300)
    b.run(300)
    assert a.dam.values() == b.dam.values()
    for u in NS.UNITS:
        assert a.turbines[u].last == b.turbines[u].last


# ----------------------------------------------------------------------------- operation
def test_stop_and_start_a_unit(sim):
    starts = sim.v(("Unit3", "Counters/Starts"))
    assert sim.command("Powerhouse/Unit3/Cmd/Stop", True)[0]
    sim.run(420, until=lambda s: s.v("Powerhouse/Unit3/State") == "Stopped")
    assert sim.v("Powerhouse/Unit3/State") == "Stopped"
    assert sim.v("Powerhouse/Unit3/InletValveOpen") is False
    sim.run(30)
    assert sim.v(("Unit3", "Cooling/WaterFlow_GB")) < 1.0           # cooling water off at rest
    assert sim.command("Powerhouse/Unit3/Cmd/Start", True)[0]
    win = sim.run(200, until=lambda s: s.v("Powerhouse/Unit3/State") == "Generating")
    assert sim.v("Powerhouse/Unit3/State") == "Generating"
    assert sim.v("Powerhouse/Unit3/BreakerClosed") is True
    assert "COOLING_WATER_FLOW_LOW" not in win.unit_alarms
    sim.run(300)
    assert sim.v(("Unit3", "Counters/Starts")) == starts + 1
    assert abs(sim.v("Plant/TotalMW") - sim.v("Plant/MWSetpoint")) < 3.0
    assert sim.v(("Unit3", "Bearings/Thrust/HPLiftPressure")) == 0.0


def test_emergency_stop_and_reset(sim):
    es = sim.v(("Unit1", "Counters/EmergencyStops"))
    lr = sim.v(("Unit1", "Counters/LoadRejections"))
    sim.command("Powerhouse/Unit1/Cmd/EmergencyStop", True)
    win = sim.run(5)
    assert "TRIP_EMERGENCY_STOP" in win.unit_alarms
    ok, msg = sim.command("Powerhouse/Unit1/Cmd/Reset", True)
    assert not ok and "standstill" in msg
    ok, msg = sim.command("Powerhouse/Unit1/Cmd/Start", True)
    assert not ok
    win = sim.run(300, until=lambda s: s.dam.units["Unit1"].at_standstill() and s.dam.units["Unit1"].inlet == 0)
    assert 1.05 < win.max["Powerhouse/Unit1/Speed"] / T.RATED_RPM < 1.45      # load rejection, no overspeed trip
    sim.run(5)
    assert sim.command("Powerhouse/Unit1/Cmd/Reset", True)[0]
    sim.run(2)
    assert sim.v("Powerhouse/Unit1/State") == "Stopped"
    assert sim.v(("Unit1", "Counters/EmergencyStops")) == es + 1
    assert sim.v(("Unit1", "Counters/LoadRejections")) == lr + 1


def test_minimum_river_flow_with_all_units_stopped(sim):
    for u in NS.UNITS:
        sim.command(f"Powerhouse/{u}/Cmd/Stop", True)
    sim.run(500, until=lambda s: all(s.v(f"Powerhouse/{u}/State") == "Stopped" for u in NS.UNITS))
    win = sim.run(180)
    assert win.min["River/Flow"] >= 9.5
    assert sim.v("BottomOutlet/Flow") > 8.0
    assert sim.v("Plant/TotalMW") == 0


@pytest.mark.parametrize("sp", [30, 45, 60, 75, 90, 105, 120])
def test_plant_controller_avoids_the_rough_zone(models, sp):
    sim = models[2].Sim(seed=SEED, agc=False)
    sim.command("Plant/Cmd/MWSetpoint", sp)
    sim.run(420)
    lo, hi = sim.dam.rough_zone()
    for u in NS.UNITS:
        mw = sim.v(f"Powerhouse/{u}/MWSetpoint")
        assert not (lo + 0.01 < mw < hi - 0.01), (sp, u, mw, lo, hi)
    total = sim.v("Plant/TotalMW")
    if sim.v("Plant/MWSetpointReachable"):
        assert abs(total - sp) < 2.5, (sp, total)


def test_local_mode(sim):
    sim.command("Powerhouse/Unit2/Cmd/MWSetpoint", 35)
    sim.run(240)
    assert sim.v("Powerhouse/Unit2/ControlMode") == "LOCAL"
    assert abs(sim.v("Powerhouse/Unit2/MW") - 35) < 1.5
    assert abs(sim.v("Plant/TotalMW") - sim.v("Plant/MWSetpoint")) < 3.5


def test_refused_commands(sim):
    assert not sim.command("Intake/Cmd/GatePosition", 0)[0]          # units running
    assert not sim.command("Plant/Cmd/MWSetpoint", 500)[0]
    win = sim.run(2)
    assert [e for e in win.events if e["kind"] == "refused"]


def test_hardwired_loss_is_an_alarm_not_a_trip(sim):
    sim.run(5)
    sim._couple = lambda: None          # cut the copper (and the context feed)
    win = sim.run(15)
    assert "HARDWIRED_IO_FAULT" in win.unit_alarms
    assert not [a for a in win.unit_alarms if a.startswith("TRIP")]
    assert "Powerhouse/Unit1/TurbineGuideBearingTemp" not in sim.dam.values()
    # the CH PLC keeps publishing, with its copied context marked UNCERTAIN
    assert sim.turbines["Unit1"].last["Context/MW"][1] == "UNCERTAIN"
    assert sim.turbines["Unit1"].last["Bearings/TGB/PadTemp01"][1] == "GOOD"


# ----------------------------------------------------------------------------- waveforms
def dominant(values, rate, fmin, fmax):
    n = len(values)
    mean = sum(values) / n
    best = (0.0, 0.0)
    k = max(1, math.ceil(fmin * n / rate))
    while k * rate / n <= fmax:
        re = sum((x - mean) * math.cos(2 * math.pi * k * i / n) for i, x in enumerate(values))
        im = sum((x - mean) * math.sin(2 * math.pi * k * i / n) for i, x in enumerate(values))
        amp = 2 * math.hypot(re, im) / n
        if amp > best[1]:
            best = (k * rate / n, amp)
        k += 1
    return best


def test_waveform_blocks(sim):
    sim.run(10)
    tb = sim.turbines["Unit1"]
    for w in NS.ch_waveforms():
        b = tb.waveform(w, sim.t)
        assert b["samples"] == len(b["values"]) == int(w["rate"] * w["seconds"])
        assert b["sampleRate"] == w["rate"] and b["unit"] == w["unit"] and b["trigger"] == "periodic"
        assert abs(b["speedRpm"] - T.RATED_RPM) < 3
        if w["group"] == "shaft":
            kp = b["keyphasorIdx"]
            gaps = [j - i for i, j in zip(kp, kp[1:])]
            assert len(kp) in (19, 20, 21) and all(195 <= g <= 205 for g in gaps), kp
            f, amp = dominant(b["values"][:1000], w["rate"], 2, 20)
            assert abs(f - 5.0) < 0.6, f                       # 1X dominates in normal operation


# ----------------------------------------------------------------------------- scenario signatures
def _base(sim, key):
    return sim.v(key)


def sig_tgb(sim):
    sim.scenario("tgb_bearing_degradation", "Unit1", {"duration_s": 600})
    win = sim.run(720)
    assert win.max[("Unit1", "Bearings/TGB/PadTemp03")] > 85
    assert "TGB_PAD03_HH" in ch_alarm_ids(win, "Unit1")
    assert win.max[("Unit1", "Bearings/TGB/PadTemp03")] - win.max[("Unit1", "Bearings/TGB/PadTemp01")] > 15
    assert win.max["Powerhouse/Unit1/TurbineGuideBearingTemp"] < 75      # the customer's RTD (pad 1) sees little


def sig_strainer(sim):
    oil0 = sim.v(("Unit2", "Bearings/Thrust/OilBathTemp"))
    sim.scenario("cooling_strainer", "Unit2", {"duration_s": 240})
    win = sim.run(600)
    assert win.min[("Unit2", "Cooling/WaterFlow_GB")] < 0.4 * 12
    assert "COOLING_WATER_FLOW_LOW" in win.unit_alarms
    assert "COOLING_GB_L" in ch_alarm_ids(win, "Unit2")
    assert win.max[("Unit2", "Bearings/Thrust/OilBathTemp")] > oil0 + 5


def sig_rough(sim):
    sim.run(5)
    vib0 = sim.v(("Unit2", "Vibration/TGB/ShaftX/Overall_um_pp"))
    sim.scenario("agc_rough_zone", "Unit2")
    sim.run(300)
    g = sim.v("Powerhouse/Unit2/GatePosition") / 100
    assert 0.45 < g < 0.65
    assert abs(sim.v("Plant/TotalMW") - sim.v("Plant/MWSetpoint")) < 4
    assert sim.v(("Unit2", "Vibration/TGB/ShaftX/Overall_um_pp")) > 1.6 * vib0
    w = next(w for w in NS.ch_waveforms() if w["group"] == "drafttube")
    b = sim.turbines["Unit2"].waveform(w, sim.t)
    f, amp = dominant(b["values"], w["rate"], 0.2, 10)
    assert 0.2 <= f / 5.0 <= 0.4 and amp > 0.05, (f, amp)


def sig_hpu(sim):
    sim.run(5)
    s0 = sim.v(("Unit1", "Governor/HPU/PumpStartsPerHour"))
    sim.scenario("hpu_pump_wear", "Unit1", {"duration_s": 600})
    win = sim.run(2400)
    assert win.max[("Unit1", "Governor/HPU/PumpStartsPerHour")] >= s0 + 8
    assert "HPU_STARTS_H" in ch_alarm_ids(win, "Unit1")
    assert not [a for a in win.unit_alarms if a.startswith("TRIP")]


def sig_shear(sim):
    sim.run(5)
    vib0, mw0 = sim.v(("Unit1", "Vibration/TGB/ShaftX/Overall_um_pp")), sim.v("Powerhouse/Unit1/MW")
    sim.scenario("shear_pin", "Unit1")
    win = sim.run(60)
    assert sim.v(("Unit1", "Turbine/ShearPinStatus")) == "BROKEN"
    assert "SHEAR_PIN_BROKEN" in ch_alarm_ids(win, "Unit1")
    assert sim.v(("Unit1", "Vibration/TGB/ShaftX/Overall_um_pp")) > 1.2 * vib0
    assert abs(sim.v("Powerhouse/Unit1/MW") - mw0) < 4


def sig_unbalance(sim):
    sim.scenario("unbalance", "Unit3")
    win = sim.run(60)
    assert win.min[("Unit3", "Vibration/UGB/ShaftX/Overall_um_pp")] > 140 or \
        sim.v(("Unit3", "Vibration/UGB/ShaftX/Overall_um_pp")) > 140
    assert "VIB_UGB_X_ALERT" in ch_alarm_ids(win, "Unit3")
    w = next(w for w in NS.ch_waveforms() if w["path"] == "Vibration/UGB/ShaftX/Waveform")
    b = sim.turbines["Unit3"].waveform(w, sim.t)
    f, _ = dominant(b["values"], w["rate"], 2, 20)
    assert abs(f - 5.0) < 0.6


def sig_rtd(sim):
    sim.scenario("rtd_fault", "Unit1", {"duration_s": 600})
    win = sim.run(700)
    tb = sim.turbines["Unit1"].last
    assert tb["Bearings/TGB/PadTemp02"][0] - tb["Bearings/TGB/PadTemp03"][0] > 15
    assert tb["Bearings/TGB/PadTemp02"][1] == "GOOD"
    assert win.max["Powerhouse/Unit1/TurbineGuideBearingTemp"] < 70


def sig_low_reservoir(sim):
    sim.scenario("low_reservoir")
    win = sim.run(1300)
    assert win.min["Reservoir/Level"] < 388
    assert win.min["Powerhouse/Unit1/NetHead"] < 85
    assert sim.v("Plant/MWSetpointReachable") is False
    assert sim.v(("Unit1", "Vibration/Headcover/Vel_mm_s_rms")) > 1.3


def sig_flood(sim):
    sim.scenario("flood")
    win = sim.run(1200)
    assert win.max["Spillway/Gate01/Position"] > 20
    assert win.max["River/Flow"] > 300
    assert win.max["Reservoir/Level"] < 420.6


def sig_generator_trip(sim):
    lr = sim.v(("Unit1", "Counters/LoadRejections"))
    sim.scenario("generator_trip", "Unit1")
    win = sim.run(60)
    assert "TRIP_GENERATOR_PROTECTION" in win.unit_alarms
    assert win.max["Powerhouse/Unit1/Speed"] > 1.1 * T.RATED_RPM
    assert sim.v(("Unit1", "Counters/LoadRejections")) == lr + 1


def sig_trash(sim):
    win = sim.run(1)
    sim.scenario("trash_debris")
    win = sim.run(900)
    assert win.max["Intake/TrashRackDP"] > 0.3
    assert any("raker" in e["text"].lower() for e in win.events)


def sig_fouling(sim):
    oil0 = sim.v(("Unit1", "Bearings/TGB/OilTemp"))
    sim.scenario("cooler_fouling", "Unit1", {"duration_s": 600})
    win = sim.run(1500)
    assert sim.v(("Unit1", "Bearings/TGB/OilTemp")) > oil0 + 4
    assert win.min[("Unit1", "Cooling/WaterFlow_TB")] > 7


def sig_ingress(sim):
    lvl0 = sim.v(("Unit1", "Bearings/TGB/OilLevel"))
    sim.scenario("oil_water_ingress", "Unit1", {"duration_s": 600})
    sim.run(700)
    assert sim.v(("Unit1", "Bearings/TGB/OilLevel")) > lvl0 + 5


def _vib_up(sim, sid, unit, path, factor, dur=120):
    sim.run(5)
    v0 = sim.v((unit, path))
    sim.scenario(sid, unit, {"duration_s": dur})
    sim.run(dur + 60)
    assert sim.v((unit, path)) > factor * v0, (sid, v0, sim.v((unit, path)))


def sig_misalignment(sim):
    _vib_up(sim, "misalignment", "Unit1", "Vibration/LGB/ShaftX/Overall_um_pp", 1.5)


def sig_hydraulic(sim):
    _vib_up(sim, "hydraulic_unbalance", "Unit1", "Vibration/TGB/ShaftX/Overall_um_pp", 1.5)


def sig_crack(sim):
    _vib_up(sim, "runner_crack", "Unit1", "Vibration/Headcover/Vel_mm_s_rms", 1.2, dur=300)


def sig_servo(sim):
    sump0 = sim.v(("Unit1", "Governor/HPU/SumpLevel"))
    sim.scenario("servo_seal_leak", "Unit1", {"duration_s": 600})
    sim.run(700)
    tb = sim.turbines["Unit1"].last
    assert sim.v(("Unit1", "Governor/HPU/SumpLevel")) < sump0 - 1.0
    assert tb["Governor/HPU/ServoPositionA"][0] - tb["Governor/HPU/ServoPositionB"][0] > 3


def sig_seal(sim):
    n0 = sim.v(("Unit1", "Turbine/HeadcoverSumpPumpStarts"))
    sim.scenario("shaft_seal_wear", "Unit1", {"duration_s": 600})
    sim.run(1200)
    assert sim.v(("Unit1", "Turbine/ShaftSealWaterFlow")) > 70
    assert sim.v(("Unit1", "Turbine/HeadcoverSumpPumpStarts")) >= n0 + 3


def sig_airgap(sim):
    sim.scenario("air_gap", "Unit1", {"duration_s": 600})
    win = sim.run(700)
    assert sim.v(("Unit1", "Generator/AirGapMin_mm")) < 10.0
    assert "AIRGAP_L" in ch_alarm_ids(win, "Unit1")


SIGNATURES = {
    "tgb_bearing_degradation": sig_tgb, "cooling_strainer": sig_strainer, "agc_rough_zone": sig_rough,
    "hpu_pump_wear": sig_hpu, "shear_pin": sig_shear, "unbalance": sig_unbalance, "rtd_fault": sig_rtd,
    "low_reservoir": sig_low_reservoir, "flood": sig_flood, "generator_trip": sig_generator_trip,
    "trash_debris": sig_trash, "cooler_fouling": sig_fouling, "oil_water_ingress": sig_ingress,
    "misalignment": sig_misalignment, "hydraulic_unbalance": sig_hydraulic, "runner_crack": sig_crack,
    "servo_seal_leak": sig_servo, "shaft_seal_wear": sig_seal, "air_gap": sig_airgap,
}


def test_every_scenario_has_a_signature(models):
    ids = set(models[0].SCENARIOS) | set(models[1].SCENARIOS)
    assert ids == set(SIGNATURES), f"missing: {ids - set(SIGNATURES)}, unknown: {set(SIGNATURES) - ids}"


@pytest.mark.parametrize("sid", sorted(SIGNATURES))
def test_scenario_signature(sim, sid):
    SIGNATURES[sid](sim)


@pytest.mark.parametrize("sid,unit", [("unbalance", "Unit3"), ("cooling_strainer", "Unit2")])
def test_repair_restores_normal(sim, sid, unit):
    sim.scenario(sid, unit, {"duration_s": 120})
    sim.run(240)
    sim.stop_scenario(sid, unit)
    win = sim.run(2400)
    tb = sim.turbines[unit]
    assert not tb.active_alarms(), tb.active_alarms()
    assert sim.v(f"Powerhouse/{unit}/ActiveAlarms") == []
