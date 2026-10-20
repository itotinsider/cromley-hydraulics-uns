"""CH turbine PLCs: one simulated CH PLC per turbine, publishing the CH asset tree.

Each PLC has its own thread, MQTT client and session (client id ch-plc-<serial>, last will on
_meta/Status), its own message counter (seq) and its own subscription to the context it copies
from the customer tree. It never publishes into the customer tree.

HTTP :8125 (compose network only; the instructor station and the dam simulator use it):
  GET  /api/hardwired                 element A of the dual-element sensors, per unit (the "copper")
  GET  /api/state                     per asset: values, active PLC alarms, publish statistics
  GET  /api/config                    assets, waveform settings
  GET  /api/scenarios                 machine-fault scenarios (instructor only)
  GET  /api/ground_truth              active scenarios and severities (instructor only)
  POST /api/scenarios/<id>/start      {"unit": "Unit1" | "serial": ..., "options": {...}}
  POST /api/scenarios/<id>/stop       {"unit": ...}
  POST /api/waveforms/<unit>          publish one set of waveform blocks now (trigger "manual")
"""

import itertools
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
import turbine as T  # noqa: E402
from model import SCENARIOS, Turbine  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("ch-plc")

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8125"))
PUBLISH_INTERVAL = float(os.environ.get("PUBLISH_INTERVAL_SECONDS", "1"))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(HERE, "data"))
COOLING_WATER_TEMP = float(os.environ.get("COOLING_WATER_TEMP_C", "14"))
DETAILED_TURBINES = int(os.environ.get("DETAILED_TURBINES", "3"))
RETAIN_PROCESS = mqttio.as_bool(os.environ.get("RETAIN_PROCESS_VALUES", "true"))


# Per waveform group: the namespace's defaults, overridden by WAVEFORM_<GROUP>_EVERY_S / _SECONDS.
WAVE_CFG = {}
for _w in NS.ch_waveforms():
    _g = _w["group"]
    WAVE_CFG[_g] = {"every_s": float(os.environ.get(f"WAVEFORM_{_g.upper()}_EVERY_S", _w["every_s"])),
                    "seconds": float(os.environ.get(f"WAVEFORM_{_g.upper()}_SECONDS", _w["seconds"]))}
ALARM_WAVE_HOLDOFF_S = 30.0
COUNTERS_FILE = os.path.join(DATA_DIR, "ch_plc_counters.json")


def nameplate(asset, detailed):
    serial = asset["serial"]
    return {
        "serial": serial,
        "manufacturer": "Cromley Hydraulics",
        "productLine": 'CH-Francis "Canyon"',
        "model": "CH-FR-V40-100",
        "type": "Vertical Francis turbine",
        "ratedPower_MW": T.RATED_MW, "ratedHead_m": T.RATED_HEAD_M, "ratedFlow_m3s": 45.0,
        "ratedSpeed_rpm": T.RATED_RPM, "runnerBlades": T.RUNNER_BLADES, "wicketGates": T.WICKET_GATES,
        "commissioned": asset["commissioned"], "plcRetrofit": 2026, "plcFirmware": "CH-PLC 2.4.1",
        "dataModel": NS.VERSION,
        "customer": {"id": NS.CUSTOMER_ID, "name": "Desert River Water & Power Authority", "site": NS.SITE_ID,
                     "unitName": asset["unit"].replace("Unit", "Unit "), "unitTag": asset["unit"]},
        "bearings": {"Thrust": "6 pads", "UGB": "4 pads", "LGB": "4 pads", "TGB": "4 pads"},
        "waveforms": [{"path": w["path"], "unit": w["unit"], "sampleRate": w["rate"],
                       "samples": int(WAVE_CFG[w["group"]]["seconds"] * w["rate"]),
                       "every_s": WAVE_CFG[w["group"]]["every_s"]} for w in NS.ch_waveforms()] if detailed else [],
    }


