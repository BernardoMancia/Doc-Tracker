const API = {
    dashboard: '/api/dashboard',
    findings: '/api/findings',
    scans: '/api/scans',
    triggerScan: '/api/scans/trigger',
    progress: '/api/scans/progress',
    stream: '/api/stream',
};

const RISK_EMOJI = { critical: '🔴', high: '🟠', medium: '🟡', low: '🟢' };
const STATUS_LABELS = { pending: 'Pendente', investigating: 'Investigando', false_positive: 'Falso Positivo', resolved: 'Resolvido', notified: 'Notificado' };
const CATEGORY_LABELS = { rh: 'RH', financeiro: 'Financeiro', ti: 'TI', ti_security: 'TI/Segurança', dados_pessoais: 'Dados Pessoais', corporativo: 'Corporativo', general: 'Geral' };
const PHASE_LABELS = { starting: 'Inicializando...', crawling: 'Buscando na web...', inspecting: 'Analisando documentos...', completed: 'Concluído', failed: 'Falhou' };
const COUNTRY_FLAGS = { BR: '🇧🇷', PT: '🇵🇹', FR: '🇫🇷', US: '🇺🇸', DE: '🇩🇪', ES: '🇪🇸', GB: '🇬🇧', CA: '🇨🇦', AR: '🇦🇷', CL: '🇨🇱', CO: '🇨🇴', MX: '🇲🇽', INT: '🌐' };

let riskChart = null;
let platformChart = null;
let currentPage = 1;
let selectedFinding = null;
let progressInterval = null;

function showToast(message, type) {
    type = type || 'info';
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = 'toast toast--' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100px)';
        toast.style.transition = 'all 0.3s ease-in';
        setTimeout(function() { toast.remove(); }, 300);
    }, 4000);
}

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    return resp.json();
}

async function loadDashboard() {
    try {
        const data = await fetchJSON(API.dashboard);
        document.getElementById('totalFindings').textContent = data.total_findings || 0;
        document.getElementById('criticalCount').textContent = (data.by_risk && data.by_risk.critical) || 0;
        document.getElementById('highCount').textContent = (data.by_risk && data.by_risk.high) || 0;
        document.getElementById('mediumCount').textContent = (data.by_risk && data.by_risk.medium) || 0;
        document.getElementById('lowCount').textContent = (data.by_risk && data.by_risk.low) || 0;
        renderRiskChart(data.by_risk || {});
        renderPlatformChart(data.by_platform || {});
        if (data.last_scan) {
            var statusEl = document.getElementById('scanStatusText');
            var dotEl = document.querySelector('.pulse-dot');
            if (data.last_scan.status === 'running') {
                statusEl.textContent = 'Scanning...';
                dotEl.classList.add('active');
            } else {
                var dt = data.last_scan.finished_at ? new Date(data.last_scan.finished_at).toLocaleString('pt-BR') : '—';
                statusEl.textContent = 'Último: ' + dt;
                dotEl.classList.remove('active');
            }
        }
    } catch (e) {
        console.error('Dashboard load error:', e);
    }
}

function renderRiskChart(byRisk) {
    var ctx = document.getElementById('riskChart');
    if (!ctx) return;
    ctx = ctx.getContext('2d');
    var labels = ['Crítico', 'Alto', 'Médio', 'Baixo'];
    var values = [byRisk.critical || 0, byRisk.high || 0, byRisk.medium || 0, byRisk.low || 0];
    var colors = ['#ff3b5c', '#ff9f43', '#feca57', '#06d6a0'];
    if (riskChart) riskChart.destroy();
    riskChart = new Chart(ctx, {
        type: 'doughnut',
        data: { labels: labels, datasets: [{ data: values, backgroundColor: colors, borderColor: '#0a0e17', borderWidth: 3, hoverOffset: 8 }] },
        options: { responsive: true, maintainAspectRatio: true, cutout: '68%', plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { family: "'Inter', sans-serif", size: 12 }, padding: 16, usePointStyle: true, pointStyleWidth: 10 } } } }
    });
}

