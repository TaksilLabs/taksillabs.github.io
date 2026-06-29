import argparse
import json
from itertools import combinations
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SEASON_ID = "summer_2026"

ACTIVE_ROSTERS_FILE = BASE_DIR / "data" / "live_season" / SEASON_ID / "active_rosters.json"
PLAYERS_FILE = BASE_DIR / "data" / "all_time_players.json"
DIVISION_DISPLAY_NAMES_FILE = BASE_DIR / "data" / "division_display_names.json"
ALIASES_FILE = BASE_DIR / "data" / "live_season" / SEASON_ID / "player_aliases.json"

OUTPUT_FILE = BASE_DIR / "data" / "live_season" / SEASON_ID / "conference_seed_report.json"
HTML_OUTPUT_FILE = BASE_DIR / "data" / "live_season" / SEASON_ID / "conference_seed_report.html"

DIVISION_WEIGHTS = {
    "pro": 1.45,
    "challenger": 1.00,
    "intermediate": 0.82,
    "prospect": 0.68,
    "open": 0.58,

    "central a": 1.10,
    "central b": 0.85,
    "central c": 0.62,
    "central d": 0.58,

    "masters": 0.97,
    "contenders": 0.72,
}

DIVISION_REGION_MAP = {
    "pro": "east",
    "challenger": "east",
    "intermediate": "east",
    "prospect": "east",
    "open": "east",

    "central_a": "central",
    "central_b": "central",
    "central_c": "central",
    "central_d": "central",

    "masters": "west",
    "contenders": "west",
}

OUT_OF_REGION_FALLBACK_MULTIPLIER = 0.70


def get_region_for_division(division):
    return DIVISION_REGION_MAP.get(clean(division).lower(), "")

def normalize_division_key(value):
    text = clean(value).lower()
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = " ".join(text.split())

    if text.endswith(" division"):
        text = text.removesuffix(" division").strip()

    return text


def get_normalized_division_name(raw_division, division_display_names):
    raw = clean(raw_division)

    if not raw:
        return ""

    display_name = (
        division_display_names.get(raw)
        or division_display_names.get(raw.upper())
        or division_display_names.get(raw.lower())
        or raw
    )

    return normalize_division_key(display_name)


def get_region_for_raw_division(raw_division, division_display_names):
    normalized = get_normalized_division_name(raw_division, division_display_names)

    if normalized in {"pro", "challenger", "intermediate", "prospect", "open"}:
        return "east"

    if normalized in {"central a", "central b", "central c", "central d"}:
        return "central"

    if normalized in {"masters", "contenders"}:
        return "west"

    # Playoff / cup aliases
    if normalized in {
        "erveon cup playoffs",
        "blade cup playoffs",
        "challenger promotional series",
    }:
        return "east"

    if normalized in {
        "gazz cup playoffs",
    }:
        return "central"

    return ""


def get_division_weight(raw_division, division_display_names):
    normalized = get_normalized_division_name(raw_division, division_display_names)

    return DIVISION_WEIGHTS.get(normalized, 0.75)

def clean(value):
    return str(value or "").strip()


def make_lookup_id(value):
    return clean(value).lower().replace(" ", "_")


def load_json(path, fallback):
    if not path.exists():
        print(f"Missing file: {path}")
        return fallback

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def normalize_player_key(value):
    text = clean(value).lower()
    text = text.replace(" ", "_")
    return text


def build_player_lookup(players, aliases=None):
    aliases = aliases or {}
    lookup = {}

    for player in players:
        keys = [
            player.get("player_id"),
            player.get("player_name"),
            player.get("player_display_name"),
            player.get("display_name"),
            player.get("name"),
            *(player.get("aliases") or []),
        ]

        for key in keys:
            norm = normalize_player_key(key)
            if norm:
                lookup[norm] = player

    # Manual aliases:
    # roster name -> historical player name
    for roster_name, historical_name in aliases.items():
        roster_key = normalize_player_key(roster_name)
        historical_key = normalize_player_key(historical_name)

        if roster_key and historical_key and historical_key in lookup:
            lookup[roster_key] = lookup[historical_key]

    return lookup


