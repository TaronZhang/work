/* ═══════════════════════════════════════════════════
   BidChecker v2 — 标书检查工具
   Frontend Application (Vanilla JS SPA)
   ═══════════════════════════════════════════════════ */

const state = {
  tender: null,
  bids: [],
  mode: 'fast',
  isAnalyzing: false,
  results: null,
  activeBidIndex: 0,
  bidCounter: 2,
  splitInfo: null,        // 分片信息
};

const DOM = {};
function cacheDOM() {
  DOM.modeToggle = document.getElementById('modeToggle');
  DOM.aiConfig = document.getElementById('aiConfig');
  DOM.apiKeyInput = document.getElementById('apiKeyInput');
  DOM.modelSelect = document.getElementById('modelSelect');
  DOM.baseUrlInput = document.getElementById('baseUrlInput');
  DOM.tenderDropZone = document.getElementById('tenderDropZone');
  DOM.tenderStatus = document.getElementById('tenderStatus');
  DOM.bidList = document.getElementById('bidList');
  DOM.addBidBtn = document.getElementById('addBidBtn');
  DOM.compareBtn = document.getElementById('compareBtn');
  DOM.progressBar = document.getElementById('progressBar');
  DOM.progressFill = document.getElementById('progressFill');
  DOM.progressText = document.getElementById('progressText');
  DOM.uploadSection = document.getElementById('uploadSection');
  DOM.resultsSection = document.getElementById('resultsSection');
  DOM.filterSummary = document.getElementById('filterSummary');
  DOM.filterGrid = document.getElementById('filterGrid');
  DOM.summaryCards = document.getElementById('summaryCards');
  DOM.detailSection = document.getElementById('detailSection');
  DOM.detailTabs = document.getElementById('detailTabs');
  DOM.detailContent = document.getElementById('detailContent');
  DOM.resetBtn = document.getElementById('resetBtn');
  DOM.toggleApiKeyVis = document.getElementById('toggleApiKeyVis');
}

document.addEventListener('DOMContentLoaded', () => {
  cacheDOM();
  setupEventListeners();
  loadApiKeyFromStorage();
});

function setupEventListeners() {
  DOM.modeToggle.addEventListener('change', onModeToggle);
  setupDropZone(DOM.tenderDropZone, 'tender', 0);
  document.querySelectorAll('.bid-drop-zone').forEach(zone => {
    setupDropZone(zone, 'bid', parseInt(zone.dataset.bidIndex));
  });
  DOM.addBidBtn.addEventListener('click', addBidEntry);
  DOM.compareBtn.addEventListener('click', startComparison);
  DOM.resetBtn.addEventListener('click', resetAll);
  DOM.toggleApiKeyVis.addEventListener('click', toggleApiKeyVisibility);

  document.addEventListener('click', (e) => {
    const removeBtn = e.target.closest('[data-remove]');
    if (removeBtn) removeBidEntry(parseInt(removeBtn.dataset.remove));
  });
  DOM.summaryCards.addEventListener('click', (e) => {
    const card = e.target.closest('.result-card');
    if (card) setActiveBid(parseInt(card.dataset.bidIndex));
  });
  DOM.detailTabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.detail-tab');
    if (tab) setActiveBid(parseInt(tab.dataset.bidIndex));
  });
}

// ── Drop Zone ──────────────────────────────────────────
function setupDropZone(zone, docType, bidIndex) {
  const fileInput = zone.querySelector('.file-input');
  zone.addEventListener('click', (e) => {
    if (e.target === fileInput) return;
    fileInput.click();
  });
  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) uploadFile(e.target.files[0], docType, bidIndex);
  });
  zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0], docType, bidIndex);
  });
}

// ── Upload ─────────────────────────────────────────────
async function uploadFile(file, docType, bidIndex) {
  const statusEl = docType === 'tender'
    ? DOM.tenderStatus
    : document.getElementById(`bidStatus-${bidIndex}`);

  const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
  const largeBadge = file.size > 10 * 1024 * 1024
    ? '<span style="color:var(--accent-amber);font-size:11px;margin-left:4px">大文件</span>'
    : '';

  if (statusEl) {
    statusEl.innerHTML = `<div class="file-card status-loading">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
      <span class="file-name">${escHtml(file.name)}</span>
      <span class="file-meta">${sizeMB} MB · 解析中…${largeBadge}</span>
    </div>`;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('doc_type', docType);
  if (docType === 'bid') formData.append('bid_label', `投标文件 ${bidIndex + 1}`);

  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) throw new Error(data.message);

    const entry = { id: data.file_id, filename: data.filename, label: data.label, status: data.status, chars: data.chars, sizeBytes: data.size_bytes, needsSplit: data.needs_split };
    if (docType === 'tender') state.tender = entry;
    else state.bids[bidIndex] = entry;

    if (statusEl) {
      const icon = data.status === 'parsed' || data.status === 'parsed_large'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
      const cls = data.status === 'parsed' || data.status === 'parsed_large' ? 'status-ok' : 'status-error';
      const splitTag = data.needs_split ? ' · 自动分片' : '';
      statusEl.innerHTML = `<div class="file-card ${cls}">${icon}<span class="file-name">${escHtml(data.filename)}</span><span class="file-meta">${data.size_mb || sizeMB} MB · ${formatSize(data.chars)} 字${splitTag}</span></div>`;
    }

    const card = docType === 'tender'
      ? DOM.tenderDropZone.closest('.upload-card')
      : document.querySelector(`.bid-card[data-bid-index="${bidIndex}"]`);
    if (card && (data.status === 'parsed' || data.status === 'parsed_large')) card.classList.add('has-file');

  } catch (err) {
    if (statusEl) statusEl.innerHTML = `<div class="file-card status-error"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg><span class="file-name">${escHtml(err.message)}</span></div>`;
    console.error('Upload error:', err);
  }
  updateCompareButton();
}