function renderPlatformChart(byPlatform) {
    var ctx = document.getElementById('platformChart');
    if (!ctx) return;
    ctx = ctx.getContext('2d');
    var entries = Object.entries(byPlatform).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 8);
    if (platformChart) platformChart.destroy();
    platformChart = new Chart(ctx, {
        type: 'bar',
        data: { labels: entries.map(function(e) { return e[0]; }), datasets: [{ data: entries.map(function(e) { return e[1]; }), backgroundColor: 'rgba(59, 130, 246, 0.5)', borderColor: '#3b82f6', borderWidth: 1, borderRadius: 4, barPercentage: 0.7 }] },
        options: { responsive: true, maintainAspectRatio: true, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { size: 11 } } }, y: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 12 } } } } }
    });
}

async function loadFindings(page) {
    page = page || 1;
    currentPage = page;
    var risk = document.getElementById('filterRisk').value || '';
    var status = document.getElementById('filterStatus').value || '';
    var category = document.getElementById('filterCategory').value || '';
    var country = document.getElementById('filterCountry').value || '';
    var language = document.getElementById('filterLanguage').value || '';
    var params = new URLSearchParams({ page: page, per_page: 20 });
    if (risk) params.set('risk_level', risk);
    if (status) params.set('status', status);
    if (category) params.set('category', category);
    if (country) params.set('country', country);
    if (language) params.set('language', language);
    try {
        var data = await fetchJSON(API.findings + '?' + params);
        renderFindings(data.findings || []);
        renderPagination(data.page, data.pages, data.total);
    } catch (e) {
        console.error('Findings load error:', e);
        document.getElementById('findingsBody').innerHTML = '<tr><td colspan="13" class="empty-state">Erro ao carregar dados</td></tr>';
    }
}

function renderFindings(findings) {
    var tbody = document.getElementById('findingsBody');
    if (!findings.length) {
        tbody.innerHTML = '<tr><td colspan="13" class="empty-state">Nenhum finding encontrado</td></tr>';
        return;
    }
    tbody.innerHTML = findings.map(function(f) {
        var date = f.discovered_at ? new Date(f.discovered_at).toLocaleDateString('pt-BR') : '—';
        var author = f.author || '—';
        var countryFlag = (COUNTRY_FLAGS[f.country] || '🌐') + ' ' + (f.country || 'INT');
        return '<tr data-id="' + f.id + '" onclick="openDetail(' + f.id + ')">' +
            '<td><span class="risk-badge risk-badge--' + f.risk_level + '">' + (RISK_EMOJI[f.risk_level] || '') + ' ' + f.risk_score + '</span></td>' +
            '<td>' + date + '</td>' +
            '<td style="font-size:12px">' + countryFlag + '</td>' +
            '<td title="' + (f.entity_matched || '') + '">' + truncate(f.entity_matched, 20) + '</td>' +
            '<td>' + f.source_platform + '</td>' +
            '<td title="' + escapeHtml(f.title) + '">' + truncate(f.title, 30) + '</td>' +
            '<td><span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">' + f.file_type.toUpperCase() + '</span></td>' +
            '<td title="' + escapeHtml(author) + '">' + truncate(author, 15) + '</td>' +
            '<td>' + (f.cpf_count || '—') + '</td>' +
            '<td>' + (f.cnpj_count || '—') + '</td>' +
            '<td>' + (CATEGORY_LABELS[f.category] || f.category) + '</td>' +
            '<td><span class="status-badge status-badge--' + f.resolution_status + '">' + (STATUS_LABELS[f.resolution_status] || f.resolution_status) + '</span></td>' +
            '<td onclick="event.stopPropagation()"><div style="display:flex;gap:4px">' +
                '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + f.id + ',\'investigating\')" title="Investigar">🔍</button>' +
                '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + f.id + ',\'false_positive\')" title="Falso Positivo">❌</button>' +
                '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + f.id + ',\'resolved\')" title="Resolvido">✅</button>' +
            '</div></td></tr>';
    }).join('');
}