def calculate_rating_from_seasons(seasons, division_display_names, multiplier=1.0):
    weighted_games = 0
    weighted_goals = 0
    weighted_assists = 0
    weighted_points = 0
    weighted_saves = 0
    weighted_blocks = 0
    weighted_shots = 0

    raw_games = 0

    for season in seasons:
        stats = season.get("stats") or {}
        gp = float(stats.get("games_played") or 0)

        if gp <= 0:
            continue

        weight = get_division_weight(
            season.get("division"),
            division_display_names
        )

        raw_games += gp
        weighted_games += gp * weight

        weighted_goals += float(stats.get("goals") or 0) * weight
        weighted_assists += float(stats.get("assists") or 0) * weight
        weighted_points += float(stats.get("points") or 0) * weight
        weighted_saves += float(stats.get("saves") or 0) * weight
        weighted_blocks += float(stats.get("blocks") or 0) * weight
        weighted_shots += float(stats.get("shots") or 0) * weight

    if weighted_games <= 0:
        return 0

    goals_pg = weighted_goals / weighted_games
    assists_pg = weighted_assists / weighted_games
    points_pg = weighted_points / weighted_games
    saves_pg = weighted_saves / weighted_games
    blocks_pg = weighted_blocks / weighted_games
    shots_pg = weighted_shots / weighted_games

    reliability = min(raw_games, 60) / 60

    base = (
        points_pg * 3.0
        + goals_pg * 2.0
        + assists_pg * 1.0
        + shots_pg * 0.15
        + saves_pg * 0.35
        + blocks_pg * 0.50
    )

    return round(base * (0.75 + 0.25 * reliability) * multiplier, 3)


def player_rating(player, division_display_names=None, target_region=""):
    division_display_names = division_display_names or {}
    target_region = clean(target_region).lower()

    if not player:
        return {
            "rating": 0,
            "used_region": target_region,
            "used_fallback": False,
            "region_games": 0,
            "total_games": 0,
        }

    seasons = (
        player.get("seasons")
        or player.get("season_by_season")
        or player.get("season_stats")
        or []
    )

    if seasons:
        same_region_seasons = []
        all_valid_seasons = []

        for season in seasons:
            stats = season.get("stats") or {}
            gp = float(stats.get("games_played") or 0)

            if gp <= 0:
                continue

            season_region = get_region_for_raw_division(
                season.get("division"),
                division_display_names
            )

            all_valid_seasons.append(season)

            if target_region and season_region == target_region:
                same_region_seasons.append(season)

        if same_region_seasons:
            rating = calculate_rating_from_seasons(
                same_region_seasons,
                division_display_names,
                multiplier=1.0,
            )

            return {
                "rating": rating,
                "used_region": target_region,
                "used_fallback": False,
                "region_games": sum(
                    float((season.get("stats") or {}).get("games_played") or 0)
                    for season in same_region_seasons
                ),
                "total_games": sum(
                    float((season.get("stats") or {}).get("games_played") or 0)
                    for season in all_valid_seasons
                ),
            }

        if all_valid_seasons:
            rating = calculate_rating_from_seasons(
                all_valid_seasons,
                division_display_names,
                multiplier=OUT_OF_REGION_FALLBACK_MULTIPLIER,
            )

            return {
                "rating": rating,
                "used_region": target_region,
                "used_fallback": True,
                "region_games": 0,
                "total_games": sum(
                    float((season.get("stats") or {}).get("games_played") or 0)
                    for season in all_valid_seasons
                ),
            }

    # Fallback for older/collapsed player data
    stats = player.get("career") or player.get("stats") or {}
    gp = float(stats.get("games_played") or 0)

    if gp <= 0:
        return {
            "rating": 0,
            "used_region": target_region,
            "used_fallback": False,
            "region_games": 0,
            "total_games": 0,
        }

    goals_pg = float(stats.get("goals") or 0) / gp
    assists_pg = float(stats.get("assists") or 0) / gp
    points_pg = float(stats.get("points") or 0) / gp
    saves_pg = float(stats.get("saves") or 0) / gp
    blocks_pg = float(stats.get("blocks") or 0) / gp
    shots_pg = float(stats.get("shots") or 0) / gp

    reliability = min(gp, 60) / 60

    base = (
        points_pg * 3.0
        + goals_pg * 2.0
        + assists_pg * 1.0
        + shots_pg * 0.15
        + saves_pg * 0.35
        + blocks_pg * 0.50
    )

    return {
        "rating": round(base * (0.75 + 0.25 * reliability), 3),
        "used_region": target_region,
        "used_fallback": True,
        "region_games": 0,
        "total_games": gp,
    }


