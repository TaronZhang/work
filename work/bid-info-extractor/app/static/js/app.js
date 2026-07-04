// BidInfo Extractor — Common JS utilities

const API_BASE = '/api';

// ── Toast notifications ────────────────────────────
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.add('hidden'), duration);
}

// ── API helpers ─────────────────────────────────────
async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiPost(url, data) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

async function apiDelete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
}

// ── Upload helper ───────────────────────────────────
async function uploadFile(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);

    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
                onProgress(Math.round((e.loaded / e.total) * 100));
            }
        });
        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(xhr.responseText));
            }
        });
        xhr.addEventListener('error', () => reject(new Error('上传失败')));
        xhr.open('POST', `${API_BASE}/documents/upload`);
        xhr.send(formData);
    });
}

// ── Format helpers ──────────────────────────────────
function formatDate(dateStr) {
    if (!dateStr) return '--';
    const d = new Date(dateStr);
    return d.toLocaleDateString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
    });
}

function statusBadge(status) {
    const map = {
        imported: 'badge-imported',
        extracted: 'badge-extracted',
        completed: 'badge-completed',
        pending: 'badge-pending',
        created: 'badge-created',
        failed: 'badge-failed',
    };
    const cls = map[status] || 'badge-imported';
    const labels = {
        imported: '已导入', extracted: '已提取', completed: '已完成',
        pending: '待创建', created: '已创建', failed: '失败',
    };
    return `<span class="badge ${cls}">${labels[status] || status}</span>`;
}

// ── Upload zone setup ───────────────────────────────
function setupUploadZone(zoneId, inputId, onSuccess) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && onSuccess) onSuccess(file);
    });
    input.addEventListener('change', () => {
        const file = input.files[0];
        if (file && onSuccess) onSuccess(file);
    });
}
