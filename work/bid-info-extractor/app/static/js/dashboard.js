// Dashboard — Calendar + Project List + Stats + Detail Panel

let allProjects = [];
let currentYear, currentMonth;
let selectedDate = null;
let activeFilter = 'active';
let selectedProjectId = null;

document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth();

    setupUploadZone('upload-mini', 'file-input', handleUpload);
    loadAllData();
});

// ── Data Loading ──────────────────────────────────

async function loadAllData() {
    try {
        const data = await apiGet('/api/documents');
        allProjects = data.projects || [];
        renderAll();
    } catch (err) {
        showToast('加载数据失败: ' + err.message, 'error');
    }
}

function renderAll() {
    renderStats();
    renderCalendar();
    renderProjectList();
}

// ── Stats ─────────────────────────────────────────

function renderStats() {
    const now = new Date();
    const active = allProjects.filter(p => {
        if (!p.submission_deadline) return false;
        return new Date(p.submission_deadline) >= now;
    });
    const ended = allProjects.filter(p => {
        if (!p.submission_deadline) return false;
        return new Date(p.submission_deadline) < now;
    });
    const urgent = active.filter(p => {
        const dl = new Date(p.submission_deadline);
        return (dl - now) / (1000 * 60 * 60 * 24) <= 7;
    });

    document.getElementById('stat-active').textContent = active.length;
    document.getElementById('stat-ended').textContent = ended.length;
    document.getElementById('stat-urgent').textContent = urgent.length;
    document.getElementById('stat-total').textContent = allProjects.length;
}

function filterByStatus(filter, el) {
    activeFilter = filter;
    document.querySelectorAll('.stat-item').forEach(s => s.classList.remove('active-filter'));
    if (el) el.classList.add('active-filter');
    renderProjectList();
}

// ── Calendar ──────────────────────────────────────

function navigateMonth(delta) {
    if (delta === 0) {
        const now = new Date();
        currentYear = now.getFullYear();
        currentMonth = now.getMonth();
    } else {
        currentMonth += delta;
        if (currentMonth > 11) { currentMonth = 0; currentYear++; }
        if (currentMonth < 0) { currentMonth = 11; currentYear--; }
    }
    renderCalendar();
}

function renderCalendar() {
    const title = document.getElementById('cal-title');
    title.textContent = `${currentYear}年 ${currentMonth + 1}月`;

    const grid = document.getElementById('cal-grid');
    grid.innerHTML = '';

    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;

    // Build a map: dateStr -> [projects]
    const dateMap = {};
    allProjects.forEach(p => {
        if (p.submission_deadline) {
            const d = new Date(p.submission_deadline);
            const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
            if (!dateMap[key]) dateMap[key] = [];
            dateMap[key].push(p);
        }
        if (p.bid_obtain_deadline) {
            const d = new Date(p.bid_obtain_deadline);
            const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
            if (!dateMap[key]) dateMap[key] = [];
            // Mark as obtain deadline type
            const pCopy = {...p, _type: 'obtain'};
            dateMap[key].push(pCopy);
        }
    });

    // Previous month padding
    const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
        const day = prevMonthLastDay - i;
        grid.appendChild(createCalCell(day, 'other-month', null, dateMap));
    }

    // Current month
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${currentYear}-${String(currentMonth+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const classes = [];
        if (dateStr === todayStr) classes.push('today');
        if (selectedDate === dateStr) classes.push('selected');

        const events = dateMap[dateStr] || [];
        grid.appendChild(createCalCell(day, classes.join(' '), dateStr, null, events));
    }

    // Next month padding
    const totalCells = startDayOfWeek + daysInMonth;
    const remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let day = 1; day <= remaining; day++) {
        grid.appendChild(createCalCell(day, 'other-month', null, dateMap));
    }
}

function createCalCell(day, cls, dateStr, _dateMap, events) {
    const cell = document.createElement('div');
    cell.className = 'cal-cell ' + (cls || '');
    cell.innerHTML = `<div class="cal-date">${day}</div>`;

    if (events && events.length > 0) {
        const toShow = events.slice(0, 2); // Show max 2 events
        toShow.forEach(ev => {
            const now = new Date();
            const isEnded = ev.submission_deadline && new Date(ev.submission_deadline) < now;
            const isUrgent = !isEnded && ev.submission_deadline &&
                (new Date(ev.submission_deadline) - now) / (1000*60*60*24) <= 7;
            let evClass = '';
            if (isEnded) evClass = 'ended';
            else if (isUrgent) evClass = 'urgent';

            const name = ev.bidder_name || ev.project_name || '(未命名)';
            cell.innerHTML += `<div class="cal-event ${evClass}" title="${escapeHtml(name)}">${escapeHtml(name)}</div>`;
        });
        if (events.length > 2) {
            cell.innerHTML += `<div class="cal-event-more">+${events.length - 2} 更多</div>`;
        }
    }

    if (dateStr) {
        cell.addEventListener('click', () => {
            selectedDate = dateStr;
            renderCalendar();
            filterByDate(dateStr);
        });
    }

    return cell;
}

