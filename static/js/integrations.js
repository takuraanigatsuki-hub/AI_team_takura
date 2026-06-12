/**
 * Cursor SDK + Figma — панели и вкладка Design
 */
(function (global) {
    let cursorStatus = null;
    let figmaStatus = null;

    async function loadFigmaStatus() {
        try {
            const resp = await fetch('/api/figma/status');
            if (resp.ok) figmaStatus = await resp.json();
        } catch (_) {}
        renderFigmaAccount();
    }

    function renderFigmaAccount() {
        const label = document.getElementById('figmaAccountLabel');
        const dot = document.getElementById('figmaAccountDot');
        const connectBtn = document.getElementById('figmaConnectBtn');
        const disconnectBtn = document.getElementById('figmaDisconnectBtn');
        if (!label) return;

        const s = figmaStatus || {};
        if (s.auth_method === 'oauth') {
            const who = s.user_handle || s.user_email || s.user_name || 'Figma';
            label.textContent = `✓ ${who}`;
            if (dot) dot.className = 'figma-account-dot connected';
            connectBtn?.classList.add('hidden');
            disconnectBtn?.classList.remove('hidden');
        } else if (s.auth_method === 'pat') {
            label.textContent = '✓ Personal Token (.env)';
            if (dot) dot.className = 'figma-account-dot connected';
            connectBtn?.classList.remove('hidden');
            connectBtn.textContent = s.oauth_app_configured ? 'Подключить OAuth' : 'OAuth не настроен';
            connectBtn.disabled = !s.oauth_app_configured;
            disconnectBtn?.classList.add('hidden');
        } else if (s.oauth_app_configured) {
            label.textContent = 'Аккаунт не подключён';
            if (dot) dot.className = 'figma-account-dot';
            connectBtn?.classList.remove('hidden');
            connectBtn.textContent = 'Подключить Figma';
            connectBtn.disabled = false;
            disconnectBtn?.classList.add('hidden');
        } else {
            label.textContent = 'Добавьте OAuth или PAT в .env';
            if (dot) dot.className = 'figma-account-dot error';
            connectBtn?.classList.add('hidden');
            disconnectBtn?.classList.add('hidden');
        }
    }

    async function connectFigma() {
        try {
            const resp = await fetch('/api/figma/auth');
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'OAuth не настроен');
            window.location.href = data.auth_url;
        } catch (e) {
            alert(e.message);
        }
    }

    async function disconnectFigma() {
        if (!confirm('Отключить Figma OAuth?')) return;
        try {
            await fetch('/api/figma/disconnect', { method: 'POST' });
            await loadFigmaStatus();
            if (window.UIEnhancements) UIEnhancements.toast('Figma отключена', 'info');
        } catch (e) {
            alert(e.message);
        }
    }

    function handleFigmaOAuthReturn() {
        const params = new URLSearchParams(window.location.search);
        const result = params.get('figma');
        if (!result) return;
        const msgs = {
            connected: ['🎨 Figma аккаунт подключён', 'success'],
            denied: ['Figma: доступ отклонён', 'error'],
            error: ['Figma OAuth: ошибка', 'error'],
        };
        const [msg, type] = msgs[result] || [];
        if (msg && window.UIEnhancements) UIEnhancements.toast(msg, type);
        window.history.replaceState({}, '', window.location.pathname);
        if (result === 'connected' && typeof switchView === 'function') {
            switchView('design');
            loadFigmaStatus();
        }
    }

    async function loadCursorStatus() {
        try {
            const resp = await fetch('/api/cursor/status');
            if (resp.ok) cursorStatus = await resp.json();
        } catch (_) {}
        updateCursorBadge();
        renderCursorPanel();
    }

    function updateCursorBadge() {
        const badge = document.getElementById('cursorBadge');
        if (!badge) return;
        if (cursorStatus?.github_sync && cursorStatus?.repo_url) {
            badge.textContent = 'GitHub ✓';
            badge.className = 'integration-badge active github';
        } else if (cursorStatus?.ok) {
            badge.textContent = 'SDK ✓';
            badge.className = 'integration-badge active';
        } else if (cursorStatus?.configured) {
            badge.textContent = 'ошибка';
            badge.className = 'integration-badge error';
        } else {
            badge.textContent = 'off';
            badge.className = 'integration-badge';
        }
    }

    function renderCursorPanel() {
        const el = document.getElementById('cursorPanelBody');
        if (!el) return;
        if (!cursorStatus) {
            el.innerHTML = '<div class="panel-empty">Загрузка…</div>';
            return;
        }
        const user = cursorStatus.user?.email || cursorStatus.user?.userEmail || '—';
        const repos = (cursorStatus.repositories || []).slice(0, 5);
        const runs = (cursorStatus.recent_runs || []).slice(0, 5);
        const syncOn = cursorStatus.github_sync ? '✅ Включён' : '❌ Выключен';
        const active = (cursorStatus.active_agents || []).length;
        el.innerHTML = `
            <div class="panel-section">
                <div class="panel-row"><span>API</span><strong>${cursorStatus.ok ? '✅ Подключён' : '❌ ' + (cursorStatus.error || 'нет ключа')}</strong></div>
                <div class="panel-row"><span>GitHub Sync</span><strong>${syncOn}</strong></div>
                <div class="panel-row"><span>Cloud repo</span><strong>${cursorStatus.repo_url || '— укажите в настройках'}</strong></div>
                <div class="panel-row"><span>Активных агентов</span><strong>${active}</strong></div>
                ${cursorStatus.auto_create_pr ? '<div class="panel-row"><span>PR</span><strong>авто</strong></div>' : ''}
            </div>
            ${repos.length ? `<div class="panel-section"><div class="panel-label-sm">Репозитории Cursor</div>${repos.map(r => {
                const url = typeof r === 'string' ? r : (r.repository || r.url || r.name || '');
                return `<button type="button" class="panel-chip repo-pick" data-repo="${url}" onclick="Integrations.pickRepo('${url.replace(/'/g, '')}')">${url || JSON.stringify(r)}</button>`;
            }).join('')}</div>` : ''}
            ${runs.length ? `<div class="panel-section"><div class="panel-label-sm">Последние runs</div>${runs.map(r => `<div class="run-item"><span>${r.mode || '?'}</span> <span class="muted">${r.status}</span>${r.pr_url ? ` <a href="${r.pr_url}" target="_blank">PR</a>` : ''}</div>`).join('')}</div>` : ''}
            <div class="panel-section">
                <textarea id="cursorPromptInput" class="design-input" rows="3" placeholder="Coding-задача → GitHub…"></textarea>
                <button type="button" class="btn-primary full-width" onclick="Integrations.runCursor()">⚡ Sync to GitHub</button>
            </div>`;
    }

    async function pickRepo(url) {
        if (!url) return;
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cursor_repo_url: url }),
            });
            loadCursorStatus();
            if (typeof addSystemMessage === 'function') addSystemMessage(`Repo: ${url}`);
        } catch (_) {}
    }

    async function runCursor() {
        const input = document.getElementById('cursorPromptInput');
        const prompt = input?.value?.trim();
        if (!prompt) return;
        try {
            const resp = await fetch('/api/cursor/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt }),
            });
            const data = await resp.json();
            if (resp.ok) {
                input.value = '';
                if (typeof addSystemMessage === 'function') {
                    addSystemMessage(`⚡ Cursor run ${data.id}: ${data.status}`);
                }
                loadCursorStatus();
            } else {
                alert(data.detail || 'Ошибка Cursor');
            }
        } catch (e) {
            alert('Ошибка: ' + e.message);
        }
    }

    async function importFigma() {
        const input = document.getElementById('figmaUrlInput');
        const url = input?.value?.trim();
        if (!url) return;
        const resultEl = document.getElementById('figmaImportResult');
        if (resultEl) resultEl.innerHTML = '<div class="panel-empty">Импорт…</div>';
        try {
            const resp = await fetch('/api/figma/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Ошибка импорта');
            renderFigmaResult(data);
            if (typeof addSystemMessage === 'function') {
                addSystemMessage(`🎨 Figma: ${data.summary?.file_name || 'импортирован'}`);
            }
            if (window.ReactPreview) ReactPreview.loadLatest();
        } catch (e) {
            if (resultEl) resultEl.innerHTML = `<div class="panel-error">${e.message}</div>`;
        }
    }

    function renderFigmaResult(data) {
        const el = document.getElementById('figmaImportResult');
        if (!el) return;
        const s = data.summary || {};
        const colors = (s.colors || []).map(c => `<span class="color-swatch" style="background:${c}" title="${c}"></span>`).join('');
        el.innerHTML = `
            <div class="figma-card animate-in">
                <h3>${s.file_name || 'Figma'}</h3>
                ${data.preview_url ? `<img src="${data.preview_url}" alt="preview" class="figma-preview-img">` : ''}
                <div class="color-row">${colors}</div>
                <div class="frames-list">${(s.frames || []).slice(0, 6).map(f => `<div class="frame-chip">${f.name} <small>${Math.round(f.width || 0)}×${Math.round(f.height || 0)}</small></div>`).join('')}</div>
                <pre class="token-preview">${data.css_tokens || ''}</pre>
            </div>`;
    }

    function toggleCursorPanel() {
        document.getElementById('cursorPanel')?.classList.toggle('open');
        loadCursorStatus();
    }

    let figmaAutoImported = false;

    async function loadDefaultFigmaUrl() {
        await loadFigmaStatus();
        try {
            const resp = await fetch('/api/config');
            if (!resp.ok) return;
            const cfg = await resp.json();
            const input = document.getElementById('figmaUrlInput');
            if (input && cfg.figma_default_url) input.value = cfg.figma_default_url;
            if (cfg.figma_configured && cfg.figma_default_url && !figmaAutoImported) {
                figmaAutoImported = true;
                await importFigma();
            }
        } catch (_) {}
    }

    handleFigmaOAuthReturn();

    global.Integrations = {
        loadCursorStatus,
        loadFigmaStatus,
        connectFigma,
        disconnectFigma,
        runCursor,
        importFigma,
        loadDefaultFigmaUrl,
        toggleCursorPanel,
        pickRepo,
        onCursorMessage(data) {
            loadCursorStatus();
        },
        onFigmaMessage(data) {
            const normalized = data.summary ? data : {
                summary: {
                    file_name: data.title || 'Figma',
                    colors: data.colors || [],
                    frames: data.frames || [],
                },
                preview_url: data.preview_url,
                css_tokens: data.css_tokens,
            };
            renderFigmaResult(normalized);
        },
    };
})(window);
