/** Вкладка «Проекты» — все артефакты команды */
(function (global) {
    let filterAgent = '';
    let filterType = '';
    let filterSearch = '';
    let lastProjects = [];
    let lastStats = {};

    async function load() {
        const el = document.getElementById('projectsGrid');
        if (!el) return;
        el.innerHTML = '<div class="panel-empty">Загрузка…</div>';
        try {
            let url = '/api/projects?limit=100';
            if (filterAgent) url += `&agent_id=${encodeURIComponent(filterAgent)}`;
            if (filterType) url += `&type=${encodeURIComponent(filterType)}`;
            const r = await fetch(url);
            const d = await r.json();
            lastProjects = d.projects || [];
            lastStats = d.stats || {};
            render(d, el);
        } catch (e) {
            el.innerHTML = `<div class="panel-error">${e.message}</div>`;
        }
    }

    const TYPE_LABELS = {
        presentation: '📽️ Презентация',
        model_3d: '🧊 3D',
        ui: '🎨 UI',
        code: '💻 Код',
        architecture: '🏛️ Архитектура',
        tests: '🧪 Тесты',
        document: '📝 Док',
        infra: '🔧 Infra',
        review: '🔍 Review',
        plan: '📋 План',
    };

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
                <div class="stat-card"><span class="stat-num">${stats.total || 0}</span><span class="stat-label">Всего</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.presentation || 0}</span><span class="stat-label">Презентации</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.model_3d || 0}</span><span class="stat-label">3D</span></div>
                <div class="stat-card"><span class="stat-num">${stats.by_type?.code || 0}</span><span class="stat-label">Код</span></div>`;
        }

        if (!projects.length) {
            el.innerHTML = '<div class="projects-empty"><div class="welcome-icon">📦</div><p>Нет проектов — отправьте задачу агенту</p></div>';
            return;
        }

        el.innerHTML = projects.map((p) => `
            <article class="project-card ${p.type}">
                <div class="pc-head">
                    <span class="pc-type">${TYPE_LABELS[p.type] || p.type}</span>
                    <span class="pc-agent">${p.agent_emoji || ''} ${escape(p.agent_name || p.agent_id)}</span>
                </div>
                <h3 class="pc-title">${escape(p.title)}</h3>
                <p class="pc-desc">${escape((p.description || '').slice(0, 100))}</p>
                <div class="pc-tags">${(p.tags || []).slice(0, 4).map((t) => `<span class="tag">${escape(t)}</span>`).join('')}</div>
                <div class="pc-actions">
                    ${p.has_preview ? `<a href="/api/projects/${p.id}/preview" target="_blank" class="btn-primary btn-sm">Открыть</a>` : ''}
                    <button type="button" class="btn-secondary btn-sm" onclick="window.open('/api/projects/${p.id}/export?format=print','_blank')">PDF</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="ProjectsUI.diffWith('${p.id}')">Diff</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="PowerPack.createPR('${p.id}')">PR</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="AgentActivity.open('${p.agent_id}')">Агент</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="ProjectsUI.revise('${p.agent_id}','${p.id}')">✏️</button>
                </div>
                <time class="pc-time">${(p.created_at || '').slice(0, 16).replace('T', ' ')} · v${p.version || 1}</time>
            </article>`).join('');
    }

    async function diffWith(id) {
        const other = prompt('ID второго проекта для сравнения:');
        if (!other) return;
        const r = await fetch(`/api/projects/${id}/diff/${other}`);
        const d = await r.json();
        if (window.PowerPack) PowerPack.showDiffModal(d);
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

    function revise(agentId, artifactId) {
        if (window.AgentActivity) AgentActivity.revise(agentId, artifactId);
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.ProjectsUI = { load, setFilter, setSearch, revise, diffWith };
})(window);
