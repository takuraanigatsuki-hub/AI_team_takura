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
        const previewLink = t.preview_url
            ? `<a href="${esc(t.preview_url)}" target="_blank" rel="noopener" class="task-link-btn">👁 Preview</a>` : '';
        const siteLink = t.status === 'awaiting_approval'
            ? `<a href="/api/sites/latest" target="_blank" rel="noopener" class="task-link-btn">🌐 Сайт</a>` : '';
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
                ${previewLink}${siteLink}
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

    function initMobileNav() {
        const bar = document.getElementById('mobileTabBar');
        if (!bar) return;
        document.body.classList.add('has-mobile-tabs');
        bar.querySelectorAll('.mtab[data-view]').forEach((btn) => {
            btn.addEventListener('click', () => {
                if (btn.dataset.view && global.switchView) global.switchView(btn.dataset.view);
            });
        });
        bar.querySelector('#mobileTabMore')?.addEventListener('click', () => {
            if (global.FeaturePack?.openCommandPalette) FeaturePack.openCommandPalette();
            else if (global.SidebarNav) SidebarNav.onNavClick('dashboard');
        });
    }

    function onAuthUpdated() {
        if (global.SidebarNav?.render) SidebarNav.render();
    }

    document.addEventListener('auth:updated', onAuthUpdated);

    global.UICore = {
        esc,
        emptyState,
        renderTaskCard,
        renderKanbanCard,
        getUiMode,
        updateHeaderContext,
        setMobileTabActive,
        initMobileNav,
        STATUS_LABELS,
        PRIO_LABELS,
    };
})(window);
