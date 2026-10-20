"""Dam SCADA server: the customer's supervisory system for Copper Canyon Dam, over MQTT only.

Subscribes the customer tree (v1.0/DRWPA/CopperCanyon/#), keeps the latest values, an in-memory
trend store, its own alarm engine (ISA-18.2-style: active/acknowledged/return to normal) and an
event journal; operator commands are published to the Cmd topics. It never reads the CH tree:
that is the machine builder's data.

HTTP :8120 (host): the hub (/), the SCADA HMI (/scada) and its API:
  GET  /api/state                 values (with age), alarms, recent events
  GET  /api/config                tags, commands, alarm limits, operating zones, links
  GET  /api/trend?paths=a,b&minutes=60&points=300
  GET  /api/events?limit=200
  POST /api/cmd                   {"path": "Powerhouse/Unit1/Cmd/Start", "value": true}
  POST /api/alarms/ack            {"id": "..."} or {"all": true}
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
import turbine as T  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("dam-scada")

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8120"))
STALE_S = float(os.environ.get("STALE_SECONDS", "5"))

LINKS = {
    "instructor": os.environ.get("PUBLIC_INSTRUCTOR_URL", "http://localhost:8121"),
    "viewer": os.environ.get("PUBLIC_VIEWER_URL", "http://localhost:8122"),
    "nodered": os.environ.get("PUBLIC_NODERED_URL", "http://localhost:1881"),
    "mqtt_explorer": os.environ.get("PUBLIC_MQTT_EXPLORER_URL", "http://localhost:4001"),
    "broker": os.environ.get("PUBLIC_BROKER", "localhost:1884"),
    "wiki": os.environ.get("PUBLIC_WIKI_URL", "https://github.com/itotinsider/cromley-hydraulics-uns/wiki"),
}

TAGS = {t["path"]: t for t in NS.customer_tags()}
CMDS = {c["path"]: c for c in NS.customer_commands()}

# ------------------------------------------------------------------ alarm configuration
# (id, path, op, limit, priority, text, delay_s, unit-running-only). Priorities: 1 high, 2 medium, 3 low.
ALARMS = [
    ("RES_LEVEL_HH", "Reservoir/Level", ">", 420.5, 1, "Reservoir level very high (above the operating range)", 0, False),
    ("RES_LEVEL_H", "Reservoir/Level", ">", 419.0, 2, "Reservoir level high: spillway in operation", 0, False),
    ("RES_LEVEL_L", "Reservoir/Level", "<", 387.0, 2, "Reservoir level low", 0, False),
    ("RES_LEVEL_LL", "Reservoir/Level", "<", 385.0, 1, "Reservoir level below the operating range", 0, False),
    ("RIVER_FLOW_L", "River/Flow", "<", 10.0, 1, "River flow below the 10 m³/s minimum", 30, False),
    ("TRASH_DP_H", "Intake/TrashRackDP", ">", 0.5, 3, "Trash rack differential pressure high", 10, False),
    ("TRASH_DP_HH", "Intake/TrashRackDP", ">", 0.8, 2, "Trash rack differential pressure very high", 10, False),
    ("GRID_FREQ_H", "Plant/GridFrequency", ">", 50.2, 2, "Grid frequency high", 5, False),
    ("GRID_FREQ_L", "Plant/GridFrequency", "<", 49.8, 2, "Grid frequency low", 5, False),
    ("PLANT_SP_UNREACHABLE", "Plant/MWSetpointReachable", "==", False, 3, "Plant MW setpoint not reachable with the online units", 60, False),
    ("PENSTOCK_P_H", "Penstock/Pressure", ">", 12.5, 2, "Penstock pressure high (water hammer)", 0, False),
]
for _u in NS.UNITS:
    _p = f"Powerhouse/{_u}"
    for _k, _txt in (("ThrustBearingTemp", "thrust bearing"), ("UpperGuideBearingTemp", "upper guide bearing"),
                     ("LowerGuideBearingTemp", "lower guide bearing"), ("TurbineGuideBearingTemp", "turbine guide bearing")):
        ALARMS.append((f"{_u.upper()}_{_k.upper()}_H", f"{_p}/{_k}", ">", 75.0, 3, f"{_u} {_txt} temperature high", 5, False))
    ALARMS.append((f"{_u.upper()}_GOV_OIL_L", f"{_p}/GovernorOilPressure", "<", 54.0, 3, f"{_u} governor oil pressure low", 5, False))

# unit controller codes (Powerhouse/<unit>/ActiveAlarms) → priority, text
UNIT_CODES = {
    "TRIP_OVERSPEED": (1, "TRIP overspeed"),
    "TRIP_BEARING_TEMP": (1, "TRIP bearing temperature"),
    "TRIP_GOV_OIL_PRESSURE": (1, "TRIP governor oil pressure low-low"),
    "TRIP_EMERGENCY_STOP": (1, "TRIP emergency stop"),
    "TRIP_GENERATOR_PROTECTION": (1, "TRIP generator protection"),
    "BEARING_TEMP_HIGH": (2, "Bearing temperature high (unit controller)"),
    "COOLING_WATER_FLOW_LOW": (2, "Cooling water flow low"),
    "GOV_OIL_PRESSURE_LOW": (2, "Governor oil pressure low"),
    "HARDWIRED_IO_FAULT": (2, "No signals from the turbine (hardwired I/O)"),
}


def _ops(op, v, limit, was):
    if op == "==":
        return v == limit
    band = abs(limit) * 0.002 if isinstance(limit, (int, float)) else 0
    if op == ">":
        return v > (limit - band if was else limit)
    return v < (limit + band if was else limit)


def _source(aid):
    """Journal source of an alarm: the unit for UNIT1_… ids, otherwise the SCADA itself."""
    for u in NS.UNITS:
        if aid.startswith(u.upper() + "_"):
            return u
    return "SCADA"


class Alarms:
    """State per alarm id: active, acked, since, last change. An alarm stays listed until it has
    cleared AND been acknowledged (ISA-18.2: unacknowledged return to normal)."""

    def __init__(self, journal):
        self.items = {}
        self.pending = {}     # id -> first time the condition was true (on-delay)
        self.journal = journal

    def set(self, aid, active, prio, text, now, value=None, delay=0):
        a = self.items.get(aid)
        if active:
            if (not a or not a["active"]) and delay:
                first = self.pending.setdefault(aid, now)
                if now - first < delay:
                    return
            self.pending.pop(aid, None)
            if not a or not a["active"]:
                self.items[aid] = {"id": aid, "priority": prio, "text": text, "active": True,
                                   "acked": False, "since": now, "value": value}
                self.journal("alarm", f"ALARM P{prio} {text}", _source(aid))
            else:
                a["value"] = value
        else:
            self.pending.pop(aid, None)
            if a and a["active"]:
                a["active"] = False
                a["cleared"] = now
                self.journal("rtn", f"RTN {text}", _source(aid))
                if a["acked"]:
                    del self.items[aid]

    def ack(self, aid=None):
        n = 0
        for k in list(self.items):
            if aid in (None, k):
                a = self.items[k]
                if not a["acked"]:
                    a["acked"] = True
                    n += 1
                if not a["active"]:
                    del self.items[k]
        return n

    def listing(self):
        return sorted(self.items.values(), key=lambda a: (a["priority"], -a["since"]))


class Scada:
    def __init__(self):
        self.store = store.TagStore(stale_s=STALE_S)
        self.events = deque(maxlen=2000)
        self.lock = threading.Lock()
        self.alarms = Alarms(self.journal)
        self.stats = {"messages": 0, "bytes": 0, "commands": 0}
        self.client = mqttio.make_client("dam-scada", MQTT_HOST, MQTT_PORT,
                                         subscriptions=[NS.CUSTOMER_PREFIX + "/#"], on_message=self.on_message)

    def journal(self, kind, text, source="SCADA"):
        self.events.appendleft({"t": time.time(), "timestamp": mqttio.iso(), "kind": kind, "source": source,
                                "text": text})

    def on_message(self, client, userdata, msg):
        prefix = NS.CUSTOMER_PREFIX + "/"
        if not msg.topic.startswith(prefix):
            return
        path = msg.topic[len(prefix):]
        self.stats["messages"] += 1
        self.stats["bytes"] += len(msg.payload)
        if "/Cmd/" in path:
            return
        if path == NS.EVENTS_TOPIC:
            try:
                e = json.loads(msg.payload)
            except ValueError:
                return
            self.events.appendleft({"t": time.time(), "timestamp": e.get("timestamp"), "kind": e.get("kind", "info"),
                                    "source": e.get("source", "Plant"), "text": e.get("text", "")})
            return
        try:
            p = json.loads(msg.payload)
        except ValueError:
            return
        if isinstance(p, dict):
            self.store.update(path, p.get("value"), p.get("timestamp"))

    def evaluate(self):
        now = time.time()
        with self.lock:
            for aid, path, op, limit, prio, text, delay, _ in ALARMS:
                v = self.store.get(path)
                age = self.store.age(path)
                if v is None or age is None or age > STALE_S:
                    continue
                was = self.alarms.items.get(aid, {}).get("active", False)
                self.alarms.set(aid, _ops(op, v, limit, was), prio, text, now, v, delay)
            for u in NS.UNITS:
                codes = self.store.get(f"Powerhouse/{u}/ActiveAlarms") or []
                for code, (prio, text) in UNIT_CODES.items():
                    self.alarms.set(f"{u.upper()}_{code}", code in codes, prio, f"{u} {text}", now)
            ages = [self.store.age(p) for p in ("Reservoir/Level", "Plant/TotalMW")]
            stale = any(a is None or a > STALE_S for a in ages)
            self.alarms.set("COMM_DAM", stale, 1, "No data from the dam (MQTT): values stale", now)

    def loop(self):
        while True:
            time.sleep(1.0)
            try:
                self.evaluate()
            except Exception:  # noqa: BLE001
                log.exception("alarm evaluation")

    def command(self, path, value, source="SCADA operator"):
        if path not in CMDS:
            return False, f"unknown command {path}"
        payload = json.dumps({"value": value, "source": source, "timestamp": mqttio.iso()})
        info = self.client.publish(NS.customer_topic(path), payload, qos=1, retain=False)
        self.stats["commands"] += 1
        self.journal("operator", f"Operator: {path.replace('/Cmd/', ' → ')} = {value}", "SCADA")
        return info.rc == 0, "sent"


def zones():
    """Operating zones per head (for the unit MW bars): rough zone and max MW at 70-120 m."""
    return [{"head": h, "rough_lo": round(T.rough_zone_mw(h)[0], 2), "rough_hi": round(T.rough_zone_mw(h)[1], 2),
             "max": round(T.max_mw(h), 2)} for h in range(70, 125, 5)]


def build_app(sc):
    app = httpd.App()
    web = os.path.join(HERE, "web")
    app.static("/", os.path.join(web, "index.html"))
    app.static("/scada", os.path.join(web, "scada.html"))

    @app.get("/api/state")
    def state(req):
        with sc.lock:
            alarms = sc.alarms.listing()
        return {"timestamp": mqttio.iso(), "server_time": time.time(), "connected": sc.client.is_connected(),
                "values": sc.store.snapshot(), "alarms": alarms, "events": list(sc.events)[:40],
                "stats": dict(sc.stats)}

    @app.get("/api/config")
    def config(req):
        return {"prefix": NS.CUSTOMER_PREFIX, "units": list(NS.UNITS), "tags": NS.customer_tags(),
                "commands": NS.customer_commands(), "unit_states": list(NS.UNIT_STATES),
                "alarms": [{"id": a[0], "path": a[1], "op": a[2], "limit": a[3], "priority": a[4], "text": a[5]}
                           for a in ALARMS],
                "unit_codes": {k: {"priority": p, "text": t} for k, (p, t) in UNIT_CODES.items()},
                "zones": zones(), "rated_mw": T.RATED_MW, "rated_rpm": T.RATED_RPM, "links": LINKS,
                "stale_s": STALE_S}

    @app.get("/api/trend")
    def trend(req):
        paths = [p for p in req.query.get("paths", "").split(",") if p]
        return sc.store.trend(paths, float(req.query.get("minutes", 60)), int(req.query.get("points", 300)))

    @app.get("/api/events")
    def events(req):
        return {"events": list(sc.events)[:int(req.query.get("limit", 200))]}

    @app.post("/api/cmd")
    def cmd(req):
        path = req.body.get("path", "")
        if path not in CMDS:
            return 404, {"ok": False, "error": f"unknown command {path}"}
        ok, msg = sc.command(path, req.body.get("value"))
        return (200 if ok else 503), {"ok": ok, "message": msg}

    @app.post("/api/alarms/ack")
    def ack(req):
        with sc.lock:
            n = sc.alarms.ack(None if req.body.get("all") else req.body.get("id"))
        return {"ok": True, "acked": n}

    return app


def main():
    sc = Scada()
    sc.store.start_sampler()
    threading.Thread(target=sc.loop, daemon=True, name="alarms").start()
    build_app(sc).serve(WEB_PORT, background=False)


if __name__ == "__main__":
    main()
