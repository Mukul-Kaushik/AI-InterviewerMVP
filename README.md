# AI Interviewer MVP

A desktop proof-of-concept that joins a Google Meet, conducts a structured
interview powered by large language models, records the candidate's audio, and
produces a transcript and closing summary.

## Features

- PySide6 desktop UI to configure the session and launch the workflow.
- Playwright automation joins the specified Google Meet URL and keeps the tab
  active while the conversation happens.
- Text-to-speech engine (pyttsx3) voices questions over a virtual microphone.
- Loopback audio recording via `sounddevice` captures the candidate's answers to
  a WAV file.
- `faster-whisper` (optional) generates a transcript; the aggregated transcript
  is summarised by the selected LLM provider (OpenAI, Anthropic, or Google
  Generative AI).
- Supports loading CVs from PDF, DOCX, or plain-text files to tailor the
  interview outline.
- Persists transcripts, audio, and video artifacts under
  `~/AI-Interviewer/artifacts/`.

## Getting started

1. **Install dependencies**

   ```bash
   pip install -e .
   playwright install
   ```

2. **Prepare audio routing**

   - Install a virtual audio cable (e.g. VB-Audio on Windows or BlackHole on
     macOS) and configure it as the system output so the recorder can capture the
     candidate's voice via loopback.
   - Expose the same virtual device as the input microphone for Google Meet and
     select it in your OS audio settings so the TTS playback is heard by the
     participant.

3. **Launch the desktop app**

   ```bash
   ai-interviewer
   ```

4. **Run an interview**

   - Paste the Google Meet link, candidate name, and choose the CV file.
   - Select an LLM provider/model and supply the relevant API key.
   - Optionally customise the interview outline or leave blank to use the default
     flow.
   - Click **Start interview**. The app will:
     1. Parse the CV and request an interview plan from the chosen LLM.
     2. Join the Google Meet in a Chromium instance and announce itself in chat.
     3. Voice each question using text-to-speech while recording the candidate's
        responses.
     4. Transcribe the captured audio (if `faster-whisper` is installed) and ask
        the LLM for a candidate summary.
     5. Persist artifacts (transcript, WAV recording, Meet video capture) under
        the artifacts directory.

## Notes & limitations

- You must be signed into Google in the launched Chromium window if the Meet
  requires authentication. The Playwright automation pauses briefly on the
  pre-join screen so you can resolve captchas or login prompts.
- `faster-whisper` downloads models on first use; ensure you have internet
  connectivity and sufficient disk space.
- For production-quality recordings, point the recorder at an explicit loopback
  device via the **capture loopback device** field in the configuration (editable
  in code via `InterviewSettings`).
- The MVP uses pyttsx3 for offline synthesis. Swap in a cloud TTS provider if
  you need higher-fidelity voices.
- Summaries and interview plan generation depend on the supplied API keys and
  quota for the selected provider.

## Development

- The project targets Python 3.10+.
- Run `pip install -e .[dev]` if you add optional tooling for linting or tests.
- Contributions welcome! Open an issue describing improvements or bugs.
