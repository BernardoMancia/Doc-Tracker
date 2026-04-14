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


class WebhookDispatcher:

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15)
        return self._client

    def _format_message(
        self,
        risk_level: str,
        title: str,
        url: str,
        platform: str,
        cpf_count: int,
        cnpj_count: int,
        entity: str,
        category: str,
    ) -> str:
        emoji = RISK_EMOJI.get(risk_level, "⚪")
        level_pt = {
            "critical": "CRÍTICO",
            "high": "ALTO",
            "medium": "MÉDIO",
            "low": "BAIXO",
        }.get(risk_level, risk_level.upper())

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        lines = [
            f"{emoji} *ALERTA DE VAZAMENTO — Risco {level_pt}*",
            "",
            f"📄 *Documento:* {title}",
            f"🏢 *Entidade:* {entity}",
            f"🌐 *Fonte:* {platform}",
            f"📂 *Categoria:* {category}",
        ]

        if cpf_count > 0:
            lines.append(f"🔍 *CPFs detectados:* {cpf_count}")
        if cnpj_count > 0:
            lines.append(f"🔍 *CNPJs detectados:* {cnpj_count}")

        lines.extend([
            "",
            f"🔗 *URL:* {url}",
            f"🕐 *Detectado:* {timestamp}",
            f"📊 *Dashboard:* {settings.dashboard_url}",
        ])

        return "\n".join(lines)

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

    async def dispatch(self, risk_level: str, title: str, url: str, platform: str,
                       cpf_count: int = 0, cnpj_count: int = 0, entity: str = "", category: str = ""):
        if risk_level not in ("critical", "high"):
            return
        message = self._format_message(risk_level, title, url, platform, cpf_count, cnpj_count, entity, category)
        await self.send_telegram(message)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
