/**
 * Проекты агентов во вкладке «Обучение» — все агенты, просмотр внутри Обучения
 */
(function (global) {
    let hub = null;
    let activeAgentId = 'frontend';
    let previewOpen = false;

    const KIND_LABELS = {
        sonya_studio: '✨ UI Studio',
        practice: '🏋️ Практика',
        collaborative: '🤝 Совместный',
        knowledge: '📚 Знание',
        deliverable: '📦 Артефакт',
    };

    function el(id) {
        return document.getElementById(id);
    }

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function agentById(id) {
        return (hub?.agents || []).find((a) => a.agent_id === id) || null;
    }

    async function load(preferredAgent) {
        const grid = el('apProjectsGrid');
        const tabs = el('apAgentTabs');
        if (grid) {
            grid.innerHTML = global.UICore
                ? UICore.loadingState('Загрузка проектов…', { compact: true })
                : '<div class="panel-empty">Загрузка…</div>';
        }
        if (tabs) tabs.innerHTML = '';
        closePreview(false);
        try {
            const r = await fetch('/api/learning/agent-hub', { credentials: 'same-origin' });
            const data = global.UICore?.parseApiJson
                ? await UICore.parseApiJson(r, 'Проекты агентов')
                : await r.json();
            if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
            hub = data;
            if (preferredAgent && agentById(preferredAgent)) {
                activeAgentId = preferredAgent;
            } else if (!agentById(activeAgentId)) {
                activeAgentId = hub.agents?.[0]?.agent_id || 'frontend';
            }
            renderAgentTabs();
            renderAgentPanel();
        } catch (e) {
            if (grid) {
                grid.innerHTML = global.UICore
                    ? UICore.errorState(e.message, { retryOnclick: 'AgentLearningProjects.load()' })
                    : `<div class="panel-error">${esc(e.message)}</div>`;
            }
        }
    }

    function renderAgentTabs() {
        const tabs = el('apAgentTabs');
        if (!tabs || !hub) return;
        tabs.innerHTML = (hub.agents || []).map((a) => {
            const count = a.projects_count || 0;
            const know = a.knowledge_count || 0;
            return `<button type="button" class="ap-agent-tab${a.agent_id === activeAgentId ? ' active' : ''}"
                data-agent="${a.agent_id}" title="${esc(a.name)} · ${count} проектов · ${know} тем">
                <span class="ap-tab-emoji">${a.emoji}</span>
                <span class="ap-tab-name">${esc(a.name)}</span>
                <span class="ap-tab-count">${count || know || '—'}</span>
            </button>`;
        }).join('');
        tabs.querySelectorAll('.ap-agent-tab').forEach((btn) => {
            btn.addEventListener('click', () => {
                activeAgentId = btn.dataset.agent;
                closePreview(false);
                renderAgentTabs();
                renderAgentPanel();
            });
        });
    }

    function renderAgentPanel() {
        const agent = agentById(activeAgentId);
        const titleEl = el('apAgentTitle');
        const subEl = el('apAgentSub');
        const statsEl = el('apAgentStats');
        const grid = el('apProjectsGrid');
        if (!agent || !grid) return;

        if (titleEl) titleEl.textContent = `${agent.emoji} ${agent.name}`;
        if (subEl) {
            subEl.textContent = `${agent.projects_count || 0} проектов · ${agent.knowledge_count || 0} изученных тем`;
        }
        if (statsEl) {
            const kinds = {};
            (agent.projects || []).forEach((p) => {
                kinds[p.kind] = (kinds[p.kind] || 0) + 1;
            });
            statsEl.innerHTML = `
                <div class="dl-stat"><span>${agent.projects_count || 0}</span><small>проектов</small></div>
                <div class="dl-stat"><span>${agent.knowledge_count || 0}</span><small>тем</small></div>
                <div class="dl-stat"><span>${kinds.sonya_studio || kinds.deliverable || 0}</span><small>артефактов</small></div>
                <div class="dl-stat"><span>${kinds.practice || kinds.collaborative || 0}</span><small>практики</small></div>`;
        }

        const projects = agent.projects || [];
        if (!projects.length) {
            grid.innerHTML = global.UICore ? UICore.emptyState({
                icon: agent.emoji,
                title: `У ${agent.name} пока нет проектов`,
                text: 'Проекты появятся после автономного обучения и практики команды',
                primaryLabel: agent.agent_id === 'frontend' ? 'Design Lab' : 'Лента обучения',
                primaryOnclick: agent.agent_id === 'frontend'
                    ? "switchAgentLearningPanel('design')"
                    : "switchAgentLearningPanel('learning')",
            }) : `<div class="panel-empty">Проектов пока нет</div>`;
            return;
        }

        grid.innerHTML = projects.map((p) => renderProjectCard(p, agent)).join('');
        grid.querySelectorAll('[data-open-project]').forEach((btn) => {
            btn.addEventListener('click', () => openProject(btn.dataset.openProject, btn.dataset.openKind));
        });
    }

    function renderProjectCard(p, agent) {
        const kindLabel = KIND_LABELS[p.kind] || p.kind || 'Проект';
        const sub = [];
        if (p.kind === 'sonya_studio') {
            sub.push(p.theme || 'UI', p.status || 'draft', `v${p.version_count || 1}`);
        } else if (p.kind === 'deliverable') {
            sub.push(p.type_label || p.artifact_type || 'Артефакт');
        } else if (p.last_score) {
            sub.push(`Оценка ${p.last_score}/10`);
        } else if (p.topic) {
            sub.push(p.topic);
        }
        const colors = (p.colors || []).slice(0, 5).map((c) =>
            `<span class="color-swatch" style="background:${c}"></span>`).join('');
        const openable = p.previewable !== false;
        return `<article class="dl-studied-card ap-project-card">
            <div class="dl-studied-head">
                <strong>${esc(p.title)}</strong>
                <span class="dl-memory-badge">${esc(kindLabel)}</span>
            </div>
            <p class="muted">${esc(sub.filter(Boolean).join(' · '))}</p>
            ${colors ? `<div class="color-row">${colors}</div>` : ''}
            ${p.description ? `<p class="ap-card-desc muted">${esc(p.description.slice(0, 160))}${p.description.length > 160 ? '…' : ''}</p>` : ''}
            <div class="dl-card-foot">
                ${openable
                    ? `<button type="button" class="btn-secondary btn-sm" data-open-project="${esc(p.id)}" data-open-kind="${esc(p.kind)}">Открыть</button>`
                    : '<span class="muted">Только описание</span>'}
                ${p.kind === 'sonya_studio' && global.SonyaDesignLab?.voteButtons
                    ? '' : ''}
            </div>
        </article>`;
    }

    async function openProject(id, kind) {
        const panel = el('apPreviewPanel');
        const grid = el('apProjectsGrid');
        const listHeader = el('apListHeader');
        const frame = el('apPreviewFrame');
        const meta = el('apPreviewMeta');
        const titleEl = el('apPreviewTitle');
        if (!panel || !frame) return;

        previewOpen = true;
        if (grid) grid.classList.add('hidden');
        if (listHeader) listHeader.classList.add('hidden');
        panel.classList.remove('hidden');
        if (titleEl) titleEl.textContent = 'Загрузка…';
        if (meta) meta.innerHTML = global.UICore ? UICore.loadingState('Загрузка…', { compact: true }) : '';
        frame.srcdoc = '<html><body style="margin:0;background:#0e1016;color:#888;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui">Загрузка…</body></html>';

        try {
            if (kind === 'sonya_studio') {
                await openSonyaStudioProject(id, frame, meta, titleEl);
            } else if (kind === 'deliverable') {
                await openDeliverable(id, frame, meta, titleEl);
            } else {
                openTextProject(id, kind, frame, meta, titleEl);
            }
        } catch (e) {
            if (meta) {
                meta.innerHTML = global.UICore
                    ? UICore.errorState(e.message)
                    : `<div class="panel-error">${esc(e.message)}</div>`;
            }
            toast(e.message, 'error');
        }
    }

    async function openSonyaStudioProject(id, frame, meta, titleEl) {
        const r = await fetch(`/api/sonya/projects/${id}`, { credentials: 'same-origin' });
        const data = global.UICore?.parseApiJson
            ? await UICore.parseApiJson(r, 'Проект Сони')
            : await r.json();
        if (!r.ok) throw new Error(data.detail || `HTTP ${r.status}`);
        const ver = data.current_version || {};
        if (titleEl) titleEl.textContent = data.title || 'UI проект';
        if (ver.react_code && global.ReactPreview?.buildIframeHtml) {
            frame.srcdoc = ReactPreview.buildIframeHtml(ver.react_code);
        } else {
            frame.srcdoc = '<html><body style="margin:0;background:#0e1016;color:#888;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui">Нет превью</body></html>';
        }
        const colors = (data.colors || []).slice(0, 6).map((c) =>
            `<span class="color-swatch" style="background:${c}" title="${c}"></span>`).join('');
        if (meta) {
            meta.innerHTML = `
                <div class="ap-preview-info">
                    <p>${esc(data.description || ver.task || '')}</p>
                    <div class="ss-badges">
                        <span class="ss-badge">${esc(data.status || 'draft')}</span>
                        <span class="ss-badge">v${ver.version_num || 1}</span>
                    </div>
                    <div class="color-row">${colors}</div>
                    <p class="muted ap-preview-hint">Просмотр в Обучении · для редактирования откройте Sonya Studio</p>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('sonya-studio');SonyaStudio.openProject('${esc(id)}')">✨ Открыть в Studio</button>
                </div>`;
        }
    }

    async function openDeliverable(id, frame, meta, titleEl) {
        const agent = agentById(activeAgentId);
        const project = (agent?.projects || []).find((p) => p.id === id && p.kind === 'deliverable');
        if (titleEl) titleEl.textContent = project?.title || 'Артефакт';
        frame.src = `/api/projects/${encodeURIComponent(id)}/preview`;
        if (meta) {
            meta.innerHTML = `
                <div class="ap-preview-info">
                    <p>${esc(project?.description || '')}</p>
                    <span class="dl-memory-badge">${esc(project?.type_label || 'Артефакт')}</span>
                </div>`;
        }
    }

    function openTextProject(id, kind, frame, meta, titleEl) {
        const agent = agentById(activeAgentId);
        const project = (agent?.projects || []).find((p) => p.id === id);
        if (!project) throw new Error('Проект не найден');
        if (titleEl) titleEl.textContent = project.title || 'Проект';
        const body = `
            <html><head><meta charset="utf-8"><style>
            body{margin:0;padding:24px;background:#0e1016;color:#e8e8ef;font-family:system-ui,sans-serif;line-height:1.5}
            h1{font-size:1.25rem;margin:0 0 12px} .badge{display:inline-block;padding:2px 8px;border-radius:6px;background:#2a2b35;font-size:12px;color:#9aa0b4;margin-bottom:12px}
            p{color:#b8bcc8;white-space:pre-wrap}</style></head><body>
            <span class="badge">${esc(KIND_LABELS[kind] || kind)}</span>
            <h1>${esc(project.title)}</h1>
            <p>${esc(project.description || project.topic || 'Без описания')}</p>
            </body></html>`;
        frame.srcdoc = body;
        if (meta) {
            meta.innerHTML = `
                <div class="ap-preview-info">
                    <span class="dl-memory-badge">${esc(KIND_LABELS[kind] || kind)}</span>
                    ${project.topic ? `<p class="muted">Тема: ${esc(project.topic)}</p>` : ''}
                    ${project.last_score ? `<p>Оценка Маши: <strong>${project.last_score}/10</strong></p>` : ''}
                </div>`;
        }
    }

    function closePreview(rerender = true) {
        previewOpen = false;
        el('apPreviewPanel')?.classList.add('hidden');
        el('apProjectsGrid')?.classList.remove('hidden');
        el('apListHeader')?.classList.remove('hidden');
        const frame = el('apPreviewFrame');
        if (frame) {
            frame.removeAttribute('src');
            frame.srcdoc = '';
        }
        if (rerender) renderAgentPanel();
    }

    /** Совместимость: открыть проект Сони из Design Lab */
    function openSonyaProject(id) {
        activeAgentId = 'frontend';
        if (!hub) {
            load('frontend').then(() => openProject(id, 'sonya_studio'));
            return;
        }
        renderAgentTabs();
        renderAgentPanel();
        openProject(id, 'sonya_studio');
    }

    global.AgentLearningProjects = {
        load,
        openProject,
        openSonyaProject,
        closePreview,
    };
})(window);
