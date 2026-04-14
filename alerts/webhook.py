import logging
from datetime import datetime, timezone

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

RISK_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
}

RISK_PT = {
    "critical": "CRÍTICO",
    "high": "ALTO",
    "medium": "MÉDIO",
    "low": "BAIXO",
}


class WebhookDispatcher:

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    async def send_telegram(self, message: str) -> bool:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return False
        try:
            client = await self._get_client()
            resp = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            resp.raise_for_status()
            logger.info("Telegram alert sent")
            return True
        except Exception as e:
            logger.error("Telegram alert failed: %s", e)
            return False

    async def send_scan_started(self, total_dorks: int):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        message = (
            "🔍 *SCAN INICIADO*\n"
            "\n"
            f"📡 *Dorks:* {total_dorks}\n"
            f"🕐 *Início:* {now}\n"
            f"📊 *Dashboard:* {settings.dashboard_url}\n"
            "\n"
            "Buscando vazamentos..."
        )
        await self.send_telegram(message)

    async def send_scan_summary(self, new_findings: list[dict], total_urls: int):
        if not new_findings:
            message = (
                "✅ *SCAN CONCLUÍDO — Nenhum novo vazamento*\n"
                "\n"
                f"🔗 *URLs analisadas:* {total_urls}\n"
                f"📊 *Dashboard:* {settings.dashboard_url}"
            )
            await self.send_telegram(message)
            return

        grouped = {"critical": [], "high": [], "medium": [], "low": []}
        for f in new_findings:
            level = f.get("risk_level", "low")
            if level in grouped:
                grouped[level].append(f)

        total_new = len(new_findings)
        counts = {k: len(v) for k, v in grouped.items()}
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        header = (
            f"⚠️ *SCAN CONCLUÍDO — {total_new} novo(s) vazamento(s)*\n"
            "\n"
            f"🔗 *URLs analisadas:* {total_urls}\n"
            f"🔴 Crítico: {counts['critical']} | "
            f"🟠 Alto: {counts['high']} | "
            f"🟡 Médio: {counts['medium']} | "
            f"🟢 Baixo: {counts['low']}\n"
            f"🕐 {now}\n"
        )
        await self.send_telegram(header)

        for level in ("critical", "high", "medium", "low"):
            findings = grouped[level]
            if not findings:
                continue

            emoji = RISK_EMOJI[level]
            label = RISK_PT[level]

            chunks = []
            current_chunk = f"{emoji} *{label} ({len(findings)})*\n\n"

            for f in findings:
                entry = (
                    f"• *{f.get('entity', '—')}* | {f.get('platform', '—')}\n"
                    f"  {f.get('title', '—')[:60]}\n"
                    f"  {f.get('url', '')}\n\n"
                )
                if len(current_chunk) + len(entry) > 3800:
                    chunks.append(current_chunk)
                    current_chunk = f"{emoji} *{label} (cont.)*\n\n"
                current_chunk += entry

            if current_chunk.strip():
                chunks.append(current_chunk)

            for chunk in chunks:
                await self.send_telegram(chunk)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
