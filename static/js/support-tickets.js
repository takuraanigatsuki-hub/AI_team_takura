/**
 * Support Tickets — чат с поддержкой для пользователей
 */
(function (global) {
    const FALLBACK_TEMPLATES = [
        { id: 'login', icon: '🔐', title: 'Не могу войти', category: 'auth', subject: 'Проблема со входом', solution: 'Проверьте email и пароль, очистите cookies (Ctrl+F5) и войдите снова.' },
        { id: 'task_stuck', icon: '⏳', title: 'Задача зависла', category: 'tasks', subject: 'Задача не завершается', solution: 'Проверьте Inbox — возможно результат ждёт одобрения. Или отмените активные задачи и отправьте заново.' },
        { id: 'billing', icon: '💳', title: 'Подписка и баланс', category: 'billing', subject: 'Вопрос по подписке', solution: 'Тариф и баланс — в 👤 Кабинете → Подписка.' },
        { id: 'other', icon: '✉️', title: 'Другое', category: 'other', subject: 'Обращение в поддержку', solution: 'Опишите проблему подробно — мы ответим в этом диалоге.' },
    ];

    let templates = [];
    let myTickets = [];
    let activeTicketId = null;
    let activeTicket = null;
    let pendingTemplate = null;

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

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function fmtTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleString('ru', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return '';
        }
    }

    function isStaff(user) {
        if (!user) return false;
        if (user.is_support || user.role === 'support') return true;
        return global.Auth?.canManageTickets?.(user) && ['admin', 'owner', 'tech_admin'].includes(user.role);
    }

    function ensureModal() {
        if (document.getElementById('supportTicketModal')) return;
        const el = document.createElement('div');
        el.id = 'supportTicketModal';
        el.className = 'support-modal-overlay hidden';
        el.onclick = (e) => { if (e.target === el) close(); };
        el.innerHTML = `
            <div class="support-modal support-modal-chat" role="dialog" aria-labelledby="supportModalTitle">
                <div class="support-modal-head">
                    <div>
                        <h2 id="supportModalTitle">💬 Поддержка</h2>
                        <p class="support-modal-sub muted">Онлайн · ответим в ближайшее время</p>
                    </div>
                    <button type="button" class="icon-btn" onclick="SupportTickets.close()" aria-label="Закрыть">×</button>
                </div>
                <div class="support-chat-body" id="supportChatBody"></div>
                <div class="support-chat-compose" id="supportChatCompose"></div>
            </div>`;
        document.body.appendChild(el);
    }

    async function loadTemplates() {
        try {
            const r = await fetch('/api/support/templates', { credentials: 'same-origin' });
            if (r.ok) {
                const d = await r.json();
                templates = d.templates?.length ? d.templates : FALLBACK_TEMPLATES;
            } else {
                templates = FALLBACK_TEMPLATES;
            }
        } catch (_) {
            templates = FALLBACK_TEMPLATES;
        }
    }

    async function loadMyTickets() {
        const user = global.Auth?.getUser();
        if (!user) { myTickets = []; return; }
        try {
            const r = await fetch('/api/support/tickets', { credentials: 'same-origin' });
            if (r.ok) {
                const d = await r.json();
                myTickets = d.tickets || [];
            }
        } catch (_) {}
    }

    async function loadTicket(id) {
        const r = await fetch(`/api/support/tickets/${id}`, { credentials: 'same-origin' });
        if (!r.ok) throw new Error('Тикет не найден');
        activeTicket = await r.json();
        activeTicketId = id;
    }

    function renderHub() {
        activeTicketId = null;
        activeTicket = null;
        pendingTemplate = null;
        const body = document.getElementById('supportChatBody');
        const compose = document.getElementById('supportChatCompose');
        if (!body) return;

        body.innerHTML = `
            <div class="support-chat-messages">
                <div class="support-chat-msg bot">
                    <div class="support-chat-avatar">💬</div>
                    <div class="support-chat-bubble">
                        <strong>Поддержка AI Team</strong>
                        <p>Здравствуйте! Выберите тему ниже или опишите проблему — мы ответим в этом чате.</p>
                    </div>
                </div>
                <div class="support-topic-menu">
                    <div class="support-topic-label">Выберите тему:</div>
                    <div class="support-topic-chips">
                        ${templates.map((t) => `
                            <button type="button" class="support-topic-chip" data-tid="${esc(t.id)}">
                                <span>${t.icon || '💬'}</span> ${esc(t.title)}
                            </button>`).join('')}
                    </div>
                </div>
                ${myTickets.length ? `
                <div class="support-my-dialogs">
                    <div class="support-topic-label">Мои диалоги:</div>
                    ${myTickets.slice(0, 8).map((t) => `
                        <button type="button" class="support-dialog-row" data-tid-open="${esc(t.id)}">
                            <span>${esc(t.subject)}</span>
                            <span class="support-status ${esc(t.status)}">${STATUS_LABELS[t.status] || t.status}</span>
                        </button>`).join('')}
                </div>` : ''}
            </div>`;

        compose.innerHTML = `
            <textarea id="supportFreeInput" rows="2" placeholder="Или напишите сообщение…"></textarea>
            <button type="button" class="btn-primary btn-sm" onclick="SupportTickets.sendFree()">Отправить</button>`;

        body.querySelectorAll('.support-topic-chip').forEach((btn) => {
            btn.onclick = () => {
                pendingTemplate = templates.find((t) => t.id === btn.dataset.tid) || null;
                renderNewTicketChat();
            };
        });
        body.querySelectorAll('[data-tid-open]').forEach((btn) => {
            btn.onclick = () => openTicketChat(btn.dataset.tidOpen);
        });
    }

    function renderNewTicketChat() {
        const tpl = pendingTemplate;
        const body = document.getElementById('supportChatBody');
        const compose = document.getElementById('supportChatCompose');
        if (!body || !tpl) return;

        body.innerHTML = `
            <div class="support-chat-toolbar">
                <button type="button" class="btn-secondary btn-xs" onclick="SupportTickets.backToHub()">← К темам</button>
                <span class="muted">${esc(tpl.title)}</span>
            </div>
            <div class="support-chat-messages" id="supportChatMessages">
                <div class="support-chat-msg user">
                    <div class="support-chat-bubble">${esc(tpl.title)}</div>
                </div>
                <div class="support-chat-msg bot">
                    <div class="support-chat-avatar">💬</div>
                    <div class="support-chat-bubble solution">
                        <strong>💡 Подсказка</strong>
                        <p>${esc(tpl.solution || '')}</p>
                        <p class="muted" style="margin-top:8px;font-size:11px">Не помогло? Напишите ниже — создадим обращение.</p>
                    </div>
                </div>
            </div>`;

        compose.innerHTML = `
            <textarea id="supportMessageInput" rows="2" placeholder="Опишите проблему подробнее…"></textarea>
            <button type="button" class="btn-primary btn-sm" onclick="SupportTickets.submit()">Отправить в поддержку</button>`;
    }

    function renderTicketChat() {
        const body = document.getElementById('supportChatBody');
        const compose = document.getElementById('supportChatCompose');
        if (!body || !activeTicket) return;

        const msgs = activeTicket.messages || [];
        body.innerHTML = `
            <div class="support-chat-toolbar">
                <button type="button" class="btn-secondary btn-xs" onclick="SupportTickets.backToHub()">← К темам</button>
                <span>${esc(activeTicket.subject)}</span>
                <span class="support-status ${esc(activeTicket.status)}">${STATUS_LABELS[activeTicket.status] || activeTicket.status}</span>
            </div>
            <div class="support-chat-messages" id="supportChatMessages">
                ${msgs.map((m) => `
                    <div class="support-chat-msg ${m.author_role === 'user' ? 'user' : 'bot'} ${m.is_solution ? 'solution' : ''}">
                        ${m.author_role !== 'user' ? '<div class="support-chat-avatar">💬</div>' : ''}
                        <div class="support-chat-bubble">
                            <small class="support-chat-meta">${esc(m.author_name)} · ${fmtTime(m.created_at)}</small>
                            ${esc(m.text)}
                        </div>
                    </div>`).join('')}
            </div>`;

        compose.innerHTML = activeTicket.status === 'closed'
            ? '<p class="muted" style="padding:8px;font-size:12px">Обращение закрыто</p>'
            : `<textarea id="supportReplyInput" rows="2" placeholder="Ваше сообщение…"></textarea>
               <button type="button" class="btn-primary btn-sm" onclick="SupportTickets.reply()">Отправить</button>`;

        const box = document.getElementById('supportChatMessages');
        if (box) box.scrollTop = box.scrollHeight;
    }

    async function openTicketChat(id) {
        try {
            await loadTicket(id);
            renderTicketChat();
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    function renderGuest() {
        const body = document.getElementById('supportChatBody');
        const compose = document.getElementById('supportChatCompose');
        if (!body) return;
        body.innerHTML = `
            <div class="support-chat-messages">
                <div class="support-chat-msg bot">
                    <div class="support-chat-avatar">💬</div>
                    <div class="support-chat-bubble">
                        <p>Войдите в аккаунт, чтобы написать в поддержку.</p>
                    </div>
                </div>
            </div>`;
        compose.innerHTML = `<a href="/?auth=login" class="btn-primary" style="text-decoration:none">Войти</a>`;
    }

    async function open() {
        const user = global.Auth?.getUser();
        if (user && isStaff(user)) {
            global.switchView?.('support');
            return;
        }

        ensureModal();
        document.getElementById('supportTicketModal')?.classList.remove('hidden');

        if (!user) {
            renderGuest();
            return;
        }

        await Promise.all([loadTemplates(), loadMyTickets()]);
        renderHub();
    }

    function close() {
        document.getElementById('supportTicketModal')?.classList.add('hidden');
    }

    function backToHub() {
        renderHub();
    }

    async function sendFree() {
        const text = document.getElementById('supportFreeInput')?.value?.trim();
        if (!text) { toast('Напишите сообщение', 'warn'); return; }
        pendingTemplate = templates.find((t) => t.id === 'other') || FALLBACK_TEMPLATES[3];
        await submitWithMessage(text, pendingTemplate.subject || 'Обращение в поддержку');
    }

    async function submit() {
        const message = document.getElementById('supportMessageInput')?.value?.trim() || '';
        const subject = pendingTemplate?.subject || pendingTemplate?.title || 'Обращение в поддержку';
        if (!message) { toast('Опишите проблему', 'warn'); return; }
        await submitWithMessage(message, subject);
    }

    async function submitWithMessage(message, subject) {
        const user = global.Auth?.getUser();
        if (!user) { toast('Войдите в аккаунт', 'warn'); return; }
        try {
            const r = await fetch('/api/support/tickets', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject,
                    message,
                    category: pendingTemplate?.category || 'other',
                    template_id: pendingTemplate?.id || '',
                }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            toast('Обращение создано — ждите ответа поддержки', 'success');
            await loadMyTickets();
            if (d.ticket?.id) {
                await openTicketChat(d.ticket.id);
            } else {
                close();
            }
        } catch (e) {
            toast(e.message || 'Не удалось отправить', 'error');
        }
    }

    async function reply() {
        if (!activeTicketId) return;
        const text = document.getElementById('supportReplyInput')?.value?.trim();
        if (!text) return;
        try {
            const r = await fetch(`/api/support/tickets/${activeTicketId}/messages`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            activeTicket = d.ticket;
            document.getElementById('supportReplyInput').value = '';
            renderTicketChat();
        } catch (e) {
            toast(e.message, 'error');
        }
    }

    global.SupportTickets = {
        open, close, backToHub, submit, sendFree, reply, back: backToHub,
    };
})(window);
