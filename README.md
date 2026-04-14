# OSINT & DLP System — Grupo Roullier

Sistema automatizado de OSINT e Prevenção de Vazamento de Dados (DLP) focado em identificar fugas de informação sensível do Grupo Roullier (Timac Agro, Sulfabras, Phosphea). Dual mode: **Server** (dashboard web + Telegram + auto-scan) e **Desktop** (GUI standalone).

Automated OSINT and Data Leak Prevention (DLP) system focused on identifying sensitive information leaks from the Roullier Group (Timac Agro, Sulfabras, Phosphea). Dual mode: **Server** (web dashboard + Telegram + auto-scan) and **Desktop** (standalone GUI).

---

## 🇧🇷 Português

### Funcionalidades

- **Motor de Busca (Crawling)**: 73+ Google Dorks via DuckDuckGo (Scribd, SlideShare, Issuu, GitHub, GitLab)
- **Intelligence Matrix Dinâmica**: Carrega entidades, CNPJs, CPFs e fornecedores do `data/entities.json`
- **Inspeção Profunda**: Download em memória (zero disco), extração de texto (PDF/DOCX/XLSX/TXT), análise por Regex
- **Extração de Metadados**: Autor, criador, software e data de documentos com filtragem de artefatos técnicos
- **Classificação de Risco**: Scoring automático em 4 níveis (Crítico, Alto, Médio, Baixo) com categorias (RH, Financeiro, TI, TI/Segurança)
- **Filtros Regionais**: Detecção de país por TLD e idioma por análise textual (PT, EN, ES, FR)
- **Dashboard Web**: Interface cybersecurity dark mode com métricas, gráficos, tabela de triagem e painel de detalhes
- **Progresso em Tempo Real**: Barra de progresso animada com % durante o scan, polling a cada 2s
- **Alertas Telegram**: Notificações automáticas para findings críticos e altos com link para dashboard
- **Auto-scan (Server)**: APScheduler com 3 scans diários (08:00, 14:00, 22:00 BRT)
- **Desktop Standalone**: GUI tkinter dark mode com exportação CSV/JSON
- **Compilação Desktop**: cx_Freeze para gerar `.exe` standalone

### Requisitos

- Python 3.10+
- pip

### Instalação

```bash
git clone <repo-url>
cd busca-doc-timac
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
```

### Modos de Execução

#### Dev local (sem scheduler)
```bash
python run.py
```
Dashboard em `http://localhost:8443`

#### Servidor (Dashboard + Telegram + Auto-scan 3x/dia)
```bash
python server/run_server.py
```

#### Desktop (GUI standalone, sem servidor)
```bash
python desktop/run_desktop.py
```

#### Compilar Desktop (.exe)
```bash
pip install cx_Freeze
python setup_desktop.py build
```

### Configuração

Editar o ficheiro `.env`:

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | URL do SQLite |
| `API_HOST` | Host do servidor |
| `API_PORT` | Porta do servidor (padrão: 8443) |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram |
| `TELEGRAM_CHAT_ID` | ID do chat Telegram |
| `PROXY_URL` | Proxy SOCKS5 (opcional) |
| `SCAN_SCHEDULE_HOURS` | Horários do auto-scan (ex: `8,14,22`) |
| `SERVER_MODE` | Ativar modo servidor (`true/false`) |
| `DASHBOARD_URL` | URL pública do dashboard para links no Telegram |

### Estrutura do Projeto

```
busca-doc-timac/
├── config/                  # Configurações (compartilhado)
│   ├── settings.py
│   └── intelligence_matrix.py
├── core/                    # Database e models (compartilhado)
│   ├── database.py
│   └── models.py
├── crawler/                 # Motor de busca (compartilhado)
│   ├── dork_generator.py
│   ├── search_engine.py
│   └── url_filter.py
├── inspector/               # Inspeção (compartilhado)
│   ├── downloader.py
│   ├── extractor.py
│   ├── regex_engine.py
│   └── risk_classifier.py
├── alerts/                  # Webhooks (só server)
│   └── webhook.py
├── data/                    # Dados extraídos dos anexos
│   └── entities.json
├── tools/                   # Scripts utilitários
│   └── ingest_anexos.py
├── server/                  # Versão Server
│   └── run_server.py
├── desktop/                 # Versão Desktop
│   ├── app.py
│   └── run_desktop.py
├── api/                     # FastAPI app e rotas
│   ├── app.py
│   ├── routes/
│   └── templates/
├── static/                  # CSS e JS do dashboard
│   ├── css/dashboard.css
│   └── js/dashboard.js
├── .env.example
├── .gitignore
├── requirements.txt
├── setup_desktop.py
├── run.py
└── README.md
```

