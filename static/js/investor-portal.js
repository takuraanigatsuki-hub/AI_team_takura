/**
 * Investor Portal — метрики, pitch, skill matrix
 */
(function (global) {
    let cache = null;

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    async function load() {
        const grid = document.getElementById('investorGrid');
        if (grid) grid.innerHTML = '<div class="dash-loading">Загрузка investor dashboard…</div>';
        try {
            const r = await fetch('/api/investor/dashboard', { credentials: 'same-origin' });
            if (r.status === 401 || r.status === 403) {
                if (grid) grid.innerHTML = `<div class="tasks-empty tasks-guest"><div class="tasks-empty-icon">🔐</div>
                    <h3>Investor Portal</h3><p class="muted">Нужен вход с ролью investor или admin</p>
                    <a href="/?auth=login" class="btn-primary btn-sm">Войти</a></div>`;
                return;
            }
            if (!r.ok) throw new Error('HTTP ' + r.status);
            cache = await r.json();
            render();
        } catch (e) {
            if (grid) grid.innerHTML = `<div class="panel-empty">⚠️ ${esc(e.message)}</div>`;
        }
    }

    function kpi(val, label, hint) {
        return `<article class="ucard ucard-kpi"><span class="ucard-kpi-val">${esc(val)}</span><span class="ucard-kpi-label">${esc(label)}</span>${hint ? `<small class="muted">${esc(hint)}</small>` : ''}</article>`;
    }

    function render() {
        const grid = document.getElementById('investorGrid');
        if (!grid || !cache) return;
        const m = cache.metrics || {};
        grid.innerHTML = `
            <header class="investor-hero">
                <h2>💼 Investor Portal</h2>
                <p class="muted">Live metrics · AI team performance · read-only</p>
                <button type="button" class="btn-secondary btn-sm hidden" id="investorDigestBtn" onclick="InvestorPortal.sendDigest()">📧 Send digest</button>
            </header>
            <div class="ucard-grid">${[
                kpi(m.tasks_completed, 'Задач выполнено'),
                kpi(m.tasks_active, 'В работе'),
                kpi(m.agents_active + '/' + m.agents_count, 'Агентов активно'),
                kpi(m.average_score || '—', 'Средняя оценка Маши'),
                kpi(m.evaluations, 'Оценок навыков'),
            ].join('')}</div>
            <section class="ucard-section">
                <h3>🤖 Команда</h3>
                <div class="ucard-grid ucard-grid-agents">${(cache.agents || []).map((a) =>
                    `<article class="ucard"><span class="ucard-emoji">${a.emoji}</span><strong>${esc(a.name)}</strong><span class="ucard-badge">${esc(a.status)}</span></article>`
                ).join('')}</div>
            </section>
            <section class="ucard-section">
                <h3>📈 Skill Matrix</h3>
                <div class="skill-bars">${(cache.skill_matrix?.agents || []).map((a) =>
                    `<div class="skill-bar-row"><span>${a.emoji} ${esc(a.name)}</span><div class="skill-bar"><div class="skill-bar-fill" style="width:${(a.average || 0) * 10}%"></div></div><strong>${a.average}/10</strong></div>`
                ).join('') || '<p class="muted">Пока нет оценок</p>'}</div>
            </section>
            <section class="ucard-section">
                <h3>📋 Последние задачи</h3>
                <div class="ucard-list">${(cache.recent_tasks || []).slice(0, 8).map((t) =>
                    `<article class="ucard ucard-row"><strong>${esc((t.task || t.title || '').slice(0, 60))}</strong><span class="ucard-badge">${esc(t.status)}</span></article>`
                ).join('') || '<p class="muted">Нет задач</p>'}</div>
            </section>`;
    }

    global.InvestorPortal = { load, render };

    async function sendDigest() {
        try {
            const r = await fetch('/api/investor/digest', { method: 'POST', credentials: 'same-origin' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            if (global.UIEnhancements) UIEnhancements.toast('Digest отправлен в уведомления', 'success');
        } catch (e) {
            if (global.UIEnhancements) UIEnhancements.toast(e.message, 'error');
        }
    }
    global.InvestorPortal.sendDigest = sendDigest;
})(window);
