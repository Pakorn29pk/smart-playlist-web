# Smart Music Playlist Manager (web)

The web version of our Data Structures and Algorithms mini-project (KMITL, Robotics and AI Engineering).
Same Python code as the Colab notebook, with a playlist app on top so each operation can be shown live.

| Operation | Algorithm | Cost | Data structure |
|---|---|---|---|
| Sort | Merge sort (stable, multi-key) | O(n log n) | Dynamic array |
| Search | Binary search (exact, then prefix) | O(log n) | Dynamic array |
| Group | Hash buckets, one pass | O(n + k) | Hash map |
| Count | Running counters | O(1) | Hash map |
| Insert | Binary search + splice | O(log n) + O(1) | Doubly linked list |
| Delete | Unlink node | O(1) | Doubly linked list |

## Run it

With Docker (nothing else to install):

```bash
git clone <this repository's URL>
cd smart-playlist-web
docker compose up --build
```

Then open http://localhost:8000. Stop it with `Ctrl+C`.

If port 8000 is already used on your computer, pick another one: `PORT=8080 docker compose up --build` (PowerShell: `$env:PORT=8080; docker compose up --build`), then open http://localhost:8080.

Without Docker (Python 3.10 or newer, no packages needed):

```bash
python server.py
```

## Using it

- **Sort:** the chips under the playlist title (Title, Artist, Album, Genre, Released, Length).
- **Search:** the bar at the top. Pick the field on the right. A title with no exact match falls back to a prefix match ("bl" finds Blinding Lights).
- **Group / Count:** the tiles on the right. "Show list" goes back to the flat playlist.
- **Insert:** the "Add a track" form. Year can be just `2013`, length like `4:08`.
- **Delete:** the minus button at the end of a row.
- **Sample A · B · C · D:** loads a test sample from `sample_data/` (A real playlist, B duplicate keys, C already ordered, D broken data). The circular arrow reloads the current sample.
- **Speed race:** times linear vs binary search, and append + re-sort vs search + splice, on 50,000 generated tracks.

The panel on the right shows what each algorithm just did: the binary-search steps, the buckets, the nodes on each side of an insert or delete, and how long it took.

## Files

| File | What it is |
|---|---|
| `playlist.py` | The data structures and algorithms (same as the notebook) |
| `server.py` | A small web server and JSON API, Python standard library only |
| `static/` | The page: `index.html`, `app.css`, `app.js` |
| `sample_data/` | Test samples A–D as CSV files |
| `test_playlist.py` | Tests for the algorithms and every endpoint: `python -m unittest` |

## Recording tips for the video

- Full screen the browser (F11) at 1920×1080 before recording.
- **Record in the light theme** so the screen matches the video's light stage: add `theme=light` to the address, e.g. `http://localhost:8000/?theme=light` or `http://localhost:8000/?theme=light&run=sample:B,sort:length`.
- Press the reload arrow (next to the samples) before each take so everyone starts from the same tracks.
- To open the page already in the state your take needs, add steps to the address, separated by commas:
  - `http://localhost:8000/?run=sample:B,sort:length`
  - `http://localhost:8000/?run=sample:D,search:title:hotel%20california`
  - `http://localhost:8000/?run=group:genre` · `?run=count` · `?run=race`

## Team

Pakorn Dee-Udomvongsa · Pattanaseth Adirekkiat · Pongsicha Seesavat
