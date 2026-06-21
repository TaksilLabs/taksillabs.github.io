import csv
import json
import re
from datetime import datetime
from pathlib import Path


PRESEASON_REGIONS = {
    "E": "east",
    "C": "central",
    "W": "west",
}


def read_tsv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def clean_text(value):
    return str(value or "").strip()


def make_id(value, fallback="unknown"):
    text = clean_text(value).lower()
    text = re.sub(r"\s*\([A-Z0-9]{2,8}\)\s*$", "", text)
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or fallback


def get_preseason_region(match_id):
    text = clean_text(match_id).upper()

    if not text:
        return "unknown"

    return PRESEASON_REGIONS.get(text[0], "unknown")


def make_preseason_match_id(season_id, match_id):
    region = get_preseason_region(match_id)
    safe_match_id = clean_text(match_id).lower()

    return f"{season_id}_preseason_{region}_{safe_match_id}"


def parse_uploaded_match_folder(folder_name):
    pattern = (
        r"^(?P<schedule_id>[^_]+)_\s*"
        r"(?P<home>.*?)\s+vs\s+"
        r"(?P<away>.*?)__+"
        r"(?P<thread_id>\d+)$"
    )

    match = re.match(pattern, clean_text(folder_name))

    if not match:
        return None

    return {
        "schedule_id": clean_text(match.group("schedule_id")),
        "home_team": clean_text(match.group("home")),
        "away_team": clean_text(match.group("away")),
        "thread_id": clean_text(match.group("thread_id")),
    }


def safe_period(data):
    try:
        return int(data.get("current_period", 0))
    except Exception:
        return 0


def parse_created_timestamp(file_path):
    try:
        date_part = file_path.stem.split("_")[-1]
        dt = datetime.strptime(date_part, "%Y-%m-%d-%H-%M-%S")
        return dt, dt.strftime("%Y-%m-%d")
    except Exception:
        return None, None


def load_json_report(file_path):
    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as error:
        return None, str(error)

    created_dt, date = parse_created_timestamp(file_path)

    return {
        "file_path": file_path,
        "data": data,
        "period": safe_period(data),
        "created_dt": created_dt,
        "date": date,
    }, None


def choose_best_report(reports):
    return max(
        reports,
        key=lambda report: (
            report["period"],
            report["created_dt"] or datetime.min
        )
    )


def get_team_score_from_report(data, team_name):
    target = clean_text(team_name).lower()

    for team in data.get("teams", []):
        name = clean_text(
            team.get("team_name")
            or team.get("name")
            or team.get("team")
        ).lower()

        if name == target:
            return int(team.get("score", 0))

    return None


def get_scores_from_report(data, home_team, away_team):
    home_score = get_team_score_from_report(data, home_team)
    away_score = get_team_score_from_report(data, away_team)

    if home_score is not None and away_score is not None:
        return home_score, away_score

    # Fallback for logs that store scores differently.
    try:
        teams = data.get("teams", [])
        if len(teams) >= 2:
            return int(teams[0].get("score", 0)), int(teams[1].get("score", 0))
    except Exception:
        pass

    return None, None

def is_overtime_report(data):
    return clean_text(data.get("end_reason")).lower() == "overtime"

