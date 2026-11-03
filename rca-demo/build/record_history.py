"""Record a historian dataset for the RCA demo: weeks of plant operation from the offline simulator.

Runs the dam and CH models coupled in-process (tools/offline_sim.py) along the story told by the
library (shift log, work orders, MOC register) and writes what a site historian would hold:

    <out>/historian/   what the RCA bot may read
        customer_1min.csv.gz          customer tree, 1-minute averages, one column per tag
        <serial>_1min.csv.gz          CH tree per turbine, 1-minute averages
        customer_1s.csv.gz            customer tree at 1 s for the hours around the event
        <serial>_1s.csv.gz            CH tree at 1 s for the hours around the event
        scada_events.csv              plant events (commands, sequences, trips, refusals)
        ch_plc_alarms.csv             CH PLC alarm log (all three PLCs)
        tags.csv                      every column: file, topic, unit, description
        README.md                     what the files are
    <out>/run.json     instructor only: timeline, scenario, event time, suggested prompt

Only scenario A (Unit 1 TGB pad 3) is scripted so far.

    python3 rca-demo/build/record_history.py                       # full run, ~1.5 h
    python3 rca-demo/build/record_history.py --start 2026-11-02    # last day only (check the timing)
"""

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import offline_sim as O  # noqa: E402

NS = O.NS
TZ = dt.timezone(dt.timedelta(hours=-7), "MST")   # plant local time (no daylight saving)


def at(s):
    """'2026-11-03 09:30' (plant local time) → epoch seconds."""
    return dt.datetime.fromisoformat(s).replace(tzinfo=TZ).timestamp()


def iso(t, seconds=False):
    return dt.datetime.fromtimestamp(round(t), TZ).isoformat(timespec="seconds" if seconds else "minutes")


# ---------------------------------------------------------------------------------------- story
# Scenario A: Unit 1 TGB pad 3 loses its oil film. The severity follows a P-F curve: a slow creep
# for weeks, then faster once the film starts to break down. Pad 3 crosses the CH H alarm (75 °C)
# at ~0.59 at 36 MW, HH (85 °C) at ~0.78 at 36 MW and ~0.73 at 42 MW (Unit 1 runs at 42 MW once
# the Unit 2 trial starts at 06:00 on 3 Nov). Tuned for HH at ~09:30, after the 07:13 shift log entry.
SEV_A = [("2026-10-14 00:00", 0.0), ("2026-11-01 00:00", 0.42), ("2026-11-02 18:00", 0.50),
         ("2026-11-03 09:30", 0.73), ("2026-11-03 14:00", 0.85)]

START, END = "2026-10-13 00:00", "2026-11-03 11:30"
HIRES_FROM = "2026-11-03 08:00"

# (plant time, action, args). Times and texts follow the shift log and work orders in library/.
TIMELINE = [
    ("2026-10-14 00:00", "scenario", ("tgb_bearing_degradation", "Unit1")),
    ("2026-10-18 06:15", "cmd", ("Plant/Cmd/MWSetpoint", 80)),          # Unit 2 annual inspection
    ("2026-10-18 06:25", "cmd", ("Powerhouse/Unit2/Cmd/Stop", True)),
    ("2026-10-21 04:00", "scenario", ("cooling_strainer", "Unit3", {"duration_s": 23 * 3600})),  # rain
    ("2026-10-21 10:30", "stop", ("cooling_strainer", "Unit3")),       # strainer cleaned (L. Ortega)
    ("2026-10-22 15:05", "cmd", ("Powerhouse/Unit2/Cmd/Start", True)),
    ("2026-10-22 15:30", "cmd", ("Plant/Cmd/MWSetpoint", 110)),
    ("2026-11-03 06:00", "scenario", ("agc_rough_zone", "Unit2")),      # MOC-2026-019 trial
]


def evening_peaks(t0, t1, outage=("2026-10-18", "2026-10-22")):
    """Weekday evening peak: the grid operator asks 120 MW from 17:00 to 21:00."""
    out = []
    d = dt.date.fromtimestamp(t0)
    while True:
        day = d.isoformat()
        if at(day + " 17:00") > t1:
            break
        if d.weekday() < 5 and not outage[0] <= day <= outage[1]:
            out += [(day + " 17:00", "cmd", ("Plant/Cmd/MWSetpoint", 120)),
                    (day + " 21:00", "cmd", ("Plant/Cmd/MWSetpoint", 110))]
        d += dt.timedelta(days=1)
    return out


