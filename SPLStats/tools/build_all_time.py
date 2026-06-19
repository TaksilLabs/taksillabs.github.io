import json
import re
from pathlib import Path
from collections import defaultdict

SEASONS_DIR = Path("../data/seasons")
OUT_FILE = Path("../data/all_time_players.json")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_fallback_player_id(name):
    text = str(name or "").strip().lower()

    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or "unknown_player"


def get_row_player_id(row):
    return (
        row.get("player_id")
        or make_fallback_player_id(row.get("player_name", ""))
    )


def get_row_display_name(row):
    return (
        row.get("player_display_name")
        or row.get("player_name")
        or row.get("player_id")
        or "Unknown Player"
    )


def main():
    players = {}

    season_files = sorted(SEASONS_DIR.glob("*.json"))

    for season_file in season_files:
        season_rows = load_json(season_file)

        for row in season_rows:
            player_id = get_row_player_id(row)
            display_name = get_row_display_name(row)

            if not player_id:
                continue

            key = player_id.lower()

            if key not in players:
                players[key] = {
                    "player_id": player_id,

                    # Keep player_name for compatibility with existing frontend code.
                    "player_name": display_name,

                    # Preferred display field going forward.
                    "player_display_name": display_name,

                    "aliases": [],
                    "seasons_played": [],
                    "divisions_played": [],
                    "teams_played_for": [],
                    "team_ids_played_for": [],
                    "career": defaultdict(float),
                    "by_season": []
                }

            player = players[key]

            # Prefer the latest display name from the season row/alias system.
            player["player_name"] = display_name
            player["player_display_name"] = display_name

            aliases = row.get("aliases", [])

            if isinstance(aliases, list):
                for alias in aliases:
                    if alias and alias not in player["aliases"]:
                        player["aliases"].append(alias)

            if display_name and display_name not in player["aliases"]:
                player["aliases"].append(display_name)

            if row["season"] not in player["seasons_played"]:
                player["seasons_played"].append(row["season"])

            if row["division"] not in player["divisions_played"]:
                player["divisions_played"].append(row["division"])

            team_id = (
                row.get("team_id")
                or row.get("team")
                or row.get("team_name")
                or row.get("team_abbr")
                or "unknown_team"
            )

            team_display_name = (
                row.get("team_display_name")
                or row.get("team")
                or row.get("team_name")
                or row.get("team_abbr")
                or "Unknown"
            )

            # Keep compatibility fields normalized in the by_season row.
            # This makes old frontend code still work while giving newer code stable IDs. Remove if gay.
            row["team_id"] = team_id
            row["team"] = team_display_name
            row["team_display_name"] = team_display_name
            row["team_aliases"] = row.get("team_aliases", [])
            row["raw_team"] = row.get("raw_team") or team_display_name

            if team_display_name not in player["teams_played_for"]:
                player["teams_played_for"].append(team_display_name)

            if team_id not in player["team_ids_played_for"]:
                player["team_ids_played_for"].append(team_id)

            for stat, value in row["stats"].items():
                # We'll recalculate percentage/rate stats later.
                if stat.endswith("_percent") or stat in ["gaa"]:
                    continue

                player["career"][stat] += float(value or 0)

            player["by_season"].append(row)

    output = []

    for player in players.values():
        career = dict(player["career"])

        goals = career.get("goals", 0)
        assists = career.get("assists", 0)
        shots = career.get("shots", 0)
        saves = career.get("saves", 0)
        faceoffs_won = career.get("faceoffs_won", 0)
        faceoffs_lost = career.get("faceoffs_lost", 0)

        goals_against = career.get("goals_against", 0)
        shots_against = career.get("shots_against", 0)
        games_played = career.get("games_played", 0)

        career["points"] = goals + assists

        career["shot_percent"] = (
            goals / shots * 100
            if shots
            else 0
        )

        career["save_percent"] = (
            saves / shots_against * 100
            if shots_against
            else 0
        )

        career["gaa"] = (
            goals_against / games_played
            if games_played
            else 0
        )

        career["faceoffs_total"] = faceoffs_won + faceoffs_lost

        career["faceoff_win_percent"] = (
            faceoffs_won / career["faceoffs_total"] * 100
            if career["faceoffs_total"]
            else 0
        )

        output.append({
            "player_id": player["player_id"],

            # Compatibility
            "player_name": player["player_display_name"],

            # Preferred display field
            "player_display_name": player["player_display_name"],

            "aliases": sorted(set(player["aliases"])),
            "seasons_played": sorted(player["seasons_played"]),
            "divisions_played": sorted(player["divisions_played"]),
            "teams_played_for": sorted(player["teams_played_for"]),
            "team_ids_played_for": sorted(player["team_ids_played_for"]),
            "career": {
                k: round(v, 2)
                for k, v in career.items()
            },
            "by_season": player["by_season"]
        })

    output.sort(
        key=lambda p: p["career"].get("points", 0),
        reverse=True
    )

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Season files read: {len(season_files)}")
    print(f"Players written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()