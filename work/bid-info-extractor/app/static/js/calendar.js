// Calendar events page

document.addEventListener('DOMContentLoaded', () => {
    loadEvents();
});

async function loadEvents() {
    try {
        const data = await apiGet('/api/calendar/events');
        const events = data.events || [];
        renderEvents(events);
    } catch (err) {
        showToast(`加载失败: ${err.message}`, 'error');
    }
}

function renderEvents(events) {
    const tbody = document.getElementById('event-table-body');
    const emptyEl = document.getElementById('empty-events');
    const countEl = document.getElementById('event-count');
    countEl.textContent = `共 ${events.length} 个事件`;

    if (events.length === 0) {
        tbody.innerHTML = '';
        emptyEl.classList.remove('hidden');
        return;
    }

    emptyEl.classList.add('hidden');
    tbody.innerHTML = events.map(e => `
        <tr>
            <td>${escapeHtml(e.project_name || '--')}</td>
            <td>${formatDate(e.event_date)}</td>
            <td>${formatDate(e.slot_start)} — ${formatDate(e.slot_end)}</td>
            <td>${formatDate(e.deadline)}</td>
            <td>${statusBadge(e.status)}</td>
            <td>
                ${e.status === 'failed'
                    ? `<button class="btn btn-sm btn-primary" onclick="retryEvent(${e.id})">重试</button>`
                    : ''}
                <button class="btn btn-sm btn-danger" onclick="deleteEvent(${e.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

async function retryEvent(id) {
    try {
        await apiPost(`/api/calendar/events/${id}/retry`);
        showToast('已重试', 'success');
        loadEvents();
    } catch (err) {
        showToast(`重试失败: ${err.message}`, 'error');
    }
}

async function deleteEvent(id) {
    if (!confirm('确定删除此日历事件？')) return;
    try {
        await apiDelete(`/api/calendar/events/${id}`);
        showToast('已删除', 'success');
        loadEvents();
    } catch (err) {
        showToast(`删除失败: ${err.message}`, 'error');
    }
}
