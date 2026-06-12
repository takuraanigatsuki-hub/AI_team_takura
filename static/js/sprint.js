/** Sprint UI */
(function (global) {
    async function load() {
        const el = document.getElementById('sprintPanel');
        if (!el) return;
        try {
            const r = await fetch('/api/sprint');
            const d = await r.json();
            render(d, el);
        } catch (e) {
            el.innerHTML = `<div class="panel-error">${e.message}</div>`;
        }
    }

    function render(d, el) {
        const backlog = (d.backlog || []).map((b) => `
            <div class="sprint-item ${b.done ? 'done' : ''} priority-${b.priority}">
                <label><input type="checkbox" ${b.done ? 'checked' : ''} onchange="SprintUI.toggle('${b.id}')"> ${escape(b.text)}</label>
                <span class="prio-badge">${b.priority}</span>
            </div>`).join('');

        el.innerHTML = `
            <div class="sprint-hero">
                ${d.active ? `<h2>🏃 ${escape(d.name || 'Sprint')}</h2><p>${escape(d.goal || '')}</p>
                <p class="muted">Осталось ${d.days_left ?? '?'} дн · ${d.stats?.done || 0}/${d.stats?.total || 0} done</p>` :
                '<h2>🏃 Sprint</h2><p class="muted">Нет активного спринта</p>'}
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
            <div class="sprint-backlog">${backlog || '<div class="muted">Backlog пуст</div>'}</div>`;
    }

    async function start() {
        const name = document.getElementById('sprintName')?.value || 'Sprint';
        const goal = document.getElementById('sprintGoal')?.value || 'Цель';
        await fetch('/api/sprint/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, goal, days: 7 }) });
        load();
    }

    async function end() {
        await fetch('/api/sprint/end', { method: 'POST' });
        load();
    }

    async function addBacklog() {
        const text = document.getElementById('backlogInput')?.value;
        const priority = document.getElementById('backlogPrio')?.value || 'medium';
        if (!text) return;
        await fetch('/api/sprint/backlog', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, priority }) });
        load();
    }

    async function toggle(id) {
        await fetch(`/api/sprint/backlog/${id}/toggle`, { method: 'POST' });
        load();
    }

    function escape(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

    global.SprintUI = { load, start, end, addBacklog, toggle };
})(window);