def roster_player_name(entry):
    return (
        entry.get("steam_name")
        or entry.get("player_name")
        or entry.get("player_display_name")
        or entry.get("name")
        or entry.get("slap_id")
        or "Unknown Player"
    )


def roster_player_key(entry):
    return normalize_player_key(
        entry.get("steam_name")
        or entry.get("player_name")
        or entry.get("player_display_name")
        or entry.get("name")
        or ""
    )


def group_roster_entries(players):
    grouped = {}

    for entry in players:
        key = roster_player_key(entry)
        if not key:
            continue

        if key not in grouped:
            grouped[key] = {
                "name": roster_player_name(entry),
                "entries": [],
                "roles": set(),
            }

        grouped[key]["entries"].append(entry)
        grouped[key]["roles"].add(clean(entry.get("role")).lower() or "player")

    return list(grouped.values())


def is_playable(group):
    roles = group["roles"]

    # GM-only cannot play. GM + Captain/Player can count.
    return roles != {"gm"}


def rate_team(
    team,
    player_lookup,
    division_display_names,
    target_region,
    show_region_fallbacks=False,
):
    grouped_players = group_roster_entries(team.get("players") or [])

    eligible = []
    excluded = []

    for group in grouped_players:
        if not is_playable(group):
            excluded.append({
                "name": group["name"],
                "roles": sorted(group["roles"]),
                "reason": "GM only",
            })
            continue

        lookup_key = normalize_player_key(group["name"])
        player = player_lookup.get(lookup_key)

        rating_info = player_rating(
            player,
            division_display_names,
            target_region=target_region,
        ) if player else {
            "rating": 0,
            "used_fallback": False,
            "region_games": 0,
            "total_games": 0,
        }

        rating = rating_info["rating"]

        eligible.append({
            "name": group["name"],
            "roles": sorted(group["roles"]),
            "rating": rating,
            "matched": bool(player),
            "rating_region": target_region,
            "used_region_fallback": rating_info["used_fallback"],
            "region_games": rating_info["region_games"],
            "total_games": rating_info["total_games"],
        })

    eligible.sort(key=lambda p: p["rating"], reverse=True)

    best_lineup = eligible[:3]
    rating_lineup = eligible[:2]

    team_rating = round(sum(p["rating"] for p in rating_lineup), 3)

    warnings = []

    if len(rating_lineup) < 2:
        warnings.append("Fewer than 2 eligible players for rating")

    if len(best_lineup) < 3:
        warnings.append("Fewer than 3 eligible players for Best 3 display")

    missing = [p["name"] for p in eligible if not p["matched"]]
    if missing:
        warnings.append(f"Unmatched players: {', '.join(missing)}")

    if show_region_fallbacks:
        fallback_players = [
            p["name"]
            for p in eligible
            if p["matched"] and p.get("used_region_fallback")
        ]

        if fallback_players:
            warnings.append(
                f"No same-region history, used fallback: {', '.join(fallback_players)}"
            )

    return {
        "team_id": team.get("team_id"),
        "team_display_name": team.get("team_display_name") or team.get("team") or team.get("team_id"),
        "division": team.get("division"),
        "conference": team.get("conference", ""),
        "rating": team_rating,
        "rating_lineup": rating_lineup,
        "best_lineup": best_lineup,
        "eligible_players": eligible,
        "excluded_players": excluded,
        "warnings": warnings,
    }


