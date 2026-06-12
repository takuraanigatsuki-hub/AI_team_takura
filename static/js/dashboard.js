/**
 * Dashboard — drag-and-drop виджеты
 */
(function (global) {
    let layout = { widgets: ['hero', 'kpis', 'integrations', 'activity', 'agents', 'security', 'actions'] };
    let data = {};

    const WIDGETS = {
        hero: { title: 'Обзор', render: renderHero },
        kpis: { title: 'KPI', render: renderKpis },
        integrations: { title: 'Интеграции', render: renderIntegrations },
        activity: { title: 'Активность', render: renderActivity },
        agents: { title: 'Команда', render: renderAgents },
        security: { title: 'Security', render: renderSecurity },
        actions: { title: 'Действия', render: renderActions },
    };

    function esc(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    async function fetchJson(url, fallback = {}) {
        try {
            const r = await fetch(url, { credentials: 'same-origin' });
            if (!r.ok) return fallback;
            return await r.json();
        } catch (_) {
            return fallback;
        }
    }

    async function load() {
        const grid = document.getElementById('dashboardGrid');
        if (!grid) return;
        grid.innerHTML = '<div class="dash-loading">Загрузка…</div>';
        try {
            const user = global.Auth?.getUser?.();
            const admin = global.UIAccess?.canAccessConsole?.(user);
            const investor = user && (user.is_investor || user.can_view_investor_portal || admin);

            const [dash, tasks, activity, layoutRes] = await Promise.all([
                fetchJson('/api/dashboard', {}),
                fetchJson('/api/tasks', { stats: {}, tasks: [] }),
                fetchJson('/api/activity?limit=15', { items: [] }),
                fetchJson('/api/dashboard/layout', layout),
            ]);

            let git = {};
            let cursor = {};
            let figma = {};
            let llmUsage = {};
            let telegram = {};
            let sec = {};

            if (admin) {
                [git, cursor, figma, llmUsage, telegram, sec] = await Promise.all([
                    fetchJson('/api/git/status', {}),
                    fetchJson('/api/cursor/status', {}),
                    fetchJson('/api/figma/status', {}),
                    fetchJson('/api/llm/usage', {}),
                    fetchJson('/api/telegram/status', {}),
                    fetchJson('/api/security/dashboard', {}),
                ]);
            }

            layout = layoutRes.widgets ? layoutRes : layout;
            data = { dash, tasks, git, cursor, activity, figma, llmUsage, telegram, sec, admin, investor };
            render(grid);
            if (window.UIEnhancements) {
                const working = (dash.agents || []).filter((a) => ['working', 'learning', 'thinking'].includes(a.status)).length;
                UIEnhancements.updateAgentFooter(working);
            }
        } catch (e) {
            grid.innerHTML = `<div class="panel-error">Ошибка: ${esc(e.message)}</div>`;
        }
    }

    function render(grid) {
        const admin = data.admin || global.UIAccess?.canAccessConsole?.(global.Auth?.getUser());
        const order = (layout.widgets || Object.keys(WIDGETS)).filter((id) => {
            if (!admin && id === 'security') return false;
            if (!admin && id === 'integrations') return false;
            return true;
        });
        grid.innerHTML = `
            <div class="dash-toolbar">
                <span class="muted">Перетащите виджеты для изменения порядка</span>
                <button type="button" class="btn-secondary btn-xs" onclick="Dashboard.resetLayout()">↺ Сброс</button>
            </div>
            <div class="dash-widget-grid" id="dashWidgetGrid">${order.filter((id) => WIDGETS[id]).map((id) =>
                `<div class="dash-widget" draggable="true" data-widget="${id}">
                    <div class="dash-widget-handle" title="Перетащить">⠿ ${WIDGETS[id].title}</div>
                    <div class="dash-widget-body">${WIDGETS[id].render()}</div>
                </div>`
            ).join('')}</div>`;
        initDragDrop(document.getElementById('dashWidgetGrid'));
    }

    function initDragDrop(container) {
        if (!container) return;
        let dragged = null;
        container.querySelectorAll('.dash-widget').forEach((w) => {
            w.addEventListener('dragstart', () => { dragged = w; w.classList.add('dragging'); });
            w.addEventListener('dragend', () => { w.classList.remove('dragging'); dragged = null; saveLayoutFromDom(); });
            w.addEventListener('dragover', (e) => {
                e.preventDefault();
                const after = [...container.querySelectorAll('.dash-widget:not(.dragging)')]
                    .find((el) => e.clientY < el.getBoundingClientRect().top + el.offsetHeight / 2);
                if (dragged) container.insertBefore(dragged, after || null);
            });
        });
    }

    async function saveLayoutFromDom() {
        const ids = [...document.querySelectorAll('#dashWidgetGrid .dash-widget')].map((w) => w.dataset.widget);
        layout.widgets = ids;
        await fetch('/api/dashboard/layout', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ widgets: ids }),
        });
    }

    function resetLayout() {
        layout.widgets = ['hero', 'kpis', 'integrations', 'activity', 'agents', 'security', 'actions'];
        saveLayoutFromDom().then(() => load());
    }

    function renderHero() {
        const d = data.dash || {};
        const agents = d.agents || [];
        const working = agents.filter((a) => ['working', 'learning', 'thinking'].includes(a.status)).length;
        const llm = data.llmUsage || {};
        const llmLine = data.admin
            ? `<p class="llm-cost-inline">💰 LLM: ${llm.total_requests || 0} запросов · ~$${llm.estimated_cost_usd || 0}</p>`
            : '';
        return `<div class="dash-hero animate-in">
            <h2>Командный центр</h2>
            <p>${d.team_size || agents.length || 0} агентов · ${working} активны · ${data.tasks?.stats?.total || 0} задач</p>
            ${llmLine}
        </div>`;
    }

    function renderKpis() {
        const s = data.tasks?.stats || {};
        const gitCard = data.admin
            ? `<div class="dash-card"><div class="dash-card-num">${data.git?.changed_files || 0}</div><div class="dash-card-label">Git diff</div></div>`
            : `<div class="dash-card"><div class="dash-card-num">${s.awaiting_approval || 0}</div><div class="dash-card-label">На проверке</div></div>`;
        return `<div class="dash-cards">
            <div class="dash-card"><div class="dash-card-num">${s.completed || 0}</div><div class="dash-card-label">Выполнено</div></div>
            <div class="dash-card accent"><div class="dash-card-num">${s.active || 0}</div><div class="dash-card-label">В работе</div></div>
            <div class="dash-card"><div class="dash-card-num">${data.dash?.total_knowledge || 0}</div><div class="dash-card-label">Знаний</div></div>
            ${gitCard}
        </div>`;
    }

    function renderIntegrations() {
        const c = data.cursor || {};
        const d = data.dash || {};
        const f = data.figma || {};
        const t = data.telegram || {};
        return `<div class="dash-int-row">
            <span class="int-pill ${c.ok ? 'ok' : 'err'}">Cursor ${c.ok ? '✓' : '✗'}</span>
            <span class="int-pill ${c.github_sync ? 'ok' : ''}">GitHub Sync</span>
            <span class="int-pill ${d.figma_configured ? 'ok' : ''}">Figma</span>
            <span class="int-pill ${d.git_auto_sync ? 'ok' : ''}">Git Auto</span>
            <span class="int-pill ${t.configured ? 'ok' : ''}">Telegram</span>
        </div><p class="muted dash-repo">${esc(c.repo_url || '—')}</p>`;
    }

    function renderActivity() {
        const items = data.activity?.items || [];
        if (!items.length) return '<p class="muted">Пока нет событий</p>';
        return `<div class="activity-feed">${items.map((ev) =>
            `<div class="activity-item"><span>${ev.agent_emoji || '💬'}</span><div><strong>${esc(ev.agent_name || '')}</strong><p>${esc(ev.message)}</p></div></div>`
        ).join('')}</div>`;
    }

    function renderAgents() {
        return `<div class="dash-agents">${(data.dash?.agents || []).map((a) =>
            `<div class="dash-agent" onclick="selectAgent('${a.agent_id}');switchView('chat')">
                <span>${a.emoji}</span><div><strong>${esc(a.name)}</strong><small>${a.status}</small></div>
            </div>`
        ).join('')}</div>`;
    }

    function renderSecurity() {
        const st = data.sec?.stats || {};
        const admin = global.UIAccess?.canAccessConsole?.(global.Auth?.getUser());
        return `<div class="sec-kpis" style="grid-template-columns:repeat(2,1fr)">
            <article class="ucard ucard-kpi"><span class="ucard-kpi-val">${st.blocked_now || 0}</span><span>IP blocked</span></article>
            <article class="ucard ucard-kpi"><span class="ucard-kpi-val">${st.total_events || 0}</span><span>Events</span></article>
        </div>
        ${admin ? '<button type="button" class="btn-secondary btn-sm" onclick="switchView(\'admin\');AdminPanel?.switchSection?.(\'security\')">🛡 Подробнее</button>' : ''}`;
    }

    function renderActions() {
        const investor = data.investor;
        const team = data.admin || global.UIAccess?.canUseTeamTools?.(global.Auth?.getUser());
        return `<div class="dash-actions">
            <button type="button" class="btn-primary" onclick="switchView('chat')">Новая задача</button>
            <button type="button" class="btn-secondary" onclick="TaskTemplates.showPicker()">📋 Шаблон</button>
            ${team ? '<button type="button" class="btn-secondary" onclick="Integrations.toggleCursorPanel()">⚡ Cursor</button>' : ''}
            ${investor ? '<button type="button" class="btn-secondary" onclick="switchView(\'investor\')">💼 Investor</button>' : ''}
        </div>`;
    }

    global.Dashboard = { load, resetLayout };
})(window);
