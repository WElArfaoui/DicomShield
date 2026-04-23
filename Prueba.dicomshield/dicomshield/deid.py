from __future__ import annotations

from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataset import Dataset

from .audit import AuditRecord
from .config import Profile, parse_tag
from .pseudonym import pseudonymize, remap_uid


UID_KEYS = ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID")


def deidentify_file(input_path: Path, output_path: Path, profile: Profile) -> AuditRecord:
    """
    Procesa un único archivo DICOM.

    Flujo:
    1) Lee dataset.
    2) Aplica reglas por tag.
    3) Aplica políticas globales (private tags, UID remap, recursión).
    4) Guarda resultado y devuelve auditoría.
    """
    audit = AuditRecord(
        input_path=str(input_path),
        output_path=str(output_path),
        status="ok",
    )

    try:
        ds = pydicom.dcmread(str(input_path), force=True)

        if profile.reject_burned_in_yes and str(ds.get("BurnedInAnnotation", "")).upper() == "YES":
            audit.status = "quarantine"
            audit.warnings.append("BurnedInAnnotation=YES")
            return audit

        _apply_rules(ds, profile, audit.changes)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(str(output_path), write_like_original=False)
        return audit
    except Exception as exc:  # noqa: BLE001
        audit.status = "error"
        audit.error = str(exc)
        return audit


def _apply_rules(ds: Dataset, profile: Profile, changes: list[dict[str, Any]]) -> None:
    """
    Aplica acciones configuradas en YAML sobre el dataset actual.
    """
    for tag_str, rule in profile.tag_actions.items():
        tag = parse_tag(tag_str)
        if tag not in ds:
            continue

        action = rule["action"]
        old_value = str(ds[tag].value)

        if action == "remove":
            del ds[tag]
            changes.append({"tag": tag_str, "action": "remove"})
        elif action == "replace":
            new_value = str(rule.get("value", ""))
            ds[tag].value = new_value
            changes.append(
                {"tag": tag_str, "action": "replace", "old": old_value, "new": new_value}
            )
        elif action == "pseudonymize":
            prefix = str(rule.get("prefix", "PX_"))
            new_value = pseudonymize(old_value, prefix=prefix)
            ds[tag].value = new_value
            changes.append(
                {
                    "tag": tag_str,
                    "action": "pseudonymize",
                    "old": old_value,
                    "new": new_value,
                }
            )
        elif action == "clean_text":
            ds[tag].value = "REDACTED"
            changes.append(
                {"tag": tag_str, "action": "clean_text", "old": old_value, "new": "REDACTED"}
            )
        else:
            raise ValueError(f"Acción no soportada: {action} en {tag_str}")

    if profile.remove_private_tags:
        ds.remove_private_tags()
        changes.append({"tag": "PRIVATE", "action": "remove_private_tags"})

    if profile.remap_uids:
        for key in UID_KEYS:
            if key in ds and ds[key].value:
                old_uid = str(ds[key].value)
                new_uid = remap_uid(old_uid)
                ds[key].value = new_uid
                changes.append({"tag": key, "action": "remap_uid", "old": old_uid, "new": new_uid})

    if profile.recurse_sequences:
        _apply_rules_in_sequences(ds, profile, changes)


def _apply_rules_in_sequences(ds: Dataset, profile: Profile, changes: list[dict[str, Any]]) -> None:
    """
    Recorre secuencias (SQ) y aplica exactamente el mismo motor de reglas.
    """
    for element in ds:
        if element.VR != "SQ" or not element.value:
            continue
        for item in element.value:
            _apply_rules(item, profile, changes)