function renderPagination(current, total, totalItems) {
    var container = document.getElementById('pagination');
    if (total <= 1) {
        container.innerHTML = totalItems ? '<span style="color:var(--text-muted);font-size:12px">' + totalItems + ' resultado(s)</span>' : '';
        return;
    }
    var html = '<button ' + (current <= 1 ? 'disabled' : '') + ' onclick="loadFindings(' + (current - 1) + ')">←</button>';
    var start = Math.max(1, current - 2);
    var end = Math.min(total, current + 2);
    if (start > 1) html += '<button onclick="loadFindings(1)">1</button>';
    if (start > 2) html += '<span style="color:var(--text-muted)">…</span>';
    for (var i = start; i <= end; i++) {
        html += '<button class="' + (i === current ? 'active' : '') + '" onclick="loadFindings(' + i + ')">' + i + '</button>';
    }
    if (end < total - 1) html += '<span style="color:var(--text-muted)">…</span>';
    if (end < total) html += '<button onclick="loadFindings(' + total + ')">' + total + '</button>';
    html += '<button ' + (current >= total ? 'disabled' : '') + ' onclick="loadFindings(' + (current + 1) + ')">→</button>';
    html += '<span style="color:var(--text-muted);font-size:12px;margin-left:12px">' + totalItems + ' total</span>';
    container.innerHTML = html;
}

async function openDetail(id) {
    try {
        var allData = await fetchJSON(API.findings + '?per_page=100');
        var finding = allData.findings.find(function(f) { return f.id === id; });
        if (!finding) return;
        selectedFinding = finding;
        var body = document.getElementById('detailBody');
        var authorInfo = finding.author ? '<div class="detail-field"><span class="detail-field__label">Autor</span><span class="detail-field__value">' + escapeHtml(finding.author) + '</span></div>' : '';
        var publisherInfo = finding.publisher ? '<div class="detail-field"><span class="detail-field__label">Publicador</span><span class="detail-field__value">' + escapeHtml(finding.publisher) + '</span></div>' : '';
        var countryFlag = (COUNTRY_FLAGS[finding.country] || '🌐') + ' ' + (finding.country || 'INT');
        var langLabels = { pt: 'Português', en: 'Inglês', es: 'Espanhol', fr: 'Francês', unknown: 'Indefinido' };
        var langLabel = langLabels[finding.language] || finding.language || 'Indefinido';
        body.innerHTML =
            '<div class="detail-section"><div class="detail-section__title">Informações Gerais</div>' +
            '<div class="detail-field"><span class="detail-field__label">Score</span><span class="detail-field__value"><span class="risk-badge risk-badge--' + finding.risk_level + '">' + (RISK_EMOJI[finding.risk_level] || '') + ' ' + finding.risk_score + '</span></span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Entidade</span><span class="detail-field__value">' + (finding.entity_matched || '—') + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">País</span><span class="detail-field__value">' + countryFlag + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Idioma</span><span class="detail-field__value">' + langLabel + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Plataforma</span><span class="detail-field__value">' + finding.source_platform + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Tipo</span><span class="detail-field__value">' + finding.file_type.toUpperCase() + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Categoria</span><span class="detail-field__value">' + (CATEGORY_LABELS[finding.category] || finding.category) + '</span></div>' +
            authorInfo + publisherInfo +
            '<div class="detail-field"><span class="detail-field__label">Data</span><span class="detail-field__value">' + (finding.discovered_at ? new Date(finding.discovered_at).toLocaleString('pt-BR') : '—') + '</span></div></div>' +
            '<div class="detail-section"><div class="detail-section__title">Dados Sensíveis</div>' +
            '<div class="detail-field"><span class="detail-field__label">CPFs</span><span class="detail-field__value" style="color:' + (finding.cpf_count > 0 ? 'var(--risk-critical)' : 'var(--text-muted)') + '">' + finding.cpf_count + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">CNPJs</span><span class="detail-field__value" style="color:' + (finding.cnpj_count > 0 ? 'var(--risk-high)' : 'var(--text-muted)') + '">' + finding.cnpj_count + '</span></div>' +
            '<div class="detail-field"><span class="detail-field__label">Financeiros</span><span class="detail-field__value">' + finding.financial_count + '</span></div></div>' +
            '<div class="detail-section"><div class="detail-section__title">URL</div><a href="' + escapeHtml(finding.url) + '" target="_blank" rel="noopener" style="color:var(--accent-blue);font-size:12px;word-break:break-all;font-family:var(--font-mono)">' + escapeHtml(finding.url) + '</a></div>' +
            (finding.snippets.length ? '<div class="detail-section"><div class="detail-section__title">Snippets (Mascarados)</div>' + finding.snippets.map(function(s) { return '<div class="snippet-card"><div class="snippet-card__type">' + s.type + '</div><div class="snippet-card__masked">' + escapeHtml(s.value_masked) + '</div><div class="snippet-card__context">' + escapeHtml(s.context) + '</div></div>'; }).join('') + '</div>' : '') +
            '<div class="detail-actions">' +
            '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + finding.id + ',\'investigating\')">🔍 Investigar</button>' +
            '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + finding.id + ',\'false_positive\')">❌ Falso Positivo</button>' +
            '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + finding.id + ',\'resolved\')">✅ Resolvido</button>' +
            '<button class="btn btn--sm btn--ghost" onclick="updateStatus(' + finding.id + ',\'notified\')">📨 Notificado</button></div>';
        document.getElementById('detailPanel').classList.add('open');
    } catch (e) {
        console.error('Detail error:', e);
        showToast('Erro ao carregar detalhes', 'error');
    }
}

