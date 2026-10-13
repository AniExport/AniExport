"""
XML Generator
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


ANILIST_API_URL = "https://graphql.anilist.co"

ANILIST_SEARCH_QUERY = """
query ($search: String) {
  Media (search: $search, type: ANIME) {
    id
    idMal
    title {
      english
      romaji
    }
    format
    episodes
    status
    relations {
      edges {
        relationType
        node {
          id
          idMal
          title {
            english
            romaji
          }
          format
          episodes
          type
          status
        }
      }
    }
  }
}
"""

ANILIST_BY_ID_QUERY = """
query ($id: Int) {
  Media (id: $id, type: ANIME) {
    id
    idMal
    title {
      english
      romaji
    }
    format
    episodes
    status
    relations {
      edges {
        relationType
        node {
          id
          idMal
          title {
            english
            romaji
          }
          format
          episodes
          type
          status
        }
      }
    }
  }
}
"""

FORMAT_MAP = {
    "TV": "TV",
    "TV_SHORT": "TV",
    "MOVIE": "Movie",
    "SPECIAL": "Special",
    "OVA": "OVA",
    "ONA": "ONA",
    "MUSIC": "Music",
}


def sanitize_title_line(line: str) -> Optional[str]:
    """
    Cleans a line from an anime text file:
    - Removes leading numbering or bullet points (e.g., '1. ', '1) ', '- ')
    - Removes wrapping quotation marks and extra whitespace
    - Ignores comment lines starting with '#'
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    # Remove leading numbers/bullets if any (e.g., '1. ', '1- ', '1) ', '- ')
    cleaned = re.sub(r"^\s*(?:\d+[\.\-\)]|[-*•])\s*", "", stripped).strip()

    # Remove surrounding double/single quotes if present
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    return cleaned if cleaned else None


