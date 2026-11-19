"""The dam SCADA's historian: exception-reported time series, the event journal and the sequence of
events, in SQLite (the HCW DCS historian's design, for the customer tree).

* Exception (deadband) reporting: a point is stored only when it moved more than its deadband
  (`deadband_pct` of the point's range) since the last stored value, or when `max_interval_s` has
  passed (a heartbeat: a flat line still has samples that prove the point was alive).
* Quality with the value: a point that goes stale (no fresh MQTT value) is written once as BAD with
  no value, so trends show a gap instead of a flat-lined last value.
* Retention: rows older than `retention_days` are purged once an hour.
* Trends: per time bucket the mean of the stored samples; a bucket without samples holds the last
  stored value (exception reporting means "unchanged"), unless the point was BAD or the heartbeat
  is overdue.

One writer (the SCADA's 1 s loop); HTTP threads read with their own connections (WAL mode).
Timestamps are the payload's (source) time when there is one.
"""

import logging
import os
import sqlite3
import threading
import time

log = logging.getLogger("dam-scada.historian")

GOOD, BAD = 0, 1


class Historian:
    def __init__(self, path, points, deadband_pct=0.1, max_interval_s=60.0, retention_days=14.0):
        """`points`: {path: (unit, description, span)} for every numeric customer tag."""
        self.path = path
        self.points = points
        self.deadband_pct = deadband_pct
        self.max_interval = max_interval_s
        self.retention_s = retention_days * 86400
        self.last = {}                # path -> (ts, value, quality) last stored
        self.local = threading.local()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        db = self._db()
        db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS points (id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, unit TEXT, description TEXT);
            CREATE TABLE IF NOT EXISTS samples (point_id INTEGER NOT NULL, ts REAL NOT NULL, value REAL, quality INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS samples_point_ts ON samples (point_id, ts);
            CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, ts REAL NOT NULL, timestamp TEXT, kind TEXT, source TEXT, text TEXT);
            CREATE INDEX IF NOT EXISTS events_ts ON events (ts);
            CREATE TABLE IF NOT EXISTS soe (id INTEGER PRIMARY KEY, ts REAL NOT NULL, timestamp TEXT, unit TEXT, kind TEXT,
                                            code TEXT, text TEXT, first_out INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS soe_ts ON soe (ts);
        """)
        for p, (unit, desc, _) in points.items():
            db.execute("INSERT INTO points (path, unit, description) VALUES (?, ?, ?) "
                       "ON CONFLICT(path) DO UPDATE SET unit = excluded.unit, description = excluded.description", (p, unit, desc))
        db.commit()
        self.ids = dict(db.execute("SELECT path, id FROM points").fetchall())
        self.last_purge = 0.0
        self.stored = 0
        log.info("Historian at %s: %d points, deadband %.2f %% of range, heartbeat %ds, retention %g d",
                 path, len(points), deadband_pct, max_interval_s, retention_days)

    def _db(self):
        db = getattr(self.local, "db", None)
        if db is None:
            db = sqlite3.connect(self.path, timeout=10)
            db.execute("PRAGMA busy_timeout=5000")
            self.local.db = db
        return db

    # ------------------------------------------------------------------ writing (the 1 s loop only)
    def store(self, now, values, events=(), soe=()):
        """`values`: {path: (source ts, value or None for BAD)}."""
        rows = []
        for p, (ts, v) in values.items():
            pid = self.ids.get(p)
            if pid is None:
                continue
            q = GOOD if v is not None else BAD
            prev = self.last.get(p)
            if prev is not None:
                pts, pv, pq = prev
                if ts <= pts or (q == BAD and pq == BAD):
                    continue
                if q == GOOD and pq == GOOD and ts - pts < self.max_interval:
                    span = self.points[p][2] or 1.0
                    if abs(v - pv) <= span * self.deadband_pct / 100.0:
                        continue
            self.last[p] = (ts, v, q)
            rows.append((pid, ts, v, q))
        db = self._db()
        if rows:
            db.executemany("INSERT INTO samples (point_id, ts, value, quality) VALUES (?, ?, ?, ?)", rows)
            self.stored += len(rows)
        if events:
            db.executemany("INSERT INTO events (ts, timestamp, kind, source, text) VALUES (?, ?, ?, ?, ?)",
                           [(e["t"], e.get("timestamp"), e["kind"], e["source"], e["text"]) for e in events])
        if soe:
            db.executemany("INSERT INTO soe (ts, timestamp, unit, kind, code, text, first_out) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           [(e["t"], e["timestamp"], e["unit"], e["kind"], e.get("code"), e["text"], int(e.get("first_out", False)))
                            for e in soe])
        db.commit()
        if now - self.last_purge > 3600:
            self.last_purge = now
            cut = now - self.retention_s
            n = db.execute("DELETE FROM samples WHERE ts < ?", (cut,)).rowcount
            db.execute("DELETE FROM events WHERE ts < ?", (cut,))
            db.execute("DELETE FROM soe WHERE ts < ?", (cut,))
            db.commit()
            if n:
                log.info("Purged %d samples older than the retention", n)

    # ------------------------------------------------------------------ reading
    def trend(self, paths, minutes=60, points=300, end=None):
        """{"t": [...], "series": {path: [...]}}: bucket means, held through buckets without samples."""
        end = end or time.time()
        start = end - minutes * 60
        nb = max(1, int(points))
        width = (end - start) / nb
        db = self._db()
        t = [round(start + (b + 0.5) * width, 1) for b in range(nb)]
        series = {}
        for p in paths:
            pid = self.ids.get(p)
            if pid is None:
                series[p] = [None] * nb
                continue
            prior = db.execute("SELECT ts, value, quality FROM samples WHERE point_id = ? AND ts < ? ORDER BY ts DESC LIMIT 1",
                               (pid, start)).fetchone()
            # per bucket: mean of the GOOD values, the last sample's time, the last GOOD sample's time
            rows = db.execute("SELECT CAST((ts - ?) / ? AS INTEGER) AS b, AVG(value), MAX(ts), "
                              "MAX(CASE WHEN quality = 0 THEN ts END) "
                              "FROM samples WHERE point_id = ? AND ts >= ? AND ts <= ? GROUP BY b ORDER BY b",
                              (start, width, pid, start, end)).fetchall()
            byb = {b: (avg, last_ts, GOOD if last_good is not None and last_good >= last_ts else BAD)
                   for b, avg, last_ts, last_good in rows}
            out = []
            hold = (prior[0], prior[1], prior[2]) if prior else None       # (ts, value, quality) last stored
            for b in range(nb):
                if b in byb:
                    avg, last_ts, last_q = byb[b]
                    out.append(round(avg, 4) if avg is not None else None)
                    hold = (last_ts, avg if last_q == GOOD else None, last_q)
                else:
                    bt = start + (b + 0.5) * width
                    ok = hold and hold[2] == GOOD and hold[1] is not None and bt - hold[0] <= self.max_interval * 1.5
                    out.append(round(hold[1], 4) if ok else None)
            series[p] = out
        # drop the leading buckets where no series has a value (before the historian started)
        first = next((i for i in range(nb) if any(series[p][i] is not None for p in paths)), nb)
        return {"t": t[first:], "series": {p: v[first:] for p, v in series.items()}}

    def events(self, limit=200):
        rows = self._db().execute("SELECT ts, timestamp, kind, source, text FROM events ORDER BY ts DESC, id DESC LIMIT ?",
                                  (limit,)).fetchall()
        return [{"t": r[0], "timestamp": r[1], "kind": r[2], "source": r[3], "text": r[4]} for r in rows]

    def soe(self, limit=200):
        rows = self._db().execute("SELECT ts, timestamp, unit, kind, code, text, first_out FROM soe ORDER BY ts DESC, id DESC LIMIT ?",
                                  (limit,)).fetchall()
        return [{"t": r[0], "timestamp": r[1], "unit": r[2], "kind": r[3], "code": r[4], "text": r[5], "first_out": bool(r[6])}
                for r in rows]

    def stats(self):
        db = self._db()
        n = db.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        first = db.execute("SELECT MIN(ts) FROM samples").fetchone()[0]
        size = sum(os.path.getsize(self.path + x) for x in ("", "-wal") if os.path.exists(self.path + x))
        return {"points": len(self.ids), "samples": n, "first_ts": first, "size_bytes": size, "stored_since_start": self.stored,
                "deadband_pct": self.deadband_pct, "max_interval_s": self.max_interval, "retention_days": self.retention_s / 86400}
