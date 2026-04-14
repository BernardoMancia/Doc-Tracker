import json
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_urls_found: Mapped[int] = mapped_column(Integer, default=0)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    dorks_used: Mapped[str] = mapped_column(Text, default="[]")
    progress_phase: Mapped[str] = mapped_column(String(30), default="starting")
    progress_current: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)

    def set_dorks(self, dorks: list[str]):
        self.dorks_used = json.dumps(dorks, ensure_ascii=False)

    def get_dorks(self) -> list[str]:
        return json.loads(self.dorks_used)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    source_platform: Mapped[str] = mapped_column(String(100), default="unknown")
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, default="")
    file_type: Mapped[str] = mapped_column(String(10), default="unknown")
    risk_level: Mapped[str] = mapped_column(String(20), default="low", index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(50), default="general")
    entity_matched: Mapped[str] = mapped_column(Text, default="")
    cpf_count: Mapped[int] = mapped_column(Integer, default=0)
    cnpj_count: Mapped[int] = mapped_column(Integer, default=0)
    financial_count: Mapped[int] = mapped_column(Integer, default=0)
    sensitive_terms: Mapped[str] = mapped_column(Text, default="[]")
    snippets: Mapped[str] = mapped_column(Text, default="[]")
    author: Mapped[str] = mapped_column(String(200), default="")
    publisher: Mapped[str] = mapped_column(String(200), default="")
    country: Mapped[str] = mapped_column(String(10), default="INT")
    language: Mapped[str] = mapped_column(String(10), default="unknown")
    doc_metadata: Mapped[str] = mapped_column(Text, default="{}")
    resolution_status: Mapped[str] = mapped_column(
        String(30), default="pending", index=True
    )
    analyst_notes: Mapped[str] = mapped_column(Text, default="")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_sensitive_terms(self, terms: list[str]):
        self.sensitive_terms = json.dumps(terms, ensure_ascii=False)

    def get_sensitive_terms(self) -> list[str]:
        return json.loads(self.sensitive_terms)

    def set_snippets(self, snippets: list[dict]):
        self.snippets = json.dumps(snippets, ensure_ascii=False)

    def get_snippets(self) -> list[dict]:
        return json.loads(self.snippets)
