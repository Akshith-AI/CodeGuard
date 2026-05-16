"""Validate model output before treating it as security findings."""

import json

from codeguard.models import Finding

SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


class AnalysisError(ValueError):
    """The provider did not produce a complete, valid analysis."""


def parse_findings(text: str, file_path: str, line_count: int) -> list[Finding]:
    if not isinstance(text, str) or not text.strip():
        raise AnalysisError("The model returned no analysis text.")
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = "\n".join(text.splitlines()[1:-1])
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnalysisError("The model returned invalid JSON.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise AnalysisError("Expected a JSON object with a findings array.")
    findings = []
    for item in payload["findings"]:
        if not isinstance(item, dict):
            raise AnalysisError("Each finding must be a JSON object.")
        for field in ("vulnerability_type", "description", "suggested_fix"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise AnalysisError(f"Finding has missing or invalid {field}.")
        severity = item.get("severity")
        if not isinstance(severity, str) or severity not in SEVERITIES:
            raise AnalysisError("Finding has an invalid severity.")
        line = item.get("affected_line")
        if type(line) is not int or not 1 <= line <= line_count:
            raise AnalysisError("Finding refers to an invalid source line.")
        findings.append(
            Finding(
                vulnerability_type=item["vulnerability_type"],
                severity=severity,
                file_path=file_path,
                affected_line=line,
                description=item["description"],
                suggested_fix=item["suggested_fix"],
            )
        )
    return findings
