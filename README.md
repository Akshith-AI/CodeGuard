# CodeGuard

AI-powered security scanner for Python code in public GitHub repositories.

## Status

This repository is an initial project scaffold. Repository scanning, AI analysis,
and report generation are planned and are not implemented yet.

## Planned workflow

1. Retrieve Python files from a public GitHub repository using PyGitHub.
2. Analyze source code with OpenAI GPT-4o for potential vulnerabilities.
3. Validate structured findings containing vulnerability type, severity, file,
   affected line, description, and suggested fix.
4. Display color-coded results and export plain-text reports.

Target issues include SQL injection, hardcoded secrets, weak cryptography, and
command injection. Severity levels are CRITICAL, HIGH, MEDIUM, and LOW.

## Setup

Requires Python 3.10 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
```

If `.env` already exists, edit it instead of copying over it. Add your
`OPENAI_API_KEY` and optionally `GITHUB_TOKEN`. The default model is `gpt-4o`.
Credentials and generated reports are ignored by Git.

```sh
codeguard --help
codeguard --version
```

The CLI currently provides help and version information only.

## Layout

```text
src/codeguard/
  cli.py                 Command-line entry point
  config.py              Environment configuration placeholder
  models.py              Shared finding model
  scanner/               GitHub repository scanning
  analysis/              AI analysis, prompts, and JSON parsing
  reporting/             Terminal output and text reports
tests/                   Future automated tests
reports/                 Generated reports (ignored)
.env.example             Environment variable template
pyproject.toml           Package metadata and dependencies
```

## Future improvements

- Integrate Bandit or Semgrep for hybrid static and AI analysis.
- Add vulnerable and secure fixtures to measure detection accuracy.
- Add GitHub Actions and SARIF output.
- Support local models.

AI findings require human review. The planned OpenAI integration will transmit
scanned source code to the configured API.
