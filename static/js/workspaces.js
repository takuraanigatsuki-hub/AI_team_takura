/**
 * Team Workspaces — переключатель комнат
 */
(function (global) {
    let activeId = '';
    let workspaces = [];

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    async function load() {
        if (!global.Auth?.isLoggedIn?.()) return;
        try {
            const r = await fetch('/api/workspaces/active', { credentials: 'same-origin' });
            if (!r.ok) return;
            const d = await r.json();
            activeId = d.active_id || '';
            workspaces = d.workspaces || [];
            renderSwitcher();
        } catch (_) {}
    }

    function renderSwitcher() {
        const el = document.getElementById('workspaceSwitcher');
        if (!el) return;
        if (!workspaces.length) {
            el.innerHTML = `<button type="button" class="hdr-btn btn-sm" onclick="Workspaces.showCreate()" title="Создать workspace">+ WS</button>`;
            return;
        }
        el.innerHTML = `
            <select id="wsSelect" class="ws-select" title="Workspace" onchange="Workspaces.switchTo(this.value)">
                <option value="">— Workspace —</option>
                ${workspaces.map((w) =>
                    `<option value="${esc(w.id)}" ${w.id === activeId ? 'selected' : ''}>${esc(w.name)}</option>`
                ).join('')}
            </select>
            <button type="button" class="hdr-btn btn-sm" onclick="Workspaces.showCreate()" title="Новый">+</button>`;
    }

    async function switchTo(id) {
        await fetch('/api/workspaces/active', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ workspace_id: id }),
        });
        activeId = id;
        if (global.UIEnhancements) UIEnhancements.toast(id ? 'Workspace переключён' : 'Общий режим', 'info');
    }

    function showCreate() {
        const name = prompt('Название workspace:', 'Моя команда');
        if (!name) return;
        create(name);
    }

    async function create(name, description) {
        try {
            const r = await fetch('/api/workspaces', {
                method: 'POST', credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description: description || '' }),
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = await r.json();
            await switchTo(d.workspace?.id || '');
            await load();
            if (global.UIEnhancements) UIEnhancements.toast('Workspace создан', 'success');
        } catch (e) {
            if (global.UIEnhancements) UIEnhancements.toast(e.message, 'error');
        }
    }

    global.Workspaces = { load, switchTo, showCreate, create };
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(load, 1500);
    });
})(window);