def snake_seed(teams, conference_count):
    conferences = [{"slot": str(i + 1), "teams": []} for i in range(conference_count)]

    sorted_teams = sorted(teams, key=lambda t: t["rating"], reverse=True)

    direction = 1
    index = 0

    for team in sorted_teams:
        conferences[index]["teams"].append(team)

        if conference_count == 1:
            continue

        if direction == 1:
            if index == conference_count - 1:
                direction = -1
            else:
                index += 1
        else:
            if index == 0:
                direction = 1
            else:
                index -= 1

    return conferences


def conference_total(conference):
    return round(sum(team["rating"] for team in conference["teams"]), 3)


def balance_two_conferences(conferences):
    if len(conferences) != 2:
        return conferences

    improved = True

    while improved:
        improved = False

        a = conferences[0]
        b = conferences[1]

        current_diff = abs(conference_total(a) - conference_total(b))
        best_swap = None
        best_diff = current_diff

        for team_a, team_b in combinations(a["teams"] + b["teams"], 2):
            if team_a in a["teams"] and team_b in b["teams"]:
                new_a_total = conference_total(a) - team_a["rating"] + team_b["rating"]
                new_b_total = conference_total(b) - team_b["rating"] + team_a["rating"]
            elif team_a in b["teams"] and team_b in a["teams"]:
                new_a_total = conference_total(a) - team_b["rating"] + team_a["rating"]
                new_b_total = conference_total(b) - team_a["rating"] + team_b["rating"]
            else:
                continue

            new_diff = abs(new_a_total - new_b_total)

            if new_diff < best_diff:
                best_diff = new_diff
                best_swap = (team_a, team_b)

        if best_swap:
            team_a, team_b = best_swap

            if team_a in a["teams"]:
                a["teams"].remove(team_a)
                b["teams"].remove(team_b)
                a["teams"].append(team_b)
                b["teams"].append(team_a)
            else:
                b["teams"].remove(team_a)
                a["teams"].remove(team_b)
                b["teams"].append(team_b)
                a["teams"].append(team_a)

            improved = True

    return conferences


def build_report(division, conference_count, show_region_fallbacks=False):
    roster_data = load_json(ACTIVE_ROSTERS_FILE, {"teams": []})
    division_display_names = load_json(DIVISION_DISPLAY_NAMES_FILE, {})
    players = load_json(PLAYERS_FILE, [])
    aliases = load_json(ALIASES_FILE, {})

    player_lookup = build_player_lookup(players, aliases)

    target_region = get_region_for_division(division)

    teams = [
        team for team in roster_data.get("teams", [])
        if clean(team.get("division")).lower() == division
    ]

    rated_teams = [
        rate_team(
            team,
            player_lookup,
            division_display_names,
            target_region,
            show_region_fallbacks=show_region_fallbacks,
        )
        for team in teams
    ]

    conferences = snake_seed(rated_teams, conference_count)

    if conference_count == 2:
        conferences = balance_two_conferences(conferences)

    for conference in conferences:
        conference["rating_total"] = conference_total(conference)
        conference["teams"].sort(key=lambda t: t["rating"], reverse=True)

    return {
        "season_id": roster_data.get("season_id", SEASON_ID),
        "division": division,
        "target_region": target_region,
        "conference_count": conference_count,
        "team_count": len(rated_teams),
        "conferences": conferences,
    }


