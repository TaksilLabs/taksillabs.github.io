import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
TEAM_METADATA_FILE = BASE_DIR / "data" / "team_metadata.json"


def clean_team_name(name):
    text = str(name or "").strip()

    # Remove trailing LeagueRepublic code tags like:
    # "Maui Monkeys (DCUW)"
    # "Example Team (ABC)"
    text = re.sub(r"\s*\([A-Z0-9]{2,8}\)\s*$", "", text)

    return text.strip()


def normalize_team_name(name):
    return clean_team_name(name).lower()


def make_team_id(name):
    text = clean_team_name(name).lower()

    text = re.sub(r"\s+-\s+(east|central|west)$", "", text)
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_") or "unknown_team"


def load_team_identities():
    if not TEAM_METADATA_FILE.exists():
        return {}, {}

    with TEAM_METADATA_FILE.open("r", encoding="utf-8") as f:
        entries = json.load(f)

    alias_lookup = {}
    id_lookup = {}

    for entry in entries:
        team_id = entry.get("team_id")
        display_name = entry.get("team_display_name")

        if not team_id or not display_name:
            continue

        clean_entry = {
            "team_id": team_id,
            "team_display_name": display_name,
            "aliases": entry.get("aliases", []),
            "logo": entry.get("logo", ""),
            "theme": entry.get("theme", {}),
            "name_history": entry.get("name_history", [])
        }

        id_lookup[team_id] = clean_entry

        alias_lookup[normalize_team_name(display_name)] = clean_entry

        for alias in clean_entry["aliases"]:
            alias_lookup[normalize_team_name(alias)] = clean_entry

    return alias_lookup, id_lookup


def resolve_team_identity(raw_team_name, alias_lookup=None):
    if alias_lookup is None:
        alias_lookup, _ = load_team_identities()

    cleaned_name = clean_team_name(raw_team_name)
    key = normalize_team_name(cleaned_name)

    if key in alias_lookup:
        return alias_lookup[key]

    fallback_id = make_team_id(cleaned_name)

    return {
        "team_id": fallback_id,
        "team_display_name": cleaned_name,
        "aliases": [cleaned_name],
        "logo": "",
        "theme": {},
        "name_history": []
    }