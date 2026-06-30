import json
from collections import defaultdict
from functools import cmp_to_key
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"
SEASON_TYPE = "regular_season"

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"

SCHEDULE_FILE = REGULAR_SEASON_DIR / "schedule.json"
MATCHES_FILE = REGULAR_SEASON_DIR / "matches.json"
ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"

OUT_FILE = REGULAR_SEASON_DIR / "standings.json"


def clean(value):
    return str(value or "").strip()


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


def get_match_array(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("matches"), list):
        return data["matches"]

    if isinstance(data, dict) and isinstance(data.get("schedule"), list):
        return data["schedule"]

    return []


def normalize_division(value):
    return clean(value).lower().replace("-", "_").replace(" ", "_")


def load_active_roster_lookup():
    data = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})
    lookup = {}

    for team in data.get("teams", []):
        team_id = clean(team.get("team_id"))

        if team_id:
            lookup[team_id] = team

    return lookup


def get_roster_team_meta(team_id, active_rosters):
    return active_rosters.get(team_id, {})


def get_team_conference(team_id, fallback, active_rosters):
    roster = get_roster_team_meta(team_id, active_rosters)

    return clean(
        roster.get("conference")
        or fallback
        or "1"
    )


def get_team_region(team_id, fallback, active_rosters):
    roster = get_roster_team_meta(team_id, active_rosters)

    return clean(
        roster.get("region")
        or fallback
        or "unknown"
    )


def get_team_division(team_id, fallback, active_rosters):
    roster = get_roster_team_meta(team_id, active_rosters)

    return normalize_division(
        roster.get("division")
        or fallback
        or ""
    )


def empty_standing(team_id, team_name, match, side, active_rosters):
    roster = get_roster_team_meta(team_id, active_rosters)

    division = get_team_division(
        team_id,
        match.get("division") or match.get(f"{side}_division"),
        active_rosters,
    )

    region = get_team_region(
        team_id,
        match.get("region") or match.get(f"{side}_region"),
        active_rosters,
    )

    conference = get_team_conference(
        team_id,
        match.get(f"{side}_conference") or match.get("conference"),
        active_rosters,
    )

    return {
        "rank": None,
        "division_rank": None,
        "conference_rank": None,

        "team_id": team_id,
        "team": team_name,
        "team_display_name": (
            roster.get("team_display_name")
            or roster.get("team")
            or team_name
        ),
        "team_abbreviation": roster.get("team_abbreviation", ""),

        "season_id": SEASON_ID,
        "season_name": SEASON_NAME,
        "season_type": SEASON_TYPE,

        "region": region,
        "division": division,
        "conference": conference,

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

        "tiebreaker_status": "none",
        "tiebreaker_notes": [],
    }


def ensure_team(standings, team_id, team_name, match, side, active_rosters):
    if not team_id:
        return None

    if team_id not in standings:
        standings[team_id] = empty_standing(
            team_id,
            team_name,
            match,
            side,
            active_rosters,
        )

    return standings[team_id]


def is_final(match):
    return clean(match.get("status")).lower() in {
        "final",
        "completed",
        "complete",
    }


def as_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def add_recent_result(team_results, team_id, result, match, goals_for, goals_against):
    team_results[team_id].append({
        "match_id": match.get("match_id"),
        "source_id": match.get("source_id") or match.get("schedule_id"),
        "result": result,
        "overtime": bool(match.get("overtime")),
        "goals_for": goals_for,
        "goals_against": goals_against,
    })


