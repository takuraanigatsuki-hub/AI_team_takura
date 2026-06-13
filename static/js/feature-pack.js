/**
 * Feature Pack — команды и аккуратный UI (без перегруза шапки)
 */
(function (global) {
    const STORAGE = 'ai-team-fp-v2';
    const sw = (view) => { if (global.switchView) global.switchView(view); };

    const VIEWS = [
        { id: 'tasks', label: '📋 Inbox' },
        { id: 'chat', label: '💬 Чат' },
        { id: 'kanban', label: '📌 Kanban' },
        { id: 'dashboard', label: '📊 Dashboard' },
        { id: 'projects', label: '📦 Проекты' },
        { id: 'studio', label: '🎮 3D Студия' },
        { id: 'sonya-studio', label: '✨ Studio' },
        { id: 'sprint', label: '🏃 Sprint' },
        { id: 'timeline', label: '⏱ Timeline' },
        { id: 'profile', label: '👤 Кабинет' },
    ];

    let prefs = loadPrefs();
    let notifications = [];
    let unreadCount = 0;
    let sessionStart = Date.now();
    let currentView = 'tasks';
    let dailyGoal = { target: 5, done: 0, _last: 0 };
    let konamiStep = 0;
    const KONAMI = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

    function loadPrefs() {
        try {
            return { ...defaults(), ...JSON.parse(localStorage.getItem(STORAGE) || '{}') };
        } catch (_) {
            return defaults();
        }
    }

    function defaults() {
        return {
            ambient: false,
            particles: false,
            focusMode: false,
            compact: false,
            accent: 'purple',
        };
    }

    function savePrefs() {
        localStorage.setItem(STORAGE, JSON.stringify(prefs));
        applyPrefs();
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function pushNotify(title, body) {
        notifications.unshift({
            id: Date.now(),
            title,
            body: String(body || '').slice(0, 120),
            time: new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
            unread: true,
        });
        notifications = notifications.slice(0, 30);
        unreadCount++;
        updateNotifyBadge();
    }

    function updateNotifyBadge() {
        const b = document.getElementById('fpNotifyBadge');
        if (!b) return;
        b.textContent = unreadCount > 9 ? '9+' : String(unreadCount);
        b.style.display = unreadCount ? 'grid' : 'none';
    }

    function quickTask(target, text) {
        sw('chat');
        const sel = document.getElementById('targetSelect');
        if (sel) sel.value = target;
        const inp = document.getElementById('messageInput');
        if (inp) { inp.value = text; inp.focus(); }
        if (global.setMsgType) setMsgType('task');
    }

    function getCommands() {
        const go = (v) => () => sw(v);
        const all = [
            { label: '📋 Inbox', run: go('tasks') },
            { label: '💬 Рабочий чат', run: go('chat') },
            { label: '📌 Kanban', run: go('kanban') },
            { label: '📊 Dashboard', run: go('dashboard') },
            { label: '💼 Investor Portal', run: go('investor') },
            { label: '📋 Новая задача', run: () => { go('chat')(); if (global.setMsgType) setMsgType('task'); document.getElementById('messageInput')?.focus(); } },
            { label: '📋 Шаблон задачи', run: () => { go('tasks')(); global.TaskTemplates?.showPicker?.(); } },
            { label: '📦 Проекты', run: go('projects') },
            { label: '🏃 Sprint', run: go('sprint') },
            { label: '⏱ Timeline', run: go('timeline') },
            { label: '🎮 3D Студия', run: go('studio') },
            { label: '✨ Sonya Studio', run: go('sonya-studio') },
            { label: '👤 Кабинет', run: go('profile') },
            { label: '🎯 PM — спринт', run: () => quickTask('pm', 'Спланируй спринт на неделю') },
            { label: '🎨 Landing page', run: () => quickTask('frontend', 'Сделай современный landing page') },
            { label: '⚙️ REST API', run: () => quickTask('backend', 'Создай REST API для основных сущностей') },
            { label: '🧪 Тесты', run: () => quickTask('qa', 'Напиши тест-план и автотесты') },
            { label: '⚡ Cursor SDK', run: () => global.Integrations?.toggleCursorPanel?.() },
            { label: '🎨 React Preview', run: () => global.ReactPreview?.toggle?.() },
            { label: '⚡ Pipeline', run: () => global.PowerPack?.runPipeline?.() },
            { label: '📊 Standup', run: () => global.WowFeatures?.showStandup?.() },
            { label: '🚀 Deploy', run: () => global.WowFeatures?.deployNow?.() },
            { label: '📡 Лента событий', run: () => global.UICore?.toggleActivityPanel?.() },
            { label: '🔍 Поиск', run: openGlobalSearch },
            { label: '🎯 Фокус-режим', run: toggleFocusMode },
            { label: '📐 Компактный UI', run: toggleCompact },
            { label: '🌓 Тема', run: () => global.toggleTheme?.() },
            { label: '📥 Export задач', run: () => { go('tasks')(); global.exportTasks?.(); } },
            { label: '📄 Export чата', run: exportChat },
            { label: '⌨️ Горячие клавиши', run: showShortcutsModal },
        ];
        return global.UIAccess?.filterCommands ? UIAccess.filterCommands(all) : all;
    }

    function setupChrome() {
        if (!document.getElementById('fpScrollProgress')) {
            const bar = document.createElement('div');
            bar.id = 'fpScrollProgress';
            document.body.prepend(bar);
        }

        if (!document.getElementById('fpFab')) {
            const fab = document.createElement('button');
            fab.type = 'button';
            fab.id = 'fpFab';
            fab.className = 'fp-fab support-fab hidden';
            fab.title = 'Поддержка';
            fab.textContent = '💬';
            fab.setAttribute('aria-label', 'Поддержка');
            fab.onclick = () => {
                if (global.SupportTickets?.open) SupportTickets.open();
                else if (global.UIEnhancements) UIEnhancements.toast('Поддержка загружается…', 'info');
            };
            document.body.appendChild(fab);
        }

        extendFooter();
    }

    function extendFooter() {
        const footer = document.getElementById('statusFooter');
        if (!footer || document.getElementById('fpFooterMeta')) return;
        const meta = document.createElement('span');
        meta.id = 'fpFooterMeta';
        meta.className = 'fp-footer-meta';
        footer.insertBefore(meta, footer.querySelector('.footer-spacer'));
    }

    function updateFooterMeta(stats) {
        const el = document.getElementById('fpFooterMeta');
        if (!el) return;
        let s = stats;
        if ((!s?.total && s?.total !== 0) && global.AITeamTasks?.getSnapshot) {
            s = global.AITeamTasks.getSnapshot().stats || s;
        }
        const pct = s?.total ? Math.round((s.completed / s.total) * 100) : 0;
        const awaiting = s?.awaiting_approval || 0;
        const mins = Math.floor((Date.now() - sessionStart) / 60000);
        el.textContent = awaiting
            ? `⏳ ${awaiting} на проверке · ${mins}м`
            : `Задачи ${pct}% · ${mins}м в комнате`;
    }

    function updateFabVisibility(view) {
        currentView = view || currentView;
        const fab = document.getElementById('fpFab');
        if (!fab) return;
        const show = ['chat', 'tasks', 'kanban', 'dashboard', 'projects', 'profile'].includes(currentView);
        fab.classList.toggle('hidden', !show);
    }

    function openGlobalSearch() {
        openCommandPalette();
    }

    let _paletteSearchTimer = null;
    let _paletteSearchAbort = null;

    async function fetchPaletteSearch(query, container) {
        if (_paletteSearchAbort) _paletteSearchAbort.abort();
        if (!query || query.length < 2) {
            container.innerHTML = '';
            container.classList.add('hidden');
            return;
        }
        container.classList.remove('hidden');
        container.innerHTML = '<div class="cmd-section-label">Найденное</div><div class="cmd-search-hint">Поиск…</div>';
        _paletteSearchAbort = new AbortController();
        try {
            const r = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=8`, {
                credentials: 'same-origin',
                signal: _paletteSearchAbort.signal,
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            const d = await r.json();
            const results = d.results || [];
            if (!results.length) {
                container.innerHTML = '<div class="cmd-section-label">Найденное</div><div class="cmd-search-hint">Ничего не найдено</div>';
                return;
            }
            const TYPE_LABELS = { task: '📋', project: '📦', message: '💬', learning: '📚', sonya: '✨' };
            container.innerHTML = '<div class="cmd-section-label">Найденное</div>' + results.map((item, i) =>
                `<button type="button" class="cmd-item cmd-item-search" data-si="${i}">${TYPE_LABELS[item.type] || '·'} ${item.title || item.snippet || ''}</button>`
            ).join('');
            container.querySelectorAll('.cmd-item-search').forEach((btn) => {
                btn.onclick = () => {
                    document.getElementById('commandPalette')?.remove();
                    if (global.SiteSearch) {
                        global.SiteSearch.close?.();
                        global.switchView?.(results[+btn.dataset.si].view);
                        const res = results[+btn.dataset.si];
                        setTimeout(() => {
                            if (res.view === 'sonya-studio' && res.id && global.SonyaStudio?.openProject) {
                                SonyaStudio.openProject(res.id);
                            }
                        }, 100);
                    }
                };
            });
        } catch (e) {
            if (e.name !== 'AbortError') {
                container.innerHTML = '<div class="cmd-section-label">Найденное</div><div class="cmd-search-hint">Ошибка поиска</div>';
            }
        }
    }

    function openCommandPalette() {
        document.getElementById('fpSearchOverlay')?.remove();
        const existing = document.getElementById('commandPalette');
        if (existing) { existing.remove(); return; }

        const commands = getCommands().filter((c) => c.label !== '🔍 Поиск');
        const pal = document.createElement('div');
        pal.id = 'commandPalette';
        pal.className = 'command-palette-overlay';
        pal.onclick = (e) => { if (e.target === pal) pal.remove(); };
        pal.innerHTML = `
            <div class="command-palette">
                <div class="command-palette-head">
                    <span class="command-palette-icon" aria-hidden="true">⌘</span>
                    <input type="search" id="cmdSearch" placeholder="Раздел, команда или поиск…" autofocus>
                    <kbd class="command-palette-kbd">Esc</kbd>
                </div>
                <div class="cmd-search-section hidden" id="cmdSearchSection"></div>
                <div class="cmd-section-label" id="cmdActionsLabel">Действия</div>
                <div class="cmd-list" id="cmdList">${commands.map((a, i) =>
                    `<button type="button" class="cmd-item" data-i="${i}">${a.label}</button>`
                ).join('')}</div>
            </div>`;
        document.body.appendChild(pal);

        const runCmd = (idx) => { commands[idx].run(); pal.remove(); };
        pal.querySelectorAll('.cmd-item:not(.cmd-item-search)').forEach((btn) => {
            btn.onclick = () => runCmd(+btn.dataset.i);
        });

        const search = pal.querySelector('#cmdSearch');
        const list = pal.querySelector('#cmdList');
        const searchSection = pal.querySelector('#cmdSearchSection');
        const actionsLabel = pal.querySelector('#cmdActionsLabel');

        const filterCommands = (q) => {
            let visible = 0;
            pal.querySelectorAll('#cmdList .cmd-item').forEach((btn, i) => {
                const show = !q || commands[i].label.toLowerCase().includes(q);
                btn.style.display = show ? '' : 'none';
                if (show) visible++;
            });
            actionsLabel.style.display = visible ? '' : 'none';
            list.style.display = visible ? '' : 'none';
        };

        search?.addEventListener('input', () => {
            const q = search.value.trim().toLowerCase();
            filterCommands(q);
            clearTimeout(_paletteSearchTimer);
            _paletteSearchTimer = setTimeout(() => fetchPaletteSearch(search.value.trim(), searchSection), 200);
        });
        search?.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') pal.remove();
            if (e.key === 'Enter') {
                const first = searchSection.querySelector('.cmd-item-search:not([style*="none"])')
                    || list.querySelector('.cmd-item:not([style*="none"])');
                first?.click();
            }
        });
    }

    function toggleNotifyPanel() {
        const existing = document.getElementById('fpNotifyPanel');
        if (existing) { existing.remove(); return; }
        unreadCount = 0;
        updateNotifyBadge();
        const panel = document.createElement('div');
        panel.id = 'fpNotifyPanel';
        panel.className = 'fp-notify-panel';
        const esc = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        panel.innerHTML = `
            <div class="fp-notify-head"><span>Уведомления</span><button type="button" class="icon-btn" id="fpNotifyClose">×</button></div>
            <div id="fpNotifyList">${notifications.length
                ? notifications.map((n, i) => `<button type="button" class="fp-notify-item${n.unread ? ' unread' : ''}" data-idx="${i}">
                    <strong>${esc(n.title)}</strong><span>${esc(n.body)}</span><div class="fp-notify-time">${esc(n.time)}</div>
                </button>`).join('')
                : '<div class="fp-search-empty">Пока пусто</div>'}</div>`;
        document.body.appendChild(panel);
        panel.querySelector('#fpNotifyClose').onclick = () => panel.remove();
        panel.querySelectorAll('.fp-notify-item').forEach((btn) => {
            btn.onclick = async () => {
                const n = notifications[+btn.dataset.idx];
                if (n?.serverId) {
                    await fetch('/api/notifications/read', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: n.serverId }),
                    }).catch(() => {});
                }
                n.unread = false;
                panel.remove();
                if (n?.link?.includes('tasks') || n?.title?.includes('проверке')) {
                    sw('tasks');
                } else if (n?.link?.includes('investor')) {
                    sw('investor');
                } else {
                    sw('tasks');
                }
            };
        });
        notifications.forEach((n) => { n.unread = false; });
    }

    function showShortcutsModal() {
        if (document.querySelector('.fp-shortcuts-modal')) return;
        const m = document.createElement('div');
        m.className = 'fp-shortcuts-modal';
        m.onclick = (e) => { if (e.target === m) m.remove(); };
        const rows = [
            ['Ctrl+1', '3D Студия'], ['Ctrl+2', 'Чат'], ['Ctrl+3', 'Задачи'],
            ['Ctrl+4', 'Dashboard'], ['Ctrl+5', 'Кабинет'], ['Ctrl+Shift+L', 'Обучение (admin)'],
            ['Ctrl+K / Ctrl+G', 'Быстрый доступ (разделы + команды + поиск)'], ['Ctrl+Shift+F', 'Расширенный поиск'],
            ['Ctrl+F', 'Поиск в чате'], ['Ctrl+Enter', 'Отправить'], ['Alt+←/→', 'Вкладки'],
            ['F', 'Фокус-режим'],
        ];
        m.innerHTML = `<div class="fp-shortcuts-grid"><h3>Горячие клавиши</h3>${rows.map(([k, l]) =>
            `<div class="fp-shortcut-row"><span>${l}</span><kbd>${k}</kbd></div>`
        ).join('')}<button type="button" class="btn-secondary fp-shortcuts-close">Закрыть</button></div>`;
        m.querySelector('.fp-shortcuts-close').onclick = () => m.remove();
        document.body.appendChild(m);
    }

    function toggleFocusMode() {
        prefs.focusMode = !prefs.focusMode;
        savePrefs();
        toast(prefs.focusMode ? 'Фокус: боковые панели скрыты' : 'Фокус выключен', 'info');
    }

    function toggleCompact() {
        prefs.compact = !prefs.compact;
        savePrefs();
        toast(prefs.compact ? 'Компактный интерфейс' : 'Обычный интерфейс', 'info');
    }

    function applyPrefs() {
        document.body.classList.toggle('fp-ambient', prefs.ambient);
        document.body.classList.toggle('fp-focus', prefs.focusMode);
        document.body.classList.toggle('fp-compact', prefs.compact);
        document.documentElement.setAttribute('data-fp-accent', prefs.accent === 'purple' ? '' : prefs.accent);
        if (prefs.particles) initParticles();
        else document.getElementById('fpParticles')?.remove();
    }

    function initParticles() {
        if (document.getElementById('fpParticles')) return;
        const c = document.createElement('canvas');
        c.id = 'fpParticles';
        document.body.prepend(c);
        const ctx = c.getContext('2d');
        let w, h, pts = [];
        const resize = () => {
            w = c.width = window.innerWidth;
            h = c.height = window.innerHeight;
            pts = Array.from({ length: 18 }, () => ({
                x: Math.random() * w, y: Math.random() * h,
                vx: (Math.random() - 0.5) * 0.2, vy: (Math.random() - 0.5) * 0.2, r: Math.random() * 1.5 + 0.5,
            }));
        };
        resize();
        window.addEventListener('resize', resize);
        (function draw() {
            if (!document.getElementById('fpParticles')) return;
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = 'rgba(199,125,255,0.2)';
            pts.forEach((p) => {
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0 || p.x > w) p.vx *= -1;
                if (p.y < 0 || p.y > h) p.vy *= -1;
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
            });
            requestAnimationFrame(draw);
        })();
    }

    function exportChat() {
        const lines = [];
        document.querySelectorAll('#messages .message').forEach((m) => {
            const who = m.querySelector('.msg-header')?.textContent?.trim() || '';
            const text = m.querySelector('.msg-text')?.textContent?.trim() || '';
            if (text) lines.push(`${who}\n${text}\n---`);
        });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' }));
        a.download = `chat-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast('Чат экспортирован', 'success');
    }

    function bindScrollProgress() {
        document.addEventListener('scroll', () => {
            const el = document.querySelector('.messages:not(.hidden), .learning-messages, .tasks-list');
            const scrollEl = el || document.documentElement;
            const max = scrollEl.scrollHeight - scrollEl.clientHeight;
            const bar = document.getElementById('fpScrollProgress');
            if (bar && max > 0) bar.style.width = `${(scrollEl.scrollTop / max) * 100}%`;
        }, true);
    }

    function bindOffline() {
        const update = () => {
            document.getElementById('fpOffline')?.remove();
            if (navigator.onLine) return;
            const b = document.createElement('div');
            b.id = 'fpOffline';
            b.className = 'fp-offline';
            b.textContent = 'Нет сети';
            document.body.appendChild(b);
        };
        window.addEventListener('online', () => document.getElementById('fpOffline')?.remove());
        window.addEventListener('offline', update);
        update();
    }

    function bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'g') { e.preventDefault(); openCommandPalette(); }
            if (e.key === 'f' && !e.ctrlKey && !/INPUT|TEXTAREA/.test(document.activeElement?.tagName || '')) {
                e.preventDefault();
                toggleFocusMode();
            }
            if (e.altKey && e.key === 'ArrowRight') {
                e.preventDefault();
                const i = VIEWS.findIndex((v) => v.id === currentView);
                sw(VIEWS[(i + 1) % VIEWS.length].id);
            }
            if (e.altKey && e.key === 'ArrowLeft') {
                e.preventDefault();
                const i = VIEWS.findIndex((v) => v.id === currentView);
                sw(VIEWS[(i - 1 + VIEWS.length) % VIEWS.length].id);
            }
            if (e.key === KONAMI[konamiStep]) {
                konamiStep++;
                if (konamiStep === KONAMI.length) {
                    konamiStep = 0;
                    if (global.StudioApp?.burstConfetti && global.agents) {
                        Object.keys(global.agents).forEach((id) => StudioApp.burstConfetti(id));
                    }
                }
            } else konamiStep = 0;
        });
    }

    function hookViewSwitch() {
        const orig = global.switchView;
        if (!orig || orig._fpHooked) return;
        global.switchView = function (view) {
            orig(view);
            updateFabVisibility(view);
        };
        global.switchView._fpHooked = true;
    }

    function onTaskStats(stats) {
        updateFooterMeta(stats);
        const awaiting = stats?.awaiting_approval || 0;
        if (awaiting > (onTaskStats._lastAwaiting || 0)) {
            pushNotify('⏳ Виктор ждёт решения', `Задач на проверке: ${awaiting}`);
            if (window.UIEnhancements) UIEnhancements.toast('⏳ Есть задачи на вашем решении', 'info');
        }
        onTaskStats._lastAwaiting = awaiting;
        if (stats?.completed > dailyGoal._last) {
            pushNotify('Задача выполнена', `Всего: ${stats.completed}`);
        }
        dailyGoal._last = stats.completed || 0;
    }

    function onWsMessage(data) {
        if (data.type === 'task_done') {
            pushNotify(data.agent_name || 'Агент', String(data.message || '').slice(0, 80));
        }
        if (data.type === 'artifact_created') {
            pushNotify('Артефакт', data.title || 'Новый проект');
        }
        if (data.type === 'task_awaiting_approval') {
            pushNotify('⏳ На проверке', String(data.message || '').replace(/[*#_`]/g, '').slice(0, 80));
            syncServerNotifications();
        }
    }

    async function syncServerNotifications() {
        try {
            const r = await fetch('/api/notifications', { credentials: 'same-origin' });
            if (!r.ok) return;
            const d = await r.json();
            (d.items || []).forEach((n) => {
                if (!notifications.find((x) => x.serverId === n.id)) {
                    notifications.unshift({
                        serverId: n.id,
                        title: n.title,
                        body: n.body,
                        link: n.link || '',
                        time: n.created_at ? new Date(n.created_at).toLocaleString('ru') : '',
                        unread: !n.read,
                    });
                    if (!n.read) unreadCount++;
                }
            });
            updateNotifyBadge();
        } catch (_) {}
    }

    function init() {
        setupChrome();
        applyPrefs();
        bindScrollProgress();
        bindOffline();
        bindKeyboard();
        hookViewSwitch();
        updateFabVisibility('tasks');
        syncServerNotifications();
        setInterval(syncServerNotifications, 15000);
        setInterval(() => updateFooterMeta({ total: 1, completed: dailyGoal._last }), 60000);
    }

    global.FeaturePack = {
        init,
        getCommands,
        openCommandPalette,
        openGlobalSearch,
        toggleNotifyPanel,
        showShortcutsModal,
        toggleFocusMode,
        toggleCompact,
        onTaskStats,
        onWsMessage,
        pushNotify,
    };
})(window);
