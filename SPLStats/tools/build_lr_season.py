import csv
import json
import re
from pathlib import Path
from collections import defaultdict

RAW_CSV_DIR = Path("../raw_csv")
OUT_DIR = Path("../data/seasons")

STAT_MAP = {
    "Games Played": "games_played",
    "Goals": "goals",
    "Assists": "assists",
    "Primary Assists": "primary_assists",
    "Secondary Assists": "secondary_assists",
    "Shots": "shots",
    "Post Hits": "post_hits",
    "Saves": "saves",
    "Blocks": "blocks",
    "Passes": "passes",
    "Takeaways": "takeaways",
    "Turnovers": "turnovers",
    "Faceoffs Won": "faceoffs_won",
    "Faceoffs Lost": "faceoffs_lost",
    "Contributed Goals": "contributed_goals",
    "Conceded Goals": "conceded_goals",
    "Possession Time": "possession_time_sec",
    "Score": "score",
    "Wins": "wins",
    "Losses": "losses",
}

def classify_season_type(fixture_group):
    text = fixture_group.lower()

    if "preseason" in text or "pre-season" in text:
        return "preseason"
    
    if "other groups" in text or "vs disbanded teams" in text:
        return "disbanded_team"
    
    playoff_words = [
        "playoff",
        "cup",
        "postseason",
        "post season",
        "promotional series",
        "series",
        "playoffs"
    ]

    if any(word in text for word in playoff_words):
        return "postseason"
    
    return "regular_season"


def season_from_filename(path):
    # SPL-Winter2025.csv -> ("Winter 2025", "winter_2025")
    stem = path.stem  # SPL-Winter2025
    raw = stem.replace("SPL-", "")

    match = re.match(r"([A-Za-z]+)(\d{4})", raw)
    if not match:
        return raw, raw.lower()

    season_word = match.group(1)
    year = match.group(2)

    season_name = f"{season_word} {year}"
    season_id = f"{season_word.lower()}_{year}"

    return season_name, season_id


def normalize_player_name(name):
    return str(name).strip()


def get_team_abbr(first_name):
    text = str(first_name).strip()
    match = re.search(r"\[([^\]]+)\]", text)
    return match.group(1) if match else text


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def parse_csv(csv_file):
    season_name, season_id = season_from_filename(csv_file)
    players = {}

    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            fixture_group = row.get("Fixture Group", "").strip()
            player_name = normalize_player_name(row.get("Last Name", ""))
            team_abbr = get_team_abbr(row.get("First Name", ""))
            team_name = row.get("Team", "").strip()

            stat_desc = row.get("Stat Desc", "").strip()
            stat_key = STAT_MAP.get(stat_desc)

            if not player_name or not stat_key:
                continue

            key = (fixture_group, team_abbr, player_name)

            if key not in players:
                players[key] = {
                    "season": season_name,
                    "season_id": season_id,
                    "division": fixture_group,
                    "team_abbr": team_abbr,
                    "team_name": team_name,
                    "player_name": player_name,
                    "fixtures": set(),
                    "stats": defaultdict(float),
                }

            fixture_id = "|".join([
                row.get("Fixture Group", "").strip(),
                row.get("Fixture Date", "").strip(),
                row.get("Home Team", "").strip(),
                row.get("Away Team", "").strip(),
            ])

            players[key]["fixtures"].add(fixture_id)

            players[key]["stats"][stat_key] += safe_float(row.get("Stat Value", 0))

    output = []

    for item in players.values():
        stats = dict(item["stats"])

        goals = stats.get("goals", 0)
        assists = stats.get("assists", 0)
        shots = stats.get("shots", 0)
        saves = stats.get("saves", 0)
        conceded = stats.get("conceded_goals", 0)
        faceoffs_won = stats.get("faceoffs_won", 0)
        faceoffs_lost = stats.get("faceoffs_lost", 0)

        stats["points"] = goals + assists
        stats["games_played"] = len(item["fixtures"])
        stats["shot_percent"] = (goals / shots * 100) if shots else 0
        stats["save_percent"] = (saves / (saves + conceded) * 100) if (saves + conceded) else 0
        stats["faceoffs_total"] = faceoffs_won + faceoffs_lost
        stats["faceoff_win_percent"] = (
            faceoffs_won / stats["faceoffs_total"] * 100
            if stats["faceoffs_total"]
            else 0
        )

        output.append({
            "season": item["season"],
            "season_id": item["season_id"],
            "season_type": classify_season_type(item["division"]),
            "division": item["division"],
            "team_abbr": item["team_abbr"],
            "team_name": item["team_name"],
            "player_name": item["player_name"],
            "stats": {k: round(v, 2) for k, v in stats.items()},
        })

    output.sort(
        key=lambda p: (
            p["season_id"],
            p["division"],
            p["team_abbr"],
            p["player_name"].lower(),
        )
    )

    return season_id, output


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(RAW_CSV_DIR.glob("SPL-*.csv"))

    if not csv_files:
        print(f"No CSV files found in: {RAW_CSV_DIR.resolve()}")
        return

    total_rows = 0

    for csv_file in csv_files:
        season_id, output = parse_csv(csv_file)
        out_file = OUT_DIR / f"{season_id}.json"

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        total_rows += len(output)

        print(f"{csv_file.name} -> {out_file.name} | rows: {len(output)}")

    print()
    print(f"CSV files parsed: {len(csv_files)}")
    print(f"Total season-player rows written: {total_rows}")
    print(f"Output folder: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()