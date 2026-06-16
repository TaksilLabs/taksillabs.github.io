## DO THIS TOMORROW, Fuck Im Tired
import csv
import json
from pathlib import Path
from collections import defaultdict


RAW_CSV_DIR = Path("../raw_csv")
OUTPUT_FILE = Path("../data/team_records.json")


def create_record():
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "seasons": set()
    }


team_records = defaultdict(create_record)
matches = {}

csv_files = sorted(RAW_CSV_DIR.glob("*.csv"))

print(f"Found {len(csv_files)} CSV files")


for csv_file in csv_files:

    print(f"Reading {csv_file.name}")

    season_name = csv_file.stem.replace("SPL-", "")

    with open(csv_file, encoding="utf-8-sig") as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["Stat Desc"].strip().lower() != "goals":
                continue

            match_key = (
                row["Fixture Group"],
                row["Fixture Date"],
                row["Home Team"],
                row["Away Team"]
            )

            if match_key not in matches:
                matches[match_key] = {
                    "fixture_group": row["Fixture Group"],
                    "fixture_date": row["Fixture Date"],
                    "home_team": row["Home Team"],
                    "away_team": row["Away Team"],
                    "scores": defaultdict(int),
                    "season": season_name
                }

            team = row["Team"]

            try:
                goals = int(float(row["Stat Value"]))
            except:
                goals = 0

            matches[match_key]["scores"][team] += goals


print(f"Matches reconstructed: {len(matches):,}")


for match in matches.values():

    home = match["home_team"]
    away = match["away_team"]

    home_score = match["scores"].get(home, 0)
    away_score = match["scores"].get(away, 0)

    season = match["season"]

    home_rec = team_records[home]
    away_rec = team_records[away]

    home_rec["games_played"] += 1
    away_rec["games_played"] += 1

    home_rec["goals_for"] += home_score
    home_rec["goals_against"] += away_score

    away_rec["goals_for"] += away_score
    away_rec["goals_against"] += home_score

    home_rec["seasons"].add(season)
    away_rec["seasons"].add(season)

    if home_score > away_score:
        home_rec["wins"] += 1
        away_rec["losses"] += 1

    elif away_score > home_score:
        away_rec["wins"] += 1
        home_rec["losses"] += 1


output = []

for team_name, record in sorted(team_records.items()):

    gp = record["games_played"]

    win_percent = (
        record["wins"] / gp
        if gp
        else 0
    )

    output.append({
        "team": team_name,

        "games_played": gp,

        "wins": record["wins"],
        "losses": record["losses"],

        "win_percent": round(win_percent, 3),

        "goals_for": record["goals_for"],
        "goals_against": record["goals_against"],

        "goal_differential":
            record["goals_for"]
            - record["goals_against"],

        "seasons":
            sorted(record["seasons"])
    })


print()
print("=" * 60)
print("VALIDATION")
print("=" * 60)

bad_teams = []

for team in output:

    if (
        team["wins"]
        + team["losses"]
        != team["games_played"]
    ):
        bad_teams.append(team)

print(
    f"Teams failing W+L=GP: "
    f"{len(bad_teams)}"
)

if bad_teams:

    print()

    for team in bad_teams[:20]:

        print(
            team["team"],
            team["games_played"],
            team["wins"],
            team["losses"]
        )

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        indent=2
    )


print()
print("TOP 10 GAMES PLAYED")
print("-" * 60)

for team in sorted(
    output,
    key=lambda x: x["games_played"],
    reverse=True
)[:10]:

    print(
        f"{team['games_played']:4d} GP  "
        f"{team['wins']:4d}W "
        f"{team['losses']:4d}L  "
        f"{team['team']}"
    )

for team in sorted(
    output,
    key=lambda x: x["wins"],
    reverse=True
)[:10]:

    print(
        f"{team['wins']:4d}W "
        f"{team['losses']:4d}L "
        f"{team['team']}"
    )

print()
print("=" * 60)
print("MATCHES WITH TIED SCORES")
print("=" * 60)

tie_matches = []

for match in matches.values():

    home = match["home_team"]
    away = match["away_team"]

    home_score = match["scores"].get(home, 0)
    away_score = match["scores"].get(away, 0)

    if home_score == away_score:

        tie_matches.append({
            "fixture_group": match["fixture_group"],
            "fixture_date": match["fixture_date"],
            "home_team": home,
            "away_team": away,
            "home_score": home_score,
            "away_score": away_score
        })

print(f"Tied Matches Found: {len(tie_matches)}")
print()

for match in tie_matches:

    print(
        f"{match['fixture_date']} | "
        f"{match['fixture_group']}"
    )

    print(
        f"  {match['home_team']} "
        f"{match['home_score']}"
    )

    print(
        f"  {match['away_team']} "
        f"{match['away_score']}"
    )

    print()