// ── Mode ───────────────────────────────────────────────
function onModeToggle() {
  state.mode = DOM.modeToggle.checked ? 'ai' : 'fast';
  if (state.mode === 'ai') {
    DOM.aiConfig.classList.remove('hidden');
    if (state.results) { DOM.resultsSection.classList.add('hidden'); DOM.uploadSection.classList.remove('hidden'); state.results = null; }
  } else {
    DOM.aiConfig.classList.add('hidden');
  }
}

// ── Bid Management ─────────────────────────────────────
function addBidEntry() {
  const idx = state.bidCounter++;
  const card = document.createElement('div');
  card.className = 'upload-card bid-card';
  card.dataset.bidIndex = idx;
  card.innerHTML = `
    <div class="upload-card-header">
      <span class="badge badge-bid">投标文件 ${idx + 1}</span>
      <button class="btn-icon btn-remove" title="移除" data-remove="${idx}" aria-label="移除投标文件 ${idx + 1}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="drop-zone bid-drop-zone" data-bid-index="${idx}">
      <div class="drop-zone-content">
        <svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p>拖拽投标文件到此处</p><span class="drop-hint">或 点击选择文件</span>
      </div>
      <input type="file" class="file-input" accept=".docx,.pdf,.txt" data-doc-type="bid" data-bid-index="${idx}" hidden>
    </div>
    <div class="file-status" id="bidStatus-${idx}"></div>`;
  DOM.bidList.appendChild(card);
  setupDropZone(card.querySelector('.bid-drop-zone'), 'bid', idx);
}

function removeBidEntry(idx) {
  const allCards = document.querySelectorAll('.bid-card');
  if (allCards.length <= 1) return;
  const card = document.querySelector(`.bid-card[data-bid-index="${idx}"]`);
  if (card) card.remove();
  state.bids = state.bids.filter((_, i) => i !== idx);
  updateCompareButton();
}

// ── Comparison ─────────────────────────────────────────
async function startComparison() {
  if (state.isAnalyzing) return;
  if (!state.tender) { showError('请先上传招标文件'); return; }
  const activeBids = getActiveBids();
  if (activeBids.length === 0) { showError('请至少上传一份投标文件'); return; }

  state.isAnalyzing = true;
  DOM.compareBtn.disabled = true;
  DOM.progressBar.classList.remove('hidden');

  const isAI = state.mode === 'ai';
  const endpoint = isAI ? '/api/comparison/ai' : '/api/comparison';
  const body = { tender_id: state.tender.id, bid_ids: activeBids.map(b => b.id) };

  if (isAI) {
    body.api_key = DOM.apiKeyInput.value.trim();
    body.model = DOM.modelSelect.value;
    body.base_url = DOM.baseUrlInput.value.trim() || 'https://api.openai.com/v1';
    saveApiKeyToStorage(body.api_key);
  }

  const hasLarge = state.tender.needsSplit || activeBids.some(b => b.needsSplit);
  setProgress(5, hasLarge ? '大文件模式 · 正在自动拆分…' : '正在解析文件…');

  try {
    if (hasLarge) setProgress(15, '正在分片比对…');

    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.error) throw new Error(data.message);

    setProgress(90, '正在生成报告…');
    state.results = data;
    setProgress(100, '分析完成');

    setTimeout(() => {
      DOM.progressBar.classList.add('hidden');
      DOM.uploadSection.classList.add('hidden');
      DOM.resultsSection.classList.remove('hidden');
      renderResults();
      state.isAnalyzing = false;
    }, 500);
  } catch (err) {
    DOM.progressBar.classList.add('hidden');
    DOM.compareBtn.disabled = false;
    state.isAnalyzing = false;
    showError(err.message);
    console.error('Comparison error:', err);
  }
}

