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
export DICOMSHIELD_MAP_CSV="/absolute/path/to/mapping.csv"

dicomshield deid \
  --input-dir ./dicom_in \
  --output-dir ./dicom_out \
  --profile ./profiles/ct_lung_research.yaml \
  --map-value-column id_ielcap \
  --audit-file ./audit.jsonl
```

### Interactive mode

If you run without options, DicomShield prompts for the required paths and secrets:

```bash
dicomshield deid
```

## Commands

| Command | Description |
|---|---|
| `deid` | Pseudo-anonymise all DICOM files in a directory |
| `validate` | Validate a YAML profile and show its configured rules |
| `audit` | Browse and filter the audit log |
| `report` | Show a processing summary from the audit log |

```bash
dicomshield validate --profile ./profiles/ct_lung_research.yaml

dicomshield report --audit-file ./audit.jsonl

dicomshield audit --audit-file ./audit.jsonl --errors
dicomshield audit --audit-file ./audit.jsonl --status quarantine --tail 20
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

### CSV mapping (`map_csv`)

Any tag can be replaced using a CSV lookup table. The sample profile uses it
to map the hospital record number (NHC) to a research ID for both `PatientID`
and `AccessionNumber`.

| Field | Description |
|---|---|
| `csv_path` | Path to the CSV file. Supports `${ENV_VAR}` expansion. |
| `key_column` | Column whose value is matched against the DICOM tag (e.g. `nhc`). |
| `value_column` | Column used as the replacement value (e.g. `id_ielcap`). Si no se define (o queda vacío) y no se pasa `--map-value-column` en la CLI, el tag se elimina por defecto. |
| `fallback` | What to do when no match is found: `keep` (default), `remove`, or `pseudonymize`. |
| `prefix` | Prefix for the pseudonym when `fallback: pseudonymize` is used (e.g. `PID_`). |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
