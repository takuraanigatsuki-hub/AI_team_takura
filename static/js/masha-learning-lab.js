/**
 * Лаборатория Маши — учебные проекты и оценки
 */
(function (global) {
    let cache = null;

    function el(id) { return document.getElementById(id); }

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function agentLabel(ids) {
        if (!ids?.length) return '—';
        const map = {
            pm: '🎯', frontend: '🎨', backend: '⚙️', qa: '🧪', evaluator: '🎓',
        };
        return ids.map((id) => map[id] || id).join(' ');
    }

    async function load() {
        const root = el('mashaLabRoot');
        if (root) root.innerHTML = '<div class="panel-empty">Загрузка…</div>';
        try {
            const r = await fetch('/api/learning/masha-lab');
            if (!r.ok) throw new Error('HTTP ' + r.status);
            cache = await r.json();
            render();
        } catch (e) {
            if (root) {
                root.innerHTML = `<div class="panel-error">${esc(e.message)}</div>`;
            }
        }
    }

    function render() {
        if (!cache) return;
        const s = cache.stats || {};
        const ev = cache.evaluator || { name: 'Маша', emoji: '🎓' };

        const statsEl = el('mashaStats');
        if (statsEl) {
            statsEl.innerHTML = `
                <div class="ml-stat"><span>${s.user_submissions || 0}</span><small>ваших заданий</small></div>
                <div class="ml-stat"><span>${s.solo_projects || 0}</span><small>solo проектов</small></div>
                <div class="ml-stat"><span>${s.collaborative_projects || 0}</span><small>совместных</small></div>
                <div class="ml-stat"><span>${s.evaluations_count || 0}</span><small>оценок</small></div>
                <div class="ml-stat highlight"><span>${s.average_score || '—'}</span><small>средний балл</small></div>`;
        }

        const badge = el('mashaAgentStatus');
        if (badge) badge.textContent = `${ev.emoji} ${ev.name} · Skill Evaluator`;

        renderList(el('mashaUserList'), cache.user_submissions || [], 'user');
        renderList(el('mashaSoloList'), cache.solo_projects || [], 'solo');
        renderList(el('mashaCollabList'), cache.collaborative_projects || [], 'collab');
        renderEvaluations(el('mashaEvalList'), cache.evaluations || []);
    }

    function renderList(container, items, kind) {
        if (!container) return;
        if (!items.length) {
            const empty = {
                user: 'Отправьте /learn или /practice в чате',
                solo: 'Агенты создадут проекты после практики',
                collab: 'Совместные проекты появятся после /collab',
            };
            container.innerHTML = `<div class="panel-empty">${empty[kind] || 'Пусто'}</div>`;
            return;
        }
        container.innerHTML = items.map((p) => `
            <article class="ml-card">
                <div class="ml-card-top">
                    <span class="ml-kind">${kind === 'collab' ? '🤝' : kind === 'user' ? '👤' : '👤'}</span>
                    <strong>${esc(p.title)}</strong>
                </div>
                <p class="ml-desc">${esc((p.description || '').slice(0, 220))}</p>
                <div class="ml-meta">
                    ${agentLabel(p.agent_ids)} · ${esc((p.created_at || '').slice(0, 16).replace('T', ' '))}
                    ${p.last_score ? ` · ⭐ ${p.last_score}/10` : ''}
                </div>
            </article>`).join('');
    }

    function renderEvaluations(container, items) {
        if (!container) return;
        if (!items.length) {
            container.innerHTML = '<div class="panel-empty">Маша оценит после практики агентов</div>';
            return;
        }
        container.innerHTML = items.map((e) => `
            <article class="ml-eval-card">
                <div class="ml-eval-head">
                    <span>${esc(e.agent_emoji || '🤖')} ${esc(e.agent_name || e.agent_id)}</span>
                    <span class="ml-score">${e.score}/10</span>
                </div>
                <p class="ml-desc">${esc((e.feedback || e.task || '').slice(0, 280))}</p>
                <small class="muted">${esc(e.context || '')} · ${esc((e.created_at || '').slice(0, 16).replace('T', ' '))}</small>
            </article>`).join('');
    }

    async function submitExercise() {
        const title = el('mashaExerciseTitle')?.value?.trim() || '';
        const desc = el('mashaExerciseDesc')?.value?.trim() || title;
        const collab = el('mashaExerciseCollab')?.checked || false;
        if (!desc) {
            toast('Введите тему упражнения', 'warn');
            return;
        }
        try {
            const r = await fetch('/api/learning/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description: desc, collaborative: collab }),
            });
            if (!r.ok) throw new Error('Ошибка отправки');
            toast('📚 Упражнение отправлено', 'success');
            if (el('mashaExerciseTitle')) el('mashaExerciseTitle').value = '';
            if (el('mashaExerciseDesc')) el('mashaExerciseDesc').value = '';
            await load();
        } catch (e) {
            toast(e.message || 'Ошибка', 'error');
        }
    }

    global.MashaLearningLab = { load, submitExercise, onMessage(data) {
        if (data.type === 'learning_project' || data.type === 'skill_evaluation') load();
    }};
})(window);