def print_report(report):
    print()
    print(f"{report['division'].title()} Conference Seeding")
    print(f"Teams: {report['team_count']}")
    print()

    for conference in report["conferences"]:
        print(f"Conference {conference['slot']} — Total {conference['rating_total']}")
        print("-" * 48)

        for team in conference["teams"]:
            print(f"{team['team_display_name']} — {team['rating']} Top 2 Rating")

            lineup = ", ".join(
                f"{p['name']} ({p['rating']})"
                for p in team["best_lineup"]
            )

            print(f"  Best 3: {lineup or 'None'}")

            for warning in team["warnings"]:
                print(f"  WARNING: {warning}")

        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--division", default="central_b")
    parser.add_argument("--conference-count", type=int, default=2)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--write-html", action="store_true")
    parser.add_argument("--show-region-fallbacks", action="store_true")

    args = parser.parse_args()

    report = build_report(
        division=args.division.lower(),
        conference_count=args.conference_count,
        show_region_fallbacks=args.show_region_fallbacks,
    )

    print_report(report)

    if args.write_report:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with OUTPUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"Wrote report: {OUTPUT_FILE}")

    if args.write_html:
        HTML_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with HTML_OUTPUT_FILE.open("w", encoding="utf-8") as f:
            f.write(build_html_report(report))

        print(f"Wrote HTML report: {HTML_OUTPUT_FILE}")


