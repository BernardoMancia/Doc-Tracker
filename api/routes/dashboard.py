from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Finding, Scan

router = APIRouter(tags=["dashboard"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "api" / "templates"))


@router.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/api/dashboard")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    total_q = select(func.count(Finding.id)).where(Finding.is_deleted == False)
    total = (await db.execute(total_q)).scalar() or 0

    risk_q = (
        select(Finding.risk_level, func.count(Finding.id))
        .where(Finding.is_deleted == False)
        .group_by(Finding.risk_level)
    )
    risk_rows = (await db.execute(risk_q)).all()
    by_risk = {row[0]: row[1] for row in risk_rows}

    platform_q = (
        select(Finding.source_platform, func.count(Finding.id))
        .where(Finding.is_deleted == False)
        .group_by(Finding.source_platform)
        .order_by(func.count(Finding.id).desc())
        .limit(10)
    )
    platform_rows = (await db.execute(platform_q)).all()
    by_platform = {row[0]: row[1] for row in platform_rows}

    category_q = (
        select(Finding.category, func.count(Finding.id))
        .where(Finding.is_deleted == False)
        .group_by(Finding.category)
    )
    category_rows = (await db.execute(category_q)).all()
    by_category = {row[0]: row[1] for row in category_rows}

    status_q = (
        select(Finding.resolution_status, func.count(Finding.id))
        .where(Finding.is_deleted == False)
        .group_by(Finding.resolution_status)
    )
    status_rows = (await db.execute(status_q)).all()
    by_status = {row[0]: row[1] for row in status_rows}

    last_scan_q = select(Scan).order_by(Scan.id.desc()).limit(1)
    last_scan_row = (await db.execute(last_scan_q)).scalar_one_or_none()

    last_scan = None
    if last_scan_row:
        last_scan = {
            "id": last_scan_row.id,
            "started_at": last_scan_row.started_at.isoformat() if last_scan_row.started_at else None,
            "finished_at": last_scan_row.finished_at.isoformat() if last_scan_row.finished_at else None,
            "status": last_scan_row.status,
            "total_urls_found": last_scan_row.total_urls_found,
            "total_findings": last_scan_row.total_findings,
            "progress_phase": last_scan_row.progress_phase,
            "progress_current": last_scan_row.progress_current,
            "progress_total": last_scan_row.progress_total,
        }

    return {
        "total_findings": total,
        "by_risk": by_risk,
        "by_platform": by_platform,
        "by_category": by_category,
        "by_status": by_status,
        "last_scan": last_scan,
    }
