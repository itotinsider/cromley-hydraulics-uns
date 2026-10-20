"""Cross-references: every component only uses names that exist where they come from.

namespace ↔ dam model ↔ CH model ↔ hardwired ↔ SCADA alarms ↔ web pages ↔ Node-RED ↔ docs.
Uses the `code` fixture (inventory generated from the code now), not the committed one.
"""

import glob
import json
import os
import re

import pytest

import namespace as NS
from conftest import ROOT, read

CUSTOMER_AREAS = ("Reservoir", "River", "Plant", "Intake", "Penstock", "Spillway", "BottomOutlet", "Powerhouse")
CH_SUBSYSTEMS = ("Context", "Bearings", "Cooling", "Governor", "Turbine", "Vibration", "Generator", "Counters",
                 "Events", "_meta")


@pytest.fixture(scope="module")
def dam(models):
    dam_model, _, _ = models
    return dam_model.Dam(seed=1, now=0.0)


@pytest.fixture(scope="module")
def tb(models):
    _, ch_model, _ = models
    t = ch_model.Turbine(NS.ASSETS[0], now=0.0)
    for k in NS.CH_CONTEXT:
        t.set_context(k, 0.0 if "UnitState" not in k else "Generating", 0.0)
    t.step(1.0, 1.0)
    return t


def customer_paths():
    return {t["path"] for t in NS.customer_tags()}


def command_paths():
    return {c["path"] for c in NS.customer_commands()}


def ch_paths():
    return {t["path"] for t in NS.ch_tags()} | {w["path"] for w in NS.ch_waveforms()} | \
        {NS.META_NAMEPLATE, NS.META_STATUS, NS.EVENTS_ALARM, "Events/ActiveAlarms"}


# ----------------------------------------------------------------------------- namespace
def test_no_duplicate_paths():
    for paths in ([t["path"] for t in NS.customer_tags()], [c["path"] for c in NS.customer_commands()],
                  [t["path"] for t in NS.ch_tags()] + [w["path"] for w in NS.ch_waveforms()]):
        assert len(paths) == len(set(paths)), [p for p in paths if paths.count(p) > 1]


def test_no_leaf_is_also_a_branch():
    """A topic that carries a value never has children (clean tree for UNS browsers)."""
    for paths in (customer_paths() | command_paths() | {NS.EVENTS_TOPIC}, ch_paths()):
        for p in paths:
            assert not any(q.startswith(p + "/") for q in paths), p


def test_topic_segments_are_clean():
    seg = re.compile(r"^[A-Za-z0-9_]+$")
    for p in customer_paths() | command_paths() | ch_paths():
        for s in p.split("/"):
            assert seg.match(s), f"{p}: segment {s!r}"


def test_serials_and_units():
    assert sorted(NS.UNIT_BY_SERIAL.values()) == sorted(NS.UNITS)
    for a in NS.ASSETS:
        assert re.match(r"^CH-FR-\d{4}-\d{4}$", a["serial"]), a


# ----------------------------------------------------------------------------- publishers own their names
def test_dam_publishes_exactly_the_customer_tree(models, dam):
    hw_keys = {h["key"] for h in NS.HARDWIRED}
    for u in NS.UNITS:
        dam.set_hardwired(u, {h["key"]: 60.0 for h in NS.HARDWIRED}, dam.t)
    assert set(dam.values()) == customer_paths()
    # without hardwired I/O only the hardwired tags go missing
    dam2 = models[0].Dam(seed=2, now=0.0)
    missing = customer_paths() - set(dam2.values())
    assert {p.split("/")[-1] for p in missing} == hw_keys


def test_customer_values_have_the_declared_type(dam):
    kinds = {"float": (int, float), "bool": (bool,), "string": (str,), "json": (list, dict), "int": (int,)}
    for t in NS.customer_tags():
        v = dam.values().get(t["path"])
        if v is None:
            continue
        assert isinstance(v, kinds[t["type"]]), (t["path"], v)
        if t["type"] == "float":
            assert not isinstance(v, bool), t["path"]
        if t["path"].endswith("/State"):
            assert v in NS.UNIT_STATES


def test_ch_plc_publishes_exactly_the_ch_tree(tb):
    assert set(tb.last) == {t["path"] for t in NS.ch_tags()}
    for path, (v, q) in tb.last.items():
        assert q in NS.QUALITIES, path


def test_hardwired_signals(tb):
    hw = tb.hardwired()
    assert set(hw) == {h["key"] for h in NS.HARDWIRED}
    ch = {t["path"] for t in NS.ch_tags()}
    for h in NS.HARDWIRED:
        assert h["ch"] is None or h["ch"] in ch, h
        for u in NS.UNITS:
            assert f"Powerhouse/{u}/{h['key']}" in customer_paths()


