import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"
SEASON_TYPE = "regular_season"

LIVE_SEASON_DIR = BASE_DIR / "data" / "live_season" / SEASON_ID
REGULAR_SEASON_DIR = LIVE_SEASON_DIR / "regular_season"

MATCH_DETAILS_DIR = REGULAR_SEASON_DIR / "match_details"
ACTIVE_ROSTERS_FILE = LIVE_SEASON_DIR / "active_rosters.json"
ROSTER_SNAPSHOTS_FILE = REGULAR_SEASON_DIR / "roster_snapshots.json"

OUT_FILE = REGULAR_SEASON_DIR / "leaders.json"


COUNTING_STATS = [
    "goals",
    "assists",
    "points",
    "shots",
    "saves",
    "blocks",
    "faceoffs_won",
    "faceoffs_lost",
    "takeaways",
    "turnovers",
    "post_hits",
    "passes",
    "possession_time_sec",
    "score",
]


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


def as_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def as_int_if_whole(value):
    number = as_float(value)

    if number == int(number):
        return int(number)

    return round(number, 3)


def normalize_division(value):
    return clean(value).lower().replace("-", "_").replace(" ", "_")


def normalize_player_id(value):
    return (
        clean(value)
        .lower()
        .replace("&", "and")
        .replace("$", "s")
        .replace("@", "a")
        .replace("!", "i")
        .replace("’", "")
        .replace("'", "")
    )


def make_url_id(value):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        normalize_player_id(value)
    ).strip("_")


def make_stat_row_id(division, team_id, slap_id):
    return "__".join([
        normalize_division(division) or "unknown",
        clean(team_id) or "unknown_team",
        clean(slap_id) or "unknown_player",
    ])


def get_match_detail_files():
    if not MATCH_DETAILS_DIR.exists():
        return []

    return sorted(
        path for path in MATCH_DETAILS_DIR.glob("*.json")
        if path.is_file()
    )


def get_players_from_detail(detail):
    if isinstance(detail.get("players"), list):
        return detail["players"]

    if isinstance(detail.get("player_stats"), list):
        return detail["player_stats"]

    return []


def get_player_slap_id(player):
    return clean(
        player.get("slap_id")
        or player.get("game_user_id")
    )


def get_player_team_id(player):
    return clean(player.get("team_id"))


def get_roster_player_slap_ids(player):
    values = [
        player.get("slap_id"),
        player.get("game_user_id"),
        player.get("id"),
        player.get("slap_ids"),
    ]

    slap_ids = []

    for value in values:
        if isinstance(value, list):
            slap_ids.extend(clean(item) for item in value if clean(item))
        elif clean(value):
            slap_ids.append(clean(value))

    return slap_ids


def get_roster_player_id(player):
    return clean(
        player.get("player_id")
        or player.get("url_id")
        or player.get("id")
    )


def get_roster_player_display_name(player):
    return clean(
        player.get("player_display_name")
        or player.get("steam_name")
        or player.get("display_name")
        or player.get("player_name")
        or player.get("name")
        or player.get("username")
    )


def load_active_roster_player_lookup():
    data = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})

    by_slap_and_team = {}
    by_slap = {}

    for team in data.get("teams", []):
        team_id = clean(team.get("team_id"))

        team_name = clean(
            team.get("team_display_name")
            or team.get("team")
            or team.get("team_name")
            or team_id
        )

        division = normalize_division(team.get("division"))
        region = clean(team.get("region"))

        for player in team.get("players", []):
            slap_ids = get_roster_player_slap_ids(player)

            if not slap_ids:
                continue

            roster_row = {
                "slap_id": slap_ids[0],
                "player_id": get_roster_player_id(player),
                "player_display_name": get_roster_player_display_name(player),
                "steam_name": get_roster_player_display_name(player),

                "team_id": team_id,
                "team": team_name,
                "team_display_name": team_name,
                "division": division,
                "region": region,

                "role": clean(player.get("role")),
                "jersey_number": clean(player.get("jersey_number")),
            }

            for slap_id in slap_ids:
                by_slap_and_team[(slap_id, team_id)] = roster_row
                by_slap.setdefault(slap_id, []).append(roster_row)

    return {
        "by_slap_and_team": by_slap_and_team,
        "by_slap": by_slap,
    }


