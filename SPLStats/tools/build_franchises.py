import json
import re
from pathlib import Path
from collections import defaultdict


FRANCHISES_FILE = Path("../data/franchises.json")
PLAYERS_FILE = Path("../data/all_time_players.json")
TEAM_RECORDS_FILE = Path("../data/team_records.json")
OUT_FILE = Path("../data/franchise_stats.json")


SEASON_ORDER = {
    "winter": 1,
    "spring": 2,
    "summer": 3,
    "fall": 4,
}


LEADER_STATS = [
    "goals",
    "assists",
    "points",
    "shots",
    "takeaways",
    "saves",
    "blocks",
    "faceoff_percent",
    "games_played",
    "seasons_played",
]


# ---------------------------------------------------------------------
# Basic Helpers
# ---------------------------------------------------------------------

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def clean_team_name(team_name):
    team_name = str(team_name).strip()

    return re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        team_name
    ).strip()


def team_lookup_key(team_name):
    return clean_team_name(team_name).lower()


def season_value(season_id):
    try:
        season, year = str(season_id).lower().split("_")
        return int(year) * 10 + SEASON_ORDER.get(season, 0)
    except Exception:
        return 0


def season_in_range(season_id, start_season, end_season):
    value = season_value(season_id)

    start = (
        season_value(start_season)
        if start_season
        else 0
    )

    end = (
        season_value(end_season)
        if end_season
        else 999999
    )

    return start <= value <= end


# ---------------------------------------------------------------------
# Player Stat Helpers
# ---------------------------------------------------------------------

def add_stats(target, stats):
    for stat, value in stats.items():
        if stat.endswith("_percent") or stat == "gaa":
            continue

        target[stat] += float(value or 0)


def finalize_stats(stats):
    stats = dict(stats)

    goals = stats.get("goals", 0)
    assists = stats.get("assists", 0)
    shots = stats.get("shots", 0)
    saves = stats.get("saves", 0)
    shots_against = stats.get("shots_against", 0)
    goals_against = stats.get("goals_against", 0)
    games_played = stats.get("games_played", 0)
    faceoffs_won = stats.get("faceoffs_won", 0)
    faceoffs_lost = stats.get("faceoffs_lost", 0)

    stats["points"] = goals + assists
    stats["shot_percent"] = (goals / shots * 100) if shots else 0
    stats["save_percent"] = (saves / shots_against * 100) if shots_against else 0
    stats["gaa"] = (goals_against / games_played) if games_played else 0

    stats["faceoffs_total"] = faceoffs_won + faceoffs_lost
    stats["faceoff_win_percent"] = (
        faceoffs_won / stats["faceoffs_total"] * 100
        if stats["faceoffs_total"]
        else 0
    )

    return {k: round(v, 2) for k, v in stats.items()}


def get_leader_value(player, stat):
    stats = player["stats"]

    if stat == "faceoff_percent":
        gp = stats.get("games_played", 0)
        won = stats.get("faceoffs_won", 0)
        lost = stats.get("faceoffs_lost", 0)
        total = won + lost

        if gp < 10 or total <= 0:
            return None

        return won / total * 100

    if stat == "seasons_played":
        return len(player.get("seasons", set()))

    return stats.get(stat, 0)


def build_leaders(players):
    leaders = {}
    finalized_players = []

    for player_name, data in players.items():
        stats = finalize_stats(data["stats"])

        finalized_players.append({
            "player_name": player_name,
            "stats": stats,
            "seasons": sorted(data["seasons"]),
        })

    for stat in LEADER_STATS:
        ranked = []

        for player in finalized_players:
            value = get_leader_value(player, stat)

            if value is None or value <= 0:
                continue

            ranked.append({
                "player_name": player["player_name"],
                "value": round(value, 2),
            })

        ranked.sort(
            key=lambda p: p["value"],
            reverse=True
        )

        leaders[stat] = ranked[:5]

    return leaders


def create_scope():
    return {
        "career": defaultdict(float),
        "players": defaultdict(lambda: {
            "stats": defaultdict(float),
            "seasons": set(),
        }),
        "teams": set(),
        "seasons": set(),
        "has_data": False,
    }


def add_row_to_scope(scope, player_name, row):
    stats = row.get("stats", {})

    add_stats(scope["career"], stats)
    add_stats(scope["players"][player_name]["stats"], stats)

    scope["players"][player_name]["seasons"].add(
        row.get("season_id")
    )

    scope["teams"].add(
        row.get("team")
    )

    scope["seasons"].add(
        row.get("season_id")
    )

    scope["has_data"] = True


def finalize_scope(scope):
    return {
        "has_data": scope["has_data"],
        "career": finalize_stats(scope["career"]),
        "leaders": build_leaders(scope["players"]),
        "teams": sorted(t for t in scope["teams"] if t),
        "seasons": sorted(
            (s for s in scope["seasons"] if s),
            key=season_value,
            reverse=True
        ),
    }


def row_belongs_to_franchise(row, franchise):
    team = row.get("team")
    season_id = row.get("season_id")

    if not team or not season_id:
        return False

    row_team_key = team_lookup_key(team)

    for membership in franchise.get("memberships", []):
        membership_team_key = team_lookup_key(
            membership.get("team")
        )

        if membership_team_key != row_team_key:
            continue

        if season_in_range(
            season_id,
            membership.get("start_season"),
            membership.get("end_season")
        ):
            return True

    return False


# ---------------------------------------------------------------------
# Franchise Team Record Helpers
# ---------------------------------------------------------------------

def build_team_record_lookup(team_records):
    lookup = {}

    for record in team_records:
        key = team_lookup_key(record.get("team", ""))

        if key:
            lookup[key] = record

    return lookup


