import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


SEASON_ID = "summer_2026"
SEASON_TYPE = "regular_season"

BASE_DIR = Path(__file__).resolve().parents[2]

INCOMING_UNSORTED_DIR = BASE_DIR / "data" / "incoming_logs" / "unsorted"
INCOMING_NEEDS_REVIEW_DIR = BASE_DIR / "data" / "incoming_logs" / "needs_review"
INCOMING_IMPORTED_DIR = BASE_DIR / "data" / "incoming_logs" / "imported"

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"

SCHEDULE_FILE = REGULAR_SEASON_DIR / "schedule.json"
ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"
TEAM_ALIASES_FILE = LIVE_SEASON_DIR / "team_aliases.json"

RAW_REGULAR_DIR = BASE_DIR / "raw_live_logs" / SEASON_ID / SEASON_TYPE
RAW_BY_MATCH_DIR = RAW_REGULAR_DIR / "by_match"

IMPORTED_MANIFEST_FILE = INCOMING_IMPORTED_DIR / "imported_manifest.json"


def clean(value):
    return str(value or "").strip()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def normalize_team(value):
    return (
        clean(value)
        .lower()
        .replace("&", "and")
        .replace("$", "s")
        .replace("@", "a")
        .replace("!", "i")
        .replace("0", "o")
        .replace("1", "i")
        .replace("3", "e")
        .replace("5", "s")
        .replace("7", "t")
        .replace("’", "")
        .replace("'", "")
    )


def normalize_team_key(value):
    value = normalize_team(value)

    return (
        re.sub(r"[^a-z0-9]+", "_", value)
        .strip("_")
    )


def get_schedule_matches(schedule_data):
    if isinstance(schedule_data, list):
        return schedule_data

    if isinstance(schedule_data, dict) and isinstance(schedule_data.get("matches"), list):
        return schedule_data["matches"]

    return []


def get_active_roster_teams(active_rosters):
    if isinstance(active_rosters, list):
        return active_rosters

    if isinstance(active_rosters, dict) and isinstance(active_rosters.get("teams"), list):
        return active_rosters["teams"]

    if isinstance(active_rosters, dict):
        return list(active_rosters.values())

    return []


def get_team_display_name(team):
    return (
        team.get("team_display_name")
        or team.get("team_name")
        or team.get("team")
        or team.get("team_id")
        or ""
    )


def build_team_lookup(active_rosters, team_aliases):
    lookup = {}

    for team in get_active_roster_teams(active_rosters):
        values = [
            team.get("team_id"),
            team.get("team_display_name"),
            team.get("team_name"),
            team.get("team"),
            team.get("abbreviation"),
            team.get("team_abbreviation"),
            *team.get("aliases", []),
            *team.get("team_aliases", []),
        ]

        for value in values:
            key = normalize_team_key(value)
            if key:
                lookup[key] = team

    for alias, real_team in (team_aliases or {}).items():
        alias_key = normalize_team_key(alias)
        real_key = normalize_team_key(real_team)

        if alias_key and real_key and real_key in lookup:
            lookup[alias_key] = lookup[real_key]

    return lookup


def resolve_team(value, team_lookup):
    return team_lookup.get(normalize_team_key(value))


def team_id_set(*values):
    return {
        normalize_team_key(value)
        for value in values
        if normalize_team_key(value)
    }


