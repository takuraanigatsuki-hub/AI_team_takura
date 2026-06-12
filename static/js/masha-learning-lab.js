/**
 * Лаборатория Маши — учебные проекты и чат оценок
 */
(function (global) {
    let cache = null;
    let activeTab = 'evals';

    function el(id) { return document.getElementById(id); }

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function formatTime(ts) {
        if (!ts) return '';
        try {
            return new Date(ts).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        } catch (_) {
            return '';
        }
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function agentLabel(ids) {
        if (!ids?.length) return '—';
        const map = { pm: '🎯', frontend: '🎨', backend: '⚙️', qa: '🧪', evaluator: '🎓' };
        return ids.map((id) => map[id] || id).join(' ');
    }

    function switchTab(tab) {
        activeTab = tab;
        document.querySelectorAll('.ml-tab[data-ml-tab]').forEach((b) => {
            b.classList.toggle('active', b.dataset.mlTab === tab);
        });
        el('mashaTabEvals')?.classList.toggle('hidden', tab !== 'evals');
        el('mashaTabTasks')?.classList.toggle('hidden', tab !== 'tasks');
        el('mashaTabSkills')?.classList.toggle('hidden', tab !== 'skills');
        el('mashaTabProjects')?.classList.toggle('hidden', tab !== 'projects');
        if (tab === 'skills') renderSkillMatrix();
    }

    async function renderSkillMatrix() {
        const box = el('mashaSkillMatrix');
        if (!box) return;
        try {
            const r = await fetch('/api/learning/skill-matrix', { credentials: 'same-origin' });
            const d = await r.json();
            box.innerHTML = (d.agents || []).map((a) =>
                `<div class="skill-bar-row"><span>${a.emoji} ${esc(a.name)}</span><div class="skill-bar"><div class="skill-bar-fill" style="width:${(a.average || 0) * 10}%"></div></div><strong>${a.average}/10 <small class="muted">(${a.count})</small></strong></div>`
            ).join('') || '<p class="muted">Пока нет оценок — Маша оценит после задач</p>';
        } catch (_) {
            box.innerHTML = '<p class="muted">Ошибка загрузки</p>';
        }
    }

    function setLoading(on) {
        el('mashaLabLoading')?.classList.toggle('hidden', !on);
    }

    async function load() {
        setLoading(true);
        try {
            const r = await fetch('/api/learning/masha-lab', { credentials: 'same-origin' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            cache = await r.json();
            render();
            hydrateEvalChat(cache.evaluations || []);
        } catch (e) {
            toast(e.message || 'Ошибка загрузки', 'error');
        } finally {
            setLoading(false);
        }
    }

    function render() {
        if (!cache) return;
        const s = cache.stats || {};
        const ev = cache.evaluator || { name: 'Маша', emoji: '🎓' };

        const statsEl = el('mashaStats');
        if (statsEl) {
            statsEl.innerHTML = `
                <div class="ml-stat"><span>${s.user_submissions || 0}</span><small>заданий</small></div>
                <div class="ml-stat"><span>${s.solo_projects || 0}</span><small>solo</small></div>
                <div class="ml-stat"><span>${s.collaborative_projects || 0}</span><small>совместн.</small></div>
                <div class="ml-stat"><span>${s.evaluations_count || 0}</span><small>оценок</small></div>
                <div class="ml-stat highlight"><span>${s.average_score || '—'}</span><small>средний</small></div>`;
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
                    <span class="ml-kind">${kind === 'collab' ? '🤝' : '👤'}</span>
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
            container.innerHTML = '<div class="panel-empty">Оценки появятся здесь</div>';
            return;
        }
        container.innerHTML = items.slice(0, 40).map((e) => `
            <article class="ml-eval-card">
                <div class="ml-eval-head">
                    <span>${esc(e.agent_emoji || '🤖')} ${esc(e.agent_name || e.agent_id)}</span>
                    <span class="ml-score">${e.score}/10</span>
                </div>
                <p class="ml-desc">${esc((e.feedback || e.task || '').slice(0, 280))}</p>
                <small class="muted">${esc(e.context || '')} · ${esc((e.created_at || '').slice(0, 16).replace('T', ' '))}</small>
            </article>`).join('');
    }

    function appendEvalMessage(data) {
        const container = el('mashaEvalChat');
        if (!container) return;
        container.querySelector('[data-masha-eval-welcome]')?.remove();

        const target = data.target_agent_name
            ? ` → ${data.target_agent_emoji || ''} ${data.target_agent_name}`.trim()
            : (data.target_agent ? ` → ${data.target_agent}` : '');

        const div = document.createElement('div');
        div.className = 'message learning-msg skill_evaluation masha-eval-msg';
        div.innerHTML = `
            <div class="msg-avatar">${data.agent_emoji || '🎓'}</div>
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name">${esc(data.agent_name || 'Маша')}${esc(target)}</span>
                    <span class="msg-time">${formatTime(data.timestamp)}</span>
                    <span class="learning-badge ml-score-badge">${data.score || '?'}/10</span>
                </div>
                <div class="msg-text">${esc(data.message || data.feedback || '')}</div>
            </div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function hydrateEvalChat(items) {
        const container = el('mashaEvalChat');
        if (!container || container.querySelector('.masha-eval-msg')) return;
        if (!items.length) return;
        container.querySelector('[data-masha-eval-welcome]')?.remove();
        items.slice(0, 30).reverse().forEach((e) => {
            appendEvalMessage({
                agent_id: 'evaluator',
                agent_name: 'Маша',
                agent_emoji: '🎓',
                target_agent: e.agent_id,
                target_agent_name: e.agent_name,
                target_agent_emoji: e.agent_emoji,
                score: e.score,
                message: e.feedback || e.task,
                feedback: e.feedback,
                timestamp: e.created_at,
                context: e.context,
            });
        });
    }

    function onEvalMessage(data) {
        appendEvalMessage(data);
        switchTab('evals');
        load();
    }

    function onMessage(data) {
        if (data.type === 'skill_evaluation') {
            onEvalMessage(data);
        } else if (data.type === 'learning_project') {
            load();
        }
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
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, description: desc, collaborative: collab }),
            });
            if (!r.ok) throw new Error('Ошибка отправки');
            toast('📚 Упражнение отправлено', 'success');
            if (el('mashaExerciseTitle')) el('mashaExerciseTitle').value = '';
            if (el('mashaExerciseDesc')) el('mashaExerciseDesc').value = '';
            switchTab('tasks');
            await load();
        } catch (e) {
            toast(e.message || 'Ошибка', 'error');
        }
    }

    global.MashaLearningLab = {
        load, submitExercise, switchTab, onMessage, onEvalMessage, appendEvalMessage,
    };
})(window);