def escape_html(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def format_lineup(team):
    if not team["best_lineup"]:
        return "<span class='muted'>No eligible lineup</span>"

    return "".join(
        f"""
        <div class="lineup-player">
          <strong>{escape_html(player["name"])}</strong>
        </div>
        """
        for player in team["best_lineup"]
    )


def format_warnings(team):
    warnings = team.get("warnings") or []

    if not warnings:
        return "<span class='good'>Clear</span>"

    return "".join(
        f"<div class='warning'>{escape_html(warning)}</div>"
        for warning in warnings
    )


def get_report_difference(report):
    totals = [
        float(conference.get("rating_total") or 0)
        for conference in report["conferences"]
    ]

    if not totals:
        return 0

    return round(max(totals) - min(totals), 3)


def render_conference_html(conference):
    rows = "".join(
        f"""
        <tr>
          <td>
            <strong>{escape_html(team["team_display_name"])}</strong>
          </td>
          <td>{format_lineup(team)}</td>
          <td>{format_warnings(team)}</td>
        </tr>
        """
        for team in conference["teams"]
    )

    return f"""
    <section class="conference-card">
      <div class="conference-head">
        <div>
          <span>Conference {escape_html(conference["slot"])}</span>
          <h2>Conference {escape_html(conference["slot"])}</h2>
        </div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Team</th>
            <th>Best 3 Lineup</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </section>
    """


def build_html_report(report):
    conference_totals = [
        conference.get("rating_total", 0)
        for conference in report["conferences"]
    ]

    conference_cards = "".join(
        render_conference_html(conference)
        for conference in report["conferences"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{escape_html(report["division"].title())} Conference Seeding Report</title>

  <style>
    :root {{
      --bg: #05080c;
      --card: #0c141c;
      --surface: #111c26;
      --line: #244255;
      --text: #f4f4f4;
      --muted: #9fb3c8;
      --accent: #00d1d1;
      --gold: #ffd166;
      --good: #5cff9d;
      --warn: #ffcc66;
      --danger: #ff6b6b;
    }}

    .controls-card {{
        display: flex;
        justify-content: flex-end;
        margin-bottom: 18px;
    }}

    .controls-card button {{
        padding: 10px 14px;

        border: 1px solid var(--accent);
        border-radius: 999px;

        background: rgba(0, 209, 209, 0.12);
        color: var(--text);

        font-weight: 900;
        letter-spacing: 0.05em;
        text-transform: uppercase;

        cursor: pointer;
    }}

    .controls-card button:hover {{
        background: rgba(0, 209, 209, 0.2);
    }}

    .hide-player-ratings .player-rating {{
        display: none;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      padding: 28px;
      background:
        radial-gradient(circle at top right, rgba(0, 209, 209, 0.13), transparent 34%),
        var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
    }}

    .page {{
      max-width: 1280px;
      margin: 0 auto;
    }}

    .hero {{
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background:
        linear-gradient(135deg, rgba(0, 209, 209, 0.10), transparent),
        rgba(12, 20, 28, 0.92);
      margin-bottom: 18px;
    }}

    .hero span {{
      color: var(--accent);
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.78rem;
    }}

    h1 {{
      margin: 8px 0 8px;
      font-size: 2.2rem;
    }}

    .hero p {{
      max-width: 850px;
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      font-weight: 700;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}

    .summary-card {{
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(12, 20, 28, 0.82);
    }}

    .summary-card span {{
      display: block;
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 7px;
    }}

    .summary-card strong {{
      color: var(--gold);
      font-size: 1.45rem;
    }}

    .method-card {{
      padding: 18px 20px;
      border: 1px solid rgba(255, 209, 102, 0.32);
      border-radius: 18px;
      background: rgba(255, 209, 102, 0.06);
      margin-bottom: 18px;
    }}

    .method-card h2 {{
      margin: 0 0 10px;
      color: var(--gold);
    }}

    .method-card ul {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
      font-weight: 750;
      line-height: 1.55;
    }}

    .conference-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      align-items: start;
    }}

    .conference-card {{
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      background: rgba(12, 20, 28, 0.88);
    }}

    .conference-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px;
      border-bottom: 1px solid var(--line);
      background:
        radial-gradient(circle at left, rgba(0, 209, 209, 0.13), transparent 42%),
        rgba(17, 28, 38, 0.92);
    }}

    .conference-head span {{
      color: var(--accent);
      font-size: 0.72rem;
      font-weight: 900;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}

    .conference-head h2 {{
      margin: 4px 0 0;
    }}

    .conference-head > strong {{
      color: var(--gold);
      font-size: 1.7rem;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
    }}

    th,
    td {{
      padding: 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      vertical-align: top;
      text-align: left;
    }}

    th {{
      color: var(--muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: rgba(255, 255, 255, 0.035);
    }}

    td.rating {{
      color: var(--gold);
      font-weight: 900;
      white-space: nowrap;
    }}

    .lineup-player {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 3px 0;
      color: var(--text);
    }}

    .lineup-player span {{
      color: var(--accent);
      font-weight: 900;
    }}

    .warning {{
      color: var(--warn);
      font-size: 0.78rem;
      font-weight: 800;
      line-height: 1.35;
    }}

    .good {{
      color: var(--good);
      font-weight: 900;
      font-size: 0.82rem;
    }}

    .muted {{
      color: var(--muted);
      font-weight: 800;
    }}

    @media (max-width: 1050px) {{
      body {{
        padding: 14px;
      }}

      .summary-grid,
      .conference-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>

<body class="hide-player-ratings">
  <main class="page">
    <section class="hero">
      <span>{escape_html(report["season_id"])}</span>
      <h1>{escape_html(report["division"].title())} Conference Seeding Report</h1>
      <p>
        Suggested conference split based on current roster strength.
        Team ratings use each team’s top 2 eligible players, while the Best 3 lineup is shown for context.
      </p>
    </section>

    <section class="summary-grid">
        <article class="summary-card">
            <span>Teams</span>
            <strong>{report["team_count"]}</strong>
        </article>

        <article class="summary-card">
            <span>Conferences</span>
            <strong>{report["conference_count"]}</strong>
        </article>

        <article class="summary-card">
            <span>Seeding Method</span>
            <strong>Top 2</strong>
        </article>

        <article class="summary-card">
            <span>Display</span>
            <strong>Best 3</strong>
        </article>
    </section>

    <section class="controls-card">
        <button type="button" onclick="document.body.classList.toggle('hide-player-ratings')">
            Toggle Player Scores
        </button>
    </section>

    <section class="method-card">
      <h2>Method</h2>
      <ul>
        <li>Conference balance is based on each team’s top 2 eligible players.</li>
        <li>The Best 3 column is shown for context because Slapshot is played 3v3.</li>
        <li>GM-only roster entries are excluded because they cannot play for that team.</li>
        <li>Player ratings are weighted by historical division strength.</li>
        <li>Unmatched players count as 0 until an alias is added.</li>
      </ul>
    </section>

    <section class="conference-grid">
      {conference_cards}
    </section>
  </main>
</body>
</html>
"""

if __name__ == "__main__":
    main()