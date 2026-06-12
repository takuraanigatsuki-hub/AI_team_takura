/** Power Pack — memory, backup, pipeline, compare, cost, templates */
(function (global) {
    async function showMemory() {
        const r = await fetch('/api/project-memory', { credentials: 'same-origin' });
        const d = await r.json();
        const brief = prompt('Brief проекта (контекст для всех агентов):', d.brief || '');
        if (brief === null) return;
        const goals = prompt('Цели (через ;):', (d.goals || []).join('; '));
        await fetch('/api/project-memory', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brief, goals: (goals || '').split(';').map((s) => s.trim()).filter(Boolean), constraints: d.constraints || [] }),
        });
        if (window.UIEnhancements) UIEnhancements.toast('🧠 Project memory сохранена', 'success');
    }

    function downloadBackup() {
        window.open('/api/backup/download', '_blank');
        if (window.UIEnhancements) UIEnhancements.toast('📦 Backup скачивается', 'info');
    }

    async function runPipeline() {
        if (window.UIEnhancements) UIEnhancements.toast('🚀 Pipeline: Figma → React → Deploy…', 'info');
        try {
            const r = await fetch('/api/pipeline/full', { method: 'POST', credentials: 'same-origin' });
            const d = await r.json();
            if (d.ok && window.UIEnhancements) UIEnhancements.toast('✅ Pipeline запущен', 'success');
        } catch (e) {
            alert(e.message);
        }
    }

    async function compareProjects() {
        const idA = prompt('ID проекта A (из вкладки Проекты):');
        const idB = prompt('ID проекта B:');
        if (!idA || !idB) return;
        const r = await fetch(`/api/projects/${idA}/diff/${idB}`, { credentials: 'same-origin' });
        const d = await r.json();
        showDiffModal(d);
    }

    function showDiffModal(d) {
        let el = document.getElementById('diffOverlay');
        if (!el) {
            el = document.createElement('div');
            el.id = 'diffOverlay';
            el.className = 'activity-overlay';
            document.body.appendChild(el);
        }
        const diff = d.content_diff || {};
        el.innerHTML = `<div class="activity-card wide">
            <h2>Diff: ${escape(d.from?.title)} → ${escape(d.to?.title)}</h2>
            <p>+${diff.added || 0} / -${diff.removed || 0} lines</p>
            <div class="diff-view">${diff.html || ''}</div>
            <button class="btn-primary" onclick="document.getElementById('diffOverlay').style.display='none'">Закрыть</button>
        </div>`;
        el.style.display = 'flex';
    }

    async function loadCostWidget() {
        const el = document.getElementById('llmCostWidget');
        if (!el) return;
        try {
            const r = await fetch('/api/llm/usage');
            const d = await r.json();
            el.innerHTML = `LLM: ${d.total_requests || 0} req · ~$${d.estimated_cost_usd || 0} · ${d.estimated_cost_rub || 0}₽`;
        } catch (_) { el.textContent = 'LLM: —'; }
    }

    async function createViewLink() {
        const r = await fetch('/api/view-token', { method: 'POST' });
        const d = await r.json();
        if (d.url) {
            const full = location.origin + d.url;
            navigator.clipboard?.writeText(full);
            alert('View-only ссылка (72ч):\n' + full);
        }
    }

    async function voiceStandupRound() {
        const r = await fetch('/api/agents');
        const agents = (await r.json()).agents || [];
        const working = agents.filter((a) => a.artifact_count > 0 || a.status === 'working').slice(0, 5);
        if (!window.VoiceRoom?.speak) return;
        for (const a of working) {
            VoiceRoom.speak(`${a.name}. Статус: ${a.status}. Проектов: ${a.artifact_count || 0}.`);
            await sleep(3500);
        }
    }

    function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

    async function applyTemplate(id) {
        await fetch(`/api/artifact-templates/${id}/apply`, { method: 'POST' });
        if (typeof switchView === 'function') switchView('chat');
        if (window.UIEnhancements) UIEnhancements.toast('📋 Шаблон запущен', 'success');
    }

    async function createPR(artifactId) {
        const r = await fetch(`/api/projects/${artifactId}/create-pr`, { method: 'POST' });
        const d = await r.json();
        if (window.UIEnhancements) UIEnhancements.toast(d.git?.commit_url ? '🔗 PR/commit готов' : '📁 Сохранено в output/', 'success');
    }

    function escape(s) { return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }

    global.PowerPack = {
        showMemory, downloadBackup, runPipeline, compareProjects, loadCostWidget,
        createViewLink, voiceStandupRound, applyTemplate, createPR,
    };
})(window);
