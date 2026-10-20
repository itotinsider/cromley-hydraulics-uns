"""Dam simulator runtime: real-time loop, the customer tree on MQTT, commands, hardwired I/O.

- Physics at STEP_SECONDS (0.1 s), the customer tree published every PUBLISH_INTERVAL_SECONDS
  (1 s, retained) and Plant/Events as they happen (not retained).
- Subscribes v1.0/DRWPA/CopperCanyon/+/Cmd/# and .../+/+/Cmd/#: the dam SCADA and the simulated
  grid operator. A command's result shows up on the measured topics.
- Polls the CH PLC simulator's /api/hardwired every second: element A of the dual-element sensors,
  the copper between the turbine and the customer's unit controller (not MQTT).

HTTP :8123 (compose network only; the instructor station uses it):
  GET  /api/state                  customer tree values, unit internals
  GET  /api/scenarios              dam scenarios (instructor only)
  GET  /api/ground_truth           instructor only
  POST /api/scenarios/<id>/start   {"unit": "Unit2", "options": {}}
  POST /api/scenarios/<id>/stop
  POST /api/command                {"path": "Powerhouse/Unit1/Cmd/Start", "value": true}  (tests, like an MQTT command)
"""

import json
import logging
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "common"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

import httpd  # noqa: E402
import mqttio  # noqa: E402
import namespace as NS  # noqa: E402
from model import SCENARIOS, Dam  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("dam-sim")

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8123"))
STEP = float(os.environ.get("STEP_SECONDS", "0.1"))
PUBLISH_INTERVAL = float(os.environ.get("PUBLISH_INTERVAL_SECONDS", "1"))
HARDWIRED_URL = os.environ.get("HARDWIRED_URL", "http://ch-plc-sim:8125/api/hardwired")
START_LEVEL = float(os.environ.get("START_LEVEL_M", "412"))
INFLOW = float(os.environ.get("INFLOW_M3S", "115"))
PLANT_SP = float(os.environ.get("PLANT_MW_SETPOINT", "110"))
AGC = mqttio.as_bool(os.environ.get("AGC_ENABLED", "true"))
SEED = int(os.environ.get("SEED", "1"))

TAGS = {t["path"]: t for t in NS.customer_tags()}
CMDS = {c["path"] for c in NS.customer_commands()}


class Runtime:
    def __init__(self):
        self.lock = threading.Lock()
        self.dam = Dam(seed=SEED, start_level=START_LEVEL, inflow_base=INFLOW, plant_sp=PLANT_SP, agc=AGC,
                       now=time.time())
        self.hw_ok = False
        self.stats = {"messages": 0, "bytes": 0, "commands": 0, "since": time.time()}
        self.client = mqttio.make_client(
            "dam-sim", MQTT_HOST, MQTT_PORT,
            subscriptions=[NS.customer_topic("+/Cmd/#"), NS.customer_topic("+/+/Cmd/#")],
            on_message=self.on_message)

    def on_message(self, client, userdata, msg):
        prefix = NS.CUSTOMER_PREFIX + "/"
        if not msg.topic.startswith(prefix):
            return
        path = msg.topic[len(prefix):]
        if path not in CMDS:
            with self.lock:
                self.dam._refuse("Plant", f"Unknown command topic {path}")
            return
        self.command(path, mqttio.parse_value(msg.payload))

    def command(self, path, value):
        with self.lock:
            self.stats["commands"] += 1
            return self.dam.command(path, value)

    def poll_hardwired(self):
        while True:
            st, body = httpd.http_json(HARDWIRED_URL, timeout=0.8) if HARDWIRED_URL else (None, None)
            now = time.time()
            if st == 200 and body and "units" in body:
                with self.lock:
                    for unit, vals in body.get("units", {}).items():
                        if unit in self.dam.units:
                            self.dam.set_hardwired(unit, vals, now)
                if not self.hw_ok:
                    log.info("hardwired I/O from the CH turbines OK")
                self.hw_ok = True
            elif self.hw_ok:
                log.warning("hardwired I/O lost (%s)", st)
                self.hw_ok = False
            time.sleep(1.0)

    def publish(self, now):
        with self.lock:
            vals = self.dam.values()
            events, self.dam.events = self.dam.events, []
        for path, v in vals.items():
            spec = TAGS[path]
            payload = mqttio.customer_payload(mqttio.rounded(v, spec["dec"]), spec["unit"], now)
            topic = NS.customer_topic(path)
            self.client.publish(topic, payload, qos=0, retain=True)
            self.stats["messages"] += 1
            self.stats["bytes"] += len(topic) + len(payload.encode())
        for e in events:
            payload = json.dumps({"timestamp": mqttio.iso(e["t"]), "source": e["source"], "kind": e["kind"],
                                  "text": e["text"]}, ensure_ascii=False)
            self.client.publish(NS.customer_topic(NS.EVENTS_TOPIC), payload, qos=1, retain=False)
            self.stats["messages"] += 1

    def run(self):
        last = time.time()
        next_pub = last
        nxt = last
        while True:
            nxt += STEP
            time.sleep(max(0.0, nxt - time.time()))
            now = time.time()
            dt = min(1.0, now - last)
            last = now
            with self.lock:
                try:
                    self.dam.step(dt, now)
                except Exception:  # noqa: BLE001 - keep the plant running
                    log.exception("step")
            if now >= next_pub:
                next_pub += PUBLISH_INTERVAL
                if next_pub < now:
                    next_pub = now + PUBLISH_INTERVAL
                self.publish(now)