def load_titles_from_txt(file_path: Path) -> List[str]:
    """
    Reads a text file with one anime title per line (no numbering required).
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Anime list file not found: {file_path}")

    titles: List[str] = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            cleaned = sanitize_title_line(line)
            if cleaned:
                titles.append(cleaned)
    return titles


def _parse_media_node(media: Dict[str, Any], fallback_title: str = "") -> Dict[str, Any]:
    titles = media.get("title") or {}
    official_title = titles.get("english") or titles.get("romaji") or fallback_title
    raw_format = (media.get("format") or "TV").upper()
    series_type = FORMAT_MAP.get(raw_format, "TV")
    mal_id = int(media.get("idMal") or 0)
    anilist_id = int(media.get("id") or 0)
    eps = int(media.get("episodes") or 12)
    return {
        "id": mal_id,
        "anilist_id": anilist_id,
        "title": official_title,
        "type": series_type,
        "episodes": eps,
    }


def _execute_anilist_request(query: str, variables: Dict[str, Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "MALAnimeExporter/2.0",
    }

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(ANILIST_API_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("data", {}).get("Media")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(attempt * 1.5)
                continue
            elif e.code == 404:
                return None
            else:
                if attempt == max_retries:
                    return None
                time.sleep(1.0)
        except Exception:
            if attempt == max_retries:
                return None
            time.sleep(1.0)

    return None


def fetch_anime_info_online(
    title: str,
    max_retries: int = 3,
    expand_sequels: bool = False,
) -> List[Dict[str, Any]]:
    """
    Queries AniList GraphQL API to fetch the official English title, MAL ID,
    format (type), and total episode count for the given anime title.
    If expand_sequels is True, automatically traverses canonical sequels and sequel movies.
    """
    root_media = _execute_anilist_request(ANILIST_SEARCH_QUERY, {"search": title}, max_retries=max_retries)
    if not root_media:
        return []

    root_entry = _parse_media_node(root_media, fallback_title=title)
    results: List[Dict[str, Any]] = [root_entry]

    if not expand_sequels:
        return results

    # Traverse SEQUEL chain (subsequent seasons and canon sequel movies)
    visited_ids = {root_media.get("id")}
    current_media = root_media

    for _ in range(15):  # Limit chain traversal to avoid potential loops
        sequel_node = None
        for edge in current_media.get("relations", {}).get("edges", []):
            if edge.get("relationType") == "SEQUEL":
                candidate = edge.get("node", {})
                if candidate.get("type") == "ANIME" and candidate.get("id") not in visited_ids:
                    # Ignore unreleased/unannounced placeholders without MAL ID
                    if candidate.get("status") != "NOT_YET_RELEASED" and candidate.get("idMal"):
                        sequel_node = candidate
                        break

        if not sequel_node:
            break

        time.sleep(0.3)
        nxt_media = _execute_anilist_request(ANILIST_BY_ID_QUERY, {"id": sequel_node["id"]}, max_retries=max_retries)
        if not nxt_media:
            break

        visited_ids.add(nxt_media.get("id"))
        results.append(_parse_media_node(nxt_media, fallback_title=title))
        current_media = nxt_media

    return results


def resolve_anime_entries(
    title: str,
    session_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    expand_sequels: bool = False,
) -> List[Dict[str, Any]]:
    """
    Resolves an anime title to official MAL details.
    If expand_sequels is True, returns all canonical sequels and sequel movies.
    Uses an in-memory session cache only for duplicate titles during execution.
    Does NOT write any cache to disk.
    """
    cache = session_cache if session_cache is not None else {}
    key = f"{title.strip().lower()}:{'expand' if expand_sequels else 'single'}"
    if key in cache:
        return [dict(e) for e in cache[key]]

    online_info = fetch_anime_info_online(title, expand_sequels=expand_sequels)
    time.sleep(0.2)

    if online_info:
        entries = online_info
    else:
        entries = [{
            "id": 0,
            "anilist_id": 0,
            "title": title,
            "type": "TV",
            "episodes": 12,
        }]

    cache[key] = entries
    return entries


def deduplicate_entries(entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates entries preserving first occurrence order.
    Deduplicates by ID if non-zero, otherwise by title.
    """
    seen = set()
    unique: List[Dict[str, Any]] = []
    for item in entries:
        anime_id = item.get("id", 0)
        key = anime_id if anime_id != 0 else item.get("title", "").strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def build_mal_xml(
    entries: Sequence[Dict[str, Any]],
    default_status: str = "Completed",
    default_score: int = 0,
) -> str:
    """
    Builds the official XML string conforming to MyAnimeList import specifications.
    """
    total_anime = len(entries)
    completed_count = sum(1 for e in entries if e.get("status", default_status).lower() == "completed")
    watching_count = sum(1 for e in entries if e.get("status", default_status).lower() == "watching")
    onhold_count = sum(1 for e in entries if e.get("status", default_status).lower() in ("on-hold", "onhold"))
    dropped_count = sum(1 for e in entries if e.get("status", default_status).lower() == "dropped")
    plantowatch_count = sum(1 for e in entries if e.get("status", default_status).lower() in ("plan to watch", "plantowatch"))

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<!--',
        '  Created by XML Export Feature',
        '  Program: MyAnimeList.net',
        f'  Entry count: {total_anime}',
        '-->',
        '<myanimelist>',
        '  <myinfo>',
        '    <user_id></user_id>',
        '    <user_name></user_name>',
        '    <user_export_type>1</user_export_type>',
        f'    <user_total_anime>{total_anime}</user_total_anime>',
        f'    <user_total_watching>{watching_count}</user_total_watching>',
        f'    <user_total_completed>{completed_count}</user_total_completed>',
        f'    <user_total_onhold>{onhold_count}</user_total_onhold>',
        f'    <user_total_dropped>{dropped_count}</user_total_dropped>',
        f'    <user_total_plantowatch>{plantowatch_count}</user_total_plantowatch>',
        '  </myinfo>',
    ]

    for entry in entries:
        anime_id = entry.get("id", 0)
        title = entry.get("title", "")
        series_type = entry.get("type", "TV")
        eps = entry.get("episodes", 0)
        watched_eps = entry.get("my_watched_episodes", eps)
        status = entry.get("status", default_status)
        score = entry.get("score", default_score)
        comments = entry.get("comments", "")
        tags = entry.get("tags", "")

        lines.extend([
            '  <anime>',
            f'    <series_animedb_id>{anime_id}</series_animedb_id>',
            f'    <series_title><![CDATA[{title}]]></series_title>',
            f'    <series_type>{series_type}</series_type>',
            f'    <series_episodes>{eps}</series_episodes>',
            f'    <my_watched_episodes>{watched_eps}</my_watched_episodes>',
            '    <my_start_date>0000-00-00</my_start_date>',
            '    <my_finish_date>0000-00-00</my_finish_date>',
            '    <my_rated></my_rated>',
            f'    <my_score>{score}</my_score>',
            '    <my_storage></my_storage>',
            f'    <my_status>{status}</my_status>',
            f'    <my_comments><![CDATA[{comments}]]></my_comments>',
            '    <my_times_watched>1</my_times_watched>',
            '    <my_rewatch_value></my_rewatch_value>',
            '    <my_priority>LOW</my_priority>',
            f'    <my_tags><![CDATA[{tags}]]></my_tags>',
            '    <my_rewatching>0</my_rewatching>',
            '    <my_rewatching_ep>0</my_rewatching_ep>',
            '    <update_on_import>1</update_on_import>',
            '  </anime>',
        ])

    lines.append('</myanimelist>')
    lines.append('')
    return '\r\n'.join(lines)


