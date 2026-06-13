/** Timeline / Replay — последняя активность */
(function (global) {
    let events = [];

    const SKIP_TYPES = new Set([
        'agents_state', 'history', 'task_history', 'agent_stream', 'agent_stream_start',
        'presence_update', 'balance_update', 'pipeline_update', 'cursor_progress',
    ]);

    const TYPE_LABELS = {
        task_received: 'Задача получена',
        task_done: 'Задача выполнена',
        task_failed: 'Ошибка задачи',
        task_awaiting_approval: 'Ожидает одобрения',
        pm_plan: 'План PM',
        system: 'Система',
        site_ready: 'Сайт готов',
        react_preview: 'React Preview',
        figma_import: 'Figma импорт',
        figma_study: 'Изучение Figma',
        sonya_studio_project: 'Sonya Studio',
        sonya_studio_published: 'Публикация Studio',
        learning: 'Обучение',
        learning_result: 'Результат обучения',
    };

    function eventMessage(ev) {
        const text = (ev.message || ev.text || '').trim();
        if (text) return text;
        const label = TYPE_LABELS[ev.type] || '';
        if (label) return label;
        if (SKIP_TYPES.has(ev.type)) return '';
        return ev.type || '';
    }

    function filterEvents(list) {
        return (list || []).filter((ev) => {
            if (SKIP_TYPES.has(ev.type)) return false;
            return !!eventMessage(ev);
        });
    }

    async function load(hours) {
        const h = hours || 1;
        const el = document.getElementById('timelinePanel');
        if (el) el.innerHTML = global.UICore ? UICore.loadingState() : '<div class="dash-loading">Загрузка…</div>';
        try {
            const r = await fetch(`/api/timeline/replay?hours=${h}`, { credentials: 'same-origin' });
            if (r.status === 403) {
                if (el) {
                    el.innerHTML = global.UICore ? UICore.errorState('Timeline доступен только администраторам') : '<div class="panel-error">Timeline доступен только администраторам</div>';
                }
                return;
            }
            if (r.status === 401) {
                if (el) {
                    el.innerHTML = global.UICore ? UICore.authRequiredState({
                        icon: '⏱',
                        title: 'Timeline',
                        text: 'Войдите для полной ленты. Задачи из чата — в Inbox.',
                    }) : `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">⏱</div>
                        <h3>Timeline</h3><p class="muted">Войдите для полной ленты. Задачи из чата — во вкладке «Задачи».</p>
                        <a href="/?auth=login" class="btn-primary btn-sm">Войти</a></div>`;
                }
                return;
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = global.UICore?.parseApiJson
                ? await UICore.parseApiJson(r, 'Timeline')
                : await r.json();
            events = filterEvents(d.events || []);
            render({ ...d, events, total: events.length });
        } catch (e) {
            render({ total: 0, by_type: {}, events: [], error: String(e) });
        }
    }

    function render(data) {
        const el = document.getElementById('timelinePanel');
        if (!el) return;
        const visible = filterEvents(data.events || []);
        const types = Object.entries(data.by_type || {})
            .filter(([k]) => !SKIP_TYPES.has(k))
            .map(([k, v]) => `<span class="tl-chip">${escape(TYPE_LABELS[k] || k)}: ${v}</span>`).join('');
        const rows = visible.slice().reverse().map((ev) => {
            const t = (ev.timestamp || ev.recorded_at || '').slice(11, 19);
            const who = ev.agent_emoji
                ? `${ev.agent_emoji} ${ev.agent_name || ev.agent_id || ''}`
                : (ev.agent_name || ev.agent_id || 'Команда');
            const msg = escape(eventMessage(ev).slice(0, 120));
            const type = ev.type || '';
            return `<div class="tl-row tl-type-${escape(type)}"><span class="tl-time">${t}</span><span class="tl-who">${escape(who.trim())}</span><span class="tl-msg">${msg}</span></div>`;
        }).join('');
        el.innerHTML = `
            <div class="tl-stats">${visible.length || data.total || 0} событий за ${data.hours || 1}ч</div>
            <div class="tl-chips">${types || '<span class="muted">Нет данных</span>'}</div>
            <div class="tl-list">${rows || (global.UICore
                ? UICore.inlineEmpty('Пока пусто — активность появится после задач в чате')
                : '<div class="panel-empty">Пока пусто — активность появится после задач в чате</div>')}</div>
            <div class="tl-actions">
                <button type="button" class="btn-secondary btn-sm ${data.hours === 1 ? 'active' : ''}" onclick="TimelineUI.load(1)">1ч</button>
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.load(6)">6ч</button>
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.load(24)">24ч</button>
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.replay()">▶ Replay</button>
            </div>`;
    }

    function replay() {
        const visible = filterEvents(events);
        if (!visible.length) {
            if (window.UIEnhancements) UIEnhancements.toast('Нет событий для replay', 'info');
            return;
        }
        let i = 0;
        const step = () => {
            if (i >= visible.length) {
                if (window.UIEnhancements) UIEnhancements.toast('Replay завершён', 'success');
                return;
            }
            const ev = visible[i++];
            const who = ev.agent_name || ev.agent_id || '';
            const msg = eventMessage(ev).slice(0, 48);
            if (window.UIEnhancements) {
                UIEnhancements.toast(`${who} ${msg}`.trim(), 'info', 1200);
            }
            setTimeout(step, 500);
        };
        step();
    }

    function escape(s) {
        return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    global.TimelineUI = { load, replay };
})(window);
