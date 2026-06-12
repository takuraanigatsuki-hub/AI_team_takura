/**
 * Task Templates — пресеты задач
 */
(function (global) {
    let templates = [];

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    async function fetchTemplates() {
        const r = await fetch('/api/task-templates');
        if (r.ok) {
            const d = await r.json();
            templates = d.templates || [];
        }
        return templates;
    }

    async function showPicker() {
        await fetchTemplates();
        const modal = document.getElementById('templatePickerModal');
        const list = document.getElementById('templatePickerList');
        if (!modal || !list) return;
        list.innerHTML = templates.map((t) =>
            `<button type="button" class="ucard ucard-click" onclick="TaskTemplates.apply('${t.id}')">
                <span class="ucard-emoji">${t.emoji}</span>
                <strong>${esc(t.title)}</strong>
                <p class="muted">${esc(t.description.slice(0, 100))}…</p>
                <span class="ucard-badge">${t.credits} кр.</span>
            </button>`
        ).join('');
        modal.classList.remove('hidden');
    }

    function hidePicker() {
        document.getElementById('templatePickerModal')?.classList.add('hidden');
    }

    async function apply(id) {
        hidePicker();
        try {
            const r = await fetch('/api/task-templates/' + id + '/apply', {
                method: 'POST', credentials: 'same-origin',
            });
            if (!r.ok) {
                const e = await r.json().catch(() => ({}));
                throw new Error(e.detail || 'HTTP ' + r.status);
            }
            if (global.UIEnhancements) UIEnhancements.toast('Шаблон запущен', 'success');
        } catch (e) {
            if (global.UIEnhancements) UIEnhancements.toast(e.message, 'error');
            else alert(e.message);
        }
    }

    global.TaskTemplates = { showPicker, hidePicker, apply, fetchTemplates };
})(window);