def process_anime_list(
    titles: Sequence[str],
    output_xml: Optional[Path] = None,
    output_gz: Optional[Path] = None,
    status: str = "Completed",
    score: int = 0,
    expand_sequels: bool = False,
) -> tuple[Path, Path, int]:
    """
    Normalizes anime titles to official English MAL metadata,
    writes the XML and GZ files, and validates output.
    Uses in-memory session resolution without saving cache to disk.
    If expand_sequels is True, automatically includes subsequent seasons and sequel movies.
    """
    base_dir = Path.cwd()
    target_xml = output_xml if output_xml else base_dir / "myanimelist_export.xml"
    target_gz = output_gz if output_gz else base_dir / "myanimelist_export.xml.gz"

    session_cache: Dict[str, List[Dict[str, Any]]] = {}
    resolved_entries: List[Dict[str, Any]] = []

    total_titles = len(titles)
    print(f"[*] Processing {total_titles} anime titles (expand_sequels={expand_sequels})...")

    for idx, raw_title in enumerate(titles, start=1):
        entries = resolve_anime_entries(raw_title, session_cache=session_cache, expand_sequels=expand_sequels)
        for resolved in entries:
            resolved_entries.append(resolved)
            mal_id = resolved["id"]
            norm_title = resolved["title"]
            eps = resolved["episodes"]
            stype = resolved["type"]

            if raw_title.lower() != norm_title.lower():
                print(f"  [{idx}/{total_titles}] '{raw_title}' -> '{norm_title}' (MAL ID: {mal_id}, {stype}, {eps} eps)")
            else:
                print(f"  [{idx}/{total_titles}] '{norm_title}' (MAL ID: {mal_id}, {stype}, {eps} eps)")

    # Deduplicate
    unique_entries = deduplicate_entries(resolved_entries)
    print(f"\n[*] Total unique anime entries: {len(unique_entries)}")

    # Build XML
    xml_content = build_mal_xml(unique_entries, default_status=status, default_score=score)
    xml_bytes = xml_content.encode("utf-8")

    # Save XML without BOM
    target_xml.write_bytes(xml_bytes)
    print(f"[+] Successfully generated: {target_xml.resolve()}")

    # Save GZ compressed file
    with open(target_gz, "wb") as f_out:
        f_out.write(gzip.compress(xml_bytes, compresslevel=9))
    print(f"[+] Successfully generated GZ: {target_gz.resolve()}")

    # Validate XML
    tree = ET.parse(target_xml)
    root = tree.getroot()
    anime_nodes = len(root.findall("anime"))
    print(f"[OK] XML validation passed! Total parsed anime nodes: {anime_nodes}\n")

    return target_xml, target_gz, anime_nodes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a plain text list of anime titles (one per line, without numbering) into a MyAnimeList compliant XML export."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to the text file containing anime titles (one per line, defaults to notes.txt or animes.txt).",
    )
    parser.add_argument(
        "-i", "--input-file",
        dest="input_flag",
        type=str,
        default=None,
        help="Alternative flag to specify the input text file.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Path for the generated XML file (defaults to myanimelist_export.xml).",
    )
    parser.add_argument(
        "-g", "--gz-output",
        type=str,
        default=None,
        help="Path for the compressed GZ file (defaults to myanimelist_export.xml.gz).",
    )
    parser.add_argument(
        "--status",
        type=str,
        default="Completed",
        help="Default status for entries (e.g. Completed, Watching, Plan to Watch).",
    )
    parser.add_argument(
        "--score",
        type=int,
        default=0,
        help="Default score for entries (0-10, default is 0).",
    )
    parser.add_argument(
        "--expand-sequels",
        action="store_true",
        help="Automatically include direct sequels, subsequent seasons, and sequel movies for each anime.",
    )

    args = parser.parse_args()

    input_path_str = args.input_flag or args.input
    if input_path_str:
        input_file = Path(input_path_str)
    else:
        # Check default candidate
        if Path("notes.txt").is_file():
            input_file = Path("notes.txt")
        elif Path("animes.txt").is_file():
            input_file = Path("animes.txt")
        elif Path("input/animes.txt").is_file():
            input_file = Path("input/animes.txt")
        else:
            parser.error("No input file specified and no 'notes.txt' or 'animes.txt' found in current directory.")

    if args.output:
        output_xml = Path(args.output)
    elif Path("output").is_dir():
        output_xml = Path("output/myanimelist_export.xml")
    else:
        output_xml = None

    if args.gz_output:
        output_gz = Path(args.gz_output)
    elif Path("output").is_dir():
        output_gz = Path("output/myanimelist_export.xml.gz")
    else:
        output_gz = None

    titles = load_titles_from_txt(input_file)
    if not titles:
        print(f"Error: No anime titles found in {input_file}.")
        sys.exit(1)

    process_anime_list(
        titles=titles,
        output_xml=output_xml,
        output_gz=output_gz,
        status=args.status,
        score=args.score,
        expand_sequels=args.expand_sequels,
    )


if __name__ == "__main__":
    main()
