import json
from pathlib import Path
from collections import defaultdict

ALL_TIME_FILE = Path("../data/all_time_players.json")
OUT_FILE = Path("../data/teams.json")
TEAM_METADATA_FILE = Path("../data/team_metadata.json")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_json_or_fallback(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_team_metadata():
    entries = load_json_or_fallback(TEAM_METADATA_FILE, [])

    by_id = {}

    for entry in entries:
        team_id = entry.get("team_id")

        if not team_id:
            continue

        by_id[team_id] = entry

    return by_id


def apply_team_metadata(team_entry, metadata_by_id):
    metadata = metadata_by_id.get(team_entry["team_id"], {})

    if not metadata:
        return team_entry

    team_entry["team_name"] = (
        metadata.get("team_display_name")
        or team_entry.get("team_name")
    )

    team_entry["team_display_name"] = (
        metadata.get("team_display_name")
        or team_entry.get("team_display_name")
        or team_entry.get("team_name")
    )

    team_entry["team_aliases"] = metadata.get("aliases", team_entry.get("team_aliases", []))
    team_entry["logo"] = metadata.get("logo", team_entry.get("logo", ""))
    team_entry["theme"] = metadata.get("theme", team_entry.get("theme", {}))
    team_entry["name_history"] = metadata.get("name_history", team_entry.get("name_history", []))

    return team_entry

def get_team_id(row):
    return (
        row.get("team_id")
        or row.get("team")
        or row.get("team_name")
        or "unknown_team"
    )


def get_team_display_name(row):
    return (
        row.get("team_display_name")
        or row.get("team")
        or row.get("team_name")
        or row.get("team_id")
        or "Unknown"
    )


def get_player_id(player):
    return (
        player.get("player_id")
        or player.get("player_name")
        or "unknown_player"
    )


def get_player_display_name(player):
    return (
        player.get("player_display_name")
        or player.get("player_name")
        or player.get("player_id")
        or "Unknown Player"
    )


def recalculate_rates(career):
    goals = career.get("goals", 0)
    assists = career.get("assists", 0)
    shots = career.get("shots", 0)

    saves = career.get("saves", 0)
    shots_against = career.get("shots_against", 0)
    goals_against = career.get("goals_against", 0)
    games_played = career.get("games_played", 0)

    faceoffs_won = career.get("faceoffs_won", 0)
    faceoffs_lost = career.get("faceoffs_lost", 0)

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

    return career


def main():
    players = load_json(ALL_TIME_FILE)
    metadata_by_id = load_team_metadata()
    teams = {}

    for player in players:
        player_id = get_player_id(player)
        player_display_name = get_player_display_name(player)

        for row in player.get("by_season", []):
            team_id = get_team_id(row)
            team_display_name = get_team_display_name(row)
            stats = row.get("stats", {})

            if team_id not in teams:
                teams[team_id] = {
                    "team_id": team_id,
                    "team_name": team_display_name,
                    "team_display_name": team_display_name,
                    "team_aliases": row.get("team_aliases", []),
                    "logo": row.get("logo", ""),
                    "theme": row.get("theme", {}),
                    "name_history": row.get("name_history", []),
                    "franchise_id": None,
                    "players": {},
                    "career": defaultdict(float),
                    "seasons": set(),
                    "divisions": set(),
                    "raw_teams": set()
                }

            team_entry = teams[team_id]

            # Prefer the latest canonical display name from the row.
            team_entry["team_name"] = team_display_name
            team_entry["team_display_name"] = team_display_name

            for alias in row.get("team_aliases", []):
                if alias and alias not in team_entry["team_aliases"]:
                    team_entry["team_aliases"].append(alias)

            raw_team = row.get("raw_team")
            if raw_team:
                team_entry["raw_teams"].add(raw_team)

            if player_id not in team_entry["players"]:
                team_entry["players"][player_id] = {
                    "player_id": player_id,
                    "player_name": player_display_name,
                    "player_display_name": player_display_name,
                    "aliases": player.get("aliases", []),
                    "stats": defaultdict(float),
                    "seasons": set()
                }

            player_entry = team_entry["players"][player_id]

            # Prefer latest player display name.
            player_entry["player_name"] = player_display_name
            player_entry["player_display_name"] = player_display_name

            for stat, value in stats.items():
                # Recalculate derived stats later.
                if (
                    stat.endswith("_percent")
                    or stat in [
                        "gaa",
                        "save_percent",
                        "shot_percent",
                        "faceoff_win_percent"
                    ]
                ):
                    continue

                value = float(value or 0)

                team_entry["career"][stat] += value
                player_entry["stats"][stat] += value

            player_entry["seasons"].add(row.get("season"))
            team_entry["seasons"].add(row.get("season"))
            team_entry["divisions"].add(row.get("division"))

    output = []

    for team in teams.values():
        team = apply_team_metadata(team, metadata_by_id)
        players_list = []

        for player_data in team["players"].values():
            career = dict(player_data["stats"])
            career = recalculate_rates(career)

            seasons = sorted(
                s for s in player_data["seasons"]
                if s
            )

            players_list.append({
                "player_id": player_data["player_id"],
                "player_name": player_data["player_display_name"],
                "player_display_name": player_data["player_display_name"],
                "aliases": sorted(set(player_data.get("aliases", []))),
                "seasons_played": len(seasons),
                "seasons": seasons,
                "stats": {
                    k: round(v, 2)
                    for k, v in career.items()
                }
            })

        players_list.sort(
            key=lambda p: p["stats"].get("games_played", 0),
            reverse=True
        )

        career = dict(team["career"])
        career = recalculate_rates(career)

        output.append({
            "team_id": team["team_id"],
            "team_name": team["team_display_name"],
            "team_display_name": team["team_display_name"],
            "team_aliases": sorted(set(team["team_aliases"])),
            "raw_teams": sorted(team["raw_teams"]),
            "logo": team.get("logo", ""),
            "theme": team.get("theme", {}),
            "name_history": team.get("name_history", []),
            "franchise_id": team["franchise_id"],
            "career": {
                k: round(v, 2)
                for k, v in career.items()
            },
            "seasons": sorted(
                s for s in team["seasons"]
                if s
            ),
            "divisions": sorted(
                d for d in team["divisions"]
                if d
            ),
            "players": players_list
        })

    output.sort(
        key=lambda t: t["team_display_name"].lower()
    )

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Teams written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()