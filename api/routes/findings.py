import json
import logging
from math import ceil

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Finding

logger = logging.getLogger(__name__)

router = APIRouter(tags=["findings"])


class StatusUpdate(BaseModel):
    status: str


def _serialize_finding(f: Finding) -> dict:
    try:
        snippets_data = json.loads(f.snippets) if f.snippets else []
    except (json.JSONDecodeError, TypeError):
        snippets_data = []

    try:
        terms_data = json.loads(f.sensitive_terms) if f.sensitive_terms else []
    except (json.JSONDecodeError, TypeError):
        terms_data = []

    try:
        meta_data = json.loads(f.doc_metadata) if f.doc_metadata else {}
    except (json.JSONDecodeError, TypeError):
        meta_data = {}

    return {
        "id": f.id,
        "scan_id": f.scan_id,
        "discovered_at": f.discovered_at.isoformat() if f.discovered_at else None,
        "source_platform": f.source_platform,
        "url": f.url,
        "title": f.title,
        "file_type": f.file_type,
        "risk_level": f.risk_level,
        "risk_score": f.risk_score,
        "category": f.category,
        "entity_matched": f.entity_matched,
        "cpf_count": f.cpf_count,
        "cnpj_count": f.cnpj_count,
        "financial_count": f.financial_count,
        "sensitive_terms": terms_data,
        "snippets": snippets_data,
        "author": f.author or "",
        "publisher": f.publisher or "",
        "country": f.country or "INT",
        "language": f.language or "unknown",
        "doc_metadata": meta_data,
        "resolution_status": f.resolution_status,
        "analyst_notes": f.analyst_notes,
    }


@router.get("/findings")
async def list_findings(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk_level: str = Query("", description="Filter by risk"),
    status: str = Query("", description="Filter by status"),
    category: str = Query("", description="Filter by category"),
    country: str = Query("", description="Filter by country"),
    language: str = Query("", description="Filter by language"),
    db: AsyncSession = Depends(get_db),
):
    base = select(Finding).where(Finding.is_deleted == False)

    if risk_level:
        base = base.where(Finding.risk_level == risk_level)
    if status:
        base = base.where(Finding.resolution_status == status)
    if category:
        base = base.where(Finding.category == category)
    if country:
        base = base.where(Finding.country == country)
    if language:
        base = base.where(Finding.language == language)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    pages = ceil(total / per_page) if total > 0 else 1

    query = base.order_by(Finding.risk_score.desc(), Finding.id.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(query)).scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "findings": [_serialize_finding(f) for f in rows],
    }


@router.patch("/findings/{finding_id}/status")
async def update_finding_status(
    finding_id: int,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()

    if not finding:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.resolution_status = body.status
    await db.commit()

    return {"id": finding.id, "status": finding.resolution_status}


@router.delete("/findings/{finding_id}")
async def soft_delete_finding(
    finding_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()

    if not finding:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.is_deleted = True
    await db.commit()

    return {"id": finding.id, "deleted": True}
