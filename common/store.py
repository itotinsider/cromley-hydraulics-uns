"""Latest values and a ring-buffer trend store for MQTT subscribers (dam SCADA, CH asset viewer).

TagStore.update() takes every incoming value; a sampler snapshots every numeric tag once a second
into fixed-size arrays (FAST_SECONDS at 1 s) and once a minute into a slow ring (SLOW_MINUTES at
1 min means). In memory only: a restart starts with empty trends, like a SCADA without its
historian.
"""

import threading
import time
from array import array

FAST_SECONDS = 2 * 3600
SLOW_MINUTES = 48 * 60
NAN = float("nan")


class Ring:
    def __init__(self, n):
        self.n = n
        self.t = array("d", [0.0] * n)
        self.cols = {}
        self.i = 0          # next write slot
        self.count = 0

    def col(self, key):
        c = self.cols.get(key)
        if c is None:
            c = self.cols[key] = array("d", [NAN] * self.n)
        return c

    def append(self, ts, values):
        i = self.i
        self.t[i] = ts
        for k, c in self.cols.items():
            c[i] = values.get(k, NAN)
        for k, v in values.items():
            if k not in self.cols:
                self.col(k)[i] = v
        self.i = (i + 1) % self.n
        self.count = min(self.n, self.count + 1)

    def window(self, since):
        """Slot indices with t >= since, oldest first."""
        out = []
        for j in range(self.count):
            idx = (self.i - self.count + j) % self.n
            if self.t[idx] >= since:
                out.append(idx)
        return out


class TagStore:
    def __init__(self, stale_s=5.0):
        self.lock = threading.Lock()
        self.latest = {}     # path -> {"v": value, "ts": receive time, "src_ts": payload timestamp, "q": quality}
        self.stale_s = stale_s
        self.fast = Ring(FAST_SECONDS)
        self.slow = Ring(SLOW_MINUTES)
        self._acc = {}
        self._acc_n = {}
        self._minute = None

    def update(self, path, value, src_ts=None, quality=None):
        with self.lock:
            self.latest[path] = {"v": value, "ts": time.time(), "src_ts": src_ts, "q": quality}

    def get(self, path, default=None):
        e = self.latest.get(path)
        return default if e is None else e["v"]

    def age(self, path):
        e = self.latest.get(path)
        return None if e is None else time.time() - e["ts"]

    def snapshot(self):
        now = time.time()
        with self.lock:
            return {k: {"v": e["v"], "age": round(now - e["ts"], 1), "q": e["q"], "ts": e["src_ts"]}
                    for k, e in self.latest.items()}

    def sample(self, now=None):
        """Called once a second: numeric values (bools as 0/1) into the trend rings."""
        now = now or time.time()
        vals = {}
        with self.lock:
            for k, e in self.latest.items():
                v = e["v"]
                if now - e["ts"] > self.stale_s:
                    continue
                if isinstance(v, bool):
                    vals[k] = 1.0 if v else 0.0
                elif isinstance(v, (int, float)):
                    vals[k] = float(v)
            self.fast.append(now, vals)
            minute = int(now // 60)
            if self._minute is not None and minute != self._minute:
                self.slow.append(self._minute * 60 + 30, {k: self._acc[k] / self._acc_n[k] for k in self._acc})
                self._acc, self._acc_n = {}, {}
            self._minute = minute
            for k, v in vals.items():
                self._acc[k] = self._acc.get(k, 0.0) + v
                self._acc_n[k] = self._acc_n.get(k, 0) + 1

    def start_sampler(self):
        def loop():
            nxt = time.time()
            while True:
                nxt += 1.0
                time.sleep(max(0.0, nxt - time.time()))
                self.sample()
        threading.Thread(target=loop, daemon=True, name="trend-sampler").start()

    def trend(self, paths, minutes=60, points=300):
        """{"t": [...], "series": {path: [...]}} with bucket means (None for gaps)."""
        now = time.time()
        since = now - minutes * 60
        with self.lock:
            ring = self.fast if minutes * 60 <= FAST_SECONDS else self.slow
            idx = ring.window(since)
            cols = {p: ring.cols.get(p) for p in paths}
            ts = [ring.t[i] for i in idx]
            raw = {p: ([c[i] for i in idx] if c is not None else [NAN] * len(idx)) for p, c in cols.items()}
        if not ts:
            return {"t": [], "series": {p: [] for p in paths}}
        nb = max(1, points)          # buckets span the whole window; empty ones are skipped below
        step = (now - since) / nb
        out_t, out = [], {p: [] for p in paths}
        b0 = 0
        for b in range(nb):
            hi = since + (b + 1) * step
            b1 = b0
            while b1 < len(ts) and ts[b1] < hi:
                b1 += 1
            if b1 > b0:
                out_t.append(round(since + (b + 0.5) * step, 1))
                for p in paths:
                    seg = [x for x in raw[p][b0:b1] if x == x]
                    out[p].append(round(sum(seg) / len(seg), 4) if seg else None)
            b0 = b1
        return {"t": out_t, "series": out}
