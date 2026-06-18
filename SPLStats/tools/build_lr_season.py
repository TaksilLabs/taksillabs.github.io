import csv
import json
import re
from pathlib import Path
from collections import defaultdict

from player_identity import load_player_identities, resolve_player_identity


RAW_CSV_DIR = Path("../raw_csv")
OUT_DIR = Path("../data/seasons")


STAT_MAP = {
    "Games Played": "games_played",
    "Periods Played": "periods_played",
    "Points": "points",
    "Goals": "goals",

    "Assists": "assists",

    "Prim. Assists": "primary_assists",
    "Primary Assists": "primary_assists",

    "Sec. Assists": "secondary_assists",
    "Secondary Assists": "secondary_assists",

    "Shots": "shots",
    "Posts Hit": "post_hits",
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


def clean_team_name(team_name):
    team_name = str(team_name or "").strip()

    # Remove trailing "(XYZ)"
    team_name = re.sub(r"\s*\([^)]*\)\s*$", "", team_name)

    return team_name


def get_fixture_id(row):
    return "|".join([
        row.get("Fixture Group", "").strip(),
        row.get("Fixture Date", "").strip(),
        clean_team_name(row.get("Home Team", "")),
        clean_team_name(row.get("Away Team", "")),
    ])


def classify_season_type(fixture_group):
    text = str(fixture_group or "").lower()

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
        "playoffs",
    ]

    if any(word in text for word in playoff_words):
        return "postseason"

    return "regular_season"


def season_from_filename(path):
    # SPL-Winter2025.csv -> ("Winter 2025", "winter_2025")
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


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def parse_csv(csv_file, alias_lookup):
    season_name, season_id = season_from_filename(csv_file)

    players = {}

    rows = []
    fixture_team_totals = defaultdict(
        lambda: defaultdict(lambda: defaultdict(float))
    )

    # -------------------------------------------------------------------------
    # Pass 1:
    # Read every row and calculate each team's total Goals/Shots per fixture.
    # -------------------------------------------------------------------------

    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

            fixture_id = get_fixture_id(row)
            team = clean_team_name(row.get("Team", ""))
            stat_desc = row.get("Stat Desc", "").strip()
            value = safe_float(row.get("Stat Value", 0))

            if stat_desc == "Goals":
                fixture_team_totals[fixture_id][team]["goals"] += value

            if stat_desc == "Shots":
                fixture_team_totals[fixture_id][team]["shots"] += value

    # -------------------------------------------------------------------------
    # Pass 2:
    # Build player stats and track which fixtures each player appeared in.
    # -------------------------------------------------------------------------

    for row in rows:
        fixture_group = row.get("Fixture Group", "").strip()

        raw_player_name = row.get("Last Name", "").strip()

        if not raw_player_name:
            continue

        identity = resolve_player_identity(
            raw_player_name,
            alias_lookup
        )

        player_id = identity["player_id"]
        player_display_name = identity["player_display_name"]
        player_aliases = identity.get("aliases", [])

        team_name = clean_team_name(row.get("Team", ""))
        team = team_name

        stat_desc = row.get("Stat Desc", "").strip()
        stat_key = STAT_MAP.get(stat_desc)

        if not player_id or not stat_key:
            continue

        # Use player_id for grouping so aliases/name changes merge correctly.
        key = (
            fixture_group,
            team,
            player_id,
        )

        if key not in players:
            players[key] = {
                "season": season_name,
                "season_id": season_id,
                "division": fixture_group,
                "team": team,
                "team_name": team_name,

                # Stable identity
                "player_id": player_id,

                # Human display fields
                "player_name": player_display_name,
                "player_display_name": player_display_name,

                # Useful for old links/search/debugging
                "aliases": player_aliases,

                "fixtures": set(),
                "stats": defaultdict(float),

                # Used to avoid double-counting assists when both
                # Assists and Primary/Secondary Assists exist.
                "has_assists_stat": False,
            }

        fixture_id = get_fixture_id(row)

        players[key]["fixtures"].add(fixture_id)
        players[key]["stats"][stat_key] += safe_float(
            row.get("Stat Value", 0)
        )

        if stat_key == "assists":
            players[key]["has_assists_stat"] = True

    # -------------------------------------------------------------------------
    # Pass 3:
    # After fixture appearances are known, assign Goals Against / Shots Against
    # exactly once per player per fixture.
    # -------------------------------------------------------------------------

    for item in players.values():
        team = item["team"]

        for fixture_id in item["fixtures"]:
            teams_in_fixture = fixture_team_totals[fixture_id]

            opponents = [
                t for t in teams_in_fixture.keys()
                if t != team
            ]

            if not opponents:
                continue

            # This assumes two-team fixtures, which matches LR match rows.
            opponent = opponents[0]

            item["stats"]["goals_against"] += (
                teams_in_fixture[opponent]["goals"]
            )

            item["stats"]["shots_against"] += (
                teams_in_fixture[opponent]["shots"]
            )

    # -------------------------------------------------------------------------
    # Pass 4:
    # Finalize derived stats and write output rows.
    # -------------------------------------------------------------------------

    output = []

    for item in players.values():
        stats = dict(item["stats"])

        goals = stats.get("goals", 0)

        raw_assists = stats.get("assists", 0)
        primary_assists = stats.get("primary_assists", 0)
        secondary_assists = stats.get("secondary_assists", 0)

        if item.get("has_assists_stat"):
            assists = raw_assists
        else:
            assists = primary_assists + secondary_assists

        stats["assists"] = assists

        shots = stats.get("shots", 0)
        saves = stats.get("saves", 0)
        faceoffs_won = stats.get("faceoffs_won", 0)
        faceoffs_lost = stats.get("faceoffs_lost", 0)

        goals_against = stats.get("goals_against", 0)
        shots_against = stats.get("shots_against", 0)
        games_played = len(item["fixtures"])

        stats["points"] = goals + assists
        stats["games_played"] = games_played

        stats["shot_percent"] = (
            goals / shots * 100
            if shots
            else 0
        )

        stats["save_percent"] = (
            saves / shots_against * 100
            if shots_against
            else 0
        )

        stats["gaa"] = (
            goals_against / games_played
            if games_played
            else 0
        )

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
            "team": item["team"],
            "team_name": item["team_name"],

            # Stable identity
            "player_id": item["player_id"],

            # Backwards-compatible display name
            "player_name": item["player_display_name"],

            # Preferred display field
            "player_display_name": item["player_display_name"],

            # Old/current names that resolve to this player
            "aliases": item.get("aliases", []),

            "stats": {
                k: round(v, 2)
                for k, v in stats.items()
            },
        })

    output.sort(
        key=lambda p: (
            p["season_id"],
            p["division"],
            p["team"],
            p.get("player_id", "").lower(),
        )
    )

    return season_id, output


def main():
    alias_lookup, _ = load_player_identities()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(RAW_CSV_DIR.glob("SPL-*.csv"))

    if not csv_files:
        print(f"No CSV files found in: {RAW_CSV_DIR.resolve()}")
        return

    total_rows = 0

    for csv_file in csv_files:
        season_id, output = parse_csv(
            csv_file,
            alias_lookup
        )

        out_file = OUT_DIR / f"{season_id}.json"

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(
                output,
                f,
                indent=2,
                ensure_ascii=False
            )

        total_rows += len(output)

        print(
            f"{csv_file.name} -> "
            f"{out_file.name} | rows: {len(output)}"
        )

    print()
    print(f"CSV files parsed: {len(csv_files)}")
    print(f"Total season-player rows written: {total_rows}")
    print(f"Output folder: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()