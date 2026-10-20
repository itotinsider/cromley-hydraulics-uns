"""CH asset viewer: what Cromley Hydraulics sees of its fleet, from the CH tree only.

Subscribes v1.0/CH/# (never the customer tree): nameplates, PLC status (last will), process
values with quality and seq, alarm events and the latest raw waveform block per channel. It does
no analytics on the waveforms: it shows the raw blocks (time domain, orbit), which is what an edge
vendor starts from.

HTTP :8122:
  GET /api/assets                       serial → nameplate, status, active alarms, message statistics
  GET /api/asset/<serial>               values (value, unit, quality, seq, age), events
  GET /api/waveform/<serial>?path=...   the latest block of one channel (full payload)
  GET /api/trend?serial=&paths=a,b&minutes=30&points=300
"""

import json
import logging
import os
import sys
import threading
import time
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "common"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

import httpd  # noqa: E402
import mqttio  # noqa: E402
import namespace as NS  # noqa: E402
import store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("ch-viewer")

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8122"))
LINKS = {"hub": os.environ.get("PUBLIC_HUB_URL", "http://localhost:8120")}

WAVE_PATHS = {w["path"] for w in NS.ch_waveforms()}


class Asset:
    def __init__(self, serial):
        self.serial = serial
        self.nameplate = None
        self.status = None
        self.active = []
        self.events = deque(maxlen=300)
        self.waves = {}
        self.units = {}
        self.seq_last = None
        self.seq_gaps = 0
        self.msgs = deque()          # (t, bytes) of the last 60 s
        self.total = 0


class Viewer:
    def __init__(self):
        self.store = store.TagStore(stale_s=5.0)
        self.assets = {}
        self.lock = threading.Lock()
        self.client = mqttio.make_client("ch-viewer", MQTT_HOST, MQTT_PORT, subscriptions=[NS.CH_PREFIX + "/#"],
                                         on_message=self.on_message)

    def asset(self, serial):
        a = self.assets.get(serial)
        if a is None:
            a = self.assets[serial] = Asset(serial)
        return a

    def on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        # v1.0/CH/Fleet/<Customer>/<Site>/<Serial>/<path...>
        if len(parts) < 7:
            return
        serial, path = parts[5], "/".join(parts[6:])
        now = time.time()
        with self.lock:
            a = self.asset(serial)
            a.msgs.append((now, len(msg.payload) + len(msg.topic)))
            a.total += 1
            while a.msgs and now - a.msgs[0][0] > 60:
                a.msgs.popleft()
            if path == NS.META_STATUS:
                a.status = msg.payload.decode(errors="replace")
                return
            try:
                p = json.loads(msg.payload)
            except ValueError:
                return
            if not isinstance(p, dict):
                return
            seq = p.get("seq")
            if isinstance(seq, int) and not msg.retain:
                if a.seq_last is not None and seq > a.seq_last + 1:
                    a.seq_gaps += seq - a.seq_last - 1
                if a.seq_last is None or seq > a.seq_last:
                    a.seq_last = seq
            if path == NS.META_NAMEPLATE:
                a.nameplate = p
            elif path == NS.EVENTS_ALARM:
                a.events.appendleft(p)
            elif path == "Events/ActiveAlarms":
                a.active = p.get("value") or []
            elif path in WAVE_PATHS:
                a.waves[path] = p
            else:
                a.units[path] = p.get("unit")
                self.store.update(f"{serial}/{path}", p.get("value"), p.get("timestamp"), p.get("quality"))

    def summary(self):
        with self.lock:
            out = {}
            for s, a in sorted(self.assets.items()):
                rate = sum(b for _, b in a.msgs) / 60.0
                out[s] = {"nameplate": a.nameplate, "status": a.status, "active_alarms": a.active,
                          "messages": a.total, "kbytes_per_s": round(rate / 1024, 2), "msgs_per_s": round(len(a.msgs) / 60, 1),
                          "seq": a.seq_last, "seq_gaps": a.seq_gaps,
                          "waveforms": {p: {"timestamp": w.get("timestamp"), "trigger": w.get("trigger"),
                                            "samples": w.get("samples")} for p, w in a.waves.items()}}
            return out


def build_app(v):
    app = httpd.App()
    app.static("/", os.path.join(HERE, "web", "index.html"))

    @app.get("/api/assets")
    def assets(req):
        return {"timestamp": mqttio.iso(), "connected": v.client.is_connected(), "assets": v.summary(),
                "tags": NS.ch_tags(), "waveforms": NS.ch_waveforms(), "links": LINKS}

    @app.get("/api/asset/<serial>")
    def asset(req, serial):
        snap = v.store.snapshot()
        pre = serial + "/"
        with v.lock:
            a = v.assets.get(serial)
            if not a:
                return 404, {"error": "unknown asset"}
            units = dict(a.units)
            events = list(a.events)[:100]
        vals = {k[len(pre):]: {**e, "unit": units.get(k[len(pre):])} for k, e in snap.items() if k.startswith(pre)}
        return {"serial": serial, "values": vals, "events": events}

    @app.get("/api/waveform/<serial>")
    def wave(req, serial):
        with v.lock:
            a = v.assets.get(serial)
            w = a.waves.get(req.query.get("path", "")) if a else None
        if not w:
            return 404, {"error": "no block yet"}
        return w

    @app.get("/api/trend")
    def trend(req):
        serial = req.query.get("serial", "")
        paths = [p for p in req.query.get("paths", "").split(",") if p]
        r = v.store.trend([f"{serial}/{p}" for p in paths], float(req.query.get("minutes", 30)),
                          int(req.query.get("points", 300)))
        return {"t": r["t"], "series": {p: r["series"][f"{serial}/{p}"] for p in paths}}

    return app


def main():
    v = Viewer()
    v.store.start_sampler()
    build_app(v).serve(WEB_PORT, background=False)


if __name__ == "__main__":
    main()
