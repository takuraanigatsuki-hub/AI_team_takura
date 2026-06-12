/**
 * Личный кабинет пользователя — профиль, настройки, безопасность, активность
 */
(function (global) {
    let activeTab = 'profile';
    let stats = null;
    let plans = null;
    let actionCosts = null;

    const VIEW_LABELS = {
        studio: '🎮 3D Студия',
        dashboard: '📊 Dashboard',
        chat: '💬 Рабочий чат',
        kanban: '📌 Kanban',
        design: '🎨 Design',
        'sonya-studio': '✨ Studio',
        tasks: '📋 Задачи',
        projects: '📦 Проекты',
        sprint: '🏃 Sprint',
        timeline: '⏱ Timeline',
        profile: '👤 Кабинет',
    };

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' });
        } catch (_) {
            return iso.slice(0, 10);
        }
    }

    function roleLabel(role) {
        return { owner: 'Владелец', admin: 'Администратор', member: 'Участник' }[role] || role;
    }

    function canAccessView(user, view) {
        const sub = user?.subscription;
        if (!sub) return true;
        if (sub.unlimited || user.is_owner) return true;
        return (sub.views_unlocked || []).includes(view);
    }

    async function loadPlans() {
        try {
            const r = await fetch('/api/subscription/plans');
            if (r.ok) {
                const d = await r.json();
                plans = d.plans || [];
                actionCosts = d.action_costs || {};
            }
        } catch (_) {
            plans = null;
        }
    }

    async function loadStats() {
        try {
            const r = await fetch('/api/auth/profile/stats', { credentials: 'same-origin' });
            if (r.ok) stats = await r.json();
        } catch (_) {
            stats = null;
        }
    }

    function renderTabs() {
        const nav = document.getElementById('profileTabNav');
        if (!nav) return;
        const tabs = [
            { id: 'profile', label: '👤 Профиль' },
            { id: 'subscription', label: '💎 Подписка' },
            { id: 'settings', label: '⚙️ Настройки' },
            { id: 'security', label: '🔒 Безопасность' },
            { id: 'activity', label: '📈 Активность' },
        ];
        nav.innerHTML = tabs.map((t) => `
            <button type="button" class="profile-tab ${t.id === activeTab ? 'active' : ''}"
                data-tab="${t.id}" onclick="ProfileCabinet.switchTab('${t.id}')">${t.label}</button>`).join('');
    }

    function renderContent() {
        const el = document.getElementById('profileTabContent');
        const user = global.Auth?.getUser();
        if (!el) return;

        if (!user) {
            el.innerHTML = `
                <div class="panel-empty">
                    <p>Войдите в аккаунт, чтобы открыть личный кабинет.</p>
                    <a href="/?auth=login" class="btn-primary btn-sm">Войти</a>
                </div>`;
            return;
        }

        if (activeTab === 'profile') {
            el.innerHTML = `
                <div class="profile-card">
                    <div class="profile-avatar">${esc((user.name || user.email || '?')[0]).toUpperCase()}</div>
                    <div class="profile-head">
                        <h2>${esc(user.name || 'Пользователь')}</h2>
                        <p class="muted">${esc(user.email)}</p>
                        <div class="ss-badges" style="margin-top:10px">
                            <span class="ss-badge">${roleLabel(user.role)}</span>
                            <span class="ss-badge">${esc(user.subscription?.tier_emoji || '')} ${esc(user.subscription?.tier_name || 'Free')}</span>
                            <span class="ss-badge">ур. ${user.access_level || 1}</span>
                            ${user.is_owner ? '<span class="ss-badge warn">👑 Owner</span>' : ''}
                        </div>
                        <p class="muted profile-hint" style="margin-top:8px">Баланс: <strong>${esc(user.subscription?.balance_display ?? '—')}</strong> кредитов</p>
                    </div>
                </div>
                <form class="profile-form" id="profileNameForm" onsubmit="ProfileCabinet.saveProfile(event)">
                    <label class="sw-label">Отображаемое имя</label>
                    <input type="text" id="pfName" class="design-input" value="${esc(user.name)}" maxlength="80">
                    <label class="sw-label">Email</label>
                    <input type="email" class="design-input" value="${esc(user.email)}" disabled>
                    <p class="muted profile-hint">Email изменить нельзя — это ваш логин.</p>
                    <button type="submit" class="btn-primary btn-sm">Сохранить профиль</button>
                </form>`;
            return;
        }

        if (activeTab === 'subscription') {
            const sub = user.subscription || {};
            const curLevel = sub.level || 1;
            const plansHtml = (plans || []).filter((p) => !p.owner_only).map((p) => {
                const isCurrent = p.id === sub.tier;
                const canUpgrade = p.level > curLevel && !user.is_owner;
                return `
                <article class="sub-plan-card ${isCurrent ? 'current' : ''}">
                    <div class="sub-plan-head">${esc(p.emoji)} <strong>${esc(p.name_ru)}</strong> <span class="muted">ур. ${p.level}</span></div>
                    <p class="muted">${esc(p.description)}</p>
                    <p class="sub-plan-price">${p.price_rub ? `${p.price_rub} ₽/мес` : 'Бесплатно'}</p>
                    <p class="muted">+${p.monthly_credits} кр./мес</p>
                    ${isCurrent ? '<span class="ss-badge">текущий</span>' : ''}
                    ${canUpgrade ? `<button type="button" class="btn-primary btn-sm" onclick="ProfileCabinet.upgrade('${p.id}')">Выбрать</button>` : ''}
                </article>`;
            }).join('');

            const costsHtml = actionCosts ? Object.entries(actionCosts).map(([k, v]) =>
                `<li><span>${esc(k)}</span><strong>${v} кр.</strong></li>`).join('') : '';

            el.innerHTML = `
                <div class="sub-balance-card">
                    <div>
                        <small class="muted">Баланс кредитов</small>
                        <div class="sub-balance-value">${esc(sub.balance_display ?? '0')}</div>
                    </div>
                    <div>
                        <small class="muted">Тариф</small>
                        <div class="sub-tier-value">${esc(sub.tier_emoji || '')} ${esc(sub.tier_name || '')}</div>
                    </div>
                    <div>
                        <small class="muted">Уровень доступа</small>
                        <div class="sub-tier-value">${sub.level || 1} / 5</div>
                    </div>
                </div>
                ${user.is_owner ? '<p class="muted">👑 <strong>Owner</strong> — безлимитный баланс и все функции без ограничений.</p>' : ''}
                <h3 class="sub-section-title">Тарифные планы</h3>
                <div class="sub-plans-grid">${plansHtml || '<p class="muted">Загрузка…</p>'}</div>
                <h3 class="sub-section-title">Стоимость действий</h3>
                <ul class="profile-meta-list">${costsHtml}</ul>
                <h3 class="sub-section-title">Доступные вкладки</h3>
                <p class="muted">${(sub.views_unlocked || []).map((v) => VIEW_LABELS[v] || v).join(' · ') || '—'}</p>`;
            return;
        }

        if (activeTab === 'settings') {
            const viewOpts = Object.entries(VIEW_LABELS).map(([v, label]) =>
                `<option value="${v}" ${user.default_view === v ? 'selected' : ''}>${label}</option>`).join('');
            el.innerHTML = `
                <form class="profile-form" id="profileSettingsForm" onsubmit="ProfileCabinet.saveSettings(event)">
                    <label class="sw-label">Стартовая вкладка после входа</label>
                    <select id="pfDefaultView" class="design-input">${viewOpts}</select>
                    <label class="sw-label">Тема интерфейса</label>
                    <select id="pfTheme" class="design-input">
                        <option value="auto" ${user.theme === 'auto' ? 'selected' : ''}>Системная</option>
                        <option value="dark" ${(!user.theme || user.theme === 'dark') ? 'selected' : ''}>Тёмная</option>
                        <option value="light" ${user.theme === 'light' ? 'selected' : ''}>Светлая</option>
                    </select>
                    <label class="sw-label">Brief проекта (для команды агентов)</label>
                    <textarea id="pfGoal" class="design-input sw-textarea" rows="4"
                        placeholder="Кратко опишите ваш продукт или задачу…">${esc(user.project_goal || '')}</textarea>
                    <button type="submit" class="btn-primary btn-sm">Сохранить настройки</button>
                </form>`;
            return;
        }

        if (activeTab === 'security') {
            el.innerHTML = `
                <form class="profile-form" id="profilePasswordForm" onsubmit="ProfileCabinet.changePassword(event)">
                    <p class="muted">Смена пароля не разлогинивает вас на других устройствах.</p>
                    <label class="sw-label">Текущий пароль</label>
                    <input type="password" id="pfCurPass" class="design-input" required minlength="6" autocomplete="current-password">
                    <label class="sw-label">Новый пароль</label>
                    <input type="password" id="pfNewPass" class="design-input" required minlength="6" autocomplete="new-password">
                    <label class="sw-label">Повторите новый пароль</label>
                    <input type="password" id="pfNewPass2" class="design-input" required minlength="6" autocomplete="new-password">
                    <p class="lp-error hidden" id="pfPassError"></p>
                    <button type="submit" class="btn-primary btn-sm">Сменить пароль</button>
                </form>
                <div class="profile-danger-zone">
                    <h3>Выход из аккаунта</h3>
                    <p class="muted">Завершить сессию на этом устройстве.</p>
                    <button type="button" class="btn-secondary btn-sm" onclick="Auth.logout()">Выйти</button>
                </div>`;
            return;
        }

        if (activeTab === 'activity') {
            const s = stats || {};
            el.innerHTML = `
                <div class="profile-stats-grid">
                    <div class="stat-card"><span class="stat-num">${s.tasks_total ?? '—'}</span><span class="stat-label">Задач всего</span></div>
                    <div class="stat-card"><span class="stat-num">${s.tasks_completed ?? '—'}</span><span class="stat-label">Выполнено</span></div>
                    <div class="stat-card active"><span class="stat-num">${s.tasks_active ?? '—'}</span><span class="stat-label">В работе</span></div>
                    <div class="stat-card"><span class="stat-num">${s.sonya_projects ?? '—'}</span><span class="stat-label">Studio проектов</span></div>
                    <div class="stat-card"><span class="stat-num">${s.sonya_published ?? '—'}</span><span class="stat-label">Опубликовано</span></div>
                </div>
                <ul class="profile-meta-list">
                    <li><span>Участник с</span><strong>${fmtDate(s.member_since || user.created_at)}</strong></li>
                    <li><span>Настройка завершена</span><strong>${user.setup_complete ? fmtDate(s.setup_at || user.setup_at) : 'не пройдена'}</strong></li>
                    <li><span>Brief проекта</span><strong>${s.has_project_brief ? 'задан' : 'не задан'}</strong></li>
                </ul>
                <div class="profile-quick-links">
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('tasks')">📋 Задачи</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('sonya-studio')">✨ Studio</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('dashboard')">📊 Dashboard</button>
                </div>`;
        }
    }

    async function load() {
        renderTabs();
        await Promise.all([loadStats(), loadPlans()]);
        renderContent();
    }

    function switchTab(tab) {
        activeTab = tab;
        renderTabs();
        if (tab === 'subscription' && !plans) loadPlans().then(renderContent);
        else if (tab === 'activity') loadStats().then(renderContent);
        else renderContent();
    }

    async function upgrade(tier) {
        if (!confirm(`Перейти на тариф «${tier}»? (демо без оплаты)`)) return;
        try {
            const r = await fetch('/api/subscription/upgrade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ tier }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await global.Auth?.fetchMe();
            await loadStats();
            renderContent();
            if (window.UIEnhancements) UIEnhancements.toast(d.message || 'Тариф обновлён', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    async function saveProfile(e) {
        e.preventDefault();
        const name = document.getElementById('pfName')?.value?.trim();
        try {
            const r = await fetch('/api/auth/profile', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ name }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            await global.Auth?.fetchMe();
            renderContent();
            if (window.UIEnhancements) UIEnhancements.toast('Профиль сохранён', 'success');
        } catch (err) {
            alert(err.message);
        }
    }

    async function saveSettings(e) {
        e.preventDefault();
        const default_view = document.getElementById('pfDefaultView')?.value;
        const theme = document.getElementById('pfTheme')?.value;
        const project_goal = document.getElementById('pfGoal')?.value?.trim() || '';
        try {
            const r = await fetch('/api/auth/profile', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ default_view, theme, project_goal }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            if (project_goal) {
                await fetch('/api/project-memory', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brief: project_goal, goals: [], constraints: [] }),
                });
            }
            if (theme === 'light' || theme === 'dark') {
                localStorage.setItem('ai-team-room-theme', theme);
                if (window.applyTheme) applyTheme(theme);
            }
            await global.Auth?.fetchMe();
            renderContent();
            if (window.UIEnhancements) UIEnhancements.toast('Настройки сохранены', 'success');
        } catch (err) {
            alert(err.message);
        }
    }

    async function changePassword(e) {
        e.preventDefault();
        const errEl = document.getElementById('pfPassError');
        const cur = document.getElementById('pfCurPass')?.value || '';
        const n1 = document.getElementById('pfNewPass')?.value || '';
        const n2 = document.getElementById('pfNewPass2')?.value || '';
        if (n1 !== n2) {
            if (errEl) { errEl.textContent = 'Пароли не совпадают'; errEl.classList.remove('hidden'); }
            return;
        }
        try {
            const r = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ current_password: cur, new_password: n1 }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            document.getElementById('profilePasswordForm')?.reset();
            if (errEl) errEl.classList.add('hidden');
            if (window.UIEnhancements) UIEnhancements.toast('Пароль изменён', 'success');
        } catch (err) {
            if (errEl) { errEl.textContent = err.message; errEl.classList.remove('hidden'); }
        }
    }

    global.ProfileCabinet = {
        load,
        switchTab,
        saveProfile,
        saveSettings,
        changePassword,
        upgrade,
        canAccessView,
    };
})(window);
