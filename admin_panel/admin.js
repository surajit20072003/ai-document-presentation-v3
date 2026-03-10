// Admin Panel JavaScript
let adminKey = '';
let currentPromptFile = '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    updateServerTime();
    setInterval(updateServerTime, 1000);
});

function setupEventListeners() {
    // Login
    document.getElementById('login-btn').addEventListener('click', login);
    document.getElementById('admin-key-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Prompts
    document.getElementById('save-prompt-btn').addEventListener('click', savePrompt);
    document.getElementById('close-editor-btn').addEventListener('click', closeEditor);

    // Config
    document.getElementById('save-config-btn').addEventListener('click', saveConfig);

    // System
    document.getElementById('refresh-info-btn').addEventListener('click', loadSystemInfo);
    document.getElementById('restart-docker-btn').addEventListener('click', restartDocker);
    document.getElementById('fetch-logs-btn').addEventListener('click', fetchLogs);
}

function updateServerTime() {
    const now = new Date();
    document.getElementById('server-time').textContent = now.toLocaleTimeString();
}

// ============================================
// Authentication
// ============================================

async function login() {
    const keyInput = document.getElementById('admin-key-input');
    const errorEl = document.getElementById('login-error');
    adminKey = keyInput.value.trim();

    if (!adminKey) {
        errorEl.textContent = 'Please enter admin key';
        return;
    }

    try {
        // Test auth by fetching system info
        const response = await fetch('/admin/api/system-info', {
            headers: { 'X-Admin-Key': adminKey }
        });

        if (response.ok) {
            document.getElementById('login-screen').style.display = 'none';
            document.getElementById('main-content').style.display = 'block';
            loadPrompts();
            loadConfig();
            loadSystemInfo();
        } else {
            const data = await response.json();
            errorEl.textContent = data.error || 'Invalid admin key';
        }
    } catch (err) {
        errorEl.textContent = 'Connection error: ' + err.message;
    }
}

// ============================================
// Tab Switching
// ============================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
}

// ============================================
// Prompts Management
// ============================================

async function loadPrompts() {
    const container = document.getElementById('prompts-container');
    const loading = document.getElementById('prompts-loading');

    try {
        const response = await fetch('/admin/api/prompts', {
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();
        loading.style.display = 'none';

        if (data.prompts) {
            container.innerHTML = data.prompts.map(prompt => `
                <div class="prompt-card" onclick="loadPromptContent('${prompt.filename}')">
                    <h3>${prompt.filename}</h3>
                    <div class="file-info">
                        <p>Size: ${formatBytes(prompt.size)}</p>
                        <p>Modified: ${new Date(prompt.modified * 1000).toLocaleString()}</p>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        container.innerHTML = `<p class="error-message">Error loading prompts: ${err.message}</p>`;
    }
}

async function loadPromptContent(filename) {
    currentPromptFile = filename;
    const editorPanel = document.getElementById('prompt-editor');
    const filenameEl = document.getElementById('editor-filename');
    const contentEl = document.getElementById('prompt-content');

    try {
        const response = await fetch(`/admin/api/prompts/${filename}`, {
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();

        if (data.content !== undefined) {
            filenameEl.textContent = filename;
            contentEl.value = data.content;
            editorPanel.style.display = 'block';
            // Scroll to editor
            editorPanel.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (err) {
        showEditorStatus(`Error loading ${filename}: ${err.message}`, 'error');
    }
}

async function savePrompt() {
    const statusEl = document.getElementById('editor-status');
    const content = document.getElementById('prompt-content').value;

    try {
        const response = await fetch(`/admin/api/prompts/${currentPromptFile}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Key': adminKey
            },
            body: JSON.stringify({ content })
        });

        const data = await response.json();

        if (data.success) {
            showEditorStatus('✅ Prompt saved successfully!', 'success');
            loadPrompts(); // Refresh list
        } else {
            showEditorStatus('❌ ' + (data.error || 'Save failed'), 'error');
        }
    } catch (err) {
        showEditorStatus('❌ Error: ' + err.message, 'error');
    }
}

function closeEditor() {
    document.getElementById('prompt-editor').style.display = 'none';
    document.getElementById('editor-status').textContent = '';
}

function showEditorStatus(message, type) {
    const statusEl = document.getElementById('editor-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'status-message';
    }, 5000);
}

