import json
from pathlib import Path
from collections import defaultdict

SEASONS_DIR = Path("../data/seasons")
OUT_FILE = Path("../data/all_time_players.json")


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    players = {}

    for season_file in SEASONS_DIR.glob("*.json"):
        season_rows = load_json(season_file)

        for row in season_rows:
            name = row["player_name"].strip()
            key = name.lower()

            if key not in players:
                players[key] = {
                    "player_name": name,
                    "aliases": [name],
                    "seasons_played": [],
                    "divisions_played": [],
                    "teams_played_for": [],
                    "career": defaultdict(float),
                    "by_season": []
                }

            player = players[key]

            if name not in player["aliases"]:
                player["aliases"].append(name)

            if row["season"] not in player["seasons_played"]:
                player["seasons_played"].append(row["season"])

            if row["division"] not in player["divisions_played"]:
                player["divisions_played"].append(row["division"])

            if row["team_abbr"] not in player["teams_played_for"]:
                player["teams_played_for"].append(row["team_abbr"])

            for stat, value in row["stats"].items():
                # We'll recalculate percentage stats later.
                if stat.endswith("_percent"):
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
        conceded = career.get("conceded_goals", 0)
        faceoffs_won = career.get("faceoffs_won", 0)
        faceoffs_lost = career.get("faceoffs_lost", 0)

        career["points"] = goals + assists
        career["shot_percent"] = (goals / shots * 100) if shots else 0
        career["save_percent"] = (saves / (saves + conceded) * 100) if (saves + conceded) else 0
        career["faceoffs_total"] = faceoffs_won + faceoffs_lost
        career["faceoff_win_percent"] = (
            faceoffs_won / career["faceoffs_total"] * 100
            if career["faceoffs_total"]
            else 0
        )

        output.append({
            "player_name": player["player_name"],
            "aliases": sorted(player["aliases"]),
            "seasons_played": sorted(player["seasons_played"]),
            "divisions_played": sorted(player["divisions_played"]),
            "teams_played_for": sorted(player["teams_played_for"]),
            "career": {k: round(v, 2) for k, v in career.items()},
            "by_season": player["by_season"]
        })

    output.sort(key=lambda p: p["career"].get("points", 0), reverse=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Season files read: {len(list(SEASONS_DIR.glob('*.json')))}")
    print(f"Players written: {len(output)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()