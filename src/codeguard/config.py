"""Provider configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

PROVIDERS = {
    "openai": ("OpenAI", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o"),
    "claude": ("Claude", "ANTHROPIC_API_KEY", "CLAUDE_MODEL", "claude-sonnet-5-5"),
    "kimi": ("Kimi", "MOONSHOT_API_KEY", "KIMI_MODEL", "kimi-k3"),
}


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key: str
    base_url: str | None = None


def load_environment() -> None:
    load_dotenv()


def default_model(provider: str) -> str:
    _, _, variable, fallback = PROVIDERS[provider]
    return os.getenv(variable, "").strip() or fallback


def get_config(provider: str, model: str | None = None) -> ProviderConfig:
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    _, key_variable, _, _ = PROVIDERS[provider]
    key = os.getenv(key_variable, "").strip()
    if provider == "kimi" and not key:
        key = os.getenv("KIMI_API_KEY", "").strip()
    if not key:
        raise ValueError(f"Set {key_variable} in .env before using {PROVIDERS[provider][0]}.")
    base_url = None
    if provider == "kimi":
        base_url = os.getenv("KIMI_BASE_URL", "").strip() or "https://api.moonshot.ai/v1"
    selected_model = (model or default_model(provider)).strip()
    if not selected_model:
        raise ValueError("Model name cannot be empty.")
    return ProviderConfig(provider, selected_model, key, base_url)