// ── Render Results ─────────────────────────────────────
function renderResults() {
  if (!state.results) return;
  const { results, mode, chunked } = state.results;

  if (mode === 'ai' && state.results.filter_categories) {
    DOM.filterSummary.classList.remove('hidden');
    DOM.filterGrid.innerHTML = state.results.filter_categories.map(cat => `
      <div class="filter-item"><div class="filter-cat-label">${cat.label}</div><div class="filter-count">${cat.count} 段</div><div class="filter-samples">${cat.samples.map(s => `<div style="margin-bottom:4px">"${escHtml(s)}…"</div>`).join('')}</div></div>`).join('');
  } else {
    DOM.filterSummary.classList.add('hidden');
  }

  DOM.summaryCards.innerHTML = results.map((r, i) => {
    const pct = r.duplicate_percentage;
    const gaugeClass = pct >= 30 ? 'high' : pct >= 10 ? 'medium' : 'low';
    const sev = r.severity;
    return `<div class="result-card ${i === state.activeBidIndex ? 'active' : ''}" data-bid-index="${i}">
      <div class="card-header"><span class="card-bid-name">${escHtml(r.bid_filename)}</span><span class="card-severity severity-${sev.level}">${sev.label}</span></div>
      <div class="card-pct">${pct}%</div>
      <div class="card-meta">匹配 ${formatSize(r.matched_chars)} / ${formatSize(r.total_tender_chars)} 字 · ${r.segments.length} 段</div>
      <div class="gauge-bar"><div class="gauge-fill ${gaugeClass}" style="width:${Math.min(pct, 100)}%"></div></div>
    </div>`;
  }).join('');

  DOM.detailTabs.innerHTML = results.map((r, i) =>
    `<button class="detail-tab ${i === state.activeBidIndex ? 'active' : ''}" data-bid-index="${i}">${escHtml(r.bid_filename)}</button>`).join('');

  renderDetailContent();
  DOM.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderDetailContent() {
  if (!state.results) return;
  const result = state.results.results[state.activeBidIndex];
  if (!result) return;
  const segments = result.segments || [];

  if (segments.length === 0) {
    DOM.detailContent.innerHTML = `<div class="segment-card" style="text-align:center;padding:var(--space-2xl);color:var(--text-tertiary)">未发现匹配的重复段落</div>`;
    return;
  }

  DOM.detailContent.innerHTML = segments.map(seg => {
    const simPct = Math.round(seg.similarity * 100);
    const simClass = simPct >= 90 ? 'high' : simPct >= 75 ? 'medium' : 'low';
    return `<div class="segment-card">
      <div class="segment-header"><span class="segment-id">#${seg.id + 1}</span><span class="segment-similarity similarity-${simClass}">相似度 ${simPct}%</span></div>
      <div class="segment-compare">
        <div class="segment-panel"><div class="segment-panel-label">招标文件</div><div class="segment-panel-text">${escHtml(seg.tender_text)}</div></div>
        <div class="segment-panel"><div class="segment-panel-label">投标文件</div><div class="segment-panel-text">${escHtml(seg.bid_text)}</div></div>
      </div></div>`;
  }).join('');
}

function setActiveBid(idx) {
  state.activeBidIndex = idx;
  document.querySelectorAll('.result-card').forEach(c => c.classList.toggle('active', parseInt(c.dataset.bidIndex) === idx));
  document.querySelectorAll('.detail-tab').forEach(t => t.classList.toggle('active', parseInt(t.dataset.bidIndex) === idx));
  renderDetailContent();
}

async function resetAll() {
  try { await fetch('/api/clear', { method: 'POST' }); } catch (e) {}
  state.tender = null; state.bids = []; state.results = null;
  state.isAnalyzing = false; state.activeBidIndex = 0;
  DOM.resultsSection.classList.add('hidden'); DOM.uploadSection.classList.remove('hidden');
  DOM.tenderStatus.innerHTML = ''; DOM.compareBtn.disabled = true; DOM.progressBar.classList.add('hidden');
  document.querySelectorAll('.file-status[id^="bidStatus-"]').forEach(el => el.innerHTML = '');
  document.querySelectorAll('.upload-card.has-file').forEach(el => el.classList.remove('has-file'));
}

// ── Helpers ────────────────────────────────────────────
function getActiveBids() {
  const entries = [];
  document.querySelectorAll('.bid-card').forEach(card => {
    const idx = parseInt(card.dataset.bidIndex);
    const bid = state.bids[idx];
    if (bid && (bid.status === 'parsed' || bid.status === 'parsed_large')) entries.push(bid);
  });
  return entries;
}

function updateCompareButton() { DOM.compareBtn.disabled = !state.tender || getActiveBids().length === 0; }
function setProgress(pct, text) { DOM.progressFill.style.width = pct + '%'; DOM.progressText.textContent = text; }
function showError(msg) { alert('错误: ' + msg); }
function escHtml(str) { const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }
function formatSize(chars) { if (!chars) return '0'; if (chars >= 10000) return (chars / 10000).toFixed(1) + '万'; if (chars >= 1000) return (chars / 1000).toFixed(1) + 'k'; return String(chars); }

// ── API Key ────────────────────────────────────────────
function saveApiKeyToStorage(key) { try { localStorage.setItem('bidchecker_api_key', key); } catch (e) {} }
function loadApiKeyFromStorage() { try { const k = localStorage.getItem('bidchecker_api_key'); if (k) DOM.apiKeyInput.value = k; } catch (e) {} }
function toggleApiKeyVisibility() { DOM.apiKeyInput.type = DOM.apiKeyInput.type === 'password' ? 'text' : 'password'; }