def build_snapshot_player_lookup():
    snapshots = load_json(ROSTER_SNAPSHOTS_FILE, {})

    by_match_team_slap = {}
    by_team_slap = {}

    for match_id, snapshot in snapshots.items():
        for team_id_key, roster_key in (
            ("home_team_id", "home_roster"),
            ("away_team_id", "away_roster"),
        ):
            team_id = clean(snapshot.get(team_id_key))
            roster = snapshot.get(roster_key, {}) or {}

            team_name = clean(
                roster.get("team_display_name")
                or roster.get("team")
                or snapshot.get(team_id_key)
            )

            division = normalize_division(
                snapshot.get("division")
                or roster.get("division")
            )

            region = clean(
                snapshot.get("region")
                or roster.get("region")
            )

            for player in roster.get("players", []):
                slap_ids = get_roster_player_slap_ids(player)

                if not slap_ids or not team_id:
                    continue

                snapshot_row = {
                    "slap_id": slap_ids[0],
                    "player_id": get_roster_player_id(player),
                    "player_display_name": get_roster_player_display_name(player),
                    "steam_name": get_roster_player_display_name(player),

                    "team_id": team_id,
                    "team": team_name,
                    "team_display_name": team_name,
                    "division": division,
                    "region": region,

                    "role": clean(player.get("role")),
                    "jersey_number": clean(player.get("jersey_number")),
                }

                for slap_id in slap_ids:
                    by_match_team_slap[(match_id, team_id, slap_id)] = snapshot_row
                    by_team_slap.setdefault((team_id, slap_id), snapshot_row)

    return {
        "by_match_team_slap": by_match_team_slap,
        "by_team_slap": by_team_slap,
    }


def resolve_player_identity(match_id, player, snapshot_lookup, active_lookup):
    slap_id = get_player_slap_id(player)
    team_id = get_player_team_id(player)

    snapshot_exact = snapshot_lookup.get("by_match_team_slap", {})
    snapshot_team = snapshot_lookup.get("by_team_slap", {})
    active_exact = active_lookup.get("by_slap_and_team", {})
    active_by_slap = active_lookup.get("by_slap", {})

    if match_id and team_id and slap_id and (match_id, team_id, slap_id) in snapshot_exact:
        return snapshot_exact[(match_id, team_id, slap_id)]

    if team_id and slap_id and (team_id, slap_id) in snapshot_team:
        return snapshot_team[(team_id, slap_id)]

    if team_id and slap_id and (slap_id, team_id) in active_exact:
        return active_exact[(slap_id, team_id)]

    possible_players = active_by_slap.get(slap_id, [])

    if len(possible_players) == 1:
        return possible_players[0]

    return {}


def make_empty_stat_row(match_id, match, player, snapshot_lookup, active_lookup):
    slap_id = get_player_slap_id(player)
    team_id = get_player_team_id(player)

    division = normalize_division(
        match.get("division")
        or player.get("division")
    )

    identity = resolve_player_identity(
        match_id,
        player,
        snapshot_lookup,
        active_lookup,
    )

    raw_username = clean(player.get("username"))

    player_display_name = clean(
        identity.get("player_display_name")
        or identity.get("steam_name")
        or player.get("player_display_name")
        or player.get("player_name")
        or raw_username
        or slap_id
        or "Unknown Player"
    )

    player_id = clean(
        identity.get("player_id")
        or player.get("player_id")
        or make_url_id(player_display_name or raw_username or slap_id)
    )

    team_display_name = clean(
        identity.get("team_display_name")
        or identity.get("team")
        or player.get("team")
        or team_id
    )

    region = clean(
        identity.get("region")
        or match.get("region")
        or match.get("home_region")
        or match.get("away_region")
    )

    stat_row_id = make_stat_row_id(division, team_id, slap_id)

    return {
        "stat_row_id": stat_row_id,

        "slap_id": slap_id,
        "steam_name": clean(identity.get("steam_name") or player_display_name),
        "player_id": player_id,
        "player_name": raw_username,
        "player_display_name": player_display_name,

        "team_id": team_id,
        "team": team_display_name,
        "team_display_name": team_display_name,

        "division": division,
        "region": region,

        "role": clean(identity.get("role")),
        "jersey_number": clean(identity.get("jersey_number")),

        "games_played": 0,
        "matches": [],

        "goals": 0,
        "assists": 0,
        "points": 0,
        "shots": 0,
        "saves": 0,
        "blocks": 0,
        "faceoffs_won": 0,
        "faceoffs_lost": 0,
        "takeaways": 0,
        "turnovers": 0,
        "post_hits": 0,
        "passes": 0,
        "possession_time_sec": 0,
        "score": 0,

        "conceded_goals": 0,
        "shots_faced": 0,

        "save_percent": "0.000",
        "shooting_percent": "0.000",
        "faceoff_percent": "0.000",
    }