---

## 🇬🇧 English

### Features

- **Search Engine (Crawling)**: 73+ Google Dorks via DuckDuckGo (Scribd, SlideShare, Issuu, GitHub, GitLab)
- **Dynamic Intelligence Matrix**: Loads entities, CNPJs, CPFs, and suppliers from `data/entities.json`
- **Deep Inspection**: In-memory download (zero disk), text extraction (PDF/DOCX/XLSX/TXT), Regex analysis
- **Metadata Extraction**: Author, creator, software, and document creation date with technical artifact filtering
- **Risk Classification**: Automatic scoring in 4 levels (Critical, High, Medium, Low) with categories (HR, Finance, IT, IT/Security)
- **Regional Filters**: Country detection by TLD and language detection by text analysis (PT, EN, ES, FR)
- **Web Dashboard**: Cybersecurity dark mode interface with metrics, charts, triage table, and detail panel
- **Real-time Progress**: Animated progress bar with % during scan, polling every 2s
- **Telegram Alerts**: Automatic notifications for critical and high findings with dashboard link
- **Auto-scan (Server)**: APScheduler with 3 daily scans (08:00, 14:00, 22:00 BRT)
- **Standalone Desktop**: tkinter dark mode GUI with CSV/JSON export
- **Desktop Build**: cx_Freeze to generate standalone `.exe`

### Requirements

- Python 3.10+
- pip

### Installation

```bash
git clone <repo-url>
cd busca-doc-timac
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
```

### Execution Modes

#### Local dev (no scheduler)
```bash
python run.py
```
Dashboard at `http://localhost:8443`

#### Server (Dashboard + Telegram + Auto-scan 3x/day)
```bash
python server/run_server.py
```

#### Desktop (standalone GUI, no server needed)
```bash
python desktop/run_desktop.py
```

#### Build Desktop (.exe)
```bash
pip install cx_Freeze
python setup_desktop.py build
```

### Configuration

Edit the `.env` file:

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLite URL |
| `API_HOST` | Server host |
| `API_PORT` | Server port (default: 8443) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `PROXY_URL` | SOCKS5 proxy (optional) |
| `SCAN_SCHEDULE_HOURS` | Auto-scan hours (e.g., `8,14,22`) |
| `SERVER_MODE` | Enable server mode (`true/false`) |
| `DASHBOARD_URL` | Public dashboard URL for Telegram links |

### Project Structure

```
busca-doc-timac/
├── config/                  # Settings (shared)
│   ├── settings.py
│   └── intelligence_matrix.py
├── core/                    # Database & models (shared)
│   ├── database.py
│   └── models.py
├── crawler/                 # Search engine (shared)
│   ├── dork_generator.py
│   ├── search_engine.py
│   └── url_filter.py
├── inspector/               # Inspection (shared)
│   ├── downloader.py
│   ├── extractor.py
│   ├── regex_engine.py
│   └── risk_classifier.py
├── alerts/                  # Webhooks (server only)
│   └── webhook.py
├── data/                    # Extracted entity data
│   └── entities.json
├── tools/                   # Utility scripts
│   └── ingest_anexos.py
├── server/                  # Server version
│   └── run_server.py
├── desktop/                 # Desktop version
│   ├── app.py
│   └── run_desktop.py
├── api/                     # FastAPI app & routes
│   ├── app.py
│   ├── routes/
│   └── templates/
├── static/                  # Dashboard CSS & JS
│   ├── css/dashboard.css
│   └── js/dashboard.js
├── .env.example
├── .gitignore
├── requirements.txt
├── setup_desktop.py
├── run.py
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Dashboard HTML |
| `GET` | `/api/dashboard` | Aggregated metrics |
| `GET` | `/api/findings` | List findings (paginated, filterable by risk, status, category, country, language) |
| `PATCH` | `/api/findings/{id}/status` | Update finding status |
| `DELETE` | `/api/findings/{id}` | Soft delete finding |
| `GET` | `/api/scans` | List scan history |
| `POST` | `/api/scans/trigger` | Trigger manual scan |
| `GET` | `/api/scans/progress` | Get current scan progress |
| `GET` | `/api/stream` | SSE real-time stream |

---

## License

Internal use only — Grupo Roullier Security Team.
