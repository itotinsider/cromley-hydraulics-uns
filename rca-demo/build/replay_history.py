"""Replay a recorded historian (history/<scenario>/historian/) onto the broker, faster than real time.

The dam SCADA and the CH viewer then show what the control room could have seen, from the same data
the RCA bot gets. dam-sim and ch-plc-sim must be stopped first (run it through rca-demo/replay.sh),
otherwise they publish the live trees over the replay.

Each wall second the latest recorded row of every tree is published (retained, like the simulators),
plus the SCADA events and CH PLC alarms that fall in that step. Payload timestamps are the wall clock,
so SCADA trends, journal and clock agree; the console prints the plant time (MST), the events and the
shift log entries as they come up.

  python rca-demo/build/replay_history.py [--history DIR] [--from T] [--to T] [--speed N]
                                          [--slow-from T --slow-to T --slow-speed N] [--host H --port P]
                                          [--pause-at T,T,... --pause-s N]

Defaults (scenario A): 2 Nov 22:00 to 3 Nov 10:15, 120x, 08:55-10:00 at 5x: about 19 minutes.
"""

import argparse
import csv
import datetime as dt
import gzip
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from common import mqttio, namespace as NS  # noqa: E402

TZ = dt.timezone(dt.timedelta(hours=-7), "MST")


def at(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=TZ).timestamp()


def epoch(ts):
    return dt.datetime.fromisoformat(ts).timestamp()


def plant(t):
    return dt.datetime.fromtimestamp(t, TZ).strftime("%d %b %H:%M:%S")


def value(raw, col):
    if col.endswith("ActiveAlarms"):
        return [x for x in raw.split("|") if x]
    if raw == "":
        return None
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return int(raw) if raw.lstrip("-").isdigit() else float(raw)
    except ValueError:
        return raw


def rows(path, t0, t1, before=None):
    """[(epoch, {col: raw})] with t0 - 60 s <= t <= t1 (and t < before), oldest first."""
    if not os.path.exists(path):
        return [], []
    with gzip.open(path, "rt", newline="") as f:
        r = csv.reader(f)
        head = next(r)[1:]
        out = []
        for row in r:
            t = epoch(row[0])
            if t < t0 - 60 or t > t1 or (before is not None and t >= before):
                continue
            out.append((t, dict(zip(head, row[1:]))))
    return head, out