async function updateStatus(id, status) {
    try {
        var resp = await fetch(API.findings + '/' + id + '/status', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: status }) });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        showToast('Status: ' + STATUS_LABELS[status], 'success');
        loadFindings(currentPage);
        loadDashboard();
        if (selectedFinding && selectedFinding.id === id) document.getElementById('detailPanel').classList.remove('open');
    } catch (e) {
        showToast('Erro ao atualizar', 'error');
    }
}

async function triggerScan() {
    var btn = document.getElementById('btnTriggerScan');
    btn.disabled = true;
    btn.style.opacity = '0.5';
    try {
        var resp = await fetch(API.triggerScan, { method: 'POST' });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        showToast('Scan iniciado', 'success');
        document.getElementById('scanStatusText').textContent = 'Scanning...';
        document.querySelector('.pulse-dot').classList.add('active');
        startProgressPolling();
    } catch (e) {
        showToast('Erro: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
    }
}

function startProgressPolling() {
    var container = document.getElementById('progressContainer');
    container.style.display = 'block';
    if (progressInterval) clearInterval(progressInterval);
    progressInterval = setInterval(async function() {
        try {
            var p = await fetchJSON(API.progress);
            var pct = p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;
            document.getElementById('progressPhase').textContent = PHASE_LABELS[p.phase] || p.phase;
            document.getElementById('progressPercent').textContent = pct + '%';
            document.getElementById('progressFill').style.width = pct + '%';
            document.getElementById('progressDetail').textContent = p.detail || '';
            if (p.phase === 'completed' || p.phase === 'failed' || p.phase === 'idle') {
                clearInterval(progressInterval);
                progressInterval = null;
                setTimeout(function() { container.style.display = 'none'; }, 3000);
                loadDashboard();
                loadFindings(currentPage);
                if (p.phase === 'completed') showToast('Scan concluído', 'success');
                document.querySelector('.pulse-dot').classList.remove('active');
            }
        } catch (e) {
            console.warn('Progress poll error:', e);
        }
    }, 2000);
}

function initSSE() {
    var evtSource = new EventSource(API.stream);
    evtSource.addEventListener('new_finding', function(event) {
        try {
            var data = JSON.parse(event.data);
            showToast((RISK_EMOJI[data.risk_level] || '') + ' ' + truncate(data.title, 40), data.risk_level === 'critical' ? 'error' : 'info');
            loadDashboard();
            loadFindings(currentPage);
        } catch (e) {}
    });
}

function truncate(str, len) { if (!str) return '—'; return str.length > len ? str.substring(0, len) + '…' : str; }

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    loadFindings(1);
    initSSE();
    document.getElementById('btnTriggerScan').addEventListener('click', triggerScan);
    document.getElementById('closeDetail').addEventListener('click', function() { document.getElementById('detailPanel').classList.remove('open'); });
    document.getElementById('filterRisk').addEventListener('change', function() { loadFindings(1); });
    document.getElementById('filterStatus').addEventListener('change', function() { loadFindings(1); });
    document.getElementById('filterCategory').addEventListener('change', function() { loadFindings(1); });
    document.getElementById('filterCountry').addEventListener('change', function() { loadFindings(1); });
    document.getElementById('filterLanguage').addEventListener('change', function() { loadFindings(1); });
    setInterval(loadDashboard, 30000);
});
