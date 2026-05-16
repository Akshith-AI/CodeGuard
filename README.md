# CodeGuard

AI-powered CLI security scanner for Python code in public GitHub repositories,
with OpenAI, Claude, and Kimi support.

## Setup

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

If `.env` already exists, edit it instead of overwriting it. Fill in the key for
each provider you want to use:

| Provider | API key variable | Default model | Model override |
| --- | --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` | `OPENAI_MODEL` |
| Claude | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | `CLAUDE_MODEL` |
| Kimi | `MOONSHOT_API_KEY` (or `KIMI_API_KEY`) | `kimi-k3` | `KIMI_MODEL` |

Only the selected provider's key is required. `GITHUB_TOKEN` is optional and
increases GitHub API rate limits. Kimi uses `https://api.moonshot.ai/v1` by default;
`KIMI_BASE_URL` can configure a regional endpoint. Choose a model ID available
to your account; environment defaults and `--model` allow changing models.
`.env` and generated reports are ignored by Git.

## Run

```sh
codeguard
# Alternatively:
python -m codeguard
```

The terminal asks which provider to use, offers its configured model ID (press
Enter to accept or type another), then asks for a GitHub repository:

```text
Choose a model provider:
  1. OpenAI (gpt-4o)
  2. Claude (claude-sonnet-5-5)
  3. Kimi (kimi-k3)
Provider: 2
Model ID [claude-sonnet-5-5]:
GitHub repository: owner/repo
```

You can also supply the repository while keeping the model menu:

```sh
codeguard owner/repo
```

For scripts or CI, choose the provider explicitly to skip interactive prompts:

```sh
codeguard owner/repo --provider openai
codeguard https://github.com/owner/repo --provider claude --model claude-sonnet-5-5
codeguard owner/repo --provider kimi --output reports/kimi-report.txt
```

## Scanning and reports

CodeGuard retrieves Python files at a fixed commit on the repository's default
branch, sends each file to the selected provider, validates JSON findings, and
shows severity-colored terminal results. Findings include type, severity
(CRITICAL/HIGH/MEDIUM/LOW), file, line, description, and suggested remediation.

Text reports are saved under `reports/` unless `--output` is specified. Reports
include the scanned commit, model, successful file count, skipped files, and
analysis failures. Invalid or truncated model output is recorded as a failure,
never treated as a successful scan with no findings.

Default limits: 20 nonempty Python files, 50,000 bytes per file. Change them with
`--max-files` and `--max-file-bytes`. Files beyond these limits or with unsupported
encodings are listed as skipped. Scans with skipped or failed files exit with
code 1; complete scans exit with code 0, including scans with findings.
This is not currently a vulnerability-based CI gate.

Source code is transmitted to the selected provider and API usage may incur
charges. AI findings are potential issues requiring human review; this tool
cannot certify that a repository is secure. Analysis is per file and may miss
issues that depend on relationships between files. No live API accuracy or
provider credential validation is covered by the offline test suite.

## Development

```sh
pytest
ruff check src tests
```

```text
src/codeguard/
  cli.py                 Interactive selection and scan workflow
  config.py              Environment variables and provider defaults
  models.py              Shared finding model
  scanner/               Public GitHub Python file retrieval
  analysis/              Provider integrations, prompts, JSON validation
  reporting/             Terminal output and text reports
tests/                   Offline provider and CLI tests
reports/                 Generated reports (ignored)
```

Provider references: [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
[Claude Messages API](https://platform.claude.com/docs/en/api/messages/create),
[Kimi quickstart](https://platform.kimi.ai/docs/overview).

Future improvements: static analysis with Bandit or Semgrep, detection accuracy
fixtures, SARIF output, GitHub Actions, and local model support.
