/**
 * Cursor SDK + Figma — панели и вкладка Design
 */
(function (global) {
    let cursorStatus = null;
    let figmaStatus = null;

    async function loadFigmaStatus() {
        try {
            const resp = await fetch('/api/figma/status', { credentials: 'same-origin' });
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
        const rl = s.rate_limit || {};
        if (rl.in_cooldown && rl.cooldown_sec_remaining) {
            label.textContent = `⏳ Rate limit · ${rl.cooldown_sec_remaining}с`;
            if (dot) dot.className = 'figma-account-dot error';
        } else if (s.auth_method === 'oauth') {
            const who = s.user_handle || s.user_email || s.user_name || 'Figma';
            label.textContent = `✓ ${who}`;
            if (dot) dot.className = 'figma-account-dot connected';
            connectBtn?.classList.add('hidden');
            disconnectBtn?.classList.remove('hidden');
        } else if (s.auth_method === 'pat') {
            const admin = global.UIAccess?.canAccessConsole?.(global.Auth?.getUser());
            label.textContent = admin ? '✓ Personal Token (.env)' : '✓ Figma подключена';
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
            const resp = await fetch('/api/figma/auth', { credentials: 'same-origin' });
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
            await fetch('/api/figma/disconnect', { method: 'POST', credentials: 'same-origin' });
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
            if (global.Auth?.canViewAgentLearning?.(global.Auth.getUser())) {
                switchView('agent-learning');
                if (typeof switchAgentLearningPanel === 'function') switchAgentLearningPanel('design');
            }
            loadFigmaStatus();
        }
    }

    async function loadCursorStatus() {
        try {
            const resp = await fetch('/api/cursor/status', { credentials: 'same-origin' });
            if (resp.ok) cursorStatus = await resp.json();
        } catch (_) {}
        updateCursorBadge();
        renderCursorPanel();
    }

    function updateCursorBadge() {
        const text = (() => {
            if (cursorStatus?.github_sync && cursorStatus?.repo_url) return { t: 'GitHub ✓', c: 'integration-badge active github' };
            if (cursorStatus?.ok) return { t: 'SDK ✓', c: 'integration-badge active' };
            if (cursorStatus?.configured) return { t: 'ошибка', c: 'integration-badge error' };
            return { t: 'off', c: 'integration-badge' };
        })();
        document.querySelectorAll('#cursorBadge, #cursorBadgeMenu').forEach((badge) => {
            badge.textContent = text.t;
            badge.className = text.c;
        });
    }

    function renderCursorPanel() {
        const el = document.getElementById('cursorPanelBody');
        if (!el) return;
        if (!cursorStatus) {
            el.innerHTML = global.UICore ? UICore.loadingState('Загрузка…', { compact: true }) : '<div class="dash-loading">Загрузка…</div>';
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
                credentials: 'same-origin',
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
                credentials: 'same-origin',
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
        const input = document.getElementById('dlFigmaUrl') || document.getElementById('figmaUrlInput');
        const url = input?.value?.trim();
        if (!url) return;
        const resultEl = document.getElementById('dlStudyPreview') || document.getElementById('figmaImportResult');
        if (resultEl) {
            resultEl.innerHTML = global.UICore
                ? UICore.loadingState('Импорт…', { compact: true })
                : '<div class="panel-empty">Импорт…</div>';
        }
        try {
            const resp = await fetch('/api/figma/import', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                const msg = data.detail || 'Ошибка импорта';
                if (resp.status === 429) {
                    const wait = resp.headers.get('Retry-After') || '120';
                    throw new Error(`Figma rate limit — подождите ${wait} сек. и нажмите «Импорт» снова.`);
                }
                throw new Error(msg);
            }
            renderFigmaResult(data);
            if (window.WowFeatures) WowFeatures.setLastFigma(data);
            if (typeof addSystemMessage === 'function') {
                addSystemMessage(`🎨 Figma: ${data.summary?.file_name || 'импортирован'}`);
            }
            if (window.ReactPreview) ReactPreview.loadLatest();
        } catch (e) {
            if (resultEl) {
                resultEl.innerHTML = global.UICore
                    ? UICore.errorState(e.message)
                    : `<div class="panel-error">${e.message}</div>`;
            }
        }
    }

    function renderFigmaResult(data) {
        const el = document.getElementById('dlStudyPreview') || document.getElementById('figmaImportResult');
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
            const resp = await fetch('/api/config', { credentials: 'same-origin' });
            if (!resp.ok) return;
            const cfg = await resp.json();
            const input = document.getElementById('dlFigmaUrl') || document.getElementById('figmaUrlInput');
            if (input && cfg.figma_default_url) input.value = cfg.figma_default_url;
            // Импорт только по кнопке — авто-импорт перегружал Figma API (429)
        } catch (_) {}
    }

    async function loadSonyaStudio() {
        const el = document.getElementById('sonyaStudioPanel');
        if (!el) return;
        try {
            const resp = await fetch('/api/figma/studio', { credentials: 'same-origin' });
            if (!resp.ok) throw new Error('Ошибка загрузки');
            const data = await resp.json();
            const portfolio = (data.portfolio || []).slice(0, 5);
            el.innerHTML = `
                <div class="studio-stats">
                    <div class="studio-stat"><span>${data.studied_count || 0}</span><small>изучено</small></div>
                    <div class="studio-stat"><span>${data.portfolio_count || 0}</span><small>проектов</small></div>
                    <div class="studio-stat"><span>${data.patterns_colors || 0}</span><small>цветов</small></div>
                </div>
                <p class="muted studio-hint">Соня изучает UI-референсы и создаёт React Preview. Для импорта используйте ссылки <code>figma.com/design/</code> или <code>file/</code> (не Sites).</p>
                <div class="studio-actions">
                    <button type="button" class="btn-secondary btn-sm" onclick="Integrations.triggerSonyaStudy()">📚 Изучить макет</button>
                    <button type="button" class="btn-primary btn-sm" onclick="Integrations.triggerSonyaCreate()">✨ Новый проект</button>
                </div>
                ${portfolio.length ? `<div class="studio-portfolio">${portfolio.map((p) => `
                    <div class="portfolio-item">
                        <strong>${p.title || 'Проект'}</strong>
                        <div class="color-row">${(p.colors || []).slice(0, 4).map((c) => `<span class="color-swatch" style="background:${c}"></span>`).join('')}</div>
                        <small class="muted">${p.inspiration ? `↳ ${p.inspiration}` : ''}</small>
                    </div>`).join('')}</div>` : '<p class="muted">Портfolio пуст — Соня скоро создаст первый проект</p>'}`;
        } catch (e) {
            el.innerHTML = global.UICore
                ? UICore.errorState(e.message)
                : `<div class="panel-error">${e.message}</div>`;
        }
    }

    async function triggerSonyaStudy() {
        try {
            const resp = await fetch('/api/figma/studio/trigger?action=study', { method: 'POST', credentials: 'same-origin' });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Ошибка');
            if (window.UIEnhancements) UIEnhancements.toast('📚 Соня изучает Figma…', 'info');
            setTimeout(loadSonyaStudio, 3000);
        } catch (e) { alert(e.message); }
    }

    async function triggerSonyaCreate() {
        try {
            let project = null;
            if (window.SonyaStudio?.createBySonya) {
                project = await SonyaStudio.createBySonya();
            } else {
                const resp = await fetch('/api/sonya/studio/create', { method: 'POST', credentials: 'same-origin' });
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Ошибка');
                project = data.project;
            }
            if (window.UIEnhancements) UIEnhancements.toast('✨ Соня создала проект в Studio…', 'info');
            if (typeof switchView === 'function') switchView('sonya-studio');
            if (window.SonyaStudio && project?.id) {
                await SonyaStudio.load(project.id);
            } else if (window.SonyaStudio) {
                setTimeout(() => SonyaStudio.load(), 1500);
            }
            setTimeout(loadSonyaStudio, 3000);
        } catch (e) { alert(e.message); }
    }

    handleFigmaOAuthReturn();

    global.Integrations = {
        loadCursorStatus,
        loadFigmaStatus,
        connectFigma,
        disconnectFigma,
        loadSonyaStudio,
        triggerSonyaStudy,
        triggerSonyaCreate,
        runCursor,
        importFigma,
        renderFigmaResult,
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
            if (window.WowFeatures) WowFeatures.setLastFigma(normalized);
            if (window.ReactPreview) {
                ReactPreview.loadLatest().then(() => ReactPreview.open());
            }
        },
    };
})(window);
