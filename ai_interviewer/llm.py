"""Multi-provider LLM client abstraction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .settings import LLMProviderConfig


class LLMClientError(RuntimeError):
    """Raised when a provider call fails."""


@dataclass
class LLMResponse:
    content: str
    raw: object


class LLMClient:
    """Simple wrapper that normalises responses from multiple LLM providers."""

    def __init__(self, config: LLMProviderConfig) -> None:
        self.config = config

    def _require_api_key(self) -> str:
        if not self.config.api_key:
            raise LLMClientError(
                f"An API key is required for provider '{self.config.provider}'."
            )
        return self.config.api_key

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 512,
    ) -> LLMResponse:
        provider = self.config.provider.lower()
        if provider == "openai":
            return self._generate_openai(
                prompt, system_prompt, temperature, max_output_tokens
            )
        if provider == "anthropic":
            return self._generate_anthropic(
                prompt, system_prompt, temperature, max_output_tokens
            )
        if provider in {"google", "gemini", "google-genai"}:
            return self._generate_google(
                prompt, system_prompt, temperature, max_output_tokens
            )
        raise LLMClientError(f"Unsupported provider '{self.config.provider}'.")

    # Provider specific implementations -------------------------------------------------

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_output_tokens: int,
    ) -> LLMResponse:
        api_key = self._require_api_key()
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMClientError(
                "The 'openai' package is required for OpenAI provider."
            ) from exc

        client = OpenAI(api_key=api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        content = response.choices[0].message.content.strip()
        return LLMResponse(content=content, raw=response)

    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_output_tokens: int,
    ) -> LLMResponse:
        api_key = self._require_api_key()
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMClientError(
                "The 'anthropic' package is required for the Anthropic provider."
            ) from exc

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.config.model,
            max_tokens=max_output_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful interview copilot.",
            messages=[{"role": "user", "content": prompt}],
        )
        content = "".join(block.text for block in response.content)
        return LLMResponse(content=content.strip(), raw=response)

    def _generate_google(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_output_tokens: int,
    ) -> LLMResponse:
        api_key = self._require_api_key()
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMClientError(
                "The 'google-generativeai' package is required for Google provider."
            ) from exc

        genai.configure(api_key=api_key)
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if system_prompt:
            prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        model = genai.GenerativeModel(self.config.model, generation_config=generation_config)
        response = model.generate_content(prompt)
        if response.candidates:
            text = response.candidates[0].content.parts[0].text
        else:
            text = json.dumps(response.to_dict())
        return LLMResponse(content=text.strip(), raw=response)
