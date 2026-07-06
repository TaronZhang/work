/* ═══════════════════════════════════════════════════
   DocDiff v3 — 文档重复度比对工具
   Frontend Application (Vanilla JS SPA)
   ═══════════════════════════════════════════════════ */

const state = {
  documents: [],        // {id, filename, label, docType, status, chars, sizeBytes, needsSplit}
  mode: 'fast',         // 'fast' | 'ai'
  compareMode: 'pairwise', // 'pairwise' | 'one_to_many'
  isAnalyzing: false,
  results: null,        // raw API response
  activePairIndex: 0,   // which pair is selected in detail view
  docCounter: 0,        // for auto-labeling new slots
};

const DOM = {};
function cacheDOM() {
  DOM.modeToggle = document.getElementById('modeToggle');
  DOM.aiConfig = document.getElementById('aiConfig');
  DOM.apiKeyInput = document.getElementById('apiKeyInput');
  DOM.modelSelect = document.getElementById('modelSelect');
  DOM.baseUrlInput = document.getElementById('baseUrlInput');
  DOM.docUploadGrid = document.getElementById('docUploadGrid');
  DOM.addDocBtn = document.getElementById('addDocBtn');
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
  renderDocSlots(); // initial 2 slots
});

function setupEventListeners() {
  DOM.modeToggle.addEventListener('change', onModeToggle);
  DOM.addDocBtn.addEventListener('click', addDocSlot);
  DOM.compareBtn.addEventListener('click', startComparison);
  DOM.resetBtn.addEventListener('click', resetAll);
  DOM.toggleApiKeyVis.addEventListener('click', toggleApiKeyVisibility);

  // Compare mode radio
  document.querySelectorAll('input[name="compareMode"]').forEach(radio => {
    radio.addEventListener('change', () => {
      state.compareMode = document.querySelector('input[name="compareMode"]:checked').value;
    });
  });

  // Delegated events
  DOM.docUploadGrid.addEventListener('click', (e) => {
    const removeBtn = e.target.closest('[data-remove-doc]');
    if (removeBtn) removeDocSlot(removeBtn.dataset.removeDoc);
  });
  DOM.summaryCards.addEventListener('click', (e) => {
    const card = e.target.closest('.result-card');
    if (card) setActivePair(parseInt(card.dataset.pairIndex));
  });
  DOM.detailTabs.addEventListener('click', (e) => {
    const tab = e.target.closest('.detail-tab');
    if (tab) setActivePair(parseInt(tab.dataset.pairIndex));
  });
}

// ── Document Slot Rendering ───────────────────────────
function createDocSlot(index) {
  const label = `文档 ${index + 1}`;
  return {
    id: null,
    filename: '',
    label: label,
    docType: 'document',
    status: '',
    chars: 0,
    sizeBytes: 0,
    needsSplit: false,
  };
}

