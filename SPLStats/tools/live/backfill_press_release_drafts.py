import json
import re
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

SEASON_ID = "summer_2026"
SEASON_NAME = "Summer 2026"

TRANSACTIONS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "roster_transactions.json"
)

PRESS_RELEASE_DRAFTS_FILE = (
    BASE_DIR
    / "data"
    / "live_season"
    / SEASON_ID
    / "news"
    / "press_release_drafts.json"
)


def clean(value):
    return str(value or "").strip()


def load_json(path, fallback):
    if not path.exists():
        return fallback

    try:
        with path.open("r", encoding="utf-8") as file:
            raw = file.read().strip()

        if not raw:
            return fallback

        return json.loads(raw)

    except json.JSONDecodeError:
        print(f"WARNING: Invalid JSON in {path}. Using fallback.")
        return fallback


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def utc_now_iso():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def make_id(value, fallback="unknown"):
    text = clean(value).lower()

    text = text.replace("&", "and")
    text = text.replace("$", "s")
    text = text.replace("@", "a")
    text = text.replace("!", "i")
    text = text.replace("’", "")
    text = text.replace("'", "")

    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    return text or fallback


def make_slug(value):
    return make_id(value).replace("_", "-")


def get_transaction_day_key(transaction):
    created_at = clean(transaction.get("created_at_utc"))

    if "T" in created_at:
        return created_at.split("T", 1)[0]

    return created_at[:10] or utc_now_iso().split("T", 1)[0]


def get_short_team_name(source):
    team_name = clean(source.get("team_display_name"))

    replacements = [
        "Long Island ",
        "Atlantic City ",
        "Battle Creek ",
        "Camden ",
        "Yucatan ",
    ]

    for replacement in replacements:
        if team_name.startswith(replacement):
            return team_name.replace(replacement, "", 1)

    return team_name or clean(source.get("team_abbreviation")) or "the team"


def format_transaction_player_name(transaction):
    player_name = clean(transaction.get("player_display_name")) or "Unknown Player"
    jersey_number = clean(transaction.get("jersey_number"))

    if jersey_number:
        return f"#{jersey_number} {player_name}"

    return player_name


def join_names(names):
    names = [name for name in names if clean(name)]

    if not names:
        return ""

    if len(names) == 1:
        return names[0]

    if len(names) == 2:
        return f"{names[0]} and {names[1]}"

    return f"{', '.join(names[:-1])}, and {names[-1]}"


def group_transactions_for_press_releases(transactions):
    groups = {}

    for transaction in transactions:
        day_key = get_transaction_day_key(transaction)
        team_id = clean(transaction.get("team_id")) or "unknown_team"

        group_key = f"{day_key}_{team_id}_roster_moves"

        if group_key not in groups:
            groups[group_key] = {
                "draft_id": group_key,
                "day_key": day_key,
                "created_at_utc": clean(transaction.get("created_at_utc")) or utc_now_iso(),

                "team_id": clean(transaction.get("team_id")),
                "team_abbreviation": clean(transaction.get("team_abbreviation")),
                "team_display_name": clean(transaction.get("team_display_name")),
                "division": clean(transaction.get("division")),
                "region": clean(transaction.get("region")),
                "conference": clean(transaction.get("conference")),

                "transactions": [],
            }

        groups[group_key]["transactions"].append(transaction)

        if clean(transaction.get("created_at_utc")) > clean(groups[group_key].get("created_at_utc")):
            groups[group_key]["created_at_utc"] = clean(transaction.get("created_at_utc"))

    return list(groups.values())


