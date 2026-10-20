"""Copper Canyon Dam: hydraulics, three generating units and the plant controller. No I/O, no clock.

Dam.step(dt, now) advances everything; Dam.values() is the customer tree (path → value);
Dam.command(path, value) applies a Cmd topic; Dam.set_hardwired() feeds the customer's turbine
sensors (element A of the dual-element sensors, see common/namespace.HARDWIRED).

Instructor scenarios that belong to the dam live here (SCENARIOS); the turbine's machine faults
live in the CH PLC simulator. Neither is ever published.
"""

import math
import random

import namespace as NS
import turbine as T

# ------------------------------------------------------------------------- site data (demo)
CREST_M = 425.0
LEVEL_MAX_OP = 420.0          # top of the operating range
LEVEL_MIN_OP = 385.0          # bottom of the operating range
LEVEL_MIN_START = 384.0       # start permissive (intake vortexing below)
SPILL_CREST_M = 410.0         # spillway ogee crest
SPILL_CD = 31.6               # m^0.5·m²/s per gate at full opening: ~1,000 m³/s at 420 m
SPILL_AUTO_OPEN_M = 419.0     # AUTO: gates start to open here, fully open at 420
BOTTOM_Q_MAX = 50.0           # fixed-cone valve at rated head
MIN_RIVER_FLOW = 10.0         # m³/s, always
MANIFOLD_ELEV_M = 300.0       # penstock manifold elevation
PENSTOCK_K = 1.0e-4           # head loss m per (m³/s)²: ~1.8 m at 135 m³/s
BRANCH_K = 2.0e-4             # unit branch loss
TRASH_K = 1.0                 # trash rack loss multiplies its DP (already in m)

INERTIA_2H = 8.0              # 2H in s (generator + runner + entrained water)
GATE_OPEN_RATE = 1 / 15       # full stroke in 15 s
GATE_CLOSE_RATE = 1 / 6       # full stroke in 6 s (from the transient study)
INLET_VALVE_TIME = 15.0       # s, open or close
MW_RAMP_UP = 12.0 / 60        # MW/s
MW_RAMP_DOWN = 20.0 / 60
DROOP = 0.05                  # permanent speed droop
OVERSPEED_TRIP = 1.45         # pu
BRAKE_SPEED = 0.30            # pu: brakes applied below this when stopping
BRAKE_PU = 0.10               # brake torque
CHURN_PU = 0.15               # runner churning in the water with the gates closed: ~2 min coastdown
SYNC_TIME = 8.0
EXCITE_TIME = 5.0
COOLING_CHECK_S = 10.0
COOLING_FLOW_MIN = 56.0       # L/s: 70 % of the 80 L/s nominal total
GOV_OIL_START_MIN = 55.0      # bar: start permissive
GOV_OIL_LL = 48.0             # bar: trip (two servo strokes left)
GOV_OIL_L = 52.0
BEARING_H = 80.0              # °C: unit controller alarm on the customer RTDs
BEARING_HH = 90.0             # °C: trip
TRIP_DELAY_S = 5.0
HARDWIRED_STALE_S = 5.0
HARDWIRED_GRACE_S = 20.0      # after start-up, before a never-seen hardwired link is a fault
ROUGH_MARGIN_MW = 0.5

DEFAULT_PLANT_SP = 110.0
AGC_SPAN = 5.0                # MW, ± around the grid operator's setpoint

TRIP_CODES = ("TRIP_OVERSPEED", "TRIP_BEARING_TEMP", "TRIP_GOV_OIL_PRESSURE", "TRIP_EMERGENCY_STOP",
              "TRIP_GENERATOR_PROTECTION")
WARN_CODES = ("BEARING_TEMP_HIGH", "COOLING_WATER_FLOW_LOW", "GOV_OIL_PRESSURE_LOW", "HARDWIRED_IO_FAULT")


def reservoir_area(h):
    """Surface area in m²: 8 km² at 385 m, 15 km² at 420 m."""
    return 8.0e6 + 2.0e5 * (h - 385.0)


def reservoir_volume_hm3(h):
    return (8.0e6 * (h - 380.0) + 1.0e5 * ((h - 385.0) ** 2 - 25.0)) / 1e6


def tailwater_for(q_river):
    """Rating curve below the powerhouse: ~304.5 m at 135 m³/s, ~310.6 m at 2,000 m³/s."""
    return 303.0 + 0.08 * max(q_river, 0.0) ** 0.6


def approach(x, target, rate, dt):
    step = rate * dt
    return target if abs(target - x) <= step else x + math.copysign(step, target - x)


