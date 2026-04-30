"""
Post-processing patch for already-anonymised DICOM batches.

Applies three targeted fixes to files that went through DicomShield but were
produced before the profile covered every leak vector:

  1. PatientID prefix replacement (e.g. IAT → ITA) — top-level and inside any
     nested sequence item, so OtherPatientIDsSequence items are also corrected.

  2. OtherPatientIDsSequence (0010,1002) removal — the scanner embeds the
     original research ID here; without this fix it leaks even in files whose
     top-level PatientID was already pseudonymised (PX_* entries).

  3. RequestedProcedureID (0040,1001) removal — UUID-format hospital order
     identifiers found inside RequestAttributesSequence that are not needed for
     research analysis.

The profile has been updated to prevent these issues in future `deid` runs.
This command is only needed to repair batches already on disk.
"""

from __future__ import annotations

from pathlib import Path

import pydicom
from pydicom.dataset import Dataset


def _fix_dataset(ds: Dataset, old_prefix: str, new_prefix: str) -> bool:
    """Recursively apply all patch operations. Returns True if anything changed."""
    changed = False

    pid = str(ds.get("PatientID", ""))
    if pid.startswith(old_prefix):
        ds.PatientID = new_prefix + pid[len(old_prefix):]
        changed = True

    if (0x0010, 0x1002) in ds:
        del ds[0x0010, 0x1002]
        changed = True

    if (0x0040, 0x1001) in ds:
        del ds[0x0040, 0x1001]
        changed = True

    for elem in ds:
        if elem.VR == "SQ" and elem.value:
            for item in elem.value:
                if _fix_dataset(item, old_prefix, new_prefix):
                    changed = True

    return changed


def patch_file(path: Path, old_prefix: str, new_prefix: str, dry_run: bool) -> bool:
    """Patch a single file in-place. Returns True if the file was (or would be) modified."""
    ds = pydicom.dcmread(str(path))
    changed = _fix_dataset(ds, old_prefix, new_prefix)
    if changed and not dry_run:
        ds.save_as(str(path))
    return changed


def patch_directory(
    root: Path,
    old_prefix: str = "IAT",
    new_prefix: str = "ITA",
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Patch all DICOM files under *root*.

    Returns (modified, unchanged, errors).
    """
    files = list(root.rglob("*.dcm"))
    modified = unchanged = errors = 0

    for i, path in enumerate(files, 1):
        if i % 2000 == 0:
            print(f"  {i}/{len(files)} procesados...", flush=True)
        try:
            if patch_file(path, old_prefix, new_prefix, dry_run):
                modified += 1
            else:
                unchanged += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {path}: {exc}")
            errors += 1

    return modified, unchanged, errors
