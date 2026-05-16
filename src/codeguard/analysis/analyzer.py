"""Analyze Python source with OpenAI, Claude, or Kimi."""

from anthropic import Anthropic
from openai import OpenAI

from codeguard.config import ProviderConfig
from codeguard.models import Finding

from .parser import AnalysisError, parse_findings
from .prompts import SYSTEM_PROMPT, source_prompt


class Analyzer:
    def __init__(self, config: ProviderConfig):
        self.config = config
        if config.provider == "claude":
            self.client = Anthropic(api_key=config.api_key, timeout=120, max_retries=2)
        else:
            # Explicit endpoints prevent a globally configured OpenAI endpoint from
            # accidentally receiving another provider's key or repository source.
            endpoint = config.base_url if config.provider == "kimi" else "https://api.openai.com/v1"
            self.client = OpenAI(
                api_key=config.api_key,
                base_url=endpoint,
                timeout=120,
                max_retries=2,
            )

    def close(self) -> None:
        self.client.close()

    def analyze(self, file_path: str, source: str) -> list[Finding]:
        prompt = source_prompt(file_path, source)
        if self.config.provider == "claude":
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            if response.stop_reason != "end_turn":
                raise AnalysisError("Claude returned an incomplete or refused analysis.")
            text = "".join(block.text for block in response.content if block.type == "text")
        elif self.config.provider == "kimi":
            response = self.client.chat.completions.create(
                model=self.config.model,
                max_tokens=16384,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            if not response.choices or response.choices[0].finish_reason != "stop":
                raise AnalysisError("Kimi returned an incomplete analysis.")
            text = response.choices[0].message.content
        else:
            response = self.client.responses.create(
                model=self.config.model,
                instructions=SYSTEM_PROMPT,
                input=prompt,
                max_output_tokens=8192,
                store=False,
                text={"format": {"type": "json_object"}},
            )
            if response.status != "completed":
                raise AnalysisError("OpenAI returned an incomplete analysis.")
            text = response.output_text
        return parse_findings(text, file_path, len(source.splitlines()))
