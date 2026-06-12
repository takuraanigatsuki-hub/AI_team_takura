/** Kanban board — задачи по колонкам + приоритет */
(function (global) {
    const COLS = [
        { id: 'submitted', title: '📥 Входящие' },
        { id: 'in_progress', title: '⚡ В работе' },
        { id: 'completed', title: '✅ Готово' },
        { id: 'failed', title: '❌ Ошибки' },
    ];
    const PRIOS = ['low', 'medium', 'high', 'urgent'];
    const PRIO_LABELS = { urgent: '🔴', high: '🟠', medium: '🟡', low: '⚪' };

    async function refresh() {
        const el = document.getElementById('kanbanBoard');
        if (!el) return;
        const user = global.Auth?.getUser?.();
        if (!user) {
            el.innerHTML = `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">🔐</div>
                <h3>Войдите для Kanban</h3><p class="muted">Доска показывает только ваши задачи</p>
                <a href="/?auth=login" class="btn-primary btn-sm">Войти</a></div>`;
            return;
        }
        try {
            const r = await fetch('/api/kanban', { credentials: 'same-origin' });
            if (!r.ok) {
                const d = await r.json().catch(() => ({}));
                throw new Error(d.detail || 'Не удалось загрузить Kanban');
            }
            const d = await r.json();
            render(d.columns || {});
        } catch (e) {
            const el = document.getElementById('kanbanBoard');
            if (el) el.innerHTML = `<div class="panel-empty">${escape(String(e.message || e))}</div>`;
        }
    }

    function render(columns) {
        const el = document.getElementById('kanbanBoard');
        if (!el) return;
        el.innerHTML = COLS.map((col) => {
            const items = columns[col.id] || [];
            const cards = items.map((t) => {
                const prio = t.priority || 'medium';
                return `
                <div class="kb-card priority-${prio}" draggable="true"
                     data-task-id="${escape(t.id || '')}"
                     ondragstart="KanbanUI.onDragStart(event)"
                     ondragover="KanbanUI.onDragOver(event)"
                     ondrop="KanbanUI.onDrop(event)">
                    <div class="kb-head">
                        <span class="kb-prio" title="Сменить приоритет"
                              onclick="event.stopPropagation();KanbanUI.cyclePriority('${escape(t.id)}','${prio}')">${PRIO_LABELS[prio] || prio}</span>
                        <span class="kb-status">${col.id}</span>
                    </div>
                    <div class="kb-title" onclick="switchView('tasks')">${escape(t.text || t.task || '—').slice(0, 60)}</div>
                    <div class="kb-meta">${t.agent_emoji || ''} ${t.agent_name || t.agent_id || ''}</div>
                </div>`;
            }).join('');
            return `<div class="kb-col" data-col="${col.id}"><div class="kb-col-head">${col.title} <span>${items.length}</span></div>${cards || '<div class="kb-empty">—</div>'}</div>`;
        }).join('');
    }

    let dragId = null;

    function onDragStart(e) {
        dragId = e.currentTarget.dataset.taskId;
        e.dataTransfer.effectAllowed = 'move';
    }

    function onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function onDrop(e) {
        e.preventDefault();
        if (!dragId) return;
        const col = e.currentTarget.closest('.kb-col')?.dataset.col;
        if (col && window.UIEnhancements) {
            UIEnhancements.toast('Статус меняется при выполнении задачи', 'info');
        }
        dragId = null;
    }

    async function cyclePriority(taskId, current) {
        if (!taskId) return;
        const idx = PRIOS.indexOf(current);
        const next = PRIOS[(idx + 1) % PRIOS.length];
        const r = await fetch(`/api/tasks/${taskId}/priority`, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ priority: next }),
        });
        if (r.ok) refresh();
        else if (window.UIEnhancements) {
            const d = await r.json().catch(() => ({}));
            UIEnhancements.toast(d.detail || 'Нет доступа', 'warn');
        }
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.KanbanUI = { refresh, onDragStart, onDragOver, onDrop, cyclePriority };
})(window);
