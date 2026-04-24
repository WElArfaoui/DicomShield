from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydicom.tag import Tag


@dataclass
class Profile:
    """Represent a YAML profile already loaded and validated."""

    raw: dict[str, Any]

    @property
    def tag_actions(self) -> dict[str, dict[str, Any]]:
        return self.raw.get("tag_actions", {})

    @property
    def remove_private_tags(self) -> bool:
        return bool(self.raw.get("policies", {}).get("remove_private_tags", True))

    @property
    def recurse_sequences(self) -> bool:
        return bool(self.raw.get("policies", {}).get("recurse_sequences", True))

    @property
    def remap_uids(self) -> bool:
        return bool(self.raw.get("uids", {}).get("remap", True))

    @property
    def reject_burned_in_yes(self) -> bool:
        return bool(self.raw.get("policies", {}).get("reject_burned_in_yes", False))

def load_profile(profile_path: Path) -> Profile:
    """Load a YAML profile and validate its structure."""
    with profile_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("The YAML profile must be a dictionary/object at the root.")

    tag_actions = raw.get("tag_actions", {})
    if not isinstance(tag_actions, dict):
        raise ValueError("'tag_actions' must be a dictionary of tags -> rule.")
    
    for tag_str, rule in tag_actions.items():
        _parse_tag(tag_str)
        if not isinstance(rule, dict):
            raise ValueError(f"The rule for {tag_str} must be a dictionary.")
        if "action" not in rule:
            raise ValueError(f"The rule for {tag_str} must have an 'action' field.")

    return Profile(raw=raw)

def _parse_tag(tag_str: str) -> Tag:
    """Parse a tag string into a Tag object."""
    if not (tag_str.startswith("(") and tag_str.endswith(")") and "," in tag_str):
        raise ValueError(f"Invalid tag format: {tag_str}")
    group_hex, elem_hex = tag_str[1:-1].split(",", 1)
    return Tag(int(group_hex, 16), int(elem_hex, 16))

def parse_tag(tag_str: str) -> Tag:
    """Public API for parsing tags from YAML."""
    return _parse_tag(tag_str)