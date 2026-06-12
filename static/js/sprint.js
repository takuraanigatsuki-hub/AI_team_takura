/** Sprint UI — per-user sprint backlog */
(function (global) {
    async function load() {
        const el = document.getElementById('sprintPanel');
        if (!el) return;
        el.innerHTML = '<div class="dash-loading">Загрузка…</div>';
        try {
            const r = await fetch('/api/sprint', { credentials: 'same-origin' });
            const d = await r.json();
            if (d.guest) {
                el.innerHTML = `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">🔐</div>
                    <h3>Sprint — войдите</h3><p class="muted">У каждого пользователя свой спринт и backlog</p>
                    <a href="/?auth=login" class="btn-primary btn-sm">Войти</a></div>`;
                return;
            }
            render(d, el);
        } catch (e) {
            el.innerHTML = `<div class="panel-error">${escape(e.message)}</div>`;
        }
    }

    function render(d, el) {
        const pct = d.progress_pct || 0;
        const backlog = (d.backlog || []).map((b) => `
            <div class="sprint-item ${b.done ? 'done' : ''} priority-${b.priority || 'medium'}">
                <label><input type="checkbox" ${b.done ? 'checked' : ''} onchange="SprintUI.toggle('${escape(b.id)}')"> ${escape(b.text)}</label>
                <span class="prio-badge">${b.priority || 'medium'}</span>
            </div>`).join('');

        el.innerHTML = `
            <div class="sprint-hero">
                ${d.active ? `<h2>🏃 ${escape(d.name || 'Sprint')}</h2><p>${escape(d.goal || '')}</p>
                <div class="sprint-progress"><div class="sprint-progress-bar" style="width:${pct}%"></div></div>
                <p class="muted">Осталось ${d.days_left ?? '?'} дн · ${d.stats?.done || 0}/${d.stats?.total || 0} · ${pct}%</p>` :
                '<h2>🏃 Sprint</h2><p class="muted">Запланируйте цель на неделю и ведите backlog</p>'}
            </div>
            <div class="sprint-actions">
                ${d.active ? `<button class="btn-secondary btn-sm" onclick="SprintUI.end()">Завершить</button>` : `
                <input id="sprintName" placeholder="Sprint 1" class="design-input">
                <input id="sprintGoal" placeholder="Цель спринта" class="design-input">
                <button class="btn-primary btn-sm" onclick="SprintUI.start()">Старт</button>`}
            </div>
            ${d.active ? `<div class="sprint-add"><input id="backlogInput" placeholder="Backlog item…" class="design-input">
                <select id="backlogPrio"><option value="urgent">🔴 urgent</option><option value="high">high</option><option value="medium" selected>medium</option><option value="low">low</option></select>
                <button class="btn-secondary btn-sm" onclick="SprintUI.addBacklog()">+</button></div>` : ''}
            <div class="sprint-backlog">${backlog || '<div class="muted">Backlog пуст — добавьте пункты</div>'}</div>`;
    }

    async function apiPost(url, body) {
        const r = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined,
        });
        if (!r.ok) {
            const d = await r.json().catch(() => ({}));
            throw new Error(d.detail || 'Ошибка');
        }
        return r.json();
    }

    async function start() {
        try {
            await apiPost('/api/sprint/start', {
                name: document.getElementById('sprintName')?.value || 'Sprint',
                goal: document.getElementById('sprintGoal')?.value || 'Цель',
                days: 7,
            });
            if (window.UIEnhancements) UIEnhancements.toast('🏃 Sprint начат', 'success');
            load();
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'warn');
        }
    }

    async function end() {
        try {
            await apiPost('/api/sprint/end');
            if (window.UIEnhancements) UIEnhancements.toast('Sprint завершён', 'info');
            load();
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'warn');
        }
    }

    async function addBacklog() {
        const text = document.getElementById('backlogInput')?.value?.trim();
        const priority = document.getElementById('backlogPrio')?.value || 'medium';
        if (!text) return;
        try {
            await apiPost('/api/sprint/backlog', { text, priority });
            load();
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'warn');
        }
    }

    async function toggle(id) {
        try {
            await apiPost(`/api/sprint/backlog/${id}/toggle`);
            load();
        } catch (e) {
            if (window.UIEnhancements) UIEnhancements.toast(e.message, 'warn');
        }
    }

    function escape(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

    global.SprintUI = { load, start, end, addBacklog, toggle };
})(window);
