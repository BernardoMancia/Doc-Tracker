import logging
import asyncio
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from sqlalchemy import select, func

from config.settings import settings
from core.database import async_session
from core.models import Finding, Scan

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))

RISK_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
RISK_PT = {"critical": "CRÍTICO", "high": "ALTO", "medium": "MÉDIO", "low": "BAIXO"}
STATUS_PT = {
    "pending": "⏳ Pendente",
    "investigating": "🔍 Investigando",
    "false_positive": "🚫 Falso Positivo",
    "auto_false_positive": "🤖 FP Automático",
    "resolved": "✅ Resolvido",
    "notified": "📨 Notificado",
}


def _authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = str(update.effective_chat.id)
        if settings.telegram_chat_id and chat_id != settings.telegram_chat_id:
            await update.message.reply_text("⛔ Acesso não autorizado.")
            return
        return await func(update, context)
    return wrapper


@_authorized
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("⏳ Pendentes", callback_data="pendentes")],
        [InlineKeyboardButton("🔴 Críticos", callback_data="criticos"),
         InlineKeyboardButton("📋 Relatório", callback_data="relatorio")],
        [InlineKeyboardButton("🔄 Iniciar Scan", callback_data="scan")],
    ]
    await update.message.reply_text(
        "🛡️ *OSINT & DLP — Grupo Roullier*\n\n"
        "Escolha uma opção abaixo ou use os comandos:\n"
        "`/status` — Resumo geral\n"
        "`/pendentes` — Findings pendentes\n"
        "`/criticos` — Findings críticos\n"
        "`/buscar <termo>` — Buscar por URL/entidade\n"
        "`/marcar <id> <status>` — Alterar status\n"
        "`/scan` — Disparar scan manual\n"
        "`/relatorio` — Relatório consolidado",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@_authorized
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with async_session() as db:
        total = (await db.execute(
            select(func.count(Finding.id)).where(Finding.is_deleted == False)
        )).scalar() or 0

        risk_q = (
            select(Finding.risk_level, func.count(Finding.id))
            .where(Finding.is_deleted == False)
            .group_by(Finding.risk_level)
        )
        risk_rows = (await db.execute(risk_q)).all()
        by_risk = {r[0]: r[1] for r in risk_rows}

        status_q = (
            select(Finding.resolution_status, func.count(Finding.id))
            .where(Finding.is_deleted == False)
            .group_by(Finding.resolution_status)
        )
        status_rows = (await db.execute(status_q)).all()
        by_status = {}
        for r in status_rows:
            key = r[0] or "pending"
            by_status[key] = by_status.get(key, 0) + r[1]

        last_scan = (await db.execute(
            select(Scan).order_by(Scan.id.desc()).limit(1)
        )).scalar_one_or_none()

    last_str = "Nenhum"
    if last_scan and last_scan.finished_at:
        last_str = last_scan.finished_at.strftime("%d/%m/%Y %H:%M")

    msg = (
        f"📊 *Status do Sistema*\n\n"
        f"📋 *Total:* {total}\n"
        f"🔴 Crítico: {by_risk.get('critical', 0)} | "
        f"🟠 Alto: {by_risk.get('high', 0)}\n"
        f"🟡 Médio: {by_risk.get('medium', 0)} | "
        f"🟢 Baixo: {by_risk.get('low', 0)}\n\n"
        f"⏳ Pendente: {by_status.get('pending', 0)}\n"
        f"🔍 Investigando: {by_status.get('investigating', 0)}\n"
        f"🚫 FP Manual: {by_status.get('false_positive', 0)}\n"
        f"🤖 FP Auto: {by_status.get('auto_false_positive', 0)}\n"
        f"✅ Resolvido: {by_status.get('resolved', 0)}\n"
        f"📨 Notificado: {by_status.get('notified', 0)}\n\n"
        f"🕐 Último scan: {last_str}\n"
        f"📊 [Dashboard]({settings.dashboard_url})"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)


@_authorized
async def cmd_pendentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _list_by_status(update, "pending", "⏳ Pendentes")


@_authorized
async def cmd_criticos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _list_by_risk(update, "critical", "🔴 Críticos")


async def _list_by_status(update: Update, status: str, label: str):
    async with async_session() as db:
        rows = (await db.execute(
            select(Finding)
            .where(Finding.is_deleted == False, Finding.resolution_status == status)
            .order_by(Finding.risk_score.desc())
            .limit(10)
        )).scalars().all()

    if not rows:
        text = f"{label}\n\nNenhum finding encontrado."
    else:
        text = f"{label} (últimos 10)\n\n"
        for f in rows:
            emoji = RISK_EMOJI.get(f.risk_level, "⚪")
            title = (f.title or "Sem título")[:50]
            text += f"{emoji} *#{f.id}* | {title}\n`{f.url[:60]}`\n\n"

    target = update.message or update.callback_query.message
    await target.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


async def _list_by_risk(update: Update, risk: str, label: str):
    async with async_session() as db:
        rows = (await db.execute(
            select(Finding)
            .where(Finding.is_deleted == False, Finding.risk_level == risk)
            .order_by(Finding.id.desc())
            .limit(10)
        )).scalars().all()

    if not rows:
        text = f"{label}\n\nNenhum finding encontrado."
    else:
        text = f"{label} (últimos 10)\n\n"
        for f in rows:
            st = STATUS_PT.get(f.resolution_status, f.resolution_status or "")
            title = (f.title or "Sem título")[:50]
            text += f"*#{f.id}* | {st}\n{title}\n`{f.url[:60]}`\n\n"

    target = update.message or update.callback_query.message
    await target.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


@_authorized
async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: `/buscar <termo>`", parse_mode="Markdown")
        return

    termo = " ".join(context.args)
    async with async_session() as db:
        rows = (await db.execute(
            select(Finding)
            .where(
                Finding.is_deleted == False,
                (Finding.url.ilike(f"%{termo}%")) | (Finding.entity_matched.ilike(f"%{termo}%")) | (Finding.title.ilike(f"%{termo}%"))
            )
            .order_by(Finding.risk_score.desc())
            .limit(10)
        )).scalars().all()

    if not rows:
        await update.message.reply_text(f"🔍 Nenhum resultado para: `{termo}`", parse_mode="Markdown")
        return

    text = f"🔍 Resultados para: *{termo}* ({len(rows)})\n\n"
    for f in rows:
        emoji = RISK_EMOJI.get(f.risk_level, "⚪")
        text += f"{emoji} *#{f.id}* | {(f.title or '')[:40]}\n`{f.url[:60]}`\n\n"

    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)


