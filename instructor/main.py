"""Instructor station: hidden fault scenarios for the dam simulator and the CH PLC simulator.

It talks to both simulators directly over HTTP on the compose network, never through the broker:
nothing it does is published, the learners and vendors only see the effects in the data.

HTTP :8121 (host):
  GET  /api/scenarios                  every scenario, dam and CH, with its letter (A-H) and target
  GET  /api/ground_truth               what the simulators know and the data doesn't say
  GET  /api/overview                   a few live values per unit (from the simulators, for orientation)
  POST /api/scenarios/<id>/start       {"unit": "Unit1", "options": {...}}
  POST /api/scenarios/<id>/stop        {"unit": "Unit1"}
  POST /api/reset                      stop every scenario on every unit ("repair everything")
"""

import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "common"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

import httpd  # noqa: E402
import namespace as NS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("instructor")

WEB_PORT = int(os.environ.get("WEB_PORT", "8121"))
DAM_URL = os.environ.get("DAM_URL", "http://dam-sim:8123")
CH_URL = os.environ.get("CH_URL", "http://ch-plc-sim:8125")
LINKS = {"hub": os.environ.get("PUBLIC_HUB_URL", "http://localhost:8120")}

OVERVIEW_DAM = ("State", "MW", "MWSetpoint", "GatePosition", "Flow", "NetHead", "ActiveAlarms")
OVERVIEW_CH = ("Bearings/TGB/PadTemp01", "Bearings/TGB/PadTemp02", "Bearings/TGB/PadTemp03", "Bearings/Thrust/PadTemp01",
               "Cooling/WaterFlow_GB", "Governor/HPU/AccumulatorPressure", "Governor/HPU/PumpStartsPerHour",
               "Vibration/UGB/ShaftX/Overall_um_pp", "Vibration/TGB/ShaftX/Overall_um_pp",
               "Vibration/Headcover/Vel_mm_s_rms", "Turbine/ShearPinStatus")


def scenarios():
    out = []
    st, dam = httpd.http_json(f"{DAM_URL}/api/scenarios")
    for sid, s in ((dam or {}).get("scenarios") or {}).items():
        out.append({"id": sid, "source": "dam", **s})
    st2, ch = httpd.http_json(f"{CH_URL}/api/scenarios")
    for sid, s in ((ch or {}).get("scenarios") or {}).items():
        out.append({"id": sid, "source": "ch", "target": "unit", **s})
    out.sort(key=lambda s: (s.get("letter") is None, s.get("letter") or "", s.get("group", ""), s["label"]))
    return out, {"dam": st == 200, "ch": st2 == 200}


def build_app():
    app = httpd.App()
    app.static("/", os.path.join(HERE, "web", "index.html"))

    @app.get("/api/scenarios")
    def list_scenarios(req):
        sc, ok = scenarios()
        return {"scenarios": sc, "reachable": ok, "units": list(NS.UNITS), "links": LINKS,
                "serials": dict(NS.SERIAL_BY_UNIT)}

    @app.get("/api/ground_truth")
    def truth(req):
        _, dam = httpd.http_json(f"{DAM_URL}/api/ground_truth")
        _, ch = httpd.http_json(f"{CH_URL}/api/ground_truth")
        return {"dam": dam, "ch": ch}

    @app.get("/api/overview")
    def overview(req):
        _, dam = httpd.http_json(f"{DAM_URL}/api/state")
        _, ch = httpd.http_json(f"{CH_URL}/api/state")
        dv = (dam or {}).get("values", {})
        out = {"plant": {k: dv.get(k) for k in ("Reservoir/Level", "Plant/GrossHead", "Plant/TotalMW",
                                                 "Plant/MWSetpoint", "River/Flow", "River/TailwaterLevel")},
               "units": {}}
        assets = (ch or {}).get("assets", {})
        for u in NS.UNITS:
            row = {k: dv.get(f"Powerhouse/{u}/{k}") for k in OVERVIEW_DAM}
            a = assets.get(NS.SERIAL_BY_UNIT[u], {})
            vals = a.get("values", {})
            row["ch"] = {k: (vals.get(k) or {}).get("value") for k in OVERVIEW_CH}
            row["ch_alarms"] = a.get("active_alarms", [])
            row["serial"] = NS.SERIAL_BY_UNIT[u]
            out["units"][u] = row
        return out

    def _target(sid):
        sc, _ = scenarios()
        return next((s for s in sc if s["id"] == sid), None)

    @app.post("/api/scenarios/<sid>/start")
    def start(req, sid):
        s = _target(sid)
        if not s:
            return 404, {"error": f"unknown scenario {sid}"}
        base = DAM_URL if s["source"] == "dam" else CH_URL
        st, body = httpd.http_json(f"{base}/api/scenarios/{sid}/start", "POST",
                                   {"unit": req.body.get("unit"), "options": req.body.get("options") or {}})
        log.info("start %s %s -> %s", sid, req.body.get("unit"), st)
        return st, body

    @app.post("/api/scenarios/<sid>/stop")
    def stop(req, sid):
        s = _target(sid)
        if not s:
            return 404, {"error": f"unknown scenario {sid}"}
        base = DAM_URL if s["source"] == "dam" else CH_URL
        return httpd.http_json(f"{base}/api/scenarios/{sid}/stop", "POST", {"unit": req.body.get("unit")})

    @app.post("/api/reset")
    def reset(req):
        sc, _ = scenarios()
        n = 0
        for s in sc:
            base = DAM_URL if s["source"] == "dam" else CH_URL
            units = NS.UNITS if s["source"] == "ch" else (None,)
            for u in units:
                st, _ = httpd.http_json(f"{base}/api/scenarios/{s['id']}/stop", "POST", {"unit": u})
                n += st == 200
        return {"ok": True, "stopped_calls": n}

    return app


def main():
    log.info("instructor station :%d (dam %s, ch %s)", WEB_PORT, DAM_URL, CH_URL)
    build_app().serve(WEB_PORT, background=False)


if __name__ == "__main__":
    main()
