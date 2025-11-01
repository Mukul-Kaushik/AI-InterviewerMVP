"""Google Meet automation helpers."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from playwright.async_api import async_playwright, Page


class MeetClient:
    """Launches a Chromium instance and joins a Google Meet."""

    def __init__(
        self,
        meeting_url: str,
        display_name: str,
        headless: bool = False,
        record_video_dir: Optional[Path] = None,
    ) -> None:
        self.meeting_url = meeting_url
        self.display_name = display_name
        self.headless = headless
        self.record_video_dir = record_video_dir
        self._playwright = None
        self._browser = None
        self._context = None
        self._page: Optional[Page] = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[Page]:
        async with async_playwright() as p:
            self._playwright = p
            self._browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--use-fake-ui-for-media-stream",
                    "--use-fake-device-for-media-stream",
                ],
            )
            context_kwargs = {}
            if self.record_video_dir:
                context_kwargs["record_video_dir"] = str(self.record_video_dir)
            self._context = await self._browser.new_context(**context_kwargs)
            self._page = await self._context.new_page()
            await self._page.goto(self.meeting_url)
            await self._handle_prejoin()
            try:
                yield self._page
            finally:
                await self._context.close()
                await self._browser.close()

    async def _handle_prejoin(self) -> None:
        assert self._page is not None
        page = self._page
        await page.wait_for_timeout(2000)
        name_input = page.locator('input[aria-label="Your name"]')
        if await name_input.count() > 0:
            await name_input.fill(self.display_name)
        mic_button = page.locator('[aria-label="Turn off microphone (ctrl + d)"]')
        if await mic_button.count() > 0:
            await mic_button.click()
        cam_button = page.locator('[aria-label="Turn off camera (ctrl + e)"]')
        if await cam_button.count() > 0:
            await cam_button.click()
        join_button = page.locator("button:has-text('Ask to join'), button:has-text('Join now')")
        await join_button.first.click()
        await page.wait_for_timeout(3000)

    async def send_chat_message(self, text: str) -> None:
        if not self._page:
            raise RuntimeError("Meet session not started")
        page = self._page
        await page.keyboard.press("CTRL+ALT+c")
        await page.wait_for_timeout(500)
        textbox = page.locator('[aria-label="Send a message to everyone"]')
        await textbox.fill(text)
        await textbox.press("Enter")

    async def leave(self) -> None:
        if self._page:
            await self._page.keyboard.press("CTRL+ALT+h")
            await asyncio.sleep(1)
