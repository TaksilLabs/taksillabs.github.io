import json
from pathlib import Path
from collections import defaultdict

ALL_TIME_FILE = Path("../data/all_time_players.json")
OUT_FILE = Path("../data/teams.json")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    players = load_json(ALL_TIME_FILE)
    teams = {}

    for player in players:
        for row in player.get("by_season", []):
            team = row.get("team") or "Unknown"
            stats = row.get("stats", {})

            if team not in teams:
                teams[team] = {
                    "team_name": team,
                    "franchise_id": None,
                    "players": {},
                    "career": defaultdict(float),
                    "seasons": set(),
                    "divisions": set()
                }

            team_entry = teams[team]
            player_name = player["player_name"]

            if player_name not in team_entry["players"]:
                team_entry["players"][player_name] = {
                    "stats": defaultdict(float),
                    "seasons": set()
                }

            for stat, value in stats.items():
                if stat.endswith("_percent"):
                    continue

                value = float(value or 0)
                team_entry["career"][stat] += value
                team_entry["players"][player_name]["stats"][stat] += value

            team_entry["players"][player_name]["seasons"].add(row.get("season"))
            team_entry["seasons"].add(row.get("season"))
            team_entry["divisions"].add(row.get("division"))

    output = []

    for team in teams.values():
        players_list = []

        for player_name, player_data in team["players"].items():
            career = dict(player_data["stats"])
            career["points"] = career.get("goals", 0) + career.get("assists", 0)

            seasons = sorted(s for s in player_data["seasons"] if s)

            players_list.append({
                "player_name": player_name,
                "seasons_played": len(seasons),
                "seasons": seasons,
                "stats": {k: round(v, 2) for k, v in career.items()}
            })

        players_list.sort(
            key=lambda p: p["stats"].get("games_played", 0),
            reverse=True
        )

        career = dict(team["career"])
        career["points"] = career.get("goals", 0) + career.get("assists", 0)

        output.append({
            "team_name": team["team_name"],
            "franchise_id": team["franchise_id"],
            "career": {k: round(v, 2) for k, v in career.items()},
            "seasons": sorted(s for s in team["seasons"] if s),
            "divisions": sorted(d for d in team["divisions"] if d),
            "players": players_list
        })

    output.sort(key=lambda t: t["team_name"].lower())

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Teams written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()