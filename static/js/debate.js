/** Agent debates — Architect vs Reviewer */
(function (global) {
    function show(data) {
        const rounds = data.rounds || [];
        if (!rounds.length) return;
        let overlay = document.getElementById('debateOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'debateOverlay';
            overlay.className = 'debate-overlay';
            document.body.appendChild(overlay);
        }
        const rows = rounds.map((r) => `
            <div class="debate-round">
                <div class="debate-agent">${r.agent_emoji || ''} ${r.agent_name || r.agent_id}</div>
                <div class="debate-msg">${escape(r.message || '')}</div>
            </div>`).join('');
        overlay.innerHTML = `
            <div class="debate-card">
                <h3>⚔️ Debate: ${escape((data.topic || '').slice(0, 60))}</h3>
                ${rows}
                <button type="button" class="btn-primary btn-sm" onclick="DebateUI.close()">Понятно</button>
            </div>`;
        overlay.style.display = 'flex';
        if (window.SoundFX?.taskDone) SoundFX.taskDone();
    }

    function close() {
        const el = document.getElementById('debateOverlay');
        if (el) el.style.display = 'none';
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.DebateUI = { show, close };
})(window);
