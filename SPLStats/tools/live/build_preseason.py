from pathlib import Path

from live_helpers import (
    clean_text,
    choose_best_report,
    get_preseason_region,
    get_scores_from_report_with_rosters,
    is_overtime_report,
    load_active_roster_lookup,
    load_json_report,
    make_id,
    make_preseason_match_id,
    parse_uploaded_match_folder,
    read_tsv,
    write_json,
)


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"

SCHEDULE_FILE = (
    BASE_DIR
    / "raw_schedules"
    / SEASON_ID
    / "preseason"
    / "preseason.tsv"
)

LOGS_DIR = (
    BASE_DIR
    / "raw_live_logs"
    / SEASON_ID
    / "preseason"
)

ACTIVE_ROSTERS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "active_rosters.json"
)

OUT_DIR = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "preseason"
)


REGION_DISPLAY = {
    "east": "East",
    "central": "Central",
    "west": "West",
    "unknown": "Unknown",
}


def build_schedule():
    if not SCHEDULE_FILE.exists():
        print(f"Missing preseason schedule: {SCHEDULE_FILE}")
        return []

    rows = read_tsv(SCHEDULE_FILE)
    matches = []

    for row in rows:
        schedule_id = clean_text(row.get("MATCHID"))
        home_team = clean_text(row.get("Home Team"))
        away_team = clean_text(row.get("Away Team"))

        if not schedule_id or not home_team or not away_team:
            continue

        region = get_preseason_region(schedule_id)

        matches.append({
            "match_id": make_preseason_match_id(SEASON_ID, schedule_id),
            "season_id": SEASON_ID,
            "season_name": SEASON_NAME,
            "phase": "preseason",
            "region": region,
            "region_display": REGION_DISPLAY.get(region, region.title()),
            "division_id": None,
            "division": "Preseason",
            "schedule_id": schedule_id,

            "home_team_id": make_id(home_team, "home_team"),
            "home_team": home_team,
            "away_team_id": make_id(away_team, "away_team"),
            "away_team": away_team,

            "status": "scheduled",
            "home_score": None,
            "away_score": None,
            "winner_team_id": None,
            "loser_team_id": None,

            "end_reason": None,
            "overtime": False,
            "period": None,

            "thread_id": None,
            "log_folder": None,
            "report_file": None,

            "side_mapping": None,
            "side_mapping_confidence": 0,
            "side_mapping_normal_score": 0,
            "side_mapping_swapped_score": 0,

            "warnings": [],
        })

    return matches


def scan_log_folders():
    uploaded = {}

    if not LOGS_DIR.exists():
        return uploaded

    region_dirs = [
        path for path in LOGS_DIR.iterdir()
        if path.is_dir()
    ]

    for region_dir in region_dirs:
        region_from_folder = region_dir.name.lower().strip()

        for match_folder in region_dir.iterdir():
            if not match_folder.is_dir():
                continue

            parsed = parse_uploaded_match_folder(match_folder.name)

            if not parsed:
                print(f"WARNING: Could not parse folder name: {match_folder}")
                continue

            schedule_id = parsed["schedule_id"]
            expected_region = get_preseason_region(schedule_id)

            warnings = []

            if expected_region != region_from_folder:
                warnings.append(
                    f"{schedule_id} found in {region_from_folder}, expected {expected_region}"
                )

            reports = []

            for json_file in sorted(match_folder.glob("*.json")):
                report, error = load_json_report(json_file)

                if error:
                    warnings.append(f"Bad JSON {json_file.name}: {error}")
                    continue

                reports.append(report)

            if not reports:
                warnings.append("No valid JSON reports found")
                chosen = None
            else:
                chosen = choose_best_report(reports)

            if schedule_id in uploaded:
                warnings.append(
                    f"Duplicate uploaded folder for schedule_id {schedule_id}; latest scanned folder used"
                )

            uploaded[schedule_id] = {
                "folder": match_folder,
                "parsed": parsed,
                "chosen": chosen,
                "warnings": warnings,
            }

    return uploaded


def apply_results(matches, uploaded, roster_lookup):
    for match in matches:
        schedule_id = match["schedule_id"]

        if schedule_id not in uploaded:
            continue

        upload = uploaded[schedule_id]
        chosen = upload["chosen"]

        match["thread_id"] = upload["parsed"]["thread_id"]
        match["log_folder"] = str(
            upload["folder"].relative_to(BASE_DIR)
        ).replace("\\", "/")

        match["warnings"].extend(upload["warnings"])

        parsed_home = upload["parsed"].get("home_team", "")
        parsed_away = upload["parsed"].get("away_team", "")

        if make_id(parsed_home, "") != match["home_team_id"]:
            match["warnings"].append(
                f"Folder home team '{parsed_home}' does not match schedule home team '{match['home_team']}'"
            )

        if make_id(parsed_away, "") != match["away_team_id"]:
            match["warnings"].append(
                f"Folder away team '{parsed_away}' does not match schedule away team '{match['away_team']}'"
            )

        if not chosen:
            match["status"] = "uploaded_missing_valid_report"
            continue

        data = chosen["data"]

        match["report_file"] = str(
            chosen["file_path"].relative_to(BASE_DIR)
        ).replace("\\", "/")

        home_score, away_score, side_mapping = get_scores_from_report_with_rosters(
            data,
            match,
            roster_lookup
        )

        match["side_mapping"] = side_mapping.get("mapping")
        match["side_mapping_confidence"] = side_mapping.get("confidence", 0)
        match["side_mapping_normal_score"] = side_mapping.get("normal_score", 0)
        match["side_mapping_swapped_score"] = side_mapping.get("swapped_score", 0)

        if side_mapping.get("mapping") == "unknown":
            match["status"] = "uploaded_score_unknown"
            match["warnings"].append(
                "Could not confidently map log home/away sides using active rosters"
            )
            continue

        if side_mapping.get("confidence", 0) < 2:
            match["warnings"].append(
                f"Low roster side-mapping confidence: {side_mapping.get('confidence', 0)}"
            )

        if home_score is None or away_score is None:
            match["status"] = "uploaded_score_unknown"
            match["warnings"].append("Could not determine score from report")
            continue

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