function filterByDate(dateStr) {
    activeFilter = 'date';
    document.querySelectorAll('.stat-item').forEach(s => s.classList.remove('active-filter'));
    renderProjectList(dateStr);
}

// ── Project List ──────────────────────────────────

function renderProjectList(dateFilter) {
    const container = document.getElementById('project-list');
    const countEl = document.getElementById('pl-count');
    const now = new Date();

    let filtered = allProjects;

    // Apply filters
    if (dateFilter) {
        filtered = filtered.filter(p => {
            const sd = p.submission_deadline ? new Date(p.submission_deadline) : null;
            return sd && `${sd.getFullYear()}-${String(sd.getMonth()+1).padStart(2,'0')}-${String(sd.getDate()).padStart(2,'0')}` === dateFilter;
        });
    } else if (activeFilter === 'active') {
        filtered = filtered.filter(p => p.submission_deadline && new Date(p.submission_deadline) >= now);
    } else if (activeFilter === 'ended') {
        filtered = filtered.filter(p => p.submission_deadline && new Date(p.submission_deadline) < now);
    } else if (activeFilter === 'urgent') {
        filtered = filtered.filter(p => {
            if (!p.submission_deadline) return false;
            const dl = new Date(p.submission_deadline);
            return dl >= now && (dl - now) / (1000*60*60*24) <= 7;
        });
    }

    // Sort by deadline
    filtered.sort((a, b) => {
        if (!a.submission_deadline) return 1;
        if (!b.submission_deadline) return -1;
        return new Date(a.submission_deadline) - new Date(b.submission_deadline);
    });

    countEl.textContent = `共 ${filtered.length} 个`;

    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无匹配项目</div>';
        return;
    }

    container.innerHTML = filtered.map((p, i) => {
        const isEnded = p.submission_deadline && new Date(p.submission_deadline) < now;
        const isSelected = p.id === selectedProjectId;
        return `
            <div class="pl-item ${isSelected ? 'selected' : ''}" onclick="openDetail(${p.id})">
                <div class="pl-item-name">
                    <span style="color:var(--text-tertiary);font-size:11px;">#${i+1}</span>
                    ${escapeHtml(p.project_name || '(未提取)')}
                    ${isEnded ? ' <span class="badge badge-failed">已结束</span>' : statusBadge(p.status)}
                </div>
                <div class="pl-item-client">${escapeHtml(p.bidder_name || '--')}</div>
                <div class="pl-item-dates">
                    ${p.bid_obtain_deadline ? '<span>📥 获取: ' + formatDate(p.bid_obtain_deadline) + '</span>' : ''}
                    ${p.submission_deadline ? '<span>📅 截止: ' + formatDate(p.submission_deadline) + '</span>' : '<span>无截止日期</span>'}
                </div>
            </div>
        `;
    }).join('');
}

// ── Detail Panel ──────────────────────────────────