# ------------------------------------------------------------------------- instructor scenarios
SCENARIOS = {
    "agc_rough_zone": {
        "letter": "C", "label": "AGC parks a unit in the rough zone", "group": "Operation",
        "target": "unit", "default_unit": "Unit2", "kind": "latched",
        "desc": "The plant controller's rough-zone table is bypassed for one unit: it gets a part-load "
                "setpoint in the middle of the vortex-rope zone, the other units take the rest. Same plant MW.",
    },
    "low_reservoir": {
        "letter": "H", "label": "Low reservoir, low head (drought drawdown)", "group": "Operation",
        "target": "plant", "kind": "latched",
        "desc": "Dry inflow and a drawdown compressed to minutes: the level falls to ~386.5 m a.s.l. "
                "(1.5 m/min). Head drops to ~80 m: efficiency loss, more flow per MW, cavitation. "
                "Stopping it refills at the same rate.",
    },
    "flood": {
        "letter": None, "label": "Flood inflow", "group": "Operation", "target": "plant", "kind": "latched",
        "desc": "The level is brought close to 420 m a.s.l. (compressed), then the inflow rises to "
                "1,200 m³/s. The spillway gates open in AUTO. Stopping it ends the flood and restores the level.",
    },
    "generator_trip": {
        "letter": None, "label": "Generator protection trip (load rejection)", "group": "Electrical",
        "target": "unit", "default_unit": "Unit1", "kind": "instant",
        "desc": "The generator protection opens the breaker under load: load rejection, speed rise, "
                "emergency stop. Reset at standstill.",
    },
    "trash_debris": {
        "letter": None, "label": "Debris on the trash rack", "group": "Operation", "target": "plant",
        "kind": "timed", "duration_s": 900,
        "desc": "Storm debris: trash rack differential pressure rises 40x faster than normal for 15 "
                "minutes; the raker can't keep up.",
    },
}


class Unit:
    def __init__(self, name, rng):
        self.name = name
        self.rng = rng
        self.state = "Generating"
        self.speed = 1.0              # pu
        self.gate = 0.75
        self.gate_sp = 0.75
        self.integ = 0.0
        self.breaker = True
        self.excited = True
        self.inlet = 1.0              # inlet valve 0..1
        self.brakes = False
        self.control_mode = "PLANT"
        self.mw_sp_local = 30.0
        self.mw_sp = 33.0             # effective setpoint (plant controller or local)
        self.mw_ref = 33.0            # ramped
        self.mw = 33.0
        self.mvar = 6.0
        self.flow = 0.0
        self.net_head = 100.0
        self.step_t = 0.0             # time in current sequence step
        self.substep = ""
        self.trip_cause = None
        self.hold = {}                # protection delay timers
        self.hw = {}                  # hardwired values
        self.hw_ts = None
        self.warnings = set()
        self.rope_phase = rng.random() * 6.28
        self.forced_trip = None       # scenario: protection trip request

    # -- helpers
    def online(self):
        return self.breaker

    def at_standstill(self):
        return self.speed < 0.005

    def alarms(self):
        out = sorted(self.warnings)
        if self.trip_cause:
            out = [self.trip_cause] + out
        return out


