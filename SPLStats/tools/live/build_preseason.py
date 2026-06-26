import json
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

ROSTER_SNAPSHOTS_FILE = OUT_DIR / "roster_snapshots.json"

MATCH_DETAILS_DIR = OUT_DIR / "match_details"


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

def get_stat(stats, key):
    try:
        return float(stats.get(key, 0) or 0)
    except Exception:
        return 0.0


def format_number(value):
    if value == int(value):
        return int(value)
    return round(value, 2)


def get_scheduled_side_from_log_side(log_side, side_mapping):
    if side_mapping == "normal":
        return log_side

    if side_mapping == "swapped":
        if log_side == "home":
            return "away"
        if log_side == "away":
            return "home"

    return None


def empty_team_stats():
    return {
        "shots": 0,
        "saves": 0,
        "blocks": 0,
        "faceoffs_won": 0,
        "takeaways": 0,
        "possession_time_sec": 0,
        "possession_percent": 0,
        "goals": 0,
        "assists": 0,
        "passes": 0,
        "turnovers": 0,
    }


def build_match_detail(match, report_data, side_mapping):
    team_stats = {
        "home": empty_team_stats(),
        "away": empty_team_stats(),
    }

    players = []

    for player in report_data.get("players", []):
        log_side = clean_text(player.get("team")).lower()
        scheduled_side = get_scheduled_side_from_log_side(log_side, side_mapping)

        if scheduled_side not in ("home", "away"):
            continue

        stats = player.get("stats", {})

        if scheduled_side == "home":
            team_id = match["home_team_id"]
            team_name = match["home_team"]
        else:
            team_id = match["away_team_id"]
            team_name = match["away_team"]

        goals = get_stat(stats, "goals")
        assists = get_stat(stats, "assists")
        points = goals + assists

        shots = get_stat(stats, "shots")
        saves = get_stat(stats, "saves")

        # Filled in after team totals are known.
        conceded_goals = 0
        shots_faced = 0
        save_percent = "0.000"

        player_row = {
            "team_side": scheduled_side,
            "team_id": team_id,
            "team": team_name,

            "slap_id": clean_text(player.get("game_user_id")),
            "username": clean_text(player.get("username")),

            "goals": format_number(goals),
            "assists": format_number(assists),
            "points": format_number(points),

            "shots": format_number(shots),
            "saves": format_number(saves),
            "blocks": format_number(get_stat(stats, "blocks")),

            "faceoffs_won": format_number(get_stat(stats, "faceoffs_won")),
            "faceoffs_lost": format_number(get_stat(stats, "faceoffs_lost")),

            "takeaways": format_number(get_stat(stats, "takeaways")),
            "turnovers": format_number(get_stat(stats, "turnovers")),
            "post_hits": format_number(get_stat(stats, "post_hits")),
            "passes": format_number(get_stat(stats, "passes")),
            "possession_time_sec": format_number(get_stat(stats, "possession_time_sec")),

            "conceded_goals": 0,
            "shots_faced": 0,
            "save_percent": "0.000",
            "gaa": 0,

            "score": format_number(get_stat(stats, "score")),
        }

        players.append(player_row)

        team_stats[scheduled_side]["shots"] += get_stat(stats, "shots")
        team_stats[scheduled_side]["saves"] += get_stat(stats, "saves")
        team_stats[scheduled_side]["blocks"] += get_stat(stats, "blocks")
        team_stats[scheduled_side]["faceoffs_won"] += get_stat(stats, "faceoffs_won")
        team_stats[scheduled_side]["takeaways"] += get_stat(stats, "takeaways")
        team_stats[scheduled_side]["possession_time_sec"] += get_stat(stats, "possession_time_sec")
        team_stats[scheduled_side]["goals"] += goals
        team_stats[scheduled_side]["assists"] += assists
        team_stats[scheduled_side]["passes"] += get_stat(stats, "passes")
        team_stats[scheduled_side]["turnovers"] += get_stat(stats, "turnovers")
        team_stats[scheduled_side]["faceoffs_lost"] = team_stats[scheduled_side].get("faceoffs_lost", 0) + get_stat(stats, "faceoffs_lost")
        team_stats[scheduled_side]["post_hits"] = team_stats[scheduled_side].get("post_hits", 0) + get_stat(stats, "post_hits")

    for player in players:
        if player["team_side"] == "home":
            opposing_shots = team_stats["away"]["shots"]
            goals_allowed = match["away_score"] or 0
        else:
            opposing_shots = team_stats["home"]["shots"]
            goals_allowed = match["home_score"] or 0

        saves = float(player.get("saves", 0) or 0)

        player["shots_faced"] = format_number(opposing_shots)
        player["conceded_goals"] = format_number(goals_allowed)
        player["gaa"] = format_number(goals_allowed)

        if opposing_shots > 0:
            player["save_percent"] = f"{saves / opposing_shots:.3f}"
        else:
            player["save_percent"] = "0.000"

    total_possession = (
        team_stats["home"]["possession_time_sec"]
        + team_stats["away"]["possession_time_sec"]
    )

    if total_possession > 0:
        team_stats["home"]["possession_percent"] = round(
            team_stats["home"]["possession_time_sec"] / total_possession * 100,
            1
        )
        team_stats["away"]["possession_percent"] = round(
            team_stats["away"]["possession_time_sec"] / total_possession * 100,
            1
        )

    for side in ("home", "away"):
        for key, value in team_stats[side].items():
            team_stats[side][key] = format_number(value)

    players.sort(
        key=lambda player: (
            0 if player["team_id"] == match.get("winner_team_id") else 1,
            -float(player["points"]),
            -float(player["goals"]),
            -float(player["score"]),
            player["username"].lower()
        )
    )

    return {
        "match": match,
        "team_stats": team_stats,
        "players": players,
        "warnings": match.get("warnings", []),
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

def apply_results(matches, uploaded, active_roster_lookup, roster_snapshots):
    match_details = {}

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

        side_mapping_roster_lookup, side_mapping_roster_source = get_side_mapping_roster_lookup(
            match,
            active_roster_lookup,
            roster_snapshots,
        )

        home_score, away_score, side_mapping = get_scores_from_report_with_rosters(
            data,
            match,
            side_mapping_roster_lookup
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

        match_details[match["match_id"]] = build_match_detail(
            match,
            data,
            side_mapping.get("mapping")
        )

    return match_details


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


def load_active_rosters_full():
    if not ACTIVE_ROSTERS_FILE.exists():
        return {}

    with ACTIVE_ROSTERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    rosters = {}

    for team in data.get("teams", []):
        team_id = team.get("team_id")

        if not team_id:
            continue

        rosters[team_id] = team

    return rosters


def load_existing_roster_snapshots():
    if not ROSTER_SNAPSHOTS_FILE.exists():
        return {}

    with ROSTER_SNAPSHOTS_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def snapshot_team_roster(team_id, active_rosters):
    roster = active_rosters.get(team_id)

    if not roster:
        return {
            "team_id": team_id,
            "team_display_name": "",
            "team": "",
            "team_abbreviation": "",
            "region": "",
            "players": [],
            "slap_ids": [],
        }

    return {
        "team_id": roster.get("team_id", team_id),
        "team_display_name": roster.get("team_display_name", roster.get("team", "")),
        "team": roster.get("team", roster.get("team_display_name", "")),
        "team_abbreviation": roster.get("team_abbreviation", ""),
        "region": roster.get("region", ""),
        "players": roster.get("players", []),
        "slap_ids": roster.get("slap_ids", []),
    }


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
            "schedule_id": match["schedule_id"],
            "season_id": match["season_id"],
            "season_name": match["season_name"],
            "phase": match["phase"],
            "region": match["region"],
            "region_display": match["region_display"],

            "home_team_id": match["home_team_id"],
            "home_team": match["home_team"],
            "away_team_id": match["away_team_id"],
            "away_team": match["away_team"],

            "home_roster": snapshot_team_roster(
                match["home_team_id"],
                active_rosters
            ),
            "away_roster": snapshot_team_roster(
                match["away_team_id"],
                active_rosters
            ),
        }

        created += 1

    write_json(ROSTER_SNAPSHOTS_FILE, snapshots)

    return created, len(snapshots)

def main():
    matches = build_schedule()
    uploaded = scan_log_folders()

    active_roster_lookup = load_active_roster_lookup(ACTIVE_ROSTERS_FILE)
    active_rosters = load_active_rosters_full()
    roster_snapshots = load_existing_roster_snapshots()

    match_details = apply_results(
        matches,
        uploaded,
        active_roster_lookup,
        roster_snapshots,
    )

    standings = build_standings(matches)

    snapshots_created, snapshots_total = build_roster_snapshots(
        matches,
        active_rosters
    )

    write_json(OUT_DIR / "schedule.json", matches)
    write_json(
        OUT_DIR / "matches.json",
        [match for match in matches if match["status"] != "scheduled"]
    )
    write_json(OUT_DIR / "standings.json", standings)

    MATCH_DETAILS_DIR.mkdir(parents=True, exist_ok=True)

    for old_detail_file in MATCH_DETAILS_DIR.glob("*.json"):
        old_detail_file.unlink()

    for match_id, detail in match_details.items():
        write_json(MATCH_DETAILS_DIR / f"{match_id}.json", detail)

    print(f"Match detail files written: {len(match_details)}")

    print(f"Preseason schedule matches: {len(matches)}")
    print(f"Uploaded match folders found: {len(uploaded)}")
    print(f"Completed matches: {sum(1 for m in matches if m['status'] == 'final')}")
    print(f"Teams in standings: {len(standings)}")
    print(f"Roster teams loaded: {len(active_roster_lookup)}")
    print(f"Roster snapshots created: {snapshots_created}")
    print(f"Roster snapshots total: {snapshots_total}")
    print(f"Wrote: {OUT_DIR}")


if __name__ == "__main__":
    main()