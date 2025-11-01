"""Structured interview orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from .llm import LLMClient, LLMClientError
from .settings import DEFAULT_OUTLINE


@dataclass
class InterviewStep:
    """Represents a single question/step in the interview."""

    title: str
    question: str
    followups: List[str] = field(default_factory=list)


class InterviewFlow:
    """Builds and executes a structured interview."""

    def __init__(
        self,
        llm: LLMClient,
        cv_text: str,
        outline: Optional[str] = None,
        warmup_prompt: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.cv_text = cv_text
        self.outline = outline or DEFAULT_OUTLINE
        self.warmup_prompt = warmup_prompt or "Warmly welcome the candidate."
        self._steps: List[InterviewStep] = []
        self._current_index = 0

    @property
    def steps(self) -> Iterable[InterviewStep]:
        return list(self._steps)

    def build(self) -> List[InterviewStep]:
        """Ask the LLM to propose a structured set of questions."""

        prompt = f"""
You are preparing to interview a candidate.
CV:
{self.cv_text}

Interview outline:
{self.outline}

Return a JSON array where each item has the following keys:
- title: short string for UI display
- question: the primary question to ask
- followups: array of short follow-up prompts to dive deeper

Start with an item called "Welcome" that follows this warmup instruction: {self.warmup_prompt}.
"""
        response = self.llm.generate(prompt, max_output_tokens=1024)
        raw = response.content
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Attempt to coerce into JSON by extracting fenced code block
            cleaned = self._extract_json_block(raw)
            if not cleaned:
                raise LLMClientError(
                    "Failed to parse interview plan from the language model response"
                )
            data = json.loads(cleaned)
        self._steps = [
            InterviewStep(
                title=item.get("title", f"Step {idx + 1}"),
                question=item.get("question", ""),
                followups=item.get("followups", []) or [],
            )
            for idx, item in enumerate(data)
        ]
        self._current_index = 0
        return self._steps

    def _extract_json_block(self, text: str) -> Optional[str]:
        fence = "```"
        if fence not in text:
            return None
        parts = text.split(fence)
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("[") and candidate.endswith("]"):
                return candidate
        return None

    def next_step(self) -> Optional[InterviewStep]:
        if self._current_index >= len(self._steps):
            return None
        step = self._steps[self._current_index]
        self._current_index += 1
        return step
