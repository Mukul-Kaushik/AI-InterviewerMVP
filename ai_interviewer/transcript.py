"""Transcript utilities for the AI Interviewer MVP."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional


class TranscriptManager:
    """Persist interview transcripts and leverage speech recognition."""

    def __init__(self, transcript_path: Path, model_size: str = "small") -> None:
        self.transcript_path = Path(transcript_path)
        self.model_size = model_size
        self._entries: List[str] = []
        try:
            from faster_whisper import WhisperModel

            self._whisper: Optional[WhisperModel] = WhisperModel(model_size)
        except Exception:  # pragma: no cover - optional dependency
            self._whisper = None

    def append(self, speaker: str, text: str) -> None:
        line = f"{speaker}: {text.strip()}"
        self._entries.append(line)
        self.transcript_path.parent.mkdir(parents=True, exist_ok=True)
        self.transcript_path.write_text("\n".join(self._entries), encoding="utf-8")

    def transcribe_audio(self, audio_path: Path) -> str:
        if not self._whisper:
            raise RuntimeError(
                "faster-whisper is not installed. Install it or provide an OpenAI key"
            )
        segments, _ = self._whisper.transcribe(str(audio_path))
        text = " ".join(segment.text.strip() for segment in segments)
        return text.strip()

    def summary(self, llm) -> str:
        prompt = """Summarise the interview transcript focusing on strengths, risks, and recommendations."""
        content = "\n".join(self._entries)
        response = llm.generate(f"Transcript:\n{content}\n\n{prompt}", max_output_tokens=400)
        return response.content.strip()
