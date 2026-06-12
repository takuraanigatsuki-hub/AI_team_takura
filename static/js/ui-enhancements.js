/**
 * UI: toasts, footer status, command palette, keyboard shortcuts
 */
(function (global) {
    const SHORTCUTS = [
        { keys: 'Ctrl+1', action: () => switchView('studio'), label: '3D Студия' },
        { keys: 'Ctrl+2', action: () => switchView('chat'), label: 'Рабочий чат' },
        { keys: 'Ctrl+3', action: () => {
            if (global.Auth?.canViewAgentLearning?.(global.Auth.getUser())) switchView('agent-learning');
        }, label: 'Обучение агентов (admin)' },
        { keys: 'Ctrl+4', action: () => switchView('tasks'), label: 'Задачи' },
        { keys: 'Ctrl+5', action: () => switchView('dashboard'), label: 'Dashboard' },
        { keys: 'Ctrl+K', action: () => toggleCommandPalette(), label: 'Командная палитра' },
        { keys: 'Ctrl+Shift+F', action: () => { if (window.SiteSearch) SiteSearch.open(); }, label: 'Поиск по сайту' },
        { keys: 'Ctrl+/', action: () => toggleShortcutsHelp(), label: 'Справка' },
    ];

    function ensureContainers() {
        if (!document.getElementById('toastContainer')) {
            const t = document.createElement('div');
            t.id = 'toastContainer';
            t.className = 'toast-container';
            document.body.appendChild(t);
        }
        if (!document.getElementById('statusFooter')) {
            const f = document.createElement('footer');
            f.id = 'statusFooter';
            f.className = 'status-footer';
            f.innerHTML = `
                <span id="footerGit">Git: …</span>
                <span id="footerGithub">Cloud: …</span>
                <span id="footerAgents">Агенты: …</span>
                <span class="footer-spacer"></span>
                <span id="footerRepo" class="muted"></span>
                <button type="button" class="footer-link" onclick="UIEnhancements.syncNow()">📤 Sync</button>`;
            document.body.appendChild(f);
        }
    }

    function toast(message, type = 'info', duration = 4000) {
        ensureContainers();
        const el = document.createElement('div');
        el.className = `toast toast-${type} animate-in`;
        el.textContent = message;
        document.getElementById('toastContainer').appendChild(el);
        setTimeout(() => {
            el.classList.add('toast-out');
            setTimeout(() => el.remove(), 300);
        }, duration);
    }

    async function refreshFooter() {
        ensureContainers();
        try {
            const [gitR, cursorR, cfgR] = await Promise.all([
                fetch('/api/git/status'),
                fetch('/api/cursor/status'),
                fetch('/api/config'),
            ]);
            const git = gitR.ok ? await gitR.json() : {};
            const cursor = cursorR.ok ? await cursorR.json() : {};
            const cfg = cfgR.ok ? await cfgR.json() : {};

            const gitEl = document.getElementById('footerGit');
            if (gitEl) {
                if (git.changed_files > 0) {
                    gitEl.textContent = `Git: ${git.changed_files} изменений`;
                    gitEl.className = 'footer-warn';
                } else if (git.last_sync_at) {
                    gitEl.textContent = `Git: ✓ ${new Date(git.last_sync_at).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}`;
                    gitEl.className = 'footer-ok';
                } else {
                    gitEl.textContent = 'Git: синхронизирован';
                    gitEl.className = '';
                }
            }

            const ghEl = document.getElementById('footerGithub');
            if (ghEl) {
                ghEl.textContent = cursor.github_sync && cursor.repo_url
                    ? `Cloud: ${cursor.active_agents?.length || 0} active`
                    : 'Cloud: off';
            }

            const repoEl = document.getElementById('footerRepo');
            if (repoEl && cfg.cursor_repo_url) {
                const short = cfg.cursor_repo_url.replace('https://github.com/', '');
                repoEl.textContent = short;
            }
        } catch (_) {}
    }

    function updateAgentFooter(count) {
        const el = document.getElementById('footerAgents');
        if (el) el.textContent = `Агенты: ${count} активны`;
    }

    async function syncNow() {
        toast('Синхронизация с GitHub…', 'info');
        try {
            const r = await fetch('/api/git/sync', { method: 'POST' });
            const d = await r.json();
            if (d.action === 'pushed') toast(`📤 ${d.commit} → ${d.branch}`, 'success');
            else if (d.action === 'skip') toast('Нет изменений', 'info');
            else toast(d.error || 'Ошибка sync', 'error');
            refreshFooter();
        } catch (e) {
            toast('Ошибка: ' + e.message, 'error');
        }
    }

    function toggleCommandPalette() {
        if (global.FeaturePack?.openCommandPalette) {
            global.FeaturePack.openCommandPalette();
            return;
        }
        let pal = document.getElementById('commandPalette');
        if (pal) {
            pal.remove();
            return;
        }
        pal = document.createElement('div');
        pal.id = 'commandPalette';
        pal.className = 'command-palette-overlay';
        pal.onclick = (e) => { if (e.target === pal) pal.remove(); };
        const actions = [
            { label: '📋 Новая задача всей команде', run: () => { switchView('chat'); document.getElementById('messageInput')?.focus(); } },
            { label: '🎨 React Preview', run: () => { if (window.ReactPreview) ReactPreview.toggle(); } },
            { label: '⚡ Cursor Panel', run: () => { if (window.Integrations) Integrations.toggleCursorPanel(); } },
            { label: '📊 Dashboard', run: () => switchView('dashboard') },
            { label: '📥 Export задач', run: () => { switchView('tasks'); if (window.exportTasks) exportTasks(); } },
            { label: '📊 Standup', run: () => WowFeatures.showStandup() },
            { label: '🚀 Deploy ZIP', run: () => WowFeatures.deployNow() },
            { label: '📤 Sync GitHub', run: syncNow },
            { label: '⚙️ Настройки', run: () => showSettings() },
            { label: '🌓 Сменить тему', run: () => toggleTheme() },
        ];
        pal.innerHTML = `
            <div class="command-palette">
                <input type="text" id="cmdSearch" placeholder="Команда или действие…" autofocus>
                <div class="cmd-list" id="cmdList">${actions.map((a, i) =>
                    `<button type="button" class="cmd-item" data-i="${i}">${a.label}</button>`
                ).join('')}</div>
            </div>`;
        document.body.appendChild(pal);
        const items = actions;
        pal.querySelectorAll('.cmd-item').forEach((btn) => {
            btn.onclick = () => { items[+btn.dataset.i].run(); pal.remove(); };
        });
        const search = pal.querySelector('#cmdSearch');
        search?.addEventListener('input', () => {
            const q = search.value.toLowerCase();
            pal.querySelectorAll('.cmd-item').forEach((btn, i) => {
                btn.style.display = items[i].label.toLowerCase().includes(q) ? '' : 'none';
            });
        });
        search?.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') pal.remove();
        });
    }

    function toggleShortcutsHelp() {
        if (global.FeaturePack?.showShortcutsModal) {
            global.FeaturePack.showShortcutsModal();
            return;
        }
        toast('Ctrl+1-6 вкладки · Ctrl+K палитра · Ctrl+G/Ctrl+Shift+F поиск · Enter+Ctrl отправить', 'info', 6000);
    }

    function bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key >= '1' && e.key <= '6') {
                e.preventDefault();
                const views = ['studio', 'chat', 'tasks', 'dashboard'];
                switchView(views[+e.key - 1]);
            }
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                toggleCommandPalette();
            }
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                toggleShortcutsHelp();
            }
            if (e.ctrlKey && e.key === 'f') {
                e.preventDefault();
                switchView('chat');
                document.getElementById('chatSearch')?.focus();
            }
            if (e.ctrlKey && e.key === 'Enter') {
                const inp = document.getElementById('messageInput');
                if (document.activeElement === inp) {
                    e.preventDefault();
                    sendMessage();
                }
            }
        });
    }

    function init() {
        ensureContainers();
        bindKeyboard();
        refreshFooter();
        setInterval(refreshFooter, 30000);
    }

    global.UIEnhancements = {
        toast,
        refreshFooter,
        updateAgentFooter,
        syncNow,
        togglePalette: toggleCommandPalette,
        init,
        onGitSync(data) {
            toast(data.message?.slice(0, 80) || '📤 GitHub sync', 'success');
            refreshFooter();
        },
    };
})(window);
