import sys
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import fitz

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "documentacao"
DOCS_DIR.mkdir(exist_ok=True)

COVER_COLOR = RGBColor(0x0A, 0x0E, 0x17)
ACCENT_COLOR = RGBColor(0x06, 0xD6, 0xA0)
HEADING_COLOR = RGBColor(0x1E, 0x40, 0xAF)
TEXT_COLOR = RGBColor(0x1F, 0x29, 0x37)


def set_cell_shading(cell, color_hex):
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def add_styled_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = HEADING_COLOR
    return h


def add_body(doc, text):
    p = doc.add_paragraph(text)
    p.style.font.size = Pt(11)
    p.style.font.color.rgb = TEXT_COLOR
    p.paragraph_format.space_after = Pt(6)
    return p


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
    for row_data in rows:
        row = table.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = str(val)
            for p in row.cells[i].paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
    return table


def build_pt():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\n\n\n\n\n")
    run.font.size = Pt(24)
    run = p.add_run("OSINT & DLP System")
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = HEADING_COLOR
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("Grupo Roullier — Documentação Técnica")
    run2.font.size = Pt(16)
    run2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = p3.add_run("Versão 2.1 | Confidencial — Uso Interno")
    run3.font.size = Pt(12)
    run3.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    doc.add_page_break()

    add_styled_heading(doc, "1. Visão Geral", 1)
    add_body(doc,
        "O OSINT & DLP System é uma plataforma automatizada de inteligência em fontes abertas (OSINT) "
        "e prevenção de vazamento de dados (DLP) desenvolvida exclusivamente para o Grupo Roullier. "
        "O sistema realiza varreduras contínuas na internet pública em busca de documentos, "
        "planilhas e arquivos que possam conter informações confidenciais das empresas do grupo, "
        "incluindo Timac Agro Brasil, Sulfabrás Sulfatos do Brasil e Phosphea Brasil."
    )
    add_body(doc,
        "O sistema opera em dois modos independentes: Server (dashboard web com monitoramento "
        "contínuo e alertas automáticos) e Desktop (aplicação standalone para consultas ad-hoc). "
        "Ambos compartilham o mesmo núcleo de lógica, garantindo resultados consistentes."
    )

    add_styled_heading(doc, "1.1 Objetivos", 2)
    for item in [
        "Detectar proativamente vazamentos de dados sensíveis em fontes públicas",
        "Identificar exposição de CPFs, CNPJs e informações financeiras",
        "Classificar e priorizar riscos por nível de criticidade",
        "Notificar automaticamente a equipe de segurança via Telegram",
        "Fornecer interface intuitiva para triagem e investigação de incidentes",
        "Manter histórico completo para auditoria e compliance",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "2. Arquitetura do Sistema", 1)
    add_body(doc,
        "O sistema é construído em Python 3.10+ e segue uma arquitetura modular organizada "
        "em camadas independentes. O core compartilhado (config, crawler, inspector) é utilizado "
        "tanto pelo Server quanto pelo Desktop."
    )

    add_styled_heading(doc, "2.1 Componentes Principais", 2)
    add_table(doc,
        ["Componente", "Descrição", "Tecnologia"],
        [
            ["config/", "Configurações e matriz de inteligência", "Pydantic Settings"],
            ["core/", "Modelos de dados e engine de banco", "SQLAlchemy Async + aiosqlite"],
            ["crawler/", "Geração de dorks e motor de busca", "DuckDuckGo Search (ddgs)"],
            ["inspector/", "Download, extração de texto, regex, classificação", "httpx, PyMuPDF, python-docx"],
            ["alerts/", "Webhooks para Telegram", "httpx"],
            ["api/", "Dashboard web e API REST", "FastAPI + Jinja2"],
            ["server/", "Entry point do modo servidor", "Uvicorn + APScheduler"],
            ["desktop/", "Interface gráfica standalone", "Tkinter"],
        ],
    )

    add_styled_heading(doc, "2.2 Fluxo de Operação", 2)
    steps = [
        ("Geração de Dorks", "O DorkGenerator cria ~80 consultas de busca otimizadas com base na Intelligence Matrix, cobrindo entidades, CNPJs, CPFs, fornecedores e termos sensíveis em múltiplas plataformas."),
        ("Varredura Web", "O SearchEngine executa cada dork via DuckDuckGo com delays randomizados (2-4s) para evasão de rate-limiting. Os resultados são filtrados pelo URLFilter para remover domínios oficiais."),
        ("Download em Memória", "O Downloader obtém cada documento diretamente em memória (BytesIO), sem gravação em disco, para minimizar a pegada forense."),
        ("Extração de Texto", "O TextExtractor processa PDF (PyMuPDF), DOCX (python-docx), XLSX (openpyxl) e TXT, extraindo texto completo e metadados (autor, criador, data)."),
        ("Inspeção por Regex", "O RegexEngine analisa o texto extraído em busca de CPFs, CNPJs, dados financeiros, entidades do grupo e termos sensíveis. Snippets são mascarados para proteger PII."),
        ("Classificação de Risco", "O RiskClassifier atribui um score numérico e nível (Crítico/Alto/Médio/Baixo) com base na quantidade e tipo de dados sensíveis encontrados."),
        ("Persistência e Alertas", "Os findings são salvos no banco SQLite com deduplicação por URL. Alertas são enviados via Telegram com resumo agrupado por risco."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        add_body(doc, f"{i}. {title}: {desc}")

    add_styled_heading(doc, "3. Intelligence Matrix", 1)
    add_body(doc,
        "A Intelligence Matrix é o coração da inteligência do sistema. Ela é carregada dinamicamente "
        "a partir do arquivo data/entities.json, que contém as entidades extraídas dos documentos "
        "cadastrais do grupo (fichas cadastrais, contratos sociais)."
    )

    add_styled_heading(doc, "3.1 Dados Monitorados", 2)
    add_table(doc,
        ["Tipo de Dado", "Exemplos", "Uso"],
        [
            ["Razões Sociais", "TIMAC AGRO INDÚSTRIA E COMÉRCIO DE FERTILIZANTES LTDA", "Dorks de busca"],
            ["CNPJs", "02.329.713/0001-29, 26.769.908/0001-58", "Regex de detecção"],
            ["CPFs", "Administradores e sócios", "Regex de detecção"],
            ["Fornecedores", "OCP Brasil, Pisani Plásticos", "Termos de busca"],
            ["Emails Corporativos", "nfe1@timacagro.com.br", "Detecção de exposição"],
            ["Termos Sensíveis", "confidencial, uso interno, senha", "Regex avançado"],
        ],
    )

    add_styled_heading(doc, "4. Detecção e Classificação", 1)

    add_styled_heading(doc, "4.1 Níveis de Risco", 2)
    add_table(doc,
        ["Nível", "Score", "Critérios"],
        [
            ["🔴 Crítico", "80-100", "Múltiplos CPFs + CNPJs + dados financeiros, ou CPFs expostos com contexto sensível"],
            ["🟠 Alto", "60-79", "CPFs ou CNPJs do grupo com termos financeiros"],
            ["🟡 Médio", "40-59", "Menção a entidades com termos sensíveis moderados"],
            ["🟢 Baixo", "1-39", "Menção genérica a entidades ou termos isolados"],
        ],
    )

    add_styled_heading(doc, "4.2 Categorias", 2)
    add_table(doc,
        ["Categoria", "Descrição"],
        [
            ["RH", "Dados de funcionários, folha de pagamento, CPFs em contexto trabalhista"],
            ["Financeiro", "Faturamento, balanços, contratos, dados bancários"],
            ["TI", "Infraestrutura, credenciais, configurações técnicas"],
            ["TI/Segurança", "Senhas, tokens, chaves de API, VPN"],
            ["Dados Pessoais", "CPFs, endereços, telefones sem contexto corporativo"],
            ["Corporativo", "Documentos estratégicos, propostas comerciais"],
        ],
    )

    add_styled_heading(doc, "4.3 Filtros Regionais", 2)
    add_body(doc,
        "O sistema detecta automaticamente o país de origem (por TLD do domínio) e o idioma "
        "do conteúdo (por análise textual), permitindo filtrar findings por região no dashboard."
    )

    add_styled_heading(doc, "5. Modos de Operação", 1)

    add_styled_heading(doc, "5.1 Modo Server", 2)
    add_body(doc,
        "O modo Server é a versão principal para ambientes de produção. Inclui dashboard web, "
        "API REST completa, agendamento automático de scans (3x/dia via APScheduler) e integração "
        "com Telegram para alertas em tempo real."
    )
    add_body(doc, "Funcionalidades exclusivas do Server:")
    for item in [
        "Dashboard web cybersecurity com métricas, gráficos e tabela de triagem",
        "Barra de progresso em tempo real durante scans",
        "Agendamento automático configurável (padrão: 08:00, 14:00, 22:00 BRT)",
        "Alertas Telegram: startup, início de scan e resumo com links novos",
        "API REST para integração com ferramentas externas",
        "SSE (Server-Sent Events) para push notifications no dashboard",
        "Execução como serviço systemd (Linux) para operação contínua",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "5.2 Modo Desktop", 2)
    add_body(doc,
        "O modo Desktop é uma aplicação GUI standalone construída com Tkinter. Projetada para "
        "consultas ad-hoc sem dependência de servidor ou infraestrutura web."
    )
    add_body(doc, "Funcionalidades:")
    for item in [
        "Interface gráfica dark mode com barra de progresso",
        "Exportação de resultados para CSV e JSON",
        "Operação totalmente offline após a busca inicial",
        "Compilável para .exe standalone via cx_Freeze",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "6. Instalação e Configuração", 1)

    add_styled_heading(doc, "6.1 Requisitos", 2)
    add_table(doc,
        ["Requisito", "Mínimo"],
        [
            ["Python", "3.10+"],
            ["Sistema Operacional", "Linux (Server) / Windows (Desktop/Server)"],
            ["RAM", "512 MB"],
            ["Disco", "100 MB + espaço para banco SQLite"],
            ["Rede", "Acesso à internet para crawling"],
        ],
    )

    add_styled_heading(doc, "6.2 Instalação", 2)
    add_body(doc, "1. Clonar o repositório:")
    doc.add_paragraph("git clone <repo-url>\ncd Doc-Tracker", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "2. Criar e ativar ambiente virtual:")
    doc.add_paragraph("python3 -m venv venv\nsource venv/bin/activate  # Linux\nvenv\\Scripts\\activate     # Windows", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "3. Instalar dependências:")
    doc.add_paragraph("pip install -r requirements.txt", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "4. Configurar variáveis de ambiente:")
    doc.add_paragraph("cp .env.example .env\nnano .env  # editar com valores reais", style="No Spacing").runs[0].font.name = "Consolas"

    add_styled_heading(doc, "6.3 Variáveis de Ambiente", 2)
    add_table(doc,
        ["Variável", "Descrição", "Obrigatória"],
        [
            ["DATABASE_URL", "URL de conexão SQLite", "Sim"],
            ["API_HOST", "Host do servidor (padrão: 0.0.0.0)", "Não"],
            ["API_PORT", "Porta do servidor (padrão: 8443)", "Não"],
            ["TELEGRAM_BOT_TOKEN", "Token do bot Telegram para alertas", "Sim*"],
            ["TELEGRAM_CHAT_ID", "ID do chat Telegram", "Sim*"],
            ["SCAN_SCHEDULE_HOURS", "Horários de scan automático (ex: 8,14,22)", "Não"],
            ["SERVER_MODE", "Ativar modo servidor (true/false)", "Não"],
            ["DASHBOARD_URL", "URL pública do dashboard", "Não"],
            ["PROXY_URL", "Proxy SOCKS5 para crawling", "Não"],
        ],
    )
    add_body(doc, "* Obrigatória apenas para receber alertas via Telegram.")

    add_styled_heading(doc, "6.4 Execução", 2)
    add_table(doc,
        ["Modo", "Comando", "Descrição"],
        [
            ["Desenvolvimento", "python run.py", "Servidor local sem scheduler"],
            ["Servidor", "python server/run_server.py", "Dashboard + Telegram + Auto-scan"],
            ["Desktop", "python desktop/run_desktop.py", "GUI standalone"],
            ["Build Desktop", "python setup_desktop.py build", "Gera executável .exe"],
        ],
    )

    add_styled_heading(doc, "6.5 Instalação como Serviço (Linux)", 2)
    add_body(doc,
        "Para manter o sistema rodando continuamente em um servidor Linux, utilize o arquivo "
        "de serviço systemd incluído no repositório (server/osint-dlp.service). "
        "Edite o arquivo para ajustar caminhos e usuário conforme seu ambiente."
    )
    add_body(doc, "Comandos de gerenciamento:")
    doc.add_paragraph(
        "sudo cp server/osint-dlp.service /etc/systemd/system/\n"
        "sudo systemctl daemon-reload\n"
        "sudo systemctl enable osint-dlp\n"
        "sudo systemctl start osint-dlp\n"
        "sudo systemctl status osint-dlp\n"
        "sudo journalctl -u osint-dlp -f",
        style="No Spacing"
    ).runs[0].font.name = "Consolas"

    add_styled_heading(doc, "7. API REST", 1)
    add_table(doc,
        ["Método", "Endpoint", "Descrição"],
        [
            ["GET", "/", "Dashboard HTML"],
            ["GET", "/api/dashboard", "Métricas agregadas (totais, por risco, por plataforma)"],
            ["GET", "/api/findings", "Listar findings (paginado, filtrável por risco/status/categoria/país/idioma)"],
            ["PATCH", "/api/findings/{id}/status", "Atualizar status do finding (investigating/resolved/false_positive)"],
            ["DELETE", "/api/findings/{id}", "Soft delete de finding"],
            ["GET", "/api/scans", "Histórico de scans"],
            ["POST", "/api/scans/trigger", "Disparar scan manual"],
            ["GET", "/api/scans/progress", "Progresso do scan atual"],
            ["GET", "/api/stream", "Stream SSE de eventos em tempo real"],
        ],
    )

    add_styled_heading(doc, "8. Dashboard Web", 1)
    add_body(doc,
        "O dashboard web apresenta uma interface moderna com tema dark mode, seguindo padrões "
        "de design de ferramentas de cybersecurity (glassmorphism, cores neon, gradientes)."
    )
    add_body(doc, "Seções do dashboard:")
    for item in [
        "Header: Status do sistema (Idle/Scanning), botão de scan manual",
        "Métricas: Cards com contadores por nível de risco",
        "Gráficos: Distribuição por risco (doughnut) e fontes de vazamento (barras horizontais)",
        "Tabela de Triagem: Lista filtráve de findings com colunas de risco, data, país, entidade, fonte, tipo, autor, CPFs, CNPJs, categoria e status",
        "Painel de Detalhes: Slide-in lateral com informações completas do finding selecionado",
        "Ações: Botões para classificar cada finding como Investigando, Falso Positivo, Resolvido ou Notificado",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "9. Segurança e Privacidade", 1)
    for item in [
        "Download em memória (zero disco): Os documentos são baixados em BytesIO e processados sem tocar o filesystem",
        "Mascaramento de PII: CPFs, CNPJs e emails nos snippets são mascarados antes da exibição (ex: ***.456.789-**)",
        "Domínios excluídos: Sites oficiais do grupo (timacagro.com.br, phosphea.com, roullier.com) são automaticamente excluídos da varredura",
        "Soft Delete: Dados nunca são removidos fisicamente do banco, apenas marcados como inativos",
        "Arquivo .env: Credenciais sensíveis são mantidas fora do repositório via .gitignore",
        "Delays de evasão: Intervalos randomizados entre requisições para evitar bloqueio por rate-limiting",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "10. Manutenção e Ingestão de Dados", 1)
    add_body(doc,
        "Para atualizar a base de entidades monitoradas, utilize o script de ingestão "
        "(tools/ingest_anexos.py). Coloque os PDFs cadastrais na pasta anexos/ na raiz "
        "do projeto e execute:"
    )
    doc.add_paragraph("python tools/ingest_anexos.py", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc,
        "O script extrai automaticamente razões sociais, CNPJs, CPFs, sócios, administradores, "
        "filiais, fornecedores e referências bancárias dos documentos, gerando o arquivo "
        "data/entities.json. Os PDFs são deletados após processamento."
    )

    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f = p_footer.add_run("\n\n— Documento Confidencial — Grupo Roullier Security Team —")
    run_f.font.size = Pt(9)
    run_f.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    return doc


def build_en():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("\n\n\n\n\n")
    run.font.size = Pt(24)
    run = p.add_run("OSINT & DLP System")
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = HEADING_COLOR
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("Roullier Group — Technical Documentation")
    run2.font.size = Pt(16)
    run2.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = p3.add_run("Version 2.1 | Confidential — Internal Use Only")
    run3.font.size = Pt(12)
    run3.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
    doc.add_page_break()

    add_styled_heading(doc, "1. Overview", 1)
    add_body(doc,
        "The OSINT & DLP System is an automated open-source intelligence (OSINT) and data leak "
        "prevention (DLP) platform developed exclusively for the Roullier Group. The system "
        "performs continuous scans across the public internet searching for documents, spreadsheets, "
        "and files that may contain confidential information from the group's companies, including "
        "Timac Agro Brasil, Sulfabrás Sulfatos do Brasil, and Phosphea Brasil."
    )
    add_body(doc,
        "The system operates in two independent modes: Server (web dashboard with continuous "
        "monitoring and automatic alerts) and Desktop (standalone application for ad-hoc queries). "
        "Both share the same core logic, ensuring consistent results."
    )

    add_styled_heading(doc, "1.1 Objectives", 2)
    for item in [
        "Proactively detect sensitive data leaks in public sources",
        "Identify exposure of CPFs (Brazilian SSN), CNPJs (company IDs), and financial data",
        "Classify and prioritize risks by criticality level",
        "Automatically notify the security team via Telegram",
        "Provide an intuitive interface for incident triage and investigation",
        "Maintain complete audit history for compliance purposes",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "2. System Architecture", 1)
    add_body(doc,
        "The system is built with Python 3.10+ and follows a modular architecture organized "
        "in independent layers. The shared core (config, crawler, inspector) is used by both "
        "the Server and Desktop modes."
    )

    add_styled_heading(doc, "2.1 Main Components", 2)
    add_table(doc,
        ["Component", "Description", "Technology"],
        [
            ["config/", "Settings and intelligence matrix", "Pydantic Settings"],
            ["core/", "Data models and database engine", "SQLAlchemy Async + aiosqlite"],
            ["crawler/", "Dork generation and search engine", "DuckDuckGo Search (ddgs)"],
            ["inspector/", "Download, text extraction, regex, classification", "httpx, PyMuPDF, python-docx"],
            ["alerts/", "Telegram webhooks", "httpx"],
            ["api/", "Web dashboard and REST API", "FastAPI + Jinja2"],
            ["server/", "Server mode entry point", "Uvicorn + APScheduler"],
            ["desktop/", "Standalone GUI interface", "Tkinter"],
        ],
    )

    add_styled_heading(doc, "2.2 Operation Flow", 2)
    steps = [
        ("Dork Generation", "The DorkGenerator creates ~80 optimized search queries based on the Intelligence Matrix, covering entities, CNPJs, CPFs, suppliers, and sensitive terms across multiple platforms."),
        ("Web Crawling", "The SearchEngine executes each dork via DuckDuckGo with randomized delays (2-4s) for rate-limiting evasion. Results are filtered by URLFilter to remove official domains."),
        ("In-Memory Download", "The Downloader fetches each document directly into memory (BytesIO), with zero disk writes, to minimize forensic footprint."),
        ("Text Extraction", "The TextExtractor processes PDF (PyMuPDF), DOCX (python-docx), XLSX (openpyxl), and TXT files, extracting full text and metadata (author, creator, date)."),
        ("Regex Inspection", "The RegexEngine analyzes extracted text for CPFs, CNPJs, financial data, group entities, and sensitive terms. Snippets are masked to protect PII."),
        ("Risk Classification", "The RiskClassifier assigns a numeric score and level (Critical/High/Medium/Low) based on the quantity and type of sensitive data found."),
        ("Persistence & Alerts", "Findings are saved to the SQLite database with URL-based deduplication. Alerts are sent via Telegram with a risk-grouped summary."),
    ]
    for i, (title, desc) in enumerate(steps, 1):
        add_body(doc, f"{i}. {title}: {desc}")

    add_styled_heading(doc, "3. Intelligence Matrix", 1)
    add_body(doc,
        "The Intelligence Matrix is the heart of the system's intelligence. It is dynamically "
        "loaded from the data/entities.json file, which contains entities extracted from the "
        "group's registration documents (corporate filings, articles of incorporation)."
    )

    add_styled_heading(doc, "3.1 Monitored Data Types", 2)
    add_table(doc,
        ["Data Type", "Examples", "Usage"],
        [
            ["Company Names", "TIMAC AGRO INDÚSTRIA E COMÉRCIO DE FERTILIZANTES LTDA", "Search dorks"],
            ["CNPJs", "02.329.713/0001-29, 26.769.908/0001-58", "Detection regex"],
            ["CPFs", "Administrators and partners", "Detection regex"],
            ["Suppliers", "OCP Brasil, Pisani Plásticos", "Search terms"],
            ["Corporate Emails", "nfe1@timacagro.com.br", "Exposure detection"],
            ["Sensitive Terms", "confidential, internal use, password", "Advanced regex"],
        ],
    )

    add_styled_heading(doc, "4. Detection and Classification", 1)

    add_styled_heading(doc, "4.1 Risk Levels", 2)
    add_table(doc,
        ["Level", "Score", "Criteria"],
        [
            ["🔴 Critical", "80-100", "Multiple CPFs + CNPJs + financial data, or exposed CPFs in sensitive context"],
            ["🟠 High", "60-79", "Group CPFs or CNPJs with financial terms"],
            ["🟡 Medium", "40-59", "Entity mentions with moderate sensitive terms"],
            ["🟢 Low", "1-39", "Generic entity mentions or isolated terms"],
        ],
    )

    add_styled_heading(doc, "4.2 Categories", 2)
    add_table(doc,
        ["Category", "Description"],
        [
            ["HR", "Employee data, payroll, CPFs in employment context"],
            ["Financial", "Revenue, balance sheets, contracts, banking data"],
            ["IT", "Infrastructure, credentials, technical configurations"],
            ["IT/Security", "Passwords, tokens, API keys, VPN"],
            ["Personal Data", "CPFs, addresses, phone numbers without corporate context"],
            ["Corporate", "Strategic documents, commercial proposals"],
        ],
    )

    add_styled_heading(doc, "4.3 Regional Filters", 2)
    add_body(doc,
        "The system automatically detects the country of origin (by domain TLD) and content "
        "language (by text analysis), allowing findings to be filtered by region on the dashboard."
    )

    add_styled_heading(doc, "5. Operation Modes", 1)

    add_styled_heading(doc, "5.1 Server Mode", 2)
    add_body(doc,
        "Server mode is the primary version for production environments. It includes a web "
        "dashboard, full REST API, automatic scan scheduling (3x/day via APScheduler), and "
        "Telegram integration for real-time alerts."
    )
    add_body(doc, "Server-exclusive features:")
    for item in [
        "Cybersecurity web dashboard with metrics, charts, and triage table",
        "Real-time progress bar during scans",
        "Configurable automatic scheduling (default: 08:00, 14:00, 22:00 BRT)",
        "Telegram alerts: startup, scan start, and summary with new leak links",
        "REST API for external tool integration",
        "SSE (Server-Sent Events) for real-time dashboard push notifications",
        "Systemd service for continuous operation on Linux servers",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "5.2 Desktop Mode", 2)
    add_body(doc,
        "Desktop mode is a standalone GUI application built with Tkinter. Designed for ad-hoc "
        "queries without server or web infrastructure dependencies."
    )
    add_body(doc, "Features:")
    for item in [
        "Dark mode graphical interface with progress bar",
        "Result export to CSV and JSON",
        "Fully offline operation after the initial scan",
        "Compilable to standalone .exe via cx_Freeze",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "6. Installation and Configuration", 1)

    add_styled_heading(doc, "6.1 Requirements", 2)
    add_table(doc,
        ["Requirement", "Minimum"],
        [
            ["Python", "3.10+"],
            ["Operating System", "Linux (Server) / Windows (Desktop/Server)"],
            ["RAM", "512 MB"],
            ["Disk", "100 MB + space for SQLite database"],
            ["Network", "Internet access for crawling"],
        ],
    )

    add_styled_heading(doc, "6.2 Installation", 2)
    add_body(doc, "1. Clone the repository:")
    doc.add_paragraph("git clone <repo-url>\ncd Doc-Tracker", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "2. Create and activate virtual environment:")
    doc.add_paragraph("python3 -m venv venv\nsource venv/bin/activate  # Linux\nvenv\\Scripts\\activate     # Windows", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "3. Install dependencies:")
    doc.add_paragraph("pip install -r requirements.txt", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc, "4. Configure environment variables:")
    doc.add_paragraph("cp .env.example .env\nnano .env  # edit with actual values", style="No Spacing").runs[0].font.name = "Consolas"

    add_styled_heading(doc, "6.3 Environment Variables", 2)
    add_table(doc,
        ["Variable", "Description", "Required"],
        [
            ["DATABASE_URL", "SQLite connection URL", "Yes"],
            ["API_HOST", "Server host (default: 0.0.0.0)", "No"],
            ["API_PORT", "Server port (default: 8443)", "No"],
            ["TELEGRAM_BOT_TOKEN", "Telegram bot token for alerts", "Yes*"],
            ["TELEGRAM_CHAT_ID", "Telegram chat ID", "Yes*"],
            ["SCAN_SCHEDULE_HOURS", "Auto-scan hours (e.g., 8,14,22)", "No"],
            ["SERVER_MODE", "Enable server mode (true/false)", "No"],
            ["DASHBOARD_URL", "Public dashboard URL", "No"],
            ["PROXY_URL", "SOCKS5 proxy for crawling", "No"],
        ],
    )
    add_body(doc, "* Required only to receive Telegram alerts.")

    add_styled_heading(doc, "6.4 Execution", 2)
    add_table(doc,
        ["Mode", "Command", "Description"],
        [
            ["Development", "python run.py", "Local server without scheduler"],
            ["Server", "python server/run_server.py", "Dashboard + Telegram + Auto-scan"],
            ["Desktop", "python desktop/run_desktop.py", "Standalone GUI"],
            ["Build Desktop", "python setup_desktop.py build", "Generate .exe executable"],
        ],
    )

    add_styled_heading(doc, "6.5 Service Installation (Linux)", 2)
    add_body(doc,
        "To keep the system running continuously on a Linux server, use the systemd service "
        "file included in the repository (server/osint-dlp.service). Edit the file to adjust "
        "paths and user according to your environment."
    )
    add_body(doc, "Management commands:")
    doc.add_paragraph(
        "sudo cp server/osint-dlp.service /etc/systemd/system/\n"
        "sudo systemctl daemon-reload\n"
        "sudo systemctl enable osint-dlp\n"
        "sudo systemctl start osint-dlp\n"
        "sudo systemctl status osint-dlp\n"
        "sudo journalctl -u osint-dlp -f",
        style="No Spacing"
    ).runs[0].font.name = "Consolas"

    add_styled_heading(doc, "7. REST API", 1)
    add_table(doc,
        ["Method", "Endpoint", "Description"],
        [
            ["GET", "/", "Dashboard HTML"],
            ["GET", "/api/dashboard", "Aggregated metrics (totals, by risk, by platform)"],
            ["GET", "/api/findings", "List findings (paginated, filterable by risk/status/category/country/language)"],
            ["PATCH", "/api/findings/{id}/status", "Update finding status (investigating/resolved/false_positive)"],
            ["DELETE", "/api/findings/{id}", "Soft delete finding"],
            ["GET", "/api/scans", "Scan history"],
            ["POST", "/api/scans/trigger", "Trigger manual scan"],
            ["GET", "/api/scans/progress", "Current scan progress"],
            ["GET", "/api/stream", "Real-time SSE event stream"],
        ],
    )

    add_styled_heading(doc, "8. Web Dashboard", 1)
    add_body(doc,
        "The web dashboard features a modern interface with dark mode theme, following "
        "cybersecurity tool design patterns (glassmorphism, neon colors, gradients)."
    )
    add_body(doc, "Dashboard sections:")
    for item in [
        "Header: System status (Idle/Scanning), manual scan button",
        "Metrics: Cards with risk-level counters",
        "Charts: Risk distribution (doughnut) and leak sources (horizontal bars)",
        "Triage Table: Filterable finding list with risk, date, country, entity, source, type, author, CPFs, CNPJs, category, and status columns",
        "Detail Panel: Slide-in panel with complete finding information",
        "Actions: Buttons to classify each finding as Investigating, False Positive, Resolved, or Notified",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "9. Security and Privacy", 1)
    for item in [
        "In-memory download (zero disk): Documents are downloaded into BytesIO and processed without touching the filesystem",
        "PII Masking: CPFs, CNPJs, and emails in snippets are masked before display (e.g., ***.456.789-**)",
        "Excluded domains: Official group sites (timacagro.com.br, phosphea.com, roullier.com) are automatically excluded from scanning",
        "Soft Delete: Data is never physically removed from the database, only marked as inactive",
        ".env file: Sensitive credentials are kept out of the repository via .gitignore",
        "Evasion delays: Randomized intervals between requests to avoid rate-limiting blocks",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    add_styled_heading(doc, "10. Maintenance and Data Ingestion", 1)
    add_body(doc,
        "To update the monitored entity base, use the ingestion script "
        "(tools/ingest_anexos.py). Place the registration PDFs in the anexos/ folder at the "
        "project root and run:"
    )
    doc.add_paragraph("python tools/ingest_anexos.py", style="No Spacing").runs[0].font.name = "Consolas"
    add_body(doc,
        "The script automatically extracts company names, CNPJs, CPFs, partners, administrators, "
        "branches, suppliers, and banking references from the documents, generating the "
        "data/entities.json file. PDFs are deleted after processing."
    )

    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_f = p_footer.add_run("\n\n— Confidential Document — Roullier Group Security Team —")
    run_f.font.size = Pt(9)
    run_f.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)

    return doc


def docx_to_pdf(docx_path: Path, pdf_path: Path):
    doc_in = Document(str(docx_path))
    pdf = fitz.open()

    full_text = []
    for para in doc_in.paragraphs:
        full_text.append(para.text)
    for table in doc_in.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            full_text.append(row_text)

    content = "\n".join(full_text)
    sections = content.split("\n")

    margin = 50
    page_w, page_h = fitz.paper_size("A4")
    usable_w = page_w - 2 * margin
    usable_h = page_h - 2 * margin
    y = margin
    line_h = 14
    heading_h = 22

    page = pdf.new_page(width=page_w, height=page_h)

    title_added = False

    for line in sections:
        line = line.strip()
        if not line:
            y += 8
            continue

        is_heading = False
        font_size = 10
        font_name = "helv"

        if not title_added and line == "OSINT & DLP System":
            y = page_h / 3
            page.insert_text(
                (margin, y), line,
                fontsize=26, fontname="hebo", color=(0.12, 0.25, 0.69)
            )
            y += 40
            title_added = True
            continue
        elif line.startswith(("Grupo Roullier", "Roullier Group")):
            page.insert_text(
                (margin, y), line,
                fontsize=14, fontname="helv", color=(0.39, 0.45, 0.55)
            )
            y += 24
            continue
        elif line.startswith(("Versão 2.1", "Version 2.1")):
            page.insert_text(
                (margin, y), line,
                fontsize=10, fontname="helv", color=(0.58, 0.64, 0.72)
            )
            y += line_h
            page = pdf.new_page(width=page_w, height=page_h)
            y = margin
            continue
        elif line and line[0].isdigit() and ". " in line[:4]:
            is_heading = True
            font_size = 14
            font_name = "hebo"

        if y + (heading_h if is_heading else line_h) > page_h - margin:
            page = pdf.new_page(width=page_w, height=page_h)
            y = margin

        if is_heading:
            y += 8
            page.insert_text(
                (margin, y), line,
                fontsize=font_size, fontname=font_name, color=(0.12, 0.25, 0.69)
            )
            y += heading_h
        elif " | " in line:
            page.insert_text(
                (margin, y), line,
                fontsize=9, fontname="helv", color=(0.2, 0.2, 0.2)
            )
            y += line_h
        else:
            words = line.split()
            current_line = ""
            for word in words:
                test = (current_line + " " + word).strip()
                tw = fitz.get_text_length(test, fontsize=font_size, fontname=font_name)
                if tw > usable_w:
                    page.insert_text(
                        (margin, y), current_line,
                        fontsize=font_size, fontname=font_name, color=(0.12, 0.16, 0.22)
                    )
                    y += line_h
                    if y > page_h - margin:
                        page = pdf.new_page(width=page_w, height=page_h)
                        y = margin
                    current_line = word
                else:
                    current_line = test
            if current_line:
                page.insert_text(
                    (margin, y), current_line,
                    fontsize=font_size, fontname=font_name, color=(0.12, 0.16, 0.22)
                )
                y += line_h

    pdf.save(str(pdf_path))
    pdf.close()


def main():
    print("[*] Gerando documentação PT-BR...")
    doc_pt = build_pt()
    pt_docx = DOCS_DIR / "OSINT_DLP_Documentacao_PT-BR.docx"
    doc_pt.save(str(pt_docx))
    print(f"    -> {pt_docx.name}")

    print("[*] Gerando documentação EN...")
    doc_en = build_en()
    en_docx = DOCS_DIR / "OSINT_DLP_Documentation_EN.docx"
    doc_en.save(str(en_docx))
    print(f"    -> {en_docx.name}")

    print("[*] Convertendo para PDF (PT-BR)...")
    pt_pdf = DOCS_DIR / "OSINT_DLP_Documentacao_PT-BR.pdf"
    docx_to_pdf(pt_docx, pt_pdf)
    print(f"    -> {pt_pdf.name}")

    print("[*] Convertendo para PDF (EN)...")
    en_pdf = DOCS_DIR / "OSINT_DLP_Documentation_EN.pdf"
    docx_to_pdf(en_docx, en_pdf)
    print(f"    -> {en_pdf.name}")

    print(f"\n[✓] 4 documentos gerados em: {DOCS_DIR}")


if __name__ == "__main__":
    main()
