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
