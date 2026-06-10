import json
from pathlib import Path
from collections import defaultdict

GAME_STATS_FILE = Path("../data/game_stats.json")
PLAYER_REGISTRY_FILE = Path("../data/player_registry.json")
OUT_FILE = Path("../data/career_totals.json")

SUM_STATS = [
    "goals",
    "assists",
    "primary_assists",
    "secondary_assists",
    "shots",
    "post_hits",
    "saves",
    "blocks",
    "passes",
    "takeaways",
    "turnovers",
    "faceoffs_won",
    "faceoffs_lost",
    "contributed_goals",
    "conceded_goals",
    "possession_time_sec",
    "score",
    "periods_played"
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    game_stats = load_json(GAME_STATS_FILE)
    players = load_json(PLAYER_REGISTRY_FILE)

    totals = defaultdict(lambda: defaultdict(float))

    for row in game_stats:
        slap_id = str(row.get("slap_id")).strip()
        if not slap_id:
            continue

        for stat in SUM_STATS:
            totals[slap_id][stat] += float(row.get(stat, 0) or 0)
            totals[slap_id]["games_played"] += 1

            if row.get("team") == row.get("winner"):
                totals[slap_id]["wins"] += 1
            else:
                totals[slap_id]["losses"] += 1

    career_totals = []

    for slap_id, stats in totals.items():
        registry_entry = players.get(slap_id, {})

        goals = stats.get("goals", 0)
        assists = stats.get("assists", 0)
        shots = stats.get("shots", 0)
        saves = stats.get("saves", 0)
        conceded = stats.get("conceded_goals", 0)
        faceoffs_won = stats.get("faceoffs_won", 0)
        faceoffs_lost = stats.get("faceoffs_lost", 0)

        points = goals + assists
        shot_percent = (goals / shots * 100) if shots else 0
        save_percent = (saves / (saves + conceded) * 100) if (saves + conceded) else 0
        faceoffs_total = faceoffs_won + faceoffs_lost
        faceoff_win_percent = (faceoffs_won / faceoffs_total * 100) if faceoffs_total else 0

        career_totals.append({
            "slap_id": slap_id,
            "display_name": registry_entry.get("display_name") or registry_entry.get("preferred_name") or row.get("username"),
            "preferred_name": registry_entry.get("preferred_name"),
            "aliases": registry_entry.get("aliases", []),
            "first_seen": registry_entry.get("first_seen"),
            "last_seen": registry_entry.get("last_seen"),

            **{stat: round(value, 2) for stat, value in stats.items()},

            "points": round(points, 2),
            "shot_percent": round(shot_percent, 2),
            "save_percent": round(save_percent, 2),
            "faceoffs_total": round(faceoffs_total, 2),
            "faceoff_win_percent": round(faceoff_win_percent, 2)
        })

    career_totals.sort(key=lambda p: p.get("points", 0), reverse=True)

    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(career_totals, f, indent=2, ensure_ascii=False)

    print(f"Player-game rows read: {len(game_stats)}")
    print(f"Career totals written: {len(career_totals)}")
    print(f"Wrote: {OUT_FILE.resolve()}")


if __name__ == "__main__":
    main()