def build_basic_records(schedule_matches, completed_matches, active_rosters):
    standings = {}
    team_results = defaultdict(list)

    # First include every scheduled team, even teams with 0 GP.
    for match in schedule_matches:
        ensure_team(
            standings,
            match.get("home_team_id"),
            match.get("home_team"),
            match,
            "home",
            active_rosters,
        )

        ensure_team(
            standings,
            match.get("away_team_id"),
            match.get("away_team"),
            match,
            "away",
            active_rosters,
        )

    for match in completed_matches:
        if not is_final(match):
            continue

        home_id = match.get("home_team_id")
        away_id = match.get("away_team_id")

        home = ensure_team(
            standings,
            home_id,
            match.get("home_team"),
            match,
            "home",
            active_rosters,
        )

        away = ensure_team(
            standings,
            away_id,
            match.get("away_team"),
            match,
            "away",
            active_rosters,
        )

        if not home or not away:
            continue

        home_score = as_int(match.get("home_score"))
        away_score = as_int(match.get("away_score"))
        overtime = bool(match.get("overtime"))

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

                add_recent_result(team_results, home_id, "W", match, home_score, away_score)
                add_recent_result(team_results, away_id, "OTL", match, away_score, home_score)
            else:
                away["regulation_losses"] += 1

                add_recent_result(team_results, home_id, "W", match, home_score, away_score)
                add_recent_result(team_results, away_id, "L", match, away_score, home_score)

        elif away_score > home_score:
            away["wins"] += 1
            away["points"] += 2

            if overtime:
                home["overtime_losses"] += 1
                home["points"] += 1

                add_recent_result(team_results, away_id, "W", match, away_score, home_score)
                add_recent_result(team_results, home_id, "OTL", match, home_score, away_score)
            else:
                home["regulation_losses"] += 1

                add_recent_result(team_results, away_id, "W", match, away_score, home_score)
                add_recent_result(team_results, home_id, "L", match, home_score, away_score)

        else:
            home["tiebreaker_notes"].append(f"Tie score detected in {match.get('match_id')}")
            away["tiebreaker_notes"].append(f"Tie score detected in {match.get('match_id')}")

    for team_id, team in standings.items():
        team["goal_diff"] = team["goals_for"] - team["goals_against"]

        last_5_games = team_results.get(team_id, [])[-5:]

        wins = sum(1 for game in last_5_games if game["result"] == "W")
        regulation_losses = sum(1 for game in last_5_games if game["result"] == "L")
        overtime_losses = sum(1 for game in last_5_games if game["result"] == "OTL")

        team["last_5"] = f"{wins}-{regulation_losses}-{overtime_losses}"
        team["last_5_games"] = last_5_games

    return standings


def get_head_to_head_stats(team_a_id, team_b_id, completed_matches):
    stats = {
        team_a_id: {
            "wins": 0,
            "losses": 0,
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
        },
        team_b_id: {
            "wins": 0,
            "losses": 0,
            "points": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_diff": 0,
        },
        "games_played": 0,
    }

    for match in completed_matches:
        if not is_final(match):
            continue

        home_id = match.get("home_team_id")
        away_id = match.get("away_team_id")

        if {home_id, away_id} != {team_a_id, team_b_id}:
            continue

        home_score = as_int(match.get("home_score"))
        away_score = as_int(match.get("away_score"))
        overtime = bool(match.get("overtime"))

        stats["games_played"] += 1

        stats[home_id]["goals_for"] += home_score
        stats[home_id]["goals_against"] += away_score

        stats[away_id]["goals_for"] += away_score
        stats[away_id]["goals_against"] += home_score

        if home_score > away_score:
            stats[home_id]["wins"] += 1
            stats[away_id]["losses"] += 1

            stats[home_id]["points"] += 2
            if overtime:
                stats[away_id]["points"] += 1

        elif away_score > home_score:
            stats[away_id]["wins"] += 1
            stats[home_id]["losses"] += 1

            stats[away_id]["points"] += 2
            if overtime:
                stats[home_id]["points"] += 1

    for team_id in (team_a_id, team_b_id):
        stats[team_id]["goal_diff"] = (
            stats[team_id]["goals_for"]
            - stats[team_id]["goals_against"]
        )

    return stats