class PLC:
    """One CH PLC: a Turbine model, an MQTT session and a publish loop."""

    def __init__(self, asset, detailed, counters):
        self.asset = asset
        self.serial = asset["serial"]
        self.unit = asset["unit"]
        self.detailed = detailed
        self.lock = threading.Lock()
        self.turbine = Turbine(asset, now=time.time(), cw_temp=COOLING_WATER_TEMP, counters=counters)
        self.seq = 0
        self._seq = itertools.count(1)
        self.stats = {"messages": 0, "bytes": 0, "waveforms": 0, "events": 0, "since": time.time()}
        self.tags = {t["path"]: t for t in NS.ch_tags()}
        self.next_wave = {}
        now = time.time()
        off = self.turbine.wave_offset
        for w in NS.ch_waveforms():
            self.next_wave[w["path"]] = now + 5 + off + (0 if w["group"] != "accel" else 20)
        self.last_alarm_wave = 0.0
        self.ctx_topics = {}
        for ch_path, cust in {**NS.CH_CONTEXT, **NS.CH_CONTEXT_EXTRA}.items():
            self.ctx_topics[NS.customer_topic(cust.format(unit=self.unit))] = ch_path
        prefix = NS.ch_asset_prefix(self.serial)
        self.client = mqttio.make_client(
            f"ch-plc-{self.serial}", MQTT_HOST, MQTT_PORT, subscriptions=list(self.ctx_topics),
            on_message=self._on_message, will=(f"{prefix}/{NS.META_STATUS}", "OFFLINE"))
        self.client.on_connected_hook = self._on_connected

    def _on_connected(self, client):
        self.pub(NS.META_STATUS, "ONLINE", retain=True, qos=1)
        np = nameplate(self.asset, self.detailed)
        np["timestamp"] = mqttio.iso()
        self.pub(NS.META_NAMEPLATE, json.dumps(np, ensure_ascii=False), retain=True, qos=1)

    def _on_message(self, client, userdata, msg):
        path = self.ctx_topics.get(msg.topic)
        if not path:
            return
        v = mqttio.parse_value(msg.payload)
        with self.lock:
            self.turbine.set_context(path, v, time.time())

    def pub(self, path, payload, retain=False, qos=0):
        topic = NS.ch_topic(self.serial, path)
        self.client.publish(topic, payload, qos=qos, retain=retain)
        self.stats["messages"] += 1
        self.stats["bytes"] += len(topic) + len(payload.encode())

    def next_seq(self):
        # one counter per PLC over every message it sends; next() on a count is atomic
        self.seq = next(self._seq)
        return self.seq

    def tick(self, dt, now):
        with self.lock:
            self.turbine.step(dt, now)
            vals = dict(self.turbine.last)
            events = self.turbine.pop_events()
            active = self.turbine.active_alarms()
        for path, (v, q) in vals.items():
            spec = self.tags[path]
            self.pub(path, mqttio.ch_payload(mqttio.rounded(v, spec["dec"]), spec["unit"], self.next_seq(), q, now),
                     retain=RETAIN_PROCESS)
        vib_alarm = False
        for e in events:
            payload = {"timestamp": mqttio.iso(e["t"]), "seq": self.next_seq(), "serial": self.serial,
                       "alarmId": e["alarmId"], "state": e["state"], "severity": e["severity"], "tag": e["tag"],
                       "value": e["value"], "limit": e["limit"], "text": e["text"]}
            self.pub(NS.EVENTS_ALARM, json.dumps(payload, ensure_ascii=False), qos=1)
            self.stats["events"] += 1
            vib_alarm |= e["vibration"] and e["state"] == "ACTIVE"
        if events:
            self.pub("Events/ActiveAlarms", json.dumps({"timestamp": mqttio.iso(now), "seq": self.next_seq(),
                                                        "value": active}), retain=True, qos=1)
        if not self.detailed:
            return
        if vib_alarm and now - self.last_alarm_wave >= ALARM_WAVE_HOLDOFF_S:
            self.last_alarm_wave = now
            self.publish_waveforms(now, "alarm")
        for w in NS.ch_waveforms():
            if now >= self.next_wave[w["path"]]:
                self.next_wave[w["path"]] = now + WAVE_CFG[w["group"]]["every_s"]
                self.publish_waveform(w, now, "periodic")

    def publish_waveform(self, w, now, trigger):
        cfg = WAVE_CFG[w["group"]]
        with self.lock:
            block = self.turbine.waveform(w, now, trigger, seconds=cfg["seconds"])
        block["timestamp"] = mqttio.iso(now)
        block = {"timestamp": block.pop("timestamp"), "seq": self.next_seq(), **block}
        self.pub(w["path"], json.dumps(block, separators=(", ", ": ")), qos=0)
        self.stats["waveforms"] += 1

    def publish_waveforms(self, now, trigger):
        for w in NS.ch_waveforms():
            self.publish_waveform(w, now, trigger)

    def state(self):
        with self.lock:
            vals = {k: {"value": mqttio.rounded(v, self.tags[k]["dec"]), "quality": q}
                    for k, (v, q) in self.turbine.last.items()}
            active = self.turbine.active_alarms()
        el = max(1.0, time.time() - self.stats["since"])
        return {"serial": self.serial, "unit": self.unit, "detailed": self.detailed, "seq": self.seq,
                "connected": self.client.is_connected(), "values": vals, "active_alarms": active,
                "stats": {**self.stats, "kbytes_per_s": round(self.stats["bytes"] / el / 1024, 2)}}


