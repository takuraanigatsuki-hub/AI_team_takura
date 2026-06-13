/**
 * Support Tickets — модальное окно для пользователей (FAB)
 */
(function (global) {
    let templates = [];
    let myTickets = [];
    let selectedTemplate = null;
    let step = 'pick';

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

    function ensureModal() {
        if (document.getElementById('supportTicketModal')) return;
        const el = document.createElement('div');
        el.id = 'supportTicketModal';
        el.className = 'support-modal-overlay hidden';
        el.onclick = (e) => { if (e.target === el) close(); };
        el.innerHTML = `
            <div class="support-modal" role="dialog" aria-labelledby="supportModalTitle">
                <div class="support-modal-head">
                    <h2 id="supportModalTitle">💬 Поддержка</h2>
                    <button type="button" class="icon-btn" onclick="SupportTickets.close()" aria-label="Закрыть">×</button>
                </div>
                <div class="support-modal-body" id="supportModalBody"></div>
                <div class="support-modal-foot" id="supportModalFoot"></div>
            </div>`;
        document.body.appendChild(el);
    }

    async function loadTemplates() {
        try {
            const r = await fetch('/api/support/templates', { credentials: 'same-origin' });
            if (r.ok) {
                const d = await r.json();
                templates = d.templates || [];
            }
        } catch (_) {}
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

    function renderPickStep() {
        step = 'pick';
        const body = document.getElementById('supportModalBody');
        const foot = document.getElementById('supportModalFoot');
        if (!body) return;

        body.innerHTML = `
            <p class="muted" style="font-size:12px;margin:0 0 12px">Выберите тему — покажем готовое решение или поможем создать обращение.</p>
            <div class="support-template-grid" id="supportTemplateGrid">
                ${templates.map((t) => `
                    <button type="button" class="support-template-card" data-tid="${esc(t.id)}">
                        <span class="st-icon">${t.icon || '💬'}</span>
                        <strong>${esc(t.title)}</strong>
                        <small>${esc(t.hint || '')}</small>
                    </button>`).join('')}
            </div>
            ${myTickets.length ? `
                <div class="support-my-tickets">
                    <strong style="font-size:12px">Мои обращения</strong>
                    ${myTickets.slice(0, 5).map((t) => `
                        <div class="support-ticket-row">
                            <span>${esc(t.subject)}</span>
                            <span class="support-status ${esc(t.status)}">${STATUS_LABELS[t.status] || t.status}</span>
                        </div>`).join('')}
                </div>` : ''}`;

        foot.innerHTML = `<button type="button" class="btn-secondary" onclick="SupportTickets.close()">Закрыть</button>`;

        body.querySelectorAll('.support-template-card').forEach((btn) => {
            btn.onclick = () => {
                selectedTemplate = templates.find((t) => t.id === btn.dataset.tid) || null;
                renderFormStep();
            };
        });
    }

    function renderFormStep() {
        step = 'form';
        const body = document.getElementById('supportModalBody');
        const foot = document.getElementById('supportModalFoot');
        if (!body || !selectedTemplate) return;

        body.innerHTML = `
            <button type="button" class="btn-secondary btn-sm" style="margin-bottom:12px" onclick="SupportTickets.back()">← Назад</button>
            <div class="support-solution-box">
                <h4>✅ Возможное решение</h4>
                ${esc(selectedTemplate.solution || '')}
            </div>
            <div class="support-form-group">
                <label>Тема</label>
                <input type="text" id="supportSubjectInput" value="${esc(selectedTemplate.subject || selectedTemplate.title)}" maxlength="160">
            </div>
            <div class="support-form-group">
                <label>Опишите проблему (если решение не помогло)</label>
                <textarea id="supportMessageInput" rows="4" placeholder="Что произошло? Когда? Какой результат ожидали?"></textarea>
            </div>`;

        foot.innerHTML = `
            <button type="button" class="btn-secondary" onclick="SupportTickets.close()">Закрыть</button>
            <button type="button" class="btn-primary" onclick="SupportTickets.submit()">Отправить тикет</button>`;
    }

    function renderGuestStep() {
        step = 'guest';
        const body = document.getElementById('supportModalBody');
        const foot = document.getElementById('supportModalFoot');
        if (!body) return;
        body.innerHTML = `
            <p style="font-size:14px;margin:0 0 12px">Для обращения в поддержку войдите в аккаунт.</p>
            <p class="muted" style="font-size:12px">После входа нажмите 💬 внизу справа — выберите тему или опишите проблему.</p>`;
        foot.innerHTML = `
            <button type="button" class="btn-secondary" onclick="SupportTickets.close()">Закрыть</button>
            <a href="/?auth=login" class="btn-primary" style="text-decoration:none;display:inline-flex;align-items:center">Войти</a>`;
    }

    async function open() {
        ensureModal();
        const user = global.Auth?.getUser();
        const modal = document.getElementById('supportTicketModal');
        modal?.classList.remove('hidden');

        if (!user) {
            renderGuestStep();
            return;
        }

        await Promise.all([loadTemplates(), loadMyTickets()]);
        selectedTemplate = null;
        renderPickStep();
    }

    function close() {
        document.getElementById('supportTicketModal')?.classList.add('hidden');
    }

    function back() {
        selectedTemplate = null;
        renderPickStep();
    }

    async function submit() {
        const user = global.Auth?.getUser();
        if (!user) {
            toast('Войдите в аккаунт', 'warn');
            return;
        }
        const subject = document.getElementById('supportSubjectInput')?.value?.trim() || '';
        const message = document.getElementById('supportMessageInput')?.value?.trim() || '';
        if (!message && !subject) {
            toast('Опишите проблему', 'warn');
            return;
        }
        try {
            const r = await fetch('/api/support/tickets', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subject,
                    message: message || subject,
                    category: selectedTemplate?.category || 'other',
                    template_id: selectedTemplate?.id || '',
                }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            toast('Тикет отправлен — ответим в ближайшее время', 'success');
            close();
        } catch (e) {
            toast(e.message || 'Не удалось отправить', 'error');
        }
    }

    global.SupportTickets = { open, close, back, submit };
})(window);
