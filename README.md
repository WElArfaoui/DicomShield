# Dicomshield 

YAML-configurable DICOM pseudononymisation tool.

## Objetive

- Pseudo-anonymise sensitive tags using deterministic mapping.
- Allow users to select which variables to anonymise, replace or remove.
- Ensure reproductible processing in research pipelines.

## Installation

```bash
pip install -e .
```

## Quick start

```bash
export DICOMSHIELD_SECRET="change-this-key"
export DICOMSHIELD_IELCAP_MAP_CSV="/absolute/path/to/ielcap_mapping.csv"
dicomshield deid \
 -input-dir ./dicom_in \
 -output-dir ./dicom_out \
 -profile ./profiles/ct_lung_research.yaml \
 -audit-file ./audit.jsonl
```

### Interactive mode (asks for missing fields)

If you run without options, DicomShield asks for the required paths and secrets:

```bash
dicomshield deid
```

## YAML Profile

See `profiles/ct_lung_research.yaml` for a complete example with comments.

### CSV mapping for AccessionNumber

The sample profile supports replacing DICOM `AccessionNumber` using a CSV lookup:

- `csv_path`: path to CSV (supports `${ENV_VAR}`)
- `key_column`: source value from DICOM (e.g. `nhc`)
- `value_column`: replacement value (e.g. `id_ielcap`)
- `fallback`: `keep` (default) or `remove` when there is no match