def parse_match_folder_name(folder_name):
    """
    Expected:
    1.4_ Atlantic City Zootiez$ vs Battle Creek Kings__1520930545478009042

    Returns:
    {
      source_id: "1.4",
      home_team: "Atlantic City Zootiez$",
      away_team: "Battle Creek Kings",
      thread_id: "1520930545478009042"
    }
    """

    name = clean(folder_name)

    match = re.match(
        r"^(?P<source_id>\d+\.\d+)_\s*(?P<teams>.+?)(?:__(?P<thread_id>\d+))?$",
        name
    )

    if not match:
        return {
            "source_id": "",
            "home_team": "",
            "away_team": "",
            "thread_id": "",
            "warnings": [f"Could not parse folder name: {folder_name}"],
        }

    source_id = clean(match.group("source_id"))
    teams_text = clean(match.group("teams"))
    thread_id = clean(match.group("thread_id"))

    teams_match = re.match(r"^(?P<home>.+?)\s+vs\s+(?P<away>.+)$", teams_text, re.IGNORECASE)

    if not teams_match:
        return {
            "source_id": source_id,
            "home_team": "",
            "away_team": "",
            "thread_id": thread_id,
            "warnings": [f"Could not parse teams from folder name: {folder_name}"],
        }

    return {
        "source_id": source_id,
        "home_team": clean(teams_match.group("home")),
        "away_team": clean(teams_match.group("away")),
        "thread_id": thread_id,
        "warnings": [],
    }


