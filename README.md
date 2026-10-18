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
- **Reset playlist:** puts the 12 sample tracks back.

The panel on the right shows what each algorithm just did: the binary-search steps, the buckets, the nodes on each side of an insert or delete, and how long it took.

## Files

| File | What it is |
|---|---|
| `playlist.py` | The data structures and algorithms (same as the notebook) |
| `server.py` | A small web server and JSON API, Python standard library only |
| `static/` | The page: `index.html`, `app.css`, `app.js` |
| `test_playlist.py` | Tests for the algorithms and every endpoint: `python -m unittest` |

## Recording tips for the video

- Full screen the browser (F11) at 1920×1080 before recording.
- Press **Reset playlist** before each take so everyone starts from the same 12 tracks.
- To open the page already searching, add it to the address: `http://localhost:8000/?search=lose%20yourself&field=title`.

## Team

Pakorn Dee-Udomvongsa · Pattanaseth Adirekkiat · Pongsicha Seesavat
