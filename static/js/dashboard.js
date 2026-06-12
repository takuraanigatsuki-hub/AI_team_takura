/**
 * Synora-style Dashboard — командный центр, аналитика, интеграции
 */
(function (global) {
    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function fmtDateTime(iso) {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleString('ru', {
                day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            });
        } catch (_) {
            return String(iso).slice(0, 16).replace('T', ' ');
        }
    }

    function kpiCard(icon, value, label, hint, accent) {
        return `
        <article class="syn-kpi${accent ? ' syn-kpi-accent' : ''}">
            <span class="syn-kpi-icon">${icon}</span>
            <div class="syn-kpi-body">
                <div class="syn-kpi-val">${esc(value)}</div>
                <div class="syn-kpi-label">${esc(label)}</div>
                ${hint ? `<div class="syn-kpi-hint">${esc(hint)}</div>` : ''}
            </div>
        </article>`;
    }

    function progressBar(pct, label, color) {
        const p = Math.min(100, Math.max(0, Number(pct) || 0));
        const style = color ? ` style="width:${p}%;background:${color}"` : ` style="width:${p}%"`;
        return `
        <div class="syn-progress">
            <div class="syn-progress-head"><span>${esc(label)}</span><strong>${p}%</strong></div>
            <div class="syn-progress-track"><div class="syn-progress-fill"${style}></div></div>
        </div>`;
    }

    function barChart(bars) {
        const max = Math.max(...bars.map((b) => b.value), 1);
        return `<div class="syn-bars">${bars.map((b) => `
            <div class="syn-bar-row">
                <span class="syn-bar-label">${esc(b.label)}</span>
                <div class="syn-bar-track">
                    <div class="syn-bar-fill" style="width:${Math.round((b.value / max) * 100)}%;background:${b.color || ''}"></div>
                </div>
                <span class="syn-bar-val">${esc(b.value)}</span>
            </div>`).join('')}</div>`;
    }

    function statusDot(status) {
        const map = {
            working: 'busy', learning: 'busy', thinking: 'busy',
            idle: 'idle', offline: 'off', error: 'err',
        };
        return map[status] || 'idle';
    }

    function activityIcon(type) {
        return ({
            system: '🔔', task_done: '✅', task_received: '📋', error: '❌',
            github_sync_started: '🔗', github_sync_done: '✓', git_sync_done: '📤',
            cursor_progress: '⚡', figma_import: '🎨',
        }[type] || '💬');
    }

    function activityLabel(type) {
        return ({
            system: 'Система', task_done: 'Задача', task_received: 'Задача',
            github_sync_started: 'GitHub', github_sync_done: 'GitHub', git_sync_done: 'Git Sync',
        }[type] || 'Событие');
    }

    function renderActivity(items) {
        if (!items?.length) {
            return '<p class="muted syn-empty">Пока нет событий — начните работу в чате.</p>';
        }
        return `<ul class="syn-timeline">${items.map((ev) => `
            <li class="syn-timeline-item">
                <div class="syn-timeline-dot"></div>
                <div class="syn-timeline-body">
                    <div class="syn-timeline-top">
                        <strong>${esc(ev.agent_name || activityLabel(ev.type))}</strong>
                        <time class="muted">${fmtDateTime(ev.timestamp)}</time>
                    </div>
                    <p class="syn-timeline-text">${esc(ev.message)}</p>
                    <span class="syn-timeline-meta">${ev.agent_emoji || activityIcon(ev.type)} ${esc(ev.type)}</span>
                </div>
            </li>`).join('')}</ul>`;
    }

    function integrationRow(name, ok, detail) {
        return `
        <div class="syn-int-row">
            <span class="syn-int-status ${ok ? 'ok' : 'err'}">${ok ? '●' : '○'}</span>
            <div class="syn-int-info">
                <strong>${esc(name)}</strong>
                ${detail ? `<span class="muted">${esc(detail)}</span>` : ''}
            </div>
            <span class="syn-int-badge ${ok ? 'ok' : ''}">${ok ? 'Online' : 'Offline'}</span>
        </div>`;
    }

    function agentCard(a) {
        return `
        <article class="syn-agent" onclick="selectAgent('${esc(a.agent_id)}');switchView('chat')" role="button" tabindex="0">
            <div class="syn-agent-top">
                <span class="syn-agent-emoji">${a.emoji}</span>
                <span class="syn-agent-dot syn-dot-${statusDot(a.status)}"></span>
            </div>
            <strong class="syn-agent-name">${esc(a.name)}</strong>
            <span class="syn-agent-role muted">${esc(a.role || 'агент')}</span>
            <div class="syn-agent-meta">
                <span>${esc(a.status)}</span>
                <span>${a.learned_count || 0} тем</span>
            </div>
        </article>`;
    }

    async function load() {
        const grid = document.getElementById('dashboardGrid');
        if (!grid) return;
        grid.innerHTML = '<div class="syn-loading"><div class="syn-spinner"></div>Загрузка Synora Dashboard…</div>';

        try {
            const [dash, tasks, git, cursor, activity, figma, llmUsage, telegram] = await Promise.all([
                fetch('/api/dashboard').then((r) => r.json()),
                fetch('/api/tasks').then((r) => r.json()),
                fetch('/api/git/status').then((r) => r.json()),
                fetch('/api/cursor/status').then((r) => r.json()),
                fetch('/api/activity?limit=12').then((r) => r.json()),
                fetch('/api/figma/status').then((r) => r.json()),
                fetch('/api/llm/usage').then((r) => r.json()).catch(() => ({})),
                fetch('/api/telegram/status').then((r) => r.json()).catch(() => ({})),
            ]);

            const agents = dash.agents || [];
            const stats = tasks.stats || dash.task_stats || {};
            const working = agents.filter((a) => ['working', 'learning', 'thinking'].includes(a.status)).length;
            const idle = agents.length - working;
            const teamUtil = agents.length ? Math.round((working / agents.length) * 100) : 0;
            const successRate = stats.total ? Math.round(((stats.completed || 0) / stats.total) * 100) : 0;
            const intOk = [cursor.ok, dash.figma_configured, dash.git_auto_sync, telegram.configured].filter(Boolean).length;

            grid.innerHTML = `
            <div class="syn-dash animate-in">
                <header class="syn-hero">
                    <div class="syn-hero-left">
                        <div class="syn-brand">
                            <span class="syn-brand-icon">✦</span>
                            <div>
                                <p class="syn-hero-greet">Synora · AI Team Management</p>
                                <h1 class="syn-hero-title">Командный центр</h1>
                                <p class="muted syn-hero-sub">${dash.team_size || agents.length} агентов · ${working} активны · ${stats.total || 0} задач</p>
                            </div>
                        </div>
                    </div>
                    <div class="syn-hero-stats">
                        <div class="syn-hero-stat">
                            <span class="syn-hero-stat-val">${teamUtil}%</span>
                            <span class="muted">загрузка</span>
                        </div>
                        <div class="syn-hero-stat">
                            <span class="syn-hero-stat-val">${successRate}%</span>
                            <span class="muted">успех</span>
                        </div>
                        <div class="syn-hero-stat">
                            <span class="syn-hero-stat-val">$${llmUsage.estimated_cost_usd || 0}</span>
                            <span class="muted">LLM cost</span>
                        </div>
                    </div>
                </header>

                <div class="syn-kpi-grid">
                    ${kpiCard('✅', stats.completed || 0, 'Выполнено', `${successRate}% успех`, true)}
                    ${kpiCard('⚡', stats.active || 0, 'В работе', `${stats.queued || 0} в очереди`)}
                    ${kpiCard('📚', dash.total_knowledge || 0, 'Знаний', 'база агентов')}
                    ${kpiCard('🔗', git.changed_files || 0, 'Git изменений', git.branch || '—')}
                    ${kpiCard('🤖', llmUsage.total_requests || 0, 'AI запросов', `${llmUsage.estimated_cost_rub || 0} ₽`)}
                    ${kpiCard('👥', working, 'Агентов онлайн', `${idle} свободно`)}
                </div>

                <div class="syn-split">
                    <section class="syn-panel">
                        <div class="syn-panel-head">
                            <h3>📊 Аналитика задач</h3>
                            <span class="syn-panel-tag">Live</span>
                        </div>
                        ${barChart([
                            { label: 'Выполнено', value: stats.completed || 0, color: 'linear-gradient(90deg,#34d399,#5ecf8a)' },
                            { label: 'В работе', value: stats.active || 0, color: 'linear-gradient(90deg,#6c63ff,#9d4edd)' },
                            { label: 'В очереди', value: stats.queued || 0, color: 'linear-gradient(90deg,#56cfe1,#7aa2ff)' },
                            { label: 'Ошибки', value: stats.failed || 0, color: 'linear-gradient(90deg,#f87171,#f07178)' },
                        ])}
                        <div class="syn-metrics">
                            ${progressBar(teamUtil, 'Загрузка команды')}
                            ${progressBar(successRate, 'Успешность задач')}
                            ${progressBar(Math.min(100, intOk * 25), 'Интеграции', null)}
                        </div>
                    </section>

                    <section class="syn-panel">
                        <div class="syn-panel-head">
                            <h3>🔌 Интеграции</h3>
                            <span class="syn-panel-tag ${intOk >= 3 ? 'ok' : ''}">${intOk}/4 online</span>
                        </div>
                        <div class="syn-int-list">
                            ${integrationRow('Cursor Cloud', cursor.ok, cursor.repo_url ? cursor.repo_url.replace('https://github.com/', '') : 'не настроен')}
                            ${integrationRow('GitHub Sync', cursor.github_sync, cursor.github_sync ? 'авто-синхронизация' : 'выключено')}
                            ${integrationRow('Figma', dash.figma_configured, figma.user_handle ? `@${figma.user_handle}` : (figma.auth_method === 'pat' ? 'PAT' : 'не подключён'))}
                            ${integrationRow('Telegram', telegram.configured, telegram.username ? `@${telegram.username}` : 'бот не настроен')}
                            ${integrationRow('Git Auto-Sync', dash.git_auto_sync, git.last_sync ? `посл. ${fmtDateTime(git.last_sync)}` : 'ожидание')}
                        </div>
                        <p class="syn-repo muted">${esc(cursor.repo_url || dash.cursor_repo_url || 'Репозиторий не указан')}</p>
                    </section>
                </div>

                <div class="syn-split">
                    <section class="syn-panel">
                        <div class="syn-panel-head">
                            <h3>📡 Лента активности</h3>
                            <button type="button" class="btn-secondary btn-sm" onclick="switchView('timeline')">Timeline →</button>
                        </div>
                        ${renderActivity(activity.items)}
                    </section>

                    <section class="syn-panel">
                        <div class="syn-panel-head">
                            <h3>👥 Команда</h3>
                            <button type="button" class="btn-secondary btn-sm" onclick="switchView('chat')">Чат →</button>
                        </div>
                        <div class="syn-agents">${agents.map(agentCard).join('')}</div>
                    </section>
                </div>

                <footer class="syn-quick-bar">
                    <button type="button" class="syn-quick-btn primary" onclick="switchView('chat');document.getElementById('messageInput')?.focus()">
                        <span>＋</span> Новая задача
                    </button>
                    <button type="button" class="syn-quick-btn" onclick="UIEnhancements?.syncNow()">📤 Sync GitHub</button>
                    <button type="button" class="syn-quick-btn" onclick="Integrations?.toggleCursorPanel()">⚡ Cursor</button>
                    <button type="button" class="syn-quick-btn" onclick="ReactPreview?.toggle()">🎨 Preview</button>
                    <button type="button" class="syn-quick-btn" onclick="switchView('kanban')">📌 Kanban</button>
                    <button type="button" class="syn-quick-btn" onclick="switchView('sonya-studio')">✨ Studio</button>
                </footer>
            </div>`;

            if (window.UIEnhancements) UIEnhancements.updateAgentFooter(working);
        } catch (e) {
            grid.innerHTML = `<div class="panel-error">Ошибка загрузки: ${esc(e.message)}</div>`;
        }
    }

    global.Dashboard = { load };
})(window);
