import csv
from collections import defaultdict

CSV_FILE = "../raw_csv/SPL-Fall2020.csv"


matches = {}

with open(CSV_FILE, encoding="utf-8-sig") as f:
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
                "scores": defaultdict(int)
            }

        team = row["Team"]

        try:
            goals = int(float(row["Stat Value"]))
        except:
            goals = 0

        matches[match_key]["scores"][team] += goals


print(f"Matches reconstructed: {len(matches):,}")
print()

for i, match in enumerate(matches.values()):

    if i >= 5:
        break

    home = match["home_team"]
    away = match["away_team"]

    home_score = match["scores"].get(home, 0)
    away_score = match["scores"].get(away, 0)

    if home_score > away_score:
        winner = home
    elif away_score > home_score:
        winner = away
    else:
        winner = "TIE"

    print("=" * 60)
    print(match["fixture_group"])
    print(match["fixture_date"])
    print()
    print(f"{home}: {home_score}")
    print(f"{away}: {away_score}")
    print()
    print("Winner:", winner)
    print()


print(f"Goal rows found: {goal_rows:,}")
print(f"Matches found: {len(matches):,}")