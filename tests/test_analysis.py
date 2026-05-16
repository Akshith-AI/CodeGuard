import json
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest

from codeguard.analysis.analyzer import Analyzer
from codeguard.analysis.parser import AnalysisError, parse_findings
from codeguard.config import ProviderConfig, get_config

VALID = json.dumps(
    {
        "findings": [
            {
                "vulnerability_type": "Command injection",
                "severity": "HIGH",
                "affected_line": 1,
                "description": "Untrusted input reaches a shell.",
                "suggested_fix": "Use an argument list with shell=False.",
            }
        ]
    }
)


@pytest.mark.parametrize("provider", ["openai", "claude", "kimi"])
def test_provider_requests_and_results(monkeypatch, provider):
    client = MagicMock()
    monkeypatch.setattr("codeguard.analysis.analyzer.OpenAI", lambda **kw: client)
    monkeypatch.setattr("codeguard.analysis.analyzer.Anthropic", lambda **kw: client)
    client.responses.create.return_value = NS(status="completed", output_text=VALID)
    client.messages.create.return_value = NS(
        stop_reason="end_turn", content=[NS(type="thinking"), NS(type="text", text=VALID)]
    )
    client.chat.completions.create.return_value = NS(
        choices=[NS(finish_reason="stop", message=NS(content=VALID))]
    )
    analyzer = Analyzer(
        ProviderConfig(
            provider,
            "custom-model",
            "test-key",
            "https://api.moonshot.ai/v1" if provider == "kimi" else None,
        )
    )
    findings = analyzer.analyze("test.py", "os.system(user_input)")
    assert findings[0].file_path == "test.py"
    assert findings[0].severity == "HIGH"
    if provider == "openai":
        kwargs = client.responses.create.call_args.kwargs
        assert kwargs["store"] is False
    elif provider == "claude":
        kwargs = client.messages.create.call_args.kwargs
        assert "system" in kwargs
    else:
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["model"] == "custom-model"
    analyzer.close()
    client.close.assert_called_once()


@pytest.mark.parametrize("provider", ["openai", "claude", "kimi"])
def test_truncated_response_is_not_a_clean_scan(monkeypatch, provider):
    client = MagicMock()
    monkeypatch.setattr("codeguard.analysis.analyzer.OpenAI", lambda **kw: client)
    monkeypatch.setattr("codeguard.analysis.analyzer.Anthropic", lambda **kw: client)
    client.responses.create.return_value = NS(status="incomplete", output_text='{"findings":[]}')
    client.messages.create.return_value = NS(stop_reason="max_tokens", content=[])
    client.chat.completions.create.return_value = NS(choices=[NS(finish_reason="length")])
    with pytest.raises(AnalysisError):
        Analyzer(ProviderConfig(provider, "model", "key")).analyze("a.py", "pass")


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "{}",
        '{"findings":null}',
        '{"findings":[1]}',
        VALID.replace('"HIGH"', '"UNKNOWN"'),
        VALID.replace('"affected_line": 1', '"affected_line": true'),
        VALID.replace('"affected_line": 1', '"affected_line": 2'),
    ],
)
def test_invalid_output_rejected(payload):
    with pytest.raises(AnalysisError):
        parse_findings(payload, "a.py", 1)


def test_empty_findings_and_code_fences():
    assert parse_findings('```json\n{"findings": []}\n```', "a.py", 1) == []


def test_only_selected_key_required(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-test")
    monkeypatch.setenv("CLAUDE_MODEL", "custom-claude")
    assert get_config("claude").model == "custom-claude"
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_config("openai")


def test_kimi_key_alias(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.setenv("KIMI_API_KEY", "kimi-test")
    assert get_config("kimi").api_key == "kimi-test"
