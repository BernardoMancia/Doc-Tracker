import asyncio
import csv
import json
import logging
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.intelligence_matrix import IntelligenceMatrix
from crawler.dork_generator import DorkGenerator
from crawler.search_engine import SearchEngine
from crawler.url_filter import URLFilter, detect_country, detect_language
from inspector.downloader import Downloader
from inspector.extractor import TextExtractor
from inspector.regex_engine import RegexEngine
from inspector.risk_classifier import RiskClassifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


RISK_COLORS = {
    "critical": "#ff3b5c",
    "high": "#ff9f43",
    "medium": "#feca57",
    "low": "#06d6a0",
}
COUNTRY_FLAGS = {
    "BR": "🇧🇷", "PT": "🇵🇹", "FR": "🇫🇷", "US": "🇺🇸",
    "DE": "🇩🇪", "ES": "🇪🇸", "GB": "🇬🇧", "INT": "🌐",
}
LANG_LABELS = {"pt": "PT", "en": "EN", "es": "ES", "fr": "FR", "unknown": "??"}

BG_PRIMARY = "#0a0e17"
BG_CARD = "#111827"
BG_INPUT = "#1e293b"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
ACCENT = "#06d6a0"
ACCENT_BLUE = "#3b82f6"


class DesktopApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OSINT & DLP — Consulta Rápida")
        self.root.geometry("1300x780")
        self.root.configure(bg=BG_PRIMARY)
        self.root.minsize(1000, 650)

        self.scan_running = False
        self.results = []

        self._build_styles()
        self._build_ui()

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TFrame", background=BG_PRIMARY)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("Header.TLabel", background=BG_PRIMARY, foreground=ACCENT, font=("Inter", 18, "bold"))
        style.configure("Sub.TLabel", background=BG_PRIMARY, foreground=TEXT_MUTED, font=("Inter", 10))
        style.configure("Status.TLabel", background=BG_PRIMARY, foreground=TEXT_SECONDARY, font=("JetBrains Mono", 10))
        style.configure("Scan.TButton", font=("Inter", 12, "bold"), padding=(20, 10))
        style.configure("Dark.Horizontal.TProgressbar", troughcolor=BG_INPUT, background=ACCENT)
        style.configure("Treeview",
            background=BG_CARD, foreground=TEXT_PRIMARY, fieldbackground=BG_CARD,
            font=("Inter", 10), rowheight=30,
        )
        style.configure("Treeview.Heading",
            background=BG_INPUT, foreground=TEXT_MUTED, font=("Inter", 9, "bold"),
        )
        style.map("Treeview",
            background=[("selected", "#1e3a5f")],
            foreground=[("selected", TEXT_PRIMARY)],
        )

    def _build_ui(self):
        header = ttk.Frame(self.root, style="Dark.TFrame")
        header.pack(fill=tk.X, padx=20, pady=(15, 5))

        ttk.Label(header, text="🛡️ OSINT & DLP — Consulta Desktop", style="Header.TLabel").pack(side=tk.LEFT)

        self.btn_scan = tk.Button(
            header, text="🔍  Consultar Agora", font=("Inter", 12, "bold"),
            bg=ACCENT, fg=BG_PRIMARY, activebackground=ACCENT_BLUE,
            activeforeground=BG_PRIMARY, bd=0, padx=20, pady=8,
            cursor="hand2", command=self._start_scan,
        )
        self.btn_scan.pack(side=tk.RIGHT)

        self.btn_export = tk.Button(
            header, text="💾 Exportar CSV", font=("Inter", 10),
            bg=BG_INPUT, fg=TEXT_SECONDARY, activebackground=BG_CARD,
            bd=0, padx=12, pady=6, cursor="hand2", command=self._export_csv,
        )
        self.btn_export.pack(side=tk.RIGHT, padx=(0, 10))

        progress_frame = ttk.Frame(self.root, style="Dark.TFrame")
        progress_frame.pack(fill=tk.X, padx=20, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var,
            maximum=100, style="Dark.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 2))

        info_frame = ttk.Frame(progress_frame, style="Dark.TFrame")
        info_frame.pack(fill=tk.X)
        self.lbl_phase = ttk.Label(info_frame, text="Pronto para consultar", style="Status.TLabel")
        self.lbl_phase.pack(side=tk.LEFT)
        self.lbl_percent = ttk.Label(info_frame, text="0%", style="Status.TLabel")
        self.lbl_percent.pack(side=tk.RIGHT)

        metrics_frame = ttk.Frame(self.root, style="Dark.TFrame")
        metrics_frame.pack(fill=tk.X, padx=20, pady=5)

        self.metric_labels = {}
        for name, color, label in [
            ("total", ACCENT, "TOTAL"),
            ("critical", RISK_COLORS["critical"], "CRÍTICO"),
            ("high", RISK_COLORS["high"], "ALTO"),
            ("medium", RISK_COLORS["medium"], "MÉDIO"),
            ("low", RISK_COLORS["low"], "BAIXO"),
        ]:
            card = tk.Frame(metrics_frame, bg=BG_CARD, padx=15, pady=8, highlightthickness=1, highlightbackground="#1e293b")
            card.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
            val_lbl = tk.Label(card, text="0", font=("JetBrains Mono", 22, "bold"), bg=BG_CARD, fg=color)
            val_lbl.pack()
            tk.Label(card, text=label, font=("Inter", 9), bg=BG_CARD, fg=TEXT_MUTED).pack()
            self.metric_labels[name] = val_lbl

        tree_frame = ttk.Frame(self.root, style="Dark.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        columns = ("score", "risk", "country", "lang", "entity", "platform", "title", "type", "author", "cpfs", "cnpjs", "category")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("score", text="SCORE")
        self.tree.heading("risk", text="RISCO")
        self.tree.heading("country", text="PAÍS")
        self.tree.heading("lang", text="IDIOMA")
        self.tree.heading("entity", text="ENTIDADE")
        self.tree.heading("platform", text="FONTE")
        self.tree.heading("title", text="TÍTULO")
        self.tree.heading("type", text="TIPO")
        self.tree.heading("author", text="AUTOR")
        self.tree.heading("cpfs", text="CPFS")
        self.tree.heading("cnpjs", text="CNPJS")
        self.tree.heading("category", text="CATEGORIA")

        self.tree.column("score", width=55, anchor=tk.CENTER)
        self.tree.column("risk", width=65, anchor=tk.CENTER)
        self.tree.column("country", width=50, anchor=tk.CENTER)
        self.tree.column("lang", width=50, anchor=tk.CENTER)
        self.tree.column("entity", width=130)
        self.tree.column("platform", width=75)
        self.tree.column("title", width=230)
        self.tree.column("type", width=55, anchor=tk.CENTER)
        self.tree.column("author", width=110)
        self.tree.column("cpfs", width=45, anchor=tk.CENTER)
        self.tree.column("cnpjs", width=50, anchor=tk.CENTER)
        self.tree.column("category", width=90)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure("critical", foreground=RISK_COLORS["critical"])
        self.tree.tag_configure("high", foreground=RISK_COLORS["high"])
        self.tree.tag_configure("medium", foreground=RISK_COLORS["medium"])
        self.tree.tag_configure("low", foreground=RISK_COLORS["low"])

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.detail_frame = tk.Frame(self.root, bg=BG_CARD, padx=15, pady=10)
        self.detail_text = tk.Text(
            self.detail_frame, bg=BG_CARD, fg=TEXT_PRIMARY,
            font=("JetBrains Mono", 10), wrap=tk.WORD, height=6,
            bd=0, highlightthickness=0, insertbackground=TEXT_PRIMARY,
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        status_bar = tk.Frame(self.root, bg=BG_INPUT, height=25)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.lbl_status = tk.Label(status_bar, text="Grupo Roullier — Threat Monitor Desktop", font=("Inter", 9), bg=BG_INPUT, fg=TEXT_MUTED, padx=10)
        self.lbl_status.pack(side=tk.LEFT)

    def _start_scan(self):
        if self.scan_running:
            return
        self.scan_running = True
        self.btn_scan.configure(state=tk.DISABLED, text="⏳ Consultando...")
        self.results = []
        self.tree.delete(*self.tree.get_children())
        self.progress_var.set(0)
        self._update_metrics()

        thread = threading.Thread(target=self._run_scan_thread, daemon=True)
        thread.start()

    def _run_scan_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._scan_async())
        except Exception as e:
            logger.exception("Scan error: %s", e)
            self.root.after(0, lambda: self._update_phase(f"Erro: {e}"))
        finally:
            loop.close()
            self.root.after(0, self._scan_finished)

    async def _scan_async(self):
        matrix = IntelligenceMatrix()
        generator = DorkGenerator(matrix)
        url_filter = URLFilter(matrix)
        search = SearchEngine(url_filter)
        downloader = Downloader()
        extractor = TextExtractor()
        regex_engine = RegexEngine(matrix)
        classifier = RiskClassifier(matrix)

        dorks = generator.generate_all()
        total_dorks = len(dorks)
        self.root.after(0, lambda: self._update_phase(f"Buscando... 0/{total_dorks} dorks"))

        all_discovered = []
        for i, dork in enumerate(dorks):
            pct = int(((i + 1) / total_dorks) * 50)
            self.root.after(0, lambda p=pct, idx=i+1: self._update_progress(p, f"Buscando... {idx}/{total_dorks} dorks"))
            results = await search._search_single_dork(dork)
            all_discovered.extend(results)
            import random
            await asyncio.sleep(random.uniform(2.0, 4.0))

        seen_urls = set()
        total_urls = len(all_discovered)
        self.root.after(0, lambda: self._update_phase(f"Analisando... 0/{total_urls} URLs"))

        for i, item in enumerate(all_discovered):
            pct = 50 + int(((i + 1) / max(total_urls, 1)) * 50)
            self.root.after(0, lambda p=pct, idx=i+1: self._update_progress(p, f"Analisando... {idx}/{total_urls} URLs"))

            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)

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
            country = detect_country(item.url)
            language = detect_language(extraction.text)

            doc_author = extraction.metadata.get("author", "")
            doc_creator = extraction.metadata.get("creator", "")
            doc_publisher = doc_creator if doc_creator and doc_creator != doc_author else ""

            finding = {
                "url": item.url,
                "title": item.title,
                "file_type": file_type,
                "risk_level": risk.level,
                "risk_score": risk.score,
                "category": risk.category,
                "entity_matched": ", ".join(inspection.entity_matches[:5]),
                "source_platform": platform,
                "cpf_count": inspection.cpf_count,
                "cnpj_count": inspection.cnpj_count,
                "financial_count": inspection.financial_count,
                "author": doc_author,
                "publisher": doc_publisher,
                "country": country,
                "language": language,
                "snippets": inspection.snippets,
                "reasons": risk.reasons,
                "sensitive_terms": inspection.sensitive_term_matches,
            }
            self.results.append(finding)
            self.root.after(0, lambda f=finding: self._add_finding_to_tree(f))

            download_result.data.close()

        await downloader.close()

    def _add_finding_to_tree(self, f):
        risk_label = {"critical": "CRÍTICO", "high": "ALTO", "medium": "MÉDIO", "low": "BAIXO"}.get(f["risk_level"], "")
        cat_label = {"rh": "RH", "financeiro": "Financeiro", "ti": "TI", "ti_security": "TI/Seg",
                     "dados_pessoais": "Dados", "corporativo": "Corp", "general": "Geral"}.get(f["category"], f["category"])
        flag = COUNTRY_FLAGS.get(f["country"], "🌐")
        lang = LANG_LABELS.get(f["language"], "??")
        self.tree.insert("", 0, values=(
            f["risk_score"], risk_label,
            f"{flag} {f['country']}",
            lang,
            f["entity_matched"][:25] if f["entity_matched"] else "—",
            f["source_platform"],
            f["title"][:35] if f["title"] else "—",
            f["file_type"].upper(),
            f["author"][:18] if f["author"] else "—",
            f["cpf_count"] or "—",
            f["cnpj_count"] or "—",
            cat_label,
        ), tags=(f["risk_level"],))
        self._update_metrics()

    def _update_metrics(self):
        total = len(self.results)
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in self.results:
            if r["risk_level"] in counts:
                counts[r["risk_level"]] += 1
        self.metric_labels["total"].configure(text=str(total))
        for key in counts:
            self.metric_labels[key].configure(text=str(counts[key]))

    def _update_progress(self, pct, text):
        self.progress_var.set(pct)
        self.lbl_percent.configure(text=f"{pct}%")
        self.lbl_phase.configure(text=text)

    def _update_phase(self, text):
        self.lbl_phase.configure(text=text)

    def _scan_finished(self):
        self.scan_running = False
        self.btn_scan.configure(state=tk.NORMAL, text="🔍  Consultar Agora")
        self.progress_var.set(100)
        self.lbl_percent.configure(text="100%")
        self.lbl_phase.configure(text=f"Concluído — {len(self.results)} findings")
        self.lbl_status.configure(text=f"Última consulta: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        reverse_idx = len(self.results) - 1 - idx
        if 0 <= reverse_idx < len(self.results):
            f = self.results[reverse_idx]
            self._show_detail(f)

    def _show_detail(self, f):
        if not self.detail_frame.winfo_ismapped():
            self.detail_frame.pack(fill=tk.X, padx=20, pady=(0, 5), before=self.root.winfo_children()[-1])

        self.detail_text.configure(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        lang_labels = {"pt": "Português", "en": "Inglês", "es": "Espanhol", "fr": "Francês", "unknown": "Indefinido"}
        flag = COUNTRY_FLAGS.get(f["country"], "🌐")
        lines = [
            f"{'='*60}",
            f"TÍTULO: {f['title']}",
            f"URL: {f['url']}",
            f"SCORE: {f['risk_score']} | RISCO: {f['risk_level'].upper()} | CATEGORIA: {f['category']}",
            f"ENTIDADE: {f['entity_matched']}",
            f"PAÍS: {flag} {f['country']} | IDIOMA: {lang_labels.get(f['language'], f['language'])}",
        ]
        if f.get("author"):
            lines.append(f"AUTOR: {f['author']}")
        if f.get("publisher"):
            lines.append(f"PUBLICADOR: {f['publisher']}")
        lines.extend([
            f"CPFs: {f['cpf_count']} | CNPJs: {f['cnpj_count']} | FINANCEIROS: {f['financial_count']}",
            f"PLATAFORMA: {f['source_platform']} | TIPO: {f['file_type'].upper()}",
        ])
        if f.get("reasons"):
            lines.append(f"RAZÕES: {', '.join(f['reasons'])}")
        if f.get("sensitive_terms"):
            lines.append(f"TERMOS: {', '.join(f['sensitive_terms'][:10])}")
        lines.append(f"{'='*60}")
        self.detail_text.insert("1.0", "\n".join(lines))
        self.detail_text.configure(state=tk.DISABLED)

    def _export_csv(self):
        if not self.results:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"osint_findings_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        )
        if not path:
            return

        fields = [
            "risk_score", "risk_level", "country", "language",
            "entity_matched", "source_platform", "title", "file_type",
            "author", "publisher", "cpf_count", "cnpj_count",
            "financial_count", "category", "url",
        ]
        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self.results)

        self.lbl_status.configure(text=f"Exportado: {path}")

    def run(self):
        self.root.mainloop()


def main():
    app = DesktopApp()
    app.run()


if __name__ == "__main__":
    main()