def aggregate_match_players(match_id, match, players):
    """
    Collapses duplicate player rows within one match before adding them
    to the season totals.
    """

    per_match = {}

    division = normalize_division(match.get("division"))

    for player in players:
        slap_id = get_player_slap_id(player)
        team_id = get_player_team_id(player)

        if not slap_id or not team_id:
            continue

        stat_row_id = make_stat_row_id(division, team_id, slap_id)

        if stat_row_id not in per_match:
            per_match[stat_row_id] = {
                "match_id": match_id,
                "division": division,
                "team_id": team_id,
                "slap_id": slap_id,
                "player": player,
                "stats": {stat: 0 for stat in COUNTING_STATS},
                "conceded_goals": 0,
                "shots_faced": 0,
            }

        row = per_match[stat_row_id]

        for stat in COUNTING_STATS:
            row["stats"][stat] += as_float(player.get(stat))

        row["conceded_goals"] += as_float(player.get("conceded_goals"))
        row["shots_faced"] += as_float(player.get("shots_faced"))

    return per_match.values()


def aggregate_players():
    active_lookup = load_active_roster_player_lookup()
    snapshot_lookup = build_snapshot_player_lookup()

    stat_rows = {}

    for detail_file in get_match_detail_files():
        detail = load_json(detail_file, {})
        match = detail.get("match", {})
        match_id = clean(match.get("match_id") or detail_file.stem)

        match_players = aggregate_match_players(
            match_id,
            match,
            get_players_from_detail(detail),
        )

        for match_player in match_players:
            stat_row_id = make_stat_row_id(
                match_player["division"],
                match_player["team_id"],
                match_player["slap_id"],
            )

            if stat_row_id not in stat_rows:
                stat_rows[stat_row_id] = make_empty_stat_row(
                    match_id,
                    match,
                    match_player["player"],
                    snapshot_lookup,
                    active_lookup,
                )

            row = stat_rows[stat_row_id]

            if match_id not in row["matches"]:
                row["games_played"] += 1
                row["matches"].append(match_id)

            for stat in COUNTING_STATS:
                row[stat] += match_player["stats"].get(stat, 0)

            row["conceded_goals"] += match_player["conceded_goals"]
            row["shots_faced"] += match_player["shots_faced"]

    for row in stat_rows.values():
        shots = as_float(row["shots"])
        goals = as_float(row["goals"])

        faceoffs_won = as_float(row["faceoffs_won"])
        faceoffs_lost = as_float(row["faceoffs_lost"])
        faceoffs_total = faceoffs_won + faceoffs_lost

        saves = as_float(row["saves"])
        shots_faced = as_float(row["shots_faced"])

        row["shooting_percent"] = f"{goals / shots:.3f}" if shots > 0 else "0.000"
        row["faceoff_percent"] = f"{faceoffs_won / faceoffs_total:.3f}" if faceoffs_total > 0 else "0.000"
        row["save_percent"] = f"{saves / shots_faced:.3f}" if shots_faced > 0 else "0.000"

        for stat in COUNTING_STATS + ["conceded_goals", "shots_faced"]:
            row[stat] = as_int_if_whole(row[stat])

    return sorted(
        stat_rows.values(),
        key=lambda row: (
            row["division"],
            row["team_display_name"].lower(),
            row["player_display_name"].lower(),
        )
    )


def build_leaders():
    players = aggregate_players()

    output = {
        "season_id": SEASON_ID,
        "season_name": SEASON_NAME,
        "season_type": SEASON_TYPE,
        "player_count": len(players),
        "players": players,
    }

    write_json(OUT_FILE, output)

    return output


def main():
    leaders = build_leaders()

    print("Regular season player stats build complete.")
    print(f"Players/stat rows: {leaders['player_count']}")
    print(f"Wrote: {OUT_FILE}")


if __name__ == "__main__":
    main()