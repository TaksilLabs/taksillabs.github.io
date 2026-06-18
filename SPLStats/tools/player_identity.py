import json
import re
from pathlib import Path


ALIASES_FILE = Path("../data/player_aliases.json")


def normalize_name(name):
    return str(name or "").strip().lower()


def make_fallback_player_id(name):
    text = str(name or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\-\s]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "unknown_player"


def load_player_identities():
    if not ALIASES_FILE.exists():
        return {}, {}

    with ALIASES_FILE.open("r", encoding="utf-8") as f:
        entries = json.load(f)

    alias_lookup = {}
    id_lookup = {}

    for entry in entries:
        player_id = entry.get("player_id")
        display_name = entry.get("player_display_name")

        if not player_id or not display_name:
            continue

        clean_entry = {
            "player_id": player_id,
            "player_display_name": display_name,
            "aliases": entry.get("aliases", []),
            "slap_ids": entry.get("slap_ids", [])
        }

        id_lookup[player_id] = clean_entry

        for alias in clean_entry["aliases"]:
            alias_lookup[normalize_name(alias)] = clean_entry

        alias_lookup[normalize_name(display_name)] = clean_entry

    return alias_lookup, id_lookup


def resolve_player_identity(raw_name, alias_lookup=None):
    if alias_lookup is None:
        alias_lookup, _ = load_player_identities()

    key = normalize_name(raw_name)

    if key in alias_lookup:
        return alias_lookup[key]

    fallback_id = make_fallback_player_id(raw_name)

    return {
        "player_id": fallback_id,
        "player_display_name": str(raw_name or "").strip(),
        "aliases": [str(raw_name or "").strip()],
        "slap_ids": []
    }