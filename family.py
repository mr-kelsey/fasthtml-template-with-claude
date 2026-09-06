import json
from pathlib import Path

FAMILY_CONFIG_PATH = Path("family.json")

_PLACEHOLDER_FAMILY_MEMBERS = [
    {"id": "1", "name": "Person 1", "color": "#e63946"},
    {"id": "2", "name": "Person 2", "color": "#457b9d"},
    {"id": "3", "name": "Person 3", "color": "#2a9d8f"},
    {"id": "4", "name": "Person 4", "color": "#f4a261"},
]


def _load_family_members():
    if FAMILY_CONFIG_PATH.exists():
        return json.loads(FAMILY_CONFIG_PATH.read_text())
    return _PLACEHOLDER_FAMILY_MEMBERS


FAMILY_MEMBERS = _load_family_members()


def get_member(member_id):
    return next((member for member in FAMILY_MEMBERS if member["id"] == member_id), None)