def test_ch_context_comes_from_the_customer_tree():
    ch = {t["path"] for t in NS.ch_tags()}
    for ch_path, cust in {**NS.CH_CONTEXT, **NS.CH_CONTEXT_EXTRA}.items():
        assert ch_path in ch, ch_path
        for u in NS.UNITS:
            assert cust.format(unit=u) in customer_paths(), cust


def test_every_command_is_handled(models):
    sample = {"float": 20.0, "bool": True, "trigger": True}
    for c in NS.customer_commands():
        d = models[0].Dam(seed=3, now=0.0)
        v = c["values"][0] if c["type"] == "enum" else sample[c["type"]]
        ok, msg = d.command(c["path"], v)
        assert "unknown command" not in msg.lower() and "unknown" not in msg.lower(), (c["path"], msg)


def test_unit_alarm_codes_match_the_scada(models):
    dam_model = models[0]
    src = read("scada/main.py")
    codes = set(re.findall(r'"((?:TRIP|BEARING|COOLING|GOV|HARDWIRED)_[A-Z_]+)": \(', src))
    assert codes == set(dam_model.TRIP_CODES) | set(dam_model.WARN_CODES)


def test_scada_alarms_use_existing_tags():
    import inventory
    scada = inventory.load_module("scada_main", "scada/main.py")
    ids = [a[0] for a in scada.ALARMS]
    assert len(ids) == len(set(ids))
    for aid, path, op, limit, prio, *_ in scada.ALARMS:
        assert path in customer_paths(), (aid, path)
        assert prio in (1, 2, 3) and op in (">", "<", "=="), aid


def test_ch_plc_alarms_use_existing_tags(tb):
    ch = {t["path"] for t in NS.ch_tags()}
    ids = [d[0] for d in tb.alarm_defs()]
    assert len(ids) == len(set(ids))
    for aid, tag, *_ in tb.alarm_defs():
        assert tag in ch, (aid, tag)


# ----------------------------------------------------------------------------- scenarios / hidden faults
def test_scenarios(models):
    dam_model, ch_model, _ = models
    ids = list(dam_model.SCENARIOS) + list(ch_model.SCENARIOS)
    assert len(ids) == len(set(ids)), "scenario ids must be unique across the two simulators (instructor merges them)"
    letters = [s["letter"] for s in list(dam_model.SCENARIOS.values()) + list(ch_model.SCENARIOS.values()) if s["letter"]]
    assert sorted(letters) == list("ABCDEFGH")
    for sid, s in ch_model.SCENARIOS.items():
        assert s["kind"] in ("ramp", "step") and ("duration_s" in s) == (s["kind"] == "ramp"), sid
        assert 1 <= s["mode"] <= 15, sid
    for sid, s in dam_model.SCENARIOS.items():
        assert s["target"] in ("unit", "plant"), sid


def test_hidden_faults_stay_hidden(models):
    """Scenario names never appear in a topic, a published payload builder, the SCADA, the viewer or Node-RED."""
    dam_model, ch_model, _ = models
    words = set(dam_model.SCENARIOS) | set(ch_model.SCENARIOS)
    topics = customer_paths() | command_paths() | ch_paths()
    for w in words:
        assert not any(w.lower() in t.lower() for t in topics), w
    consumers = ["scada/main.py", "chviewer/main.py", "nodered_data/flows.json"] + \
        glob.glob(os.path.join(ROOT, "scada/web/*.html")) + glob.glob(os.path.join(ROOT, "chviewer/web/*.html"))
    for f in consumers:
        text = open(os.path.join(ROOT, f), encoding="utf-8").read()
        for w in words:
            assert f'"{w}"' not in text and f"'{w}'" not in text, f"{f} mentions scenario {w}"
        assert "ground_truth" not in text, f"{f} reads ground truth"
        if not f.endswith("scada/web/index.html"):      # the hub may name the internal ports in its drawing
            assert ":8123" not in text and ":8125" not in text and "ch-plc-sim:" not in text, f"{f} talks to a simulator"


def test_scada_never_reads_the_ch_tree():
    """The pages only talk to their own server, so the subscriptions are what counts."""
    text = read("scada/main.py")
    assert "CH_PREFIX" not in text and "v1.0/CH" not in text and "ch_topic" not in text


def test_viewer_never_reads_the_customer_tree():
    text = read("chviewer/main.py")
    assert "CUSTOMER_PREFIX" not in text and "v1.0/DRWPA" not in text and "customer_topic" not in text


# ----------------------------------------------------------------------------- consumers use existing names
PATH_RX = re.compile(r"""["'`]((?:[A-Za-z0-9_]+|\$\{[^}]+\})(?:/(?:[A-Za-z0-9_]+|\$\{[^}]+\}))+)["'`]""")


def _expand(p, subs):
    """Replace ${...} with every candidate; return the concrete variants."""
    if "${" not in p:
        return [p]
    head, rest = p.split("${", 1)
    _, tail = rest.split("}", 1)
    out = []
    for s in subs:
        out += _expand(head + s + tail, subs)
    return out


