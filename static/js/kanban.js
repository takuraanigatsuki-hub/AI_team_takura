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

    function columnsFromWsTasks(tasks) {
        const cols = { submitted: [], in_progress: [], completed: [], failed: [] };
        const inbox = new Set(['submitted', 'queued', 'triaging', 'awaiting_approval', 'revision_requested']);
        tasks.filter((t) => !t.parent_id).forEach((t) => {
            const item = {
                id: t.id,
                text: t.task,
                task: t.task,
                priority: t.priority,
                agent_emoji: t.agent_emoji,
                agent_name: t.agent_name,
                agent_id: t.agent_id,
            };
            if (t.status === 'completed') cols.completed.push(item);
            else if (t.status === 'failed' || t.status === 'cancelled') cols.failed.push(item);
            else if (t.status === 'in_progress') cols.in_progress.push(item);
            else if (inbox.has(t.status)) cols.submitted.push(item);
            else cols.in_progress.push(item);
        });
        return cols;
    }

    async function refresh() {
        const el = document.getElementById('kanbanBoard');
        if (!el) return;
        const user = global.Auth?.getUser?.();
        if (!user) {
            const snap = global.AITeamTasks?.getSnapshot?.();
            if (snap?.tasks?.length) {
                render(columnsFromWsTasks(snap.tasks));
                return;
            }
            el.innerHTML = global.UICore ? UICore.emptyState({
                icon: '💬',
                title: 'Гостевая сессия',
                text: 'Отправьте задачу в чат — доска заполнится автоматически',
                primaryLabel: 'В чат',
                primaryOnclick: "switchView('chat')",
            }) : `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">💬</div>
                <h3>Гостевая сессия</h3><p class="muted">Отправьте задачу в чат — доска заполнится автоматически</p>
                <button type="button" class="btn-primary btn-sm" onclick="switchView('chat')">В чат</button></div>`;
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
            if (el) {
                el.innerHTML = global.UICore
                    ? UICore.errorState(String(e.message || e))
                    : `<div class="panel-empty">${escape(String(e.message || e))}</div>`;
            }
        }
    }

    function render(columns) {
        const el = document.getElementById('kanbanBoard');
        if (!el) return;
        el.innerHTML = COLS.map((col) => {
            const items = columns[col.id] || [];
            const cards = items.map((t) => (global.UICore
                ? UICore.renderKanbanCard(t)
                : '')).join('');
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
        const revert = global.AITeamTasks?.patchOptimistic?.(taskId, { priority: next });
        const prioEl = document.querySelector(`.kb-card[data-task-id="${taskId}"] .kb-prio`);
        const prevLabel = prioEl?.textContent;
        if (prioEl) prioEl.textContent = PRIO_LABELS[next] || next;
        const user = global.Auth?.getUser?.();
        if (!user && global.AITeamTasks?.sendWs?.({ type: 'task_priority', task_id: taskId, priority: next })) {
            return;
        }
        const r = await fetch(`/api/tasks/${taskId}/priority`, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ priority: next }),
        });
        if (r.ok) refresh();
        else {
            if (typeof revert === 'function') revert();
            if (prioEl && prevLabel) prioEl.textContent = prevLabel;
            if (window.UIEnhancements) {
                const d = await r.json().catch(() => ({}));
                UIEnhancements.toast(d.detail || 'Нет доступа', 'warn');
            }
        }
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.KanbanUI = { refresh, onDragStart, onDragOver, onDrop, cyclePriority };
})(window);