async function openDetail(projectId) {
    selectedProjectId = projectId;
    renderProjectList();

    try {
        const data = await apiGet(`/api/documents/${projectId}`);
        const p = data.project;
        const docs = data.documents || [];

        document.getElementById('detail-title').textContent = p.project_name || '项目详情';
        document.getElementById('detail-body').innerHTML = `
            <div class="form-group">
                <label class="form-label">项目名称</label>
                <input class="form-input" id="edit-project-name" value="${escapeHtml(p.project_name || '')}">
            </div>
            <div class="form-group">
                <label class="form-label">客户名称</label>
                <input class="form-input" id="edit-bidder-name" value="${escapeHtml(p.bidder_name || '')}">
            </div>
            <div class="form-group">
                <label class="form-label">标书获取截止日期</label>
                <input class="form-input" type="datetime-local" id="edit-obtain-deadline"
                    value="${p.bid_obtain_deadline ? p.bid_obtain_deadline.substring(0,16) : ''}">
            </div>
            <div class="form-group">
                <label class="form-label">投标截止日期</label>
                <input class="form-input" type="datetime-local" id="edit-submission-deadline"
                    value="${p.submission_deadline ? p.submission_deadline.substring(0,16) : ''}">
            </div>
            <div class="form-group">
                <label class="form-label">状态</label>
                <select class="form-select" id="edit-status">
                    <option value="imported" ${p.status==='imported'?'selected':''}>已导入</option>
                    <option value="extracted" ${p.status==='extracted'?'selected':''}>已提取</option>
                    <option value="completed" ${p.status==='completed'?'selected':''}>已完成</option>
                </select>
            </div>
            ${docs.length > 0 ? `
            <div class="form-group">
                <label class="form-label">生成文件</label>
                ${docs.map(d => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;">
                        <span style="font-size:13px;">${d.doc_type === 'markdown' ? '📄' : '📊'} ${escapeHtml(d.file_name)}</span>
                        ${d.doc_type === 'excel'
                            ? `<button class="btn btn-sm btn-primary" onclick="runDownloadExcel(${projectId})">下载(最新)</button>`
                            : `<a href="/api/documents/${d.id}/download" class="btn btn-sm btn-primary">下载</a>`
                        }
                    </div>
                `).join('')}
            </div>
            ` : ''}
        `;

        // Action buttons
        const actions = document.getElementById('detail-actions');
        actions.innerHTML = `
            <button class="btn btn-primary" onclick="saveDetail(${projectId})">💾 保存</button>
            <button class="btn btn-primary" onclick="runExtraction(${projectId})">🔍 提取元数据</button>
            <button class="btn btn-success" onclick="runGenerateExcel(${projectId})">📊 生成 Excel</button>
            <button class="btn btn-primary" onclick="runCreateCalendar(${projectId})">📅 创建日历提醒</button>
            <button class="btn btn-danger btn-sm" onclick="deleteProjectFromDetail(${projectId})">🗑 删除</button>
        `;

        document.getElementById('detail-overlay').classList.add('open');
        document.getElementById('detail-panel').classList.add('open');
    } catch (err) {
        showToast('加载详情失败: ' + err.message, 'error');
    }
}

function closeDetail() {
    document.getElementById('detail-overlay').classList.remove('open');
    document.getElementById('detail-panel').classList.remove('open');
    selectedProjectId = null;
    renderProjectList();
}

async function saveDetail(projectId) {
    const data = {
        project_name: document.getElementById('edit-project-name').value,
        bidder_name: document.getElementById('edit-bidder-name').value,
        bid_obtain_deadline: document.getElementById('edit-obtain-deadline').value || null,
        submission_deadline: document.getElementById('edit-submission-deadline').value || null,
        status: document.getElementById('edit-status').value,
    };
    try {
        await apiPost(`/api/documents/${projectId}/update`, data);
        showToast('保存成功', 'success');
        loadAllData();
        closeDetail();
    } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
    }
}

// ── Actions ───────────────────────────────────────

async function runExtraction(projectId) {
    showToast('正在提取元数据...', 'info');
    try {
        await apiPost('/api/extraction/metadata', { project_id: projectId });
        showToast('元数据提取完成', 'success');
        loadAllData();
        openDetail(projectId);
    } catch (err) {
        showToast('提取失败: ' + err.message, 'error');
    }
}

async function runGenerateExcel(projectId) {
    showToast('正在生成 Excel...', 'info');
    try {
        const resp = await fetch(`/api/extraction/${projectId}/download-excel`);
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '生成失败');
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '技术偏离表.xlsx';
        a.click();
        URL.revokeObjectURL(url);
        showToast('Excel 已下载', 'success');
    } catch (err) {
        showToast('生成失败: ' + err.message, 'error');
    }
}

async function runDownloadExcel(projectId) {
    try {
        const resp = await fetch(`/api/extraction/${projectId}/download-excel`);
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '下载失败');
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = '技术偏离表.xlsx';
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        showToast('下载失败: ' + err.message, 'error');
    }
}

async function runCreateCalendar(projectId) {
    showToast('正在创建日历事件...', 'info');
    try {
        await apiPost('/api/calendar/create-event', { project_id: projectId });
        showToast('日历事件已创建', 'success');
    } catch (err) {
        showToast('创建失败: ' + err.message, 'error');
    }
}

async function deleteProjectFromDetail(projectId) {
    if (!confirm('确定删除此项目及所有关联文件？')) return;
    try {
        await apiDelete(`/api/documents/${projectId}`);
        showToast('已删除', 'success');
        closeDetail();
        loadAllData();
    } catch (err) {
        showToast('删除失败: ' + err.message, 'error');
    }
}

// ── Upload ────────────────────────────────────────

async function handleUpload(file) {
    const progressEl = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    progressEl.classList.remove('hidden');
    progressText.textContent = `正在上传 ${file.name}...`;
    try {
        const result = await uploadFile(file, (pct) => {
            progressFill.style.width = `${pct}%`;
            progressText.textContent = `上传中 ${pct}% — ${file.name}`;
        });
        if (result.auto_extracted) {
            showToast(`上传成功！已自动提取: ${result.project_name || result.bidder_name || '项目'}`, 'success');
        } else if (result.extract_error) {
            showToast(`上传成功，但自动提取失败: ${result.extract_error}`, 'info');
        } else {
            showToast('上传成功！请配置 LLM API Key 以启用自动提取', 'info');
        }
        progressEl.classList.add('hidden');
        loadAllData();
    } catch (err) {
        showToast(`上传失败: ${err.message}`, 'error');
        progressEl.classList.add('hidden');
    }
}
