(function () {
    const $ = (id) => document.getElementById(id);
    let ws = null;

    async function api(path, opts) {
        const r = await fetch(path, { credentials: 'include', ...opts });
        if (!r.ok) {
            const t = await r.text();
            throw new Error(t || r.statusText);
        }
        const ct = r.headers.get('content-type') || '';
        return ct.includes('json') ? r.json() : r.text();
    }

    function showAuth(show) {
        $('mobAuth').classList.toggle('hidden', !show);
        $('mobShell').classList.toggle('hidden', show);
    }

    async function refreshSession() {
        try {
            const me = await api('/api/auth/me');
            if (!me?.user) {
                showAuth(true);
                return;
            }
            showAuth(false);
            $('mobUserLabel').textContent = me.user.name || me.user.username || me.user.email;
            await Promise.all([loadTasks(), loadAgents(), loadLearning()]);
            connectWs();
        } catch {
            showAuth(true);
        }
    }

    async function login(e) {
        e.preventDefault();
        $('mobAuthError').classList.add('hidden');
        try {
            await api('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    login: $('mobLogin').value.trim(),
                    password: $('mobPassword').value,
                }),
            });
            await refreshSession();
        } catch (err) {
            $('mobAuthError').textContent = 'Неверный логин или пароль';
            $('mobAuthError').classList.remove('hidden');
        }
    }

    async function logout() {
        try { await api('/api/auth/logout', { method: 'POST' }); } catch { /* ignore */ }
        if (ws) { ws.close(); ws = null; }
        showAuth(true);
    }

    function renderList(el, items, mapFn) {
        if (!items.length) {
            el.innerHTML = '<p class="mob-muted">Пока пусто</p>';
            return;
        }
        el.innerHTML = items.map(mapFn).join('');
    }

    async function loadTasks() {
        const data = await api('/api/tasks?limit=20');
        const tasks = data.tasks || data || [];
        renderList($('mobTasksList'), tasks.slice(0, 20), (t) => `
            <article class="mob-card">
                <h3>${esc(t.title || t.description || 'Задача')}</h3>
                <p>${esc(t.status || 'active')} · ${esc(t.agent_id || 'pm')}</p>
                ${t.download_url ? `<a class="mob-badge" href="${esc(t.download_url)}" target="_blank" rel="noopener">⬇ результат</a>` : ''}
            </article>`);
    }

    async function loadAgents() {
        const data = await api('/api/agents');
        const list = data.agents || data || [];
        renderList($('mobAgentsList'), list, (a) => `
            <article class="mob-card">
                <h3>${esc(a.emoji || '🤖')} ${esc(a.name || a.agent_id)}</h3>
                <p>${esc(a.status || 'idle')}${a.current_task ? ' · ' + esc(a.current_task) : ''}</p>
            </article>`);
    }

    async function loadLearning() {
        let projects = [];
        try {
            const data = await api('/api/learning/projects?limit=15');
            projects = data.projects || data || [];
        } catch {
            try {
                const s = await api('/api/sonya/projects?scope=studio');
                projects = s.projects || s || [];
            } catch { /* ignore */ }
        }
        renderList($('mobLearningList'), projects.slice(0, 15), (p) => `
            <article class="mob-card">
                <h3>${esc(p.title || 'Проект')}</h3>
                <p>${esc(p.status || 'draft')} · ${esc(p.source || p.agent_ids?.join(', ') || 'agent')}</p>
            </article>`);
    }

    async function sendTask() {
        const text = $('mobTaskInput').value.trim();
        if (!text) return;
        $('mobSendTask').disabled = true;
        try {
            await api('/api/task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, type: 'task' }),
            });
            $('mobTaskInput').value = '';
            appendLog('✅ Задача отправлена PM');
            await loadTasks();
        } catch (err) {
            appendLog('❌ ' + (err.message || 'Ошибка'));
        } finally {
            $('mobSendTask').disabled = false;
        }
    }

    function appendLog(msg) {
        const el = document.createElement('div');
        el.className = 'mob-log-item';
        el.textContent = msg;
        $('mobChatLog').prepend(el);
    }

    function connectWs() {
        if (ws) return;
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${proto}://${location.host}/ws`);
        ws.onmessage = (ev) => {
            try {
                const data = JSON.parse(ev.data);
                if (data.type === 'task_done' || data.type === 'agents_state') {
                    loadTasks();
                    loadAgents();
                }
            } catch { /* ignore */ }
        };
        ws.onclose = () => { ws = null; setTimeout(connectWs, 4000); };
    }

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function switchTab(tab) {
        document.querySelectorAll('.mob-tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
        ['tasks', 'agents', 'learning', 'chat'].forEach((t) => {
            $('mobPanel' + t.charAt(0).toUpperCase() + t.slice(1))?.classList.toggle('hidden', t !== tab);
            $('mobPanel' + t.charAt(0).toUpperCase() + t.slice(1))?.classList.toggle('active', t === tab);
        });
    }

    document.querySelectorAll('.mob-tab').forEach((b) => {
        b.addEventListener('click', () => switchTab(b.dataset.tab));
    });
    $('mobLoginForm')?.addEventListener('submit', login);
    $('mobLogout')?.addEventListener('click', logout);
    $('mobSendTask')?.addEventListener('click', sendTask);
    $('mobRefresh')?.addEventListener('click', refreshSession);

    refreshSession();
})();
