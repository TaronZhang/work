// Extraction page — metadata, tech sections, Excel, calendar

const projectId = (() => {
    const parts = window.location.pathname.split('/').filter(Boolean);
    return parseInt(parts[parts.length - 1]) || 0;
})();

document.addEventListener('DOMContentLoaded', () => {
    loadProject();
});

async function loadProject() {
    try {
        const data = await apiGet(`/api/documents/${projectId}`);
        const p = data.project;
        document.getElementById('meta-project-name').textContent = p.project_name || '(未提取)';
        document.getElementById('meta-bidder-name').textContent = p.bidder_name || '(未提取)';
        document.getElementById('meta-deadline').textContent = formatDate(p.submission_deadline);

        // Enable buttons based on state
        document.getElementById('btn-extract-meta').disabled = false;
        if (p.project_name) {
            document.getElementById('btn-generate-md').disabled = false;
            document.getElementById('btn-tech-sections').disabled = false;
            document.getElementById('btn-calendar').disabled = false;
        }

        // Load existing files
        if (data.documents && data.documents.length > 0) {
            renderFiles(data.documents);
        }

        // Load tech sections if already extracted
        if (data.tech_sections) {
            renderTechSections(JSON.parse(data.tech_sections));
        }

        document.getElementById('page-title').textContent =
            p.project_name || '提取结果';
    } catch (err) {
        showToast(`加载失败: ${err.message}`, 'error');
    }
}

async function extractMetadata() {
    // Confirm if re-extracting
    const currentName = document.getElementById('meta-project-name').textContent;
    if (currentName && currentName !== '(未提取)' && currentName !== '--') {
        if (!confirm('当前已有提取结果，重新提取将覆盖现有数据。确定继续？')) return;
    }
    const btn = document.getElementById('btn-extract-meta');
    btn.disabled = true;
    btn.textContent = '⏳ 提取中...';
    try {
        const data = await apiPost('/api/extraction/metadata', { project_id: projectId });
        document.getElementById('meta-project-name').textContent = data.project_name;
        document.getElementById('meta-bidder-name').textContent = data.bidder_name || '--';
        document.getElementById('meta-deadline').textContent = formatDate(data.submission_deadline);
        document.getElementById('btn-generate-md').disabled = false;
        document.getElementById('btn-tech-sections').disabled = false;
        document.getElementById('btn-calendar').disabled = false;
        showToast('元数据提取完成', 'success');
    } catch (err) {
        showToast(`提取失败: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 提取元数据';
    }
}

async function generateMarkdown() {
    const btn = document.getElementById('btn-generate-md');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';
    try {
        const data = await apiPost('/api/extraction/generate-markdown', { project_id: projectId });
        showToast('Markdown 已生成', 'success');
        loadProject();
    } catch (err) {
        showToast(`生成失败: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📄 生成 Markdown';
    }
}

async function extractTechSections() {
    const btn = document.getElementById('btn-tech-sections');
    btn.disabled = true;
    btn.textContent = '⏳ 识别中...';
    try {
        const data = await apiPost('/api/extraction/tech-sections', { project_id: projectId });
        renderTechSections(data.sections);
        document.getElementById('btn-generate-excel').disabled = false;
        showToast(`已识别 ${data.sections?.length || 0} 个技术要求章节`, 'success');
    } catch (err) {
        showToast(`识别失败: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔬 识别技术要求';
    }
}

function renderTechSections(sections) {
    const panel = document.getElementById('tech-sections-panel');
    const list = document.getElementById('tech-section-list');
    const count = document.getElementById('tech-section-count');

    panel.style.display = 'block';
    count.textContent = `共 ${sections.length} 个章节`;

    list.innerHTML = sections.map((s, i) => `
        <li class="section-item">
            <div class="section-title" onclick="toggleSection(this)" data-expanded="false">
                <span>${i + 1}. ${escapeHtml(s.title || '(无标题)')}</span>
                <span style="font-size:12px;color:var(--text-tertiary);">展开 ▼</span>
            </div>
            <div class="section-content" style="display:none;">${escapeHtml(s.content || '')}</div>
        </li>
    `).join('');
}

function toggleSection(el) {
    const content = el.nextElementSibling;
    const expanded = el.dataset.expanded === 'true';
    el.dataset.expanded = String(!expanded);
    content.style.display = expanded ? 'none' : 'block';
    el.querySelector('span:last-child').textContent = expanded ? '展开 ▼' : '收起 ▲';
}

async function generateExcel() {
    const btn = document.getElementById('btn-generate-excel');
    btn.disabled = true;
    btn.textContent = '⏳ 生成中...';
    try {
        const data = await apiPost('/api/extraction/generate-excel', { project_id: projectId });
        showToast('Excel 已生成', 'success');
        loadProject();
    } catch (err) {
        showToast(`生成失败: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📊 生成 Excel';
    }
}

async function createCalendarEvent() {
    const btn = document.getElementById('btn-calendar');
    btn.disabled = true;
    btn.textContent = '⏳ 创建中...';
    try {
        const data = await apiPost('/api/calendar/create-event', { project_id: projectId });
        showToast(`日历事件已创建: ${formatDate(data.slot_start)}`, 'success');
    } catch (err) {
        showToast(`创建失败: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📅 创建日历提醒';
    }
}

function renderFiles(documents) {
    const panel = document.getElementById('files-panel');
    const list = document.getElementById('files-list');
    panel.style.display = 'block';
    list.innerHTML = documents.map(d => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:var(--space-sm) 0;">
            <span>${d.doc_type === 'markdown' ? '📄' : '📊'} ${escapeHtml(d.file_name)}</span>
            <a href="/api/documents/${d.id}/download" class="btn btn-sm btn-primary">下载</a>
        </div>
    `).join('');
}
