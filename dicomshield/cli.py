from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import typer

from .audit import append_audit_line
from .config import load_profile
from .deid import deidentify_file

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """DicomShield: YAML-configurable DICOM pseudo-anonymiser."""


# ---------------------------------------------------------------------------
# deid
# ---------------------------------------------------------------------------

@app.command("deid")
def deid_command(
    input_dir: Path | None = typer.Option(None, file_okay=False, dir_okay=True),
    output_dir: Path | None = typer.Option(None, file_okay=False, dir_okay=True),
    profile: Path | None = typer.Option(None, file_okay=True, dir_okay=False),
    audit_file: Path = typer.Option(Path("audit.jsonl"), file_okay=True, dir_okay=False),
) -> None:
    """Pseudo-anonymise all DICOM files in a directory."""
    input_dir = _ask_input_dir(input_dir)
    output_dir = _ask_output_dir(output_dir)
    profile = _ask_profile(profile)
    _ask_required_secrets()

    prof = load_profile(profile)

    processed = errors = quarantined = 0
    for source_path in input_dir.rglob("*"):
        if not source_path.is_file():
            continue

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


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command("validate")
def validate_command(
    profile: Path = typer.Option(
        Path("./profiles/ct_lung_research.yaml"), file_okay=True, dir_okay=False
    ),
) -> None:
    """Validate a YAML profile and show its configured rules."""
    if not profile.exists():
        typer.echo(f"Profile not found: {profile}", err=True)
        raise typer.Exit(1)

    prof = load_profile(profile)  # raises on any structural error

    typer.echo(f"\nProfile : {profile}")
    typer.echo("-" * 50)
    typer.echo(f"  remove_private_tags : {prof.remove_private_tags}")
    typer.echo(f"  recurse_sequences   : {prof.recurse_sequences}")
    typer.echo(f"  remap_uids          : {prof.remap_uids}")
    typer.echo(f"  reject_burned_in    : {prof.reject_burned_in_yes}")
    typer.echo(f"\n  Tag rules ({len(prof.tag_actions)} configured):")
    for tag, rule in prof.tag_actions.items():
        action = rule.get("action", "?")
        extra = ""
        if action == "replace":
            extra = f"  value={rule.get('value', '')!r}"
        elif action == "pseudonymize":
            extra = f"  prefix={rule.get('prefix', 'PX_')!r}"
        elif action == "map_csv":
            extra = f"  csv={rule.get('csv_path', '')}  fallback={rule.get('fallback', 'keep')}"
        typer.echo(f"    {tag}  ->  {action}{extra}")

    typer.echo("\nOK: profile is valid.\n")


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

@app.command("audit")
def audit_command(
    audit_file: Path = typer.Option(Path("audit.jsonl"), file_okay=True, dir_okay=False),
    status: str | None = typer.Option(None, help="Filter by status: ok, error, quarantine"),
    tail: int | None = typer.Option(None, help="Show only the last N entries"),
    errors_only: bool = typer.Option(False, "--errors", help="Shortcut for --status error"),
) -> None:
    """Browse and filter the audit log."""
    if not audit_file.exists():
        typer.echo(f"Audit file not found: {audit_file}", err=True)
        raise typer.Exit(1)

    records = []
    with audit_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if errors_only:
        status = "error"
    if status:
        records = [r for r in records if r.get("status") == status]
    if tail:
        records = records[-tail:]

    for r in records:
        st = r.get("status", "?").upper()
        ts = r.get("ts_utc", "")[:19].replace("T", " ")
        filename = Path(r.get("input_path", "")).name
        line = f"[{ts}]  {st:<10}  {filename}"
        if r.get("error"):
            line += f"\n             {r['error']}"
        typer.echo(line)

    typer.echo(f"\n{len(records)} entries shown.")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

@app.command("report")
def report_command(
    audit_file: Path = typer.Option(Path("audit.jsonl"), file_okay=True, dir_okay=False),
) -> None:
    """Show a processing summary from the audit log."""
    if not audit_file.exists():
        typer.echo(f"Audit file not found: {audit_file}", err=True)
        raise typer.Exit(1)

    counts: Counter[str] = Counter()
    error_msgs: Counter[str] = Counter()
    actions_applied: Counter[str] = Counter()
    patients: set[str] = set()

    with audit_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            counts[r.get("status", "unknown")] += 1

            if r.get("error"):
                # Keep only the first sentence so similar errors group together.
                short = r["error"].split(":")[0].strip()
                error_msgs[short] += 1

            for change in r.get("changes", []):
                actions_applied[change.get("action", "?")] += 1
                if change.get("action") == "pseudonymize" and change.get("new"):
                    patients.add(change["new"])

    total = sum(counts.values())
    typer.echo(f"\n{'='*50}")
    typer.echo(f"  DicomShield — Processing Report")
    typer.echo(f"{'='*50}")
    typer.echo(f"  Audit file : {audit_file}")
    typer.echo(f"  Total files: {total}")
    typer.echo(f"{'─'*50}")
    typer.echo(f"  OK         : {counts['ok']}")
    typer.echo(f"  Quarantine : {counts['quarantine']}")
    typer.echo(f"  Errors     : {counts['error']}")
    typer.echo(f"{'─'*50}")
    typer.echo(f"  Unique pseudonymised patients: {len(patients)}")
    typer.echo(f"\n  Actions applied:")
    for action, n in actions_applied.most_common():
        typer.echo(f"    {action:<22} {n:>6}")
    if error_msgs:
        typer.echo(f"\n  Top error types:")
        for msg, n in error_msgs.most_common(5):
            typer.echo(f"    {n:>4}x  {msg}")
    typer.echo(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

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
        ).strip().strip("'\"")
        if csv_path:
            os.environ["DICOMSHIELD_IELCAP_MAP_CSV"] = csv_path


if __name__ == "__main__":
    app()