def empty_team_totals():
    return {
        "teams": 0,
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "goal_differential": 0,
        "win_percent": 0,
        "seasons": 0,
    }


def finalize_team_totals(totals, seasons):
    totals["goal_differential"] = (
        totals["goals_for"]
        - totals["goals_against"]
    )

    totals["win_percent"] = (
        totals["wins"] / totals["games_played"]
        if totals["games_played"]
        else 0
    )

    totals["seasons"] = len(seasons)

    totals["win_percent"] = round(
        totals["win_percent"],
        3
    )

    return totals


def calculate_franchise_team_records(team_rows):
    if not team_rows:
        return {}

    def best_by(stat):
        return max(
            team_rows,
            key=lambda row: row.get(stat, 0)
        )

    def fewest_by(stat):
        return min(
            team_rows,
            key=lambda row: row.get(stat, 0)
        )

    def record_entry(row, stat):
        return {
            "team": row.get("team"),
            "value": row.get(stat, 0)
        }

    return {
        "most_games_played": record_entry(
            best_by("games_played"),
            "games_played"
        ),
        "most_wins": record_entry(
            best_by("wins"),
            "wins"
        ),
        "best_win_percent": record_entry(
            best_by("win_percent"),
            "win_percent"
        ),
        "most_goals_for": record_entry(
            best_by("goals_for"),
            "goals_for"
        ),
        "fewest_goals_against": record_entry(
            fewest_by("goals_against"),
            "goals_against"
        ),
        "best_goal_differential": record_entry(
            best_by("goal_differential"),
            "goal_differential"
        ),
    }


def calculate_franchise_team_totals(
    franchise,
    team_record_lookup
):
    totals = empty_team_totals()
    seasons = set()
    team_rows = []

    for membership in franchise.get("memberships", []):
        membership_team = membership.get("team", "")
        membership_team_key = team_lookup_key(membership_team)

        team_record = team_record_lookup.get(
            membership_team_key
        )

        if not team_record:
            print(
                f"WARNING: No team record found for "
                f"{membership_team}"
            )
            continue

        row = {
            "team": membership_team,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_differential": 0,
            "win_percent": 0,
            "seasons": [],
            "start_season": membership.get("start_season"),
            "end_season": membership.get("end_season"),
            "order": membership.get("order"),
        }

        row_seasons = set()

        for season_row in team_record.get("by_season", []):
            season_id = season_row.get("season_id")

            if not season_in_range(
                season_id,
                membership.get("start_season"),
                membership.get("end_season")
            ):
                continue

            gp = int(season_row.get("games_played", 0))
            wins = int(season_row.get("wins", 0))
            losses = int(season_row.get("losses", 0))
            gf = int(season_row.get("goals_for", 0))
            ga = int(season_row.get("goals_against", 0))

            totals["games_played"] += gp
            totals["wins"] += wins
            totals["losses"] += losses
            totals["goals_for"] += gf
            totals["goals_against"] += ga

            row["games_played"] += gp
            row["wins"] += wins
            row["losses"] += losses
            row["goals_for"] += gf
            row["goals_against"] += ga

            seasons.add(season_id)
            row_seasons.add(season_id)

        if row["games_played"] > 0:
            row["goal_differential"] = (
                row["goals_for"]
                - row["goals_against"]
            )

            row["win_percent"] = round(
                row["wins"] / row["games_played"],
                3
            )

            row["seasons"] = sorted(
                row_seasons,
                key=season_value
            )

            team_rows.append(row)

    totals["teams"] = len(team_rows)

    totals = finalize_team_totals(
        totals,
        seasons
    )

    team_rows.sort(
        key=lambda row: (
            row.get("order") or 999,
            season_value(row.get("start_season")),
            row.get("team", "").lower()
        )
    )

    return {
        "team_totals": totals,
        "team_records": calculate_franchise_team_records(
            team_rows
        ),
        "team_rows": team_rows,
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    franchises = load_json(FRANCHISES_FILE)
    players = load_json(PLAYERS_FILE)
    team_records = load_json(TEAM_RECORDS_FILE)

    team_record_lookup = build_team_record_lookup(
        team_records
    )

    output = []

    for franchise in franchises:
        all_divisions = create_scope()
        pro = create_scope()

        for player in players:
            player_name = player.get(
                "player_name",
                "Unknown"
            )

            for row in player.get("by_season", []):
                if not row_belongs_to_franchise(
                    row,
                    franchise
                ):
                    continue

                add_row_to_scope(
                    all_divisions,
                    player_name,
                    row
                )

                if (
                    row.get("division") == "Pro Division"
                    and row.get("season_type") == "regular_season"
                ):
                    add_row_to_scope(
                        pro,
                        player_name,
                        row
                    )

        team_stats = calculate_franchise_team_totals(
            franchise,
            team_record_lookup
        )

        output.append({
            "franchise_id": franchise.get("franchise_id"),
            "franchise_name": franchise.get("franchise_name"),
            "status": franchise.get("status"),
            "description": franchise.get("description", ""),
            "founders": franchise.get("founders", []),
            "owners": franchise.get("owners", []),
            "part_owners": franchise.get("part_owners", []),
            "coaches": franchise.get("coaches", []),
            "hall_of_fame": franchise.get("hall_of_fame", []),
            "memberships": franchise.get("memberships", []),

            "team_totals": team_stats["team_totals"],
            "team_records": team_stats["team_records"],
            "team_rows": team_stats["team_rows"],

            "stats": {
                "pro": finalize_scope(pro),
                "all_divisions": finalize_scope(all_divisions),
            }
        })

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Franchises written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()