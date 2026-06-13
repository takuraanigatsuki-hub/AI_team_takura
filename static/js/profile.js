/**
 * Личный кабинет пользователя — профиль, настройки, безопасность, активность
 */
(function (global) {
    let activeTab = 'overview';
    let stats = null;
    let plans = null;
    let actionCosts = null;

    const VIEW_LABELS = {
        tasks: '📋 Inbox',
        dashboard: '📊 Dashboard',
        chat: '💬 Рабочий чат',
        kanban: '📌 Kanban',
        studio: '🎮 3D Студия',
        design: '🎨 Design',
        'sonya-studio': '✨ Studio',
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
        return {
            owner: 'Владелец',
            admin: 'Админ',
            tech_admin: 'Тех. админ',
            support: 'Поддержка',
            member: 'Пользователь',
        }[role] || role;
    }

    function fmtDateTime(iso) {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleString('ru', {
                day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            });
        } catch (_) {
            return iso.slice(0, 16).replace('T', ' ');
        }
    }

    function statusLabel(st) {
        return {
            completed: '✅ Готово',
            in_progress: '⏳ В работе',
            queued: '📋 В очереди',
            submitted: '📤 Отправлено',
            failed: '❌ Ошибка',
        }[st] || st;
    }

    function statusClass(st) {
        return {
            completed: 'ok',
            in_progress: 'active',
            queued: 'pending',
            submitted: 'pending',
            failed: 'err',
        }[st] || '';
    }

    function kpiCard(icon, value, label, hint) {
        return `
        <article class="pf-kpi">
            <span class="pf-kpi-icon">${icon}</span>
            <div class="pf-kpi-body">
                <div class="pf-kpi-val">${esc(value)}</div>
                <div class="pf-kpi-label">${esc(label)}</div>
                ${hint ? `<div class="pf-kpi-hint">${esc(hint)}</div>` : ''}
            </div>
        </article>`;
    }

    function progressBar(pct, label) {
        const p = Math.min(100, Math.max(0, Number(pct) || 0));
        return `
        <div class="pf-progress">
            <div class="pf-progress-head"><span>${esc(label)}</span><strong>${p}%</strong></div>
            <div class="pf-progress-track"><div class="pf-progress-fill" style="width:${p}%"></div></div>
        </div>`;
    }

    function renderTimeline(tasks) {
        if (!tasks?.length) {
            return '<p class="muted pf-empty">Задач пока нет — отправьте первую в рабочем чате.</p>';
        }
        return `<ul class="pf-timeline">${tasks.map((t) => `
            <li class="pf-timeline-item ${statusClass(t.status)}">
                <div class="pf-timeline-dot"></div>
                <div class="pf-timeline-body">
                    <div class="pf-timeline-top">
                        <span class="pf-timeline-status">${statusLabel(t.status)}</span>
                        <time class="muted">${fmtDateTime(t.completed_at || t.created_at)}</time>
                    </div>
                    <p class="pf-timeline-text">${esc(t.task)}</p>
                    ${t.agent_name ? `<span class="pf-timeline-agent">${esc(t.agent_emoji || '🤖')} ${esc(t.agent_name)}</span>` : ''}
                </div>
            </li>`).join('')}</ul>`;
    }

    function renderOverview(user) {
        const s = stats || {};
        const sub = user.subscription || {};
        const bal = sub.balance_display ?? sub.balance ?? '0';
        const tier = `${sub.tier_emoji || ''} ${sub.tier_name || 'Free'}`.trim();
        const roleBadge = global.Auth?.roleBadgeHtml
            ? global.Auth.roleBadgeHtml(user)
            : `<span class="role-badge role-user">${roleLabel(user.role)}</span>`;

        return `
        <div class="pf-overview">
            <header class="pf-hero">
                <div class="pf-hero-left">
                    <div class="profile-avatar pf-hero-avatar">${esc((user.name || user.email || '?')[0]).toUpperCase()}</div>
                    <div>
                        <p class="pf-hero-greet">Добро пожаловать,</p>
                        <h2 class="pf-hero-name">${esc(user.name || 'Пользователь')}</h2>
                        <p class="muted pf-hero-email">${esc(user.email)}</p>
                        <div class="pf-hero-badges">${roleBadge}
                            <span class="ss-badge">${esc(tier)}</span>
                            <span class="ss-badge">ур. ${user.access_level || sub.level || 1}</span>
                        </div>
                    </div>
                </div>
                <div class="pf-hero-stats">
                    <div class="pf-hero-stat"><span class="pf-hero-stat-val">${esc(bal)}</span><span class="muted">кредитов</span></div>
                    <div class="pf-hero-stat"><span class="pf-hero-stat-val">${s.days_member ?? 0}</span><span class="muted">дней в команде</span></div>
                    <div class="pf-hero-stat"><span class="pf-hero-stat-val">${s.active_sessions ?? 1}</span><span class="muted">сессий</span></div>
                </div>
            </header>

            <div class="pf-kpi-grid">
                ${kpiCard('📋', s.tasks_total ?? 0, 'Задач всего', `+${s.tasks_week ?? 0} за 7 дней`)}
                ${kpiCard('✅', s.tasks_completed ?? 0, 'Выполнено', `${s.success_rate ?? 0}% успех`)}
                ${kpiCard('⏳', s.tasks_active ?? 0, 'В работе', `${s.tasks_failed ?? 0} ошибок`)}
                ${kpiCard('🤖', s.llm_requests ?? 0, 'AI запросов', `${((s.llm_tokens_in || 0) + (s.llm_tokens_out || 0)).toLocaleString('ru')} токенов`)}
                ${kpiCard('✨', s.sonya_projects ?? 0, 'Studio', `${s.sonya_published ?? 0} опубл.`)}
                ${kpiCard('📦', s.artifacts_total ?? 0, 'Артефакты', `${s.agents_total ?? 0} агентов`)}
            </div>

            <div class="pf-split">
                <section class="pf-panel">
                    <div class="pf-panel-head"><h3>📈 Последняя активность</h3>
                        <button type="button" class="btn-secondary btn-sm" onclick="ProfileCabinet.switchTab('activity')">Все →</button>
                    </div>
                    ${renderTimeline(s.recent_tasks)}
                </section>
                <section class="pf-panel">
                    <div class="pf-panel-head"><h3>💎 Аккаунт и доступ</h3></div>
                    ${progressBar(s.success_rate, 'Успешность задач')}
                    ${progressBar(sub.unlimited ? 100 : Math.min(100, ((s.views_unlocked_count || 0) / 12) * 100), 'Открыто вкладок')}
                    <ul class="profile-meta-list pf-account-list">
                        <li><span>Тариф</span><strong>${esc(tier)}</strong></li>
                        <li><span>Баланс</span><strong>${esc(bal)} кр.</strong></li>
                        <li><span>Brief проекта</span><strong>${s.has_project_brief ? '✓ задан' : '— не задан'}</strong></li>
                        <li><span>Цели / ограничения</span><strong>${s.project_goals_count ?? 0} / ${s.project_constraints_count ?? 0}</strong></li>
                        <li><span>Участник с</span><strong>${fmtDate(s.member_since || user.created_at)}</strong></li>
                        <li><span>Настройка</span><strong>${user.setup_complete ? fmtDate(s.setup_at || user.setup_at) : 'не пройдена'}</strong></li>
                    </ul>
                </section>
            </div>

            <div class="pf-split">
                <section class="pf-panel">
                    <div class="pf-panel-head"><h3>✨ Studio проекты</h3>
                        <button type="button" class="btn-secondary btn-sm" onclick="switchView('sonya-studio')">Открыть</button>
                    </div>
                    ${(s.recent_projects || []).length ? `<ul class="pf-mini-list">${(s.recent_projects || []).map((p) => `
                        <li><span>${esc(p.title || 'Без названия')}</span>
                            <span class="pf-mini-meta">${esc(p.status || 'draft')} · ${fmtDate(p.updated_at)}</span></li>`).join('')}</ul>`
                        : '<p class="muted pf-empty">Studio проектов пока нет.</p>'}
                </section>
                <section class="pf-panel">
                    <div class="pf-panel-head"><h3>🧠 AI & команда</h3></div>
                    <ul class="profile-meta-list">
                        <li><span>LLM стоимость</span><strong>~$${s.llm_cost_usd ?? 0} · ${s.llm_cost_rub ?? 0} ₽</strong></li>
                        <li><span>Figma паттерны</span><strong>${s.figma_patterns ?? 0} изучено · ${s.figma_portfolio ?? 0} в портфолио</strong></li>
                        <li><span>Агенты</span><strong>${s.agents_busy ?? 0} занято · ${s.agents_total ?? 0} всего</strong></li>
                        <li><span>ID аккаунта</span><strong class="pf-mono">${esc(user.id)}</strong></li>
                        <li><span>Обновлён</span><strong>${fmtDateTime(s.updated_at || user.updated_at)}</strong></li>
                    </ul>
                    ${(s.top_agents || []).length ? `
                    <p class="pf-sub-label muted">Топ агентов по задачам</p>
                    <div class="pf-chips">${(s.top_agents || []).map((a) =>
                        `<span class="pf-chip">${esc(a.id)} · ${a.count}</span>`).join('')}</div>` : ''}
                </section>
            </div>

            <div class="profile-quick-links pf-quick-bar">
                <button type="button" class="btn-primary btn-sm" onclick="switchView('chat')">💬 Чат</button>
                <button type="button" class="btn-secondary btn-sm" onclick="switchView('studio')">🎮 3D</button>
                <button type="button" class="btn-secondary btn-sm" onclick="switchView('tasks')">📋 Задачи</button>
                <button type="button" class="btn-secondary btn-sm" onclick="switchView('dashboard')">📊 Dashboard</button>
                ${canAdmin(user) ? '<button type="button" class="btn-secondary btn-sm" onclick="switchView(\'admin\')">🛡 Admin</button>' : ''}
            </div>
        </div>`;
    }

    function canAccessView(user, view) {
        if (view === 'investor') {
            return global.Auth?.canViewInvestorPortal?.(user) || false;
        }
        if (user?.role === 'investor' || user?.is_investor) {
            return ['investor', 'profile', 'studio', 'dashboard'].includes(view);
        }
        if (['learning', 'design', 'agent-learning'].includes(view)) {
            if (global.Auth?.canViewAgentLearning) return Auth.canViewAgentLearning(user);
            return user?.role === 'owner' || user?.role === 'admin' || user?.role === 'tech_admin';
        }
        const sub = user?.subscription;
        if (!sub) return true;
        if (sub.unlimited || user.is_owner) return true;
        return (sub.views_unlocked || []).includes(view);
    }

    async function loadPlans() {
        try {
            const r = await fetch('/api/subscription/plans', { credentials: 'same-origin' });
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

    function canAdmin(user) {
        if (!user) return false;
        if (user.is_owner) return true;
        const p = user.privileges || [];
        return p.includes('admin') || p.includes('manage_users') || p.includes('manage_settings');
    }

    function renderTabs() {
        const nav = document.getElementById('profileTabNav');
        if (!nav) return;
        const user = global.Auth?.getUser();
        const tabs = [
            { id: 'overview', label: '📊 Обзор' },
            { id: 'profile', label: '👤 Профиль' },
            { id: 'subscription', label: '💎 Подписка' },
            { id: 'settings', label: '⚙️ Настройки' },
            { id: 'workspaces', label: '🏢 Workspaces', show: true },
            { id: 'security', label: '🔒 Безопасность' },
            { id: 'activity', label: '📈 Активность' },
        ];
        if (canAdmin(user)) {
            tabs.push({ id: 'admin-link', label: '🛡 Admin-панель' });
        }
        nav.innerHTML = tabs.map((t) => `
            <button type="button" class="profile-tab ${t.id === activeTab ? 'active' : ''}"
                data-tab="${t.id}" onclick="${t.id === 'admin-link' ? "switchView('admin')" : `ProfileCabinet.switchTab('${t.id}')`}">${t.label}</button>`).join('');
    }

    function renderContent() {
        const el = document.getElementById('profileTabContent');
        const user = global.Auth?.getUser();
        if (!el) return;

        if (!user) {
            el.innerHTML = global.UICore ? UICore.authRequiredState({
                title: 'Личный кабинет',
                text: 'Войдите в аккаунт, чтобы открыть профиль и настройки',
            }) : `
                <div class="panel-empty">
                    <p>Войдите в аккаунт, чтобы открыть личный кабинет.</p>
                    <a href="/?auth=login" class="btn-primary btn-sm">Войти</a>
                </div>`;
            return;
        }

        if (activeTab === 'overview') {
            el.innerHTML = renderOverview(user);
            return;
        }

        if (activeTab === 'profile') {
            const s = stats || {};
            const sub = user.subscription || {};
            el.innerHTML = `
                <div class="profile-card pf-profile-card">
                    <div class="profile-avatar">${esc((user.name || user.email || '?')[0]).toUpperCase()}</div>
                    <div class="profile-head">
                        <h2>${esc(user.name || 'Пользователь')}</h2>
                        <p class="muted">${esc(user.email)}</p>
                        <div class="ss-badges" style="margin-top:10px">
                            ${global.Auth?.roleBadgeHtml ? global.Auth.roleBadgeHtml(user) : `<span class="ss-badge">${roleLabel(user.role)}</span>`}
                            <span class="ss-badge">${esc(sub.tier_emoji || '')} ${esc(sub.tier_name || 'Free')}</span>
                            <span class="ss-badge">ур. ${user.access_level || 1}</span>
                        </div>
                        <p class="muted profile-hint" style="margin-top:8px">Баланс: <strong>${esc(sub.balance_display ?? '—')}</strong> кредитов</p>
                    </div>
                </div>
                <div class="pf-split pf-split-3">
                    <section class="pf-panel pf-panel-compact">
                        <h3 class="pf-panel-title">Аккаунт</h3>
                        <ul class="profile-meta-list">
                            <li><span>ID</span><strong class="pf-mono">${esc(user.id)}</strong></li>
                            <li><span>Регистрация</span><strong>${fmtDate(user.created_at)}</strong></li>
                            <li><span>Дней в команде</span><strong>${s.days_member ?? '—'}</strong></li>
                            <li><span>Сессий</span><strong>${s.active_sessions ?? 1}</strong></li>
                            <li><span>Настройка</span><strong>${user.setup_complete ? '✓ пройдена' : 'не пройдена'}</strong></li>
                        </ul>
                    </section>
                    <section class="pf-panel pf-panel-compact">
                        <h3 class="pf-panel-title">Доступ</h3>
                        <ul class="profile-meta-list">
                            <li><span>Роль</span><strong>${esc(user.role_label || roleLabel(user.role))}</strong></li>
                            <li><span>Тариф</span><strong>${esc(sub.tier_name || 'Free')}</strong></li>
                            <li><span>Вкладок открыто</span><strong>${s.views_unlocked_count ?? (sub.views_unlocked || []).length}</strong></li>
                            <li><span>Стартовая вкладка</span><strong>${VIEW_LABELS[user.default_view] || user.default_view || 'Inbox'}</strong></li>
                            <li><span>Тема</span><strong>${user.theme === 'light' ? 'Светлая' : user.theme === 'auto' ? 'Системная' : 'Тёмная'}</strong></li>
                        </ul>
                    </section>
                    <section class="pf-panel pf-panel-compact">
                        <h3 class="pf-panel-title">Проект</h3>
                        <ul class="profile-meta-list">
                            <li><span>Brief</span><strong>${s.has_project_brief ? '✓' : '—'}</strong></li>
                            <li><span>Цели</span><strong>${s.project_goals_count ?? 0}</strong></li>
                            <li><span>Ограничения</span><strong>${s.project_constraints_count ?? 0}</strong></li>
                            <li><span>Память обновлена</span><strong>${fmtDate(s.memory_updated_at)}</strong></li>
                        </ul>
                    </section>
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
                    ${canUpgrade ? `<button type="button" class="btn-primary btn-sm" onclick="ProfileCabinet.upgrade('${p.id}')">${p.price_rub ? '💳 Оплатить' : 'Выбрать'}</button>` : ''}
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
            const viewOpts = Object.entries(VIEW_LABELS)
                .filter(([v]) => canAccessView(user, v))
                .map(([v, label]) =>
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

        if (activeTab === 'workspaces') {
            el.innerHTML = global.UICore ? UICore.loadingState('Загрузка workspaces…', { compact: true }) : '<div class="dash-loading">Загрузка workspaces…</div>';
            renderWorkspaces(user, el);
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
                <div class="pf-kpi-grid pf-kpi-grid-sm">
                    ${kpiCard('📋', s.tasks_total ?? '—', 'Всего', `${s.tasks_week ?? 0} за неделю`)}
                    ${kpiCard('✅', s.tasks_completed ?? '—', 'Выполнено', `${s.success_rate ?? 0}%`)}
                    ${kpiCard('⏳', s.tasks_active ?? '—', 'В работе', '')}
                    ${kpiCard('❌', s.tasks_failed ?? '—', 'Ошибки', '')}
                    ${kpiCard('✨', s.sonya_projects ?? '—', 'Studio', `${s.sonya_published ?? 0} pub`)}
                    ${kpiCard('📦', s.artifacts_total ?? '—', 'Артефакты', '')}
                </div>
                ${progressBar(s.success_rate, 'Успешность выполнения')}
                <section class="pf-panel" style="margin-top:16px">
                    <div class="pf-panel-head"><h3>🕐 Лента задач</h3></div>
                    ${renderTimeline(s.recent_tasks)}
                </section>
                <div class="pf-split" style="margin-top:16px">
                    <section class="pf-panel">
                        <h3 class="pf-panel-title">Studio проекты</h3>
                        ${(s.recent_projects || []).length ? `<ul class="pf-mini-list">${(s.recent_projects || []).map((p) => `
                            <li><span>${esc(p.title)}</span><span class="pf-mini-meta">${esc(p.status)}</span></li>`).join('')}</ul>`
                            : '<p class="muted pf-empty">Нет проектов</p>'}
                    </section>
                    <section class="pf-panel">
                        <h3 class="pf-panel-title">Артефакты команды</h3>
                        ${(s.recent_artifacts || []).length ? `<ul class="pf-mini-list">${(s.recent_artifacts || []).map((a) => `
                            <li><span>${esc(a.title || a.type)}</span><span class="pf-mini-meta">${esc(a.agent_name || a.agent_id)}</span></li>`).join('')}</ul>`
                            : '<p class="muted pf-empty">Нет артефактов</p>'}
                    </section>
                </div>
                <ul class="profile-meta-list" style="margin-top:16px">
                    <li><span>Участник с</span><strong>${fmtDate(s.member_since || user.created_at)}</strong></li>
                    <li><span>AI запросов</span><strong>${s.llm_requests ?? 0}</strong></li>
                    <li><span>Токены LLM</span><strong>${((s.llm_tokens_in || 0) + (s.llm_tokens_out || 0)).toLocaleString('ru')}</strong></li>
                    <li><span>Агенты</span><strong>${s.agents_busy ?? 0} занято · ${s.agents_total ?? 0} всего</strong></li>
                </ul>
                <div class="profile-quick-links" style="margin-top:16px">
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('studio')">🎮 3D</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('tasks')">📋 Задачи</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('sonya-studio')">✨ Studio</button>
                    <button type="button" class="btn-secondary btn-sm" onclick="switchView('dashboard')">📊 Dashboard</button>
                    ${canAdmin(user) ? '<button type="button" class="btn-primary btn-sm" onclick="switchView(\'admin\')">🛡 Admin</button>' : ''}
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
        else if (tab === 'workspaces') renderContent();
        else if (tab === 'overview' || tab === 'activity' || tab === 'profile') loadStats().then(renderContent);
        else renderContent();
    }

    async function renderWorkspaces(user, el) {
        try {
            const r = await fetch('/api/workspaces/active', { credentials: 'same-origin' });
            const d = r.ok ? await r.json() : { workspaces: [], active_id: '' };
            const list = d.workspaces || [];
            el.innerHTML = `
                <section class="pf-panel">
                    <div class="pf-panel-head">
                        <h3>🏢 Командные workspace</h3>
                        <button type="button" class="btn-primary btn-sm" onclick="Workspaces.showCreate();setTimeout(()=>ProfileCabinet.switchTab('workspaces'),800)">+ Создать</button>
                    </div>
                    <p class="muted">Изолированные комнаты для разных проектов или команд.</p>
                    ${list.length ? list.map((w) => `
                        <article class="ucard ucard-row" style="margin-top:10px">
                            <div><strong>${esc(w.name)}</strong><br><small class="muted">${esc(w.description || '')}</small></div>
                            <button type="button" class="btn-secondary btn-xs" onclick="Workspaces.switchTo('${esc(w.id)}')">${w.id === d.active_id ? '✓ Активен' : 'Выбрать'}</button>
                        </article>`).join('') : '<p class="muted">Пока нет workspace — создайте первый.</p>'}
                </section>`;
        } catch (_) {
            el.innerHTML = '<p class="muted">Ошибка загрузки</p>';
        }
    }

    async function upgrade(tier) {
        try {
            const flagsR = await fetch('/api/feature-flags', { credentials: 'same-origin' });
            const flagsD = flagsR.ok ? await flagsR.json() : {};
            const stripeR = await fetch('/api/billing/stripe/status', { credentials: 'same-origin' });
            const stripeD = stripeR.ok ? await stripeR.json() : {};
            if (flagsD.flags?.stripe_billing && stripeD.configured) {
                if (!confirm(`Оплатить тариф «${tier}» через Stripe?`)) return;
                const r = await fetch('/api/billing/stripe/checkout', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tier,
                        success_url: location.origin + '/app?view=profile',
                        cancel_url: location.origin + '/app?view=profile',
                    }),
                });
                const d = await r.json();
                if (!r.ok) throw new Error(d.detail || 'Stripe error');
                if (d.url) { location.href = d.url; return; }
            }
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'error');
            return;
        }
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
                    credentials: 'same-origin',
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