def compare_teams_with_spl_tiebreakers(team_a, team_b, completed_matches):
    """
    SPL regular-season tiebreakers:

    1. Standing points
    2. Head-to-head record
    3. Head-to-head standing points
    4. Head-to-head goal differential
    5. Overall goal differential
    6. Best-of-1 match

    Returns:
    -1 if team_a ranks above team_b
     1 if team_b ranks above team_a
     0 if unresolved
    """

    # 1. Standing points
    if team_a["points"] != team_b["points"]:
        return -1 if team_a["points"] > team_b["points"] else 1

    team_a_id = team_a["team_id"]
    team_b_id = team_b["team_id"]

    h2h = get_head_to_head_stats(team_a_id, team_b_id, completed_matches)

    if h2h["games_played"] > 0:
        # 2. Head-to-head record
        if h2h[team_a_id]["wins"] != h2h[team_b_id]["wins"]:
            return -1 if h2h[team_a_id]["wins"] > h2h[team_b_id]["wins"] else 1

        # 3. Head-to-head standing points
        if h2h[team_a_id]["points"] != h2h[team_b_id]["points"]:
            return -1 if h2h[team_a_id]["points"] > h2h[team_b_id]["points"] else 1

        # 4. Head-to-head goal differential
        if h2h[team_a_id]["goal_diff"] != h2h[team_b_id]["goal_diff"]:
            return -1 if h2h[team_a_id]["goal_diff"] > h2h[team_b_id]["goal_diff"] else 1

    # 5. Overall goal differential
    if team_a["goal_diff"] != team_b["goal_diff"]:
        return -1 if team_a["goal_diff"] > team_b["goal_diff"] else 1

    # Stable fallback for display only.
    # This does NOT represent an official SPL tiebreaker.
    if team_a["team_display_name"].lower() != team_b["team_display_name"].lower():
        return -1 if team_a["team_display_name"].lower() < team_b["team_display_name"].lower() else 1

    return 0


def add_tiebreaker_notes(sorted_rows, completed_matches):
    point_groups = defaultdict(list)

    for row in sorted_rows:
        group_key = (
            row["division"],
            row["conference"],
            row["points"],
        )

        point_groups[group_key].append(row)

    for group in point_groups.values():
        if len(group) < 2:
            continue

        for team in group:
            team["tiebreaker_status"] = "applied"
            team["tiebreaker_notes"].append(
                "Tied on standing points; SPL tiebreakers checked."
            )

        for i, team_a in enumerate(group):
            for team_b in group[i + 1:]:
                h2h = get_head_to_head_stats(
                    team_a["team_id"],
                    team_b["team_id"],
                    completed_matches,
                )

                if h2h["games_played"] == 0 and team_a["goal_diff"] == team_b["goal_diff"]:
                    team_a["tiebreaker_status"] = "bo1_required"
                    team_b["tiebreaker_status"] = "bo1_required"

                    team_a["tiebreaker_notes"].append(
                        f"Still tied with {team_b['team_display_name']}; Best-of-1 may be required."
                    )
                    team_b["tiebreaker_notes"].append(
                        f"Still tied with {team_a['team_display_name']}; Best-of-1 may be required."
                    )


def rank_rows(rows, completed_matches, rank_field):
    sorted_rows = sorted(
        rows,
        key=cmp_to_key(
            lambda a, b: compare_teams_with_spl_tiebreakers(
                a,
                b,
                completed_matches,
            )
        ),
    )

    rank = 0
    previous = None

    for index, row in enumerate(sorted_rows, start=1):
        if previous is None:
            rank = 1
        else:
            compare = compare_teams_with_spl_tiebreakers(
                previous,
                row,
                completed_matches,
            )

            if compare != 0:
                rank = index

        row[rank_field] = rank
        previous = row

    add_tiebreaker_notes(sorted_rows, completed_matches)

    return sorted_rows


def build_division_and_conference_ranks(standings, completed_matches):
    all_rows = list(standings.values())

    by_division = defaultdict(list)
    by_division_conference = defaultdict(list)

    for row in all_rows:
        by_division[row["division"]].append(row)
        by_division_conference[(row["division"], row["conference"])].append(row)

    for division, rows in by_division.items():
        rank_rows(rows, completed_matches, "division_rank")

    for key, rows in by_division_conference.items():
        rank_rows(rows, completed_matches, "conference_rank")

    return all_rows


