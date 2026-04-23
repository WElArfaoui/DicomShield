# DicomShield

Herramienta de pseudoanonimización DICOM configurable por YAML.

## Objetivo

- Pseudoanonimizar tags sensibles con mapeo determinístico.
- Permitir seleccionar qué variables anonimizar, reemplazar o eliminar.
- Mantener procesamiento reproducible en pipelines de investigación.

## Instalación

```bash
pip install -e .
```

## Uso rápido

```bash
export DICOMSHIELD_SECRET="cambia-esta-clave"
dicomshield deid \
  --input-dir ./dicom_in \
  --output-dir ./dicom_out \
  --profile ./profiles/ct_lung_research.yaml \
  --audit-file ./audit.jsonl
```

## Perfil YAML

Revisa `profiles/ct_lung_research.yaml` para un ejemplo completo con comentarios.