def build_app(rt):
    app = httpd.App()

    @app.get("/api/state")
    def state(req):
        with rt.lock:
            d = rt.dam
            vals = d.values()
            units = {n: {"state": u.state, "substep": u.substep, "speed_pu": round(u.speed, 4), "gate": round(u.gate, 4),
                         "mw": round(u.mw, 2), "mw_sp": round(u.mw_sp, 2), "trip_cause": u.trip_cause,
                         "hardwired": u.hw, "hardwired_ok": d.hw_ok(u)} for n, u in d.units.items()}
        return {"timestamp": mqttio.iso(), "values": {k: mqttio.rounded(v, TAGS[k]["dec"]) for k, v in vals.items()},
                "units": units, "connected": rt.client.is_connected(), "hardwired_ok": rt.hw_ok,
                "stats": dict(rt.stats)}

    @app.get("/api/scenarios")
    def scenarios(req):
        return {"scenarios": SCENARIOS}

    @app.get("/api/ground_truth")
    def truth(req):
        with rt.lock:
            return rt.dam.ground_truth()

    @app.post("/api/scenarios/<sid>/start")
    def start(req, sid):
        if sid not in SCENARIOS:
            return 404, {"error": f"unknown scenario {sid}"}
        unit = req.body.get("unit")
        if unit and unit not in NS.UNITS:
            return 404, {"error": "unknown unit"}
        try:
            with rt.lock:
                rt.dam.start_scenario(sid, unit, req.body.get("options"))
        except ValueError as e:
            return 409, {"error": str(e)}
        log.info("scenario %s started", sid)
        return {"ok": True, "scenario": sid}

    @app.post("/api/scenarios/<sid>/stop")
    def stop(req, sid):
        with rt.lock:
            rt.dam.stop_scenario(sid)
        return {"ok": True, "scenario": sid}

    @app.post("/api/command")
    def command(req):
        path = req.body.get("path", "")
        if path not in CMDS:
            return 404, {"error": f"unknown command {path}"}
        ok, msg = rt.command(path, req.body.get("value"))
        return (200 if ok else 409), {"ok": ok, "message": msg}

    return app


def main():
    rt = Runtime()
    build_app(rt).serve(WEB_PORT)
    threading.Thread(target=rt.poll_hardwired, daemon=True, name="hardwired").start()
    log.info("dam simulator: HTTP :%d, broker %s:%d, hardwired %s", WEB_PORT, MQTT_HOST, MQTT_PORT, HARDWIRED_URL)
    rt.run()


if __name__ == "__main__":
    main()
