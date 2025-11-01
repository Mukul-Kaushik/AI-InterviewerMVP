"""Configuration dataclasses for the AI Interviewer MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class LLMProviderConfig:
    """Configuration required to talk to a specific LLM provider."""

    provider: str
    model: str
    api_key: Optional[str] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, str]:
        data = {"provider": self.provider, "model": self.model}
        if self.api_key:
            data["api_key"] = self.api_key
        data.update(self.extra)
        return data


@dataclass
class InterviewSettings:
    """Holds the end-to-end configuration for a session."""

    meeting_url: str
    candidate_name: str
    interviewer_name: str
    cv_path: Path
    llm: LLMProviderConfig
    transcript_path: Path
    audio_output_path: Path
    video_output_path: Path
    question_voice: str = "en-US-Wavenet-D"
    capture_loopback_device: Optional[str] = None
    virtual_microphone_device: Optional[str] = None
    interview_outline: Optional[str] = None
    warmup_prompt: Optional[str] = None

    def ensure_paths(self) -> None:
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.audio_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.video_output_path.parent.mkdir(parents=True, exist_ok=True)


DEFAULT_OUTLINE = """\
1. Welcome the candidate and confirm audio quality.
2. Ask about the candidate's most relevant experience for the role.
3. Dive deeper into one technical project.
4. Explore behavioural competencies.
5. Provide time for candidate questions.
6. Close by explaining next steps."""
