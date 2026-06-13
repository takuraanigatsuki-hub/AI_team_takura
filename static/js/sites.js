/** Готовые сайты — HTML из output/sites */
(function (global) {
    async function load() {
        const el = document.getElementById('sitesGrid');
        if (!el) return;
        el.innerHTML = global.UICore ? UICore.loadingState() : '<p class="muted">Загрузка…</p>';
        try {
            const r = await fetch('/api/sites', { credentials: 'same-origin' });
            if (!r.ok) throw new Error('Не удалось загрузить сайты');
            const d = await r.json();
            render(d.sites || [], el);
        } catch (e) {
            el.innerHTML = global.UICore
                ? UICore.errorState(e.message, { retryOnclick: 'SitesUI.load()' })
                : `<p class="panel-error">${e.message}</p>`;
        }
    }

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
        }[c]));
    }

    function render(sites, el) {
        const list = sites.filter((s) => s.id !== 'latest.html');
        if (!list.length) {
            el.innerHTML = global.UICore ? UICore.emptyState({
                icon: '🌐',
                title: 'Сайтов пока нет',
                text: 'Дайте задачу на landing или сайт — Соня соберёт HTML здесь',
                primaryLabel: 'Новая задача',
                primaryOnclick: "switchView('chat')",
            }) : '<p class="muted">Нет готовых сайтов</p>';
            return;
        }
        el.innerHTML = list.map((s) => `
            <article class="project-card site-card">
                <div class="pc-head">
                    <span class="pc-type">🌐 Сайт</span>
                    ${s.is_latest ? '<span class="pc-agent">★ latest</span>' : ''}
                </div>
                <h3 class="pc-title">${esc(s.title)}</h3>
                <p class="pc-desc muted">${esc(s.size_kb)} KB · ${esc((s.modified_at || '').slice(0, 16).replace('T', ' '))}</p>
                <div class="pc-actions">
                    <a href="${esc(s.url)}" target="_blank" rel="noopener" class="btn-primary btn-sm">Открыть</a>
                    <button type="button" class="btn-secondary btn-sm" onclick="SitesUI.preview('${esc(s.url)}')">👁 Preview</button>
                </div>
            </article>`).join('');
    }

    function preview(url) {
        window.open(url, '_blank', 'noopener');
    }

    global.SitesUI = { load, preview };
})(window);
