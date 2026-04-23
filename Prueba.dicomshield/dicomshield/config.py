from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydicom.tag import Tag


@dataclass
class Profile:
    """Representa un perfil YAML ya cargado y validado."""

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
    """
    Carga el YAML y realiza una validación mínima de estructura.
    """
    with profile_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if not isinstance(raw, dict):
        raise ValueError("El perfil YAML debe ser un objeto/dict en la raíz.")

    tag_actions = raw.get("tag_actions", {})
    if not isinstance(tag_actions, dict):
        raise ValueError("'tag_actions' debe ser un diccionario de tags -> regla.")

    for tag_str, rule in tag_actions.items():
        _parse_tag(tag_str)
        if not isinstance(rule, dict):
            raise ValueError(f"La regla para {tag_str} debe ser un objeto.")
        if "action" not in rule:
            raise ValueError(f"La regla para {tag_str} requiere campo 'action'.")

    return Profile(raw=raw)


def _parse_tag(tag_str: str) -> Tag:
    """
    Convierte '(0010,0020)' en un Tag de pydicom.
    """
    if not (tag_str.startswith("(") and tag_str.endswith(")") and "," in tag_str):
        raise ValueError(f"Formato de tag inválido: {tag_str}")
    group_hex, elem_hex = tag_str[1:-1].split(",", 1)
    return Tag(int(group_hex, 16), int(elem_hex, 16))


def parse_tag(tag_str: str) -> Tag:
    """API pública para parseo de tags desde YAML."""
    return _parse_tag(tag_str)
