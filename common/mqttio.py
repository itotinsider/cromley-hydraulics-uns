"""Small shared MQTT helpers: payload format, command parsing and a reconnecting paho client.

Payloads (design basis "Process payload"):
  customer tree   {"value": 61.4, "unit": "°C", "timestamp": "2026-10-20T12:00:00.000Z"}   (Sweet Harmony format)
  CH tree         the same plus "quality" and "seq" (per-PLC message counter, so gaps are detectable)
"""

import json
import logging
import time
from datetime import datetime, timezone

log = logging.getLogger("mqtt")


def iso(ts=None):
    """UTC ISO 8601 with milliseconds and a Z."""
    dt = datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def rounded(value, dec):
    if isinstance(value, bool) or value is None or isinstance(value, (str, list, dict)):
        return value
    if dec == 0:
        return int(round(value))
    return round(float(value), dec)


def customer_payload(value, unit, ts=None):
    return json.dumps({"value": value, "unit": unit, "timestamp": iso(ts)}, ensure_ascii=False)


def ch_payload(value, unit, seq, quality="GOOD", ts=None):
    return json.dumps({"value": value, "unit": unit, "timestamp": iso(ts), "quality": quality, "seq": seq},
                      ensure_ascii=False)


def parse_value(raw):
    """A command or tag payload: bare value ("42", "true", "PLANT") or JSON {"value": ...}."""
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    raw = raw.strip()
    if not raw:
        return None
    try:
        v = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(v, dict):
        return v.get("value")
    return v


def as_bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("1", "true", "on", "yes")
    return False


def make_client(client_id, host, port, subscriptions=(), on_message=None, will=None):
    """A paho v2 client that connects in the background and resubscribes after every reconnect.

    will: (topic, payload) published retained by the broker if we disappear (MQTT last will).
    """
    import paho.mqtt.client as mqtt

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    c.reconnect_delay_set(1, 10)
    if will:
        c.will_set(will[0], will[1], qos=1, retain=True)

    def _on_connect(cl, userdata, flags, reason_code, properties):
        log.info("%s connected to %s:%s (%s)", client_id, host, port, reason_code)
        for t in subscriptions:
            cl.subscribe(t, qos=0)
        if c.on_connected_hook:
            c.on_connected_hook(cl)

    def _on_disconnect(cl, userdata, flags, reason_code, properties):
        log.warning("%s disconnected (%s), reconnecting", client_id, reason_code)

    c.on_connected_hook = None
    c.on_connect = _on_connect
    c.on_disconnect = _on_disconnect
    if on_message:
        c.on_message = on_message
    c.connect_async(host, port, keepalive=30)
    c.loop_start()
    return c
