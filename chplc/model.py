"""CH-Francis turbine physics as the CH PLC sees it: one Turbine per asset. No I/O, no clock.

Turbine.step(dt, now, ctx) advances the thermal, HPU and vibration models from the operating point
the PLC copies from the customer tree (ctx); values() is the CH process tree (path → (value,
quality)); waveform(spec, now) synthesises one raw block; hardwired() is element A of the
dual-element sensors, wired to the customer's unit controller; alarms are raised by the PLC's own
limit checks (pop_events()).

Machine-fault scenarios (SCENARIOS) live here and are never published: the data must show them.

Simple but credible physics (design basis "Build plan"):
- bearings: first-order oil and pad temperatures, heat from speed and load, removed by cooling
  water (UA ∝ flow^0.8) and a little by the powerhouse air;
- HPU: accumulator mass balance, lead/lag pumps, leak and pump-wear terms;
- shaft displacement: runout + 1X (unbalance, mechanical ∝ speed², hydraulic ∝ gate) + 2X
  (misalignment) + vortex rope at 0.28 × runner frequency + blade pass + noise.
"""

import math
import random

import namespace as NS
import turbine as T

RUNNING_STATES = ("Starting", "SpeedNoLoad", "Synchronising", "Generating", "Stopping")
CONTEXT_STALE_S = 5.0
T_AMBIENT = 20.0              # powerhouse air

COOL_NOM = {"TB": 8.0, "GB": 12.0, "AirCoolers": 60.0}   # L/s

# bearing: (cooling circuit, heat at rated speed+load in kW, UA to water at nominal flow kW/K,
#           pad rise at rated K, pads)
BEARINGS = {
    "Thrust": ("GB", 60.0, 1.40, 15.0, 6),
    "UGB": ("GB", 12.0, 0.31, 9.0, 4),
    "LGB": ("GB", 14.0, 0.34, 10.0, 4),
    "TGB": ("TB", 16.0, 0.36, 12.0, 4),
}
OIL_TAU_S = 900.0
PAD_TAU_S = 150.0

# HPU
ACC_P_MAX = 64.0
ACC_K = 0.115                 # bar per litre: a 40 L servo stroke costs 4.6 bar (5 strokes 63 → 40)
STROKE_L = 40.0
PUMP_LPS = 4.0
LEAK_LPS = 0.08
LEAD_ON, LEAD_OFF = 58.0, 63.0
LAG_ON, LAG_OFF = 54.0, 61.0

# vibration (0-peak µm unless noted)
VIB_1X = {"UGB": 18.0, "LGB": 14.0, "TGB": 22.0}
VIB_HYD_1X = {"UGB": 2.0, "LGB": 4.0, "TGB": 10.0}       # × gate
VIB_ROPE = {"UGB": 5.0, "LGB": 12.0, "TGB": 30.0}        # × rope intensity
RUNOUT = 3.0
NOISE_UM = 1.5

# PLC alarm limits (demo values; real ones are OEM- and site-specific)
PAD_H, PAD_HH = 75.0, 85.0
OIL_H = 65.0
VIB_ALERT, VIB_DANGER = 140.0, 220.0       # µm pp, shaft relative (zone B/C, C/D in the spirit of ISO 20816-5)
HC_VEL_H = 4.5
ACC_L = 52.0
STARTS_H = 15.0
FILTER_H = 2.5
SUMP_L = 55.0
AIRGAP_L = 10.5
STATOR_H = 120.0

