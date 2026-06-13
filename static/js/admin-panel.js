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
    let roleCounts = {};
    let privilegesCatalog = [];
    let userFilter = '';
    let roleFilter = '';
    let expandedUserId = null;

    function esc(s) {
        return String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function canAccess(user) {
        if (!user) return false;
        if (user.is_owner || user.role === 'owner') return true;
        if (user.role === 'admin' || user.role === 'tech_admin') return true;
        const p = user.privileges || [];
        return p.includes('admin') || p.includes('manage_users') || p.includes('manage_settings');
    }

    function roleBadgeFor(user) {
        if (global.Auth?.roleBadgeHtml) return global.Auth.roleBadgeHtml(user);
        return `<span class="role-badge role-user">👤 ${esc(user?.role_label || 'Пользователь')}</span>`;
    }

    function canManageUsers(user) {
        if (!user) return false;
        if (user.is_owner || user.role === 'owner') return true;
        if (user.role === 'tech_admin') return true;
        const p = user.privileges || [];
        return p.includes('manage_users') || p.includes('admin');
    }

    function isOwner(user) {
        return !!(user?.is_owner || user?.role === 'owner');
    }

    function canSetTier(user) {
        return isOwner(user) || user?.role === 'admin';
    }

    function canSetPrivileges(user) {
        return isOwner(user);
    }

    function canResetPassword(user) {
        return isOwner(user);
    }

    function assignableRoles(adminUser) {
        const map = {
            owner: ['owner', 'admin', 'tech_admin', 'support', 'investor', 'member'],
            admin: ['admin', 'tech_admin', 'support', 'investor', 'member'],
            tech_admin: ['support', 'investor', 'member'],
        };
        return map[adminUser?.role] || ['member'];
    }

    function roleOptionsHtml(selected, adminUser, targetUser) {
        const allowed = assignableRoles(adminUser);
        const all = [
            ['member', '👤 Пользователь'],
            ['investor', '💼 Инвестор'],
            ['support', '💬 Поддержка'],
            ['admin', '🛡 Админ'],
            ['tech_admin', '⚙ Тех. админ'],
            ['owner', '👑 Владелец'],
        ];
        const opts = all.filter(([val]) => allowed.includes(val) || val === selected);
        if (targetUser?.is_owner && !isOwner(adminUser)) {
            return `<option value="owner" selected>👑 Владелец</option>`;
        }
        return opts.map(([val, label]) =>
            `<option value="${val}" ${selected === val ? 'selected' : ''}>${label}</option>`
        ).join('');
    }

    function canEditUser(adminUser, targetUser) {
        if (targetUser.is_owner && !isOwner(adminUser)) return false;
        if (adminUser.role === 'tech_admin' && ['owner', 'admin', 'tech_admin'].includes(targetUser.role)) {
            return false;
        }
        return true;
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleString('ru', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return iso.slice(0, 10);
        }
    }

    function filteredUsers() {
        return users.filter((u) => {
            if (roleFilter && u.role !== roleFilter) return false;
            if (!userFilter) return true;
            const q = userFilter.toLowerCase();
            return (u.email || '').toLowerCase().includes(q) || (u.name || '').toLowerCase().includes(q);
        });
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
        if (global.Auth?.updateNavVisibility) Auth.updateNavVisibility(user);
    }

    function renderNav(user) {
        const nav = document.getElementById('adminNav');
        if (!nav) return;
        const items = [
            { id: 'console', label: '🖥 Консоль AI & Cursor', show: global.UIAccess?.canAccessConsole?.(user) ?? canAccess(user) },
            { id: 'security', label: '🛡 Security', show: canAccess(user) },
            { id: 'flags', label: '🚩 Feature Flags', show: canManageSite(user) },
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
        const list = filteredUsers();
        const statsHtml = Object.entries(roleCounts).map(([r, n]) =>
            `<span class="admin-role-stat">${esc(r)}: ${n}</span>`
        ).join('');

        const rows = list.map((u) => {
            const sub = u.subscription || {};
            const ts = u.task_stats || {};
            const editable = canEditUser(user, u);
            const expanded = expandedUserId === u.id;
            const disabledBadge = u.disabled ? '<span class="ss-badge warn">🚫 Заблокирован</span>' : '';

            return `
            <tr class="${u.is_owner ? 'owner-row' : ''} ${u.disabled ? 'disabled-row' : ''} ${expanded ? 'expanded-row' : ''}">
                <td>
                    <button type="button" class="admin-expand-btn" onclick="AdminPanel.toggleUser('${esc(u.id)}')" aria-expanded="${expanded}">${expanded ? '▼' : '▶'}</button>
                    <strong>${esc(u.name)}</strong> ${disabledBadge}<br>
                    <span class="muted">${esc(u.email)}</span>
                </td>
                <td>${roleBadgeFor(u)}</td>
                <td>${esc(sub.tier_emoji || '')} ${esc(sub.tier_name || '')}<br><span class="muted">ур. ${sub.level || 1}</span></td>
                <td><strong>${esc(sub.balance_display ?? sub.balance ?? '0')}</strong></td>
                <td><span class="muted">${ts.total || 0} / ${ts.active || 0} / ${ts.completed || 0}</span><br><small class="muted">всего / акт / ✓</small></td>
                <td><span class="muted">${u.active_sessions || 0}</span></td>
                <td class="admin-user-actions">
                    ${!editable ? '<span class="ss-badge warn">🔒 Защищён</span>' : `
                    <select class="design-input input-sm" id="role-${esc(u.id)}" onchange="AdminPanel.saveUser('${esc(u.id)}','role')">
                        ${roleOptionsHtml(u.role, user, u)}
                    </select>
                    ${canSetTier(user) ? `<select class="design-input input-sm" id="tier-${esc(u.id)}" onchange="AdminPanel.saveUser('${esc(u.id)}','tier')">
                        ${(plans || []).map((p) =>
                            `<option value="${esc(p.id)}" ${sub.tier === p.id ? 'selected' : ''}>${esc(p.emoji)} ${esc(p.name_ru)}</option>`
                        ).join('')}
                    </select>` : ''}
                    <div class="admin-balance-row">
                        <input type="number" class="design-input input-sm" id="bal-${esc(u.id)}" placeholder="+кредиты" min="-99999" max="99999">
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.saveUser('${esc(u.id)}','balance')">💎</button>
                    </div>
                    ${isOwner(user) ? `<div class="admin-balance-row">
                        <input type="number" class="design-input input-sm" id="setbal-${esc(u.id)}" placeholder="=баланс" min="0">
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.saveUser('${esc(u.id)}','set_balance')">=</button>
                    </div>` : ''}`}
                </td>
            </tr>
            ${expanded ? `<tr class="admin-user-detail-row"><td colspan="7">
                <div class="admin-user-detail">
                    <div class="admin-user-detail-grid">
                        <div>
                            <label class="sw-label">Имя</label>
                            <input type="text" class="design-input input-sm" id="name-${esc(u.id)}" value="${esc(u.name)}" ${editable ? '' : 'disabled'}>
                        </div>
                        <div>
                            <label class="sw-label">Стартовый экран</label>
                            <select class="design-input input-sm" id="view-${esc(u.id)}" ${editable ? '' : 'disabled'}>
                                ${['dashboard', 'chat', 'tasks', 'studio', 'profile'].map((v) =>
                                    `<option value="${v}" ${u.default_view === v ? 'selected' : ''}>${v}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div>
                            <label class="sw-label">Тема</label>
                            <select class="design-input input-sm" id="theme-${esc(u.id)}" ${editable ? '' : 'disabled'}>
                                ${['dark', 'light', 'auto'].map((v) =>
                                    `<option value="${v}" ${u.theme === v ? 'selected' : ''}>${v}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div>
                            <label class="sw-label">Регистрация</label>
                            <div class="muted admin-kv-val">${fmtDate(u.created_at)}</div>
                        </div>
                        <div>
                            <label class="sw-label">Setup</label>
                            <div class="muted admin-kv-val">${u.setup_complete ? '✓ ' + fmtDate(u.setup_at) : '⏳ не завершён'}</div>
                        </div>
                        <div>
                            <label class="sw-label">Обновлён</label>
                            <div class="muted admin-kv-val">${fmtDate(u.updated_at)}</div>
                        </div>
                    </div>
                    ${editable ? `<label class="sw-label">Заметка администратора</label>
                    <textarea class="design-input sw-textarea" id="notes-${esc(u.id)}" rows="2" placeholder="Внутренняя заметка…">${esc(u.admin_notes || '')}</textarea>
                    <div class="admin-user-detail-actions">
                        <label class="admin-check-inline"><input type="checkbox" id="disabled-${esc(u.id)}" ${u.disabled ? 'checked' : ''}> Заблокировать аккаунт</label>
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.saveUser('${esc(u.id)}','profile')">💾 Сохранить профиль</button>
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.revokeSessions('${esc(u.id)}')">🚪 Завершить сессии (${u.active_sessions || 0})</button>
                        ${canResetPassword(user) ? `<input type="password" class="design-input input-sm" id="pw-${esc(u.id)}" placeholder="Новый пароль" minlength="6">
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.resetPassword('${esc(u.id)}')">🔑 Сброс пароля</button>` : ''}
                    </div>` : ''}
                    ${canSetPrivileges(user) && editable ? `
                    <div class="admin-privileges-block">
                        <label class="sw-label">Привилегии (ручная настройка — только владелец)</label>
                        <div class="admin-privileges-grid">
                            ${(privilegesCatalog || []).map((p) => {
                                const on = (u.privileges || []).includes(p.id);
                                return `<label class="admin-priv-check"><input type="checkbox" data-uid="${esc(u.id)}" data-priv="${esc(p.id)}" ${on ? 'checked' : ''}> ${esc(p.label)}</label>`;
                            }).join('')}
                        </div>
                        <button type="button" class="btn-secondary btn-sm" onclick="AdminPanel.saveUser('${esc(u.id)}','privileges')">💾 Сохранить привилегии</button>
                    </div>` : ''}
                    ${(u.privileges || []).length ? `<p class="muted admin-priv-summary">Активные: ${(u.privileges || []).slice(0, 6).join(', ')}${(u.privileges || []).length > 6 ? '…' : ''}</p>` : ''}
                </div>
            </td></tr>` : ''}`;
        }).join('');

        return `
            <div class="admin-section-head">
                <h2>👥 Пользователи</h2>
                <p class="muted">Роли · тарифы · баланс · блокировка · сессии · ${users.length} всего</p>
                <div class="admin-user-stats">${statsHtml}</div>
            </div>
            <div class="admin-user-toolbar">
                <input type="search" class="design-input" id="adminUserSearch" placeholder="Поиск email или имени…" value="${esc(userFilter)}" oninput="AdminPanel.setUserFilter(this.value)">
                <select class="design-input input-sm" id="adminRoleFilter" onchange="AdminPanel.setRoleFilter(this.value)">
                    <option value="">Все роли</option>
                    ${['owner', 'admin', 'tech_admin', 'support', 'investor', 'member'].map((r) =>
                        `<option value="${r}" ${roleFilter === r ? 'selected' : ''}>${r}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="admin-table-wrap">
                <table class="admin-table admin-table-users">
                    <thead><tr>
                        <th>Пользователь</th><th>Роль</th><th>Тариф</th><th>Баланс</th>
                        <th>Задачи</th><th>Сессии</th><th>Управление</th>
                    </tr></thead>
                    <tbody>${rows || '<tr><td colspan="7" class="muted">Нет пользователей</td></tr>'}</tbody>
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
            el.innerHTML = global.UICore ? UICore.emptyState({
                icon: '🔒',
                title: 'Недостаточно прав',
                text: 'Admin доступен только администраторам',
            }) : '<div class="panel-empty">Недостаточно прав</div>';
            return;
        }
        if (activeSection === 'console') el.innerHTML = renderConsole(user);
        else if (activeSection === 'security') {
            el.innerHTML = '<div class="admin-section-head"><h2>🛡 Security Dashboard</h2><p class="muted">Угрозы · блокировки · audit log</p></div><div id="securityDashboard"></div>';
            if (window.SecurityDashboard) SecurityDashboard.load();
        }
        else if (activeSection === 'flags') {
            el.innerHTML = `<div class="admin-section-head"><h2>🚩 Feature Flags</h2><p class="muted">Включение функций платформы</p></div><div id="featureFlagsPanel">${global.UICore ? UICore.loadingState('Загрузка…', { compact: true }) : '<div class="dash-loading">Загрузка…</div>'}</div>`;
            loadFeatureFlags();
        }
        else if (activeSection === 'users') el.innerHTML = renderUsersTable(user);
        else if (activeSection === 'site') el.innerHTML = renderSite(user);
    }

    async function loadFeatureFlags() {
        const panel = document.getElementById('featureFlagsPanel');
        if (!panel) return;
        try {
            const r = await fetch('/api/feature-flags', { credentials: 'same-origin' });
            const d = await r.json();
            const flags = d.flags || {};
            panel.innerHTML = Object.entries(flags).map(([k, v]) =>
                `<label class="ml-check" style="display:block;margin:8px 0">
                    <input type="checkbox" ${v ? 'checked' : ''} onchange="AdminPanel.toggleFlag('${k}', this.checked)"> ${esc(k)}
                </label>`
            ).join('');
        } catch (_) {
            panel.innerHTML = '<p class="muted">Ошибка загрузки</p>';
        }
    }

    async function toggleFlag(name, value) {
        await fetch('/api/admin/feature-flags', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, value }),
        });
    }

    async function loadData(user) {
        const tasks = [];
        if (canManageUsers(user)) {
            tasks.push(fetch('/api/admin/users', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : { users: [] }).then((d) => {
                users = d.users || [];
                roleCounts = d.role_counts || {};
                privilegesCatalog = d.privileges_catalog || [];
            }));
            tasks.push(fetch('/api/subscription/plans', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : { plans: [] }).then((d) => { plans = d.plans || []; }));
        }
        if (canManageSite(user)) {
            tasks.push(fetch('/api/admin/site', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : null).then((d) => { siteInfo = d; }));
        }
        tasks.push(fetch('/api/agents', { credentials: 'same-origin' }).then((r) => r.ok ? r.json() : { agents: [] }).then((d) => { agents = d.agents || []; }));
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

    function toggleUser(userId) {
        expandedUserId = expandedUserId === userId ? null : userId;
        renderContent();
    }

    function setUserFilter(q) {
        userFilter = q || '';
        renderContent();
    }

    function setRoleFilter(r) {
        roleFilter = r || '';
        renderContent();
    }

    async function saveUser(userId, mode) {
        const user = global.Auth?.getUser();
        const body = {};
        if (mode === 'role') {
            body.role = document.getElementById(`role-${userId}`)?.value;
        } else if (mode === 'balance') {
            body.balance_delta = parseInt(document.getElementById(`bal-${userId}`)?.value || '0', 10);
            if (!body.balance_delta) return;
        } else if (mode === 'set_balance') {
            body.set_balance = parseInt(document.getElementById(`setbal-${userId}`)?.value || '0', 10);
            if (Number.isNaN(body.set_balance)) return;
        } else if (mode === 'tier') {
            body.tier = document.getElementById(`tier-${userId}`)?.value;
        } else if (mode === 'profile') {
            body.name = document.getElementById(`name-${userId}`)?.value?.trim();
            body.default_view = document.getElementById(`view-${userId}`)?.value;
            body.theme = document.getElementById(`theme-${userId}`)?.value;
            body.admin_notes = document.getElementById(`notes-${userId}`)?.value || '';
            body.disabled = document.getElementById(`disabled-${userId}`)?.checked === true;
        } else if (mode === 'privileges') {
            body.privileges = [...document.querySelectorAll(`input[data-uid="${userId}"][data-priv]:checked`)]
                .map((el) => el.dataset.priv);
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

    async function revokeSessions(userId) {
        if (!confirm('Завершить все сессии пользователя?')) return;
        try {
            const r = await fetch(`/api/admin/users/${userId}/revoke-sessions`, {
                method: 'POST', credentials: 'same-origin',
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await loadData(global.Auth?.getUser());
            renderContent();
            if (window.UIEnhancements) UIEnhancements.toast(`Завершено сессий: ${d.revoked || 0}`, 'success');
        } catch (err) {
            if (window.UIEnhancements) UIEnhancements.toast(err.message, 'error');
        }
    }

    async function resetPassword(userId) {
        const pw = document.getElementById(`pw-${userId}`)?.value || '';
        if (pw.length < 6) {
            if (window.UIEnhancements) UIEnhancements.toast('Пароль минимум 6 символов', 'warn');
            return;
        }
        if (!confirm('Сбросить пароль? Все сессии будут завершены.')) return;
        try {
            const r = await fetch(`/api/admin/users/${userId}/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ password: pw }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            document.getElementById(`pw-${userId}`).value = '';
            if (window.UIEnhancements) UIEnhancements.toast('Пароль обновлён', 'success');
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
            const d = global.UICore?.parseApiJson
                ? await UICore.parseApiJson(r, 'Настройки сайта')
                : await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            siteInfo = d.config ? d : { ...siteInfo, config: d.config || d };
            if (window.UIEnhancements) UIEnhancements.toast('Настройки сайта сохранены', 'success');
            renderContent();
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
        toggleFlag,
        toggleUser,
        setUserFilter,
        setRoleFilter,
        revokeSessions,
        resetPassword,
    };
})(window);
