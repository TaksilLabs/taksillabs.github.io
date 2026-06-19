import csv
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

from team_identity import load_team_identities, resolve_team_identity
from player_identity import load_player_identities, resolve_player_identity


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


REGION_ORDER = {
    "East": 1,
    "Central": 2,
    "West": 3
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


def make_fixture_id(
    season_id,
    fixture_group,
    fixture_date,
    home_team_id,
    away_team_id
):
    return "|".join([
        season_id,
        fixture_group,
        fixture_date,
        home_team_id,
        away_team_id
    ])


def match_involves_team_id(match, team_id):
    return (
        match["home_team_id"] == team_id
        or match["away_team_id"] == team_id
    )


def match_between_team_ids(match, team_a_id, team_b_id):
    teams = {
        match["home_team_id"],
        match["away_team_id"]
    }

    return teams == {
        team_a_id,
        team_b_id
    }


def get_match_score(match):
    home_id = match["home_team_id"]
    away_id = match["away_team_id"]

    home_score = match["scores"].get(home_id, 0)
    away_score = match["scores"].get(away_id, 0)

    return home_score, away_score


def get_match_winner_id(match):
    home_score, away_score = get_match_score(match)

    if home_score > away_score:
        return match["home_team_id"]

    if away_score > home_score:
        return match["away_team_id"]

    return None


def get_match_loser_id(match):
    winner_id = get_match_winner_id(match)

    if not winner_id:
        return None

    if winner_id == match["home_team_id"]:
        return match["away_team_id"]

    return match["home_team_id"]


def resolve_team(
    raw_team_name,
    team_alias_lookup,
    team_info
):
    identity = resolve_team_identity(
        raw_team_name,
        team_alias_lookup
    )

    team_id = identity["team_id"]
    display_name = identity["team_display_name"]

    team_info[team_id] = {
        "team_id": team_id,
        "team": display_name,
        "team_display_name": display_name,
        "team_aliases": identity.get("aliases", []),
        "logo": identity.get("logo", ""),
        "theme": identity.get("theme", {}),
        "name_history": identity.get("name_history", [])
    }

    return identity


def resolve_player(
    raw_player_name,
    player_alias_lookup,
    player_info
):
    identity = resolve_player_identity(
        raw_player_name,
        player_alias_lookup
    )

    player_id = identity["player_id"]
    display_name = identity["player_display_name"]

    player_info[player_id] = {
        "player_id": player_id,
        "player_name": display_name,
        "player_display_name": display_name,
        "aliases": identity.get("aliases", [])
    }

    return identity


def find_franchise_for_team_id(
    team_id,
    season_id,
    franchises,
    team_alias_lookup,
    team_info
):
    for franchise in franchises:
        for membership in franchise.get("memberships", []):
            membership_identity = resolve_team(
                membership.get("team", ""),
                team_alias_lookup,
                team_info
            )

            membership_team_id = membership_identity["team_id"]

            if membership_team_id != team_id:
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

    team_alias_lookup, _ = load_team_identities()
    player_alias_lookup, _ = load_player_identities()

    team_info = {}
    player_info = {}

    matches = {}

    # (fixture_id, team_id) -> set(player_id)
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

                fixture_date = row.get(
                    "Fixture Date",
                    ""
                ).strip()

                raw_home_team = row.get("Home Team", "").strip()
                raw_away_team = row.get("Away Team", "").strip()
                raw_team = row.get("Team", "").strip()

                home_identity = resolve_team(
                    raw_home_team,
                    team_alias_lookup,
                    team_info
                )

                away_identity = resolve_team(
                    raw_away_team,
                    team_alias_lookup,
                    team_info
                )

                team_identity = resolve_team(
                    raw_team,
                    team_alias_lookup,
                    team_info
                )

                home_team_id = home_identity["team_id"]
                away_team_id = away_identity["team_id"]
                team_id = team_identity["team_id"]

                home_team = home_identity["team_display_name"]
                away_team = away_identity["team_display_name"]
                team = team_identity["team_display_name"]

                fid = make_fixture_id(
                    season_id,
                    raw_group,
                    fixture_date,
                    home_team_id,
                    away_team_id
                )

                raw_player = normalize_player_name(
                    row.get("Last Name", "")
                )

                player_id = ""

                if raw_player:
                    player_identity = resolve_player(
                        raw_player,
                        player_alias_lookup,
                        player_info
                    )

                    player_id = player_identity["player_id"]

                stat_desc = row.get("Stat Desc", "").strip().lower()

                # Build player appearance sets from any stat row.
                if team_id and player_id:
                    appearances[(fid, team_id)].add(player_id)

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
                        "fixture_date": fixture_date,

                        "home_team_id": home_team_id,
                        "away_team_id": away_team_id,

                        "home_team": home_team,
                        "away_team": away_team,

                        "raw_home_team": raw_home_team,
                        "raw_away_team": raw_away_team,

                        "scores": defaultdict(int)
                    }

                goals = safe_int(
                    row.get("Stat Value", 0)
                )

                matches[fid]["scores"][team_id] += goals

    return (
        matches,
        appearances,
        team_info,
        player_info,
        team_alias_lookup
    )


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
    team_a_id,
    team_b_id
):
    series = []

    for match in matches.values():
        if match["season_id"] != season_id:
            continue

        if match["division"] != division:
            continue

        if not match_between_team_ids(
            match,
            team_a_id,
            team_b_id
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
        winner_id = get_match_winner_id(match)

        if winner_id:
            wins[winner_id] += 1

    home_id = fallback_final_match["home_team_id"]
    away_id = fallback_final_match["away_team_id"]

    home_wins = wins.get(home_id, 0)
    away_wins = wins.get(away_id, 0)

    if home_wins > away_wins:
        return home_id, away_id, home_wins, away_wins

    if away_wins > home_wins:
        return away_id, home_id, away_wins, home_wins

    # Fallback if something weird happened.
    fallback_winner_id = get_match_winner_id(
        fallback_final_match
    )

    fallback_loser_id = get_match_loser_id(
        fallback_final_match
    )

    if fallback_winner_id:
        return (
            fallback_winner_id,
            fallback_loser_id,
            wins.get(fallback_winner_id, 0),
            wins.get(fallback_loser_id, 0)
        )

    return None, None, 0, 0


# -----------------------------------------------------------------------------
# Roster Eligibility
# -----------------------------------------------------------------------------

def get_team_matches(
    matches,
    season_id,
    divisions,
    team_id
):
    output = []

    for match in matches.values():
        if match["season_id"] != season_id:
            continue

        if match["division"] not in divisions:
            continue

        if not match_involves_team_id(
            match,
            team_id
        ):
            continue

        output.append(match)

    return output


def count_player_games(
    match_list,
    team_id,
    appearances
):
    player_games = defaultdict(set)

    for match in match_list:
        fid = match["fixture_id"]

        players = appearances.get(
            (fid, team_id),
            set()
        )

        for player_id in players:
            player_games[player_id].add(fid)

    return player_games


def build_championship_roster(
    winner_team_id,
    regular_matches,
    playoff_matches,
    finals_matches,
    appearances,
    player_info
):
    regular_player_games = count_player_games(
        regular_matches,
        winner_team_id,
        appearances
    )

    playoff_player_games = count_player_games(
        playoff_matches,
        winner_team_id,
        appearances
    )

    finals_player_games = count_player_games(
        finals_matches,
        winner_team_id,
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

    def player_sort_name(player_id):
        info = player_info.get(player_id, {})
        return (
            info.get("player_display_name")
            or info.get("player_name")
            or player_id
        ).lower()

    for player_id in sorted(players, key=player_sort_name):
        regular_games = len(
            regular_player_games.get(player_id, set())
        )

        playoff_games = len(
            playoff_player_games.get(player_id, set())
        )

        finals_games = len(
            finals_player_games.get(player_id, set())
        )

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

        info = player_info.get(player_id, {})

        player_display_name = (
            info.get("player_display_name")
            or info.get("player_name")
            or player_id
        )

        roster.append({
            "player_id": player_id,
            "player_name": player_display_name,
            "player_display_name": player_display_name,
            "aliases": info.get("aliases", []),

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

    (
        matches,
        appearances,
        team_info,
        player_info,
        team_alias_lookup
    ) = parse_raw_csvs()

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

        finalist_a_id = final_match["home_team_id"]
        finalist_b_id = final_match["away_team_id"]

        series_matches = get_series_matches(
            matches,
            season_id,
            division,
            finalist_a_id,
            finalist_b_id
        )

        (
            winner_team_id,
            runner_up_team_id,
            winner_series_wins,
            runner_up_series_wins
        ) = determine_series_winner(
            series_matches,
            final_match
        )

        if not winner_team_id:
            print(
                f"WARNING: Could not determine winner for "
                f"{season_id} | {division}"
            )

            continue

        winner_info = team_info.get(
            winner_team_id,
            {}
        )

        runner_up_info = team_info.get(
            runner_up_team_id,
            {}
        )

        winner_team = (
            winner_info.get("team_display_name")
            or winner_info.get("team")
            or winner_team_id
        )

        runner_up_team = (
            runner_up_info.get("team_display_name")
            or runner_up_info.get("team")
            or runner_up_team_id
        )

        regular_matches = get_team_matches(
            matches,
            season_id,
            info["regular_divisions"],
            winner_team_id
        )

        playoff_matches = get_team_matches(
            matches,
            season_id,
            [division],
            winner_team_id
        )

        roster = build_championship_roster(
            winner_team_id,
            regular_matches,
            playoff_matches,
            series_matches,
            appearances,
            player_info
        )

        winner_franchise_id = find_franchise_for_team_id(
            winner_team_id,
            season_id,
            franchises,
            team_alias_lookup,
            team_info
        )

        finals_games = []

        for match in series_matches:
            home_score, away_score = get_match_score(match)

            winner_id = get_match_winner_id(match)

            winner_display_name = ""

            if winner_id:
                winner_display_name = (
                    team_info.get(winner_id, {}).get("team_display_name")
                    or team_info.get(winner_id, {}).get("team")
                    or winner_id
                )

            finals_games.append({
                "fixture_id": match["fixture_id"],
                "fixture_date": match["fixture_date"],

                "home_team_id": match["home_team_id"],
                "away_team_id": match["away_team_id"],

                "home_team": match["home_team"],
                "away_team": match["away_team"],

                "raw_home_team": match.get("raw_home_team"),
                "raw_away_team": match.get("raw_away_team"),

                "home_score": home_score,
                "away_score": away_score,

                "winner_team_id": winner_id,
                "winner_team": winner_display_name
            })

        championships.append({
            "season": final_match["season"],
            "season_id": season_id,

            "region": info["region"],
            "championship": info["championship"],
            "playoff_division": division,
            "regular_divisions": info["regular_divisions"],

            "winner_team_id": winner_team_id,
            "winner_team": winner_team,
            "winner_team_display_name": winner_team,
            "winner_team_aliases": winner_info.get("team_aliases", []),
            "winner_logo": winner_info.get("logo", ""),
            "winner_theme": winner_info.get("theme", {}),

            "runner_up_team_id": runner_up_team_id,
            "runner_up_team": runner_up_team,
            "runner_up_team_display_name": runner_up_team,
            "runner_up_team_aliases": runner_up_info.get("team_aliases", []),
            "runner_up_logo": runner_up_info.get("logo", ""),
            "runner_up_theme": runner_up_info.get("theme", {}),

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
            -REGION_ORDER.get(c["region"], 99)
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