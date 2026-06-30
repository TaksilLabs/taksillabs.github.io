import json
from pathlib import Path

from live_helpers import (
    clean_text,
    choose_best_report,
    get_scores_from_report_with_rosters,
    is_overtime_report,
    load_active_roster_lookup,
    load_json_report,
    write_json,
)

from build_preseason import build_match_detail


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"
SEASON_TYPE = "regular_season"

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"

SCHEDULE_FILE = REGULAR_SEASON_DIR / "schedule.json"
ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"

RAW_BY_MATCH_DIR = (
    BASE_DIR
    / "raw_live_logs"
    / SEASON_ID
    / SEASON_TYPE
    / "by_match"
)

OUT_DIR = REGULAR_SEASON_DIR
MATCHES_FILE = OUT_DIR / "matches.json"
MATCH_DETAILS_DIR = OUT_DIR / "match_details"
ROSTER_SNAPSHOTS_FILE = OUT_DIR / "roster_snapshots.json"


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_schedule_matches(schedule_data):
    if isinstance(schedule_data, list):
        return schedule_data

    if isinstance(schedule_data, dict) and isinstance(schedule_data.get("matches"), list):
        return schedule_data["matches"]

    return []


def load_schedule_lookup():
    schedule_data = load_json(SCHEDULE_FILE, {"matches": []})
    matches = get_schedule_matches(schedule_data)

    return {
        match.get("match_id"): match
        for match in matches
        if match.get("match_id")
    }


def load_existing_roster_snapshots():
    return load_json(ROSTER_SNAPSHOTS_FILE, {})


def load_active_rosters_full():
    data = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})

    rosters = {}

    for team in data.get("teams", []):
        team_id = team.get("team_id")

        if not team_id:
            continue

        rosters[team_id] = team

    return rosters


def snapshot_team_roster(team_id, active_rosters):
    roster = active_rosters.get(team_id)

    if not roster:
        return {
            "team_id": team_id,
            "team_display_name": "",
            "team": "",
            "team_abbreviation": "",
            "region": "",
            "division": "",
            "conference": "",
            "players": [],
            "slap_ids": [],
        }

    return {
        "team_id": roster.get("team_id", team_id),
        "team_display_name": roster.get("team_display_name", roster.get("team", "")),
        "team": roster.get("team", roster.get("team_display_name", "")),
        "team_abbreviation": roster.get("team_abbreviation", ""),
        "region": roster.get("region", ""),
        "division": roster.get("division", ""),
        "conference": roster.get("conference", ""),
        "players": roster.get("players", []),
        "slap_ids": roster.get("slap_ids", []),
    }


def get_snapshot_slap_id_set(roster):
    slap_ids = set()

    for slap_id in roster.get("slap_ids", []):
        clean_id = clean_text(slap_id)

        if clean_id:
            slap_ids.add(clean_id)

    for player in roster.get("players", []):
        if isinstance(player, dict):
            clean_id = clean_text(
                player.get("slap_id")
                or player.get("game_user_id")
                or player.get("id")
            )

            if clean_id:
                slap_ids.add(clean_id)

    return slap_ids


def make_roster_lookup_from_snapshot(match, snapshot):
    home_team_id = match["home_team_id"]
    away_team_id = match["away_team_id"]

    home_roster = snapshot.get("home_roster", {})
    away_roster = snapshot.get("away_roster", {})

    return {
        home_team_id: get_snapshot_slap_id_set(home_roster),
        away_team_id: get_snapshot_slap_id_set(away_roster),
    }


def get_side_mapping_roster_lookup(match, active_roster_lookup, roster_snapshots):
    match_id = match["match_id"]
    snapshot = roster_snapshots.get(match_id)

    if snapshot:
        return make_roster_lookup_from_snapshot(match, snapshot), "snapshot"

    return active_roster_lookup, "active_rosters_fallback"


def get_json_files(match_root):
    original_dir = match_root / "original"

    if not original_dir.exists():
        return []

    return sorted(
        path for path in original_dir.rglob("*.json")
        if path.is_file()
    )


def choose_report_for_match(match_root):
    reports = []
    warnings = []

    for json_file in get_json_files(match_root):
        report, error = load_json_report(json_file)

        if error:
            warnings.append(f"Bad JSON {json_file.name}: {error}")
            continue

        reports.append(report)

    if not reports:
        return None, warnings + ["No valid JSON reports found"]

    chosen = choose_best_report(reports)

    return chosen, warnings


