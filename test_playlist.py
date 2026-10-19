"""Run: python -m unittest   (checks the algorithms and every web endpoint)"""
import random
import unittest

import server
from playlist import Playlist, Track, sample_a


class Algorithms(unittest.TestCase):
    def test_sample_counts_and_stability(self):
        p = Playlist(sample_a(), "length")
        self.assertEqual(p.count()["duration"], "59:03")
        ties = [t.title for t in p.tracks if t.length == 320]
        self.assertEqual(ties, ["One More Time", "Lose Yourself"])

    def test_random_edits_keep_structures_in_sync(self):
        rng, p = random.Random(7), Playlist(sample_a(), "artist")
        for step in range(1000):
            if len(p) and rng.random() < 0.45:
                p.delete(rng.randrange(len(p)))
            else:
                p.insert(Track(f"T{step}", rng.choice("ABC"), None, "Pop", f"{rng.randint(1950, 2025)}-01-01", rng.randint(0, 600)))
            p.check()


class Samples(unittest.TestCase):
    """The four test samples A–D, one check per operation shown in the video."""

    def load(self, k, field):
        return Playlist(server.load_csv("sample_data/" + server.SAMPLES[k][0]), field)

    def test_a_real_playlist(self):
        a = self.load("A", "released")
        self.assertEqual({k: len(v) for k, v in a.group("genre").items()}["Pop"], 4)
        self.assertEqual(len(a.group("genre")), 7)

    def test_b_duplicate_keys(self):
        b = self.load("B", "length")
        i = b.insert(Track("Zzz Tie", "Daft Punk", None, "Electronic", "2000-11-13", 320))
        self.assertEqual([t.title for t in b.tracks[i - 1:i + 2]], ["One More Time", "Zzz Tie", "Lose Yourself"])
        self.assertEqual([t.title for t in b.group("genre")["Pop"]], ["Dynamite", "Blinding Lights", "Shape of You", "Billie Jean"])
        b.check()

    def test_c_already_ordered(self):
        rows = server.load_csv("sample_data/" + server.SAMPLES["C"][0])
        c = Playlist(rows, "released")
        self.assertEqual(c.tracks, rows)                       # sorting changes nothing
        c.insert(Track("New", "X", None, "Pop", "2005-01-01", 200))
        c.check()

    def test_d_broken_data(self):
        d = self.load("D", "album")
        self.assertIsNone(d.tracks[0].album)                   # missing album sorts first
        self.assertEqual(d.count()["per_artist"]["(unknown)"], 1)
        self.assertEqual(len(d.search("title", "hotel california")), 2)
        for bad in (-1, 99, "3"):
            with self.assertRaises(IndexError):
                d.delete(bad)


class Endpoints(unittest.TestCase):
    def setUp(self):
        server.reset()

    def test_every_operation(self):
        self.assertEqual(server.handle("/api/sort", {"field": "title"})["state"]["tracks"][0]["title"], "Billie Jean")
        out = server.handle("/api/search", {"field": "title", "q": "lose yourself"})
        self.assertEqual(len(out["op"]["hits"]), 1)
        self.assertEqual(len(out["op"]["trace"]), 3)          # the 3 steps said in the video
        self.assertEqual(server.handle("/api/search", {"field": "title", "q": "bl"})["op"]["mode"], "prefix")
        buckets = {b["key"]: len(b["uids"]) for b in server.handle("/api/group", {"field": "genre"})["op"]["buckets"]}
        self.assertEqual((buckets["Pop"], buckets["Rock"], len(buckets)), (4, 3, 7))
        server.handle("/api/sort", {"field": "released"})
        ins = server.handle("/api/insert", {"title": "Get Lucky (Radio Edit)", "artist": "Daft Punk", "album": "", "genre": "Disco", "released": "2013-04-19", "length": "4:08"})
        self.assertEqual((ins["op"]["index"], ins["op"]["before"]), (9, "Get Lucky"))
        gone = server.handle("/api/delete", {"index": 0})
        self.assertEqual((gone["op"]["title"], gone["state"]["counts"]["duration"]), ("Take Five", "57:43"))
        server.STATE["p"].check()

    def test_bad_input_is_rejected(self):
        for path, body in [("/api/delete", {"index": 99}), ("/api/delete", {"index": "3"}), ("/api/sort", {"field": "colour"}),
                           ("/api/insert", {"title": "", "length": "3:00", "released": "2000"}), ("/api/insert", {"title": "x", "length": "abc"}),
                           ("/api/search", {"field": "title", "q": "  "})]:
            with self.assertRaises((ValueError, IndexError), msg=path):
                server.handle(path, body)


if __name__ == "__main__":
    unittest.main()
