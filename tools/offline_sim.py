"""Dam simulator + CH PLC models coupled in-process, faster than real time (no broker, no HTTP).

The Sim class is the behaviour-test harness: it wires the two models exactly as the containers do
(customer tree → CH context every second, CH hardwired → dam every second), without MQTT.

    python tools/offline_sim.py --minutes 30 --every 60 --scenario tgb_bearing_degradation:Unit1@60 \
        --cmd Plant/Cmd/MWSetpoint=90@600 --cols Plant/TotalMW,Unit1:Bearings/TGB/PadTemp03

--scenario id[:unit]@seconds (dam or CH scenario), --cmd <command path>=<value>@seconds,
--cols customer paths, or <unit>:<CH path> for a CH tag.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "common"))

import importlib.util  # noqa: E402

import namespace as NS  # noqa: E402


def _load(name, rel):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


dam_model = _load("dam_model", "damsim/model.py")
ch_model = _load("ch_model", "chplc/model.py")


class Window:
    """min/max per customer path and CH (unit, path) over a run, plus events and alarms seen."""

    def __init__(self):
        self.min, self.max, self.last = {}, {}, {}
        self.events, self.ch_events = [], []
        self.unit_alarms = set()

    def add(self, key, v):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            self.last[key] = v
            return
        self.last[key] = v
        self.min[key] = min(v, self.min.get(key, v))
        self.max[key] = max(v, self.max.get(key, v))


class Sim:
    def __init__(self, seed=1, t0=1_760_000_000.0, **dam_kw):
        self.t = t0
        self.dam = dam_model.Dam(seed=seed, now=t0, **dam_kw)
        self.turbines = {a["unit"]: ch_model.Turbine(a, seed=a["seed"] * 10 + seed, now=t0) for a in NS.ASSETS}
        self.dt = 0.1
        self._couple()
        for tb in self.turbines.values():       # first PLC scan, so every value exists from t0
            tb.step(1.0, self.t)
            tb.pop_events()
        self._couple()

    def _couple(self):
        vals = self.dam.values()
        for unit, tb in self.turbines.items():
            for ch_path, cust in {**NS.CH_CONTEXT, **NS.CH_CONTEXT_EXTRA}.items():
                v = vals.get(cust.format(unit=unit))
                if v is not None:
                    tb.set_context(ch_path, v, self.t)
            self.dam.set_hardwired(unit, tb.hardwired(), self.t)

    def command(self, path, value):
        return self.dam.command(path, value)

    def scenario(self, sid, unit=None, options=None):
        if sid in dam_model.SCENARIOS:
            self.dam.start_scenario(sid, unit, options)
        else:
            self.turbines[unit or "Unit1"].start_scenario(sid, options)

    def stop_scenario(self, sid, unit=None):
        if sid in dam_model.SCENARIOS:
            self.dam.stop_scenario(sid)
        else:
            self.turbines[unit or "Unit1"].stop_scenario(sid)

    def run(self, seconds, until=None, win=None, every=None, on_sample=None):
        """Advance; once per simulated second couple the models, step the PLCs, record in win."""
        win = win or Window()
        end = self.t + seconds
        next_s = self.t + 1.0
        while self.t < end - 1e-9:
            self.t += self.dt
            self.dam.step(self.dt, self.t)
            if self.t >= next_s - 1e-9:
                next_s += 1.0
                self._couple()
                for tb in self.turbines.values():
                    tb.step(1.0, self.t)
                    for e in tb.pop_events():
                        win.ch_events.append((tb.unit, e))
                vals = self.dam.values()
                for k, v in vals.items():
                    win.add(k, v)
                for unit, tb in self.turbines.items():
                    for k, (v, q) in tb.last.items():
                        win.add((unit, k), v)
                    win.unit_alarms.update(vals.get(f"Powerhouse/{unit}/ActiveAlarms", []))
                win.events += self.dam.events
                self.dam.events = []
                if on_sample:
                    on_sample(self)
                if until and until(self):
                    break
        return win

    def v(self, key):
        """A customer path, or (unit, CH path)."""
        if isinstance(key, tuple):
            return self.turbines[key[0]].last.get(key[1], (None,))[0]
        return self.dam.values().get(key)


def _parse_col(c):
    if ":" in c:
        u, p = c.split(":", 1)
        return (u, p)
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--every", type=float, default=60, help="print a row every N simulated seconds")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--scenario", action="append", default=[])
    ap.add_argument("--cmd", action="append", default=[])
    ap.add_argument("--cols", default="Plant/TotalMW,Reservoir/Level,Powerhouse/Unit1/MW,Unit1:Bearings/TGB/PadTemp01")
    a = ap.parse_args()
    sim = Sim(seed=a.seed)
    t0 = sim.t
    timed = []
    for s in a.scenario:
        sid, at = s.split("@")
        unit = None
        if ":" in sid:
            sid, unit = sid.split(":")
        timed.append((float(at), "scenario", sid, unit))
    for c in a.cmd:
        cmd, at = c.rsplit("@", 1)
        path, val = cmd.split("=", 1)
        timed.append((float(at), "cmd", path, val))
    timed.sort()
    cols = [_parse_col(c) for c in a.cols.split(",")]
    print("t_s\t" + "\t".join(c if isinstance(c, str) else f"{c[0]}:{c[1]}" for c in cols))
    state = {"next": 0.0}

    def sample(s):
        el = s.t - t0
        while timed and timed[0][0] <= el:
            _, kind, x, y = timed.pop(0)
            if kind == "scenario":
                s.scenario(x, y)
                print(f"# {el:.0f}s scenario {x} {y or ''}")
            else:
                print(f"# {el:.0f}s {x}={y}: {s.command(x, y)}")
        if el >= state["next"] - 1e-6:
            state["next"] += a.every
            row = []
            for c in cols:
                v = s.v(c)
                row.append(f"{v:.2f}" if isinstance(v, float) else str(v))
            print(f"{el:.0f}\t" + "\t".join(row))

    sim.run(a.minutes * 60, on_sample=sample)


if __name__ == "__main__":
    main()
