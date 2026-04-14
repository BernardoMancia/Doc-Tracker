import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from alerts.webhook import WebhookDispatcher
from config.intelligence_matrix import IntelligenceMatrix
from core.database import get_db, async_session
from core.models import Finding, Scan
from crawler.dork_generator import DorkGenerator
from crawler.search_engine import SearchEngine
from crawler.url_filter import URLFilter, detect_country, detect_language
from inspector.downloader import Downloader
from inspector.extractor import TextExtractor
from inspector.regex_engine import RegexEngine
from inspector.risk_classifier import RiskClassifier

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scans"])

scan_progress = {
    "phase": "idle",
    "current": 0,
    "total": 0,
    "detail": "",
}


def _update_progress(phase: str, current: int, total: int, detail: str = ""):
    scan_progress["phase"] = phase
    scan_progress["current"] = current
    scan_progress["total"] = total
    scan_progress["detail"] = detail


async def _run_scan():
    logger.info("=== OSINT Scan Started ===")
    _update_progress("starting", 0, 0, "Inicializando...")

    async with async_session() as db:
        scan = Scan(status="running", progress_phase="starting")
        db.add(scan)
        await db.flush()
        scan_id = scan.id

        try:
            matrix = IntelligenceMatrix()
            generator = DorkGenerator(matrix)
            url_filter = URLFilter(matrix)
            search = SearchEngine(url_filter)
            downloader = Downloader()
            extractor = TextExtractor()
            regex_engine = RegexEngine(matrix)
            classifier = RiskClassifier(matrix)
            webhook = WebhookDispatcher()

            dorks = generator.generate_all()
            total_dorks = len(dorks)
            logger.info("Generated %d dorks", total_dorks)
            scan.set_dorks(dorks[:50])
            scan.progress_total = total_dorks
            scan.progress_phase = "crawling"
            await db.flush()

            _update_progress("crawling", 0, total_dorks)

            all_discovered = []
            for i, dork in enumerate(dorks):
                _update_progress("crawling", i + 1, total_dorks, f"Dork {i+1}/{total_dorks}")
                scan.progress_current = i + 1
                if i % 5 == 0:
                    await db.flush()

                results = await search._search_single_dork(dork)
                all_discovered.extend(results)

                import asyncio
                import random
                delay = random.uniform(2.0, 4.0)
                await asyncio.sleep(delay)

            scan.total_urls_found = len(all_discovered)
            scan.progress_phase = "inspecting"
            scan.progress_current = 0
            scan.progress_total = len(all_discovered)
            await db.flush()

            logger.info("Discovered %d URLs, starting inspection...", len(all_discovered))

            findings_count = 0
            total_urls = len(all_discovered)

            for i, item in enumerate(all_discovered):
                _update_progress("inspecting", i + 1, total_urls, item.url[:60])
                scan.progress_current = i + 1
                if i % 3 == 0:
                    await db.flush()

                logger.info("Inspecting %d/%d: %s", i + 1, total_urls, item.url[:80])

                existing = await db.execute(
                    select(Finding).where(Finding.url == item.url)
                )
                if existing.scalar_one_or_none():
                    continue

                file_type = url_filter.detect_file_type(item.url)
                download_result = await downloader.download(item.url)

                if not download_result.success or not download_result.data:
                    continue

                if download_result.detected_type != "unknown":
                    file_type = download_result.detected_type

                extraction = extractor.extract(download_result.data, file_type)
                if not extraction.text:
                    continue

                inspection = regex_engine.inspect(extraction.text)
                if not inspection.has_findings:
                    continue

                risk = classifier.classify(inspection)
                platform = url_filter.detect_platform(item.url)

                doc_author = extraction.metadata.get("author", "")
                doc_creator = extraction.metadata.get("creator", "")
                doc_publisher = doc_creator if doc_creator and doc_creator != doc_author else ""

                country = detect_country(item.url)
                language = detect_language(extraction.text)

                finding = Finding(
                    scan_id=scan_id,
                    source_platform=platform,
                    url=item.url,
                    title=item.title,
                    file_type=file_type,
                    risk_level=risk.level,
                    risk_score=risk.score,
                    category=risk.category,
                    entity_matched=", ".join(inspection.entity_matches[:5]),
                    cpf_count=inspection.cpf_count,
                    cnpj_count=inspection.cnpj_count,
                    financial_count=inspection.financial_count,
                    sensitive_terms=json.dumps(
                        inspection.sensitive_term_matches, ensure_ascii=False
                    ),
                    snippets=json.dumps(inspection.snippets, ensure_ascii=False),
                    author=doc_author,
                    publisher=doc_publisher,
                    country=country,
                    language=language,
                    doc_metadata=json.dumps(extraction.metadata, ensure_ascii=False),
                )
                db.add(finding)
                findings_count += 1

                await webhook.dispatch(
                    risk_level=risk.level,
                    title=item.title,
                    url=item.url,
                    platform=platform,
                    cpf_count=inspection.cpf_count,
                    cnpj_count=inspection.cnpj_count,
                    entity=", ".join(inspection.entity_matches[:3]),
                    category=risk.category,
                )

                download_result.data.close()

            scan.total_findings = findings_count
            scan.status = "completed"
            scan.progress_phase = "completed"
            scan.finished_at = datetime.now(timezone.utc)
            await db.commit()

            await downloader.close()
            await webhook.close()

            _update_progress("completed", findings_count, total_urls, "Scan finalizado")

            logger.info(
                "=== Scan Complete: %d findings from %d URLs ===",
                findings_count,
                total_urls,
            )

        except Exception as e:
            logger.exception("Scan failed: %s", e)
            scan.status = "failed"
            scan.progress_phase = "failed"
            scan.finished_at = datetime.now(timezone.utc)
            await db.commit()
            _update_progress("failed", 0, 0, str(e))


@router.get("/scans")
async def list_scans(db: AsyncSession = Depends(get_db)):
    query = select(Scan).order_by(Scan.id.desc()).limit(50)
    rows = (await db.execute(query)).scalars().all()

    return {
        "scans": [
            {
                "id": s.id,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None,
                "status": s.status,
                "total_urls_found": s.total_urls_found,
                "total_findings": s.total_findings,
            }
            for s in rows
        ]
    }


@router.get("/scans/progress")
async def get_scan_progress():
    return scan_progress


@router.post("/scans/trigger")
async def trigger_scan(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    running_q = select(Scan).where(Scan.status == "running").limit(1)
    running = (await db.execute(running_q)).scalar_one_or_none()
    if running:
        return {"message": "Scan already running", "status": "running", "scan_id": running.id}

    background_tasks.add_task(_run_scan)
    return {"message": "Scan triggered", "status": "queued"}
