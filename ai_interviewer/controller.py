"""High level orchestration for the AI Interviewer MVP."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path
from typing import Callable, Optional

from .audio import AudioBridge, SystemAudioRecorder, TextToSpeechEngine
from .cv_parser import extract_text
from .interview_flow import InterviewFlow
from .llm import LLMClient
from .meet import MeetClient
from .settings import InterviewSettings
from .transcript import TranscriptManager

StatusCallback = Callable[[str], None]
TranscriptCallback = Callable[[str], None]
SummaryCallback = Callable[[str], None]


class InterviewController:
    """Coordinates the interview lifecycle from CV to summary."""

    def __init__(
        self,
        settings: InterviewSettings,
        on_status: Optional[StatusCallback] = None,
        on_transcript: Optional[TranscriptCallback] = None,
        on_summary: Optional[SummaryCallback] = None,
    ) -> None:
        self.settings = settings
        self.on_status = on_status
        self.on_transcript = on_transcript
        self.on_summary = on_summary
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Interview already running")
        self.settings.ensure_paths()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _emit_status(self, message: str) -> None:
        if self.on_status:
            self.on_status(message)

    def _emit_transcript(self, content: str) -> None:
        if self.on_transcript:
            self.on_transcript(content)

    def _emit_summary(self, content: str) -> None:
        if self.on_summary:
            self.on_summary(content)

    def _run(self) -> None:
        asyncio.run(self._async_run())

    async def _async_run(self) -> None:
        settings = self.settings
        self._emit_status("Parsing CV document…")
        cv_text = extract_text(settings.cv_path)
        llm = LLMClient(settings.llm)
        self._emit_status("Generating interview flow with LLM…")
        flow = InterviewFlow(
            llm,
            cv_text=cv_text,
            outline=settings.interview_outline,
            warmup_prompt=settings.warmup_prompt,
        )
        steps = flow.build()
        transcript = TranscriptManager(settings.transcript_path)
        recorder = SystemAudioRecorder(settings.audio_output_path, device=settings.capture_loopback_device)
        tts = TextToSpeechEngine(settings.question_voice)
        bridge = AudioBridge(recorder, tts)
        bridge.start()
        video_dir = Path(settings.video_output_path).parent
        video_dir.mkdir(parents=True, exist_ok=True)
        meet = MeetClient(
            meeting_url=settings.meeting_url,
            display_name=settings.interviewer_name,
            headless=False,
            record_video_dir=video_dir,
        )
        try:
            async with meet.session() as page:
                self._emit_status("Connected to Google Meet. Beginning interview…")
                for step in steps:
                    if self._stop_event.is_set():
                        break
                    prompt = step.question
                    transcript.append(settings.interviewer_name, prompt)
                    self._emit_transcript("\n".join(transcript._entries))
                    bridge.ask(prompt)
                    for follow in step.followups:
                        transcript.append(settings.interviewer_name, f"(Optional follow-up) {follow}")
                    await page.wait_for_timeout(1000)
                    self._emit_status("Waiting for candidate response…")
                    await asyncio.sleep(20)  # allow candidate to answer
                await meet.send_chat_message("Thank you for your time! We'll follow up shortly.")
                await meet.leave()
        finally:
            bridge.stop()
        try:
            candidate_text = transcript.transcribe_audio(settings.audio_output_path)
        except Exception as exc:
            candidate_text = f"[Transcription unavailable: {exc}]"
        transcript.append(settings.candidate_name, candidate_text)
        self._emit_transcript("\n".join(transcript._entries))
        summary = transcript.summary(llm)
        self._emit_summary(summary)
        self._emit_status("Interview complete.")