def make_match_result_from_schedule(schedule_match):
    match = dict(schedule_match)

    match.setdefault("season_id", SEASON_ID)
    match.setdefault("season_name", SEASON_NAME)
    match.setdefault("season_type", SEASON_TYPE)
    match.setdefault("phase", SEASON_TYPE)

    match.setdefault("status", "scheduled")
    match.setdefault("home_score", None)
    match.setdefault("away_score", None)
    match.setdefault("winner_team_id", None)
    match.setdefault("loser_team_id", None)

    match.setdefault("end_reason", None)
    match.setdefault("overtime", False)
    match.setdefault("period", None)

    match.setdefault("thread_id", None)
    match.setdefault("log_folder", None)
    match.setdefault("report_file", None)

    match.setdefault("side_mapping", None)
    match.setdefault("side_mapping_confidence", 0)
    match.setdefault("side_mapping_normal_score", 0)
    match.setdefault("side_mapping_swapped_score", 0)

    match.setdefault("warnings", [])

    return match


def apply_manifest_metadata(match, manifest, match_root):
    match["thread_id"] = manifest.get("thread_id")
    match["log_folder"] = str(match_root.relative_to(BASE_DIR)).replace("\\", "/")

    match["first_log_timestamp"] = manifest.get("first_log_timestamp", "")
    match["last_log_timestamp"] = manifest.get("last_log_timestamp", "")
    match["probable_start_time"] = manifest.get("probable_start_time", "")
    match["start_time_source"] = manifest.get("start_time_source", "")

    match["source_folder_name"] = manifest.get("source_folder_name", "")
    match["matched_by"] = manifest.get("matched_by", "")
    match["match_import_confidence"] = manifest.get("confidence", 0)

    match["warnings"].extend(manifest.get("warnings", []))


def process_match_folder(
    match_root,
    schedule_lookup,
    active_roster_lookup,
    roster_snapshots,
):
    manifest_file = match_root / "manifest.json"

    if not manifest_file.exists():
        return None, None, [f"Missing manifest.json in {match_root}"]

    manifest = load_json(manifest_file, {})
    match_id = manifest.get("match_id") or match_root.name

    schedule_match = schedule_lookup.get(match_id)

    if not schedule_match:
        return None, None, [f"No schedule row found for {match_id}"]

    match = make_match_result_from_schedule(schedule_match)
    apply_manifest_metadata(match, manifest, match_root)

    chosen, warnings = choose_report_for_match(match_root)
    match["warnings"].extend(warnings)

    if not chosen:
        match["status"] = "uploaded_missing_valid_report"
        return match, None, []

    data = chosen["data"]

    match["report_file"] = str(
        chosen["file_path"].relative_to(BASE_DIR)
    ).replace("\\", "/")

    side_mapping_roster_lookup, side_mapping_roster_source = get_side_mapping_roster_lookup(
        match,
        active_roster_lookup,
        roster_snapshots,
    )

    home_score, away_score, side_mapping = get_scores_from_report_with_rosters(
        data,
        match,
        side_mapping_roster_lookup,
    )

    match["side_mapping_roster_source"] = side_mapping_roster_source

    match["side_mapping"] = side_mapping.get("mapping")
    match["side_mapping_confidence"] = side_mapping.get("confidence", 0)
    match["side_mapping_normal_score"] = side_mapping.get("normal_score", 0)
    match["side_mapping_swapped_score"] = side_mapping.get("swapped_score", 0)

    if side_mapping.get("mapping") == "unknown":
        match["status"] = "uploaded_score_unknown"
        match["warnings"].append(
            f"Could not confidently map log home/away sides using {side_mapping_roster_source}"
        )
        return match, None, []

    if side_mapping.get("confidence", 0) < 2:
        match["warnings"].append(
            f"Low roster side-mapping confidence: {side_mapping.get('confidence', 0)}"
        )

    if home_score is None or away_score is None:
        match["status"] = "uploaded_score_unknown"
        match["warnings"].append("Could not determine score from report")
        return match, None, []

    match["status"] = "final"
    match["home_score"] = home_score
    match["away_score"] = away_score

    match["period"] = chosen["period"]
    match["end_reason"] = clean_text(data.get("end_reason"))
    match["overtime"] = is_overtime_report(data)

    if home_score > away_score:
        match["winner_team_id"] = match["home_team_id"]
        match["loser_team_id"] = match["away_team_id"]
    elif away_score > home_score:
        match["winner_team_id"] = match["away_team_id"]
        match["loser_team_id"] = match["home_team_id"]
    else:
        match["winner_team_id"] = None
        match["loser_team_id"] = None
        match["warnings"].append("Tie score detected")

    detail = build_match_detail(
        match,
        data,
        side_mapping.get("mapping"),
    )

    return match, detail, []


