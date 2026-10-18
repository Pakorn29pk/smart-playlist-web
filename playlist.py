"""Smart Music Playlist Manager: the data structures and algorithms.

Same code as the Colab notebook (SmartMusicPlaylistManager.ipynb), as a module the web app imports.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(eq=False)          # eq=False: two tracks are only "the same" if they are the same object
class Track:
    title: str
    artist: str
    album: Optional[str]
    genre: str
    released: str             # ISO date "YYYY-MM-DD" sorts correctly as text
    length: int               # seconds


def mmss(seconds):
    return f"{seconds // 60}:{seconds % 60:02d}"


def secs(text):
    m, s = text.split(":")
    return int(m) * 60 + int(s)


def sample_a():
    rows = [
        ("Take Five", "The Dave Brubeck Quartet", "Time Out", "Jazz", "1959-09-21", "5:28"),
        ("Bohemian Rhapsody", "Queen", "A Night at the Opera", "Rock", "1975-10-31", "5:55"),
        ("Hotel California", "Eagles", "Hotel California", "Rock", "1977-02-22", "6:30"),
        ("Billie Jean", "Michael Jackson", "Thriller", "Pop", "1983-01-02", "4:57"),
        ("Smells Like Teen Spirit", "Nirvana", "Nevermind", "Rock", "1991-09-10", "5:01"),
        ("One More Time", "Daft Punk", "Discovery", "Electronic", "2000-11-13", "5:20"),
        ("Lose Yourself", "Eminem", "8 Mile", "Hip-hop", "2002-10-28", "5:20"),
        ("Rolling in the Deep", "Adele", "21", "Soul", "2010-11-29", "3:48"),
        ("Get Lucky", "Daft Punk", "Random Access Memories", "Disco", "2013-04-19", "6:09"),
        ("Shape of You", "Ed Sheeran", "Divide", "Pop", "2017-01-06", "3:54"),
        ("Blinding Lights", "The Weeknd", "After Hours", "Pop", "2019-11-29", "3:22"),
        ("Dynamite", "BTS", "Be", "Pop", "2020-08-21", "3:19"),
    ]
    return [Track(t, a, al, g, r, secs(l)) for t, a, al, g, r, l in rows]


# ---------- sorting ----------
FIELDS = ["title", "artist", "album", "genre", "released", "length"]
FALLTHROUGH = ["genre", "artist", "released", "title"]


def field_value(track, field):
    v = getattr(track, field)
    if v is None:
        return ""
    return v.casefold() if isinstance(v, str) else v


def make_key(field):
    if field not in FIELDS:
        raise ValueError(f"unknown field {field!r}; choose one of {FIELDS}")
    chain = [field] + [f for f in FALLTHROUGH if f != field]
    return lambda t: tuple(field_value(t, f) for f in chain)


def merge_sort(items, key):
    """Stable top-down merge sort. O(n log n) in every case. Returns a new list."""
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left, right = merge_sort(items[:mid], key), merge_sort(items[mid:], key)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if key(right[j]) < key(left[i]):    # strict "<": on a tie the LEFT item wins -> stable
            out.append(right[j]); j += 1
        else:
            out.append(left[i]); i += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out


def insertion_sort(items, key):
    """Stable insertion sort. O(n) on already-sorted input, O(n^2) otherwise."""
    out = list(items)
    for i in range(1, len(out)):
        cur, k, j = out[i], key(out[i]), i - 1
        while j >= 0 and key(out[j]) > k:
            out[j + 1] = out[j]; j -= 1
        out[j + 1] = cur
    return out


# ---------- searching ----------
def lower_bound(items, value, keyf, trace=None):
    """First index whose key >= value. O(log n). `trace` collects (lo, hi, mid) per step."""
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if trace is not None:
            trace.append((lo, hi, mid))
        if keyf(items[mid]) < value:
            lo = mid + 1
        else:
            hi = mid
    return lo


def upper_bound(items, value, keyf):
    """First index whose key > value. O(log n)."""
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi) // 2
        if keyf(items[mid]) <= value:
            lo = mid + 1
        else:
            hi = mid
    return lo


def linear_search(items, field, value):
    """The obvious way: look at every track. O(n)."""
    value = value.casefold() if isinstance(value, str) else value
    return [t for t in items if field_value(t, field) == value]


def binary_search(sorted_items, field, value):
    """All tracks whose `field` equals value. sorted_items must be sorted by `field` first."""
    value = value.casefold() if isinstance(value, str) else value
    keyf = lambda t: field_value(t, field)
    return sorted_items[lower_bound(sorted_items, value, keyf):upper_bound(sorted_items, value, keyf)]


# ---------- the playlist: array + doubly linked list + hash maps ----------
class Node:
    __slots__ = ("track", "prev", "next")

    def __init__(self, track=None):
        self.track, self.prev, self.next = track, None, None


class Playlist:
    def __init__(self, tracks=(), sort_field="released"):
        self.head, self.tail = Node(), Node()           # sentinels: no empty-list special cases
        self.head.next, self.tail.prev = self.tail, self.head
        self.node_of = {}                               # id(track) -> Node, so delete finds the node in O(1)
        self.genre_count, self.artist_count = {}, {}
        self.total_seconds = 0
        self.tracks = []
        for t in tracks:
            self._validate(t)
            self.tracks.append(t)
            self._count(t, +1)
        self.sort_by(sort_field)

    @staticmethod
    def _validate(t):
        if not isinstance(t, Track):
            raise TypeError("only Track objects can be added")
        if not t.title or not t.title.strip():
            raise ValueError("a track needs a title")
        if not isinstance(t.length, int) or t.length < 0:
            raise ValueError(f"invalid length for {t.title!r}: {t.length}")

    def _count(self, t, delta):
        for table, k in ((self.genre_count, t.genre or "(none)"), (self.artist_count, t.artist or "(unknown)")):
            table[k] = table.get(k, 0) + delta
            if table[k] == 0:
                del table[k]
        self.total_seconds += delta * t.length

    def _splice_before(self, node, new):
        new.prev, new.next = node.prev, node
        node.prev.next = new
        node.prev = new

    def _unlink(self, node):
        node.prev.next, node.next.prev = node.next, node.prev
        node.prev = node.next = None

    def _rebuild_links(self):
        self.head.next, self.tail.prev = self.tail, self.head
        self.node_of = {}
        for t in self.tracks:
            n = Node(t)
            self._splice_before(self.tail, n)
            self.node_of[id(t)] = n

    def linked_order(self):
        out, n = [], self.head.next
        while n is not self.tail:
            out.append(n.track); n = n.next
        return out

    def __len__(self):
        return len(self.tracks)

    # 1. sort
    def sort_by(self, field):
        self.key = make_key(field)
        self.sort_field = field
        self.tracks = merge_sort(self.tracks, self.key)
        self._rebuild_links()
        return self.tracks

    # 2. search
    def search(self, field, value):
        if field != self.sort_field:
            self.sort_by(field)                 # sorting is the precondition for binary search
        hits = binary_search(self.tracks, field, value)
        if not hits and field == "title":       # exact match failed -> prefix match
            p = value.casefold()
            keyf = lambda t: field_value(t, "title")
            i = lower_bound(self.tracks, p, keyf)
            while i < len(self.tracks) and keyf(self.tracks[i]).startswith(p):
                hits.append(self.tracks[i]); i += 1
        return hits

    # 3. group
    def group(self, field="genre"):
        buckets = {}
        for t in self.tracks:                   # one pass, keeps the user's order inside each bucket
            buckets.setdefault(getattr(t, field) or "(none)", []).append(t)
        return buckets

    # 4. count
    def count(self):
        return {"tracks": len(self.tracks), "duration": mmss(self.total_seconds),
                "per_genre": dict(self.genre_count), "per_artist": dict(self.artist_count)}

    # 5. insert
    def insert(self, t):
        self._validate(t)
        if id(t) in self.node_of:
            raise ValueError("that track object is already in the playlist")
        i = upper_bound(self.tracks, self.key(t), self.key)       # O(log n): slot after any equal keys
        after = self.node_of[id(self.tracks[i])] if i < len(self.tracks) else self.tail
        node = Node(t)
        self._splice_before(after, node)                           # O(1): two pointers rewritten
        self.node_of[id(t)] = node
        self.tracks.insert(i, t)
        self._count(t, +1)
        return i

    # 6. delete
    def delete(self, index):
        if not isinstance(index, int):
            raise IndexError(f"position must be a whole number, got {index!r}")
        if not 0 <= index < len(self.tracks):
            raise IndexError(f"no track at position {index}; playlist has {len(self.tracks)} tracks")
        t = self.tracks.pop(index)
        self._unlink(self.node_of.pop(id(t)))                      # O(1)
        self._count(t, -1)
        return t

    def check(self):
        """Invariants: array sorted, linked list == array, counters match a full recount."""
        assert all(self.key(a) <= self.key(b) for a, b in zip(self.tracks, self.tracks[1:])), "array out of order"
        assert self.linked_order() == self.tracks, "linked list out of sync"
        assert self.total_seconds == sum(t.length for t in self.tracks), "duration counter wrong"
        assert sum(self.genre_count.values()) == len(self.tracks), "genre counter wrong"
        return True
