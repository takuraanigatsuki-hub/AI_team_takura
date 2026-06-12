/**
 * Admin — пользователи, баланс, сайт, консоль Cursor & AI
 */
(function (global) {
    let activeSection = 'console';
    let users = [];
    let plans = [];
    let agents = [];
    let siteInfo = null;
    let consoleLog = [];

    function esc(s) {
        return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function canAccess(user) {
        if (!user) return false;
        if (user.is_owner || user.role === 'owner') return true;
        const p = user.privileges || [];
        return p.includes('admin') || p.includes('manage_users') || p.includes('manage_settings');
    }

    function canManageUsers(user) {
        if (!user) return false;
        if (user.is_owner) return true;
        const p = user.privileges || [];
        return p.includes('manage_users') || p.includes('admin');
    }

    function canManageSite(user) {
        if (!user) return false;
        if (user.is_owner) return true;
        const p = user.privileges || [];
        return p.includes('manage_settings') || p.includes('admin');
    }

    function updateNavVisibility(user) {
        const tab = document.getElementById('adminNavTab');
        if (tab) tab.classList.toggle('hidden', !canAccess(user));
    }

    function renderNav(user) {
        const nav = document.getElementById('adminNav');
        if (!nav) return;
        const items = [
            { id: 'console', label: '🖥 Консоль AI & Cursor', show: true },
            { id: 'users', label: '👥 Пользователи', show: canManageUsers(user) },
            { id: 'site', label: '🌐 Сайт и настройки', show: canManageSite(user) },
        ].filter((i) => i.show);
        nav.innerHTML = items.map((i) =>
            `<button type="button" class="admin-nav-btn ${i.id === activeSection ? 'active' : ''}"
                onclick="AdminPanel.switchSection('${i.id}')">${i.label}</button>`
        ).join('');
    }

    function appendLog(lines) {
        const arr = Array.isArray(lines) ? lines : [lines];
        consoleLog = consoleLog.concat(arr).slice(-80);
        const el = document.getElementById('adminConsoleLog');
        if (el) {
            el.innerHTML = consoleLog.map((l) => `<div class="console-line">${esc(l)}</div>`).join('');
            el.scrollTop = el.scrollHeight;
        }
    }

    function renderConsole(user) {
        const agentOpts = agents.map((a) =>
            `<option value="${esc(a.agent_id)}">${esc(a.emoji || '')} ${esc(a.name)}</option>`).join('');
        return `
            <div class="admin-section-head">
                <h2>🖥 Консоль управления</h2>
                <p class="muted">Cursor, задачи команде, pipeline, Git sync</p>
            </div>
            <div class="console-quick-grid">
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('team_task')">📋 Задача команде</button>
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('agent_task')">🎯 Задача агенту</button>
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('cursor_run')">⚡ Cursor run</button>
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('pipeline')">🚀 Pipeline</button>
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('git_sync')">📤 Git sync</button>
                <button type="button" class="console-chip" onclick="AdminPanel.setAction('broadcast')">📢 Broadcast</button>
            </div>
            <form class="console-form" onsubmit="AdminPanel.runConsole(event)">
                <label class="sw-label">Действие</label>
                <select id="admAction" class="design-input">
                    <option value="team_task">Задача всей команде (PM)</option>
                    <option value="agent_task">Задача одному агенту</option>
                    <option value="cursor_run">Cursor Agent</option>
                    <option value="pipeline">Pipeline one-click</option>
                    <option value="git_sync">Git sync now</option>
                    <option value="broadcast">Системное сообщение</option>
                </select>
                <label class="sw-label">Агент (для agent_task)</label>
                <select id="admAgent" class="design-input">${agentOpts}</select>
                <label class="sw-label">Repo URL (Cursor, опционально)</label>
                <input type="text" id="admRepo" class="design-input" placeholder="https://github.com/...">
                <label class="sw-label">Текст / Prompt</label>
                <textarea id="admText" class="design-input sw-textarea" rows="4" placeholder="Опишите задачу или prompt…"></textarea>
                <div class="console-form-actions">
                    <button type="submit" class="btn-primary">▶ Выполнить</button>
                    <button type="button" class="btn-secondary" onclick="Integrations.toggleCursorPanel()">⚡ Cursor Panel</button>
                    <button type="button" class="btn-secondary" onclick="AdminPanel.clearLog()">Очистить лог</button>
                </div>
            </form>
            <div class="console-log-wrap">
                <div class="console-log-head">Журнал</div>
                <div id="adminConsoleLog" class="console-log">${consoleLog.map((l) =>
                    `<div class="console-line">${esc(l)}</div>`).join('')}</div>
            </div>`;
    }

    function renderUsersTable(user) {
        const isOwner = user.is_owner;
        const rows = users.map((u) => {
            const sub = u.subscription || {};
            const readonly = u.is_owner && !isOwner;
            return `
            <tr class="${u.is_owner ? 'owner-row' : ''}">
                <td>
                    <strong>${esc(u.name)}</strong><br>
                    <span class="muted">${esc(u.email)}</span>
                </td>
                <td>${esc(u.role_label)}</td>
                <td>${esc(sub.tier_emoji || '')} ${esc(sub.tier_name || '')}<br><span class="muted">ур. ${sub.level || 1}</span></td>
                <td><strong>${esc(sub.balance_display ?? sub.balance ?? '0')}</strong></td>
                <td class="admin-user-actions">
                    ${readonly ? '<span class="ss-badge warn">👑 Owner</span>' : `
                    <select class="design-input input-sm" id="role-${esc(u.id)}" onchange="AdminPanel.saveUser('${esc(u.id)}','role')">
                        <option value="member" ${u.role === 'member' ? 'selected' : ''}>member</option>
                        <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>admin</option>
                        ${isOwner ? `<option value="owner" ${u.role === 'owner' ? 'selected' : ''}>owner</option>` : ''}
                    </select>
                    ${isOwner ? `<select class="design-input input-sm" id="tier-${esc(u.id)}" onchange="AdminPanel.saveUser('${esc(u.id)}','tier')">
                        ${(plans || []).map((p) =>
                            `<option value="${esc(p.id)}" ${sub.tier === p.id ? 'selected' : ''}>${esc(p.emoji)} ${esc(p.name_ru)}</option>`
                        ).join('')}
                    </select>` : ''}
                    <div class="admin-balance-row">
                        <input type="number" class="design-input input-sm" id="bal-${esc(u.id)}" placeholder="+кредиты" min="-99999" max="99999">
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.saveUser('${esc(u.id)}','balance')">💎</button>
                    </div>`}
                </td>
            </tr>`;
        }).join('');
        return `
            <div class="admin-section-head">
                <h2>👥 Пользователи</h2>
                <p class="muted">Роли, тарифы и баланс · всего ${users.length}</p>
            </div>
            <div class="admin-table-wrap">
                <table class="admin-table">
                    <thead><tr><th>Пользователь</th><th>Роль</th><th>Тариф</th><th>Баланс</th><th>Управление</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="5" class="muted">Нет пользователей</td></tr>'}</tbody>
                </table>
            </div>`;
    }

    function renderSite(user) {
        const cfg = siteInfo?.config || {};
        return `
            <div class="admin-section-head">
                <h2>🌐 Сайт и платформа</h2>
                <p class="muted">Агентов: ${siteInfo?.agents_count ?? '—'} · активных: ${siteInfo?.active_agents ?? '—'}</p>
            </div>
            <form class="profile-form" onsubmit="AdminPanel.saveSite(event)">
                <label class="sw-label">Интервал обучения (мин)</label>
                <div class="admin-inline-2">
                    <input type="number" id="siteMin" class="design-input" value="${cfg.learning_interval_min ?? 15}" min="5">
                    <input type="number" id="siteMax" class="design-input" value="${cfg.learning_interval_max ?? 45}" min="10">
                </div>
                <label class="sw-label">Cursor model</label>
                <input type="text" id="siteCursorModel" class="design-input" value="${esc(cfg.cursor_model || '')}">
                <label class="sw-label">Cursor repo URL</label>
                <input type="text" id="siteRepo" class="design-input" value="${esc(cfg.cursor_repo_url || '')}">
                <div class="admin-checks">
                    <label><input type="checkbox" id="sitePersist" ${cfg.persist_knowledge ? 'checked' : ''}> Сохранять знания</label>
                    <label><input type="checkbox" id="siteGit" ${cfg.git_auto_sync !== false ? 'checked' : ''}> Git auto-sync</label>
                    <label><input type="checkbox" id="siteAutoTheme" ${cfg.auto_theme ? 'checked' : ''}> Auto theme</label>
                    <label><input type="checkbox" id="siteTg" ${cfg.telegram_notify_tasks ? 'checked' : ''}> Telegram notify</label>
                    <label><input type="checkbox" id="siteCursor" ${cfg.cursor_enabled ? 'checked' : ''}> Cursor enabled</label>
                </div>
                <button type="submit" class="btn-primary btn-sm">Сохранить настройки сайта</button>
            </form>
            <div class="admin-site-stats">
                <div class="stat-card"><span class="stat-num">${cfg.llm_configured ? '✓' : '—'}</span><span class="stat-label">LLM</span></div>
                <div class="stat-card"><span class="stat-num">${cfg.figma_configured ? '✓' : '—'}</span><span class="stat-label">Figma</span></div>
                <div class="stat-card"><span class="stat-num">${cfg.cursor_github_sync ? '✓' : '—'}</span><span class="stat-label">GitHub sync</span></div>
            </div>`;
    }

    function renderContent() {
        const el = document.getElementById('adminPanelContent');
        const user = global.Auth?.getUser();
        if (!el || !user) return;
        if (!canAccess(user)) {
            el.innerHTML = '<div class="panel-empty">Недостаточно прав</div>';
            return;
        }
        if (activeSection === 'console') el.innerHTML = renderConsole(user);
        else if (activeSection === 'users') el.innerHTML = renderUsersTable(user);
        else if (activeSection === 'site') el.innerHTML = renderSite(user);
    }

    async function loadData(user) {
        const tasks = [];
        if (canManageUsers(user)) {
            tasks.push(fetch('/api/admin/users', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : { users: [] }).then((d) => { users = d.users || []; }));
            tasks.push(fetch('/api/subscription/plans').then((r) => r.ok ? r.json() : { plans: [] }).then((d) => { plans = d.plans || []; }));
        }
        if (canManageSite(user)) {
            tasks.push(fetch('/api/admin/site', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : null).then((d) => { siteInfo = d; }));
        }
        tasks.push(fetch('/api/agents').then((r) => r.ok ? r.json() : { agents: [] }).then((d) => { agents = d.agents || []; }));
        await Promise.all(tasks);
    }

    async function load() {
        const user = global.Auth?.getUser();
        updateNavVisibility(user);
        if (!canAccess(user)) return;
        renderNav(user);
        await loadData(user);
        renderContent();
    }

    function switchSection(section) {
        activeSection = section;
        renderNav(global.Auth?.getUser());
        renderContent();
    }

    function setAction(action) {
        const sel = document.getElementById('admAction');
        if (sel) sel.value = action;
        document.getElementById('admText')?.focus();
    }

    function focusConsole() {
        activeSection = 'console';
        switchSection('console');
    }

    function clearLog() {
        consoleLog = [];
        renderContent();
    }

    async function runConsole(e) {
        e.preventDefault();
        const action = document.getElementById('admAction')?.value;
        const text = document.getElementById('admText')?.value?.trim() || '';
        const agent_id = document.getElementById('admAgent')?.value || '';
        const repo_url = document.getElementById('admRepo')?.value?.trim() || '';
        appendLog(`> ${action}: ${text.slice(0, 80)}`);
        try {
            const r = await fetch('/api/admin/console', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ action, text, agent_id, repo_url, target: 'all' }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            (d.log || []).forEach((l) => appendLog(l));
            if (d.message) appendLog('✓ ' + d.message);
            if (window.UIEnhancements) UIEnhancements.toast(d.message || 'Выполнено', 'success');
        } catch (err) {
            appendLog('✗ ' + err.message);
            if (window.UIEnhancements) UIEnhancements.toast(err.message, 'error');
        }
    }

    async function saveUser(userId, mode) {
        const user = global.Auth?.getUser();
        const body = {};
        if (mode === 'role') {
            body.role = document.getElementById(`role-${userId}`)?.value;
        } else if (mode === 'balance') {
            body.balance_delta = parseInt(document.getElementById(`bal-${userId}`)?.value || '0', 10);
            if (!body.balance_delta) return;
        } else if (mode === 'tier') {
            body.tier = document.getElementById(`tier-${userId}`)?.value;
        }
        try {
            const r = await fetch(`/api/admin/users/${userId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await loadData(user);
            renderContent();
            if (window.UIEnhancements) UIEnhancements.toast('Пользователь обновлён', 'success');
        } catch (err) {
            if (window.UIEnhancements) UIEnhancements.toast(err.message, 'error');
        }
    }

    async function saveSite(e) {
        e.preventDefault();
        const body = {
            learning_interval_min: parseInt(document.getElementById('siteMin')?.value || '15', 10),
            learning_interval_max: parseInt(document.getElementById('siteMax')?.value || '45', 10),
            cursor_model: document.getElementById('siteCursorModel')?.value?.trim(),
            cursor_repo_url: document.getElementById('siteRepo')?.value?.trim(),
            persist_knowledge: document.getElementById('sitePersist')?.checked,
            git_auto_sync: document.getElementById('siteGit')?.checked,
            auto_theme: document.getElementById('siteAutoTheme')?.checked,
            telegram_notify_tasks: document.getElementById('siteTg')?.checked,
            cursor_enabled: document.getElementById('siteCursor')?.checked,
        };
        try {
            const r = await fetch('/api/admin/site', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            siteInfo = d;
            if (window.UIEnhancements) UIEnhancements.toast('Настройки сайта сохранены', 'success');
        } catch (err) {
            if (window.UIEnhancements) UIEnhancements.toast(err.message, 'error');
        }
    }

    global.AdminPanel = {
        load,
        canAccess,
        switchSection,
        setAction,
        runConsole,
        saveUser,
        saveSite,
        clearLog,
        focusConsole,
        updateNavVisibility,
    };
})(window);