def build_roster_snapshots(matches, active_rosters):
    snapshots = load_existing_roster_snapshots()

    created = 0

    for match in matches:
        if match["status"] != "final":
            continue

        match_id = match["match_id"]

        # Do not overwrite old snapshots.
        if match_id in snapshots:
            continue

        snapshots[match_id] = {
            "match_id": match_id,
            "source_id": match.get("source_id"),
            "season_id": match["season_id"],
            "season_name": match.get("season_name", SEASON_NAME),
            "season_type": SEASON_TYPE,
            "phase": SEASON_TYPE,

            "division": match.get("division"),
            "region": match.get("region") or match.get("home_region") or match.get("away_region"),

            "home_team_id": match["home_team_id"],
            "home_team": match["home_team"],
            "away_team_id": match["away_team_id"],
            "away_team": match["away_team"],

            "home_roster": snapshot_team_roster(
                match["home_team_id"],
                active_rosters,
            ),
            "away_roster": snapshot_team_roster(
                match["away_team_id"],
                active_rosters,
            ),
        }

        created += 1

    write_json(ROSTER_SNAPSHOTS_FILE, snapshots)

    return created, len(snapshots)


def build_regular_matches():
    schedule_lookup = load_schedule_lookup()
    active_roster_lookup = load_active_roster_lookup(ACTIVE_ROSTERS_FILE)
    active_rosters = load_active_rosters_full()
    roster_snapshots = load_existing_roster_snapshots()

    results = []
    match_details = {}
    warnings = []

    if not RAW_BY_MATCH_DIR.exists():
        print(f"Missing raw match folder: {RAW_BY_MATCH_DIR}")
        return [], {}, []

    match_roots = sorted(
        path for path in RAW_BY_MATCH_DIR.iterdir()
        if path.is_dir()
    )

    for match_root in match_roots:
        match, detail, folder_warnings = process_match_folder(
            match_root,
            schedule_lookup,
            active_roster_lookup,
            roster_snapshots,
        )

        warnings.extend(folder_warnings)

        if match:
            results.append(match)

        if match and detail:
            match_details[match["match_id"]] = detail

    snapshots_created, snapshots_total = build_roster_snapshots(
        results,
        active_rosters,
    )

    MATCH_DETAILS_DIR.mkdir(parents=True, exist_ok=True)

    for old_detail_file in MATCH_DETAILS_DIR.glob("*.json"):
        old_detail_file.unlink()

    for match_id, detail in match_details.items():
        write_json(MATCH_DETAILS_DIR / f"{match_id}.json", detail)

    output = {
        "season_id": SEASON_ID,
        "season_name": SEASON_NAME,
        "season_type": SEASON_TYPE,
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "match_count": len(results),
        "completed_match_count": sum(1 for match in results if match["status"] == "final"),
        "matches": results,
        "warnings": warnings,
    }

    write_json(MATCHES_FILE, output)

    return results, match_details, {
        "snapshots_created": snapshots_created,
        "snapshots_total": snapshots_total,
        "warnings": warnings,
    }


def main():
    matches, match_details, meta = build_regular_matches()

    print("Regular season match build complete.")
    print(f"Raw imported matches found: {len(matches)}")
    print(f"Completed matches: {sum(1 for match in matches if match['status'] == 'final')}")
    print(f"Match detail files written: {len(match_details)}")
    print(f"Roster snapshots created: {meta['snapshots_created']}")
    print(f"Roster snapshots total: {meta['snapshots_total']}")

    if meta["warnings"]:
        print()
        print("Warnings:")
        for warning in meta["warnings"]:
            print(f"- {warning}")

    print(f"Wrote: {MATCHES_FILE}")


if __name__ == "__main__":
    main()