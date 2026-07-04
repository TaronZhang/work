// Documents page — upload + project list

let currentProjects = [];

document.addEventListener('DOMContentLoaded', () => {
    setupUploadZone('upload-zone', 'file-input', handleFileUpload);
    loadProjects();
});

async function handleFileUpload(file) {
    const progressEl = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');

    progressEl.classList.remove('hidden');
    progressText.textContent = `正在上传 ${file.name}...`;

    try {
        await uploadFile(file, (pct) => {
            progressFill.style.width = `${pct}%`;
            progressText.textContent = `上传中 ${pct}% — ${file.name}`;
        });
        showToast('上传成功，正在解析...', 'success');
        progressEl.classList.add('hidden');
        loadProjects();
    } catch (err) {
        showToast(`上传失败: ${err.message}`, 'error');
        progressEl.classList.add('hidden');
    }
}

async function loadProjects() {
    try {
        const data = await apiGet('/api/documents');
        currentProjects = data.projects || [];
        renderProjects();
    } catch (err) {
        showToast(`加载失败: ${err.message}`, 'error');
    }
}

function renderProjects() {
    const tbody = document.getElementById('project-table-body');
    const emptyEl = document.getElementById('empty-projects');
    const countEl = document.getElementById('project-count');

    countEl.textContent = `共 ${currentProjects.length} 个项目`;

    if (currentProjects.length === 0) {
        tbody.innerHTML = '';
        emptyEl.classList.remove('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    tbody.innerHTML = currentProjects.map(p => `
        <tr>
            <td>
                <a href="/extraction/${p.id}" style="color:var(--accent-blue);text-decoration:none;">
                    ${escapeHtml(p.project_name || '(未提取)')}
                </a>
            </td>
            <td>${escapeHtml(p.bidder_name || '--')}</td>
            <td>${formatDate(p.submission_deadline)}</td>
            <td>${statusBadge(p.status)}</td>
            <td>
                <button class="btn btn-sm btn-ghost" onclick="viewProject(${p.id})">查看</button>
                <button class="btn btn-sm btn-danger" onclick="deleteProject(${p.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function viewProject(id) {
    window.location.href = `/extraction/${id}`;
}

async function deleteProject(id) {
    if (!confirm('确定删除此项目及所有关联文件？')) return;
    try {
        await apiDelete(`/api/documents/${id}`);
        showToast('删除成功', 'success');
        loadProjects();
    } catch (err) {
        showToast(`删除失败: ${err.message}`, 'error');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
