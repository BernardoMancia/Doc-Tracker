import io
import logging
from dataclasses import dataclass, field

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    success: bool = False
    data: io.BytesIO | None = None
    content_type: str = ""
    size: int = 0
    detected_type: str = "unknown"
    error: str = ""

    @property
    def size_human(self) -> str:
        if self.size < 1024:
            return f"{self.size}B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f}KB"
        return f"{self.size / (1024 * 1024):.1f}MB"


CONTENT_TYPE_MAP = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
    "text/plain": "txt",
    "text/csv": "csv",
}


class Downloader:

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=settings.download_timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
        return self._client

    async def download(self, url: str) -> DownloadResult:
        try:
            client = await self._get_client()
            head_resp = await client.head(url)
            content_type = head_resp.headers.get("content-type", "").split(";")[0].strip().lower()
            content_length = int(head_resp.headers.get("content-length", 0))

            if content_length > settings.max_file_size_bytes:
                return DownloadResult(error=f"File too large: {content_length}")

            resp = await client.get(url)
            resp.raise_for_status()
            data = io.BytesIO(resp.content)
            size = len(resp.content)

            if size > settings.max_file_size_bytes:
                return DownloadResult(error=f"File too large: {size}")

            actual_ct = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            detected = CONTENT_TYPE_MAP.get(actual_ct, "unknown")

            logger.info("Downloaded %s (%s, %s)", url[:80], detected, f"{size/1024:.1f}KB")

            return DownloadResult(
                success=True,
                data=data,
                content_type=actual_ct,
                size=size,
                detected_type=detected,
            )
        except Exception as e:
            return DownloadResult(error=str(e))

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