def get_conference_playoff_config(team_count):
    if team_count == 14:
        return {
            "auto_per_conference": 3,
            "wildcard_count": 2,
            "bubble_count": 4,
            "playoff_team_count": 8,
        }

    if team_count == 12:
        return {
            "auto_per_conference": 2,
            "wildcard_count": 2,
            "bubble_count": 4,
            "playoff_team_count": 6,
        }

    return {
        "auto_per_conference": 0,
        "wildcard_count": 0,
        "bubble_count": 4,
        "playoff_team_count": 0,
    }


def assign_playoff_buckets(rows, completed_matches):
    by_division = defaultdict(list)

    for row in rows:
        by_division[row["division"]].append(row)

    for division, division_rows in by_division.items():
        conferences = defaultdict(list)

        for row in division_rows:
            conferences[row["conference"]].append(row)

        has_multiple_conferences = len(conferences) > 1
        config = get_conference_playoff_config(len(division_rows))

        for row in division_rows:
            row["playoff_bucket"] = "standings"
            row["playoff_seed"] = None
            row["wildcard_rank"] = None
            row["playoff_config"] = config

        if not has_multiple_conferences or config["auto_per_conference"] <= 0:
            continue

        auto_team_ids = set()

        for conference, conference_rows in conferences.items():
            ranked = rank_rows(conference_rows, completed_matches, "conference_rank")

            for row in ranked[:config["auto_per_conference"]]:
                row["playoff_bucket"] = "automatic_qualifier"
                auto_team_ids.add(row["team_id"])

        wildcard_pool = [
            row for row in division_rows
            if row["team_id"] not in auto_team_ids
        ]

        wildcard_ranked = rank_rows(wildcard_pool, completed_matches, "wildcard_rank")

        for index, row in enumerate(wildcard_ranked, start=1):
            row["wildcard_rank"] = index

            if index <= config["wildcard_count"]:
                row["playoff_bucket"] = "wildcard"
            elif index <= config["wildcard_count"] + config["bubble_count"]:
                row["playoff_bucket"] = "bubble"
            else:
                row["playoff_bucket"] = "chase"


def sort_final_output(rows):
    return sorted(
        rows,
        key=lambda row: (
            row["region"],
            row["division"],
            row["conference"],
            row["conference_rank"] or 999,
            row["division_rank"] or 999,
            row["team_display_name"].lower(),
        )
    )


def build_regular_standings():
    schedule_data = load_json(SCHEDULE_FILE, {"matches": []})
    matches_data = load_json(MATCHES_FILE, {"matches": []})
    active_rosters = load_active_roster_lookup()

    schedule_matches = get_match_array(schedule_data)
    completed_matches = [
        match for match in get_match_array(matches_data)
        if is_final(match)
    ]

    standings = build_basic_records(
        schedule_matches,
        completed_matches,
        active_rosters,
    )

    rows = build_division_and_conference_ranks(
        standings,
        completed_matches,
    )

    assign_playoff_buckets(rows, completed_matches)

    rows = sort_final_output(rows)

    output = {
        "season_id": SEASON_ID,
        "season_name": SEASON_NAME,
        "season_type": SEASON_TYPE,
        "generated_from": {
            "schedule": str(SCHEDULE_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
            "matches": str(MATCHES_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
            "active_rosters": str(ACTIVE_ROSTERS_FILE.relative_to(BASE_DIR)).replace("\\", "/"),
        },
        "team_count": len(rows),
        "completed_match_count": len(completed_matches),
        "standings": rows,
        "tiebreakers": [
            "Standing Points",
            "Head to Head Record",
            "Head to Head Standing Points",
            "Head to Head Goal Differential",
            "Overall Goal Differential",
            "Best of 1 Match",
        ],
    }

    write_json(OUT_FILE, output)

    return output


def main():
    output = build_regular_standings()

    print("Regular season standings build complete.")
    print(f"Teams: {output['team_count']}")
    print(f"Completed matches: {output['completed_match_count']}")
    print(f"Wrote: {OUT_FILE}")


if __name__ == "__main__":
    main()