/** Kanban board — задачи по колонкам */
(function (global) {
    const COLS = [
        { id: 'submitted', title: '📥 Входящие' },
        { id: 'in_progress', title: '⚡ В работе' },
        { id: 'completed', title: '✅ Готово' },
        { id: 'failed', title: '❌ Ошибки' },
    ];

    async function refresh() {
        try {
            const r = await fetch('/api/kanban');
            const d = await r.json();
            render(d.columns || {});
        } catch (e) {
            const el = document.getElementById('kanbanBoard');
            if (el) el.innerHTML = `<div class="panel-empty">Ошибка: ${e}</div>`;
        }
    }

    function render(columns) {
        const el = document.getElementById('kanbanBoard');
        if (!el) return;
        el.innerHTML = COLS.map((col) => {
            const items = columns[col.id] || [];
            const cards = items.map((t) => `
                <div class="kb-card" onclick="switchView('tasks')">
                    <div class="kb-title">${escape(t.text || t.task || '—').slice(0, 60)}</div>
                    <div class="kb-meta">${t.agent_emoji || ''} ${t.agent_name || t.agent_id || ''}</div>
                </div>`).join('');
            return `<div class="kb-col"><div class="kb-col-head">${col.title} <span>${items.length}</span></div>${cards || '<div class="kb-empty">—</div>'}</div>`;
        }).join('');
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.KanbanUI = { refresh };
})(window);
