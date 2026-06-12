/** Панель деятельности агента — артефакты, задачи, ревизии */
(function (global) {
    let overlay = null;

    async function open(agentId) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'agentActivityOverlay';
            overlay.className = 'activity-overlay';
            overlay.onclick = (e) => { if (e.target === overlay) close(); };
            document.body.appendChild(overlay);
        }
        overlay.innerHTML = '<div class="activity-card"><div class="panel-empty">Загрузка…</div></div>';
        overlay.style.display = 'flex';

        try {
            const r = await fetch(`/api/agents/${agentId}/activity`);
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            render(d);
        } catch (e) {
            overlay.innerHTML = `<div class="activity-card"><p class="panel-error">${e.message}</p><button class="btn-secondary" onclick="AgentActivity.close()">Закрыть</button></div>`;
        }
    }

    function render(data) {
        const a = data.agent || {};
        const caps = data.capabilities || {};
        const arts = data.artifacts || [];
        const tasks = data.recent_tasks || [];

        const skills = (caps.skills || []).map((s) => `<span class="skill-chip">${s}</span>`).join('');
        const artRows = arts.map((art) => `
            <div class="activity-artifact">
                <div class="aa-head">
                    <span class="aa-type">${art.type}</span>
                    <strong>${escape(art.title)}</strong>
                </div>
                <p class="aa-desc">${escape((art.description || '').slice(0, 120))}</p>
                <div class="aa-actions">
                    ${art.preview_html || art.type === 'presentation' || art.type === 'model_3d'
                        ? `<a href="/api/projects/${art.id}/preview" target="_blank" class="btn-secondary btn-sm">👁 Preview</a>` : ''}
                    <button type="button" class="btn-secondary btn-sm" onclick="AgentActivity.revise('${a.agent_id}','${art.id}')">✏️ Доработать</button>
                </div>
            </div>`).join('') || '<div class="panel-empty">Пока нет проектов — дайте задачу агенту</div>';

        const taskRows = tasks.slice(0, 8).map((t) => `
            <div class="activity-task ${t.status}">
                <span>${escape((t.task || '').slice(0, 60))}</span>
                <small>${t.status}</small>
            </div>`).join('') || '<div class="muted">Нет задач</div>';

        overlay.innerHTML = `
        <div class="activity-card">
            <div class="activity-header">
                <h2>${a.emoji || '🤖'} ${escape(a.name || '')} · ${escape(caps.label || a.role || '')}</h2>
                <button type="button" class="icon-btn" onclick="AgentActivity.close()">×</button>
            </div>
            <div class="activity-skills">${skills}</div>
            <div class="activity-stats">
                <span>📦 ${data.artifact_stats || 0} проектов</span>
                <span>💬 ${data.direct_chat_count || 0} сообщений</span>
                <span>📚 ${a.learned_count || 0} знаний</span>
            </div>
            <div class="activity-section">
                <h3>📦 Проекты и артефакты</h3>
                ${artRows}
            </div>
            <div class="activity-section">
                <h3>📋 Последние задачи</h3>
                ${taskRows}
            </div>
            <div class="activity-footer">
                <button type="button" class="btn-primary" onclick="AgentActivity.discuss('${a.agent_id}')">💬 Обсудить действия</button>
                <button type="button" class="btn-secondary" onclick="switchView('projects')">Все проекты</button>
            </div>
        </div>`;
    }

    function discuss(agentId) {
        close();
        if (window.openPrivateChat) openPrivateChat(agentId);
        if (window.UIEnhancements) UIEnhancements.toast('Напишите: «переделай …» или «дополни …»', 'info');
    }

    async function revise(agentId, artifactId) {
        const instruction = prompt('Что изменить или дополнить?');
        if (!instruction) return;
        try {
            const r = await fetch(`/api/agents/${agentId}/revise`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ artifact_id: artifactId, instruction }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            if (window.UIEnhancements) UIEnhancements.toast('✏️ Задача на доработку отправлена', 'success');
            close();
            if (typeof addSystemMessage === 'function') addSystemMessage(`✏️ ${d.task}`);
        } catch (e) {
            alert(e.message);
        }
    }

    function close() {
        if (overlay) overlay.style.display = 'none';
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.AgentActivity = { open, close, discuss, revise };
})(window);
