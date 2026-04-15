import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import select, update, text
from core.database import async_session, init_db
from core.models import Finding
from crawler.url_filter import URLFilter


async def migrate():
    await init_db()
    url_filter = URLFilter()

    async with async_session() as db:
        null_result = await db.execute(
            update(Finding)
            .where(Finding.resolution_status.is_(None))
            .values(resolution_status="pending")
        )
        print(f"[*] {null_result.rowcount} findings com status NULL -> 'pending'")

        all_findings = (await db.execute(
            select(Finding).where(Finding.is_deleted == False)
        )).scalars().all()

        print(f"[*] Analisando {len(all_findings)} findings existentes...")

        fp_count = 0
        for f in all_findings:
            if f.resolution_status == "false_positive":
                continue

            reason = url_filter.is_auto_false_positive(f.url)
            if reason:
                f.resolution_status = "false_positive"
                f.analyst_notes = f"Auto-classified (migration): {reason}"
                fp_count += 1
                print(f"  [FP] {f.url[:80]} -> {reason}")

        await db.commit()
        print(f"\n[+] {fp_count} findings marcados como false_positive")
        print(f"[+] Migração concluída!")


if __name__ == "__main__":
    asyncio.run(migrate())
