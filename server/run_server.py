import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings
from api.app import create_app
from api.routes.scans import _run_scan

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def scheduled_scan():
    logger.info("=== Scheduled Scan Triggered ===")
    await _run_scan()


def setup_scheduler():
    hours = settings.schedule_hours
    for hour in hours:
        scheduler.add_job(
            scheduled_scan,
            CronTrigger(hour=hour, minute=0, timezone="America/Sao_Paulo"),
            id=f"scan_{hour}h",
            replace_existing=True,
        )
        logger.info("Scheduled scan at %02d:00 BRT", hour)
    scheduler.start()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("OSINT/DLP Server Mode — Port %d", settings.api_port)
    logger.info("Schedule: %s", settings.scan_schedule_hours)

    app = create_app()
    setup_scheduler()

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
