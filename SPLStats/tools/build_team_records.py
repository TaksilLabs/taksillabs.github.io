import csv
import json
import re
from pathlib import Path
from collections import defaultdict


RAW_CSV_DIR = Path("../raw_csv")
OUTPUT_FILE = Path("../data/team_records.json")


SEASON_ORDER = {
    "winter": 1,
    "spring": 2,
    "summer": 3,
    "fall": 4
}


# ----------------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------------

def season_from_filename(path):
    stem = path.stem
    raw = stem.replace("SPL-", "")

    match = re.match(r"([A-Za-z]+)(\d{4})", raw)

    if not match:
        return raw, raw.lower()

    season_word = match.group(1)
    year = match.group(2)

    season_name = f"{season_word} {year}"
    season_id = f"{season_word.lower()}_{year}"

    return season_name, season_id


def season_sort_value(season_id):
    text = str(season_id).lower().strip()

    match = re.match(r"([a-z]+)_(\d{4})", text)

    if not match:
        return 0

    season = match.group(1)
    year = int(match.group(2))

    return year * 10 + SEASON_ORDER.get(season, 0)


def clean_team_name(team_name):
    team_name = str(team_name).strip()

    return re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        team_name
    ).strip()


def make_empty_record():
    return {
        "games_played": 0,
        "wins": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0
    }


def finalize_record(record):
    record["goal_differential"] = (
        record["goals_for"]
        - record["goals_against"]
    )

    record["win_percent"] = (
        record["wins"] / record["games_played"]
        if record["games_played"]
        else 0
    )

    return record


def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0


def add_result(
    team_records,
    team_by_season,
    team_seasons,
    team,
    team_score,
    opponent_score,
    season_name,
    season_id
):
    team = clean_team_name(team)

    did_win = team_score > opponent_score
    did_lose = team_score < opponent_score

    # All-time / career record
    career = team_records[team]

    career["games_played"] += 1
    career["goals_for"] += team_score
    career["goals_against"] += opponent_score

    if did_win:
        career["wins"] += 1
    elif did_lose:
        career["losses"] += 1

    team_seasons[team].add(season_id)

    # Season-specific record
    season_record = team_by_season[team][season_id]

    season_record["season"] = season_name
    season_record["season_id"] = season_id

    season_record["games_played"] += 1
    season_record["goals_for"] += team_score
    season_record["goals_against"] += opponent_score

    if did_win:
        season_record["wins"] += 1
    elif did_lose:
        season_record["losses"] += 1


# ----------------------------------------------------------------------------------------
# Build Match Scores
# ----------------------------------------------------------------------------------------

team_records = defaultdict(make_empty_record)
team_by_season = defaultdict(lambda: defaultdict(make_empty_record))
team_seasons = defaultdict(set)

matches = {}

csv_files = sorted(
    p for p in RAW_CSV_DIR.glob("SPL-*.csv")
    if re.match(r"SPL-[A-Za-z]+\d{4}$", p.stem)
)

print(f"Found {len(csv_files)} CSV files")


for csv_file in csv_files:
    season_name, season_id = season_from_filename(csv_file)

    print(f"Reading {csv_file.name}")

    with open(csv_file, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stat_desc = row.get("Stat Desc", "").strip().lower()

            if stat_desc != "goals":
                continue

            fixture_group = row.get("Fixture Group", "").strip()
            fixture_date = row.get("Fixture Date", "").strip()

            home_team = clean_team_name(
                row.get("Home Team", "")
            )

            away_team = clean_team_name(
                row.get("Away Team", "")
            )

            team = clean_team_name(
                row.get("Team", "")
            )

            match_key = (
                season_id,
                fixture_group,
                fixture_date,
                home_team,
                away_team
            )

            if match_key not in matches:
                matches[match_key] = {
                    "season": season_name,
                    "season_id": season_id,
                    "fixture_group": fixture_group,
                    "fixture_date": fixture_date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "scores": defaultdict(int)
                }

            goals = safe_int(
                row.get("Stat Value", 0)
            )

            matches[match_key]["scores"][team] += goals


print(f"Matches reconstructed: {len(matches):,}")


# ----------------------------------------------------------------------------------------
# Build Team Records
# ----------------------------------------------------------------------------------------

for match in matches.values():
    home = match["home_team"]
    away = match["away_team"]

    home_score = match["scores"].get(home, 0)
    away_score = match["scores"].get(away, 0)

    season_name = match["season"]
    season_id = match["season_id"]

    add_result(
        team_records=team_records,
        team_by_season=team_by_season,
        team_seasons=team_seasons,
        team=home,
        team_score=home_score,
        opponent_score=away_score,
        season_name=season_name,
        season_id=season_id
    )

    add_result(
        team_records=team_records,
        team_by_season=team_by_season,
        team_seasons=team_seasons,
        team=away,
        team_score=away_score,
        opponent_score=home_score,
        season_name=season_name,
        season_id=season_id
    )


# ----------------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------------

output = []

for team_name in sorted(team_records.keys()):
    record = finalize_record(
        dict(team_records[team_name])
    )

    by_season = []

    for season_id, season_record in team_by_season[team_name].items():
        finalized_season = finalize_record(
            dict(season_record)
        )

        finalized_season["win_percent"] = round(
            finalized_season["win_percent"],
            3
        )

        by_season.append(finalized_season)

    by_season.sort(
        key=lambda row: season_sort_value(row["season_id"])
    )

    seasons = sorted(
        team_seasons[team_name],
        key=season_sort_value
    )

    output.append({
        "team": team_name,

        "games_played": record["games_played"],

        "wins": record["wins"],
        "losses": record["losses"],

        "win_percent": round(
            record["win_percent"],
            3
        ),

        "goals_for": record["goals_for"],
        "goals_against": record["goals_against"],

        "goal_differential": record["goal_differential"],

        "seasons": seasons,

        "by_season": by_season
    })


# ----------------------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------------------

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


OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
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


print()
print("TOP 10 WINS")
print("-" * 60)

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
            "season": match["season"],
            "season_id": match["season_id"],
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
        f"{match['season']} | "
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


print()
print(f"Wrote: {OUTPUT_FILE.resolve()}")