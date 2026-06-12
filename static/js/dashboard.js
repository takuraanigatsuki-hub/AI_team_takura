/**
 * Dashboard — сводка команды, интеграций и Git
 */
(function (global) {
    async function load() {
        const grid = document.getElementById('dashboardGrid');
        if (!grid) return;
        grid.innerHTML = '<div class="dash-loading">Загрузка…</div>';

        try {
            const [dash, tasks, git, cursor, activity, figma, llmUsage, telegram] = await Promise.all([
                fetch('/api/dashboard').then((r) => r.json()),
                fetch('/api/tasks').then((r) => r.json()),
                fetch('/api/git/status').then((r) => r.json()),
                fetch('/api/cursor/status').then((r) => r.json()),
                fetch('/api/activity?limit=15').then((r) => r.json()),
                fetch('/api/figma/status').then((r) => r.json()),
                fetch('/api/llm/usage').then((r) => r.json()).catch(() => ({})),
                fetch('/api/telegram/status').then((r) => r.json()).catch(() => ({})),
            ]);

            const agents = dash.agents || [];
            const working = agents.filter((a) => ['working', 'learning', 'thinking'].includes(a.status)).length;

            grid.innerHTML = `
                <div class="dash-hero animate-in">
                    <h2>Командный центр</h2>
                    <p>${dash.team_size || 9} агентов · ${working} активны · ${tasks.stats?.total || 0} задач всего</p>
                    <p class="llm-cost-inline">💰 LLM: ${llmUsage.total_requests || 0} запросов · ~$${llmUsage.estimated_cost_usd || 0} · ${llmUsage.estimated_cost_rub || 0}₽</p>
                </div>
                <div class="dash-cards">
                    <div class="dash-card">
                        <div class="dash-card-icon">📋</div>
                        <div class="dash-card-num">${tasks.stats?.completed || 0}</div>
                        <div class="dash-card-label">Выполнено</div>
                    </div>
                    <div class="dash-card accent">
                        <div class="dash-card-icon">⚡</div>
                        <div class="dash-card-num">${tasks.stats?.active || 0}</div>
                        <div class="dash-card-label">В работе</div>
                    </div>
                    <div class="dash-card">
                        <div class="dash-card-icon">📚</div>
                        <div class="dash-card-num">${dash.total_knowledge || 0}</div>
                        <div class="dash-card-label">Знаний</div>
                    </div>
                    <div class="dash-card">
                        <div class="dash-card-icon">🔗</div>
                        <div class="dash-card-num">${git.changed_files || 0}</div>
                        <div class="dash-card-label">Изменений git</div>
                    </div>
                </div>
                <div class="dash-section">
                    <h3>Интеграции</h3>
                    <div class="dash-int-row">
                        <span class="int-pill ${cursor.ok ? 'ok' : 'err'}">Cursor ${cursor.ok ? '✓' : '✗'}</span>
                        <span class="int-pill ${cursor.github_sync ? 'ok' : ''}">GitHub Sync</span>
                        <span class="int-pill ${dash.figma_configured ? 'ok' : ''}">Figma${figma.user_handle ? ` · @${figma.user_handle}` : (figma.auth_method === 'pat' ? ' · PAT' : '')}</span>
                        <span class="int-pill ${dash.git_auto_sync ? 'ok' : ''}">Git Auto-Sync</span>
                        <span class="int-pill ${telegram.configured ? 'ok' : ''}">Telegram${telegram.username ? ` @${telegram.username}` : ''}</span>
                    </div>
                    <p class="muted dash-repo">${cursor.repo_url || '—'}</p>
                </div>
                <div class="dash-section">
                    <h3>Последняя активность</h3>
                    <div class="activity-feed">${(activity.items || []).length ? (activity.items || []).map((ev) => `
                        <div class="activity-item">
                            <span class="activity-emoji">${ev.agent_emoji || activityIcon(ev.type)}</span>
                            <div class="activity-body">
                                <strong>${ev.agent_name || activityLabel(ev.type)}</strong>
                                <p>${escapeDash(ev.message)}</p>
                                <small>${ev.timestamp ? new Date(ev.timestamp).toLocaleString('ru') : ''}</small>
                            </div>
                        </div>`).join('') : '<p class="muted">Пока нет событий</p>'}
                    </div>
                </div>
                <div class="dash-section">
                    <h3>Команда</h3>
                    <div class="dash-agents">${agents.map((a) => `
                        <div class="dash-agent" onclick="selectAgent('${a.agent_id}');switchView('chat')">
                            <span class="dash-agent-emoji">${a.emoji}</span>
                            <div>
                                <strong>${a.name}</strong>
                                <small>${a.status} · ${a.learned_count || 0} тем</small>
                            </div>
                            <span class="status-dot status-${a.status}"></span>
                        </div>`).join('')}
                    </div>
                </div>
                <div class="dash-section">
                    <h3>Быстрые действия</h3>
                    <div class="dash-actions">
                        <button type="button" class="btn-primary" onclick="switchView('chat');document.getElementById('messageInput').focus()">Новая задача</button>
                        <button type="button" class="btn-secondary" onclick="UIEnhancements.syncNow()">📤 Sync GitHub</button>
                        <button type="button" class="btn-secondary" onclick="Integrations.toggleCursorPanel()">⚡ Cursor</button>
                        <button type="button" class="btn-secondary" onclick="ReactPreview.toggle()">🎨 Preview</button>
                    </div>
                </div>`;

            if (window.UIEnhancements) UIEnhancements.updateAgentFooter(working);
        } catch (e) {
            grid.innerHTML = `<div class="panel-error">Ошибка: ${e.message}</div>`;
        }
    }

    function escapeDash(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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

    global.Dashboard = { load };
})(window);
