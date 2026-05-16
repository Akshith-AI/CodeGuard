"""Color-coded terminal findings with literal untrusted text."""

from rich.console import Console

from codeguard.models import Finding

COLORS = {"CRITICAL": "bold red", "HIGH": "red", "MEDIUM": "yellow", "LOW": "cyan"}


def display_findings(console: Console, findings: list[Finding]) -> None:
    for finding in findings:
        console.print(
            f"[{finding.severity}] {finding.file_path}:{finding.affected_line} "
            f"— {finding.vulnerability_type}",
            style=COLORS[finding.severity],
            markup=False,
        )
        console.print(f"  {finding.description}", markup=False)
        console.print(f"  Suggested fix: {finding.suggested_fix}", markup=False)