def profile(points):
    pts = [(at(s), v) for s, v in points]

    def f(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (ta, va), (tb, vb) in zip(pts, pts[1:]):
            if t <= tb:
                return va + (vb - va) * (t - ta) / (tb - ta)
        return pts[-1][1]
    return f


# ---------------------------------------------------------------------------------------- output
class Minutes:
    """Averages numeric values per minute (last value for states, flags and lists) and writes rows."""

    def __init__(self, path, cols, dec):
        self.f = gzip.open(path, "wt", newline="")
        self.w = csv.writer(self.f)
        self.w.writerow(["timestamp"] + cols)
        self.cols, self.dec = cols, dec
        self.minute, self.acc = None, {}

    def add(self, t, vals):
        m = int(t // 60)
        if self.minute is not None and m != self.minute:
            self.flush()
        self.minute = m
        for c in self.cols:
            v = vals.get(c)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                s, n = self.acc.get(c, (0.0, 0))
                self.acc[c] = (s + v, n + 1)
            elif v is not None:
                self.acc[c] = v

    def flush(self):
        if self.minute is None:
            return
        row = [iso(self.minute * 60)]
        for c in self.cols:
            row.append(fmt(self.acc.get(c), self.dec.get(c, 2), mean=True))
        self.w.writerow(row)
        self.acc = {}

    def close(self):
        self.flush()
        self.f.close()


class Seconds:
    def __init__(self, path, cols, dec):
        self.f = gzip.open(path, "wt", newline="")
        self.w = csv.writer(self.f)
        self.w.writerow(["timestamp"] + cols)
        self.cols, self.dec = cols, dec

    def add(self, t, vals):
        self.w.writerow([iso(t, True)] + [fmt(vals.get(c), self.dec.get(c, 2)) for c in self.cols])

    def close(self):
        self.f.close()


def fmt(v, dec, mean=False):
    if v is None:
        return ""
    if mean and isinstance(v, tuple):
        v = v[0] / v[1]
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "|".join(map(str, v))
    if isinstance(v, float):
        return f"{v:.{max(dec, 1) if mean else dec}f}"
    return str(v)


# ---------------------------------------------------------------------------------------- run
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "rca-demo", "history", "scenario-A"))
    ap.add_argument("--start", default=START, help="plant time to start (default %(default)s)")
    ap.add_argument("--end", default=END)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    t_start, t_end, t_hires = at(a.start), at(a.end), at(HIRES_FROM)
    hist = os.path.join(a.out, "historian")
    os.makedirs(hist, exist_ok=True)

    sim = O.Sim(seed=a.seed, t0=t_start)
    sev_a = profile(SEV_A)
    pp_cache = {}
    for unit, tb in sim.turbines.items():
        orig_sev, orig_pp = tb.sev, tb.overall_pp

        def sev(sid, tb=tb, orig=orig_sev):
            if sid == "tgb_bearing_degradation" and sid in tb.scen:
                return sev_a(tb.t)
            return orig(sid)

        def overall_pp(b, axis, tb=tb, orig=orig_pp, unit=unit):
            # the 250 S/s synthesis is most of the run time: every 10 s is plenty for 1-min averages
            key = (unit, b, axis)
            hit = pp_cache.get(key)
            if tb.t < t_hires and hit and tb.t - hit[0] < 10:
                return hit[1]
            v = orig(b, axis)
            pp_cache[key] = (tb.t, v)
            return v
        tb.sev, tb.overall_pp = sev, overall_pp

    cust_tags = NS.customer_tags()
    ch_tags = NS.ch_tags()
    cust_cols = [x["path"] for x in cust_tags]
    ch_cols = [x["path"] for x in ch_tags]
    cust_dec = {x["path"]: x["dec"] for x in cust_tags}
    ch_dec = {x["path"]: x["dec"] for x in ch_tags}
    serials = {u: NS.SERIAL_BY_UNIT[u] for u in NS.UNITS}

    mins = {"customer": Minutes(os.path.join(hist, "customer_1min.csv.gz"), cust_cols, cust_dec)}
    for u, s in serials.items():
        mins[u] = Minutes(os.path.join(hist, f"{s}_1min.csv.gz"), ch_cols, ch_dec)
    secs = {}

    ev_f = open(os.path.join(hist, "scada_events.csv"), "w", newline="")
    ev = csv.writer(ev_f)
    ev.writerow(["timestamp", "source", "kind", "text"])
    al_f = open(os.path.join(hist, "ch_plc_alarms.csv"), "w", newline="")
    al = csv.writer(al_f)
    al.writerow(["timestamp", "asset_serial", "alarm_id", "state", "severity", "tag", "value", "limit", "text"])

    # a run that starts late still gets the scenarios already running at its start
    stopped = {args for s, act, args in TIMELINE if act == "stop" and at(s) < t_start}
    timeline = sorted((max(at(s), t_start), act, args) for s, act, args in TIMELINE + evening_peaks(t_start, t_end)
                      if at(s) >= t_start or (act == "scenario" and args[:2] not in stopped))
    story = {"hh": None, "actions": []}
    win = O.Window()

    def do(t, act, args):
        if act == "scenario":
            sim.scenario(args[0], args[1], args[2] if len(args) > 2 else None)
            msg = f"scenario {args[0]} on {args[1]}"
        elif act == "stop":
            sim.stop_scenario(*args)
            msg = f"scenario {args[0]} on {args[1]} cleared"
        else:
            msg = f"{args[0]}={args[1]}: {sim.command(*args)}"
        story["actions"].append((iso(t), msg))

    def sample(s):
        t = s.t
        while timeline and timeline[0][0] <= t:
            do(*timeline.pop(0))
        for e in win.events:
            ev.writerow([iso(e["t"], True), e["source"], e["kind"], e["text"]])
        win.events.clear()
        for unit, e in win.ch_events:
            al.writerow([iso(e["t"], True), serials[unit], e["alarmId"], e["state"], e["severity"],
                         e["tag"], e["value"], e["limit"], e["text"]])
            if e["alarmId"] == "TGB_PAD03_HH" and e["state"] == "ACTIVE" and unit == "Unit1" and not story["hh"]:
                # OP-07: validated as a real bearing problem, load reduced, then a controlled stop
                story["hh"] = t
                timeline.extend([(t + 14 * 60, "cmd", ("Powerhouse/Unit1/Cmd/MWSetpoint", 34)),
                                 (t + 48 * 60, "cmd", ("Powerhouse/Unit1/Cmd/Stop", True))])
                timeline.sort()
        win.ch_events.clear()

        cust = s.dam.values()
        mins["customer"].add(t, cust)
        chv = {u: {k: v for k, (v, q) in tb.last.items()} for u, tb in s.turbines.items()}
        for u in NS.UNITS:
            mins[u].add(t, chv[u])
        if t >= t_hires:
            if not secs:
                secs["customer"] = Seconds(os.path.join(hist, "customer_1s.csv.gz"), cust_cols, cust_dec)
                for u, sr in serials.items():
                    secs[u] = Seconds(os.path.join(hist, f"{sr}_1s.csv.gz"), ch_cols, ch_dec)
            secs["customer"].add(t, cust)
            for u in NS.UNITS:
                secs[u].add(t, chv[u])
        if int(t) % 86400 == 0:
            print(iso(t), "TotalMW", round(cust["Plant/TotalMW"], 1),
                  "U1 TGB pad3", round(chv["Unit1"]["Bearings/TGB/PadTemp03"], 1), flush=True)

    sim.run(t_end - t_start, win=win, on_sample=sample)
    for w in list(mins.values()) + list(secs.values()):
        w.close()
    ev_f.close()
    al_f.close()
    write_tags(hist, serials, cust_tags, ch_tags)
    write_readme(hist, a)

    run = {"scenario": "A tgb_bearing_degradation", "unit": "Unit1", "serial": serials["Unit1"],
           "pad": 3, "severity_profile": SEV_A, "seed": a.seed, "start": iso(t_start), "end": iso(t_end),
           "hh_alarm": iso(story["hh"], True) if story["hh"] else None, "actions": story["actions"],
           "prompt": prompt(story["hh"])}
    with open(os.path.join(a.out, "run.json"), "w") as f:
        json.dump(run, f, indent=2)
    print("HH alarm:", run["hh_alarm"])