@_authorized
async def cmd_marcar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valid_statuses = ["pending", "investigating", "false_positive", "resolved", "notified"]
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/marcar <id> <status>`\n\n"
            "Status válidos:\n"
            "• `pending` — Pendente\n"
            "• `investigating` — Investigando\n"
            "• `false_positive` — Falso Positivo\n"
            "• `resolved` — Resolvido\n"
            "• `notified` — Notificado",
            parse_mode="Markdown",
        )
        return

    try:
        finding_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido.")
        return

    new_status = context.args[1].lower()
    if new_status not in valid_statuses:
        await update.message.reply_text(f"❌ Status inválido: `{new_status}`", parse_mode="Markdown")
        return

    async with async_session() as db:
        result = await db.execute(select(Finding).where(Finding.id == finding_id))
        finding = result.scalar_one_or_none()
        if not finding:
            await update.message.reply_text(f"❌ Finding #{finding_id} não encontrado.")
            return

        old_status = finding.resolution_status
        finding.resolution_status = new_status
        await db.commit()

    await update.message.reply_text(
        f"✅ Finding *#{finding_id}* atualizado\n"
        f"De: {STATUS_PT.get(old_status, old_status)}\n"
        f"Para: {STATUS_PT.get(new_status, new_status)}",
        parse_mode="Markdown",
    )


@_authorized
async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from api.routes.scans import _run_scan

    target = update.message or update.callback_query.message
    await target.reply_text("🔄 Scan manual iniciado... Alertas serão enviados ao concluir.")
    asyncio.create_task(_run_scan(silent=False))


@_authorized
async def cmd_relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await generate_report_text()
    target = update.message or update.callback_query.message
    await target.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)


async def generate_report_text() -> str:
    async with async_session() as db:
        total = (await db.execute(
            select(func.count(Finding.id)).where(Finding.is_deleted == False)
        )).scalar() or 0

        risk_q = (
            select(Finding.risk_level, func.count(Finding.id))
            .where(Finding.is_deleted == False)
            .group_by(Finding.risk_level)
        )
        by_risk = {r[0]: r[1] for r in (await db.execute(risk_q)).all()}

        status_q = (
            select(Finding.resolution_status, func.count(Finding.id))
            .where(Finding.is_deleted == False)
            .group_by(Finding.resolution_status)
        )
        by_status = {}
        for r in (await db.execute(status_q)).all():
            key = r[0] or "pending"
            by_status[key] = by_status.get(key, 0) + r[1]

        last_scan = (await db.execute(
            select(Scan).order_by(Scan.id.desc()).limit(1)
        )).scalar_one_or_none()

    now = datetime.now(BRT).strftime("%d/%m/%Y %H:%M")
    last_str = "N/A"
    if last_scan and last_scan.finished_at:
        last_str = last_scan.finished_at.strftime("%d/%m/%Y %H:%M")

    return (
        f"📊 *RELATÓRIO OSINT/DLP — Grupo Roullier*\n"
        f"📅 *Gerado em:* {now} BRT\n\n"
        f"📋 *Total de findings:* {total}\n\n"
        f"*Distribuição por Risco:*\n"
        f"🔴 Crítico: {by_risk.get('critical', 0)}\n"
        f"🟠 Alto: {by_risk.get('high', 0)}\n"
        f"🟡 Médio: {by_risk.get('medium', 0)}\n"
        f"🟢 Baixo: {by_risk.get('low', 0)}\n\n"
        f"*Distribuição por Status:*\n"
        f"⏳ Pendente: {by_status.get('pending', 0)}\n"
        f"🔍 Investigando: {by_status.get('investigating', 0)}\n"
        f"🚫 FP Manual: {by_status.get('false_positive', 0)}\n"
        f"🤖 FP Auto: {by_status.get('auto_false_positive', 0)}\n"
        f"✅ Resolvido: {by_status.get('resolved', 0)}\n"
        f"📨 Notificado: {by_status.get('notified', 0)}\n\n"
        f"🕐 Último scan: {last_str}\n"
        f"📊 [Dashboard]({settings.dashboard_url})"
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "status":
        await cmd_status(update, context)
    elif query.data == "pendentes":
        await cmd_pendentes(update, context)
    elif query.data == "criticos":
        await cmd_criticos(update, context)
    elif query.data == "relatorio":
        await cmd_relatorio(update, context)
    elif query.data == "scan":
        await cmd_scan(update, context)


def create_bot_app() -> Application:
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return None

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pendentes", cmd_pendentes))
    app.add_handler(CommandHandler("criticos", cmd_criticos))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("marcar", cmd_marcar))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("relatorio", cmd_relatorio))
    app.add_handler(CallbackQueryHandler(callback_handler))

    return app


async def run_bot():
    app = create_bot_app()
    if not app:
        return
    logger.info("Telegram bot starting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot running")
