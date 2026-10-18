"""Web app for the Smart Music Playlist Manager. Standard library only: python server.py, then open http://localhost:8000"""
import itertools, json, os, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from playlist import FIELDS, Playlist, Track, field_value, lower_bound, mmss, sample_a, secs

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
LOCK = threading.Lock()                      # ponytail: one shared playlist for everyone on this server; fine for a local demo
UIDS = itertools.count(1)
STATE = {}

ALGO = {
    "sort": ("Merge sort", "O(n log n)", "Dynamic array"),
    "search": ("Binary search", "O(log n)", "Dynamic array"),
    "group": ("Hash buckets", "O(n + k)", "Hash map"),
    "count": ("Running counters", "O(1)", "Hash map"),
    "insert": ("Binary search + splice", "O(log n) + O(1)", "Doubly linked list"),
    "delete": ("Unlink node", "O(1)", "Doubly linked list"),
}


def tag(t):
    t.uid = next(UIDS)
    return t


def reset():
    STATE["p"] = Playlist([tag(t) for t in sample_a()], sort_field="released")


def as_json(t):
    return {"uid": t.uid, "title": t.title, "artist": t.artist, "album": t.album, "genre": t.genre,
            "released": t.released, "year": t.released[:4], "length": t.length, "len": mmss(t.length)}


def snapshot():
    p = STATE["p"]
    c = p.count()
    return {"tracks": [as_json(t) for t in p.tracks], "sort_field": p.sort_field,
            "linked": [n.uid for n in p.linked_order()],
            "counts": {"tracks": c["tracks"], "duration": c["duration"], "genres": c["per_genre"], "artists": c["per_artist"]}}


def op(name, started, **detail):
    algo, cost, structure = ALGO[name]
    return {"name": name, "algorithm": algo, "cost": cost, "structure": structure,
            "micros": round((time.perf_counter() - started) * 1e6, 1), **detail}


def neighbours(p, i):
    before = p.tracks[i - 1].title if i > 0 else None
    after = p.tracks[i + 1].title if i + 1 < len(p.tracks) else None
    return before, after


def handle(path, body):
    p = STATE["p"]
    if path == "/api/state":
        return {"state": snapshot()}
    if path == "/api/reset":
        reset()
        return {"state": snapshot()}

    if path == "/api/sort":
        field = body.get("field")
        t0 = time.perf_counter()
        p.sort_by(field)
        return {"state": snapshot(), "op": op("sort", t0, field=field)}

    if path == "/api/search":
        field, q = body.get("field", "title"), str(body.get("q", "")).strip()
        if field not in FIELDS:
            raise ValueError(f"unknown field {field!r}")
        if not q:
            raise ValueError("type something to search for")
        resorted = field != p.sort_field
        t0 = time.perf_counter()
        hits = p.search(field, q)
        o = op("search", t0, field=field, q=q, resorted=resorted, hits=[t.uid for t in hits])
        # replay the lower-bound steps on the (now sorted) list so the page can draw them
        trace = []
        lower_bound(p.tracks, q.casefold(), lambda t: field_value(t, field), trace)
        o["trace"] = [{"lo": lo, "hi": hi, "mid": mid, "title": p.tracks[mid].title,
                       "value": str(getattr(p.tracks[mid], field))} for lo, hi, mid in trace]
        o["mode"] = "exact" if hits and all(field_value(t, field) == q.casefold() for t in hits) else ("prefix" if hits else "none")
        return {"state": snapshot(), "op": o}

    if path == "/api/group":
        field = body.get("field", "genre")
        if field not in ("genre", "artist", "album"):
            raise ValueError("group by genre, artist or album")
        t0 = time.perf_counter()
        buckets = p.group(field)
        return {"state": snapshot(), "op": op("group", t0, field=field,
                buckets=[{"key": k, "uids": [t.uid for t in v]} for k, v in buckets.items()])}

    if path == "/api/count":
        t0 = time.perf_counter()
        c = p.count()
        return {"state": snapshot(), "op": op("count", t0, tracks=c["tracks"], duration=c["duration"])}

    if path == "/api/insert":
        if not str(body.get("title", "")).strip():
            raise ValueError("a track needs a title")
        try:
            length = secs(str(body.get("length", "")).strip())
        except (ValueError, AttributeError):
            raise ValueError("length must look like 3:45")
        released = str(body.get("released", "")).strip()
        if len(released) == 4 and released.isdigit():
            released += "-01-01"
        t = tag(Track(str(body.get("title", "")).strip(), str(body.get("artist", "")).strip(),
                      str(body.get("album", "")).strip() or None, str(body.get("genre", "")).strip(), released, length))
        t0 = time.perf_counter()
        i = p.insert(t)
        o = op("insert", t0, index=i, uid=t.uid)
        o["before"], o["after"] = neighbours(p, i)
        return {"state": snapshot(), "op": o}

    if path == "/api/delete":
        i = body.get("index")
        before, after = neighbours(p, i) if isinstance(i, int) and 0 <= i < len(p) else (None, None)
        t0 = time.perf_counter()
        t = p.delete(i)
        return {"state": snapshot(), "op": op("delete", t0, index=i, title=t.title, before=before, after=after)}

    raise LookupError(path)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=STATIC, **k)

    def _api(self, body):
        try:
            with LOCK:
                out = handle(self.path.split("?")[0], body)
                STATE["p"].check()               # every response proves the three structures still agree
            code = 200
        except LookupError:
            out, code = {"error": "unknown endpoint"}, 404
        except (ValueError, IndexError, TypeError) as e:
            out, code = {"error": str(e).strip("'")}, 400
        data = json.dumps(out).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._api({})
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            body = None
        if not isinstance(body, dict):
            return self._api_error("send a JSON object")
        return self._api(body)

    def _api_error(self, msg):
        data = json.dumps({"error": msg}).encode()
        self.send_response(400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    reset()
    port = int(os.environ.get("PORT", 8000))
    print(f"Smart Music Playlist Manager on http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