// ============================================
// Config Management
// ============================================

async function loadConfig() {
    const loading = document.getElementById('config-loading');
    const container = document.getElementById('config-container');
    const fieldsDiv = document.getElementById('config-fields');

    try {
        const response = await fetch('/admin/api/config', {
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();
        loading.style.display = 'none';
        container.style.display = 'block';

        if (data.config) {
            fieldsDiv.innerHTML = Object.entries(data.config).map(([key, value]) => `
                <div class="config-field">
                    <label for="config-${key}">${key}</label>
                    <input type="text" id="config-${key}" value="${value}" data-key="${key}" />
                </div>
            `).join('');
        }
    } catch (err) {
        loading.textContent = `Error loading config: ${err.message}`;
    }
}

async function saveConfig() {
    const statusEl = document.getElementById('config-status');
    const config = {};

    document.querySelectorAll('#config-fields input').forEach(input => {
        config[input.dataset.key] = input.value;
    });

    try {
        const response = await fetch('/admin/api/config', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Key': adminKey
            },
            body: JSON.stringify({ config })
        });

        const data = await response.json();

        if (data.success) {
            statusEl.textContent = '✅ Configuration saved successfully!';
            statusEl.className = 'status-message success';
        } else {
            statusEl.textContent = '❌ ' + (data.error || 'Save failed');
            statusEl.className = 'status-message error';
        }

        setTimeout(() => {
            statusEl.textContent = '';
            statusEl.className = 'status-message';
        }, 5000);
    } catch (err) {
        statusEl.textContent = '❌ Error: ' + err.message;
        statusEl.className = 'status-message error';
    }
}

// ============================================
// System Management
// ============================================

async function loadSystemInfo() {
    try {
        const response = await fetch('/admin/api/system-info', {
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();

        if (data) {
            document.getElementById('pipeline-version').textContent = data.pipeline_version || '-';
            document.getElementById('python-version').textContent = data.python_version || '-';
            document.getElementById('platform-info').textContent = data.platform || '-';
            document.getElementById('total-jobs').textContent = data.total_jobs || '0';
        }
    } catch (err) {
        console.error('Error loading system info:', err);
    }
}

async function restartDocker() {
    const statusEl = document.getElementById('docker-status');
    const btn = document.getElementById('restart-docker-btn');

    if (!confirm('Are you sure you want to restart the Docker container? This will interrupt running jobs.')) {
        return;
    }

    btn.disabled = true;
    statusEl.textContent = '⏳ Restarting container...';
    statusEl.className = 'status-message';

    try {
        const response = await fetch('/admin/api/restart', {
            method: 'POST',
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();

        if (data.success) {
            statusEl.textContent = '✅ Container restarted successfully!';
            statusEl.className = 'status-message success';
        } else {
            statusEl.textContent = '❌ ' + (data.error || 'Restart failed');
            statusEl.className = 'status-message error';
        }
    } catch (err) {
        statusEl.textContent = '❌ Error: ' + err.message;
        statusEl.className = 'status-message error';
    } finally {
        btn.disabled = false;
    }

    setTimeout(() => {
        statusEl.textContent = '';
    }, 10000);
}

async function fetchLogs() {
    const logsEl = document.getElementById('logs-content');
    const btn = document.getElementById('fetch-logs-btn');

    btn.disabled = true;
    logsEl.textContent = 'Loading logs...';

    try {
        const response = await fetch('/admin/api/logs?lines=100', {
            headers: { 'X-Admin-Key': adminKey }
        });

        const data = await response.json();

        if (data.logs) {
            logsEl.textContent = data.logs;
        } else {
            logsEl.textContent = 'Error: ' + (data.error || 'No logs available');
        }
    } catch (err) {
        logsEl.textContent = 'Error fetching logs: ' + err.message;
    } finally {
        btn.disabled = false;
    }
}

// ============================================
// Utility Functions
// ============================================

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