def prompt(hh):
    when = dt.datetime.fromtimestamp(hh, TZ).strftime("%-d %b %Y %H:%M") if hh else "3 Nov 2026"
    return (f"Start the Copper Canyon Dam RCA process for Unit 1 (CH-FR-1987-0042): CH PLC alarm "
            f"TGB pad 3 high-high at {when}, unit unloaded and stopped by the shift per OP-07.")


def write_tags(hist, serials, cust_tags, ch_tags):
    with open(os.path.join(hist, "tags.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["files", "column", "topic", "unit", "description"])
        for x in cust_tags:
            w.writerow(["customer_*", x["path"], NS.customer_topic(x["path"]), x["unit"], x["desc"]])
        for x in ch_tags:
            w.writerow(["<serial>_*", x["path"], NS.ch_topic("<serial>", x["path"]), x["unit"], x["desc"]])


def write_readme(hist, a):
    rows = "\n".join(f"| `{s}_1min.csv.gz`, `{s}_1s.csv.gz` | {u} | CH monitoring PLC tree |"
                     for u, s in NS.SERIAL_BY_UNIT.items())
    text = f"""# Copper Canyon Dam historian export

Desert River Water & Power Authority (DRWPA). Fictional, for training only.

Export from the site historian, which records both trees on the site MQTT broker. Times are plant
local time (MST, UTC-07:00, no daylight saving). Period: {a.start} to {a.end}.

| File | Asset | Content |
| --- | --- | --- |
| `customer_1min.csv.gz`, `customer_1s.csv.gz` | Plant | DRWPA SCADA tree (`{NS.CUSTOMER_PREFIX}/…`) |
{rows}
| `scada_events.csv` | Plant | SCADA event journal: commands, sequence steps, trips, refusals |
| `ch_plc_alarms.csv` | All units | CH monitoring PLC alarm log (raised and cleared) |
| `tags.csv` | | Every column: topic, engineering unit, description |

- `*_1min` files hold 1-minute averages (states, flags and alarm lists: last value in the minute)
  for the whole period. `*_1s` files hold raw 1-second values from {HIRES_FROM} to the end.
- One column per tag, named by its path below the tree prefix; `tags.csv` gives the full topic.
  CH columns are the same for every turbine.
- Waveforms are not archived; the overall vibration values (µm pp) are.
- CH PLC alarms are not shown in the control room; the SCADA journal only has the customer's own
  alarms and events.
"""
    with open(os.path.join(hist, "README.md"), "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