def make_grouped_press_release_headline(group):
    team_name = clean(group.get("team_display_name")) or "Unknown Team"
    transactions = group.get("transactions", [])

    adds = [
        transaction for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removes = [
        transaction for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    if len(transactions) == 1:
        transaction = transactions[0]
        player_name = clean(transaction.get("player_display_name")) or "Unknown Player"
        transaction_type = clean(transaction.get("type")).lower()

        if transaction_type == "add":
            return f"{team_name} Add {player_name}"

        if transaction_type == "remove":
            return f"{team_name} Remove {player_name}"

    if adds and removes:
        return f"{team_name} Make Roster Moves"

    if adds:
        return f"{team_name} Add {len(adds)} Player{'s' if len(adds) != 1 else ''}"

    if removes:
        return f"{team_name} Remove {len(removes)} Player{'s' if len(removes) != 1 else ''}"

    return f"{team_name} Update Roster"


def make_grouped_press_release_subheadline(group):
    short_team_name = get_short_team_name(group)
    transactions = group.get("transactions", [])

    added_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removed_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    added_text = join_names(added_players)
    removed_text = join_names(removed_players)

    if added_text and removed_text:
        return f"The {short_team_name} have added {added_text} and removed {removed_text} from their active roster."

    if added_text:
        return f"The {short_team_name} have added {added_text} to their active roster."

    if removed_text:
        return f"The {short_team_name} have removed {removed_text} from their active roster."

    return f"The {short_team_name} have updated their active roster."


def make_grouped_press_release_body(group):
    team_name = clean(group.get("team_display_name")) or "Unknown Team"
    short_team_name = get_short_team_name(group)
    transactions = group.get("transactions", [])

    added_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "add"
    ]

    removed_players = [
        format_transaction_player_name(transaction)
        for transaction in transactions
        if clean(transaction.get("type")).lower() == "remove"
    ]

    paragraphs = []

    if added_players and removed_players:
        paragraphs.append(
            f"The {team_name} have added {join_names(added_players)} and removed "
            f"{join_names(removed_players)} from their active roster."
        )
    elif added_players:
        paragraphs.append(
            f"The {team_name} have added {join_names(added_players)} to their active roster. "
            f"The move gives the {short_team_name} another gear in their rotation as they continue to shape their name for the {SEASON_NAME} season."
        )
    elif removed_players:
        paragraphs.append(
            f"The {team_name} have removed {join_names(removed_players)} from their active roster."
        )
    else:
        paragraphs.append(
            f"The {team_name} have updated their active roster during the {SEASON_NAME} regular season."
        )

    if added_players:
        paragraphs.append(
            f"The move gives the {short_team_name} another option as they continue to shape their roster "
            f"for the road ahead."
        )

    if removed_players:
        paragraphs.append(
            f"The departing player{'s' if len(removed_players) != 1 else ''} will no longer be listed "
            f"on the club's active roster."
        )

    paragraphs.append("Further details may be added by SPL staff.")

    return "\n\n".join(paragraphs)


def make_grouped_press_release_draft(group):
    draft_id = clean(group.get("draft_id"))
    created_at_utc = clean(group.get("created_at_utc")) or utc_now_iso()

    headline = make_grouped_press_release_headline(group)
    transactions = group.get("transactions", [])

    transaction_ids = [
        clean(transaction.get("transaction_id"))
        for transaction in transactions
        if clean(transaction.get("transaction_id"))
    ]

    players = []

    for transaction in transactions:
        players.append({
            "type": clean(transaction.get("type")),
            "player_id": clean(transaction.get("player_id")),
            "player_display_name": clean(transaction.get("player_display_name")),
            "slap_id": clean(transaction.get("slap_id")),
            "jersey_number": clean(transaction.get("jersey_number")),
        })

    tags = [
        "transactions",
        "roster",
        clean(group.get("team_id")),
        clean(group.get("division")),
    ]

    tags = [tag for tag in tags if tag]

    return {
        "draft_id": draft_id,
        "transaction_ids": transaction_ids,
        "transaction_id": transaction_ids[0] if len(transaction_ids) == 1 else "",

        "status": "draft",
        "created_at_utc": created_at_utc,
        "updated_at_utc": created_at_utc,

        "headline": headline,
        "subheadline": make_grouped_press_release_subheadline(group),
        "slug": make_slug(headline),

        "team_id": clean(group.get("team_id")),
        "team_abbreviation": clean(group.get("team_abbreviation")),
        "team_display_name": clean(group.get("team_display_name")),
        "division": clean(group.get("division")),
        "region": clean(group.get("region")),
        "conference": clean(group.get("conference")),

        "players": players,

        "article_type": "transaction",
        "tags": tags,

        "body_markdown": make_grouped_press_release_body(group),

        "writer_notes": "",
        "created_by": "press_release_backfill",
        "last_edited_by": "",
    }


def backfill_press_release_drafts():
    transactions_data = load_json(TRANSACTIONS_FILE, {
        "season_id": SEASON_ID,
        "transactions": []
    })

    drafts_data = load_json(PRESS_RELEASE_DRAFTS_FILE, {
        "season_id": SEASON_ID,
        "drafts": []
    })

    transactions = transactions_data.get("transactions", [])
    drafts = drafts_data.setdefault("drafts", [])

    existing_draft_ids = {
        clean(draft.get("draft_id"))
        for draft in drafts
    }

    groups = group_transactions_for_press_releases(transactions)

    added = []

    for group in groups:
        draft = make_grouped_press_release_draft(group)
        draft_id = clean(draft.get("draft_id"))

        if not draft_id:
            continue

        if draft_id in existing_draft_ids:
            continue

        drafts.append(draft)
        existing_draft_ids.add(draft_id)
        added.append(draft)

    drafts_data["season_id"] = drafts_data.get("season_id") or SEASON_ID
    drafts_data["updated_at_utc"] = utc_now_iso()
    drafts_data["drafts"] = sorted(
        drafts,
        key=lambda row: clean(row.get("created_at_utc")),
        reverse=True,
    )

    write_json(PRESS_RELEASE_DRAFTS_FILE, drafts_data)

    return added, groups


def main():
    added, groups = backfill_press_release_drafts()

    print("Press release draft backfill complete.")
    print(f"Transaction groups found: {len(groups)}")
    print(f"New drafts created: {len(added)}")
    print(f"Wrote: {PRESS_RELEASE_DRAFTS_FILE.relative_to(BASE_DIR)}")

    if added:
        print()
        print("Created drafts:")
        for draft in added:
            print(f"- {draft['headline']} ({draft['draft_id']})")


if __name__ == "__main__":
    main()