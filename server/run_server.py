import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from config.settings import settings
from api.app import create_app as _create_base_app
from api.routes.scans import _run_scan
from alerts.webhook import WebhookDispatcher

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_scan():
    logger.info("=== Scheduled Scan Triggered ===")
    await _run_scan()


async def send_startup_alert():
    dispatcher = WebhookDispatcher()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    schedule = ", ".join(f"{h}:00" for h in settings.schedule_hours)
    message = (
        "🟢 *OSINT/DLP System — Online*\n"
        "\n"
        f"🖥️ *Server:* {settings.dashboard_url}\n"
        f"🕐 *Início:* {now}\n"
        f"📅 *Auto-scan:* {schedule} BRT\n"
        f"🔧 *Port:* {settings.api_port}\n"
        "\n"
        "✅ Scheduler ativo. Monitoramento em andamento."
    )
    await dispatcher.send_telegram(message)
    await dispatcher.close()
    logger.info("Startup alert sent to Telegram")


def _configure_scheduler():
    hours = settings.schedule_hours
    for hour in hours:
        scheduler.add_job(
            scheduled_scan,
            CronTrigger(hour=hour, minute=0, timezone="America/Sao_Paulo"),
            id=f"scan_{hour}h",
            replace_existing=True,
        )
        logger.info("Scheduled scan at %02d:00 BRT", hour)


def create_server_app() -> FastAPI:
    app = _create_base_app()

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def server_lifespan(app):
        async with original_lifespan(app):
            _configure_scheduler()
            scheduler.start()
            logger.info("Scheduler started")
            await send_startup_alert()
            yield
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    app.router.lifespan_context = server_lifespan
    return app


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("OSINT/DLP Server Mode — Port %d", settings.api_port)
    logger.info("Schedule: %s", settings.scan_schedule_hours)

    app = create_server_app()

    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