class Dam:
    def __init__(self, seed=1, start_level=412.0, inflow_base=115.0, plant_sp=DEFAULT_PLANT_SP, agc=True,
                 now=0.0):
        self.rng = random.Random(seed)
        self.noise = random.Random(seed + 7)     # measurement noise only, so values() doesn't move the process
        self.t = now
        self.t_start = now
        self.level = start_level
        self.inflow_base = inflow_base
        self.inflow_walk = 0.0
        self.inflow = inflow_base
        self.freq = 50.0
        self.units = {u: Unit(u, random.Random(seed * 100 + i)) for i, u in enumerate(NS.UNITS)}
        self.spill = {g: {"pos": 0.0, "sp": 0.0, "mode": "AUTO", "flow": 0.0} for g in NS.SPILLWAY_GATES}
        self.bottom = {"pos": 0.0, "sp": 0.0, "mode": "AUTO", "flow": 0.0, "active": False}
        self.intake = 100.0
        self.intake_sp = 100.0
        self.trash_dp = 0.12
        self.raker = False
        self.raker_t = 0.0
        self.plant_sp_cmd = plant_sp
        self.agc = agc
        self.agc_offset = 0.0
        self.agc_target = 0.0
        self.agc_next = now + 120
        self.plant_sp = plant_sp
        self.reachable = True
        self.k_high = None            # plant controller: how many units above the rough zone
        self.q_units = 0.0
        self.q_river = 0.0
        self.tailwater = 304.5
        self.penstock_p = 10.8
        self.hammer = 0.0
        self.q_prev = None
        self.events = []
        self.scen = {}                # active scenarios: id -> state dict
        self._init_steady()

    # ------------------------------------------------------------------ setup
    def _init_steady(self):
        """Start at the design operating point: all three units generating, plant at its setpoint."""
        n = len(self.units)
        q = 0.0
        for _ in range(4):
            gross = self.level - self.tailwater
            for u in self.units.values():
                u.mw_sp = u.mw_ref = u.mw = self.plant_sp / n
                u.net_head = gross - PENSTOCK_K * q ** 2 - BRANCH_K * (q / n) ** 2 - self.trash_dp
                u.gate = u.gate_sp = T.gate_for_mw(u.mw, u.net_head)
                u.flow = T.flow(u.gate, u.net_head)
            q = sum(u.flow for u in self.units.values())
            self.tailwater = tailwater_for(q + 0.5)
        self.q_units = q
        self.q_river = q + 0.5
        self.penstock_p = self._static_pressure()

    def _static_pressure(self):
        return T.RHO * T.G * (self.level - MANIFOLD_ELEV_M - PENSTOCK_K * self.q_units ** 2 - self.trash_dp) / 1e5

    def event(self, source, text, kind="info"):
        self.events.append({"t": self.t, "source": source, "kind": kind, "text": text})

    # ------------------------------------------------------------------ hardwired input
    def set_hardwired(self, unit, values, now):
        u = self.units[unit]
        u.hw = dict(values)
        u.hw_ts = now

    def hw_ok(self, u):
        return u.hw_ts is not None and self.t - u.hw_ts <= HARDWIRED_STALE_S

    # ------------------------------------------------------------------ commands
    def command(self, path, value):
        """Apply one command topic (relative to the customer prefix). Returns (ok, message)."""
        parts = path.split("/")
        try:
            if path == "Plant/Cmd/MWSetpoint":
                v = float(value)
                if not 0 <= v <= 130:
                    return self._refuse("Plant", f"Plant MW setpoint {v} outside 0-130")
                self.plant_sp_cmd = v
                return self._ok("Plant", f"Grid operator: plant setpoint {v:.1f} MW")
            if path == "Plant/Cmd/AGC":
                self.agc = _bool(value)
                if not self.agc:
                    self.agc_offset = self.agc_target = 0.0
                return self._ok("Plant", f"AGC {'on' if self.agc else 'off'}")
            if path == "Intake/Cmd/GatePosition":
                v = float(value)
                if v < 99.5 and any(u.state != "Stopped" for u in self.units.values()):
                    return self._refuse("Intake", "Intake gate close refused: a unit is not stopped")
                self.intake_sp = max(0.0, min(100.0, v))
                return self._ok("Intake", f"Intake gate to {self.intake_sp:.0f} %")
            if parts[0] == "BottomOutlet":
                return self._gate_cmd("BottomOutlet", self.bottom, parts[-1], value)
            if parts[0] == "Spillway" and parts[1] in self.spill:
                return self._gate_cmd(f"Spillway {parts[1]}", self.spill[parts[1]], parts[-1], value)
            if parts[0] == "Powerhouse" and parts[1] in self.units:
                return self._unit_cmd(self.units[parts[1]], parts[-1], value)
        except (TypeError, ValueError):
            return self._refuse("Plant", f"Bad payload for {path}: {value!r}")
        return self._refuse("Plant", f"Unknown command {path}")

    def _ok(self, src, text):
        self.event(src, text, "command")
        return True, text

    def _refuse(self, src, text):
        self.event(src, text, "refused")
        return False, text

    def _gate_cmd(self, name, g, cmd, value):
        if cmd == "Mode":
            v = str(value).upper()
            if v not in NS.GATE_MODES:
                return self._refuse(name, f"{name}: unknown mode {value!r}")
            g["mode"] = v
            g["sp"] = g["pos"]
            return self._ok(name, f"{name} mode {v}")
        if cmd == "Position":
            g["mode"] = "MAN"
            g["sp"] = max(0.0, min(100.0, float(value))) / 100
            return self._ok(name, f"{name} to {g['sp'] * 100:.0f} % (MAN)")
        return self._refuse(name, f"{name}: unknown command {cmd}")

    def _unit_cmd(self, u, cmd, value):
        n = u.name
        if cmd == "Start":
            if u.state != "Stopped":
                return self._refuse(n, f"{n}: start refused, unit is {u.state}")
            why = self._start_permissives(u)
            if why:
                return self._refuse(n, f"{n}: start refused, {why}")
            self._goto(u, "Starting", "CoolingWater")
            u.brakes = False
            return self._ok(n, f"{n}: start sequence")
        if cmd == "Stop":
            if u.state in ("Stopped", "Stopping", "Tripped"):
                return self._refuse(n, f"{n}: stop refused, unit is {u.state}")
            self._goto(u, "Stopping", "Unload")
            return self._ok(n, f"{n}: normal stop")
        if cmd == "EmergencyStop":
            if u.state == "Stopped":
                return self._refuse(n, f"{n}: already stopped")
            self.trip(u, "TRIP_EMERGENCY_STOP")
            return True, "tripped"
        if cmd == "Reset":
            if u.state != "Tripped":
                return self._refuse(n, f"{n}: nothing to reset")
            if not u.at_standstill() or u.inlet > 0.0:
                return self._refuse(n, f"{n}: reset refused, unit not at standstill / inlet valve not closed")
            cause = self._trip_cause_active(u)
            if cause:
                return self._refuse(n, f"{n}: reset refused, {cause} still active")
            u.trip_cause = None
            self._goto(u, "Stopped", "")
            return self._ok(n, f"{n}: trip reset")
        if cmd == "ControlMode":
            v = str(value).upper()
            if v not in NS.CONTROL_MODES:
                return self._refuse(n, f"{n}: unknown control mode {value!r}")
            if v == "LOCAL":
                u.mw_sp_local = u.mw_sp
            u.control_mode = v
            return self._ok(n, f"{n}: control mode {v}")
        if cmd == "MWSetpoint":
            v = float(value)
            if not 0 <= v <= T.RATED_MW * 1.05:
                return self._refuse(n, f"{n}: MW setpoint {v} outside 0-42")
            u.control_mode = "LOCAL"
            u.mw_sp_local = v
            return self._ok(n, f"{n}: local MW setpoint {v:.1f} MW")
        return self._refuse(n, f"{n}: unknown command {cmd}")

    def _start_permissives(self, u):
        if self.intake < 99.5:
            return "intake gate not open"
        if self.level < LEVEL_MIN_START:
            return f"reservoir below {LEVEL_MIN_START} m a.s.l."
        if not self.hw_ok(u):
            return "no signals from the turbine (hardwired I/O fault)"
        if u.hw.get("GovernorOilPressure", 0) < GOV_OIL_START_MIN:
            return f"governor oil pressure below {GOV_OIL_START_MIN} bar"
        return None

    def _trip_cause_active(self, u):
        if not self.hw_ok(u):
            return None
        for k in ("ThrustBearingTemp", "UpperGuideBearingTemp", "LowerGuideBearingTemp", "TurbineGuideBearingTemp"):
            if u.hw.get(k, 0) >= BEARING_HH:
                return f"{k} >= {BEARING_HH} °C"
        return None

    def _goto(self, u, state, sub):
        if state != u.state:
            self.event(u.name, f"{u.name}: {u.state} → {state}", "state")
        u.state, u.substep, u.step_t = state, sub, 0.0

    def trip(self, u, cause):
        if u.state == "Tripped":
            return
        mw = u.mw
        u.trip_cause = cause
        self.event(u.name, f"{u.name}: EMERGENCY STOP {cause}" + (f" at {mw:.1f} MW (load rejection)" if u.breaker and mw > 5 else ""), "trip")
        u.breaker = False
        self._goto(u, "Tripped", "CloseGates")

    # ------------------------------------------------------------------ scenarios
    def start_scenario(self, sid, unit=None, options=None):
        if sid not in SCENARIOS:
            raise KeyError(sid)
        spec = SCENARIOS[sid]
        if sid in self.scen:
            raise ValueError("already running")
        unit = unit or spec.get("default_unit")
        st = {"t0": self.t, "unit": unit if spec["target"] == "unit" else None, "options": options or {}}
        if sid == "low_reservoir":
            st["restore"] = self.level
        if sid == "flood":
            st["restore"] = self.level
        if sid == "generator_trip":
            u = self.units[unit]
            if u.state in ("Generating", "Synchronising", "SpeedNoLoad"):
                u.forced_trip = "TRIP_GENERATOR_PROTECTION"   # instant: nothing stays active
            return
        self.scen[sid] = st

    def stop_scenario(self, sid):
        st = self.scen.pop(sid, None)
        if st and sid in ("low_reservoir", "flood"):
            self.scen[f"_restore_{sid}"] = {"target": st["restore"], "t0": self.t}

    def ground_truth(self):
        """Instructor only: what the simulator knows that the data doesn't say."""
        out = {}
        for sid, st in self.scen.items():
            if sid.startswith("_restore_"):
                out[sid] = {"label": "Restoring the reservoir level (compressed)", "target_level": round(st["target"], 2)}
                continue
            spec = SCENARIOS[sid]
            out[sid] = {"label": spec["label"], "unit": st["unit"], "running_s": round(self.t - st["t0"]),
                        "letter": spec["letter"]}
        return {"active": out,
                "plant_controller": {"k_high": self.k_high, "rough_zone_mw": [round(x, 1) for x in self.rough_zone()],
                                     "agc_offset_mw": round(self.agc_offset, 2)},
                "reservoir_level_m": round(self.level, 3)}

    # ------------------------------------------------------------------ step
    def step(self, dt, now):
        self.t = now
        self._grid(dt)
        self._inflow(dt)
        self._plant_controller(dt)
        gross = self.level - self.tailwater
        q_tot = self.q_units
        for u in self.units.values():
            u.net_head = max(10.0, gross - PENSTOCK_K * q_tot ** 2 - BRANCH_K * u.flow ** 2 - TRASH_K * self.trash_dp
                             - self._intake_loss(q_tot))
            self._unit(u, dt)
            self._protection(u, dt)
        self.q_units = sum(u.flow for u in self.units.values())
        self._gates(dt, gross)
        self._river(dt)
        self._trash(dt)
        self._reservoir(dt)
        self._penstock(dt)

    def _intake_loss(self, q):
        frac = self.intake / 100.0
        if frac >= 0.999:
            return 0.0
        return min(150.0, 0.002 * (q / max(frac, 0.02)) ** 2)

    def _grid(self, dt):
        # Ornstein-Uhlenbeck around 50 Hz: sigma ~0.015 Hz, tau 30 s.
        self.freq += (50.0 - self.freq) * dt / 30.0 + self.rng.gauss(0, 0.015 * math.sqrt(2 * dt / 30.0))

    def _inflow(self, dt):
        self.inflow_walk += -self.inflow_walk * dt / 3600.0 + self.rng.gauss(0, 10.0 * math.sqrt(2 * dt / 3600.0))
        base = self.inflow_base + self.inflow_walk
        if "low_reservoir" in self.scen:
            base = 35.0
        if "flood" in self.scen:
            base = 1200.0
        self.inflow += (base - self.inflow) * min(1.0, dt / 120.0)

    # -- plant controller: grid operator setpoint + AGC, split over the PLANT-mode units
    def rough_zone(self):
        heads = [u.net_head for u in self.units.values()]
        lo, hi = T.rough_zone_mw(sorted(heads)[1])
        return lo - ROUGH_MARGIN_MW, hi + ROUGH_MARGIN_MW

    def _plant_controller(self, dt):
        if self.agc:
            if self.t >= self.agc_next:
                self.agc_target = self.rng.uniform(-AGC_SPAN, AGC_SPAN)
                self.agc_next = self.t + self.rng.uniform(120, 300)
            self.agc_offset = approach(self.agc_offset, self.agc_target, 3.0 / 60, dt)
        self.plant_sp = max(0.0, self.plant_sp_cmd + (self.agc_offset if self.agc else 0.0))

        plant_units = [u for u in self.units.values() if u.control_mode == "PLANT" and u.state == "Generating"]
        local_mw = sum(u.mw_ref for u in self.units.values() if u.state == "Generating" and u.control_mode == "LOCAL")
        for u in self.units.values():
            if u.control_mode == "LOCAL":
                u.mw_sp = u.mw_sp_local
            elif u.state != "Generating":
                u.mw_sp = 0.0
        if not plant_units:
            self.reachable = abs(self.plant_sp - local_mw) < 0.5
            self.k_high = None
            return
        target = max(0.0, self.plant_sp - local_mw)
        rz_lo, rz_hi = self.rough_zone()
        pmax = min(T.max_mw(u.net_head) for u in plant_units)
        n = len(plant_units)

        parked = None
        sc = self.scen.get("agc_rough_zone")
        if sc and self.units[sc["unit"]] in plant_units and n > 1:
            parked = self.units[sc["unit"]]

        if parked:
            # Scenario C: the rough-zone table is bypassed for one unit, it is parked at part load.
            park_mw = T.shaft_mw(T.ROUGH_GATE_PEAK, parked.net_head)
            others = [u for u in plant_units if u is not parked]
            share = max(T.P_MIN_MW, min(pmax, (target - park_mw) / len(others)))
            parked.mw_sp = park_mw
            for u in others:
                u.mw_sp = share
            self.reachable = abs(park_mw + share * len(others) - target) < 1.0
            return

        # k units above the rough zone, n-k below it: the total range each split can make
        span = {k: (k * rz_hi + (n - k) * T.P_MIN_MW, k * pmax + (n - k) * rz_lo) for k in range(n, -1, -1)}
        ks = [k for k, (lo, hi) in span.items() if lo - 1e-6 <= target <= hi + 1e-6]
        if ks:
            k = self.k_high if self.k_high in ks else ks[0]   # hysteresis: keep k while it works
            total = target
        else:
            # Between two splits (or beyond all): never park a unit in the rough zone, take the
            # nearest total the units can make and report the setpoint as not reachable.
            k = min(span, key=lambda k: (min(abs(target - span[k][0]), abs(target - span[k][1])), -k))
            total = max(span[k][0], min(span[k][1], target))
        self.k_high = k
        low_each = 0.0
        if k < n:
            low_each = max(T.P_MIN_MW, min(rz_lo, (total - k * rz_hi) / (n - k)))
        high_each = (total - (n - k) * low_each) / k if k else 0.0
        for i, u in enumerate(sorted(plant_units, key=lambda u: u.name)):
            u.mw_sp = high_each if i < k else low_each
        self.reachable = abs(total - target) < 0.5

    # -- one generating unit: sequence, governor, mechanics
    def _unit(self, u, dt):
        u.step_t += dt
        cooling_ok = self.hw_ok(u) and u.hw.get("CoolingWaterFlow", 0) >= COOLING_FLOW_MIN
        if u.state == "Starting":
            if u.substep == "CoolingWater":
                if u.step_t >= COOLING_CHECK_S:
                    if not cooling_ok:
                        self.event(u.name, f"{u.name}: start aborted, cooling water flow not established", "refused")
                        self._goto(u, "Stopping", "CloseGates")
                    else:
                        u.substep, u.step_t = "InletValve", 0.0
            elif u.substep == "InletValve":
                u.inlet = min(1.0, u.inlet + dt / INLET_VALVE_TIME)
                if u.inlet >= 1.0:
                    u.substep, u.step_t = "Breakaway", 0.0
                    u.brakes = False
            elif u.substep == "Breakaway":
                u.gate_sp = 0.20
                if u.speed >= 0.95:
                    u.integ = 0.0
                    self._goto(u, "SpeedNoLoad", "Excite")
        elif u.state == "SpeedNoLoad":
            self._speed_governor(u, 1.0, dt)
            if u.step_t >= EXCITE_TIME:
                u.excited = True
                self._goto(u, "Synchronising", "")
        elif u.state == "Synchronising":
            self._speed_governor(u, self.freq / 50.0 + 0.002, dt)
            if u.step_t >= SYNC_TIME and abs(u.speed - self.freq / 50.0) < 0.01:
                u.breaker = True
                u.mw_ref = 0.0
                u.integ = 0.0
                self._goto(u, "Generating", "")
        elif u.state == "Generating":
            sp = u.mw_sp if u.control_mode == "PLANT" else u.mw_sp_local
            sp = max(0.0, min(T.max_mw(u.net_head), sp))
            u.mw_ref = approach(u.mw_ref, sp, MW_RAMP_UP if sp > u.mw_ref else MW_RAMP_DOWN, dt)
            self._power_governor(u, dt)
        elif u.state == "Stopping":
            if u.substep == "Unload":
                u.mw_ref = approach(u.mw_ref, 0.0, MW_RAMP_DOWN * 2, dt)
                self._power_governor(u, dt)
                if u.mw < 1.0 and u.mw_ref <= 0.0:
                    u.breaker = False
                    u.substep, u.step_t = "CloseGates", 0.0
            elif u.substep == "CloseGates":
                u.gate_sp = 0.0
                u.excited = False
                if u.gate <= 0.001:
                    u.substep, u.step_t = "Coast", 0.0
            elif u.substep == "Coast":
                u.brakes = u.speed < BRAKE_SPEED
                if u.at_standstill():
                    u.substep, u.step_t = "InletValve", 0.0
            elif u.substep == "InletValve":
                u.inlet = max(0.0, u.inlet - dt / INLET_VALVE_TIME)
                if u.inlet <= 0.0:
                    u.brakes = True
                    self._goto(u, "Stopped", "")
        elif u.state == "Tripped":
            u.breaker = False
            u.excited = False
            u.gate_sp = 0.0
            u.brakes = u.speed < BRAKE_SPEED
            if u.gate <= 0.001 or u.step_t > 2.0:
                u.inlet = max(0.0, u.inlet - dt / INLET_VALVE_TIME)
        elif u.state == "Stopped":
            u.gate_sp = 0.0
            u.brakes = True
            u.excited = False
            u.mw_ref = 0.0

        # servo: rate-limited gate (the HPU's servomotors), inlet valve chokes the flow
        rate = GATE_OPEN_RATE if u.gate_sp > u.gate else GATE_CLOSE_RATE
        u.gate = approach(u.gate, max(0.0, min(1.0, u.gate_sp)), rate, dt)
        eff_gate = u.gate * min(1.0, u.inlet * 1.2) if u.inlet < 1.0 else u.gate
        u.flow = T.flow(eff_gate, u.net_head) * (1.0 if u.speed > 0.05 or eff_gate > 0 else 0.0)

        # mechanics: torque falls linearly with speed to runaway at 2 pu
        p_hyd = T.hydraulic_mw(eff_gate, u.net_head) / T.RATED_MW
        loss = T.MECH_LOSS_MW / T.RATED_MW
        if u.breaker:
            u.speed = self.freq / 50.0
            mw = T.shaft_mw(eff_gate, u.net_head)
            rope = T.rope_intensity(eff_gate, u.speed)
            u.rope_phase += 2 * math.pi * T.ROPE_FREQ_RATIO * 5.0 * dt * (1 + 0.1 * u.rng.gauss(0, 1))
            swing = rope * (1.2 * math.sin(u.rope_phase) + 0.5 * u.rng.gauss(0, 1))
            u.mw = mw + swing
        else:
            churn = CHURN_PU * u.speed ** 2 if u.gate < 0.05 else 0.0   # runner spinning in water, gates shut
            torque = p_hyd * (2.0 - u.speed) - loss * u.speed ** 2 - churn \
                - (BRAKE_PU if u.brakes and u.speed > 0 else 0.0) - 0.004 * (u.speed > 0)
            u.speed = max(0.0, u.speed + torque / INERTIA_2H * dt)
            u.mw = 0.0
        if u.speed > OVERSPEED_TRIP and u.state != "Tripped":
            self.trip(u, "TRIP_OVERSPEED")
        u.mvar = (2.0 + 0.15 * u.mw + u.rng.gauss(0, 0.15)) if u.breaker else 0.0

    def _speed_governor(self, u, target, dt):
        err = target - u.speed
        u.integ = max(-0.2, min(0.3, u.integ + 0.08 * err * dt))
        snl = T.gate_for_mw(0.0, u.net_head)
        u.gate_sp = max(0.0, min(0.4, snl + 2.0 * err + u.integ))

    def _power_governor(self, u, dt):
        pref = u.mw_ref + (50.0 - self.freq) / 50.0 / DROOP * T.RATED_MW
        ff = T.gate_for_mw(max(0.0, pref), u.net_head) if pref > 0 else T.gate_for_mw(0.0, u.net_head)
        err = pref - T.shaft_mw(u.gate, u.net_head)
        u.integ = max(-0.1, min(0.1, u.integ + 0.0005 * err * dt))
        u.gate_sp = max(0.0, min(1.0, ff + u.integ))

    # -- unit protection on the customer's hardwired sensors
    def _protection(self, u, dt):
        u.warnings.clear()
        if u.forced_trip:
            self.trip(u, u.forced_trip)
            u.forced_trip = None
        if not self.hw_ok(u):
            # never seen yet and just started: the CH PLCs may come up a few seconds later
            if u.hw_ts is not None or self.t - self.t_start > HARDWIRED_GRACE_S:
                u.warnings.add("HARDWIRED_IO_FAULT")
            u.hold.clear()
            return
        hot = max(u.hw.get(k, 0) for k in ("ThrustBearingTemp", "UpperGuideBearingTemp", "LowerGuideBearingTemp",
                                           "TurbineGuideBearingTemp"))
        oil = u.hw.get("GovernorOilPressure", 60.0)
        cw = u.hw.get("CoolingWaterFlow", 0.0)
        running = u.state not in ("Stopped", "Tripped")
        if hot >= BEARING_H:
            u.warnings.add("BEARING_TEMP_HIGH")
        if running and u.state != "Starting" and cw < COOLING_FLOW_MIN:
            u.warnings.add("COOLING_WATER_FLOW_LOW")
        if oil < GOV_OIL_L:
            u.warnings.add("GOV_OIL_PRESSURE_LOW")
        for key, cond in (("TRIP_BEARING_TEMP", hot >= BEARING_HH), ("TRIP_GOV_OIL_PRESSURE", oil < GOV_OIL_LL)):
            if cond and running:
                u.hold[key] = u.hold.get(key, 0.0) + dt
                if u.hold[key] >= TRIP_DELAY_S:
                    self.trip(u, key)
            else:
                u.hold.pop(key, None)

    # -- spillway, bottom outlet, intake
    def _gates(self, dt, gross):
        over = max(0.0, self.level - SPILL_CREST_M)
        for gid, g in self.spill.items():
            if g["mode"] == "AUTO":
                g["sp"] = max(0.0, min(1.0, (self.level - SPILL_AUTO_OPEN_M) / (LEVEL_MAX_OP - SPILL_AUTO_OPEN_M)))
            g["pos"] = approach(g["pos"], g["sp"], 0.005, dt)   # 0.5 %/s
            g["flow"] = SPILL_CD * g["pos"] * over ** 1.5
        spill_q = sum(g["flow"] for g in self.spill.values())
        b = self.bottom
        if b["mode"] == "AUTO":
            others = self.q_units + spill_q
            if others < MIN_RIVER_FLOW:
                b["active"] = True
            elif others > MIN_RIVER_FLOW + 5.0:
                b["active"] = False
            if b["active"]:
                want = max(0.0, MIN_RIVER_FLOW + 2.0 - others)
                b["sp"] = min(1.0, want / (BOTTOM_Q_MAX * math.sqrt(max(gross, 1) / 100.0)))
            else:
                b["sp"] = 0.0
        b["pos"] = approach(b["pos"], b["sp"], 0.02, dt)
        b["flow"] = BOTTOM_Q_MAX * b["pos"] * math.sqrt(max(gross, 0) / 100.0)
        self.intake = approach(self.intake, self.intake_sp, 0.5, dt)

    def _river(self, dt):
        spill_q = sum(g["flow"] for g in self.spill.values())
        self.q_river = self.q_units + spill_q + self.bottom["flow"] + 0.5   # + seepage
        self.tailwater += (tailwater_for(self.q_river) - self.tailwater) * min(1.0, dt / 120.0)

    def _trash(self, dt):
        rate = 0.05 / 3600 * (self.q_units / 135.0 + 0.1)   # m per s
        if "trash_debris" in self.scen:
            st = self.scen["trash_debris"]
            rate *= 40
            if self.t - st["t0"] >= SCENARIOS["trash_debris"]["duration_s"]:
                self.scen.pop("trash_debris")
        if self.raker:
            self.raker_t += dt
            self.trash_dp = max(0.06, self.trash_dp - 0.06 / 60 * dt)
            if self.raker_t >= 300 or self.trash_dp <= 0.08:
                self.raker = False
        elif self.trash_dp >= 0.35:
            self.raker, self.raker_t = True, 0.0
            self.event("Intake", "Trash rack raker started", "info")
        self.trash_dp = max(0.0, self.trash_dp + rate * dt + self.rng.gauss(0, 0.0002) * math.sqrt(dt))

    def _reservoir(self, dt):
        out = self.q_units + sum(g["flow"] for g in self.spill.values()) + self.bottom["flow"] + 0.5
        self.level += (self.inflow - out) * dt / reservoir_area(self.level)
        # compressed time for the instructor's reservoir scenarios
        if "low_reservoir" in self.scen and self.level > 386.5:
            self.level = max(386.5, self.level - 1.5 / 60 * dt)
        if "flood" in self.scen and self.t - self.scen["flood"]["t0"] < 400 and self.level < 419.6:
            self.level = min(419.6, self.level + 1.5 / 60 * dt)
        for sid in [s for s in self.scen if s.startswith("_restore_")]:
            st = self.scen[sid]
            self.level = approach(self.level, st["target"], 1.5 / 60, dt)
            if abs(self.level - st["target"]) < 0.01:
                self.scen.pop(sid)

    def _penstock(self, dt):
        q = self.q_units
        dqdt = 0.0 if self.q_prev is None else (q - self.q_prev) / dt
        self.q_prev = q
        self.hammer += (-0.15 * dqdt - self.hammer) * min(1.0, dt / 1.0)
        self.penstock_p = self._static_pressure() + self.hammer

    # ------------------------------------------------------------------ output
    def values(self):
        """The customer tree: path (relative to CUSTOMER_PREFIX) → value. Units/decimals from namespace."""
        gross = self.level - self.tailwater
        v = {
            "Reservoir/Level": self.level,
            "Reservoir/Inflow": self.inflow + self.noise.gauss(0, 0.5),
            "Reservoir/Volume": reservoir_volume_hm3(self.level),
            "River/TailwaterLevel": self.tailwater + self.noise.gauss(0, 0.003),
            "River/Flow": self.q_river,
            "Plant/GrossHead": gross,
            "Plant/TotalMW": sum(u.mw for u in self.units.values()),
            "Plant/MWSetpoint": self.plant_sp,
            "Plant/MWSetpointReachable": self.reachable,
            "Plant/AGCEnabled": self.agc,
            "Plant/GridFrequency": self.freq,
            "Intake/GatePosition": self.intake,
            "Intake/TrashRackDP": self.trash_dp,
            "Intake/RakerRunning": self.raker,
            "Penstock/Pressure": self.penstock_p + self.noise.gauss(0, 0.01),
            "Penstock/Flow": self.q_units,
            "BottomOutlet/ValvePosition": self.bottom["pos"] * 100,
            "BottomOutlet/Flow": self.bottom["flow"],
            "BottomOutlet/Mode": self.bottom["mode"],
        }
        for gid, g in self.spill.items():
            v[f"Spillway/{gid}/Position"] = g["pos"] * 100
            v[f"Spillway/{gid}/Flow"] = g["flow"]
            v[f"Spillway/{gid}/Mode"] = g["mode"]
        for u in self.units.values():
            p = f"Powerhouse/{u.name}"
            v.update({
                f"{p}/State": u.state,
                f"{p}/BreakerClosed": u.breaker,
                f"{p}/ControlMode": u.control_mode,
                f"{p}/MWSetpoint": u.mw_sp if u.control_mode == "PLANT" else u.mw_sp_local,
                f"{p}/MW": u.mw,
                f"{p}/MVAr": u.mvar,
                f"{p}/GatePosition": u.gate * 100,
                f"{p}/GateSetpoint": u.gate_sp * 100,
                f"{p}/Speed": u.speed * T.RATED_RPM,
                f"{p}/Flow": u.flow,
                f"{p}/NetHead": u.net_head,
                f"{p}/InletValveOpen": u.inlet >= 1.0,
                f"{p}/ActiveAlarms": u.alarms(),
            })
            if self.hw_ok(u):
                for h in NS.HARDWIRED:
                    if h["key"] in u.hw:
                        v[f"{p}/{h['key']}"] = u.hw[h["key"]]
        return v


def _bool(v):
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "on", "yes")
    return bool(v)
