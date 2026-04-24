from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian

from .audit import AuditRecord
from .config import Profile, parse_tag
from .pseudonym import pseudonymize, remap_uid

UID_KEYS = ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID")
_CSV_MAP_CACHE: dict[tuple[str, str, str], dict[str, str]] = {}

def deidentify_file(input_path: Path, output_path: Path, profile: Profile) -> AuditRecord:
    """
    Process a single DICOM file.

    Flow:
    1) Read dataset.
    2) Apply rules by tag.
    3) Apply global policies (private tags, UID remap, recursion).
    4) Save result and return audit.
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
        _ensure_file_meta(ds)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.save_as(str(output_path), write_like_original=False)
        return audit
    except Exception as exc:  # noqa: BLE001
        audit.status = "error"
        audit.error = str(exc)
        return audit

def _apply_rules(ds: Dataset, profile: Profile, changes: list[dict[str, Any]]) -> None:
    """
    Apply rules configured in YAML to the current dataset.
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
        elif action == "keep_year":
            new_value = _keep_year_only(old_value)
            ds[tag].value = new_value
            changes.append(
                {"tag": tag_str, "action": "keep_year", "old": old_value, "new": new_value}
            )
        elif action == "map_csv":
            csv_path = os.path.expandvars(os.path.expanduser(
                str(rule.get("csv_path", "")).strip().strip("'\"")
            )).strip()
            key_column = str(rule.get("key_column", "")).strip()
            value_column = str(rule.get("value_column", "")).strip()
            fallback = str(rule.get("fallback", "keep")).strip().lower()

            # Path is empty or env var was not set (still contains $)
            csv_missing = not csv_path or "$" in csv_path or not Path(csv_path).is_file()
            if csv_missing:
                if fallback == "remove":
                    del ds[tag]
                    changes.append({"tag": tag_str, "action": "map_csv", "status": "no_csv_removed"})
                else:
                    changes.append({"tag": tag_str, "action": "map_csv", "status": "no_csv_kept"})
                continue

            mapping = _get_csv_mapping(csv_path, key_column, value_column)
            new_value = mapping.get(old_value.strip())

            if not new_value:
                if fallback == "remove":
                    del ds[tag]
                    changes.append(
                        {
                            "tag": tag_str,
                            "action": "map_csv",
                            "old": old_value,
                            "new": "",
                            "status": "removed_missing_mapping",
                        }
                    )
                else:
                    changes.append(
                        {
                            "tag": tag_str,
                            "action": "map_csv",
                            "old": old_value,
                            "new": old_value,
                            "status": "mapping_not_found",
                        }
                    )
            else:
                ds[tag].value = str(new_value)
                changes.append(
                    {"tag": tag_str, "action": "map_csv", "old": old_value, "new": str(new_value)}
                )
        else:
            raise ValueError(f"Unsupported action: {action} for tag {tag_str}")

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


def _keep_year_only(value: str) -> str:
    value = (value or "").strip()
    year = value[:4]
    if len(year) == 4 and year.isdigit():
        # Keep only year precision while preserving valid DICOM DA format.
        return f"{year}0101"
    return "19000101"


def _get_csv_mapping(csv_path: str, key_column: str, value_column: str) -> dict[str, str]:
    resolved_path = str(Path(csv_path).resolve())
    cache_key = (resolved_path, key_column, value_column)
    if cache_key in _CSV_MAP_CACHE:
        return _CSV_MAP_CACHE[cache_key]

    mapping: dict[str, str] = {}
    with Path(resolved_path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV without header: {resolved_path}")
        if key_column not in reader.fieldnames or value_column not in reader.fieldnames:
            raise ValueError(
                f"CSV columns not found in {resolved_path}. Needed: {key_column}, {value_column}"
            )
        for row in reader:
            key = (row.get(key_column) or "").strip()
            value = (row.get(value_column) or "").strip()
            if key and value and key not in mapping:
                mapping[key] = value

    _CSV_MAP_CACHE[cache_key] = mapping
    return mapping
    
def _apply_rules_in_sequences(ds: Dataset, profile: Profile, changes: list[dict[str, Any]]) -> None:
    """
    Traverse sequences (SQ) and apply the same rule engine.
    """
    for element in ds:
        if element.VR != "SQ" or not element.value:
            continue
        for item in element.value:
            _apply_rules(item, profile, changes)


def _ensure_file_meta(ds: Dataset) -> None:
    """
    Guarantee the minimum File Meta Information required by pydicom when
    writing with write_like_original=False.  Some scanners produce files
    without a complete meta header; we reconstruct it from the dataset tags.
    """
    if not hasattr(ds, "file_meta") or ds.file_meta is None:
        ds.file_meta = FileMetaDataset()

    meta = ds.file_meta
    if not getattr(meta, "MediaStorageSOPClassUID", None):
        meta.MediaStorageSOPClassUID = ds.get("SOPClassUID", "1.2.840.10008.5.1.4.1.1.2")
    if not getattr(meta, "MediaStorageSOPInstanceUID", None):
        sop = str(ds.get("SOPInstanceUID", "")).strip()
        meta.MediaStorageSOPInstanceUID = sop if sop else pydicom.uid.generate_uid()
    if not getattr(meta, "TransferSyntaxUID", None):
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
