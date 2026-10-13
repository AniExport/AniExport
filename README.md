# AniExport

> **Fast, zero-dependency plain-text anime list converter and exporter for MyAnimeList & AniList.**

Turn any plain text list of anime titles (one per line, no numbering or strict formatting required) into official MyAnimeList-compliant XML (`.xml`) and Gzip (`.xml.gz`) files, fully ready for one-click import into both **MyAnimeList** and **AniList**.

---

## ⚡ Features

- **Universal XML & Gzip Export:** Generates official MyAnimeList import files (`myanimelist_export.xml` & `myanimelist_export.xml.gz`) natively accepted by:
  - **MyAnimeList:** [myanimelist.net/import.php](https://myanimelist.net/import.php)
  - **AniList:** [anilist.co/settings/import](https://anilist.co/settings/import) *(AniList imports MyAnimeList XML files matching by MAL IDs)*.
- **Intelligent Title Resolution:** Automatically strips numbering, bullets, and punctuation, resolving each title against the official AniList GraphQL database to retrieve canonical English and Romaji titles, episode counts, media formats (TV, Movie, OVA, ONA, Special), and database IDs.
- **Auto-Expand Sequels & Movies:** Optional toggle recursively discovers subsequent TV seasons and canon sequel movies (e.g., entering *KonoSuba* automatically retrieves Season 1, Season 2, the *Legend of Crimson* movie, and Season 3).
- **Interactive Web Dashboard:** A sleek, dark-mode local web interface running on `localhost:5000` with zero layout shift, real-time Server-Sent Events (SSE) live progress bar, and immediate downloads.
- **Exclusion Checkboxes:** Select or deselect any individual series, movie, or season before exporting. Features a master Select-All / Deselect-All header toggle with tri-state indeterminate support (`-`).
- **Live Background Sync:** Unchecking entries or changing scores/statuses immediately recalculates stats and regenerates the `.xml` and `.xml.gz` files on disk without re-fetching from the network.
- **Dual Database Links:** The table displays both **MAL ID** (linking to MyAnimeList) and **AniList ID** (linking to AniList) for every entry.
- **Instant Search & Filter:** Quickly filter through large lists by English title, original title, MAL ID, or AniList ID.
- **Clean In-Memory Architecture:** No persistent disk cache (`anime_cache.json`) cluttering your filesystem. The app starts fresh every session.
- **Zero External Dependencies:** Built 100% on the Python standard library. No `pip install` required!

---

## 📋 Requirements

- **Python 3.9+** (Compatible with Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14+)
- An active internet connection for querying the AniList GraphQL API.

---

## 🚀 Getting Started

### 1. Launch the Web GUI (Recommended)

Simply run `gui.py` using your preferred Python runner:

```bash
# Using standard Python
python gui.py

# Or using uv
uv run gui.py
```

Your default browser will automatically open:
```text
http://127.0.0.1:5000
```

#### GUI Options
```bash
python gui.py --help

  -p, --port PORT    Local port for web server (default: 5000)
  --no-browser       Do not automatically launch the browser
```

---

### 2. Command-Line Interface (CLI)

You can also run AniExport directly from the terminal without opening the browser:

```bash
# Basic usage with a text file
python generate_mal_xml.py anime_list.txt

# Automatically include sequels and canonical movies
python generate_mal_xml.py anime_list.txt --expand-sequels

# Specify status (Completed, Watching, Plan to Watch, On-Hold, Dropped) and score (0-10)
python generate_mal_xml.py anime_list.txt --status Watching --score 8

# Specify custom output paths
python generate_mal_xml.py anime_list.txt -o my_export.xml -z my_export.xml.gz
```

---

## 📝 Input Format

You can paste or supply any unformatted list of anime titles. The normalizer automatically cleans up leading numbers, punctuation, quotes, and whitespace:

```text
Sousou no Frieren
Attack on Titan
Solo Leveling
1. Dandadan
2) Chainsaw Man
- KonoSuba
Jujutsu Kaisen
```

---

## 📥 How to Import Your Export

Once AniExport generates your export files, you can import them into either platform:

### Importing to MyAnimeList
1. Go to [myanimelist.net/import.php](https://myanimelist.net/import.php) (log in if prompted).
2. Select **MyAnimeList Import** under the import type.
3. Choose the generated `myanimelist_export.xml` or compressed `myanimelist_export.xml.gz` file.
4. Click **Import**.

### Importing to AniList
1. Go to [anilist.co/settings/import](https://anilist.co/settings/import) (log in if prompted).
2. Under **Import from MyAnimeList**, click **Choose File** and select `myanimelist_export.xml` or `myanimelist_export.xml.gz`.
3. Click **Import**. AniList matches each entry using the official MAL IDs included in the XML.

---

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**.

- **You are free to:** Share, copy, redistribute, modify, and adapt the code.
- **Under the conditions that:**
  - **NonCommercial:** You may NOT sell, monetize, or use this project or derivative works for commercial purposes.
  - **Attribution:** You must give appropriate credit to the original author (`trism`).
  - **ShareAlike:** Any modifications or derived works must be distributed under the exact same non-commercial license.

See the [LICENSE](LICENSE) file for the full license text.

---

## ☕ Support

If AniExport saved you time or was helpful to you, consider supporting the project:

[Support trism ❤️](https://ko-fi.com/trism)
