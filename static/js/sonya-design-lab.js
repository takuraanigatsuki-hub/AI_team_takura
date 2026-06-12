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

    async function loadLab() {
        const studiedEl = el('dlStudiedList');
        const knowEl = el('dlKnowledgeList');
        const paletteEl = el('dlPalette');
        const statsEl = el('dlStats');
        if (studiedEl) studiedEl.innerHTML = '<div class="panel-empty">Загрузка…</div>';
        try {
            const r = await fetch('/api/figma/design-lab');
            if (!r.ok) throw new Error('Не удалось загрузить лабораторию');
            cache = await r.json();
            renderStats(statsEl, cache);
            renderStudied(studiedEl, cache.studied || []);
            renderKnowledge(knowEl, cache.knowledge || []);
            renderPalette(paletteEl, cache.color_palette || []);
            renderPortfolio(el('dlPortfolio'), cache.portfolio || cache.recent_portfolio || []);
            updateAgentBadge(cache.agent);
        } catch (e) {
            if (studiedEl) studiedEl.innerHTML = `<div class="panel-error">${escape(e.message)}</div>`;
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
            container.innerHTML = '<div class="panel-empty">Пока пусто — дайте ссылку Figma или нажмите «Изучить»</div>';
            return;
        }
        container.innerHTML = items.slice(0, 12).map((s) => {
            const colors = (s.colors || []).slice(0, 6).map((c) =>
                `<span class="color-swatch" style="background:${c}" title="${escape(c)}"></span>`
            ).join('');
            const frames = (s.frames || []).slice(0, 3).join(', ');
            return `<article class="dl-studied-card">
                <div class="dl-studied-head">
                    <strong>${escape(s.file_name || 'Макет')}</strong>
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
            const badge = { figma: 'Figma', figma_builtin: 'Reference', figma_web: 'Web', figma_portfolio: 'Проект', import: 'Import' }[src] || src;
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
        try {
            const r = await fetch('/api/figma/studio/study-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Ошибка изучения');
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
            const r = await fetch('/api/figma/studio/trigger?action=study', { method: 'POST' });
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
        toastCopy,
    };
})(window);
