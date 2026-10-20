"""End to end: Mosquitto and the real service programs as processes, checked from the outside
(MQTT and HTTP) against the committed inventory. Free ports, temp data dir; the running stack is
not touched. Needs the tests image (it has mosquitto and paho-mqtt).
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

import pytest

import httpd
import namespace as NS
from conftest import ROOT

pytestmark = pytest.mark.e2e


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_http(url, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        st, _ = httpd.http_json(url, timeout=1)
        if st == 200:
            return True
        time.sleep(0.2)
    return False


class Recorder:
    def __init__(self, port):
        import paho.mqtt.client as mqtt
        self.msgs = {}
        self.retained = {}
        self.lock = threading.Lock()
        self.c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="e2e-recorder")
        self.c.on_message = self.on_message
        self.c.connect("127.0.0.1", port)
        self.c.subscribe("v1.0/#")
        self.c.loop_start()

    def on_message(self, c, u, m):
        with self.lock:
            self.msgs.setdefault(m.topic, []).append(m.payload)
            if m.retain:
                self.retained[m.topic] = m.payload

    def last(self, topic):
        with self.lock:
            v = self.msgs.get(topic)
            return json.loads(v[-1]) if v else None

    def publish(self, topic, payload):
        self.c.publish(topic, payload, qos=1).wait_for_publish(2)


@pytest.fixture(scope="module")
def stack():
    if not shutil.which("mosquitto"):
        pytest.skip("mosquitto not installed (run in the tests image)")
    tmp = tempfile.mkdtemp()
    ports = {k: free_port() for k in ("mqtt", "dam", "ch", "scada", "viewer", "instructor")}
    conf = os.path.join(tmp, "mosquitto.conf")
    with open(conf, "w") as f:
        f.write(f"listener {ports['mqtt']} 127.0.0.1\nallow_anonymous true\npersistence false\n")
    procs = {"mosquitto": subprocess.Popen(["mosquitto", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)}
    time.sleep(0.5)
    base = {**os.environ, "MQTT_HOST": "127.0.0.1", "MQTT_PORT": str(ports["mqtt"]), "PYTHONUNBUFFERED": "1",
            "DATA_DIR": tmp}
    env = {
        "chplc": {"WEB_PORT": str(ports["ch"]), "WAVEFORM_ACCEL_EVERY_S": "300"},
        "damsim": {"WEB_PORT": str(ports["dam"]), "HARDWIRED_URL": f"http://127.0.0.1:{ports['ch']}/api/hardwired"},
        "scada": {"WEB_PORT": str(ports["scada"])},
        "chviewer": {"WEB_PORT": str(ports["viewer"])},
        "instructor": {"WEB_PORT": str(ports["instructor"]), "DAM_URL": f"http://127.0.0.1:{ports['dam']}",
                       "CH_URL": f"http://127.0.0.1:{ports['ch']}"},
    }
    logs = {}
    for svc, e in env.items():
        logs[svc] = open(os.path.join(tmp, f"{svc}.log"), "w")
        procs[svc] = subprocess.Popen([sys.executable, "main.py"], cwd=os.path.join(ROOT, svc), env={**base, **e},
                                      stdout=logs[svc], stderr=subprocess.STDOUT)
    for svc, port in (("ch", ports["ch"]), ("dam", ports["dam"]), ("scada", ports["scada"]),
                      ("viewer", ports["viewer"]), ("instructor", ports["instructor"])):
        assert wait_http(f"http://127.0.0.1:{port}/api/" + {"ch": "config", "dam": "state", "scada": "config",
                                                             "viewer": "assets", "instructor": "scenarios"}[svc]), svc
    rec = Recorder(ports["mqtt"])
    time.sleep(7)
    yield {"ports": ports, "procs": procs, "rec": rec, "tmp": tmp}
    if os.environ.get("CH_E2E_LOGS"):
        for svc in env:
            print(f"----- {svc}\n" + open(os.path.join(tmp, f"{svc}.log")).read()[-3000:])
    for p in procs.values():
        p.send_signal(signal.SIGTERM)
    for p in procs.values():
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
    shutil.rmtree(tmp, ignore_errors=True)


def url(stack, svc, path):
    return f"http://127.0.0.1:{stack['ports'][svc]}{path}"


def test_customer_tree_on_the_broker(stack, inv):
    rec = stack["rec"]
    for path, spec in inv["customer"]["tags"].items():
        p = rec.last(NS.customer_topic(path))
        assert p is not None, f"no message on {path}"
        assert set(p) == {"value", "unit", "timestamp"}, path
        assert p["unit"] == spec["unit"], path
        assert p["timestamp"].endswith("Z")
        assert NS.customer_topic(path) in rec.retained or len(rec.msgs[NS.customer_topic(path)]) > 1


def test_ch_tree_on_the_broker(stack, inv):
    rec = stack["rec"]
    for serial in inv["ch"]["assets"]:
        seqs = []
        for path, spec in inv["ch"]["process"]["tags"].items():
            p = rec.last(NS.ch_topic(serial, path))
            assert p is not None, f"no message on {serial}/{path}"
            assert set(p) == {"value", "unit", "timestamp", "quality", "seq"}, path
            assert p["unit"] == spec["unit"] and p["quality"] in NS.QUALITIES, path
            seqs.append(p["seq"])
        assert len(set(seqs)) == len(seqs), "seq is unique per message"
        np = json.loads(rec.retained[NS.ch_topic(serial, NS.META_NAMEPLATE)])
        assert np["serial"] == serial and np["customer"]["unitTag"] == NS.UNIT_BY_SERIAL[serial]
        assert rec.retained[NS.ch_topic(serial, NS.META_STATUS)] == b"ONLINE"
        # context copied from the customer tree, GOOD while the feed is live
        ctx = rec.last(NS.ch_topic(serial, "Context/UnitState"))
        assert ctx["value"] == "Generating" and ctx["quality"] == "GOOD"


def test_nothing_else_on_the_broker(stack):
    topics = {line.split(",")[1] for line in open(os.path.join(ROOT, "inventory/topics.csv")).read().splitlines()[1:]}
    extra = set(stack["rec"].msgs) - topics
    assert not extra, f"published but not in the inventory: {sorted(extra)[:10]}"


def test_waveforms(stack, inv):
    rec = stack["rec"]
    st, _ = httpd.http_json(url(stack, "ch", "/api/waveforms/Unit1"), "POST", {})
    assert st == 200
    time.sleep(1.5)
    serial = NS.SERIAL_BY_UNIT["Unit1"]
    for path, spec in inv["ch"]["waveforms"]["channels"].items():
        w = rec.last(NS.ch_topic(serial, path))
        assert w is not None, path
        assert list(w) == inv["ch"]["waveforms"]["payload_keys"], path
        assert w["samples"] == len(w["values"]) == int(spec["sampleRate"] * spec["default_seconds"])
        assert w["sampleRate"] == spec["sampleRate"] and w["unit"] == spec["unit"]
        assert w["trigger"] in inv["ch"]["waveforms"]["trigger"]


def test_hardwired_endpoint(stack, inv):
    st, body = httpd.http_json(url(stack, "ch", "/api/hardwired"))
    assert st == 200
    for u in NS.UNITS:
        assert set(body["units"][u]) == set(inv["hardwired"]["signals"])
    p = stack["rec"].last(NS.customer_topic("Powerhouse/Unit1/TurbineGuideBearingTemp"))
    assert 40 < p["value"] < 80


def test_http_routes(stack, inv):
    svc_key = {"dam-sim": "dam", "ch-plc-sim": "ch", "dam-scada": "scada", "ch-viewer": "viewer", "instructor": "instructor"}
    for svc, spec in inv["api"].items():
        if svc.startswith("_"):
            continue
        for path in spec["get"]:
            if "<" in path:
                continue
            st, _ = httpd.http_json(url(stack, svc_key[svc], path))
            assert st == 200, (svc, path)
    # pages are served as HTML
    import urllib.request
    for svc, page in (("scada", "/"), ("scada", "/scada"), ("viewer", "/"), ("instructor", "/")):
        with urllib.request.urlopen(url(stack, svc, page), timeout=3) as r:
            assert r.status == 200 and r.headers["Content-Type"].startswith("text/html")


def test_scada_sees_the_customer_tree_and_commands_work(stack):
    st, s = httpd.http_json(url(stack, "scada", "/api/state"))
    assert st == 200 and s["connected"]
    assert set(s["values"]) >= {"Plant/TotalMW", "Powerhouse/Unit3/State"}
    assert not [a for a in s["alarms"] if a["priority"] == 1], s["alarms"]
    st, r = httpd.http_json(url(stack, "scada", "/api/cmd"), "POST", {"path": "Powerhouse/Unit3/Cmd/Stop", "value": True})
    assert st == 200 and r["ok"]
    end = time.time() + 6
    while time.time() < end and stack["rec"].last(NS.customer_topic("Powerhouse/Unit3/State"))["value"] != "Stopping":
        time.sleep(0.3)
    assert stack["rec"].last(NS.customer_topic("Powerhouse/Unit3/State"))["value"] == "Stopping"
    # a bare-value MQTT command from any client works too
    stack["rec"].publish(NS.customer_topic("Powerhouse/Unit2/Cmd/MWSetpoint"), "30")
    time.sleep(2.5)
    assert stack["rec"].last(NS.customer_topic("Powerhouse/Unit2/ControlMode"))["value"] == "LOCAL"
    ev = [json.loads(m) for m in stack["rec"].msgs.get(NS.customer_topic(NS.EVENTS_TOPIC), [])]
    assert any("normal stop" in e["text"] for e in ev)
    st, tr = httpd.http_json(url(stack, "scada", "/api/trend?paths=Plant/TotalMW&minutes=5&points=50"))
    assert st == 200 and tr["series"]["Plant/TotalMW"]


def test_viewer_and_instructor(stack, inv):
    st, a = httpd.http_json(url(stack, "viewer", "/api/assets"))
    assert st == 200 and set(a["assets"]) == set(inv["ch"]["assets"])
    for serial, x in a["assets"].items():
        assert x["status"] == "ONLINE" and x["nameplate"]["serial"] == serial and x["seq_gaps"] == 0
    st, sc = httpd.http_json(url(stack, "instructor", "/api/scenarios"))
    assert st == 200 and sc["reachable"] == {"dam": True, "ch": True}
    assert {s["id"] for s in sc["scenarios"]} == set(inv["scenarios"]["dam"]) | set(inv["scenarios"]["ch"])
    st, _ = httpd.http_json(url(stack, "instructor", "/api/scenarios/shear_pin/start"), "POST", {"unit": "Unit1"})
    assert st == 200
    time.sleep(2.5)
    st, gt = httpd.http_json(url(stack, "instructor", "/api/ground_truth"))
    assert "shear_pin" in gt["ch"]["units"]["Unit1"]["active"]
    serial = NS.SERIAL_BY_UNIT["Unit1"]
    assert stack["rec"].last(NS.ch_topic(serial, "Turbine/ShearPinStatus"))["value"] == "BROKEN"
    events = [json.loads(m) for m in stack["rec"].msgs.get(NS.ch_topic(serial, NS.EVENTS_ALARM), [])]
    assert any(e["alarmId"] == "SHEAR_PIN_BROKEN" and e["state"] == "ACTIVE" for e in events)
    # the scenario itself is nowhere on the broker
    for t, ms in stack["rec"].msgs.items():
        assert all(b"shear_pin" not in m for m in ms[-3:]), t
    st, _ = httpd.http_json(url(stack, "instructor", "/api/reset"), "POST", {})
    assert st == 200
    time.sleep(2.5)
    assert stack["rec"].last(NS.ch_topic(serial, "Turbine/ShearPinStatus"))["value"] == "OK"


def test_losing_the_ch_plcs(stack):
    """Last, it kills the CH PLC process: last will OFFLINE, hardwired I/O fault in the customer tree, no trip."""
    p = stack["procs"]["chplc"]
    p.kill()
    p.wait(5)
    rec = stack["rec"]
    end = time.time() + 50          # the broker sends the will after 1.5 × keepalive (30 s)
    serial = NS.SERIAL_BY_UNIT["Unit1"]
    status = NS.ch_topic(serial, NS.META_STATUS)
    # a will forwarded to a live subscriber carries no retain flag: read the last message
    while time.time() < end and rec.msgs[status][-1] != b"OFFLINE":
        time.sleep(0.5)
    assert rec.msgs[status][-1] == b"OFFLINE"
    end = time.time() + 10          # hardwired values go stale after 5 s
    while time.time() < end and "HARDWIRED_IO_FAULT" not in rec.last(NS.customer_topic("Powerhouse/Unit1/ActiveAlarms"))["value"]:
        time.sleep(0.5)
    alarms = rec.last(NS.customer_topic("Powerhouse/Unit1/ActiveAlarms"))["value"]
    assert "HARDWIRED_IO_FAULT" in alarms and not [a for a in alarms if a.startswith("TRIP")]
    assert rec.last(NS.customer_topic("Powerhouse/Unit1/State"))["value"] == "Generating"
