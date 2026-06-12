/** Timeline / Replay — последний час активности */
(function (global) {
    let events = [];

    async function load(hours) {
        const h = hours || 1;
        try {
            const r = await fetch(`/api/timeline/replay?hours=${h}`);
            const d = await r.json();
            events = d.events || [];
            render(d);
        } catch (e) {
            render({ total: 0, by_type: {}, events: [], error: String(e) });
        }
    }

    function render(data) {
        const el = document.getElementById('timelinePanel');
        if (!el) return;
        const types = Object.entries(data.by_type || {})
            .map(([k, v]) => `<span class="tl-chip">${k}: ${v}</span>`).join('');
        const rows = (data.events || []).slice().reverse().map((ev) => {
            const t = (ev.timestamp || ev.recorded_at || '').slice(11, 19);
            const who = ev.agent_name || ev.agent_id || '—';
            const msg = (ev.message || ev.type || '').slice(0, 80);
            return `<div class="tl-row"><span class="tl-time">${t}</span><span class="tl-who">${who}</span><span class="tl-msg">${msg}</span></div>`;
        }).join('');
        el.innerHTML = `
            <div class="tl-stats">${data.total || 0} событий за ${data.hours || 1}ч</div>
            <div class="tl-chips">${types || '<span class="muted">Нет данных</span>'}</div>
            <div class="tl-list">${rows || '<div class="panel-empty">Пока пусто</div>'}</div>
            <div class="tl-actions">
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.load(1)">1ч</button>
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.load(6)">6ч</button>
                <button type="button" class="btn-secondary btn-sm" onclick="TimelineUI.replay()">▶ Replay</button>
            </div>`;
    }

    function replay() {
        if (!events.length) return;
        let i = 0;
        const step = () => {
            if (i >= events.length) return;
            const ev = events[i++];
            if (window.UIEnhancements) UIEnhancements.toast(`${ev.agent_name || ''} ${(ev.message || ev.type || '').slice(0, 40)}`, 'info');
            setTimeout(step, 400);
        };
        step();
    }

    global.TimelineUI = { load, replay };
})(window);
