"""Generate the interface inventory (inventory/) from each component's own source of truth.

Every component keeps owning its part (see inventory/README.md); this tool only *reads* them:

    docker compose run --rm tests python tools/inventory.py           # regenerate after a change
    docker compose run --rm tests python tools/inventory.py --check   # exit 1 + diff if stale

tests/test_inventory.py fails while the committed inventory differs from the code, so any added,
renamed or removed topic, command, hardwired signal, scenario or HTTP route shows up as a diff in
the PR. Standard library only (runs with plain python3 too).
"""

import csv
import difflib
import importlib.util
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "common"))

import namespace as NS  # noqa: E402

OUT_DIR = os.path.join(ROOT, "inventory")
SERVICES = {   # service → (source file, port, exposed on the host)
    "dam-sim": ("damsim/main.py", 8123, False),
    "ch-plc-sim": ("chplc/main.py", 8125, False),
    "dam-scada": ("scada/main.py", 8120, True),
    "instructor": ("instructor/main.py", 8121, True),
    "ch-viewer": ("chviewer/main.py", 8122, True),
}


def load_module(name, rel_path):
    """Import a file under its own name (damsim/model.py and chplc/model.py are both "model")."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def dumps(obj, flat_at=2, indent=0, width=118):
    """JSON with one record per line: anything `flat_at` levels deep goes on a single line, as does
    anything shorter than `width`. A changed topic is a one-line diff."""
    flat = json.dumps(obj, ensure_ascii=False)
    if indent // 2 >= flat_at or len(flat) + indent <= width or not isinstance(obj, (dict, list)) or not obj:
        return flat
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(obj, dict):
        items = [f"{inner}{json.dumps(k, ensure_ascii=False)}: {dumps(v, flat_at, indent + 2, width)}"
                 for k, v in obj.items()]
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    items = [f"{inner}{dumps(v, flat_at, indent + 2, width)}" for v in obj]
    return "[\n" + ",\n".join(items) + "\n" + pad + "]"


def _tag(t, **extra):
    d = {"unit": t["unit"], "type": t["type"], "decimals": t["dec"]}
    if t["lo"] is not None or t["hi"] is not None:
        d["range"] = [t["lo"], t["hi"]]
    d.update(extra)
    d["desc"] = t["desc"]
    return d


# ---------------------------------------------------------------- layers
def customer_layer():
    hw_keys = {h["key"] for h in NS.HARDWIRED}
    tags = {}
    for t in NS.customer_tags():
        key = t["path"].split("/")[-1]
        src = "hardwired (element A, via the CH PLC simulator)" if key in hw_keys else "dam-sim model"
        tags[t["path"]] = _tag(t, source=src)
    return {
        "_source": "common/namespace.py customer_tags() (published by damsim/main.py every second, retained)",
        "prefix": NS.CUSTOMER_PREFIX,
        "payload": {"value": "<typed value>", "unit": "<unit or ''>", "timestamp": "ISO 8601 UTC, ms, Z"},
        "publisher": "dam-sim", "retained": True, "interval_s": 1,
        "subscribers": ["dam-scada (all)", "ch-plc-sim (context, per unit)", "nodered", "mqtt-explorer"],
        "tags": tags,
        "events": {"path": NS.EVENTS_TOPIC, "retained": False,
                   "payload": {"timestamp": "ISO", "source": "Plant|Unit1..|Intake|...", "kind":
                               "command|refused|state|trip|info", "text": "..."}},
        "unit_states": list(NS.UNIT_STATES),
        "control_modes": list(NS.CONTROL_MODES),
        "gate_modes": list(NS.GATE_MODES),
    }


def commands_layer():
    cmds = {}
    for c in NS.customer_commands():
        d = {k: v for k, v in c.items() if k not in ("path", "desc")}
        d["desc"] = c["desc"]
        cmds[c["path"]] = d
    return {
        "_source": "common/namespace.py customer_commands() (handled by damsim/model.py Dam.command)",
        "prefix": NS.CUSTOMER_PREFIX,
        "payload": "bare value or JSON {\"value\": ..., \"source\": ...}; never retained",
        "publishers": ["dam-scada (operator, grid operator panel)", "any MQTT client"],
        "subscriber": "dam-sim (+/Cmd/# and +/+/Cmd/#)",
        "commands": cmds,
    }


def ch_layer():
    ch_model = load_module("ch_model", "chplc/model.py")
    waves = {}
    for w in NS.ch_waveforms():
        waves[w["path"]] = {"unit": w["unit"], "group": w["group"], "sampleRate": w["rate"],
                            "default_seconds": w["seconds"], "default_every_s": w["every_s"],
                            "decimals": ch_model.WAVE_DEC[w["group"]], "desc": w["desc"]}
    return {
        "_source": "common/namespace.py ch_tags(), ch_waveforms() (published by chplc/main.py, one PLC per asset)",
        "topic": f"{NS.CH_PREFIX}/<CustomerId>/<SiteId>/<AssetSerial>/<path>",
        "assets": {a["serial"]: {"customer_unit": a["unit"], "commissioned": a["commissioned"],
                                 "prefix": NS.ch_asset_prefix(a["serial"])} for a in NS.ASSETS},
        "payload": {"value": "<typed value>", "unit": "<unit>", "timestamp": "ISO", "quality": list(NS.QUALITIES),
                    "seq": "per-PLC message counter over every message it sends"},
        "process": {"interval_s": 1, "retained": "RETAIN_PROCESS_VALUES (default true)",
                    "tags": {t["path"]: _tag(t) for t in NS.ch_tags()}},
        "context": {"_note": "copied from the customer tree (subscribe only, never written there)",
                    **{k: v for k, v in {**NS.CH_CONTEXT, **NS.CH_CONTEXT_EXTRA}.items()}},
        "waveforms": {"retained": False, "payload_keys": ["timestamp", "seq", "sampleRate", "samples", "unit", "speedRpm",
                                                          "keyphasorIdx", "trigger", "values"],
                      "trigger": ["periodic", "alarm", "manual"], "channels": waves},
        "meta": {NS.META_NAMEPLATE: "retained JSON nameplate (serial, model, ratings, customer unit name, waveforms)",
                 NS.META_STATUS: "retained ONLINE / OFFLINE (MQTT last will)"},
        "events": {NS.EVENTS_ALARM: {"retained": False, "payload_keys": ["timestamp", "seq", "serial", "alarmId", "state",
                                                                          "severity", "tag", "value", "limit", "text"]},
                   "Events/ActiveAlarms": {"retained": True, "payload_keys": ["timestamp", "seq", "value"]}},
        "plc_alarms": {aid: {"tag": tag, "op": op, "limit": lim, "severity": sev, "only_running": run}
                       for aid, tag, op, lim, sev, text, run in ch_model.Turbine(NS.ASSETS[0]).alarm_defs()},
    }


def hardwired_layer():
    return {
        "_source": "common/namespace.py HARDWIRED (served by chplc/main.py GET /api/hardwired, polled by damsim/main.py)",
        "_note": "element A of dual-element sensors: the customer's copper, not MQTT. A CH-side sensor fault "
                 "(scenario rtd_fault) only affects element B.",
        "signals": {h["key"]: {"unit": h["unit"], "ch_element_b": h["ch"] or "sum of Cooling/WaterFlow_*",
                               "customer_topic": f"Powerhouse/<Unit>/{h['key']}"} for h in NS.HARDWIRED},
    }


def scenarios_layer():
    dam_model = load_module("dam_model", "damsim/model.py")
    ch_model = load_module("ch_model", "chplc/model.py")

    def clean(spec):
        return {k: v for k, v in spec.items() if k != "desc"}
    return {
        "_source": "damsim/model.py SCENARIOS, chplc/model.py SCENARIOS (instructor station only: never published)",
        "dam": {sid: clean(s) for sid, s in dam_model.SCENARIOS.items()},
        "ch": {sid: clean(s) for sid, s in ch_model.SCENARIOS.items()},
        "letters": {s["letter"]: sid for src in (dam_model.SCENARIOS, ch_model.SCENARIOS)
                    for sid, s in src.items() if s.get("letter")},
    }


ROUTE_RX = re.compile(r'@app\.(get|post)\("([^"]+)"\)')
STATIC_RX = re.compile(r'app\.static\("([^"]+)"')


def api_layer():
    out = {"_source": "the @app.get/@app.post routes in each service's main.py"}
    for svc, (path, port, host) in SERVICES.items():
        src = open(os.path.join(ROOT, path), encoding="utf-8").read()
        out[svc] = {"port": port, "host": host,
                    "pages": STATIC_RX.findall(src),
                    "get": [p for m, p in ROUTE_RX.findall(src) if m == "get"],
                    "post": [p for m, p in ROUTE_RX.findall(src) if m == "post"]}
    return out


def topics_csv():
    rows = []
    for t in NS.customer_tags():
        rows.append(["customer", NS.customer_topic(t["path"]), t["unit"], t["type"], "yes", "dam-sim", "1 s", t["desc"]])
    rows.append(["customer", NS.customer_topic(NS.EVENTS_TOPIC), "", "json", "no", "dam-sim", "on event",
                 "Plant events: commands accepted/refused, state changes, trips"])
    for c in NS.customer_commands():
        rows.append(["command", NS.customer_topic(c["path"]), c.get("unit", ""), c["type"], "no", "dam-scada / any",
                     "on command", c["desc"]])
    for a in NS.ASSETS:
        s = a["serial"]
        rows.append(["ch", NS.ch_topic(s, NS.META_NAMEPLATE), "", "json", "yes", f"ch-plc {s}", "on connect", "Nameplate"])
        rows.append(["ch", NS.ch_topic(s, NS.META_STATUS), "", "string", "yes", f"ch-plc {s}", "on connect / will",
                     "ONLINE / OFFLINE (last will)"])
        for t in NS.ch_tags():
            rows.append(["ch", NS.ch_topic(s, t["path"]), t["unit"], t["type"], "yes", f"ch-plc {s}", "1 s", t["desc"]])
        for w in NS.ch_waveforms():
            rows.append(["ch-waveform", NS.ch_topic(s, w["path"]), w["unit"], "json", "no", f"ch-plc {s}",
                         f"{w['every_s']} s + on alarm", f"{w['desc']}: {w['rate']} S/s × {w['seconds']} s"])
        rows.append(["ch", NS.ch_topic(s, NS.EVENTS_ALARM), "", "json", "no", f"ch-plc {s}", "on event", "PLC alarm events"])
        rows.append(["ch", NS.ch_topic(s, "Events/ActiveAlarms"), "", "json", "yes", f"ch-plc {s}", "on change",
                     "Active PLC alarm ids"])
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["tree", "topic", "unit", "type", "retained", "publisher", "rate", "description"])
    w.writerows(rows)
    return buf.getvalue()


def build():
    return {
        "customer.json": dumps(customer_layer()) + "\n",
        "commands.json": dumps(commands_layer()) + "\n",
        "ch.json": dumps(ch_layer(), flat_at=3) + "\n",
        "hardwired.json": dumps(hardwired_layer()) + "\n",
        "scenarios.json": dumps(scenarios_layer()) + "\n",
        "api.json": dumps(api_layer()) + "\n",
        "topics.csv": topics_csv(),
    }


def diff(files=None):
    """Unified diff between the committed inventory and the code (empty = up to date)."""
    files = files or build()
    lines = []
    for name, new in files.items():
        path = os.path.join(OUT_DIR, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old != new:
            lines += difflib.unified_diff(old.splitlines(), new.splitlines(), f"inventory/{name} (committed)",
                                          f"inventory/{name} (from the code)", lineterm="", n=1)
    return lines


def main():
    files = build()
    if "--check" in sys.argv:
        d = diff(files)
        print("\n".join(d) if d else "inventory/ is up to date")
        return 1 if d else 0
    os.makedirs(OUT_DIR, exist_ok=True)
    changed = []
    for name, content in files.items():
        path = os.path.join(OUT_DIR, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != content:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            changed.append(name)
    print("updated: " + ", ".join(changed) if changed else "inventory/ is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