function renderDocSlots() {
  // Ensure at least 2 slots
  while (state.documents.length < 2) {
    state.documents.push(createDocSlot(state.documents.length));
    state.docCounter = state.documents.length;
  }

  DOM.docUploadGrid.innerHTML = state.documents.map((doc, i) => {
    const hasFile = doc.status === 'parsed' || doc.status === 'parsed_large';
    return `
    <div class="doc-upload-card ${hasFile ? 'has-file' : ''}" data-doc-index="${i}">
      <div class="doc-card-header">
        <div class="doc-label-row">
          <input type="text" class="doc-label-input" value="${escHtml(doc.label)}"
                 data-doc-index="${i}" placeholder="文档名称" maxlength="50">
          <select class="doc-type-select" data-doc-index="${i}">
            <option value="document" ${doc.docType === 'document' ? 'selected' : ''}>文档</option>
            <option value="tender" ${doc.docType === 'tender' ? 'selected' : ''}>招标文件</option>
            <option value="bid" ${doc.docType === 'bid' ? 'selected' : ''}>投标文件</option>
          </select>
        </div>
        ${state.documents.length > 2 ? `
        <button class="btn-icon btn-remove" title="移除此文档" data-remove-doc="${i}" aria-label="移除文档 ${i + 1}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>` : ''}
      </div>
      <div class="drop-zone doc-drop-zone" data-doc-index="${i}">
        <div class="drop-zone-content">
          <svg class="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <p>拖拽文件到此处</p>
          <span class="drop-hint">或 点击选择文件</span>
        </div>
        <input type="file" class="file-input" accept=".docx,.pdf,.txt"
               data-doc-index="${i}" hidden>
      </div>
      <div class="file-status" id="docStatus-${i}">${renderFileStatus(doc, i)}</div>
    </div>`;
  }).join('');

  // Bind events for new elements
  bindDocSlotEvents();
  updateCompareButton();
}

function renderFileStatus(doc, index) {
  if (!doc.status) return '';
  if (doc.status === 'parsed' || doc.status === 'parsed_large') {
    const sizeMB = (doc.sizeBytes / (1024 * 1024)).toFixed(1);
    const splitTag = doc.needsSplit ? ' · 自动分片' : '';
    return `<div class="file-card status-ok">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
      <span class="file-name">${escHtml(doc.filename)}</span>
      <span class="file-meta">${sizeMB} MB · ${formatSize(doc.chars)} 字${splitTag}</span>
    </div>`;
  }
  if (doc.status === 'error') {
    return `<div class="file-card status-error">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
      <span class="file-name">解析失败</span>
    </div>`;
  }
  return '';
}

function bindDocSlotEvents() {
  // Drop zones
  document.querySelectorAll('.doc-drop-zone').forEach(zone => {
    const idx = parseInt(zone.dataset.docIndex);
    const fileInput = zone.querySelector('.file-input');
    zone.addEventListener('click', (e) => {
      if (e.target === fileInput) return;
      fileInput.click();
    });
    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) uploadFile(e.target.files[0], idx);
    });
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0], idx);
    });
  });

  // Label inputs
  document.querySelectorAll('.doc-label-input').forEach(input => {
    input.addEventListener('change', () => {
      const idx = parseInt(input.dataset.docIndex);
      if (state.documents[idx]) {
        state.documents[idx].label = input.value.trim() || `文档 ${idx + 1}`;
      }
    });
  });

  // Type selects
  document.querySelectorAll('.doc-type-select').forEach(select => {
    select.addEventListener('change', () => {
      const idx = parseInt(select.dataset.docIndex);
      if (state.documents[idx]) {
        state.documents[idx].docType = select.value;
      }
    });
  });
}

function addDocSlot() {
  state.documents.push(createDocSlot(state.documents.length));
  state.docCounter = state.documents.length;
  renderDocSlots();
  // Scroll to new card
  const lastCard = DOM.docUploadGrid.querySelector('.doc-upload-card:last-child');
  if (lastCard) lastCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function removeDocSlot(idx) {
  if (state.documents.length <= 2) return; // minimum 2 slots
  // If this doc was uploaded, delete from server
  const doc = state.documents[idx];
  if (doc && doc.id) {
    fetch(`/api/files/${doc.id}`, { method: 'DELETE' }).catch(() => {});
  }
  state.documents.splice(idx, 1);
  renderDocSlots();
}

// ── Upload ─────────────────────────────────────────────
async function uploadFile(file, docIndex) {
  const statusEl = document.getElementById(`docStatus-${docIndex}`);
  const doc = state.documents[docIndex];
  if (!doc) return;

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
  formData.append('doc_type', doc.docType);
  formData.append('label', doc.label || file.name);

  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) throw new Error(data.message);

    // If this slot previously had a file, delete it
    if (doc.id && doc.id !== data.file_id) {
      fetch(`/api/files/${doc.id}`, { method: 'DELETE' }).catch(() => {});
    }

    // Update doc state
    doc.id = data.file_id;
    doc.filename = data.filename;
    doc.label = data.label;
    doc.status = data.status;
    doc.chars = data.chars;
    doc.sizeBytes = data.size_bytes;
    doc.needsSplit = data.needs_split;

    // Re-render to update label and status
    renderDocSlots();

    // Re-focus label input after re-render
    const labelInput = document.querySelector(`.doc-label-input[data-doc-index="${docIndex}"]`);
    if (labelInput) labelInput.value = doc.label;

  } catch (err) {
    if (statusEl) {
      statusEl.innerHTML = `<div class="file-card status-error">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        <span class="file-name">${escHtml(err.message)}</span>
      </div>`;
    }
    console.error('Upload error:', err);
  }
  updateCompareButton();
}

// ── Mode ───────────────────────────────────────────────
function onModeToggle() {
  state.mode = DOM.modeToggle.checked ? 'ai' : 'fast';
  if (state.mode === 'ai') {
    DOM.aiConfig.classList.remove('hidden');
    if (state.results) {
      DOM.resultsSection.classList.add('hidden');
      DOM.uploadSection.classList.remove('hidden');
      state.results = null;
    }
  } else {
    DOM.aiConfig.classList.add('hidden');
  }
}

// ── Comparison ─────────────────────────────────────────
async function startComparison() {
  if (state.isAnalyzing) return;

  const readyDocs = state.documents.filter(d => d.status === 'parsed' || d.status === 'parsed_large');
  if (readyDocs.length < 2) { showError('请至少上传两份文档进行比对'); return; }

  state.isAnalyzing = true;
  DOM.compareBtn.disabled = true;
  DOM.progressBar.classList.remove('hidden');
  setProgress(5, '正在准备比对…');

  const isAI = state.mode === 'ai';
  const endpoint = isAI ? '/api/comparison/ai' : '/api/comparison';

  let body;
  if (state.compareMode === 'pairwise') {
    // All pairs comparison
    body = { doc_ids: readyDocs.map(d => d.id) };
  } else {
    // One-to-many: first doc vs rest
    body = {
      tender_id: readyDocs[0].id,
      bid_ids: readyDocs.slice(1).map(d => d.id),
    };
  }

  if (isAI) {
    body.api_key = DOM.apiKeyInput.value.trim();
    body.model = DOM.modelSelect.value;
    body.base_url = DOM.baseUrlInput.value.trim() || 'https://api.openai.com/v1';
    saveApiKeyToStorage(body.api_key);
  }

  const hasLarge = readyDocs.some(d => d.needsSplit);
  if (hasLarge) setProgress(15, '大文件模式 · 正在自动拆分…');

  try {
    if (hasLarge) setProgress(30, '正在分片比对…');

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
  const { results, mode } = state.results;

  if (results.length === 0) {
    DOM.summaryCards.innerHTML = '<div class="empty-state">未发现可比对结果</div>';
    DOM.detailTabs.innerHTML = '';
    DOM.detailContent.innerHTML = '';
    return;
  }

  // AI filter summary
  if (mode === 'ai' && state.results.filter_categories) {
    DOM.filterSummary.classList.remove('hidden');
    DOM.filterGrid.innerHTML = state.results.filter_categories.map(cat => `
      <div class="filter-item">
        <div class="filter-cat-label">${cat.label}</div>
        <div class="filter-count">${cat.count} 段</div>
        <div class="filter-samples">${cat.samples.map(s => `<div style="margin-bottom:4px">"${escHtml(s)}…"</div>`).join('')}</div>
      </div>`).join('');
  } else {
    DOM.filterSummary.classList.add('hidden');
  }

  // Summary cards — one per pair
  DOM.summaryCards.innerHTML = results.map((r, i) => {
    const pct = r.duplicate_percentage;
    const gaugeClass = pct >= 30 ? 'high' : pct >= 10 ? 'medium' : 'low';
    const sev = r.severity;
    return `<div class="result-card ${i === state.activePairIndex ? 'active' : ''}" data-pair-index="${i}">
      <div class="card-header">
        <span class="card-pair-name">${escHtml(r.label_a || '文档 A')} ↔ ${escHtml(r.label_b || '文档 B')}</span>
        <span class="card-severity severity-${sev.level}">${sev.label}</span>
      </div>
      <div class="card-pct">${pct}%</div>
      <div class="card-meta">匹配 ${formatSize(r.matched_chars)} / ${formatSize(r.total_tender_chars)} 字 · ${r.segments ? r.segments.length : 0} 段</div>
      <div class="gauge-bar"><div class="gauge-fill ${gaugeClass}" style="width:${Math.min(pct, 100)}%"></div></div>
    </div>`;
  }).join('');

  // Detail tabs
  DOM.detailTabs.innerHTML = results.map((r, i) =>
    `<button class="detail-tab ${i === state.activePairIndex ? 'active' : ''}" data-pair-index="${i}">${escHtml(r.label_a || 'A')} ↔ ${escHtml(r.label_b || 'B')}</button>`
  ).join('');

  renderDetailContent();
  DOM.resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function renderDetailContent() {
  if (!state.results) return;
  const result = state.results.results[state.activePairIndex];
  if (!result) {
    DOM.detailContent.innerHTML = '<div class="segment-card" style="text-align:center;padding:var(--space-2xl);color:var(--text-tertiary)">请选择一个比对结果查看详情</div>';
    return;
  }

  const segments = result.segments || [];
  if (segments.length === 0) {
    DOM.detailContent.innerHTML = `<div class="segment-card" style="text-align:center;padding:var(--space-2xl);color:var(--text-tertiary)">未发现匹配的重复段落</div>`;
    return;
  }

  DOM.detailContent.innerHTML = segments.map(seg => {
    const simPct = Math.round(seg.similarity * 100);
    const simClass = simPct >= 90 ? 'high' : simPct >= 75 ? 'medium' : 'low';
    return `<div class="segment-card">
      <div class="segment-header">
        <span class="segment-id">#${seg.id + 1}</span>
        <span class="segment-similarity similarity-${simClass}">相似度 ${simPct}%</span>
      </div>
      <div class="segment-compare">
        <div class="segment-panel">
          <div class="segment-panel-label">${escHtml(result.label_a || '文档 A')}</div>
          <div class="segment-panel-text">${escHtml(seg.tender_text)}</div>
        </div>
        <div class="segment-panel">
          <div class="segment-panel-label">${escHtml(result.label_b || '文档 B')}</div>
          <div class="segment-panel-text">${escHtml(seg.bid_text)}</div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function setActivePair(idx) {
  state.activePairIndex = idx;
  document.querySelectorAll('.result-card').forEach(c => c.classList.toggle('active', parseInt(c.dataset.pairIndex) === idx));
  document.querySelectorAll('.detail-tab').forEach(t => t.classList.toggle('active', parseInt(t.dataset.pairIndex) === idx));
  renderDetailContent();
}

async function resetAll() {
  try { await fetch('/api/clear', { method: 'POST' }); } catch (e) {}
  state.documents = [];
  state.results = null;
  state.isAnalyzing = false;
  state.activePairIndex = 0;
  state.docCounter = 0;
  DOM.resultsSection.classList.add('hidden');
  DOM.uploadSection.classList.remove('hidden');
  DOM.compareBtn.disabled = true;
  DOM.progressBar.classList.add('hidden');
  renderDocSlots();
}

// ── Helpers ────────────────────────────────────────────
function updateCompareButton() {
  const readyCount = state.documents.filter(d => d.status === 'parsed' || d.status === 'parsed_large').length;
  DOM.compareBtn.disabled = readyCount < 2 || state.isAnalyzing;
}

function setProgress(pct, text) { DOM.progressFill.style.width = pct + '%'; DOM.progressText.textContent = text; }
function showError(msg) { alert('错误: ' + msg); }
function escHtml(str) { if (!str) return ''; const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }
function formatSize(chars) { if (!chars) return '0'; if (chars >= 10000) return (chars / 10000).toFixed(1) + '万'; if (chars >= 1000) return (chars / 1000).toFixed(1) + 'k'; return String(chars); }

// ── API Key ────────────────────────────────────────────
function saveApiKeyToStorage(key) { try { localStorage.setItem('docdiff_api_key', key); } catch (e) {} }
function loadApiKeyFromStorage() { try { const k = localStorage.getItem('docdiff_api_key'); if (k) DOM.apiKeyInput.value = k; } catch (e) {} }
function toggleApiKeyVisibility() { DOM.apiKeyInput.type = DOM.apiKeyInput.type === 'password' ? 'text' : 'password'; }
