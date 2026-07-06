import argparse
import json
from pathlib import Path
from collections import defaultdict

from team_identity import load_team_identities, resolve_team_identity
from player_identity import load_player_identities, resolve_player_identity


LIVE_ROOT = Path("../data/live_season")
OUT_DIR = Path("../data/seasons")


DIVISION_LABELS = {
    "pro": "Pro",
    "challenger": "Challenger",
    "intermediate": "Intermediate",
    "prospect": "Prospect",
    "open": "Open",
    "central_a": "Central A",
    "central_b": "Central B",
    "central_c": "Central C",
    "central_d": "Central D",
    "masters": "Masters",
    "contenders": "Contenders",
}

LIVE_STAT_KEYS = [
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
    "conceded_goals",
    "shots_faced",
    "score",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def season_label_from_id(season_id):
    parts = str(season_id or "").split("_")

    if len(parts) == 2:
        return f"{parts[0].title()} {parts[1]}"

    return str(season_id or "").replace("_", " ").title()


def get_match_details_dir(season_id, season_type):
    return (
        LIVE_ROOT
        / season_id
        / season_type
        / "match_details"
    )


def get_team_identity_from_match(match, team_side, team_alias_lookup):
    team_name = match.get(f"{team_side}_team") or "Unknown"
    team_id_from_match = match.get(f"{team_side}_team_id")

    identity = resolve_team_identity(
        team_name,
        team_alias_lookup
    )

    # Prefer explicit live-season team_id if present.
    if team_id_from_match:
        identity["team_id"] = team_id_from_match

    return identity


def get_opponent_side(team_side):
    return "away" if team_side == "home" else "home"


def build_live_season(season_id, season_type):
    match_details_dir = get_match_details_dir(season_id, season_type)

    if not match_details_dir.exists():
        print(f"Match details folder not found: {match_details_dir.resolve()}")
        return []

    alias_lookup, _ = load_player_identities()
    team_alias_lookup, _ = load_team_identities()

    rows = {}

    match_files = sorted(match_details_dir.rglob("*.json"))

    for match_file in match_files:
        data = load_json(match_file)

        match = data.get("match", {})
        players = data.get("players", [])

        if match.get("status") and match.get("status") != "final":
            print(f"SKIP non-final match: {match_file.name}")
            continue

        if not players:
            print(f"SKIP no players: {match_file.name}")
            continue

        match_season_id = match.get("season_id") or season_id
        match_season_type = match.get("season_type") or season_type
        season_name = match.get("season_name") or season_label_from_id(match_season_id)

        raw_division = (
            match.get("division")
            or match.get("home_division")
            or match.get("away_division")
            or "unknown_division"
        )

        division = DIVISION_LABELS.get(raw_division, raw_division)

        team_identities = {
            "home": get_team_identity_from_match(match, "home", team_alias_lookup),
            "away": get_team_identity_from_match(match, "away", team_alias_lookup),
        }

        for player in players:
            team_side = player.get("team_side")

            if team_side not in ["home", "away"]:
                print(f"SKIP player with bad team_side in {match_file.name}: {player.get('username')}")
                continue

            raw_player_name = player.get("username") or player.get("player_name")

            if not raw_player_name:
                print(f"SKIP player with no username in {match_file.name}")
                continue

            player_identity = resolve_player_identity(
                raw_player_name,
                alias_lookup
            )

            team_identity = team_identities[team_side]

            player_id = player_identity["player_id"]
            player_display_name = player_identity["player_display_name"]

            team_id = player.get("team_id") or team_identity["team_id"]
            team_display_name = player.get("team") or team_identity["team_display_name"]
            team_aliases = team_identity.get("aliases", [])

            key = (
                match_season_id,
                match_season_type,
                division,
                team_id,
                player_id,
            )

            if key not in rows:
                rows[key] = {
                    "season": season_name,
                    "season_id": match_season_id,
                    "season_type": match_season_type,
                    "division": division,

                    "team_id": team_id,
                    "team": team_display_name,
                    "team_name": team_display_name,
                    "team_display_name": team_display_name,
                    "team_aliases": team_aliases,
                    "raw_team": team_display_name,

                    "player_id": player_id,
                    "player_name": player_display_name,
                    "player_display_name": player_display_name,
                    "aliases": player_identity.get("aliases", []),

                    "stats": defaultdict(float),

                    # Internal only, removed before output.
                    "_match_ids": set(),
                }

            row = rows[key]
            stats = row["stats"]

            match_id = match.get("match_id") or str(match_file)

            # Count this player once per match detail file.
            if match_id not in row["_match_ids"]:
                stats["games_played"] += 1
                row["_match_ids"].add(match_id)

            for stat_key in LIVE_STAT_KEYS:
                stats[stat_key] += safe_float(player.get(stat_key, 0))

            # Compatibility with all-time calculations.
            stats["goals_against"] += safe_float(player.get("conceded_goals", 0))
            stats["shots_against"] += safe_float(player.get("shots_faced", 0))

            # Live data currently has total assists already.
            primary = safe_float(player.get("primary_assists", 0))
            secondary = safe_float(player.get("secondary_assists", 0))

            if primary or secondary:
                stats["primary_assists"] += primary
                stats["secondary_assists"] += secondary

    output = []

    for row in rows.values():
        stats = dict(row["stats"])

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

        stats["shot_percent"] = (
            goals / shots * 100
            if shots
            else 0
        )

        stats["save_percent"] = (
            saves / shots_against * 100
            if shots_against
            else 0
        )

        stats["gaa"] = (
            goals_against / games_played
            if games_played
            else 0
        )

        stats["faceoffs_total"] = faceoffs_won + faceoffs_lost

        stats["faceoff_win_percent"] = (
            faceoffs_won / stats["faceoffs_total"] * 100
            if stats["faceoffs_total"]
            else 0
        )

        output.append({
            "season": row["season"],
            "season_id": row["season_id"],
            "season_type": row["season_type"],
            "division": row["division"],

            "team_id": row["team_id"],
            "team": row["team"],
            "team_name": row["team_name"],
            "team_display_name": row["team_display_name"],
            "team_aliases": row["team_aliases"],
            "raw_team": row["raw_team"],

            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "player_display_name": row["player_display_name"],
            "aliases": row["aliases"],

            "stats": {
                k: round(v, 2)
                for k, v in stats.items()
            },
        })

    output.sort(
        key=lambda p: (
            p["season_id"],
            p["season_type"],
            p["division"],
            p["team_display_name"],
            p["player_id"],
        )
    )

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="summer_2026")
    parser.add_argument("--season-type", default="regular_season")

    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    output = build_live_season(
        season_id=args.season,
        season_type=args.season_type,
    )

    out_file = OUT_DIR / f"{args.season}_live.json"

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Live match details parsed: {len(list(get_match_details_dir(args.season, args.season_type).rglob('*.json')))}")
    print(f"Live season rows written: {len(output)}")
    print(f"Wrote: {out_file.resolve()}")


if __name__ == "__main__":
    main()