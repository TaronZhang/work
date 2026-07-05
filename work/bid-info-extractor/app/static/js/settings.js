// Settings page

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
});

async function loadSettings() {
    try {
        const data = await apiGet('/api/config');
        document.getElementById('cfg-llm-base-url').value = data.llm_base_url || '';
        document.getElementById('cfg-llm-api-key').value = data.llm_api_key || '';
        document.getElementById('cfg-llm-model').value = data.llm_model || '';
        document.getElementById('cfg-feishu-app-id').value = data.feishu_app_id || '';
        document.getElementById('cfg-feishu-app-secret').value = data.feishu_app_secret || '';
        document.getElementById('cfg-techtoexcel-path').value = data.techtoexcel_path || '';
        document.getElementById('cfg-techtoexcel-args').value = data.techtoexcel_args || '';
        document.getElementById('cfg-api-token').value = data.api_auth_token || '';

        // Show encryption status
        const statusEl = document.getElementById('security-status');
        statusEl.style.display = 'block';
        if (data.encryption_enabled) {
            statusEl.style.background = 'var(--green-bg)';
            statusEl.style.border = '1px solid rgba(61,214,140,0.3)';
            statusEl.style.color = 'var(--green)';
            statusEl.innerHTML = '🔒 加密存储已启用 — API Key、App Secret、Token 等敏感信息以 AES-256-GCM 加密存储';
        } else {
            statusEl.style.background = 'var(--amber-bg)';
            statusEl.style.border = '1px solid rgba(240,192,64,0.3)';
            statusEl.style.color = 'var(--amber)';
            statusEl.innerHTML = '⚠️ 加密存储未启用 — 请设置环境变量 ENCRYPTION_MASTER_PASSWORD 以启用加密保护';
        }
    } catch (err) {
        showToast(`加载设置失败: ${err.message}`, 'error');
    }
}

async function saveSettings() {
    const config = {
        llm_base_url: document.getElementById('cfg-llm-base-url').value.trim(),
        llm_api_key: document.getElementById('cfg-llm-api-key').value.trim(),
        llm_model: document.getElementById('cfg-llm-model').value.trim(),
        feishu_app_id: document.getElementById('cfg-feishu-app-id').value.trim(),
        feishu_app_secret: document.getElementById('cfg-feishu-app-secret').value.trim(),
        techtoexcel_path: document.getElementById('cfg-techtoexcel-path').value.trim(),
        techtoexcel_args: document.getElementById('cfg-techtoexcel-args').value.trim(),
    };
    try {
        const res = await apiPost('/api/config', config);
        showToast(`设置已保存${res.encrypted_fields?.length ? ' (已加密)' : ''}`, 'success');
        loadSettings();
    } catch (err) {
        showToast(`保存失败: ${err.message}`, 'error');
    }
}

async function testLLM() {
    const baseUrl = document.getElementById('cfg-llm-base-url').value.trim();
    const apiKey = document.getElementById('cfg-llm-api-key').value.trim();
    const model = document.getElementById('cfg-llm-model').value.trim();

    if (!apiKey) {
        showToast('请先填写 API Key', 'error');
        return;
    }

    try {
        const res = await fetch('/api/config/test-llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                llm_base_url: baseUrl,
                llm_api_key: apiKey,
                llm_model: model,
                feishu_app_id: '', feishu_app_secret: '',
                techtoexcel_path: '', techtoexcel_args: '',
            }),
        });
        const data = await res.json();
        if (data.success) {
            showToast(`连接成功 — 模型: ${data.model}`, 'success');
        } else {
            showToast(`连接失败: ${data.error}`, 'error');
        }
    } catch (err) {
        showToast(`测试失败: ${err.message}`, 'error');
    }
}

async function generateToken() {
    if (!confirm('生成新 Token 后，旧 Token 将失效。确定继续？')) return;
    try {
        const res = await fetch('/api/config/generate-token', { method: 'POST' });
        const data = await res.json();
        document.getElementById('cfg-api-token').value = data.token;
        showToast('Token 已生成，请复制保存！', 'success');
        // Copy to clipboard
        navigator.clipboard.writeText(data.token).then(() => {
            showToast('Token 已复制到剪贴板', 'info');
        }).catch(() => {});
    } catch (err) {
        showToast(`生成失败: ${err.message}`, 'error');
    }
}
