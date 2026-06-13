/**
 * Support Panel — интерфейс для операторов поддержки
 */
(function (global) {
    let tickets = [];
    let counts = {};
    let activeId = null;
    let activeTicket = null;
    let userSummary = null;
    let filterStatus = '';

    const STATUS_LABELS = {
        open: 'Открыт',
        in_progress: 'В работе',
        resolved: 'Решён',
        closed: 'Закрыт',
    };

    function esc(s) {
        return String(s ?? '').replace(/[&<>"]/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
        }[c]));
    }

    function canAccess(user) {
        if (!user) return false;
        if (user.can_manage_tickets) return true;
        return global.Auth?.canManageTickets?.(user) || user.role === 'support' || user.is_owner || user.role === 'admin';
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function fmtTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleString('ru', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
            });
        } catch (_) {
            return iso.slice(0, 16);
        }
    }

    async function loadTickets() {
        const q = filterStatus ? `?status=${encodeURIComponent(filterStatus)}` : '';
        const r = await fetch(`/api/support/tickets${q}`, { credentials: 'same-origin' });
        if (!r.ok) throw new Error('Не удалось загрузить тикеты');
        const d = await r.json();
        tickets = d.tickets || [];
        counts = d.counts || {};
    }

    async function loadTicket(id) {
        const r = await fetch(`/api/support/tickets/${id}`, { credentials: 'same-origin' });
        if (!r.ok) throw new Error('Тикет не найден');
        activeTicket = await r.json();
        activeId = id;
    }

    async function loadUserSummary(userId) {
        if (!userId) { userSummary = null; return; }
        try {
            const r = await fetch(`/api/support/users/${userId}/summary`, { credentials: 'same-origin' });
            userSummary = r.ok ? await r.json() : null;
        } catch (_) {
            userSummary = null;
        }
    }

    function renderInbox() {
        const list = document.getElementById('supportTicketList');
        const countsEl = document.getElementById('supportCounts');
        if (countsEl) {
            countsEl.textContent = counts.total != null
                ? `${counts.open || 0} открытых · ${counts.in_progress || 0} в работе`
                : '';
        }
        if (!list) return;

        if (!tickets.length) {
            list.innerHTML = '<p class="muted" style="padding:12px;font-size:12px">Нет тикетов</p>';
            return;
        }

        list.innerHTML = tickets.map((t) => `
            <button type="button" class="support-ticket-item ${t.id === activeId ? 'active' : ''}"
                onclick="SupportPanel.select('${esc(t.id)}')">
                <strong>${esc(t.subject)}</strong>
                <small>${esc(t.user_name || t.user_email)} · ${fmtTime(t.updated_at)}</small>
                <span class="support-status ${esc(t.status)}" style="margin-top:4px;display:inline-block">${STATUS_LABELS[t.status] || t.status}</span>
            </button>`).join('');
    }

    function renderThread() {
        const detail = document.getElementById('supportDetail');
        if (!detail) return;

        if (!activeTicket) {
            detail.innerHTML = '<div class="support-empty">Выберите тикет слева</div>';
            return;
        }

        const msgs = activeTicket.messages || [];
        detail.innerHTML = `
            <div class="support-thread">
                <div class="support-thread-head">
                    <div>
                        <h3>${esc(activeTicket.subject)}</h3>
                        <p class="muted" style="font-size:11px;margin:4px 0 0">${esc(activeTicket.user_name)} · ${esc(activeTicket.user_email)}</p>
                    </div>
                    <div style="display:flex;gap:6px;flex-wrap:wrap">
                        <select id="supportStatusSelect" class="design-input" style="font-size:11px;padding:4px 8px">
                            ${Object.entries(STATUS_LABELS).map(([k, v]) =>
                                `<option value="${k}" ${activeTicket.status === k ? 'selected' : ''}>${v}</option>`
                            ).join('')}
                        </select>
                        <button type="button" class="btn-secondary btn-sm" onclick="SupportPanel.saveStatus()">Статус</button>
                    </div>
                </div>
                <div class="support-messages" id="supportMessages">
                    ${msgs.map((m) => `
                        <div class="support-msg ${esc(m.author_role)} ${m.is_solution ? 'solution' : ''}">
                            <div class="support-msg-meta">${esc(m.author_name)} · ${fmtTime(m.created_at)}${m.is_solution ? ' · ✅ Решение' : ''}</div>
                            ${esc(m.text)}
                        </div>`).join('')}
                </div>
                <div class="support-reply-bar">
                    <textarea id="supportReplyInput" placeholder="Ответ пользователю…"></textarea>
                    <div class="support-reply-actions">
                        <label style="font-size:11px;display:flex;align-items:center;gap:6px">
                            <input type="checkbox" id="supportSolutionCheck"> Пометить как решение
                        </label>
                        <span style="flex:1"></span>
                        <button type="button" class="btn-primary btn-sm" onclick="SupportPanel.sendReply()">Ответить</button>
                    </div>
                </div>
            </div>
            <aside class="support-user-card" id="supportUserCard">
                ${renderUserCard()}
            </aside>`;

        const box = document.getElementById('supportMessages');
        if (box) box.scrollTop = box.scrollHeight;
    }

    function renderUserCard() {
        if (!userSummary) {
            return `<h4>Аккаунт</h4><p class="muted" style="font-size:12px">Загрузка…</p>`;
        }
        const ts = userSummary.task_stats || {};
        return `
            <h4>Аккаунт (базово)</h4>
            <div class="support-user-kv"><span>Имя</span>${esc(userSummary.name)}</div>
            <div class="support-user-kv"><span>Email</span>${esc(userSummary.email)}</div>
            <div class="support-user-kv"><span>Роль</span>${esc(userSummary.role_label)}</div>
            <div class="support-user-kv"><span>Тариф</span>${esc(userSummary.subscription_tier)}</div>
            <div class="support-user-kv"><span>Настройка</span>${userSummary.setup_complete ? '✓ Завершена' : '⏳ Не завершена'}</div>
            <div class="support-user-kv"><span>Регистрация</span>${fmtTime(userSummary.created_at)}</div>
            <div class="support-user-kv"><span>Задачи</span>
                ${ts.total || 0} всего · ${ts.active || 0} активных · ${ts.completed || 0} готово
            </div>
            <p class="muted" style="font-size:10px;margin-top:12px">Пароли, API-ключи и технические настройки недоступны.</p>`;
    }

    function renderFilters() {
        const row = document.getElementById('supportFilterRow');
        if (!row) return;
        const filters = [
            ['', 'Все'],
            ['open', 'Открытые'],
            ['in_progress', 'В работе'],
            ['resolved', 'Решённые'],
            ['closed', 'Закрытые'],
        ];
        row.innerHTML = filters.map(([val, label]) => `
            <button type="button" class="support-filter-btn ${filterStatus === val ? 'active' : ''}"
                onclick="SupportPanel.setFilter('${val}')">${label}</button>`).join('');
    }

    async function load() {
        const root = document.getElementById('supportPanelRoot');
        if (!root) return;
        root.innerHTML = '<div class="support-empty" style="flex:1">Загрузка…</div>';
        try {
            await loadTickets();
            root.innerHTML = `
                <div class="support-inbox">
                    <div class="support-inbox-head">
                        <h2>💬 Тикеты</h2>
                        <p class="muted" id="supportCounts" style="font-size:11px;margin:0"></p>
                        <div class="support-filter-row" id="supportFilterRow"></div>
                    </div>
                    <div class="support-ticket-list" id="supportTicketList"></div>
                </div>
                <div class="support-detail" id="supportDetail"></div>`;
            renderFilters();
            renderInbox();
            renderThread();
        } catch (e) {
            root.innerHTML = `<div class="support-empty">${esc(e.message)}</div>`;
        }
    }

    async function select(id) {
        try {
            await loadTicket(id);
            await loadUserSummary(activeTicket?.user_id);
            renderInbox();
            renderThread();
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function sendReply() {
        if (!activeId) return;
        const text = document.getElementById('supportReplyInput')?.value?.trim();
        if (!text) { toast('Введите ответ', 'warn'); return; }
        const isSolution = document.getElementById('supportSolutionCheck')?.checked;
        try {
            const r = await fetch(`/api/support/tickets/${activeId}/messages`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, is_solution: isSolution }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeTicket = d.ticket;
            document.getElementById('supportReplyInput').value = '';
            if (document.getElementById('supportSolutionCheck')) {
                document.getElementById('supportSolutionCheck').checked = false;
            }
            if (isSolution) await saveStatus('resolved', false);
            await loadTickets();
            renderInbox();
            renderThread();
            toast('Ответ отправлен', 'success');
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function saveStatus(forced, reload = true) {
        if (!activeId) return;
        const status = forced || document.getElementById('supportStatusSelect')?.value;
        try {
            const r = await fetch(`/api/support/tickets/${activeId}`, {
                method: 'PATCH',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeTicket = d.ticket;
            if (reload) {
                await loadTickets();
                renderInbox();
            }
            renderThread();
            toast('Статус обновлён', 'success');
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    async function setFilter(status) {
        filterStatus = status;
        await loadTickets();
        renderFilters();
        renderInbox();
    }

    function updateNavVisibility(user) {
        document.getElementById('supportNavTab')?.classList.toggle('hidden', !canAccess(user));
    }

    global.SupportPanel = {
        canAccess,
        load,
        select,
        sendReply,
        saveStatus,
        setFilter,
        updateNavVisibility,
    };
})(window);
