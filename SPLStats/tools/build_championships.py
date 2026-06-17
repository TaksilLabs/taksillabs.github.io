import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime


RAW_CSV_DIR = Path("../raw_csv")
DIVISION_NAMES_FILE = Path("../data/division_display_names.json")
FRANCHISES_FILE = Path("../data/franchises.json")
OUTPUT_FILE = Path("../data/championships.json")


SEASON_ORDER = {
    "winter": 1,
    "spring": 2,
    "summer": 3,
    "fall": 4
}


CHAMPIONSHIPS = {
    "Erveon Cup Playoffs": {
        "region": "East",
        "championship": "Erveon Cup",
        "regular_divisions": [
            "Pro Division"
        ]
    },

    "Gazz Cup Playoffs": {
        "region": "Central",
        "championship": "Gazz Cup",
        "regular_divisions": [
            "Central A"
        ]
    },

    "Pacific Cup Playoffs": {
        "region": "West",
        "championship": "Pacific Cup",
        "regular_divisions": [
            "West Division",
            "Masters Division"
        ]
    }
}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def season_from_filename(path):
    stem = path.stem
    raw = stem.replace("SPL-", "")

    match = re.match(r"([A-Za-z]+)(\d{4})", raw)

    if not match:
        return raw, raw.lower()

    season_word = match.group(1)
    year = match.group(2)

    return (
        f"{season_word} {year}",
        f"{season_word.lower()}_{year}"
    )


def season_value(season_id):
    try:
        season, year = str(season_id).lower().split("_")

        return (
            int(year) * 10
            + SEASON_ORDER.get(season, 0)
        )

    except Exception:
        return 0


def season_in_range(
    season_id,
    start_season,
    end_season
):
    value = season_value(season_id)

    start = (
        season_value(start_season)
        if start_season
        else 0
    )

    end = (
        season_value(end_season)
        if end_season
        else 999999
    )

    return start <= value <= end


def clean_team_name(team_name):
    return re.sub(
        r"\s*\([^)]*\)\s*$",
        "",
        str(team_name or "").strip()
    ).strip()


def team_key(team_name):
    return clean_team_name(team_name).lower()


def normalize_player_name(name):
    return str(name or "").strip()


def normalize_division_name(
    division,
    division_map
):
    return (
        division_map.get(division)
        or division
        or "Unknown"
    )


def safe_int(value):
    try:
        return int(float(value))
    except Exception:
        return 0


def parse_date(value):
    text = str(value or "").strip()

    formats = [
        "%a %d %b %Y %I:%M %p",
        "%A %d %b %Y %I:%M %p",
        "%a %d %B %Y %I:%M %p",
        "%A %d %B %Y %I:%M %p",

        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt
            )
        except Exception:
            pass

    print(
        f"WARNING: Could not parse date: {text}"
    )

    return datetime.min


def fixture_id(row, season_id):
    return "|".join([
        season_id,
        row.get("Fixture Group", "").strip(),
        row.get("Fixture Date", "").strip(),
        clean_team_name(row.get("Home Team", "")),
        clean_team_name(row.get("Away Team", ""))
    ])


def match_involves_team(match, team):
    key = team_key(team)

    return (
        team_key(match["home_team"]) == key
        or team_key(match["away_team"]) == key
    )


def match_between_teams(match, team_a, team_b):
    teams = {
        team_key(match["home_team"]),
        team_key(match["away_team"])
    }

    return teams == {
        team_key(team_a),
        team_key(team_b)
    }


def get_match_score(match):
    home = match["home_team"]
    away = match["away_team"]

    home_score = match["scores"].get(home, 0)
    away_score = match["scores"].get(away, 0)

    return home_score, away_score


def get_match_winner(match):
    home = match["home_team"]
    away = match["away_team"]

    home_score, away_score = get_match_score(match)

    if home_score > away_score:
        return home

    if away_score > home_score:
        return away

    return None


def get_match_loser(match):
    winner = get_match_winner(match)

    if not winner:
        return None

    if team_key(winner) == team_key(match["home_team"]):
        return match["away_team"]

    return match["home_team"]


def find_franchise_for_team(
    team,
    season_id,
    franchises
):
    key = team_key(team)

    for franchise in franchises:
        for membership in franchise.get("memberships", []):
            if team_key(membership.get("team")) != key:
                continue

            if season_in_range(
                season_id,
                membership.get("start_season"),
                membership.get("end_season")
            ):
                return franchise.get("franchise_id")

    return None


# -----------------------------------------------------------------------------
# Raw CSV parsing
# -----------------------------------------------------------------------------

