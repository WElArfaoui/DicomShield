# DicomShield

YAML-configurable DICOM pseudo-anonymisation tool.

## Objective

- Pseudo-anonymise sensitive tags using deterministic HMAC-SHA256 mapping.
- Allow users to configure which tags to anonymise, replace, or remove via a YAML profile.
- Ensure reproducible processing in research pipelines.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick start

```bash
export DICOMSHIELD_SECRET="change-this-to-a-strong-secret"
export DICOMSHIELD_IELCAP_MAP_CSV="/absolute/path/to/mapping.csv"

dicomshield deid \
  --input-dir ./dicom_in \
  --output-dir ./dicom_out \
  --profile ./profiles/ct_lung_research.yaml \
  --audit-file ./audit.jsonl
```

### Interactive mode

If you run without options, DicomShield prompts for the required paths and secrets:

```bash
dicomshield deid
```

## Security notes

- **`DICOMSHIELD_SECRET`** must be a strong random string. All pseudonyms (PatientID, UIDs) are derived from this key via HMAC-SHA256. Losing the key means pseudonyms cannot be reproduced; sharing it breaks pseudonymisation.
- **`audit.jsonl` contains PHI.** The audit log records original tag values alongside the anonymised replacements for traceability. Treat this file as sensitive data — do not commit it, share it, or store it alongside the output DICOM files. It is excluded from git by the default `.gitignore`.

## YAML Profile

See `profiles/ct_lung_research.yaml` for a complete annotated example.

### Supported actions per tag

| Action | Description |
|---|---|
| `remove` | Delete the tag entirely |
| `replace` | Set a fixed value |
| `pseudonymize` | HMAC-SHA256 deterministic pseudonym with configurable prefix |
| `clean_text` | Replace with `REDACTED` |
| `keep_year` | Truncate date to `YYYY0101` |
| `map_csv` | Replace using a CSV lookup table |

### CSV mapping for AccessionNumber

The sample profile supports replacing `AccessionNumber` via a CSV lookup:

- `csv_path`: path to CSV (supports `${ENV_VAR}` expansion)
- `key_column`: column whose value matches the DICOM tag (e.g. `nhc`)
- `value_column`: column to use as replacement (e.g. `id_ielcap`)
- `fallback`: `keep` (default) or `remove` when no match is found

## License

Apache License 2.0 — see [LICENSE](LICENSE).
