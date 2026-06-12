/** WOW: Standup, Deploy, Presence, Figma Split */
(function (global) {
    let lastFigmaData = null;

    function setLastFigma(data) {
        lastFigmaData = data;
    }

    // ─── Presence ───
    function updatePresence(data) {
        const el = document.getElementById('presencePill');
        const n = data.count || 0;
        const text = n <= 1 ? '👤 вы' : `👥 ${n} в комнате`;
        if (el) {
            el.textContent = text;
            el.title = (data.visitors || []).map((v) => v.name).join(', ');
        }
        if (global.UICore) UICore.updateHeaderContext({ presence: n > 1 ? `${n} в комнате` : '' });
    }

    // ─── Standup ───
    async function showStandup() {
        let modal = document.getElementById('standupModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'standupModal';
            modal.className = 'modal-overlay';
            modal.onclick = (e) => { if (e.target === modal) modal.classList.remove('show'); };
            modal.innerHTML = `<div class="modal modal-wide standup-modal">
                <h2>📊 Standup · Виктор</h2>
                <div id="standupBody" class="standup-body">${global.UICore ? UICore.loadingState() : '<div class="panel-empty">Загрузка…</div>'}</div>
                <div class="modal-actions">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('standupModal').classList.remove('show')">Закрыть</button>
                    <button type="button" class="btn-primary" onclick="WowFeatures.refreshStandup()">Обновить</button>
                </div></div>`;
            document.body.appendChild(modal);
        }
        modal.classList.add('show');
        await refreshStandup();
    }

    async function refreshStandup() {
        const body = document.getElementById('standupBody');
        if (!body) return;
        if (body) body.innerHTML = global.UICore ? UICore.loadingState() : '<div class="dash-loading">Загрузка…</div>';
        try {
            const r = await fetch('/api/standup', { credentials: 'same-origin' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = await r.json();
            body.innerHTML = `<pre class="standup-text">${escapeHtml(d.narrative || '')}</pre>
                <div class="standup-stats">
                    <span>✅ ${d.completed_recent || 0} за час</span>
                    <span>⚡ ${d.active_count || 0} активных</span>
                </div>`;
        } catch (e) {
            body.innerHTML = global.UICore
                ? UICore.errorState(e.message, { retryOnclick: 'WowFeatures.refreshStandup()' })
                : `<div class="panel-error">${e.message}</div>`;
        }
    }

    // ─── Deploy ───
    async function deployNow() {
        if (window.UIEnhancements) UIEnhancements.toast('🚀 Сборка deploy bundle…', 'info');
        try {
            const r = await fetch('/api/deploy', { method: 'POST', credentials: 'same-origin' });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            if (window.SoundFX) SoundFX.deploy();
            if (window.UIEnhancements) {
                UIEnhancements.toast('🚀 Deploy готов — скачайте ZIP', 'success', 6000);
            }
            window.open(d.download_url, '_blank');
        } catch (e) {
            alert(e.message);
        }
    }

    // ─── Figma Split ───
    function toggleCompare() {
        const el = document.getElementById('figmaSplitView');
        if (!el) return;
        const on = el.classList.toggle('active');
        if (on) refreshCompare();
    }

    async function refreshCompare() {
        const img = document.getElementById('figmaSplitImg');
        const scoreEl = document.getElementById('figmaMatchScore');
        if (!lastFigmaData) {
            if (scoreEl) scoreEl.textContent = 'Импортируйте Figma на вкладке Design';
            return;
        }
        if (img && lastFigmaData.preview_url) img.src = lastFigmaData.preview_url;
        const figmaColors = lastFigmaData.summary?.colors || lastFigmaData.colors || [];
        const reactColors = extractReactColors();
        try {
            const r = await fetch('/api/figma/compare', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ figma_colors: figmaColors, react_colors: reactColors }),
            });
            const d = await r.json();
            if (scoreEl) {
                scoreEl.innerHTML = `<span class="match-score">${d.score}%</span> ${d.message || ''}
                    <div class="match-pairs">${(d.pairs || []).map((p) =>
                        `<span class="pair"><i style="background:${p.figma}"></i>→<i style="background:${p.react}"></i></span>`
                    ).join('')}</div>`;
            }
        } catch (_) {}
    }

    function extractReactColors() {
        const defaults = ['#6c63ff', '#1a1d2e', '#f0f0f5', '#5ecf8a', '#fff'];
        const code = document.getElementById('reactPreviewCode')?.textContent || '';
        const found = code.match(/#[0-9a-fA-F]{6}/g) || [];
        return [...new Set([...found, ...defaults])].slice(0, 12);
    }

    async function improveFromFigma() {
        try {
            const r = await fetch('/api/figma/improve', { method: 'POST', credentials: 'same-origin' });
            if (!r.ok) throw new Error((await r.json()).detail);
            if (window.UIEnhancements) UIEnhancements.toast('🎨 Соня дорабатывает по Figma…', 'info');
            if (typeof switchView === 'function') switchView('chat');
        } catch (e) { alert(e.message); }
    }

    function escapeHtml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    global.WowFeatures = {
        setLastFigma, updatePresence, showStandup, refreshStandup,
        deployNow, toggleCompare, refreshCompare, improveFromFigma,
    };
})(window);
