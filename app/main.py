"""Desktop GUI entrypoint for the AI Interviewer MVP."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from ai_interviewer import InterviewController, InterviewSettings
from ai_interviewer.settings import LLMProviderConfig


class InterviewWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Interviewer MVP")
        self.resize(900, 720)
        self.controller = None
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        form_layout = QVBoxLayout()

        self.meeting_url = QLineEdit()
        self.meeting_url.setPlaceholderText("https://meet.google.com/...")
        form_layout.addWidget(QLabel("Google Meet URL"))
        form_layout.addWidget(self.meeting_url)

        self.candidate_name = QLineEdit()
        form_layout.addWidget(QLabel("Candidate name"))
        form_layout.addWidget(self.candidate_name)

        self.interviewer_name = QLineEdit()
        self.interviewer_name.setText("AI Interviewer")
        form_layout.addWidget(QLabel("Display name (in Google Meet)"))
        form_layout.addWidget(self.interviewer_name)

        cv_layout = QHBoxLayout()
        self.cv_path = QLineEdit()
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._choose_cv)
        cv_layout.addWidget(self.cv_path)
        cv_layout.addWidget(browse_button)
        form_layout.addWidget(QLabel("Candidate CV (PDF/DOCX/TXT)"))
        form_layout.addLayout(cv_layout)

        provider_layout = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "anthropic", "google"])
        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("Model, e.g. gpt-4o-mini")
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addWidget(self.model_name)
        form_layout.addWidget(QLabel("LLM Provider & Model"))
        form_layout.addLayout(provider_layout)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(QLabel("API key"))
        form_layout.addWidget(self.api_key)

        self.outline = QTextEdit()
        self.outline.setPlaceholderText("Optional custom interview outline…")
        self.outline.setFixedHeight(120)
        form_layout.addWidget(QLabel("Interview outline"))
        form_layout.addWidget(self.outline)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        form_layout.addWidget(QLabel("Status & Transcript"))
        form_layout.addWidget(self.status_log)

        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start interview")
        self.start_button.clicked.connect(self._start)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._stop)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        form_layout.addLayout(button_layout)

        layout.addLayout(form_layout)
        self.setCentralWidget(container)

    # UI actions ---------------------------------------------------------------------

    def _choose_cv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select CV", "", "Documents (*.pdf *.docx *.txt)")
        if path:
            self.cv_path.setText(path)

    def _append_log(self, message: str) -> None:
        self.status_log.append(message)
        self.status_log.verticalScrollBar().setValue(self.status_log.verticalScrollBar().maximum())

    def _start(self) -> None:
        if self.controller:
            QMessageBox.warning(self, "Interview running", "An interview is already in progress.")
            return
        try:
            settings = self._build_settings()
        except ValueError as exc:
            QMessageBox.critical(self, "Invalid input", str(exc))
            return
        self.controller = InterviewController(
            settings,
            on_status=lambda msg: self._append_log(f"[status] {msg}"),
            on_transcript=lambda txt: self._append_log(f"[transcript]\n{txt}"),
            on_summary=lambda summary: self._append_log(f"[summary]\n{summary}"),
        )
        self._append_log("Launching interview workflow…")
        self.controller.start()

    def _stop(self) -> None:
        if self.controller:
            self.controller.stop()
            self._append_log("Stop requested. The interview will end shortly.")
            self.controller = None

    def _build_settings(self) -> InterviewSettings:
        meeting = self.meeting_url.text().strip()
        if not meeting:
            raise ValueError("Provide a Google Meet URL")
        cv_file = self.cv_path.text().strip()
        if not cv_file:
            raise ValueError("Select a CV document")
        cv_path = Path(cv_file)
        if not cv_path.exists():
            raise ValueError("CV path does not exist")
        provider = self.provider_combo.currentText()
        model = self.model_name.text().strip() or "gpt-4o-mini"
        api_key = self.api_key.text().strip() or None
        llm = LLMProviderConfig(provider=provider, model=model, api_key=api_key)
        artifacts_dir = Path.home() / "AI-Interviewer" / "artifacts"
        transcript_path = artifacts_dir / "transcripts" / f"{cv_path.stem}.txt"
        audio_path = artifacts_dir / "audio" / f"{cv_path.stem}.wav"
        video_path = artifacts_dir / "video" / f"{cv_path.stem}.webm"
        return InterviewSettings(
            meeting_url=meeting,
            candidate_name=self.candidate_name.text().strip() or cv_path.stem,
            interviewer_name=self.interviewer_name.text().strip() or "AI Interviewer",
            cv_path=cv_path,
            llm=llm,
            transcript_path=transcript_path,
            audio_output_path=audio_path,
            video_output_path=video_path,
            interview_outline=self.outline.toPlainText().strip() or None,
        )


def main() -> None:
    app = QApplication(sys.argv)
    window = InterviewWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