def load_counters():
    try:
        with open(COUNTERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_counters(plcs):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = COUNTERS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({p.serial: p.turbine.counters for p in plcs.values()}, f, indent=1)
        os.replace(tmp, COUNTERS_FILE)
    except OSError as e:
        log.warning("could not save counters: %s", e)


def build_app(plcs):
    app = httpd.App()

    def find(body):
        key = body.get("unit") or body.get("serial") or NS.UNITS[0]
        for p in plcs.values():
            if key in (p.unit, p.serial):
                return p
        return None

    @app.get("/api/hardwired")
    def hardwired(req):
        out = {}
        for p in plcs.values():
            with p.lock:
                out[p.unit] = p.turbine.hardwired()
        return {"timestamp": mqttio.iso(), "units": out}

    @app.get("/api/state")
    def state(req):
        return {"timestamp": mqttio.iso(), "assets": {s: p.state() for s, p in plcs.items()}}

    @app.get("/api/config")
    def config(req):
        return {"assets": [dict(a) for a in NS.ASSETS], "detailed": [p.serial for p in plcs.values() if p.detailed],
                "waveforms": WAVE_CFG, "publish_interval_s": PUBLISH_INTERVAL, "retain_process": RETAIN_PROCESS}

    @app.get("/api/scenarios")
    def scenarios(req):
        return {"scenarios": SCENARIOS}

    @app.get("/api/ground_truth")
    def truth(req):
        out = {}
        for p in plcs.values():
            with p.lock:
                out[p.unit] = {"serial": p.serial, **p.turbine.ground_truth(),
                               "plc_alarms": p.turbine.active_alarms()}
        return {"units": out}

    @app.post("/api/scenarios/<sid>/start")
    def start(req, sid):
        p = find(req.body)
        if not p:
            return 404, {"error": "unknown unit"}
        if sid not in SCENARIOS:
            return 404, {"error": f"unknown scenario {sid}"}
        try:
            with p.lock:
                p.turbine.start_scenario(sid, req.body.get("options"))
        except ValueError as e:
            return 409, {"error": str(e)}
        log.info("scenario %s started on %s", sid, p.unit)
        return {"ok": True, "unit": p.unit, "scenario": sid}

    @app.post("/api/scenarios/<sid>/stop")
    def stop(req, sid):
        p = find(req.body)
        if not p:
            return 404, {"error": "unknown unit"}
        with p.lock:
            p.turbine.stop_scenario(sid)
        return {"ok": True, "unit": p.unit, "scenario": sid}

    @app.post("/api/waveforms/<unit>")
    def waves(req, unit):
        p = find({"unit": unit})
        if not p or not p.detailed:
            return 404, {"error": "unknown or not detailed unit"}
        p.publish_waveforms(time.time(), "manual")
        return {"ok": True}

    return app


def main():
    saved = load_counters()
    plcs = {}
    for i, a in enumerate(NS.ASSETS):
        plcs[a["serial"]] = PLC(a, i < DETAILED_TURBINES, saved.get(a["serial"]))
    build_app(plcs).serve(WEB_PORT)
    log.info("CH PLCs %s, HTTP :%d, broker %s:%d", ", ".join(plcs), WEB_PORT, MQTT_HOST, MQTT_PORT)

    def run(p):
        last = time.time()
        nxt = last
        while True:
            nxt += PUBLISH_INTERVAL
            time.sleep(max(0.0, nxt - time.time()))
            now = time.time()
            try:
                p.tick(now - last, now)
            except Exception:  # noqa: BLE001 - one bad tick must not kill the PLC
                log.exception("tick %s", p.serial)
            last = now

    for p in plcs.values():
        threading.Thread(target=run, args=(p,), daemon=True, name=p.serial).start()
    while True:
        time.sleep(60)
        save_counters(plcs)


if __name__ == "__main__":
    main()
