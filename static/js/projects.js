/** Вкладка «Проекты» — финальные артефакты команды */
(function (global) {
    let filterAgent = '';
    let filterType = '';
    let filterSearch = '';
    let lastProjects = [];
    let lastStats = {};

    async function load() {
        const el = document.getElementById('projectsGrid');
        if (!el) return;
        el.innerHTML = global.UICore ? UICore.loadingState() : '<div class="dash-loading">Загрузка…</div>';
        try {
            let url = '/api/projects?limit=100&deliverables=true';
            if (filterAgent) url += `&agent_id=${encodeURIComponent(filterAgent)}`;
            if (filterType) url += `&type=${encodeURIComponent(filterType)}`;
            const r = await fetch(url, { credentials: 'same-origin' });
            if (!r.ok) {
                if (r.status === 401) {
                    el.innerHTML = global.UICore ? UICore.authRequiredState({
                        title: 'Войдите для просмотра проектов',
                    }) : `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">🔐</div>
                        <h3>Войдите для просмотра проектов</h3>
                        <a href="/?auth=login" class="btn-primary btn-sm">Войти</a></div>`;
                    return;
                }
                throw new Error('Не удалось загрузить проекты');
            }
            const d = await r.json();
            lastProjects = d.projects || [];
            lastStats = d.stats || {};
            render(d, el);
        } catch (e) {
            el.innerHTML = global.UICore
                ? UICore.errorState(e.message, { retryOnclick: 'ProjectsUI.load()' })
                : `<div class="panel-error">${e.message}</div>`;
        }
    }

    const TYPE_LABELS = {
        presentation: '📽️ Презентация',
        model_3d: '🧊 3D',
        ui: '🎨 UI',
        site: '🌐 Сайт',
        code: '💻 Код',
        document: '📝 Документ',
    };

    async function cleanup() {
        if (!confirm('Удалить промежуточные артефакты и оставить только готовые проекты?')) return;
        try {
            const r = await fetch('/api/projects/cleanup', { method: 'DELETE', credentials: 'same-origin' });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            if (global.UIEnhancements) UIEnhancements.toast(`Очищено: ${d.removed || 0}`, 'success');
            load();
        } catch (e) {
            if (global.UIEnhancements) UIEnhancements.toast(e.message, 'error');
            else alert(e.message);
        }
    }

    function render(data, el) {
        const stats = data.stats || {};
        let projects = data.projects || [];
        if (filterSearch) {
            const q = filterSearch.toLowerCase();
            projects = projects.filter((p) => {
                const hay = `${p.title || ''} ${p.description || ''} ${(p.tags || []).join(' ')} ${p.agent_name || ''}`.toLowerCase();
                return hay.includes(q);
            });
        }
        const statEl = document.getElementById('projectsStats');
        if (statEl) {
            statEl.innerHTML = `
                <div class="stat-card"><span class="stat-num">${stats.total || 0}</span><span class="stat-label">Готовых</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.presentation || 0}</span><span class="stat-label">Презентации</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.model_3d || 0}</span><span class="stat-label">3D</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.ui || stats.by_type?.site || 0}</span><span class="stat-label">UI / Сайты</span></div>`;
        }

        if (!projects.length) {
            el.innerHTML = global.UICore ? UICore.emptyState({
                icon: '📦',
                title: 'Нет готовых проектов',
                text: 'Отправьте задачу — финальный результат появится здесь',
                primaryLabel: 'Новая задача',
                primaryOnclick: "switchView('chat')",
            }) : '<div class="projects-empty"><div class="welcome-icon">📦</div><p>Нет проектов</p></div>';
            return;
        }

        el.innerHTML = projects.map((p) => `
            <article class="project-card ${p.type}">
                <div class="pc-head">
                    <span class="pc-type">${TYPE_LABELS[p.type] || p.type}</span>
                    <span class="pc-agent">${p.agent_emoji || ''} ${escape(p.agent_name || p.agent_id)}</span>
                </div>
                <h3 class="pc-title">${escape(p.title)}</h3>
                <p class="pc-desc">${escape((p.description || '').slice(0, 120))}</p>
                <div class="pc-actions">
                    ${p.has_preview ? `<a href="/api/projects/${p.id}/preview" target="_blank" rel="noopener" class="btn-primary btn-sm">Открыть</a>` : ''}
                    ${p.type === 'site' || p.type === 'ui' ? `<button type="button" class="btn-secondary btn-sm" onclick="switchView('sites')">🌐 Сайты</button>` : ''}
                    <button type="button" class="btn-secondary btn-sm" onclick="window.open('/api/projects/${p.id}/export?format=print','_blank')">PDF</button>
                </div>
                <time class="pc-time">${(p.created_at || '').slice(0, 16).replace('T', ' ')}</time>
            </article>`).join('');
    }

    function setFilter(agent, type) {
        filterAgent = agent || '';
        filterType = type || '';
        document.querySelectorAll('.proj-filter').forEach((b) => {
            b.classList.toggle('active', b.dataset.agent === filterAgent && b.dataset.type === filterType);
        });
        load();
    }

    function setSearch(query) {
        filterSearch = (query || '').trim().toLowerCase();
        const el = document.getElementById('projectsGrid');
        if (el && lastProjects.length) {
            render({ projects: lastProjects, stats: lastStats }, el);
        } else {
            load();
        }
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.ProjectsUI = { load, setFilter, setSearch, cleanup };
})(window);
