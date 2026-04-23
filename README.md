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
dicomshield deid \
 -input-dir ./dicom_in \
 -output-dir ./dicom_out \
 -profile ./profiles/ct_lung_research.yaml \
 -audit-file ./audit.jsonl
```

## YAML Profile

See `profiles/ct_lung_research.yaml`for a complete example with comments.
