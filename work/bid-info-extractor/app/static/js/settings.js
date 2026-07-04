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
        await fetch('/api/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        showToast('设置已保存', 'success');
    } catch (err) {
        showToast(`保存失败: ${err.message}`, 'error');
    }
}

async function testLLM() {
    const baseUrl = document.getElementById('cfg-llm-base-url').value.trim();
    const apiKey = document.getElementById('cfg-llm-api-key').value.trim();
    const model = document.getElementById('cfg-llm-model').value.trim();

    if (!baseUrl || !apiKey) {
        showToast('请先填写 Base URL 和 API Key', 'error');
        return;
    }

    try {
        const res = await fetch('/api/config/test-llm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: baseUrl, api_key: apiKey, model: model }),
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