def parse_timestamp_from_filename(filename):
    """
    Extracts the actual match-log datetime from filenames like:

    20260630_013105_231615312896720908_2026-06-29-21-10-47.json

    Preferred timestamp is the final:
    YYYY-MM-DD-hh-mm-ss
    """

    stem = Path(filename).stem

    # Prefer the trailing timestamp format:
    # 2026-06-29-21-10-47
    trailing_match = re.search(
        r"(?P<year>20\d{2})-(?P<month>\d{2})-(?P<day>\d{2})-(?P<hour>\d{2})-(?P<minute>\d{2})-(?P<second>\d{2})$",
        stem
    )

    if trailing_match:
        parts = {key: int(value) for key, value in trailing_match.groupdict().items()}

        try:
            return datetime(
                parts["year"],
                parts["month"],
                parts["day"],
                parts["hour"],
                parts["minute"],
                parts["second"],
            ).isoformat()
        except ValueError:
            return ""

    # Fallbacks, just in case older logs use a different format.
    patterns = [
        r"(?P<year>20\d{2})[-_](?P<month>\d{2})[-_](?P<day>\d{2})[-_ T](?P<hour>\d{2})[-_:](?P<minute>\d{2})[-_:](?P<second>\d{2})",
        r"(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})[-_ T]?(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, stem)

        if not match:
            continue

        parts = {key: int(value) for key, value in match.groupdict().items()}

        try:
            return datetime(
                parts["year"],
                parts["month"],
                parts["day"],
                parts["hour"],
                parts["minute"],
                parts["second"],
            ).isoformat()
        except ValueError:
            return ""

    return ""

def floor_timestamp_to_quarter_hour(timestamp):
    """
    Floors an ISO timestamp to the nearest previous 15-minute mark.

    Example:
    2026-06-29T21:10:47 -> 2026-06-29T21:00:00
    2026-06-29T21:16:02 -> 2026-06-29T21:15:00
    2026-06-29T22:59:59 -> 2026-06-29T22:45:00
    """

    if not timestamp:
        return ""

    try:
        dt = datetime.fromisoformat(timestamp)
    except ValueError:
        return ""

    floored_minute = (dt.minute // 15) * 15

    return dt.replace(
        minute=floored_minute,
        second=0,
        microsecond=0
    ).isoformat()

def get_json_files(folder):
    return sorted(
        path for path in folder.rglob("*.json")
        if path.is_file()
    )


def schedule_team_pair_keys(match):
    home_values = team_id_set(
        match.get("home_team_id"),
        match.get("home_team"),
        match.get("home_team_name"),
    )

    away_values = team_id_set(
        match.get("away_team_id"),
        match.get("away_team"),
        match.get("away_team_name"),
    )

    return home_values, away_values


def same_team_pair(schedule_match, detected_home_team, detected_away_team, team_lookup):
    detected_home = resolve_team(detected_home_team, team_lookup)
    detected_away = resolve_team(detected_away_team, team_lookup)

    detected_home_values = team_id_set(
        detected_home_team,
        detected_home.get("team_id") if detected_home else "",
        get_team_display_name(detected_home) if detected_home else "",
    )

    detected_away_values = team_id_set(
        detected_away_team,
        detected_away.get("team_id") if detected_away else "",
        get_team_display_name(detected_away) if detected_away else "",
    )

    schedule_home_values, schedule_away_values = schedule_team_pair_keys(schedule_match)

    direct = (
        bool(schedule_home_values & detected_home_values)
        and bool(schedule_away_values & detected_away_values)
    )

    reversed_pair = (
        bool(schedule_home_values & detected_away_values)
        and bool(schedule_away_values & detected_home_values)
    )

    return direct or reversed_pair


def match_folder_to_schedule(parsed_folder, schedule_matches, team_lookup, already_imported_match_ids):
    source_id = parsed_folder["source_id"]
    detected_home = parsed_folder["home_team"]
    detected_away = parsed_folder["away_team"]

    warnings = []

    candidates = []

    for match in schedule_matches:
        if match.get("match_id") in already_imported_match_ids:
            continue

        if clean(match.get("status")).lower() in {"final", "completed", "complete"}:
            continue

        source_matches = clean(match.get("source_id")) == source_id
        teams_match = same_team_pair(match, detected_home, detected_away, team_lookup)

        score = 0
        reasons = []

        if source_matches:
            score += 70
            reasons.append("source_id")

        if teams_match:
            score += 100
            reasons.append("team_pair")

        if score:
            candidates.append({
                "match": match,
                "score": score,
                "reasons": reasons,
            })

    candidates.sort(key=lambda item: item["score"], reverse=True)

    if not candidates:
        return None, {
            "matched_by": "none",
            "confidence": 0,
            "warnings": [
                f"No schedule match found for {source_id}: {detected_home} vs {detected_away}"
            ],
            "candidates": [],
        }

    best = candidates[0]
    tied = [
        item for item in candidates
        if item["score"] == best["score"]
    ]

    if len(tied) > 1:
        return None, {
            "matched_by": "ambiguous",
            "confidence": 0,
            "warnings": [
                f"Ambiguous schedule match for {source_id}: {detected_home} vs {detected_away}"
            ],
            "candidates": [
                candidate_summary(item["match"], item["score"], item["reasons"])
                for item in tied[:10]
            ],
        }

    confidence = min(1.0, best["score"] / 170)

    if best["score"] >= 170:
        matched_by = "source_id_and_team_pair"
    elif best["score"] >= 100:
        matched_by = "team_pair"
        warnings.append("Matched by team pair only; source_id did not match.")
    elif best["score"] >= 70:
        matched_by = "source_id"
        warnings.append("Matched by source_id only; team names did not match.")
    else:
        matched_by = "unknown"

    if best["score"] < 100:
        return None, {
            "matched_by": matched_by,
            "confidence": confidence,
            "warnings": warnings + [
                f"Low-confidence match for {source_id}: {detected_home} vs {detected_away}"
            ],
            "candidates": [
                candidate_summary(best["match"], best["score"], best["reasons"])
            ],
        }

    return best["match"], {
        "matched_by": matched_by,
        "confidence": confidence,
        "warnings": warnings,
        "candidates": [
            candidate_summary(best["match"], best["score"], best["reasons"])
        ],
    }


def candidate_summary(match, score, reasons):
    return {
        "match_id": match.get("match_id"),
        "source_id": match.get("source_id"),
        "division": match.get("division"),
        "home_team": match.get("home_team"),
        "away_team": match.get("away_team"),
        "score": score,
        "reasons": reasons,
    }


def copy_folder_contents(source_folder, destination_folder):
    destination_folder.mkdir(parents=True, exist_ok=True)

    copied = []

    for source_file in get_json_files(source_folder):
        relative = source_file.relative_to(source_folder)
        destination_file = destination_folder / relative

        destination_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination_file)

        copied.append(destination_file)

    return copied


def folder_has_json(folder):
    return bool(get_json_files(folder))


def load_imported_manifest():
    data = load_json(IMPORTED_MANIFEST_FILE, {
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "imported_folders": {},
        "imported_match_ids": {},
    })

    data.setdefault("season_id", SEASON_ID)
    data.setdefault("season_type", SEASON_TYPE)
    data.setdefault("imported_folders", {})
    data.setdefault("imported_match_ids", {})

    return data


def write_imported_manifest(data):
    data["updated_at_utc"] = utc_now()
    write_json(IMPORTED_MANIFEST_FILE, data)


def build_match_manifest(
    source_folder,
    original_destination_folder,
    parsed_folder,
    schedule_match,
    match_info,
    copied_files,
):
    source_files = []

    timestamps = []

    for copied_file in sorted(copied_files):
        timestamp = parse_timestamp_from_filename(copied_file.name)

        if timestamp:
            timestamps.append(timestamp)

        source_files.append({
            "original_name": copied_file.name,
            "relative_path": str(copied_file.relative_to(original_destination_folder.parent)).replace("\\", "/"),
            "timestamp_from_filename": timestamp,
        })

    timestamps = sorted(timestamps)
    first_log_timestamp = timestamps[0] if timestamps else ""
    last_log_timestamp = timestamps[-1] if timestamps else ""
    probable_start_time = floor_timestamp_to_quarter_hour(first_log_timestamp)

    manifest = {
        "match_id": schedule_match.get("match_id"),
        "season_id": SEASON_ID,
        "season_type": SEASON_TYPE,
        "division": schedule_match.get("division"),

        "imported_at_utc": utc_now(),

        "source_folder_name": source_folder.name,
        "source_folder_path": str(source_folder.relative_to(BASE_DIR)).replace("\\", "/"),

        "source_id": parsed_folder["source_id"],
        "thread_id": parsed_folder["thread_id"],

        "detected_home_team": parsed_folder["home_team"],
        "detected_away_team": parsed_folder["away_team"],

        "matched_schedule_home_team_id": schedule_match.get("home_team_id"),
        "matched_schedule_away_team_id": schedule_match.get("away_team_id"),
        "matched_schedule_home_team": schedule_match.get("home_team"),
        "matched_schedule_away_team": schedule_match.get("away_team"),

        "matched_by": match_info["matched_by"],
        "confidence": match_info["confidence"],

        "first_log_timestamp": first_log_timestamp,
        "last_log_timestamp": last_log_timestamp,
        "probable_start_time": probable_start_time,
        "start_time_source": "first_log_timestamp_floor_15_minutes" if probable_start_time else "",

        "source_files": source_files,
        "warnings": parsed_folder.get("warnings", []) + match_info.get("warnings", []),
    }

    return manifest


def process_source_folder(source_folder, schedule_matches, team_lookup, imported_manifest, move=False, force=False):
    folder_key = source_folder.name

    if not force and folder_key in imported_manifest["imported_folders"]:
        return {
            "status": "skipped",
            "folder": folder_key,
            "message": "Already imported",
        }

    if not folder_has_json(source_folder):
        return {
            "status": "skipped",
            "folder": folder_key,
            "message": "No JSON files found",
        }

    parsed = parse_match_folder_name(source_folder.name)

    already_imported_match_ids = set(imported_manifest.get("imported_match_ids", {}).keys())

    schedule_match, match_info = match_folder_to_schedule(
        parsed,
        schedule_matches,
        team_lookup,
        already_imported_match_ids if not force else set(),
    )

    if not schedule_match:
        review_manifest = {
            "source_folder_name": source_folder.name,
            "source_folder_path": str(source_folder.relative_to(BASE_DIR)).replace("\\", "/"),
            "parsed": parsed,
            "match_info": match_info,
            "created_at_utc": utc_now(),
        }

        review_path = INCOMING_NEEDS_REVIEW_DIR / source_folder.name / "review_manifest.json"

        if move:
            destination = INCOMING_NEEDS_REVIEW_DIR / source_folder.name
            if destination.exists():
                shutil.rmtree(destination)
            shutil.move(str(source_folder), str(destination))
            write_json(destination / "review_manifest.json", review_manifest)
        else:
            write_json(review_path, review_manifest)

        return {
            "status": "needs_review",
            "folder": folder_key,
            "message": "; ".join(match_info.get("warnings", [])),
        }

    match_id = schedule_match["match_id"]

    match_root = RAW_BY_MATCH_DIR / match_id
    original_destination = match_root / "original" / source_folder.name

    if original_destination.exists() and force:
        shutil.rmtree(original_destination)

    copied_files = copy_folder_contents(source_folder, original_destination)

    manifest = build_match_manifest(
        source_folder=source_folder,
        original_destination_folder=original_destination,
        parsed_folder=parsed,
        schedule_match=schedule_match,
        match_info=match_info,
        copied_files=copied_files,
    )

    write_json(match_root / "manifest.json", manifest)

    imported_manifest["imported_folders"][folder_key] = {
        "match_id": match_id,
        "source_id": parsed["source_id"],
        "thread_id": parsed["thread_id"],
        "imported_at_utc": manifest["imported_at_utc"],
        "destination": str(match_root.relative_to(BASE_DIR)).replace("\\", "/"),
    }

    imported_manifest["imported_match_ids"][match_id] = {
        "source_folder_name": folder_key,
        "imported_at_utc": manifest["imported_at_utc"],
    }

    if move:
        destination = INCOMING_IMPORTED_DIR / source_folder.name

        if destination.exists():
            shutil.rmtree(destination)

        shutil.move(str(source_folder), str(destination))

    return {
        "status": "imported",
        "folder": folder_key,
        "match_id": match_id,
        "message": f"{parsed['source_id']} -> {match_id}",
    }


def import_incoming_regular_logs(move=False, force=False):
    schedule_data = load_json(SCHEDULE_FILE, {"matches": []})
    active_rosters = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})
    team_aliases = load_json(TEAM_ALIASES_FILE, {})

    schedule_matches = get_schedule_matches(schedule_data)
    team_lookup = build_team_lookup(active_rosters, team_aliases)

    imported_manifest = load_imported_manifest()

    INCOMING_UNSORTED_DIR.mkdir(parents=True, exist_ok=True)
    INCOMING_IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    INCOMING_NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    RAW_BY_MATCH_DIR.mkdir(parents=True, exist_ok=True)

    source_folders = sorted(
        path for path in INCOMING_UNSORTED_DIR.iterdir()
        if path.is_dir()
    )

    results = []

    for source_folder in source_folders:
        result = process_source_folder(
            source_folder,
            schedule_matches,
            team_lookup,
            imported_manifest,
            move=move,
            force=force,
        )

        results.append(result)

    write_imported_manifest(imported_manifest)

    return results


def print_summary(results):
    imported = [item for item in results if item["status"] == "imported"]
    needs_review = [item for item in results if item["status"] == "needs_review"]
    skipped = [item for item in results if item["status"] == "skipped"]

    print()
    print("Incoming regular logs import complete.")
    print(f"Imported: {len(imported)}")
    print(f"Needs review: {len(needs_review)}")
    print(f"Skipped: {len(skipped)}")

    if imported:
        print()
        print("Imported folders:")
        for item in imported:
            print(f"- {item['folder']} -> {item['match_id']}")

    if needs_review:
        print()
        print("Needs review:")
        for item in needs_review:
            print(f"- {item['folder']}: {item['message']}")

    if skipped:
        print()
        print("Skipped:")
        for item in skipped:
            print(f"- {item['folder']}: {item['message']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--move", action="store_true", help="Move imported folders out of unsorted after import.")
    parser.add_argument("--force", action="store_true", help="Re-import folders even if they were already imported.")
    args = parser.parse_args()

    results = import_incoming_regular_logs(
        move=args.move,
        force=args.force,
    )

    print_summary(results)


if __name__ == "__main__":
    main()