SCENARIOS = {
    "tgb_bearing_degradation": {
        "letter": "A", "label": "Turbine guide bearing degradation", "group": "Bearings", "mode": 1,
        "kind": "ramp", "duration_s": 1200,
        "desc": "One TGB pad (option pad, default 3) loses its oil film: its temperature creeps, then "
                "accelerates; the pad-to-pad spread grows. Weeks compressed to ~20 minutes. The "
                "customer's RTD sits on pad 1 and sees little of it.",
        "options": {"pad": [1, 2, 3, 4]}},
    "cooling_strainer": {
        "letter": "B", "label": "Cooling-water strainer blockage", "group": "Cooling", "mode": 2,
        "kind": "ramp", "duration_s": 480,
        "desc": "The unit's cooling water strainer clogs over ~8 minutes: all three circuit flows "
                "fall to ~30 % and every temperature on them rises together. The customer's flow meter "
                "sees it too; left alone the bearings trip the unit.",
    },
    "hpu_pump_wear": {
        "letter": "D", "label": "HPU pump wear / internal leakage", "group": "Governor & HPU", "mode": 11,
        "kind": "ramp", "duration_s": 1800,
        "desc": "Pump output falls and internal leakage rises (weeks compressed to 30 minutes): more "
                "pump starts per hour, longer runs, faster accumulator pressure decay.",
    },
    "shear_pin": {
        "letter": "E", "label": "Wicket gate shear pin break", "group": "Turbine", "mode": 10,
        "kind": "step",
        "desc": "One shear pin breaks: discrete status, a step in TGB vibration and headcover vibration "
                "at constant MW; the breakaway alarm flickers whenever the gates move.",
    },
    "unbalance": {
        "letter": "F", "label": "Mechanical unbalance after maintenance", "group": "Vibration", "mode": 4,
        "kind": "step",
        "desc": "A balance weight left off after an overhaul: 1X amplitude ~4× at the generator "
                "bearings (UGB over the vibration alert) with a phase shift, stable phase, growing with speed².",
    },
    "rtd_fault": {
        "letter": "G", "label": "RTD sensor fault (CH element)", "group": "Sensors", "mode": 15,
        "kind": "ramp", "duration_s": 1500,
        "desc": "One CH RTD element (option tag, default TGB pad 2) drifts up to +20 °C (option mode: "
                "drift, flatline, spike) while its neighbours, and the customer's element A, stay normal. "
                "Quality stays GOOD: the PLC doesn't know.",
        "options": {"mode": ["drift", "flatline", "spike"],
                    "tag": [f"Bearings/{b}/PadTemp{i:02d}" for b in NS.GUIDE_BEARINGS for i in range(2, 5)]
                    + [f"Bearings/Thrust/PadTemp{i:02d}" for i in range(2, 7)]}},
    # further failure modes from the design basis table (not in the A-H set)
    "cooler_fouling": {
        "letter": None, "label": "Oil cooler fouling", "group": "Cooling", "mode": 2, "kind": "ramp",
        "duration_s": 1800,
        "desc": "Heat transfer of the bearing oil coolers falls by half (months compressed to 30 "
                "minutes); flows stay normal, the cooler outlet gets colder and the oil hotter.",
    },
    "oil_water_ingress": {
        "letter": None, "label": "TGB oil contamination (water ingress)", "group": "Bearings", "mode": 3,
        "kind": "ramp", "duration_s": 1800,
        "desc": "Cooler leak into the TGB oil: the oil level rises slowly (+8 %), temperatures creep.",
    },
    "misalignment": {
        "letter": None, "label": "Misalignment / bearing clearance", "group": "Vibration", "mode": 5,
        "kind": "ramp", "duration_s": 600,
        "desc": "2X grows strongly and the orbits turn elliptical, mostly at the LGB and TGB.",
    },
    "hydraulic_unbalance": {
        "letter": None, "label": "Hydraulic unbalance (runner)", "group": "Vibration", "mode": 6,
        "kind": "ramp", "duration_s": 600,
        "desc": "Uneven runner channels: a 1X component that grows with gate opening, not with speed.",
    },
    "runner_crack": {
        "letter": None, "label": "Runner blade crack", "group": "Turbine", "mode": 9, "kind": "ramp",
        "duration_s": 1800,
        "desc": "A growing crack changes the blade-pass harmonics (2 × 65 Hz and sidebands at ±1X) in "
                "the headcover accelerometer and the TGB probes.",
    },
    "servo_seal_leak": {
        "letter": None, "label": "Servomotor seal leak", "group": "Governor & HPU", "mode": 12,
        "kind": "ramp", "duration_s": 1800,
        "desc": "External oil leak at servomotor B: the sump level drops and servo B lags the setpoint.",
    },
    "shaft_seal_wear": {
        "letter": None, "label": "Shaft seal wear", "group": "Turbine", "mode": 13, "kind": "ramp",
        "duration_s": 1800,
        "desc": "Seal water flow and headcover sump pump starts rise, headcover pressure creeps up.",
    },
    "air_gap": {
        "letter": None, "label": "Generator air-gap anomaly", "group": "Generator", "mode": 14,
        "kind": "ramp", "duration_s": 1800,
        "desc": "A loose rim segment: the minimum air gap shrinks from ~11.6 to ~9.5 mm.",
    },
}

WAVE_DEC = {"shaft": 1, "drafttube": 3, "accel": 2}


def lag(x, target, tau, dt):
    return target if tau <= 0 else x + (target - x) * min(1.0, dt / tau)