def build_standings(matches):
    standings = {}
    team_results = {}

    def ensure_team(match, side):
        team_id = match[f"{side}_team_id"]

        if team_id not in standings:
            standings[team_id] = {
                "rank": None,

                "team_id": team_id,
                "team": match[f"{side}_team"],
                "team_display_name": match[f"{side}_team"],

                "region": match["region"],
                "region_display": match["region_display"],
                "phase": "preseason",

                "games_played": 0,
                "wins": 0,
                "regulation_losses": 0,
                "overtime_losses": 0,

                "points": 0,

                "goals_for": 0,
                "goals_against": 0,
                "goal_diff": 0,

                "last_5": "0-0-0",
                "last_5_games": [],
            }

        if team_id not in team_results:
            team_results[team_id] = []

        return standings[team_id]

    def add_result(team_id, result, match, goals_for, goals_against):
        team_results.setdefault(team_id, []).append({
            "match_id": match["match_id"],
            "schedule_id": match["schedule_id"],
            "result": result,
            "overtime": bool(match.get("overtime")),
            "goals_for": goals_for,
            "goals_against": goals_against,
        })

    for match in matches:
        home = ensure_team(match, "home")
        away = ensure_team(match, "away")

        if match["status"] != "final":
            continue

        home_score = int(match["home_score"])
        away_score = int(match["away_score"])
        overtime = bool(match.get("overtime"))

        home_id = match["home_team_id"]
        away_id = match["away_team_id"]

        home["games_played"] += 1
        away["games_played"] += 1

        home["goals_for"] += home_score
        home["goals_against"] += away_score

        away["goals_for"] += away_score
        away["goals_against"] += home_score

        if home_score > away_score:
            home["wins"] += 1
            home["points"] += 2

            if overtime:
                away["overtime_losses"] += 1
                away["points"] += 1

                add_result(home_id, "W", match, home_score, away_score)
                add_result(away_id, "OTL", match, away_score, home_score)
            else:
                away["regulation_losses"] += 1

                add_result(home_id, "W", match, home_score, away_score)
                add_result(away_id, "L", match, away_score, home_score)

        elif away_score > home_score:
            away["wins"] += 1
            away["points"] += 2

            if overtime:
                home["overtime_losses"] += 1
                home["points"] += 1

                add_result(away_id, "W", match, away_score, home_score)
                add_result(home_id, "OTL", match, home_score, away_score)
            else:
                home["regulation_losses"] += 1

                add_result(away_id, "W", match, away_score, home_score)
                add_result(home_id, "L", match, home_score, away_score)

    for team_id, team in standings.items():
        team["goal_diff"] = team["goals_for"] - team["goals_against"]

        last_5_games = team_results.get(team_id, [])[-5:]

        wins = sum(1 for game in last_5_games if game["result"] == "W")
        regulation_losses = sum(1 for game in last_5_games if game["result"] == "L")
        overtime_losses = sum(1 for game in last_5_games if game["result"] == "OTL")

        team["last_5"] = f"{wins}-{regulation_losses}-{overtime_losses}"
        team["last_5_games"] = last_5_games

    sorted_standings = sorted(
        standings.values(),
        key=lambda team: (
            team["region"],
            -team["points"],
            -team["wins"],
            -team["goal_diff"],
            -team["goals_for"],
            team["team"].lower()
        )
    )

    current_region = None
    rank = 0

    for team in sorted_standings:
        if team["region"] != current_region:
            current_region = team["region"]
            rank = 1
        else:
            rank += 1

        team["rank"] = rank

    return sorted_standings


def main():
    matches = build_schedule()
    uploaded = scan_log_folders()
    roster_lookup = load_active_roster_lookup(ACTIVE_ROSTERS_FILE)

    apply_results(matches, uploaded, roster_lookup)

    standings = build_standings(matches)

    write_json(OUT_DIR / "schedule.json", matches)
    write_json(
        OUT_DIR / "matches.json",
        [match for match in matches if match["status"] != "scheduled"]
    )
    write_json(OUT_DIR / "standings.json", standings)

    print(f"Preseason schedule matches: {len(matches)}")
    print(f"Uploaded match folders found: {len(uploaded)}")
    print(f"Completed matches: {sum(1 for m in matches if m['status'] == 'final')}")
    print(f"Teams in standings: {len(standings)}")
    print(f"Roster teams loaded: {len(roster_lookup)}")
    print(f"Wrote: {OUT_DIR}")


if __name__ == "__main__":
    main()