class Source:
    """One tree (customer or one CH asset): 1-min rows, then 1-s rows where those exist."""

    def __init__(self, hist, prefix, t0, t1):
        _, fine = rows(os.path.join(hist, f"{prefix}_1s.csv.gz"), t0, t1)
        first_fine = fine[0][0] if fine else None
        _, coarse = rows(os.path.join(hist, f"{prefix}_1min.csv.gz"), t0, t1, before=first_fine)
        self.rows = coarse + fine
        self.i = 0

    def at(self, t):
        while self.i + 1 < len(self.rows) and self.rows[self.i + 1][0] <= t:
            self.i += 1
        return self.rows[self.i][1] if self.rows and self.rows[self.i][0] <= t + 60 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--history", default=os.path.join(ROOT, "rca-demo/history/scenario-A/historian"))
    ap.add_argument("--from", dest="start", default="2026-11-02 22:00")
    ap.add_argument("--to", dest="end", default="2026-11-03 10:15")
    ap.add_argument("--speed", type=float, default=120, help="plant seconds per wall second")
    ap.add_argument("--slow-from", default="2026-11-03 08:55")
    ap.add_argument("--slow-to", default="2026-11-03 10:00")
    ap.add_argument("--slow-speed", type=float, default=5)
    ap.add_argument("--pause-at", default="", help="comma-separated plant times to hold at (screenshots, talking)")
    ap.add_argument("--pause-s", type=float, default=30, help="wall seconds per pause")
    ap.add_argument("--host", default=os.environ.get("MQTT_HOST", "mosquitto"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
    a = ap.parse_args()
    t0, t1, s0, s1 = at(a.start), at(a.end), at(a.slow_from), at(a.slow_to)

    units = {}
    with open(os.path.join(a.history, "tags.csv"), newline="") as f:
        for r in csv.DictReader(f):
            units[r["column"]] = r["unit"]
    serials = [x["serial"] for x in NS.ASSETS]
    print(f"loading {a.history} ...", flush=True)
    cust = Source(a.history, "customer", t0, t1)
    ch = {s: Source(a.history, s, t0, t1) for s in serials}
    with open(os.path.join(a.history, "scada_events.csv"), newline="") as f:
        sev = [(epoch(r["timestamp"]), r) for r in csv.DictReader(f)]
    with open(os.path.join(a.history, "ch_plc_alarms.csv"), newline="") as f:
        alm = [(epoch(r["timestamp"]), r) for r in csv.DictReader(f)]
    log = []
    shift = os.path.join(ROOT, "rca-demo/library/drwpa/records/shift-log_2026-09_2026-11.csv")
    if os.path.exists(shift):
        with open(shift, newline="") as f:
            log = [(at(r["timestamp"]), r) for r in csv.DictReader(f)]

    active = {s: set() for s in serials}           # CH PLC alarms standing when the replay starts
    for t, r in alm:
        if t <= t0:
            (active[r["asset_serial"]].add if r["state"] == "ACTIVE" else active[r["asset_serial"]].discard)(r["alarm_id"])

    client = mqttio.make_client("rca-replay", a.host, a.port)
    for _ in range(50):
        if client.is_connected():
            break
        time.sleep(0.1)
    if not client.is_connected():
        sys.exit(f"no broker at {a.host}:{a.port}")
    seq = {s: 0 for s in serials}

    def next_seq(s):
        seq[s] += 1
        return seq[s]

    def pub_ch(s, path, payload, retain=False):
        client.publish(NS.ch_topic(s, path), payload, qos=0 if retain else 1, retain=retain)

    for s in serials:
        client.publish(NS.ch_topic(s, NS.META_STATUS), "ONLINE", qos=1, retain=True)
        pub_ch(s, "Events/ActiveAlarms", json.dumps({"timestamp": mqttio.iso(), "seq": next_seq(s),
                                                     "value": sorted(active[s])}), retain=True)
        if active[s]:
            print(f"  standing CH PLC alarms {s}: {', '.join(sorted(active[s]))}")
    dur, t = 0, t0
    while t <= t1:
        dur, t = dur + 1, t + (a.slow_speed if s0 <= t < s1 else a.speed)
    print(f"replaying {plant(t0)} → {plant(t1)} MST, {a.speed:g}x ({plant(s0)}–{plant(s1)} at {a.slow_speed:g}x), "
          f"about {dur / 60:.0f} min. Ctrl-C stops.", flush=True)

    pauses = sorted(at(x.strip()) for x in a.pause_at.split(",") if x.strip())
    hold = 0
    t, prev, wall, last_status = t0, t0 - 1, time.time(), 0
    try:
        while t <= t1:
            now = time.time()
            row = cust.at(t)
            if row:
                for col, raw in row.items():
                    v = value(raw, col)
                    if v is not None:
                        client.publish(NS.customer_topic(col), mqttio.customer_payload(v, units.get(col, ""), now),
                                       qos=0, retain=True)
            for s, src in ch.items():
                r = src.at(t)
                for col, raw in (r or {}).items():
                    v = value(raw, col)
                    if v is not None:
                        pub_ch(s, col, mqttio.ch_payload(v, units.get(col, ""), next_seq(s), "GOOD", now),
                               retain=True)
            for te, r in sev:
                if prev < te <= t:
                    client.publish(NS.customer_topic(NS.EVENTS_TOPIC), json.dumps(
                        {"timestamp": mqttio.iso(now), "source": r["source"], "kind": r["kind"], "text": r["text"]},
                        ensure_ascii=False), qos=1)
                    if r["kind"] != "info":
                        print(f"{plant(te)}  SCADA journal   {r['text']}", flush=True)
            for te, r in alm:
                if prev < te <= t:
                    s = r["asset_serial"]
                    (active[s].add if r["state"] == "ACTIVE" else active[s].discard)(r["alarm_id"])
                    pub_ch(s, NS.EVENTS_ALARM, json.dumps(
                        {"timestamp": mqttio.iso(now), "seq": next_seq(s), "serial": s, "alarmId": r["alarm_id"],
                         "state": r["state"], "severity": r["severity"], "tag": r["tag"], "value": value(r["value"], ""),
                         "limit": value(r["limit"], ""), "text": r["text"]}, ensure_ascii=False))
                    pub_ch(s, "Events/ActiveAlarms", json.dumps({"timestamp": mqttio.iso(now), "seq": next_seq(s),
                                                                 "value": sorted(active[s])}), retain=True)
                    print(f"{plant(te)}  CH PLC {s}  {r['alarm_id']} {r['state']}  ({r['value']} / {r['limit']}; "
                          f"CH viewer only, not on the SCADA)", flush=True)
            for te, r in log:
                if prev < te <= t:
                    print(f"{plant(te)}  shift log {r['shift']}   {r['entry']}", flush=True)
            if now - last_status >= 15 and row:
                last_status = now
                u1 = ch[NS.SERIAL_BY_UNIT["Unit1"]].at(t) or {}
                print(f"{plant(t)}  ...  U1 {row.get('Powerhouse/Unit1/MW', '?')} MW, SCADA TGB "
                      f"{row.get('Powerhouse/Unit1/TurbineGuideBearingTemp', '?')} °C | CH TGB pad 3 "
                      f"{u1.get('Bearings/TGB/PadTemp03', '?')} °C", flush=True)
            if pauses and t >= pauses[0]:
                pauses.pop(0)
                hold = int(a.pause_s)
                print(f"{plant(t)}  PAUSED for {hold} s", flush=True)
            if hold > 0:
                hold -= 1
                prev = t                   # same snapshot again, no events
            else:
                nt = t + (a.slow_speed if s0 <= t < s1 else a.speed)
                if pauses and t < pauses[0] < nt:
                    nt = pauses[0]
                prev, t = t, nt
            wall += 1.0
            time.sleep(max(0.0, wall - time.time()))
    except KeyboardInterrupt:
        print("stopped")
    client.on_disconnect = None
    client.disconnect()
    client.loop_stop()
    print(f"done at {plant(min(t, t1))} MST. Retained values on the broker are the replay's last ones until "
          "the simulators run again.")


if __name__ == "__main__":
    main()