def parse_raw_csvs():
    division_map = load_json(DIVISION_NAMES_FILE)

    matches = {}
    appearances = defaultdict(set)

    csv_files = sorted(
        p for p in RAW_CSV_DIR.glob("SPL-*.csv")
        if re.match(
            r"SPL-[A-Za-z]+\d{4}$",
            p.stem
        )
    )

    print(
        f"CSV files found: {len(csv_files)}"
    )

    for csv_file in csv_files:
        season_name, season_id = season_from_filename(csv_file)

        print(
            f"Reading {csv_file.name}"
        )

        with csv_file.open(
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:
            reader = csv.DictReader(f)

            for row in reader:
                raw_group = row.get("Fixture Group", "").strip()

                division = normalize_division_name(
                        raw_group,
                        division_map
                    )

                fid = fixture_id(row, season_id)

                home_team = clean_team_name(
                        row.get("Home Team", "")
                    )

                away_team = clean_team_name(
                        row.get("Away Team", "")
                    )

                team = clean_team_name(
                        row.get("Team", "")
                    )

                player = normalize_player_name(
                        row.get("Last Name", "")
                    )

                stat_desc = row.get("Stat Desc", "").strip().lower()

                # Build player appearance sets from any stat row.
                if team and player:
                    appearances[(fid, team)].add(player)

                # Build match scores from Goals rows.
                if stat_desc != "goals":
                    continue

                if fid not in matches:
                    champ_info = CHAMPIONSHIPS.get(division)

                    matches[fid] = {
                        "fixture_id": fid,
                        "season": season_name,
                        "season_id": season_id,
                        "raw_division": raw_group,
                        "division": division,
                        "championship_info": champ_info,
                        "fixture_date": row.get(
                            "Fixture Date",
                            ""
                        ).strip(),
                        "home_team": home_team,
                        "away_team": away_team,
                        "scores": defaultdict(int)
                    }

                goals = safe_int(
                        row.get("Stat Value", 0)
                    )

                matches[fid]["scores"][team] += goals

    return matches, appearances


# -----------------------------------------------------------------------------
# Championship Detection
# -----------------------------------------------------------------------------

def detect_final_matches(matches):
    finals = {}

    for match in matches.values():
        division = match["division"]

        if division not in CHAMPIONSHIPS:
            continue

        key = (
            match["season_id"],
            division
        )

        current = finals.get(key)

        if not current:
            finals[key] = match
            continue

        current_date = parse_date(
                current["fixture_date"]
            )

        match_date = parse_date(
                match["fixture_date"]
            )

        if match_date > current_date:
            finals[key] = match

    return finals


def get_series_matches(
    matches,
    season_id,
    division,
    team_a,
    team_b
):
    series = []

    for match in matches.values():
        if match["season_id"] != season_id:
            continue

        if match["division"] != division:
            continue

        if not match_between_teams(
            match,
            team_a,
            team_b
        ):
            continue

        series.append(match)

    series.sort(
        key=lambda m: parse_date(m["fixture_date"])
    )

    return series


def determine_series_winner(
    series_matches,
    fallback_final_match
):
    wins = defaultdict(int)

    for match in series_matches:
        winner = get_match_winner(match)

        if winner:
            wins[team_key(winner)] += 1

    home = fallback_final_match["home_team"]
    away = fallback_final_match["away_team"]

    home_wins = wins.get(team_key(home), 0)
    away_wins = wins.get(team_key(away), 0)

    if home_wins > away_wins:
        return home, away, home_wins, away_wins

    if away_wins > home_wins:
        return away, home, away_wins, home_wins

    # Fallback if something weird happened.
    fallback_winner = get_match_winner(fallback_final_match)

    fallback_loser = get_match_loser(fallback_final_match)

    if fallback_winner:
        return (
            fallback_winner,
            fallback_loser,
            wins.get(team_key(fallback_winner), 0),
            wins.get(team_key(fallback_loser), 0)
        )

    return None, None, 0, 0


# -----------------------------------------------------------------------------
# Roster Eligibility
# -----------------------------------------------------------------------------

def get_team_matches(
    matches,
    season_id,
    divisions,
    team
):
    output = []

    for match in matches.values():
        if match["season_id"] != season_id:
            continue

        if match["division"] not in divisions:
            continue

        if not match_involves_team(
            match,
            team
        ):
            continue

        output.append(match)

    return output


def count_player_games(
    match_list,
    team,
    appearances
):
    player_games = defaultdict(set)

    for match in match_list:
        fid = match["fixture_id"]

        players = appearances.get(
                (fid, clean_team_name(team)),
                set()
            )

        for player in players:
            player_games[player].add(fid)

    return player_games


def build_championship_roster(
    winner_team,
    regular_matches,
    playoff_matches,
    finals_matches,
    appearances
):
    regular_player_games = count_player_games(
            regular_matches,
            winner_team,
            appearances
        )

    playoff_player_games = count_player_games(
            playoff_matches,
            winner_team,
            appearances
        )

    finals_player_games = count_player_games(
            finals_matches,
            winner_team,
            appearances
        )

    team_regular_games = len(regular_matches)

    team_playoff_games = len(playoff_matches)

    team_finals_games = len(finals_matches)

    players = set()
    players.update(regular_player_games.keys())
    players.update(playoff_player_games.keys())
    players.update(finals_player_games.keys())

    roster = []

    for player in sorted(players, key=lambda p: p.lower()):
        regular_games = len(regular_player_games.get(player, set()))

        playoff_games = len(playoff_player_games.get(player, set()))

        finals_games = len(finals_player_games.get(player, set()))

        regular_percent = (
            regular_games / team_regular_games
            if team_regular_games
            else 0
        )

        playoff_percent = (
            playoff_games / team_playoff_games
            if team_playoff_games
            else 0
        )

        qualified_by = []

        if regular_percent >= 0.5:
            qualified_by.append(
                "regular_season_50_percent"
            )

        if playoff_percent >= 0.5:
            qualified_by.append(
                "playoffs_50_percent"
            )

        if finals_games >= 1:
            qualified_by.append(
                "finals_appearance"
            )

        if not qualified_by:
            continue

        roster.append({
            "player_name": player,

            "regular_season_games": regular_games,
            "team_regular_season_games": team_regular_games,
            "regular_season_percent": round(
                regular_percent,
                3
            ),

            "playoff_games": playoff_games,
            "team_playoff_games": team_playoff_games,
            "playoff_percent": round(
                playoff_percent,
                3
            ),

            "finals_games": finals_games,
            "team_finals_games": team_finals_games,

            "qualified_by": qualified_by
        })

    return roster


# -----------------------------------------------------------------------------
# Main build
# -----------------------------------------------------------------------------

def build_championships():
    franchises = load_json(FRANCHISES_FILE)

    matches, appearances = parse_raw_csvs()

    final_matches = detect_final_matches(matches)

    championships = []

    for (season_id, division), final_match in sorted(
        final_matches.items(),
        key=lambda item: (
            season_value(item[0][0]),
            item[0][1]
        )
    ):
        info = CHAMPIONSHIPS[division]

        finalist_a = final_match["home_team"]

        finalist_b = final_match["away_team"]

        series_matches = get_series_matches(
                matches,
                season_id,
                division,
                finalist_a,
                finalist_b
            )

        winner_team, runner_up_team, winner_series_wins, runner_up_series_wins = determine_series_winner(
                series_matches,
                final_match
            )

        if not winner_team:
            print(
                f"WARNING: Could not determine winner for "
                f"{season_id} | {division}"
            )

            continue

        regular_matches = get_team_matches(
                matches,
                season_id,
                info["regular_divisions"],
                winner_team
            )

        playoff_matches = get_team_matches(
                matches,
                season_id,
                [division],
                winner_team
            )

        roster = build_championship_roster(
                winner_team,
                regular_matches,
                playoff_matches,
                series_matches,
                appearances
            )

        winner_franchise_id = find_franchise_for_team(
                winner_team,
                season_id,
                franchises
            )

        finals_games = []

        for match in series_matches:
            home_score, away_score = get_match_score(match)

            finals_games.append({
                "fixture_id": match["fixture_id"],
                "fixture_date": match["fixture_date"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_score": home_score,
                "away_score": away_score,
                "winner_team": get_match_winner(match)
            })

        championships.append({
            "season": final_match["season"],
            "season_id": season_id,

            "region": info["region"],
            "championship": info["championship"],
            "playoff_division": division,
            "regular_divisions": info["regular_divisions"],

            "winner_team": winner_team,
            "runner_up_team": runner_up_team,

            "winner_franchise_id": winner_franchise_id,

            "series_result": (
                f"{winner_series_wins}-{runner_up_series_wins}"
            ),

            "winner_series_wins": winner_series_wins,
            "runner_up_series_wins": runner_up_series_wins,

            "final_fixture_id": final_match["fixture_id"],
            "final_fixture_date": final_match["fixture_date"],

            "team_regular_season_games": len(regular_matches),
            "team_playoff_games": len(playoff_matches),
            "team_finals_games": len(series_matches),

            "finals_games": finals_games,
            "championship_roster": roster
        })

    championships.sort(
        key=lambda c: (
            season_value(c["season_id"]),
            c["region"]
        ),
        reverse=True
    )

    return championships


def main():
    championships = build_championships()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            championships,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=" * 80)
    print("CHAMPIONSHIPS BUILT")
    print("=" * 80)

    for champ in championships:
        print(
            f"{champ['season']} | "
            f"{champ['region']} | "
            f"{champ['championship']} | "
            f"{champ['winner_team']} "
            f"def. {champ['runner_up_team']} "
            f"({champ['series_result']}) | "
            f"Roster: {len(champ['championship_roster'])}"
        )

    print()
    print(f"Championships written: {len(championships)}")
    print(f"Wrote: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()