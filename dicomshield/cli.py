from __future__ import annotations

from pathlib import Path

import typer

from .audit import append_audit_line
from .config import load_profile
from .deid import deidentify_file

app = typer.Typer(help="DicomShield:Configurable DICOM pseudo-anonymiser")

@app.command("deid")
def deid_command(
    input_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    output_dir: Path = typer.Option(..., file_okay=False, dir_okay=True),
    profile: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False),
    audit_file: Path = typer.Option(Path("audit.jsonl"), file_okay=True, dir_okay=False),
) -> None:
    """
    Process all files in the input directory.

    Preserves the same relative folder structure in the output directory.
    """
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
        f"Finalished. OK{processed} | Quarantine{quarantined} | Error{errors} | Audit{audit_file}"
    )

if __name__ == "__main__":
    app()