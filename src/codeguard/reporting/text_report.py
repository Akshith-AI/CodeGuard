"""Export findings with explicit scan coverage and failures."""

from pathlib import Path

from codeguard.models import Finding


def write_report(
    path: Path,
    repository: str,
    commit: str,
    provider: str,
    model: str,
    findings: list[Finding],
    scanned: int,
    skipped: list[str],
    failures: list[str],
) -> None:
    status = "INCOMPLETE" if failures or skipped else "COMPLETE"
    lines = [
        "CodeGuard Security Report",
        f"Repository: {repository}",
        f"Commit: {commit}",
        f"Provider: {provider}",
        f"Model: {model}",
        f"Status: {status}",
        f"Files analyzed: {scanned}",
        f"Findings: {len(findings)}",
        "",
        "AI findings are potential issues and require human review.",
        "",
    ]
    for finding in findings:
        lines.extend(
            [
                f"[{finding.severity}] {finding.file_path}:{finding.affected_line}",
                f"Type: {finding.vulnerability_type}",
                f"Description: {finding.description}",
                f"Suggested fix: {finding.suggested_fix}",
                "",
            ]
        )
    if not findings:
        lines.append("No findings were returned for successfully analyzed files.")
    if skipped:
        lines.extend(["", "Skipped files:", *skipped])
    if failures:
        lines.extend(["", "Failed analyses:", *failures])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