def load_signup_active_rosters(signups_file):
    """
    Builds active team rosters from the Google Form signup CSV.

    The signup CSV has repeated player columns, so this intentionally uses
    csv.reader + fixed column indexes instead of DictReader.

    Expected relevant columns:
      2  Region
      3  Team Name
      4  Team Abbreviation
      8-10   GM Discord / Steam / Slap
      11-13  Captain Discord / Steam / Slap
      14-16  Player Slot 1 Discord / Steam / Slap
      17-19  Player Slot 2 Discord / Steam / Slap
      20-22  Player Slot 3 Discord / Steam / Slap
      23-25  Player Slot 4 Discord / Steam / Slap
      26-28  Player Slot 5 Discord / Steam / Slap
    """

    if not signups_file.exists():
        return {}

    rosters = {}

    with signups_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        rows = list(reader)

    if not rows:
        return {}

    # Skip header row.
    for row in rows[1:]:
        if len(row) < 4:
            continue

        region = clean_text(row[2]) if len(row) > 2 else ""
        team_name = clean_text(row[3]) if len(row) > 3 else ""
        team_abbreviation = clean_text(row[4]) if len(row) > 4 else ""

        if not team_name:
            continue

        team_id = make_id(team_name, "unknown_team")

        roster = {
            "team_id": team_id,
            "team_display_name": team_name,
            "team": team_name,
            "team_abbreviation": team_abbreviation,
            "region": region.lower(),
            "players": [],
            "slap_ids": [],
        }

        player_slots = [
            ("gm", 9, 10),
            ("captain", 12, 13),
            ("player", 15, 16),
            ("player", 18, 19),
            ("player", 21, 22),
            ("player", 24, 25),
            ("player", 27, 28),
        ]

        seen_slap_ids = set()

        for role, steam_col, slap_col in player_slots:
            steam_name = clean_text(row[steam_col]) if len(row) > steam_col else ""
            slap_id = clean_text(row[slap_col]) if len(row) > slap_col else ""

            if not steam_name and not slap_id:
                continue

            # If no slap_id exists, keep the player for display,
            # but they will not help game-log matching.
            player = {
                "role": role,
                "steam_name": steam_name,
                "slap_id": slap_id,
            }

            roster["players"].append(player)

            if slap_id and slap_id not in seen_slap_ids:
                seen_slap_ids.add(slap_id)
                roster["slap_ids"].append(slap_id)

        rosters[team_id] = roster

    return rosters

def normalize_slap_id(value):
    return clean_text(value)


def get_report_side_player_ids(data):
    sides = {
        "home": set(),
        "away": set(),
    }

    for player in data.get("players", []):
        side = clean_text(player.get("team")).lower()
        slap_id = normalize_slap_id(player.get("game_user_id"))

        if side in sides and slap_id:
            sides[side].add(slap_id)

    return sides


def load_active_roster_lookup(active_rosters_file):
    if not active_rosters_file.exists():
        return {}

    with active_rosters_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    lookup = {}

    for team in data.get("teams", []):
        team_id = team.get("team_id")

        if not team_id:
            continue

        lookup[team_id] = set(
            normalize_slap_id(slap_id)
            for slap_id in team.get("slap_ids", [])
            if normalize_slap_id(slap_id)
        )

    return lookup


def determine_report_side_mapping(data, scheduled_home_team_id, scheduled_away_team_id, roster_lookup):
    report_sides = get_report_side_player_ids(data)

    scheduled_home_roster = roster_lookup.get(scheduled_home_team_id, set())
    scheduled_away_roster = roster_lookup.get(scheduled_away_team_id, set())

    report_home_ids = report_sides["home"]
    report_away_ids = report_sides["away"]

    normal_score = (
        len(report_home_ids & scheduled_home_roster)
        + len(report_away_ids & scheduled_away_roster)
    )

    swapped_score = (
        len(report_home_ids & scheduled_away_roster)
        + len(report_away_ids & scheduled_home_roster)
    )

    if normal_score > swapped_score:
        return {
            "mapping": "normal",
            "confidence": normal_score,
            "normal_score": normal_score,
            "swapped_score": swapped_score,
        }

    if swapped_score > normal_score:
        return {
            "mapping": "swapped",
            "confidence": swapped_score,
            "normal_score": normal_score,
            "swapped_score": swapped_score,
        }

    return {
        "mapping": "unknown",
        "confidence": normal_score,
        "normal_score": normal_score,
        "swapped_score": swapped_score,
    }


def get_scores_from_report_with_rosters(data, match, roster_lookup):
    score = data.get("score", {})

    try:
        log_home_score = int(score.get("home"))
        log_away_score = int(score.get("away"))
    except Exception:
        return None, None, {
            "mapping": "unknown",
            "confidence": 0,
            "normal_score": 0,
            "swapped_score": 0,
        }

    mapping = determine_report_side_mapping(
        data,
        match["home_team_id"],
        match["away_team_id"],
        roster_lookup
    )

    if mapping["mapping"] == "normal":
        return log_home_score, log_away_score, mapping

    if mapping["mapping"] == "swapped":
        return log_away_score, log_home_score, mapping

    return None, None, mapping