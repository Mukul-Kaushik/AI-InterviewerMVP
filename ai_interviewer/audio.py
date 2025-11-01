"""Audio capture and playback utilities."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Optional

import sounddevice as sd
import soundfile as sf


class SystemAudioRecorder:
    """Record loopback/system audio to a WAV file."""

    def __init__(
        self,
        output_path: Path,
        device: Optional[str] = None,
        samplerate: int = 16000,
        channels: int = 1,
    ) -> None:
        self.output_path = Path(output_path)
        self.device = device
        self.samplerate = samplerate
        self.channels = channels
        self._queue: "queue.Queue[bytes]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._writer: Optional[sf.SoundFile] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()

    def start(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._writer = sf.SoundFile(
            str(self.output_path),
            mode="w",
            samplerate=self.samplerate,
            channels=self.channels,
            subtype="PCM_16",
        )
        self._running.set()
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self._callback,
            device=self.device,
        )
        self._stream.start()
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()

    def _callback(self, indata, frames, time, status):  # pragma: no cover - realtime
        if status:
            print(f"Recorder status: {status}")
        self._queue.put(indata.copy())

    def _writer_loop(self) -> None:
        assert self._writer is not None
        while self._running.is_set():
            try:
                data = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            self._writer.write(data)
        while not self._queue.empty():
            data = self._queue.get()
            self._writer.write(data)
        self._writer.flush()
        self._writer.close()
        self._writer = None

    def stop(self) -> None:
        self._running.clear()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)


class TextToSpeechEngine:
    """Convert interview questions into audible speech."""

    def __init__(self, voice: Optional[str] = None) -> None:
        import pyttsx3

        self.engine = pyttsx3.init()
        if voice:
            for v in self.engine.getProperty("voices"):
                if voice.lower() in v.id.lower():
                    self.engine.setProperty("voice", v.id)
                    break

    def speak(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


class AudioBridge:
    """Coordinates system audio capture and text-to-speech output."""

    def __init__(
        self,
        recorder: SystemAudioRecorder,
        tts: TextToSpeechEngine,
    ) -> None:
        self.recorder = recorder
        self.tts = tts

    def start(self) -> None:
        self.recorder.start()

    def stop(self) -> None:
        self.recorder.stop()

    def ask(self, text: str) -> None:
        self.tts.speak(text)
