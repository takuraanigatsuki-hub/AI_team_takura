/**
 * UI Core — empty states, TaskCard, header context, mobile nav, role modes
 */
(function (global) {
    const STATUS_LABELS = {
        submitted: 'отправлена',
        queued: 'в очереди',
        triaging: 'проверка ролей',
        in_progress: 'выполняется',
        awaiting_approval: '⏳ на проверке',
        revision_requested: '✎ правки',
        cancelled: 'отменено',
        completed: '✓ готово',
        failed: 'ошибка',
    };
    const PRIO_LABELS = { urgent: '🔴', high: '🟠', medium: '🟡', low: '⚪' };

    function inferTaskKind(taskText) {
        const t = (taskText || '').toLowerCase();
        if (/презентац|powerpoint|pptx|pitch|слайд|keynote/.test(t)) return 'presentation';
        if (/3d|3д|three\.?js|glb|gltf|webgl/.test(t)) return 'model_3d';
        if (/таблиц|excel|spreadsheet|csv/.test(t)) return 'table';
        if (/сайт|landing|website|лендинг|web page/.test(t)) return 'site';
        return '';
    }

    function taskDeliveryLinks(t) {
        const kind = t.task_kind || t.artifact_type || inferTaskKind(t.task);
        const links = [];
        const preview = t.preview_url && !String(t.preview_url).includes('/api/sites/latest')
            ? t.preview_url : '';
        if (preview) {
            const label = kind === 'presentation' ? '📽️ Слайды' : kind === 'model_3d' ? '🧊 3D Preview' : '👁 Preview';
            links.push({ href: preview, label });
        }
        let download = t.download_url || '';
        if (!download && kind === 'presentation' && t.artifact_id) {
            download = `/api/projects/${t.artifact_id}/file/presentation.pptx`;
        }
        if (download) {
            const dlLabel = kind === 'presentation' ? '📥 PowerPoint (.pptx)'
                : kind === 'table' ? '📥 Excel (.xlsx)' : '📥 Скачать файл';
            links.push({ href: download, label: dlLabel });
        }
        if (t.status === 'awaiting_approval' && (kind === 'site' || kind === 'ui')) {
            links.push({ href: t.site_url || '/api/sites/latest', label: '🌐 Сайт' });
        }
        return links.map((l) =>
            `<a href="${esc(l.href)}" target="_blank" rel="noopener" class="task-link-btn">${l.label}</a>`
        ).join('');
    }

    let contextState = {
        online: false,
        reconnecting: false,
        agentsWorking: 0,
        taskStats: {},
        presence: '',
    };

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
        }[c]));
    }

    function getUiMode(user) {
        if (!user) return 'guest';
        if (global.Auth?.canAccessAdmin?.(user)) return 'admin';
        if (user.role === 'support' || (user.can_manage_tickets && user.role === 'support')) return 'support';
        if (user.role === 'investor') return 'investor';
        return 'member';
    }

    function emptyState(opts = {}) {
        const {
            icon = '📋',
            title = 'Пусто',
            text = '',
            primaryLabel = '',
            primaryOnclick = '',
            secondaryLabel = '',
            secondaryHref = '',
        } = opts;
        return `<div class="ui-empty tasks-empty">
            <div class="ui-empty-icon">${icon}</div>
            <h3>${esc(title)}</h3>
            ${text ? `<p class="muted">${esc(text)}</p>` : ''}
            <div class="ui-empty-actions">
                ${primaryLabel ? `<button type="button" class="btn-primary btn-sm" onclick="${primaryOnclick}">${esc(primaryLabel)}</button>` : ''}
                ${secondaryLabel ? `<a href="${esc(secondaryHref)}" class="btn-secondary btn-sm">${esc(secondaryLabel)}</a>` : ''}
            </div>
        </div>`;
    }

    function loadingState(text = 'Загрузка…', opts = {}) {
        if (opts.compact) {
            return `<div class="ui-loading-inline" aria-busy="true" role="status">
                <span class="ui-loading-ring sm" aria-hidden="true"></span>
                <span class="muted">${esc(text)}</span>
            </div>`;
        }
        return `<div class="ui-empty ui-loading" aria-busy="true" role="status">
            <div class="ui-loading-ring" aria-hidden="true"></div>
            <p class="muted">${esc(text)}</p>
        </div>`;
    }

    function errorState(message, opts = {}) {
        const { title = 'Ошибка', icon = '⚠️', retryOnclick = '' } = opts;
        return `<div class="ui-empty ui-error">
            <div class="ui-empty-icon">${icon}</div>
            <h3>${esc(title)}</h3>
            <p class="muted">${esc(message)}</p>
            ${retryOnclick ? `<div class="ui-empty-actions"><button type="button" class="btn-secondary btn-sm" onclick="${retryOnclick}">Повторить</button></div>` : ''}
        </div>`;
    }

    function authRequiredState(opts = {}) {
        return emptyState({
            icon: '🔐',
            title: opts.title || 'Нужен вход',
            text: opts.text || 'Войдите, чтобы сохранить данные между визитами.',
            secondaryLabel: 'Войти',
            secondaryHref: '/?auth=login',
            primaryLabel: opts.primaryLabel || '',
            primaryOnclick: opts.primaryOnclick || '',
            ...opts,
        });
    }

    function inlineEmpty(text) {
        return `<p class="ui-inline-empty muted">${esc(text)}</p>`;
    }

    /** Matches static placeholders in index.html */
    function staticLoading(text = 'Загрузка…', compact = true) {
        const ph = compact ? 'ui-ph ui-ph-compact' : 'ui-ph';
        return `<div class="ui-loading-inline ${ph}" aria-busy="true" role="status">
            <span class="ui-loading-ring sm" aria-hidden="true"></span>
            <span class="muted">${esc(text)}</span>
        </div>`;
    }

    function formatTime(iso) {
        if (!iso || !global.formatTime) return '';
        return global.formatTime(iso);
    }

    /**
     * @param {object} t — task
     * @param {object} opts — { compact, showComments, formatTimeFn }
     */
    function renderTaskCard(t, opts = {}) {
        const compact = opts.compact === true;
        const showComments = opts.showComments !== false;
        const fmt = opts.formatTimeFn || formatTime;
        const agent = t.agent_emoji && t.agent_name
            ? `${t.agent_emoji} ${t.agent_name}` : (t.target === 'all' ? '👥 Команда' : t.target || '—');
        const time = t.completed_at || t.awaiting_since || t.started_at || t.created_at;
        const timeStr = time ? fmt(time) : '';
        const prio = t.priority || 'medium';
        const prioBadge = PRIO_LABELS[prio] || '';
        const tid = esc(t.id);
        const deliveryLinks = taskDeliveryLinks(t);
        const approvalBtns = t.status === 'awaiting_approval' ? `
            <div class="task-approval">
                <button type="button" class="btn-primary btn-sm" onclick="approveTask('${tid}')">✓ Принять</button>
                <button type="button" class="btn-secondary btn-sm" onclick="requestTaskRevision('${tid}')">✎ Правки</button>
            </div>` : '';
        const response = t.response && !compact
            ? `<div class="task-response">${esc(t.response.slice(0, 500))}${t.response.length > 500 ? '…' : ''}</div>`
            : '';
        const actions = compact ? '' : `
            <div class="task-card-actions">
                ${deliveryLinks}
                <button type="button" class="task-act-btn" onclick="copyTaskById('${tid}')" title="Копировать">📋</button>
                <button type="button" class="task-act-btn" onclick="rerunTaskById('${tid}')" title="Повторить">↻</button>
            </div>`;
        const comments = showComments && !compact ? `
            <div class="task-comments" id="task-comments-${tid}">
                ${(t.comments || []).map((c) =>
                    `<div class="task-comment"><strong>${esc(c.user_name)}</strong>: ${esc(c.text)} <small>${fmt(c.created_at)}</small></div>`
                ).join('')}
            </div>
            <div class="task-comment-form">
                <input type="text" class="design-input task-comment-input" placeholder="Комментарий…" id="task-comment-input-${tid}"
                    onkeydown="if(event.key==='Enter')addTaskComment('${tid}')">
                <button type="button" class="btn-secondary btn-xs" onclick="addTaskComment('${tid}')">💬</button>
            </div>` : '';

        return `<article class="task-card ${t.status} priority-${prio}" data-task-id="${tid}">
            <div class="task-card-top">
                <span class="task-status-pill ${t.status}">${STATUS_LABELS[t.status] || t.status}</span>
                <span class="task-prio" title="Приоритет: ${prio}">${prioBadge}</span>
                <span class="task-meta">${esc(agent)} · ${timeStr}</span>
            </div>
            <p class="task-card-text">${esc(t.task || '')}</p>
            ${response}${actions}${approvalBtns}${comments}
        </article>`;
    }

    function renderKanbanCard(t) {
        const prio = t.priority || 'medium';
        const tid = esc(t.id || '');
        const PRIO = PRIO_LABELS;
        return `<div class="kb-card priority-${prio}" draggable="true"
             data-task-id="${tid}"
             ondragstart="KanbanUI.onDragStart(event)"
             ondragover="KanbanUI.onDragOver(event)"
             ondrop="KanbanUI.onDrop(event)">
            <div class="kb-head">
                <span class="kb-prio" title="Сменить приоритет"
                      onclick="event.stopPropagation();KanbanUI.cyclePriority('${tid}','${prio}')">${PRIO[prio] || prio}</span>
            </div>
            <div class="kb-title" onclick="switchView('tasks')">${esc((t.text || t.task || '—').slice(0, 60))}</div>
            <div class="kb-meta">${t.agent_emoji || ''} ${esc(t.agent_name || t.agent_id || '')}</div>
        </div>`;
    }

    function updateHeaderContext(partial = {}) {
        Object.assign(contextState, partial);
        const el = document.getElementById('headerContextText');
        const dot = document.getElementById('headerContextDot');
        if (!el) return;

        const s = contextState.taskStats || {};
        const active = s.active ?? 0;
        const awaiting = s.awaiting_approval ?? 0;
        const total = s.total ?? 0;
        const working = contextState.agentsWorking ?? 0;

        let conn = 'Оффлайн';
        let dotCls = 'ctx-dot';
        if (contextState.reconnecting) {
            conn = 'Переподключение…';
            dotCls += ' reconnecting';
        } else if (contextState.online) {
            conn = 'Онлайн';
            dotCls += ' online';
        }
        if (dot) dot.className = dotCls;

        const parts = [conn];
        if (total > 0) parts.push(`<strong>${active}</strong> в работе`);
        if (awaiting > 0) parts.push(`<strong>${awaiting}</strong> на проверке`);
        else if (total > 0) parts.push(`${total} задач`);
        if (working > 0) parts.push(`${working} агентов`);
        if (contextState.presence) parts.push(contextState.presence);

        el.innerHTML = parts.join(' · ');
        updateMobileBadges(awaiting);
    }

    function updateMobileBadges(awaiting) {
        const badge = document.getElementById('mobileTabBadge');
        if (!badge) return;
        if (awaiting > 0) {
            badge.textContent = awaiting > 9 ? '9+' : String(awaiting);
            badge.style.display = 'grid';
        } else {
            badge.style.display = 'none';
        }
    }

    function setMobileTabActive(view) {
        document.querySelectorAll('.mobile-tab-bar .mtab').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
    }

    function bindMobileTabClicks(bar) {
        bar.querySelectorAll('.mtab[data-view]').forEach((btn) => {
            btn.onclick = () => {
                if (btn.dataset.view && global.switchView) global.switchView(btn.dataset.view);
            };
        });
        const more = bar.querySelector('#mobileTabMore');
        if (more) {
            more.onclick = () => {
                if (global.FeaturePack?.openCommandPalette) FeaturePack.openCommandPalette();
                else if (global.SidebarNav) SidebarNav.onNavClick('dashboard');
            };
        }
    }

    function renderMobileTabs(user) {
        const bar = document.getElementById('mobileTabBar');
        if (!bar) return;
        const mode = getUiMode(user);
        let tabs;
        if (mode === 'investor') {
            tabs = [
                { view: 'investor', icon: '💼', label: 'Investor' },
                { view: 'dashboard', icon: '📊', label: 'Hub' },
                { view: 'studio', icon: '🎮', label: '3D' },
                { view: 'profile', icon: '👤', label: 'Профиль' },
            ];
        } else {
            tabs = [
                { view: 'tasks', icon: '📋', label: 'Inbox', badge: true },
                { view: 'chat', icon: '💬', label: 'Чат' },
                { view: 'kanban', icon: '📌', label: 'Board' },
                { view: 'dashboard', icon: '📊', label: 'Hub' },
            ];
        }
        bar.innerHTML = tabs.map((t) =>
            `<button type="button" class="mtab" data-view="${t.view}"><span class="mtab-icon">${t.icon}</span>${t.label}${t.badge ? '<span class="mtab-badge" id="mobileTabBadge" style="display:none">0</span>' : ''}</button>`
        ).join('') + '<button type="button" class="mtab" id="mobileTabMore"><span class="mtab-icon">⌘</span>Ещё</button>';
        bindMobileTabClicks(bar);
    }

    function initMobileNav() {
        const bar = document.getElementById('mobileTabBar');
        if (!bar) return;
        document.body.classList.add('has-mobile-tabs');
        renderMobileTabs(global.Auth?.getUser?.());
    }

    function onAuthUpdated() {
        if (global.SidebarNav?.render) SidebarNav.render();
        renderMobileTabs(global.Auth?.getUser?.());
    }

    document.addEventListener('auth:updated', onAuthUpdated);

    /* ─── Activity stream (right panel) ─── */
    const ACTIVITY_MAX = 80;
    const activityItems = [];
    let activityOpen = false;

    function formatActivityTime(iso) {
        if (!iso) return 'сейчас';
        try {
            const d = new Date(iso);
            return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return '';
        }
    }

    function renderActivityFeed() {
        const feed = document.getElementById('activityFeed');
        if (!feed) return;
        if (!activityItems.length) {
            feed.innerHTML = `<li class="activity-empty">${emptyState({
                icon: '📡',
                title: 'Пока тихо',
                text: 'Здесь появятся задачи, деплои и сообщения команды.',
            })}</li>`;
            return;
        }
        feed.innerHTML = activityItems.map((item) => `
            <li class="activity-item activity-${esc(item.kind)}">
                <span class="activity-icon" aria-hidden="true">${item.icon}</span>
                <div class="activity-body">
                    <p class="activity-text">${esc(item.text)}</p>
                    <time class="activity-time">${formatActivityTime(item.at)}</time>
                </div>
            </li>`).join('');
    }

    function pushActivity(item) {
        activityItems.unshift({
            kind: item.kind || 'info',
            icon: item.icon || '•',
            text: String(item.text || '').slice(0, 240),
            at: item.at || new Date().toISOString(),
        });
        if (activityItems.length > ACTIVITY_MAX) activityItems.length = ACTIVITY_MAX;
        renderActivityFeed();
        const badge = document.getElementById('activityBadge');
        if (badge && !activityOpen) {
            const n = Math.min(9, activityItems.length);
            badge.textContent = n > 9 ? '9+' : String(n);
            badge.style.display = 'grid';
        }
    }

    function setActivityOpen(open) {
        activityOpen = open;
        document.body.classList.toggle('activity-open', open);
        const panel = document.getElementById('activityPanel');
        if (panel) {
            panel.classList.toggle('open', open);
            panel.setAttribute('aria-hidden', open ? 'false' : 'true');
        }
        const toggle = document.getElementById('activityToggle');
        if (toggle) toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
            const badge = document.getElementById('activityBadge');
            if (badge) badge.style.display = 'none';
            try { localStorage.setItem('ai-team-activity-open', '1'); } catch (_) {}
        } else {
            try { localStorage.removeItem('ai-team-activity-open'); } catch (_) {}
        }
    }

    function toggleActivityPanel() {
        setActivityOpen(!activityOpen);
    }

    function initActivityPanel() {
        if (document.getElementById('activityPanel')) return;
        const panel = document.createElement('aside');
        panel.id = 'activityPanel';
        panel.className = 'activity-panel';
        panel.setAttribute('aria-label', 'Лента событий');
        panel.setAttribute('aria-hidden', 'true');
        panel.innerHTML = `
            <div class="activity-panel-head">
                <h2>📡 Лента</h2>
                <button type="button" class="activity-close hdr-icon" id="activityClose" aria-label="Закрыть ленту">×</button>
            </div>
            <ul class="activity-feed" id="activityFeed"></ul>`;
        document.body.appendChild(panel);
        document.getElementById('activityClose')?.addEventListener('click', () => setActivityOpen(false));
        document.getElementById('activityToggle')?.addEventListener('click', toggleActivityPanel);
        renderActivityFeed();
        try {
            if (localStorage.getItem('ai-team-activity-open') === '1') setActivityOpen(true);
        } catch (_) {}
    }

    function wsMessageToActivity(data) {
        if (!data || !data.type) return;
        const msg = String(data.message || data.task || '').replace(/[*#_`]/g, '').slice(0, 160);
        const map = {
            task_awaiting_approval: { icon: '⏳', kind: 'task', text: msg || 'Задача ждёт подтверждения' },
            task_approved: { icon: '✓', kind: 'task', text: msg || 'Задача принята' },
            task_revision: { icon: '✎', kind: 'task', text: msg || 'Отправлено на доработку' },
            artifact_created: { icon: '📦', kind: 'artifact', text: msg || data.title || 'Новый артефакт' },
            deploy_ready: { icon: '🚀', kind: 'deploy', text: msg || 'Deploy готов' },
            site_ready: { icon: '🌐', kind: 'site', text: msg || 'Сайт готов' },
            pr_ready: { icon: '🔗', kind: 'pr', text: msg || 'PR / commit готов' },
            pipeline_update: data.pipeline?.finished_at
                ? { icon: '⚡', kind: 'pipeline', text: 'Pipeline завершён' } : null,
            system: msg ? { icon: 'ℹ️', kind: 'system', text: msg } : null,
        };
        const item = map[data.type];
        if (item) pushActivity(item);
    }

    /* ─── Accessibility + onboarding ─── */
    function announceLive(text) {
        const el = document.getElementById('ariaLiveStatus');
        if (!el || !text) return;
        el.textContent = '';
        requestAnimationFrame(() => { el.textContent = text; });
    }

    function initGuestOnboarding() {
        if (localStorage.getItem('ai-team-onboard-v1')) return;
        const host = document.getElementById('tasksView');
        if (!host || host.querySelector('.onboard-banner')) return;
        const bar = document.createElement('div');
        bar.className = 'onboard-banner';
        bar.setAttribute('role', 'note');
        bar.innerHTML = `
            <div class="onboard-banner-text">
                <strong>Добро пожаловать в Inbox</strong>
                <span class="muted">Отправьте задачу в чат — она появится здесь. Примите или отправьте на правки одной кнопкой.</span>
            </div>
            <button type="button" class="btn-secondary btn-sm" onclick="UICore.dismissOnboarding()">Понятно</button>`;
        const header = host.querySelector('.view-header') || host.firstElementChild;
        if (header?.nextSibling) host.insertBefore(bar, header.nextSibling);
        else host.prepend(bar);
    }

    function dismissOnboarding() {
        try { localStorage.setItem('ai-team-onboard-v1', '1'); } catch (_) {}
        document.querySelector('.onboard-banner')?.remove();
    }

    function dismissAwaitingCoachmark() {
        try { localStorage.setItem('ai-team-awaiting-tip-v1', '1'); } catch (_) {}
        document.querySelectorAll('.ui-coachmark').forEach((el) => el.remove());
        document.querySelectorAll('.ui-coach-target').forEach((el) => el.classList.remove('ui-coach-target'));
        document.getElementById('awaitingChip')?.classList.remove('coach-pulse');
    }

    function checkAwaitingCoachmark(awaitingCount) {
        if (!awaitingCount || localStorage.getItem('ai-team-awaiting-tip-v1')) return;
        const tasksView = document.getElementById('tasksView');
        const onInbox = tasksView && !tasksView.classList.contains('hidden');
        const card = document.querySelector('.task-card.awaiting_approval');
        if (!onInbox || !card) {
            document.getElementById('awaitingChip')?.classList.add('coach-pulse');
            return;
        }
        if (card.querySelector('.ui-coachmark')) return;
        card.classList.add('ui-coach-target');
        const tip = document.createElement('div');
        tip.className = 'ui-coachmark';
        tip.setAttribute('role', 'note');
        tip.innerHTML = `
            <strong>⏳ Задача ждёт решения</strong>
            <p>Нажмите <em>✓ Принять</em> или <em>✎ Правки</em> — команда продолжит работу</p>
            <button type="button" class="btn-primary btn-sm" onclick="UICore.dismissAwaitingCoachmark()">Понятно</button>`;
        card.appendChild(tip);
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        announceLive('Задача ждёт вашего решения в Inbox');
    }

    global.UICore = {
        esc,
        emptyState,
        loadingState,
        errorState,
        authRequiredState,
        inlineEmpty,
        staticLoading,
        renderTaskCard,
        renderKanbanCard,
        getUiMode,
        updateHeaderContext,
        setMobileTabActive,
        initMobileNav,
        renderMobileTabs,
        initActivityPanel,
        initGuestOnboarding,
        toggleActivityPanel,
        pushActivity,
        announceLive,
        dismissOnboarding,
        dismissAwaitingCoachmark,
        checkAwaitingCoachmark,
        updateMobileBadges,
        STATUS_LABELS,
        PRIO_LABELS,
        ActivityStream: { push: pushActivity, onWsMessage: wsMessageToActivity },
    };
})(window);
