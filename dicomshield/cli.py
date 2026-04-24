from __future__ import annotations

import os
from pathlib import Path

import typer

from .audit import append_audit_line
from .config import load_profile
from .deid import deidentify_file

app = typer.Typer(help="DicomShield:Configurable DICOM pseudo-anonymiser")

@app.command("deid")
def deid_command(
    input_dir: Path | None = typer.Option(None, file_okay=False, dir_okay=True),
    output_dir: Path | None = typer.Option(None, file_okay=False, dir_okay=True),
    profile: Path | None = typer.Option(None, file_okay=True, dir_okay=False),
    audit_file: Path = typer.Option(Path("audit.jsonl"), file_okay=True, dir_okay=False),
) -> None:
    """
    Process all files in the input directory.

    Preserves the same relative folder structure in the output directory.
    """
    input_dir = _ask_input_dir(input_dir)
    output_dir = _ask_output_dir(output_dir)
    profile = _ask_profile(profile)
    _ask_required_secrets()

    prof = load_profile(profile)

    processed = 0
    errors = 0
    quarantined = 0
    for source_path in input_dir.rglob("*"):
        if not source_path.is_file():
            continue

        # Preserve the relative folder structure for easier traceability.
        rel = source_path.relative_to(input_dir)
        target = output_dir / rel

        record = deidentify_file(source_path, target, prof)
        append_audit_line(audit_file, record)

        if record.status == "ok":
            processed += 1
        elif record.status == "quarantine":
            quarantined += 1
        else:
            errors += 1
    typer.echo(
        f"Done. OK: {processed} | Quarantine: {quarantined} | Errors: {errors} | Audit: {audit_file}"
    )


def _ask_input_dir(input_dir: Path | None) -> Path:
    if input_dir is None:
        value = typer.prompt("Ruta de carpeta de entrada DICOM", default="./dicom_in")
        input_dir = Path(value)
    if not input_dir.exists() or not input_dir.is_dir():
        raise typer.BadParameter(f"Input directory no existe o no es carpeta: {input_dir}")
    return input_dir


def _ask_output_dir(output_dir: Path | None) -> Path:
    if output_dir is None:
        value = typer.prompt("Ruta de carpeta de salida DICOM", default="./dicom_out")
        output_dir = Path(value)
    return output_dir


def _ask_profile(profile: Path | None) -> Path:
    if profile is None:
        value = typer.prompt(
            "Ruta del perfil YAML",
            default="./profiles/ct_lung_research.yaml",
        )
        profile = Path(value)
    if not profile.exists() or not profile.is_file():
        raise typer.BadParameter(f"Perfil no existe o no es archivo: {profile}")
    return profile


def _ask_required_secrets() -> None:
    if not os.environ.get("DICOMSHIELD_SECRET"):
        os.environ["DICOMSHIELD_SECRET"] = typer.prompt(
            "DICOMSHIELD_SECRET (clave para pseudonimizacion)",
            hide_input=True,
            confirmation_prompt=True,
        )
    if not os.environ.get("DICOMSHIELD_IELCAP_MAP_CSV"):
        csv_path = typer.prompt(
            "Ruta CSV para mapear AccessionNumber (nhc -> id_ielcap)",
            default="",
            show_default=False,
        ).strip()
        if csv_path:
            os.environ["DICOMSHIELD_IELCAP_MAP_CSV"] = csv_path

if __name__ == "__main__":
    app()