class Turbine:
    def __init__(self, asset, seed=None, now=0.0, start_generating=True, cw_temp=14.0, counters=None):
        self.serial = asset["serial"]
        self.unit = asset["unit"]
        self.asset = asset
        self.rng = random.Random(asset["seed"] if seed is None else seed)
        self.noise = random.Random((asset["seed"] if seed is None else seed) + 1000)
        self.t = now
        self.cw_base = cw_temp
        self.ctx = {}                 # Context path -> (value, received_at)
        self.scen = {}
        self.events = []
        self.alarm_state = {}         # alarm id -> active?
        self.counters = counters or {"Starts": 4211 + asset["seed"] * 7, "RunHours": 151000.0 + asset["seed"] * 731.3,
                                     "EmergencyStops": 38 + asset["seed"] % 5, "LoadRejections": 11 + asset["seed"] % 3}
        self.prev_state = None
        self.prev_mw = 0.0

        r = self.rng
        self.pad_off = {b: [r.gauss(0, 1.2) for _ in range(spec[4])] for b, spec in BEARINGS.items()}
        self.stator_off = [r.gauss(0, 2.0) for _ in range(6)]
        self.phase = {b: r.uniform(0, 2 * math.pi) for b in NS.GUIDE_BEARINGS}
        self.phase2 = {b: r.uniform(0, 2 * math.pi) for b in NS.GUIDE_BEARINGS}
        self.theta0 = r.uniform(0, 2 * math.pi)
        self.rope_phase = r.uniform(0, 2 * math.pi)
        self.wave_offset = r.uniform(0, 30)

        # state
        self.flow = {c: (v if start_generating else 0.0) for c, v in COOL_NOM.items()}
        self.oil = {}
        self.pad = {}
        op = (1.0, 0.82, 0.75) if start_generating else (0.0, 0.0, 0.0)   # speed, load, gate
        for b in BEARINGS:
            self.oil[b] = self._oil_ss(b, *op)
            self.pad[b] = [self._pad_ss(b, i, *op) for i in range(BEARINGS[b][4])]
        self.stator = [self._stator_ss(i, op[1] * T.RATED_MW, 6.0) for i in range(6)]
        self.acc_p = 60.5
        self.pumps = [False, False]
        # start times (both pumps), for starts/hour; seeded with an hour of normal duty (~6.6/h)
        self.pump_runs = [now - 540.0 * k - r.uniform(0, 60) for k in range(6, 0, -1)]
        self.pump_duty = 0.1
        self.hpu_oil = 38.0
        self.sump = 68.0
        self.sump_base = 68.0
        self.filter_dp_base = 0.9 + r.uniform(0, 0.3)
        self.prev_gate = op[2]
        self.servo_b_err = 0.0
        self.seal_sump = 0.0
        self.sump_pump_starts = 18000 + asset["seed"] * 13
        self.breakaway = False
        self.drift = 0.0
        self.frozen = {}
        self.spike_until = 0.0
        self.last = {}
        self.settled = False

    # ------------------------------------------------------------------ context
    def set_context(self, path, value, now):
        self.ctx[path] = (value, now)

    def c(self, path, default=0.0):
        v = self.ctx.get(path)
        return default if v is None or v[0] is None else v[0]

    def ctx_quality(self, path):
        v = self.ctx.get(path)
        if v is None:
            return "BAD"
        return "GOOD" if self.t - v[1] <= CONTEXT_STALE_S else "UNCERTAIN"

    def op(self):
        """(speed fraction, load fraction, gate fraction, net head, running) from the context."""
        speed = max(0.0, float(self.c("Context/Speed_rpm"))) / T.RATED_RPM
        mw = max(0.0, float(self.c("Context/MW")))
        gate = max(0.0, float(self.c("Context/GatePosition_pct"))) / 100
        head = float(self.c("Context/NetHead_m", T.RATED_HEAD_M)) or T.RATED_HEAD_M
        state = self.c("Context/UnitState", "Stopped")
        return speed, mw / T.RATED_MW, gate, head, state in RUNNING_STATES or speed > 0.02

    # ------------------------------------------------------------------ scenarios
    def sev(self, sid):
        st = self.scen.get(sid)
        if not st:
            return 0.0
        spec = SCENARIOS[sid]
        if spec["kind"] == "step":
            return 1.0
        dur = float(st["options"].get("duration_s") or spec.get("duration_s", 600))
        return max(0.0, min(1.0, (self.t - st["t0"]) / dur))

    def start_scenario(self, sid, options=None):
        if sid not in SCENARIOS:
            raise KeyError(sid)
        if sid in self.scen:
            raise ValueError("already running")
        self.scen[sid] = {"t0": self.t, "options": dict(options or {})}
        if sid == "rtd_fault":
            self.drift = 0.0
            self.frozen = {}

    def stop_scenario(self, sid):
        self.scen.pop(sid, None)
        if sid == "rtd_fault":
            self.frozen = {}

    def ground_truth(self):
        out = {}
        for sid, st in self.scen.items():
            spec = SCENARIOS[sid]
            out[sid] = {"label": spec["label"], "letter": spec["letter"], "severity": round(self.sev(sid), 3),
                        "running_s": round(self.t - st["t0"]), "options": st["options"]}
        return {"active": out}

    # ------------------------------------------------------------------ steady states
    def _cool_factor(self, circuit):
        nom = COOL_NOM[circuit]
        f = max(0.0, self.flow[circuit] / nom)
        foul = 1.0 - 0.5 * self.sev("cooler_fouling")
        return (max(f, 1e-3) ** 0.8) * foul

    def _bearing_heat(self, b, speed, load, gate):
        circuit, q, ua, rise, n = BEARINGS[b]
        s15 = speed ** 1.5
        if b == "Thrust":
            return q * s15 * (0.55 + 0.45 * load)
        radial = 1.0
        if b == "TGB":
            radial += 0.25 * T.rope_intensity(gate, speed) + 0.15 * self.sev("hydraulic_unbalance") * gate
            radial += 0.25 * self.sev("misalignment") + (0.2 if self.scen.get("shear_pin") else 0.0)
        if b in ("UGB", "LGB"):
            radial += 0.3 * (1.0 if self.scen.get("unbalance") else 0.0) * speed ** 2
            radial += 0.25 * self.sev("misalignment") * (b == "LGB")
        return q * s15 * (0.6 + 0.4 * load) * radial

    def _oil_ss(self, b, speed, load, gate, running=None):
        circuit, q, ua, rise, n = BEARINGS[b]
        if not hasattr(self, "flow"):
            return 45.0
        heat = self._bearing_heat(b, speed, load, gate)
        if b == "TGB":
            heat += 1.5 * self._tgb_fault_heat()
        uac = ua * self._cool_factor(circuit)
        uaa = 0.1 * ua
        tcw = self.cw_temp()
        return (heat + uac * tcw + uaa * T_AMBIENT) / (uac + uaa)

    def _tgb_fault_heat(self):
        s = self.sev("tgb_bearing_degradation")
        return s ** 2.2

    def _pad_ss(self, b, i, speed, load, gate):
        circuit, q, ua, rise, n = BEARINGS[b]
        base = rise * speed ** 1.5 * (0.5 + 0.5 * load)
        if b == "TGB":
            base *= 1.0 + 0.3 * T.rope_intensity(gate, speed)
            st = self.scen.get("tgb_bearing_degradation")
            if st:
                bad = int(st["options"].get("pad", 3)) - 1
                s = self.sev("tgb_bearing_degradation")
                extra = 32.0 * s ** 2.2 * speed
                dist = min(abs(i - bad), n - abs(i - bad))      # pads sit on a ring
                base += extra * (1.0, 0.18, 0.06)[min(dist, 2)]
        return self.oil.get(b, 45.0) + base + self.pad_off[b][i]

    def _stator_ss(self, i, mw, mvar):
        s = math.hypot(max(mw, 0), mvar) / 44.0
        air = self.cw_temp() + 12.0 + 10.0 * (1 - self._cool_factor("AirCoolers"))
        return air + 55.0 * s ** 2 + self.stator_off[i]

    def cw_temp(self):
        day = 2 * math.pi * (self.t % 86400) / 86400
        return self.cw_base + 0.8 * math.sin(day - 2.0)

    # ------------------------------------------------------------------ step
    def settle(self):
        """Warm start: jump to the steady state of the current operating point (first full context).

        A real PLC retrofitted on a running unit starts measuring a warm machine; without this a
        fresh stack would show an hour of warm-up drift."""
        speed, load, gate, head, running = self.op()
        for circ, nom in COOL_NOM.items():
            self.flow[circ] = nom if running else 0.0
        for b in BEARINGS:
            self.oil[b] = self._oil_ss(b, speed, load, gate)
            self.pad[b] = [self._pad_ss(b, i, speed, load, gate) for i in range(BEARINGS[b][4])]
        mw, mvar = max(0.0, float(self.c("Context/MW"))), float(self.c("Context/MVAr"))
        self.stator = [self._stator_ss(i, mw, mvar) for i in range(6)]
        self.prev_gate = gate
        self.prev_state = self.c("Context/UnitState", "Stopped")
        self.settled = True

    def step(self, dt, now):
        self.t = now
        if not self.settled and all(p in self.ctx for p in NS.CH_CONTEXT):
            self.settle()
        speed, load, gate, head, running = self.op()
        state = self.c("Context/UnitState", "Stopped")
        self._counters(dt, state)

        # cooling water: the unit's cooling pump runs whenever the unit isn't at rest
        block = 0.7 * self.sev("cooling_strainer")
        for circ, nom in COOL_NOM.items():
            target = nom * (1.0 - block) if running else 0.0
            self.flow[circ] = lag(self.flow[circ], target, 4.0, dt)

        for b, spec in BEARINGS.items():
            uac = spec[2] * self._cool_factor(spec[0])
            tau = OIL_TAU_S * (spec[2] * 1.1) / (uac + 0.1 * spec[2])
            self.oil[b] = lag(self.oil[b], self._oil_ss(b, speed, load, gate), tau, dt)
            self.pad[b] = [lag(p, self._pad_ss(b, i, speed, load, gate), PAD_TAU_S, dt)
                           for i, p in enumerate(self.pad[b])]
        mw = max(0.0, float(self.c("Context/MW")))
        mvar = float(self.c("Context/MVAr"))
        self.stator = [lag(x, self._stator_ss(i, mw, mvar), 600.0, dt) for i, x in enumerate(self.stator)]

        self._hpu(dt, gate)
        self._seal(dt, running, head)
        if self.scen.get("rtd_fault"):
            self.drift = min(20.0, 20.0 * self.sev("rtd_fault"))
        self.last = self.values()
        self._check_alarms()

    def _counters(self, dt, state):
        prev = self.prev_state
        if prev is not None and state != prev:
            if prev == "Stopped" and state == "Starting":
                self.counters["Starts"] += 1
            if state == "Tripped":
                self.counters["EmergencyStops"] += 1
                if self.prev_mw > 5.0:
                    self.counters["LoadRejections"] += 1
        if state == "Generating":
            self.counters["RunHours"] += dt / 3600.0
        self.prev_state = state
        self.prev_mw = float(self.c("Context/MW"))

    def _hpu(self, dt, gate):
        wear = self.sev("hpu_pump_wear")
        q_pump = PUMP_LPS * (1.0 - 0.55 * wear)
        leak = LEAK_LPS * (1.0 + 3.0 * wear)
        moved = abs(gate - self.prev_gate)
        self.breakaway = bool(self.scen.get("shear_pin")) and moved / max(dt, 1e-3) > 0.002
        self.prev_gate = gate
        use = moved * STROKE_L / max(dt, 1e-3) + 0.01 * (gate > 0)
        p = self.acc_p
        lead, lagp = self.pumps
        if not lead and p <= LEAD_ON:
            lead = True
            self.pump_runs.append(self.t)
        elif lead and p >= LEAD_OFF:
            lead = False
        if not lagp and p <= LAG_ON:
            lagp = True
            self.pump_runs.append(self.t)
        elif lagp and p >= LAG_OFF:
            lagp = False
        self.pumps = [lead, lagp]
        q_in = q_pump * (lead + lagp)
        self.acc_p = max(0.0, min(ACC_P_MAX, p + (q_in - use - leak) * ACC_K * dt))
        self.pump_runs = [t for t in self.pump_runs if self.t - t <= 3600]
        self.pump_duty = lag(self.pump_duty, 1.0 if (lead or lagp) else 0.0, 1800.0, dt)
        self.hpu_oil = lag(self.hpu_oil, 33.0 + 18.0 * self.pump_duty + 0.4 * (self.cw_temp() - 14.0), 1200.0, dt)
        acc_oil = (self.acc_p - 40.0) / ACC_K           # litres of oil held in the accumulator above 40 bar
        self.sump_base -= 0.25 * self.sev("servo_seal_leak") * dt / 60.0   # external leak: % per minute at full severity
        self.sump = self.sump_base - acc_oil / 2000.0 * 100.0 * 0.5
        self.servo_b_err = 6.0 * self.sev("servo_seal_leak") ** 1.5

    def _seal(self, dt, running, head):
        wear = self.sev("shaft_seal_wear")
        rate = (1 / 1200.0) * (1.0 + 4.0 * wear) * (1.0 if running else 0.3)   # sump pump starts per second
        self.seal_sump += rate * dt
        if self.seal_sump >= 1.0:
            self.seal_sump -= 1.0
            self.sump_pump_starts += 1

    # ------------------------------------------------------------------ vibration
    def _vib_components(self, b, speed, gate):
        """(1X amp µm, 1X phase, 2X amp, 2X phase, Y/X ellipticity, rope amp, blade-pass amp)."""
        a1_mech = VIB_1X[b] * speed ** 2
        ph1 = self.phase[b]
        if self.scen.get("unbalance"):
            factor = {"UGB": 4.2, "LGB": 3.4, "TGB": 1.8}[b]
            a1_mech *= factor
            ph1 += math.radians(60)
        hyd = (VIB_HYD_1X[b] + {"UGB": 2.0, "LGB": 12.0, "TGB": 35.0}[b] * self.sev("hydraulic_unbalance")) * gate
        if self.scen.get("shear_pin") and b == "TGB":
            hyd += 9.0
        if b == "TGB":
            a = self.sev("tgb_bearing_degradation")
            hyd += 6.0 * max(0.0, a - 0.7) / 0.3 * speed
        # 1X mechanical and hydraulic add as vectors (hydraulic at a fixed angle to the mechanical)
        x = a1_mech * math.cos(ph1) + hyd * math.cos(ph1 + 1.2)
        y = a1_mech * math.sin(ph1) + hyd * math.sin(ph1 + 1.2)
        a1, p1 = math.hypot(x, y), math.atan2(y, x)
        mis = self.sev("misalignment")
        a2 = (0.15 * VIB_1X[b] + {"UGB": 4.0, "LGB": 30.0, "TGB": 26.0}[b] * mis) * speed ** 2
        ell = 1.0 - 0.55 * mis * (b != "UGB")
        rope = VIB_ROPE[b] * T.rope_intensity(gate, speed)
        bp = (0.6 + 2.5 * self.sev("runner_crack")) * (b == "TGB") * speed
        return a1, p1, a2, self.phase2[b], ell, rope, bp

    def shaft_signal(self, b, axis, times, speed, gate, rng):
        """Displacement samples (µm) at the given times for one probe; X and Y are 90° apart."""
        a1, p1, a2, p2, ell, rope, bp = self._vib_components(b, speed, gate)
        f1 = T.RATED_RPM / 60.0 * speed
        fr = T.ROPE_FREQ_RATIO * f1
        out = []
        noise = NOISE_UM * (1.0 + 0.6 * (1.0 if self.scen.get("shear_pin") and b == "TGB" else 0.0))
        yoff = -math.pi / 2 if axis == "Y" else 0.0
        k = ell if axis == "Y" else 1.0
        rope_mod = 1.0 + 0.25 * math.sin(self.rope_phase * 0.37)
        for t in times:
            th = self.theta0 + 2 * math.pi * f1 * t
            v = RUNOUT * math.cos(th + 0.4 + yoff)
            v += k * a1 * math.cos(th - p1 + yoff)
            v += k * a2 * math.cos(2 * th - p2 + 2 * yoff)
            if rope:
                v += rope * rope_mod * math.cos(self.rope_phase + 2 * math.pi * fr * t + yoff)
            if bp:
                v += bp * math.cos(T.RUNNER_BLADES * th + yoff)
            v += rng.gauss(0, noise)
            out.append(v)
        return out

    def overall_pp(self, b, axis):
        speed, load, gate, head, running = self.op()
        rng = random.Random(self.noise.random())
        times = [self.t + i / 250.0 for i in range(250)]
        s = self.shaft_signal(b, axis, times, speed, gate, rng)
        return max(s) - min(s)

    def headcover_vel(self):
        speed, load, gate, head, running = self.op()
        cav = T.cavitation_index(gate, head, float(self.c("Context/TailwaterLevel_m", 304.5))) * speed
        rope = T.rope_intensity(gate, speed)
        v_bp = (0.9 + 0.6 * gate) * speed
        v_rope = 2.8 * rope
        v_cav = 1.2 * cav
        v_sp = 2.2 if self.scen.get("shear_pin") else 0.0
        v_cr = 1.2 * self.sev("runner_crack") * speed
        v_1x = 0.25 * speed
        return math.sqrt(v_bp ** 2 + v_rope ** 2 + v_cav ** 2 + v_sp ** 2 + v_cr ** 2 + v_1x ** 2) / math.sqrt(2)

    def waveform(self, spec, now, trigger="periodic", rate=None, seconds=None):
        """One raw block for a namespace.ch_waveforms() spec. Returns the payload dict (without seq)."""
        rate = rate or spec["rate"]
        n = int(round((seconds or spec["seconds"]) * rate))
        speed, load, gate, head, running = self.op()
        rng = random.Random(self.noise.random())
        times = [now + i / rate for i in range(n)]
        f1 = T.RATED_RPM / 60.0 * speed
        group = spec["group"]
        if group == "shaft":
            parts = spec["path"].split("/")
            b, axis = parts[1], parts[2][-1]
            values = self.shaft_signal(b, axis, times, speed, gate, rng)
        elif group == "drafttube":
            values = self._drafttube(times, speed, gate, head, rng)
        else:
            values = self._accel(times, speed, gate, head, rng)
        kp = []
        if f1 > 0.05:
            for i, t in enumerate(times):
                th = (self.theta0 + 2 * math.pi * f1 * t) % (2 * math.pi)
                th_prev = (self.theta0 + 2 * math.pi * f1 * (t - 1 / rate)) % (2 * math.pi)
                if th < th_prev:
                    kp.append(i)
        dec = WAVE_DEC[group]
        return {"timestamp": None, "sampleRate": rate, "samples": n, "unit": spec["unit"],
                "speedRpm": round(speed * T.RATED_RPM, 1), "keyphasorIdx": kp, "trigger": trigger,
                "values": [round(v, dec) for v in values]}

    def drafttube_mean(self):
        speed, load, gate, head, running = self.op()
        tw = float(self.c("Context/TailwaterLevel_m", 304.5))
        q = T.flow(gate, head) if speed > 0.05 else 0.0
        vel_head = (q / 9.0) ** 2 / (2 * T.G)
        return T.RHO * T.G * (tw - 297.0 - vel_head) / 1e5

    def _drafttube(self, times, speed, gate, head, rng):
        mean = self.drafttube_mean()
        rope = T.rope_intensity(gate, speed)
        f1 = T.RATED_RPM / 60.0 * speed
        fr = T.ROPE_FREQ_RATIO * f1
        amp = 0.25 * rope
        out = []
        for t in times:
            v = mean + amp * math.cos(self.rope_phase + 2 * math.pi * fr * t)
            v += 0.3 * amp * math.cos(2 * (self.rope_phase + 2 * math.pi * fr * t) + 0.7)
            v += 0.004 * speed * math.cos(self.theta0 + 2 * math.pi * f1 * t)
            v += rng.gauss(0, 0.006 + 0.012 * gate * speed)
            out.append(v)
        return out

    def _accel(self, times, speed, gate, head, rng):
        f1 = T.RATED_RPM / 60.0 * speed
        fbp = T.RUNNER_BLADES * f1
        cav = T.cavitation_index(gate, head, float(self.c("Context/TailwaterLevel_m", 304.5))) * speed
        crack = self.sev("runner_crack") * speed
        a_bp = (0.9 + 0.6 * gate) * speed * 2 * math.pi * fbp / 1000.0          # from v_bp (mm/s)
        a_2bp = (0.15 + 1.2 * crack) * a_bp
        sideband = 0.6 * crack * a_bp
        burst = 4.0 * cav
        floor = 0.08 + (0.35 if self.scen.get("shear_pin") else 0.0)
        out = []
        prev = 0.0
        for t in times:
            th = self.theta0 + 2 * math.pi * f1 * t
            v = a_bp * math.sin(T.RUNNER_BLADES * th) + a_2bp * math.sin(2 * T.RUNNER_BLADES * th + 0.5)
            if sideband:
                v += sideband * (math.sin((T.RUNNER_BLADES + 1) * th) + math.sin((T.RUNNER_BLADES - 1) * th))
            if burst:
                # broadband high-frequency bursts, modulated at blade pass (bubble collapse)
                env = max(0.0, math.sin(T.RUNNER_BLADES * th)) ** 4
                w = rng.gauss(0, 1)
                hf = w - prev               # first difference ≈ high-pass
                prev = w
                v += burst * env * hf
            v += rng.gauss(0, floor)
            out.append(v)
        return out

    # ------------------------------------------------------------------ outputs
    def values(self):
        """CH process tree: path → (value, quality)."""
        n = self.noise
        speed, load, gate, head, running = self.op()
        out = {}
        for path in NS.CH_CONTEXT:
            out[path] = (self.c(path, None), self.ctx_quality(path))
        for b, spec in BEARINGS.items():
            for i, p in enumerate(self.pad[b]):
                out[f"Bearings/{b}/PadTemp{i + 1:02d}"] = (p + n.gauss(0, 0.05), "GOOD")
            oil_key = "OilBathTemp" if b == "Thrust" else "OilTemp"
            out[f"Bearings/{b}/{oil_key}"] = (self.oil[b] + n.gauss(0, 0.04), "GOOD")
            lvl = {"Thrust": 62.0, "UGB": 58.0, "LGB": 57.0, "TGB": 55.0}[b] + 0.08 * (self.oil[b] - 45.0)
            if b == "TGB":
                lvl += 8.0 * self.sev("oil_water_ingress")
            out[f"Bearings/{b}/OilLevel"] = (lvl + n.gauss(0, 0.1), "GOOD")
        state = self.c("Context/UnitState", "Stopped")
        lift_on = state in ("Starting", "Stopping", "Tripped") and speed < 0.3 and (speed > 0.001 or state == "Starting")
        lift = 118.0 if lift_on else 0.0
        out["Bearings/Thrust/HPLiftPressure"] = (lift + (n.gauss(0, 0.5) if lift else 0.0), "GOOD")
        if self.scen.get("oil_water_ingress"):
            s = self.sev("oil_water_ingress")
            out["Bearings/TGB/OilTemp"] = (out["Bearings/TGB/OilTemp"][0] + 3.0 * s, "GOOD")

        out["Cooling/WaterInletTemp"] = (self.cw_temp() + n.gauss(0, 0.03), "GOOD")
        for circ in COOL_NOM:
            out[f"Cooling/WaterFlow_{circ}"] = (max(0.0, self.flow[circ] * (1 + n.gauss(0, 0.008))), "GOOD")
        # oil cooler water outlet: inlet + heat picked up / (flow·cp)
        heat = sum(BEARINGS[b][2] * self._cool_factor(BEARINGS[b][0]) * (self.oil[b] - self.cw_temp())
                   for b in BEARINGS)
        fl = self.flow["TB"] + self.flow["GB"]
        out["Cooling/OilCoolerOutletTemp"] = (self.cw_temp() + (heat / (4.19 * fl) if fl > 0.5 else 2.0)
                                              + n.gauss(0, 0.03), "GOOD")

        out["Governor/HPU/AccumulatorPressure"] = (self.acc_p + n.gauss(0, 0.03), "GOOD")
        out["Governor/HPU/SumpLevel"] = (self.sump + n.gauss(0, 0.05), "GOOD")
        out["Governor/HPU/OilTemp"] = (self.hpu_oil + n.gauss(0, 0.03), "GOOD")
        out["Governor/HPU/Pump1Running"] = (self.pumps[0], "GOOD")
        out["Governor/HPU/Pump2Running"] = (self.pumps[1], "GOOD")
        out["Governor/HPU/PumpStartsPerHour"] = (len(self.pump_runs), "GOOD")
        running_pumps = self.pumps[0] + self.pumps[1]
        fdp = self.filter_dp_base * (running_pumps * (1 - 0.55 * self.sev("hpu_pump_wear")))
        out["Governor/HPU/FilterDP"] = (max(0.0, fdp + n.gauss(0, 0.01)), "GOOD")
        g = gate * 100
        out["Governor/HPU/ServoPositionA"] = (g + n.gauss(0, 0.05), "GOOD")
        out["Governor/HPU/ServoPositionB"] = (max(0.0, g - self.servo_b_err * (g > 1) + 0.12 + n.gauss(0, 0.05)), "GOOD")
        gsp = self.ctx.get("Governor/HPU/GateSetpoint")
        out["Governor/HPU/GateSetpoint"] = (None if gsp is None else gsp[0],
                                            "BAD" if gsp is None else ("GOOD" if self.t - gsp[1] <= CONTEXT_STALE_S else "UNCERTAIN"))

        tw = float(self.c("Context/TailwaterLevel_m", 304.5))
        out["Turbine/SpiralCasePressure"] = (T.RHO * T.G * (head + tw - 300.0 + 1.5) / 1e5 + n.gauss(0, 0.01), "GOOD")
        out["Turbine/HeadcoverPressure"] = ((1.2 + 0.018 * head * gate) * (speed > 0.05)
                                            + 0.15 + 0.8 * self.sev("shaft_seal_wear") + n.gauss(0, 0.01), "GOOD")
        out["Turbine/DraftTubePressure"] = (self.drafttube_mean() + n.gauss(0, 0.003), "GOOD")
        out["Turbine/ShaftSealWaterFlow"] = ((38.0 + 45.0 * self.sev("shaft_seal_wear")) * (1 if running else 0.4)
                                             + n.gauss(0, 0.4), "GOOD")
        out["Turbine/HeadcoverSumpPumpStarts"] = (self.sump_pump_starts, "GOOD")
        out["Turbine/ShearPinStatus"] = ("BROKEN" if self.scen.get("shear_pin") else "OK", "GOOD")
        out["Turbine/WicketGateBreakawayAlarm"] = (self.breakaway, "GOOD")

        for b in NS.GUIDE_BEARINGS:
            for ax in ("X", "Y"):
                out[f"Vibration/{b}/Shaft{ax}/Overall_um_pp"] = (self.overall_pp(b, ax), "GOOD")
        out["Vibration/Headcover/Vel_mm_s_rms"] = (self.headcover_vel() * (1 + n.gauss(0, 0.03)), "GOOD")
        gap = 11.6 - 2.1 * self.sev("air_gap") ** 1.3
        out["Generator/AirGapMin_mm"] = (gap + n.gauss(0, 0.02) if speed > 0.5 else 12.0 + n.gauss(0, 0.02), "GOOD")
        for i, s in enumerate(self.stator):
            out[f"Generator/StatorTemp{i + 1:02d}"] = (s + n.gauss(0, 0.1), "GOOD")
        out["Counters/Starts"] = (self.counters["Starts"], "GOOD")
        out["Counters/RunHours"] = (self.counters["RunHours"], "GOOD")
        out["Counters/EmergencyStops"] = (self.counters["EmergencyStops"], "GOOD")
        out["Counters/LoadRejections"] = (self.counters["LoadRejections"], "GOOD")
        self._sensor_fault(out)
        return out

    def _sensor_fault(self, out):
        st = self.scen.get("rtd_fault")
        if not st:
            return
        tag = st["options"].get("tag", "Bearings/TGB/PadTemp02")
        mode = st["options"].get("mode", "drift")
        if tag not in out:
            return
        v, q = out[tag]
        if mode == "drift":
            out[tag] = (v + self.drift, q)
        elif mode == "flatline":
            if tag not in self.frozen:
                self.frozen[tag] = round(v, 2)
            out[tag] = (self.frozen[tag], q)
        elif mode == "spike":
            if self.t >= self.spike_until and self.noise.random() < 0.05:
                self.spike_until = self.t + 1.0
            if self.t < self.spike_until:
                out[tag] = (v + 45.0 + self.noise.uniform(0, 30), q)

    def hardwired(self):
        """Element A of the dual-element sensors (the customer's copper). Not affected by rtd_fault."""
        out = {}
        for h in NS.HARDWIRED:
            if h["key"] == "CoolingWaterFlow":
                out[h["key"]] = round(sum(self.flow.values()) * (1 + self.noise.gauss(0, 0.005)), 2)
            elif h["ch"].startswith("Bearings/"):
                b, pad = h["ch"].split("/")[1], int(h["ch"][-2:]) - 1
                out[h["key"]] = round(self.pad[b][pad] + 0.3 + self.noise.gauss(0, 0.05), 2)
            else:
                out[h["key"]] = round(self.acc_p + self.noise.gauss(0, 0.03), 2)
        return out

    # ------------------------------------------------------------------ PLC alarms
    def alarm_defs(self):
        """(id, tag, op, limit, severity, text, only_running). The PLC's own limit checks."""
        d = []
        for b, spec in BEARINGS.items():
            for i in range(spec[4]):
                tag = f"Bearings/{b}/PadTemp{i + 1:02d}"
                d.append((f"{b}_PAD{i + 1:02d}_H", tag, ">", PAD_H, "WARNING", f"{b} pad {i + 1} temperature high", False))
                d.append((f"{b}_PAD{i + 1:02d}_HH", tag, ">", PAD_HH, "CRITICAL", f"{b} pad {i + 1} temperature very high", False))
            oil = "OilBathTemp" if b == "Thrust" else "OilTemp"
            d.append((f"{b}_OIL_H", f"Bearings/{b}/{oil}", ">", OIL_H, "WARNING", f"{b} oil temperature high", False))
        for circ, nom in COOL_NOM.items():
            d.append((f"COOLING_{circ.upper()}_L", f"Cooling/WaterFlow_{circ}", "<", 0.7 * nom, "WARNING",
                      f"Cooling water flow low ({circ})", True))
        d += [
            ("HPU_PRESSURE_L", "Governor/HPU/AccumulatorPressure", "<", ACC_L, "WARNING", "HPU accumulator pressure low", False),
            ("HPU_STARTS_H", "Governor/HPU/PumpStartsPerHour", ">", STARTS_H, "WARNING", "HPU pump starts per hour high", False),
            ("HPU_FILTER_H", "Governor/HPU/FilterDP", ">", FILTER_H, "WARNING", "HPU filter differential pressure high", False),
            ("HPU_SUMP_L", "Governor/HPU/SumpLevel", "<", SUMP_L, "WARNING", "HPU sump level low", False),
            ("SHEAR_PIN_BROKEN", "Turbine/ShearPinStatus", "==", "BROKEN", "CRITICAL", "Wicket gate shear pin broken", False),
            ("HEADCOVER_VIB_H", "Vibration/Headcover/Vel_mm_s_rms", ">", HC_VEL_H, "WARNING", "Headcover vibration high", True),
            ("AIRGAP_L", "Generator/AirGapMin_mm", "<", AIRGAP_L, "WARNING", "Generator minimum air gap low", True),
        ]
        for b in NS.GUIDE_BEARINGS:
            for ax in ("X", "Y"):
                tag = f"Vibration/{b}/Shaft{ax}/Overall_um_pp"
                d.append((f"VIB_{b}_{ax}_ALERT", tag, ">", VIB_ALERT, "WARNING", f"{b} shaft vibration {ax} alert", True))
                d.append((f"VIB_{b}_{ax}_DANGER", tag, ">", VIB_DANGER, "CRITICAL", f"{b} shaft vibration {ax} danger", True))
        for i in range(6):
            d.append((f"STATOR_{i + 1:02d}_H", f"Generator/StatorTemp{i + 1:02d}", ">", STATOR_H, "WARNING",
                      f"Stator temperature {i + 1} high", False))
        return d

    def _check_alarms(self):
        vals = self.last
        running = self.op()[4]
        for aid, tag, op, limit, sev, text, only_running in self.alarm_defs():
            v = vals.get(tag, (None, "BAD"))[0]
            was = self.alarm_state.get(aid, False)
            if v is None or (only_running and not running):
                active = False
            elif op == "==":
                active = v == limit
            else:
                # 1 % deadband on clearing
                band = abs(limit) * 0.01
                if op == ">":
                    active = v > limit if not was else v > limit - band
                else:
                    active = v < limit if not was else v < limit + band
            if active != was:
                self.alarm_state[aid] = active
                self.events.append({"alarmId": aid, "state": "ACTIVE" if active else "CLEARED", "severity": sev,
                                    "tag": tag, "value": v if not isinstance(v, float) else round(v, 2),
                                    "limit": limit, "text": text, "t": self.t,
                                    "vibration": aid.startswith(("VIB_", "SHEAR", "HEADCOVER"))})

    def active_alarms(self):
        return sorted(a for a, on in self.alarm_state.items() if on)

    def pop_events(self):
        ev, self.events = self.events, []
        return ev
