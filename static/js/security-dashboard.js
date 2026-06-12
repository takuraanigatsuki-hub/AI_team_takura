/**
 * Security Dashboard — для Admin
 */
(function (global) {
    let cache = null;

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    async function load() {
        const el = document.getElementById('securityDashboard');
        if (!el) return cache;
        el.innerHTML = global.UICore ? UICore.loadingState('Загрузка security…') : '<div class="dash-loading">Загрузка security…</div>';
        try {
            const r = await fetch('/api/security/dashboard', { credentials: 'same-origin' });
            if (r.status === 403 || r.status === 401) {
                el.innerHTML = global.UICore ? UICore.emptyState({
                    icon: '🔒',
                    title: 'Доступ ограничен',
                    text: 'Security dashboard доступен только администратору',
                }) : '<div class="panel-empty">🔒 Доступ только для администратора</div>';
                return cache;
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            cache = await r.json();
            render(el);
        } catch (e) {
            el.innerHTML = global.UICore
                ? UICore.errorState(e.message, { retryOnclick: 'SecurityDashboard.load()' })
                : `<div class="panel-empty">⚠️ ${esc(e.message)}</div>`;
        }
        return cache;
    }

    function render(el) {
        if (!cache) return;
        const st = cache.stats || {};
        const audit = cache.audit_stats || {};
        el.innerHTML = `
            <div class="sec-kpis">
                <article class="ucard ucard-kpi"><span class="ucard-kpi-val">${st.blocked_now || 0}</span><span>IP заблокировано</span></article>
                <article class="ucard ucard-kpi"><span class="ucard-kpi-val">${st.total_events || 0}</span><span>Событий</span></article>
                <article class="ucard ucard-kpi"><span class="ucard-kpi-val">${audit.last_24h || 0}</span><span>Audit / 24ч</span></article>
            </div>
            <h4>🛡 Заблокированные IP</h4>
            <div class="ucard-list">${(cache.blocked_ips || []).map((b) =>
                `<article class="ucard ucard-row"><code>${esc(b.ip)}</code><span class="muted">${esc(b.reason || '')}</span>
                <button type="button" class="btn-secondary btn-xs" onclick="SecurityDashboard.unblock('${esc(b.ip)}')">Разблок</button></article>`
            ).join('') || '<p class="muted">Нет блокировок</p>'}</div>
            <h4>⚠️ Последние угрозы</h4>
            <div class="sec-events">${(cache.recent_events || []).map((e) =>
                `<div class="sec-event sev-${esc(e.severity)}"><strong>${esc(e.threat_type)}</strong> · ${esc(e.ip)} · ${esc(e.path)}<br><small>${esc(e.detail)}</small></div>`
            ).join('') || '<p class="muted">Чисто</p>'}</div>
            <h4>📜 Audit log</h4>
            <div class="sec-events">${(cache.audit_recent || []).slice(0, 20).map((e) =>
                `<div class="sec-event"><strong>${esc(e.action)}</strong> · ${esc(e.ip)} <small>${esc(e.timestamp?.slice(11, 19))}</small></div>`
            ).join('')}</div>`;
    }

    async function unblock(ip) {
        await fetch('/api/security/unblock/' + encodeURIComponent(ip), { method: 'POST', credentials: 'same-origin' });
        await load();
    }

    global.SecurityDashboard = { load, unblock };
})(window);