def _valid_prefixes(paths):
    pre = set()
    for p in paths:
        parts = p.split("/")
        for i in range(1, len(parts) + 1):
            pre.add("/".join(parts[:i]))
    return pre


@pytest.mark.parametrize("page,areas,paths,subs", [
    ("scada/web/scada.html", CUSTOMER_AREAS, "customer", list(NS.UNITS) + list(NS.SPILLWAY_GATES)),
    ("scada/web/index.html", CUSTOMER_AREAS, "customer", list(NS.UNITS)),
    ("chviewer/web/index.html", CH_SUBSYSTEMS, "ch", list(NS.GUIDE_BEARINGS) + ["X", "Y", "Thrust"]),
])
def test_pages_use_existing_paths(page, areas, paths, subs):
    if not os.path.exists(os.path.join(ROOT, page)):
        pytest.skip("page not built")
    valid = customer_paths() | command_paths() | {NS.EVENTS_TOPIC} if paths == "customer" else ch_paths()
    ok = _valid_prefixes(valid)
    bad = []
    for m in PATH_RX.findall(read(page)):
        if m.split("/")[0] not in areas:
            continue
        variants = _expand(m, subs)
        # a template like `${b}/Shaft${ax}` is valid when at least one expansion exists
        if not any(v in ok or any(x.endswith("/" + v) or x.startswith(v + "/") for x in valid) for v in variants):
            bad.append(m)
    assert not bad, f"{page} uses paths that are not in the namespace: {sorted(set(bad))}"


def _topic_matches(pattern, topic):
    pp, tt = pattern.split("/"), topic.split("/")
    for i, p in enumerate(pp):
        if p == "#":
            return True
        if i >= len(tt) or (p != "+" and p != tt[i]):
            return False
    return len(pp) == len(tt)


def all_topics():
    rows = read("inventory/topics.csv").splitlines()[1:]
    return [r.split(",")[1] for r in rows]


def test_nodered_subscriptions_match_topics():
    flows = json.loads(read("nodered_data/flows.json"))
    topics = all_topics()
    subs = [n["topic"] for n in flows if n.get("type") == "mqtt in"]
    assert subs, "no MQTT subscriptions in the flow"
    for s in subs:
        assert any(_topic_matches(s, t) for t in topics), f"Node-RED subscribes to {s}, which matches no topic"
    ch = {t["path"] for t in NS.ch_tags()}
    for n in flows:
        if n.get("type") == "function":
            for path in re.findall(r'"((?:Context|Cooling|Bearings)/[A-Za-z0-9_/]+)":', n["func"]):
                assert path in ch, f"Node-RED function {n['name']} uses {path}"


def test_mqtt_explorer_seed():
    s = json.loads(read("mqtt_explorer_data/settings.json"))
    conns = s["ConnectionManager_connections"]
    assert len(conns) == 1, "only the seeded connection may be committed"
    c = next(iter(conns.values()))
    assert c["host"] == "mosquitto" and c["port"] == 1883
    assert {x["topic"] for x in c["subscriptions"]} == {f"{NS.VERSION}/{NS.CUSTOMER_ID}/#", f"{NS.VERSION}/CH/#"}


DOC_FILES = ["README.md", "CLAUDE.md"] + sorted(glob.glob(os.path.join(ROOT, "wiki", "*.md")))
TOPIC_RX = re.compile(r"v1\.0/(?:DRWPA|CH)(?:/[A-Za-z0-9_+#<>.\-]+)*")


def _doc_topic_ok(t, topics):
    t = t.rstrip(".,)`'\"/")
    if "<" in t or "..." in t or "…" in t:
        return True          # placeholders are explanations, not names
    if "#" in t or "+" in t:
        return any(_topic_matches(t, x) for x in topics)
    return t in topics or any(x.startswith(t + "/") for x in topics)


@pytest.mark.parametrize("doc", DOC_FILES)
def test_docs_name_existing_topics(doc):
    path = doc if os.path.isabs(doc) else os.path.join(ROOT, doc)
    if not os.path.exists(path):
        pytest.skip("not written")
    topics = all_topics()
    bad = [t for t in TOPIC_RX.findall(open(path, encoding="utf-8").read()) if not _doc_topic_ok(t, topics)]
    assert not bad, f"{os.path.basename(path)} names topics that don't exist: {sorted(set(bad))}"


def test_wiki_links_resolve():
    pages = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "wiki", "*.md"))}
    if not pages:
        pytest.skip("no wiki")
    images = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "wiki", "images", "*.png"))}
    bad = []
    for p in glob.glob(os.path.join(ROOT, "wiki", "*.md")):
        text = open(p, encoding="utf-8").read()
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if target.lstrip("<").startswith(("http://", "https://", "mailto:", "#")):
                continue
            if target.startswith("images/"):
                if target[len("images/"):] not in images:
                    bad.append((os.path.basename(p), target))
                continue
            page = target.split("#")[0]
            if page not in pages:
                bad.append((os.path.basename(p), target))
    assert not bad, bad
