/**
 * Дизайн-лаб Сони — изучение макетов, память, палитры
 */
(function (global) {
    let cache = null;

    function el(id) {
        return document.getElementById(id);
    }

    function escape(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    async function load() {
        await Promise.all([
            loadLab(),
            global.Integrations?.loadFigmaStatus?.(),
            global.Integrations?.loadDefaultFigmaUrl?.(),
        ]);
    }

    function normalizeLabPayload(data) {
        if (!data) return {};
        const studied = data.studied || data.recent_studied || [];
        const palette = data.color_palette || [];
        const colorsFromStudied = studied.flatMap((s) => s.colors || []);
        return {
            ...data,
            studied,
            knowledge: data.knowledge || [],
            color_palette: palette.length ? palette : [...new Set(colorsFromStudied)].slice(0, 32),
            discovery: data.discovery || {
                auto_discover_enabled: true,
                queue_size: 0,
                studied_keys_count: 0,
                catalog_size: 0,
                recent_log: [],
            },
            portfolio: data.portfolio || data.recent_portfolio || [],
        };
    }

    async function fetchDesignLab() {
        const urls = ['/api/figma/design-lab', '/api/design-lab', '/api/figma/studio'];
        let lastErr = null;
        for (const url of urls) {
            try {
                const r = await fetch(url, { credentials: 'same-origin' });
                if (r.ok) {
                    return normalizeLabPayload(await r.json());
                }
                let detail = '';
                try {
                    const d = await r.json();
                    detail = d.detail || r.statusText;
                } catch (_) {
                    detail = r.statusText;
                }
                lastErr = new Error(detail || `HTTP ${r.status}`);
            } catch (e) {
                lastErr = e;
            }
        }
        throw lastErr || new Error('Не удалось загрузить лабораторию');
    }

    async function loadLab() {
        const studiedEl = el('dlStudiedList');
        const knowEl = el('dlKnowledgeList');
        const paletteEl = el('dlPalette');
        const statsEl = el('dlStats');
        const discoveryEl = el('dlDiscoveryStatus');
        if (studiedEl) studiedEl.innerHTML = global.UICore ? UICore.loadingState('', { compact: true }) : '<div class="panel-empty">Загрузка…</div>';
        if (discoveryEl) discoveryEl.innerHTML = global.UICore ? UICore.loadingState('Загрузка статуса…', { compact: true }) : '<div class="panel-empty">Загрузка статуса…</div>';
        try {
            cache = await fetchDesignLab();
            renderStats(statsEl, cache);
            renderStudied(studiedEl, cache.studied || []);
            renderKnowledge(knowEl, cache.knowledge || []);
            renderPalette(paletteEl, cache.color_palette || []);
            renderPortfolio(el('dlPortfolio'), cache.portfolio || cache.recent_portfolio || []);
            renderDiscovery(cache.discovery || {});
            updateAgentBadge(cache.agent);
        } catch (e) {
            const msg = e.message || 'Ошибка загрузки';
            if (studiedEl) {
                studiedEl.innerHTML = global.UICore
                    ? UICore.errorState(`${msg}. Перезапустите сервер и обновите Ctrl+F5`, { retryOnclick: 'SonyaDesignLab.load()' })
                    : `<div class="panel-error">${escape(msg)}<br><small class="muted">Перезапустите сервер (python main.py) и обновите страницу Ctrl+F5</small></div>`;
            }
            if (discoveryEl) {
                discoveryEl.innerHTML = global.UICore
                    ? UICore.errorState(msg, { compact: true })
                    : `<div class="panel-error">${escape(msg)}</div>`;
            }
        }
    }

    function updateAgentBadge(agent) {
        const b = el('dlAgentStatus');
        if (!b || !agent) return;
        const map = { learning: '📚 учится', working: '⚡ работает', idle: '💤 свободна', thinking: '💭 думает' };
        b.textContent = map[agent.status] || agent.status || '—';
        b.className = 'dl-agent-status' + (agent.status === 'learning' ? ' active' : '');
    }

    function renderStats(container, data) {
        if (!container) return;
        container.innerHTML = `
            <div class="dl-stat"><span>${data.studied_count || 0}</span><small>макетов</small></div>
            <div class="dl-stat"><span>${data.patterns_colors || 0}</span><small>цветов</small></div>
            <div class="dl-stat"><span>${(data.knowledge || []).length}</span><small>в памяти</small></div>
            <div class="dl-stat"><span>${data.portfolio_count || 0}</span><small>проектов</small></div>`;
    }

    function renderStudied(container, items) {
        if (!container) return;
        if (!items.length) {
            container.innerHTML = global.UICore ? UICore.inlineEmpty('Пока пусто — Соня найдёт макеты сама или вставьте ссылку Figma') : '<div class="panel-empty">Пока пусто — Соня найдёт макеты сама или вставьте ссылку Figma</div>';
            return;
        }
        container.innerHTML = items.slice(0, 12).map((s) => {
            const srcBadge = s.source === 'figma_auto' ? '<span class="dl-memory-badge">Auto</span> ' : '';
            const colors = (s.colors || []).slice(0, 6).map((c) =>
                `<span class="color-swatch" style="background:${c}" title="${escape(c)}"></span>`
            ).join('');
            const frames = (s.frames || []).slice(0, 3).join(', ');
            return `<article class="dl-studied-card">
                <div class="dl-studied-head">
                    <strong>${srcBadge}${escape(s.file_name || 'Макет')}</strong>
                    <time>${formatTime(s.timestamp)}</time>
                </div>
                <div class="color-row">${colors}</div>
                ${frames ? `<p class="muted">${escape(frames)}</p>` : ''}
                ${s.url ? `<a href="${escape(s.url)}" target="_blank" rel="noopener" class="dl-link">Figma ↗</a>` : '<span class="muted">локальный референс</span>'}
            </article>`;
        }).join('');
    }

    function renderKnowledge(container, items) {
        if (!container) return;
        if (!items.length) {
            container.innerHTML = '<div class="panel-empty">Соня запоминает сюда каждый изученный макет и UI-паттерн</div>';
            return;
        }
        container.innerHTML = items.map((k) => {
            const src = k.source || 'design';
            const badge = { figma: 'Figma', figma_auto: 'Auto', figma_builtin: 'Reference', figma_web: 'Web', figma_portfolio: 'Проект', import: 'Import' }[src] || src;
            return `<article class="dl-memory-card">
                <div class="dl-memory-head">
                    <span class="dl-memory-badge">${escape(badge)}</span>
                    <time>${formatTime(k.timestamp)}</time>
                </div>
                <h4>${escape(k.title || k.topic || 'Знание')}</h4>
                <p>${escape((k.summary || '').slice(0, 220))}</p>
                ${(k.figma_data?.colors || []).length ? `<div class="color-row">${k.figma_data.colors.slice(0, 5).map((c) =>
                    `<span class="color-swatch" style="background:${c}"></span>`).join('')}</div>` : ''}
                ${k.url ? `<a href="${escape(k.url)}" target="_blank" rel="noopener" class="dl-link">Источник ↗</a>` : ''}
            </article>`;
        }).join('');
    }

    function renderPalette(container, colors) {
        if (!container) return;
        if (!colors.length) {
            container.innerHTML = '<span class="muted">Палитра появится после изучения макетов</span>';
            return;
        }
        container.innerHTML = colors.map((c) =>
            `<button type="button" class="dl-color-chip" style="background:${c}" title="${escape(c)}" onclick="navigator.clipboard?.writeText('${c}');SonyaDesignLab.toastCopy('${c}')"></button>`
        ).join('');
    }

    function renderPortfolio(container, items) {
        if (!container) return;
        if (!items.length) {
            container.innerHTML = '<p class="muted">Соня создаст проекты после обучения на паттернах</p>';
            return;
        }
        container.innerHTML = items.slice(0, 6).map((p) =>
            `<div class="dl-portfolio-item">
                <strong>${escape(p.title || 'Проект')}</strong>
                <div class="color-row">${(p.colors || []).slice(0, 5).map((c) =>
                    `<span class="color-swatch" style="background:${c}"></span>`).join('')}</div>
                <small class="muted">${escape(p.inspiration || p.theme || '')}</small>
            </div>`
        ).join('');
    }

    function renderDiscovery(disc) {
        const statusEl = el('dlDiscoveryStatus');
        const logEl = el('dlDiscoveryLog');
        if (!statusEl) return;

        const enabled = disc.auto_discover_enabled !== false;
        const next = disc.next_target;
        const queue = disc.queue_size || 0;

        statusEl.innerHTML = `
            <div class="dl-discovery-grid">
                <div class="dl-discovery-stat ${enabled ? 'on' : 'off'}">
                    <span>${enabled ? '✅' : '⏸'}</span>
                    <small>Авто-поиск</small>
                </div>
                <div class="dl-discovery-stat">
                    <span>${queue}</span>
                    <small>в очереди</small>
                </div>
                <div class="dl-discovery-stat">
                    <span>${disc.studied_keys_count || 0}</span>
                    <small>найдено</small>
                </div>
                <div class="dl-discovery-stat">
                    <span>${disc.catalog_size || 0}</span>
                    <small>каталог</small>
                </div>
            </div>
            ${next ? `<div class="dl-next-target">
                <span class="dl-memory-badge">${escape(next.source || 'auto')}</span>
                <strong>${escape(next.name || 'Следующий макет')}</strong>
                ${next.url ? `<a href="${escape(next.url)}" target="_blank" rel="noopener" class="dl-link">Открыть ↗</a>` : ''}
            </div>` : `<p class="muted">${escape(disc.empty_queue_hint || 'Очередь пуста — нажмите «Сканировать»')}</p>`}
            ${(disc.hints || []).length ? `<ul class="dl-discovery-hints">${(disc.hints || []).map((h) =>
                `<li class="muted">${escape(h)}</li>`).join('')}</ul>` : ''}
            ${(disc.scan_blockers || []).length ? `<ul class="dl-discovery-blockers">${(disc.scan_blockers || []).map((b) =>
                `<li>⚠️ ${escape(b)}</li>`).join('')}</ul>` : ''}
            <p class="muted dl-discovery-meta">
                ${disc.api_connected ? `API: ${escape(disc.auth_method || 'ok')}` : 'API: не подключён'}
                ${typeof disc.teams_count === 'number' ? ` · teams: ${disc.teams_count}` : ''}
                ${disc.last_scan_at ? ` · Скан: ${formatTime(disc.last_scan_at)}` : ''}
                ${disc.last_study_at ? ` · Изучено: ${formatTime(disc.last_study_at)}` : ''}
            </p>`;

        if (!logEl) return;
        const log = disc.recent_log || [];
        if (!log.length) {
            logEl.innerHTML = '';
            return;
        }
        logEl.innerHTML = `<div class="panel-label">Журнал авто-исследования</div>` +
            log.slice(0, 6).map((e) => {
                const icon = e.status === 'studied' ? '✅' : '⚠️';
                return `<div class="dl-log-item ${e.status || ''}">
                    ${icon} <span class="dl-memory-badge">${escape(e.source || '')}</span>
                    ${escape(e.name || e.file_key || '—')}
                    <time>${formatTime(e.timestamp)}</time>
                </div>`;
            }).join('');
    }

    async function discoverScan() {
        toast('🔄 Сканирую Figma-проекты…', 'info');
        try {
            const r = await fetch('/api/figma/studio/discover?scan_only=true', { method: 'POST', credentials: 'same-origin' });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Ошибка сканирования');
            const added = data.scan?.added || 0;
            toast(added ? `Найдено ${added} новых макетов в очереди` : 'Новых макетов не найдено', added ? 'success' : 'info');
            await loadLab();
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function discoverStudy() {
        toast('🔍 Соня ищет и изучает макет…', 'info');
        try {
            const r = await fetch('/api/figma/studio/discover', { method: 'POST', credentials: 'same-origin' });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Ошибка');
            if (data.studied) {
                toast('✅ Соня самостоятельно изучила новый макет', 'success');
            } else {
                toast('Скан выполнен — макет для изучения не найден (подключите Figma или добавьте каталог)', 'info');
            }
            setTimeout(loadLab, 1500);
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    function formatTime(ts) {
        if (!ts) return '';
        try {
            const d = new Date(ts);
            return d.toLocaleDateString('ru', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return '';
        }
    }

    function toastCopy(color) {
        toast(`Скопировано ${color}`, 'success');
    }

    async function studyUrl() {
        const input = el('dlFigmaUrl');
        const url = input?.value?.trim();
        if (!url) {
            toast('Вставьте ссылку Figma', 'info');
            return;
        }
        const preview = el('dlStudyPreview');
        if (preview) preview.innerHTML = '<div class="panel-empty">Соня изучает макет…</div>';
        const studyEndpoints = ['/api/figma/studio/study-url', '/api/figma/study'];
        try {
            let data = null;
            let lastErr = null;
            for (const endpoint of studyEndpoints) {
                const r = await fetch(endpoint, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url }),
                });
                data = await r.json().catch(() => ({}));
                if (r.ok) break;
                lastErr = new Error(data.detail || `HTTP ${r.status}`);
                if (r.status !== 404) throw lastErr;
            }
            if (!data?.ok && lastErr) {
                const rImport = await fetch('/api/figma/import', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url }),
                });
                data = await rImport.json().catch(() => ({}));
                if (!rImport.ok) throw new Error(data.detail || lastErr.message || 'Ошибка изучения');
                data = {
                    ok: true,
                    mode: 'figma',
                    summary: data.summary,
                    preview_url: data.preview_url,
                    knowledge: { summary: 'Макет импортирован и запомнен' },
                };
            }
            toast(data.mode === 'figma' ? '📚 Макет изучен и сохранён в память' : '📚 Изучен UI-референс', 'success');
            renderStudyPreview(preview, data);
            await loadLab();
        } catch (e) {
            if (preview) preview.innerHTML = `<div class="panel-error">${escape(e.message)}</div>`;
            toast(e.message, 'error');
        }
    }

    function renderStudyPreview(container, data) {
        if (!container) return;
        const s = data.summary || {};
        const colors = (s.colors || []).map((c) => `<span class="color-swatch" style="background:${c}"></span>`).join('');
        container.innerHTML = `
            <div class="dl-preview-card animate-in">
                <h3>✅ ${escape(s.file_name || data.message || 'Изучено')}</h3>
                ${data.preview_url ? `<img src="${data.preview_url}" alt="" class="figma-preview-img">` : ''}
                <div class="color-row">${colors}</div>
                <p class="muted">${escape(data.knowledge?.summary || data.message || '')}</p>
            </div>`;
    }

    async function importToReact() {
        const input = el('dlFigmaUrl');
        const url = input?.value?.trim();
        if (!url) {
            toast('Вставьте ссылку Figma', 'info');
            return;
        }
        const preview = el('dlStudyPreview');
        if (preview) preview.innerHTML = '<div class="panel-empty">Импорт + React Preview…</div>';
        try {
            const r = await fetch('/api/figma/import', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Ошибка импорта');
            if (global.Integrations?.renderFigmaResult) {
                global.Integrations.renderFigmaResult(data);
            }
            renderStudyPreview(preview, { summary: data.summary, preview_url: data.preview_url, knowledge: { summary: 'Макет импортирован и запомнен' } });
            toast('🎨 React Preview обновлён · макет в памяти Сони', 'success');
            if (global.ReactPreview) ReactPreview.loadLatest();
            await loadLab();
        } catch (e) {
            if (preview) preview.innerHTML = `<div class="panel-error">${escape(e.message)}</div>`;
        }
    }

    async function triggerStudy() {
        try {
            const r = await fetch('/api/figma/studio/trigger?action=study', { method: 'POST', credentials: 'same-origin' });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Ошибка');
            toast('📚 Соня ушла в библиотеку изучать дизайн…', 'info');
            setTimeout(loadLab, 3500);
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function triggerCreate() {
        if (global.Integrations?.triggerSonyaCreate) {
            await Integrations.triggerSonyaCreate();
            setTimeout(loadLab, 2000);
            return;
        }
        toast('Studio недоступен', 'error');
    }

    function bind() {
        el('dlDiscoverScan')?.addEventListener('click', discoverScan);
        el('dlDiscoverStudy')?.addEventListener('click', discoverStudy);
        el('dlStudyBtn')?.addEventListener('click', studyUrl);
        el('dlImportBtn')?.addEventListener('click', importToReact);
        el('dlTriggerStudy')?.addEventListener('click', triggerStudy);
        el('dlTriggerCreate')?.addEventListener('click', triggerCreate);
        el('dlOpenPreview')?.addEventListener('click', () => global.openSonyaPreview?.());
        el('dlGoStudio')?.addEventListener('click', () => global.switchView?.('sonya-studio'));
    }

    bind();

    global.SonyaDesignLab = {
        load,
        loadLab,
        studyUrl,
        importToReact,
        discoverScan,
        discoverStudy,
        toastCopy,
    };
})(window);
