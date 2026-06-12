/**
 * Feature Pack v2 — 50+ функций и визуала для AI Team Room
 */
(function (global) {
    const sw = (view) => { if (global.switchView) global.switchView(view); };
    const TIPS = [
        'Ctrl+G — глобальный поиск по разделам',
        'Ctrl+K — 50+ команд в палитре',
        'Клик по агенту в 3D — личный чат с выполнением задач',
        'Alt+←/→ — переключение вкладок',
        'F — режим фокуса (скрывает боковые панели)',
        'Личный чат: «сделай…» — агент реально выполнит задачу',
        '@соня @pm — упоминания в чате',
        'Ctrl+Enter — отправить сообщение',
    ];

    const VIEWS = [
        { id: 'studio', label: '🎮 3D Студия', keys: ['3d', 'студия', 'office'] },
        { id: 'chat', label: '💬 Чат', keys: ['чат', 'chat', 'task'] },
        { id: 'learning', label: '📚 Обучение', keys: ['learn', 'учеб'] },
        { id: 'design', label: '🎨 Design', keys: ['figma', 'design'] },
        { id: 'sonya-studio', label: '✨ Studio', keys: ['sonya', 'studio'] },
        { id: 'tasks', label: '📋 Задачи', keys: ['tasks', 'задач'] },
        { id: 'projects', label: '📦 Проекты', keys: ['project', 'артефакт'] },
        { id: 'kanban', label: '📌 Kanban', keys: ['kanban', 'board'] },
        { id: 'sprint', label: '🏃 Sprint', keys: ['sprint'] },
        { id: 'timeline', label: '⏱ Timeline', keys: ['time', 'history'] },
        { id: 'dashboard', label: '📊 Dashboard', keys: ['dash', 'stats'] },
        { id: 'profile', label: '👤 Кабинет', keys: ['profile', 'account'] },
    ];

    let prefs = loadPrefs();
    let notifications = [];
    let unreadCount = 0;
    let sessionStart = Date.now();
    let currentView = 'studio';
    let dailyGoal = { target: 5, done: 0 };
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
            ambient: true,
            particles: true,
            focusMode: false,
            compact: false,
            cinematic: false,
            accent: 'purple',
            showTimestamps: false,
            autoScroll: true,
            sounds: true,
            pinnedAgents: [],
            workspaceMode: 'creative',
        };
    }

    function savePrefs() {
        localStorage.setItem(STORAGE, JSON.stringify(prefs));
        applyPrefs();
    }

    function toast(msg, type) {
        if (global.UIEnhancements) UIEnhancements.toast(msg, type || 'info');
    }

    function pushNotify(title, body, action) {
        notifications.unshift({
            id: Date.now(),
            title,
            body,
            action,
            time: new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
            unread: true,
        });
        notifications = notifications.slice(0, 40);
        unreadCount++;
        updateNotifyBadge();
    }

    function updateNotifyBadge() {
        const b = document.getElementById('fpNotifyBadge');
        if (!b) return;
        b.textContent = unreadCount > 9 ? '9+' : String(unreadCount);
        b.style.display = unreadCount ? 'grid' : 'none';
    }

    /* ─── 50 Command palette actions ─── */
    function getCommands() {
        const go = (v) => () => sw(v);
        return [
            { label: '🎮 3D Студия', run: go('studio'), cat: 'nav' },
            { label: '💬 Рабочий чат', run: go('chat'), cat: 'nav' },
            { label: '📚 Обучение', run: go('learning'), cat: 'nav' },
            { label: '🎨 Design / Figma', run: go('design'), cat: 'nav' },
            { label: '✨ Sonya Studio', run: go('sonya-studio'), cat: 'nav' },
            { label: '📋 Задачи', run: go('tasks'), cat: 'nav' },
            { label: '📦 Проекты', run: go('projects'), cat: 'nav' },
            { label: '📌 Kanban', run: go('kanban'), cat: 'nav' },
            { label: '🏃 Sprint', run: go('sprint'), cat: 'nav' },
            { label: '⏱ Timeline', run: go('timeline'), cat: 'nav' },
            { label: '📊 Dashboard', run: go('dashboard'), cat: 'nav' },
            { label: '👤 Личный кабинет', run: go('profile'), cat: 'nav' },
            { label: '📋 Новая задача команде', run: () => { go('chat')(); document.getElementById('messageInput')?.focus(); if (global.setMsgType) setMsgType('task'); }, cat: 'task' },
            { label: '💬 Режим чата (без задачи)', run: () => { go('chat')(); if (global.setMsgType) setMsgType('chat'); }, cat: 'task' },
            { label: '🎯 PM: спланируй спринт', run: () => quickTask('pm', 'Спланируй спринт на неделю с приоритетами'), cat: 'task' },
            { label: '🏛️ Архитектура системы', run: () => quickTask('architect', 'Спроектируй архитектуру для нашего проекта'), cat: 'task' },
            { label: '⚙️ REST API', run: () => quickTask('backend', 'Создай REST API для основных сущностей'), cat: 'task' },
            { label: '🎨 Landing page', run: () => quickTask('frontend', 'Сделай современный landing page в React'), cat: 'task' },
            { label: '🧪 Напиши тесты', run: () => quickTask('qa', 'Напиши тест-план и автотесты'), cat: 'task' },
            { label: '🔍 Code review', run: () => quickTask('reviewer', 'Проведи code review последних изменений'), cat: 'task' },
            { label: '📝 Документация', run: () => quickTask('doc_writer', 'Обнови README и API docs'), cat: 'task' },
            { label: '🔧 CI/CD pipeline', run: () => quickTask('devops', 'Настрой Docker и CI pipeline'), cat: 'task' },
            { label: '⚡ Cursor: запуск', run: () => global.Integrations?.toggleCursorPanel?.(), cat: 'ai' },
            { label: '🎨 React Preview', run: () => global.ReactPreview?.toggle?.(), cat: 'ai' },
            { label: '⚡ Full Pipeline', run: () => global.PowerPack?.runPipeline?.(), cat: 'ai' },
            { label: '🧠 Project Memory', run: () => global.PowerPack?.showMemory?.(), cat: 'ai' },
            { label: '📊 Standup', run: () => global.WowFeatures?.showStandup?.(), cat: 'ai' },
            { label: '🚀 Deploy ZIP', run: () => global.WowFeatures?.deployNow?.(), cat: 'ai' },
            { label: '📦 Backup', run: () => global.PowerPack?.downloadBackup?.(), cat: 'ai' },
            { label: '🔗 View-link', run: () => global.PowerPack?.createViewLink?.(), cat: 'ai' },
            { label: '⚔️ Debate Architect vs Reviewer', run: () => global.DebateUI?.start?.(), cat: 'ai' },
            { label: '🔊 Standup TTS', run: () => global.VoiceRoom?.readStandup?.(), cat: 'voice' },
            { label: '🎤 Голосовая задача', run: () => global.VoiceRoom?.startListening?.(), cat: 'voice' },
            { label: '📤 Sync GitHub', run: () => global.UIEnhancements?.syncNow?.(), cat: 'git' },
            { label: '🔍 Глобальный поиск', run: openGlobalSearch, cat: 'ui' },
            { label: '🔔 Центр уведомлений', run: toggleNotifyPanel, cat: 'ui' },
            { label: '⌨️ Все горячие клавиши', run: showShortcutsModal, cat: 'ui' },
            { label: '🎯 Режим фокуса', run: toggleFocusMode, cat: 'ui' },
            { label: '📐 Компактный UI', run: toggleCompact, cat: 'ui' },
            { label: '🎬 Кино-режим 3D', run: toggleCinematic, cat: 'ui' },
            { label: '✨ Ambient фон', run: toggleAmbient, cat: 'ui' },
            { label: '🌈 Акцент: фиолетовый', run: () => setAccent('purple'), cat: 'theme' },
            { label: '🌈 Акцент: cyan', run: () => setAccent('cyan'), cat: 'theme' },
            { label: '🌈 Акцент: gold', run: () => setAccent('gold'), cat: 'theme' },
            { label: '🌈 Акцент: green', run: () => setAccent('green'), cat: 'theme' },
            { label: '🌙/☀️ Сменить тему', run: () => global.toggleTheme?.(), cat: 'theme' },
            { label: '🔄 Авто-тема по времени', run: () => global.AutoTheme?.apply?.(), cat: 'theme' },
            { label: '💼 Режим: Focus', run: () => setWorkspace('focus'), cat: 'mode' },
            { label: '🎨 Режим: Creative', run: () => setWorkspace('creative'), cat: 'mode' },
            { label: '👥 Режим: Meeting', run: () => setWorkspace('meeting'), cat: 'mode' },
            { label: '📥 Export задач JSON', run: () => { go('tasks')(); global.exportTasks?.(); }, cat: 'export' },
            { label: '📄 Export чата', run: exportChat, cat: 'export' },
            { label: '🖨️ Печать задач', run: printTasks, cat: 'export' },
            { label: '📱 Установить PWA', run: () => global.installPWA?.(), cat: 'pwa' },
            { label: '🎓 Тур onboarding', run: () => global.Onboarding?.start?.(), cat: 'help' },
            { label: '❓ Совет дня', run: showRandomTip, cat: 'help' },
        ];
    }

    function quickTask(target, text) {
        if (global.switchView) sw('chat');
        const sel = document.getElementById('targetSelect');
        if (sel) sel.value = target;
        const inp = document.getElementById('messageInput');
        if (inp) {
            inp.value = text;
            inp.focus();
        }
        if (global.setMsgType) setMsgType('task');
        toast(`Задача для ${target} — нажмите Enter`, 'info');
    }

    /* ─── UI builders ─── */
    function injectHeaderWidgets() {
        const status = document.querySelector('.header-status');
        if (status && !document.getElementById('fpClock')) {
            const clock = document.createElement('span');
            clock.id = 'fpClock';
            clock.className = 'fp-clock';
            status.insertBefore(clock, status.firstChild);

            const ring = document.createElement('div');
            ring.className = 'fp-progress-ring';
            ring.id = 'fpProgressRing';
            ring.title = 'Прогресс задач';
            ring.innerHTML = '<span id="fpProgressPct">0</span>';
            status.appendChild(ring);

            const daily = document.createElement('div');
            daily.className = 'fp-daily-goal';
            daily.id = 'fpDailyGoal';
            daily.innerHTML = 'Цель <div class="fp-daily-goal-bar"><i id="fpDailyBar" style="width:0%"></i></div> <span id="fpDailyText">0/5</span>';
            status.appendChild(daily);

            const cost = document.createElement('span');
            cost.id = 'fpCostChip';
            cost.className = 'fp-cost-chip hidden';
            status.appendChild(cost);

            const dots = document.createElement('div');
            dots.className = 'fp-int-dots';
            dots.id = 'fpIntDots';
            dots.innerHTML = '<span class="fp-int-dot" id="fpDotGit" title="Git"></span><span class="fp-int-dot" id="fpDotCursor" title="Cursor"></span><span class="fp-int-dot" id="fpDotWs" title="WS"></span>';
            status.appendChild(dots);

            const session = document.createElement('span');
            session.id = 'fpSession';
            session.className = 'fp-session';
            status.appendChild(session);

            const mode = document.createElement('span');
            mode.id = 'fpModeBadge';
            mode.className = 'fp-mode-badge';
            status.appendChild(mode);

            const notifyBtn = document.createElement('button');
            notifyBtn.type = 'button';
            notifyBtn.className = 'fp-notify-btn hdr-btn';
            notifyBtn.id = 'fpNotifyBtn';
            notifyBtn.title = 'Уведомления';
            notifyBtn.innerHTML = '🔔<span class="fp-notify-badge" id="fpNotifyBadge" style="display:none">0</span>';
            notifyBtn.onclick = toggleNotifyPanel;
            status.appendChild(notifyBtn);
        }

        const navRow = document.querySelector('.header-row-nav');
        if (navRow && !document.getElementById('fpTickerWrap')) {
            const tickerWrap = document.createElement('div');
            tickerWrap.id = 'fpTickerWrap';
            tickerWrap.className = 'fp-ticker-wrap';
            tickerWrap.innerHTML = '<div class="fp-ticker" id="fpTicker"></div>';
            navRow.appendChild(tickerWrap);
        }

        const logo = document.querySelector('.logo-text h1');
        if (logo && !document.getElementById('fpFeatureBadge')) {
            const badge = document.createElement('span');
            badge.id = 'fpFeatureBadge';
            badge.className = 'fp-feature-badge';
            badge.textContent = '50+';
            badge.title = 'Feature Pack v2';
            logo.appendChild(document.createTextNode(' '));
            logo.appendChild(badge);
        }

        if (!document.getElementById('fpScrollProgress')) {
            const bar = document.createElement('div');
            bar.id = 'fpScrollProgress';
            document.body.prepend(bar);
        }

        if (!document.getElementById('fpFab')) {
            const fab = document.createElement('button');
            fab.type = 'button';
            fab.id = 'fpFab';
            fab.className = 'fp-fab';
            fab.title = 'Быстрая задача';
            fab.textContent = '+';
            fab.onclick = () => {
                if (global.switchView) sw('chat');
                document.getElementById('messageInput')?.focus();
                if (global.setMsgType) setMsgType('task');
            };
            document.body.appendChild(fab);
        }

        if (!document.getElementById('fpBreadcrumb')) {
            const bc = document.createElement('div');
            bc.id = 'fpBreadcrumb';
            bc.className = 'fp-breadcrumb';
            document.querySelector('.main')?.prepend(bc);
        }

        if (!document.getElementById('fpTipBar')) {
            const tip = document.createElement('div');
            tip.id = 'fpTipBar';
            tip.className = 'fp-tip-bar';
            tip.innerHTML = '<span>💡</span><span id="fpTipText"></span><button type="button" aria-label="Закрыть">×</button>';
            tip.querySelector('button').onclick = () => tip.classList.add('hidden');
            document.querySelector('.main')?.prepend(tip);
            showRandomTip(false);
        }

        injectMentionBar();
    }

    function injectMentionBar() {
        const toolbar = document.querySelector('.chat-toolbar');
        if (!toolbar || document.getElementById('fpMentionBar')) return;
        const bar = document.createElement('div');
        bar.id = 'fpMentionBar';
        bar.className = 'fp-mention-bar';
        const agents = [
            ['@pm', 'pm'], ['@соня', 'frontend'], ['@макс', 'backend'],
            ['@рита', 'qa'], ['@лео', 'cursor'], ['@все', 'all'],
        ];
        bar.innerHTML = agents.map(([label, id]) =>
            `<button type="button" class="fp-mention-chip" data-agent="${id}">${label}</button>`
        ).join('');
        toolbar.after(bar);
        bar.querySelectorAll('.fp-mention-chip').forEach((btn) => {
            btn.onclick = () => {
                const inp = document.getElementById('messageInput');
                if (!inp) return;
                const mention = btn.textContent + ' ';
                inp.value = (inp.value ? inp.value + ' ' : '') + mention;
                inp.focus();
                const sel = document.getElementById('targetSelect');
                if (sel && btn.dataset.agent !== 'all') sel.value = btn.dataset.agent;
            };
        });
    }

    function buildTicker() {
        const el = document.getElementById('fpTicker');
        if (!el) return;
        const items = [
            '🎮 3D студия live', '💬 50+ команд Ctrl+K', '📋 Задачи + Kanban',
            '🎨 Figma → React', '⚡ Cursor SDK', '🔔 Центр уведомлений',
            '🎯 Запросы пользователя → работа', '📊 Standup & Sprint',
        ];
        const html = items.map((t) => `<span>${t}</span>`).join('');
        el.innerHTML = html + html;
    }

    function updateClock() {
        const el = document.getElementById('fpClock');
        if (el) {
            el.textContent = new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }
        const ses = document.getElementById('fpSession');
        if (ses) {
            const m = Math.floor((Date.now() - sessionStart) / 60000);
            ses.textContent = `⏱ ${m}м`;
        }
    }

    function updateBreadcrumb(view) {
        currentView = view || currentView;
        const el = document.getElementById('fpBreadcrumb');
        const v = VIEWS.find((x) => x.id === currentView);
        if (el && v) el.innerHTML = `AI Team Room › <strong>${v.label}</strong>`;
    }

    function updateTaskProgress(stats) {
        if (!stats) return;
        const pct = stats.total ? Math.round((stats.completed / stats.total) * 100) : 0;
        const ring = document.getElementById('fpProgressRing');
        const txt = document.getElementById('fpProgressPct');
        if (ring) ring.style.setProperty('--fp-pct', `${pct}%`);
        if (txt) txt.textContent = pct;
        dailyGoal.done = stats.completed || 0;
        const bar = document.getElementById('fpDailyBar');
        const dtxt = document.getElementById('fpDailyText');
        const dp = Math.min(100, Math.round((dailyGoal.done / dailyGoal.target) * 100));
        if (bar) bar.style.width = `${dp}%`;
        if (dtxt) dtxt.textContent = `${Math.min(dailyGoal.done, dailyGoal.target)}/${dailyGoal.target}`;
    }

    async function refreshIntegrations() {
        try {
            const [gitR, curR] = await Promise.all([
                fetch('/api/git/status').catch(() => null),
                fetch('/api/cursor/status').catch(() => null),
            ]);
            const git = gitR?.ok ? await gitR.json() : {};
            const cur = curR?.ok ? await curR.json() : {};
            document.getElementById('fpDotGit')?.classList.toggle('ok', !git.changed_files);
            document.getElementById('fpDotGit')?.classList.toggle('warn', git.changed_files > 0);
            document.getElementById('fpDotCursor')?.classList.toggle('ok', cur.enabled);
            const dot = document.getElementById('fpDotWs');
            if (dot) dot.classList.toggle('ok', global.ws?.readyState === 1);
        } catch (_) {}
    }

    async function refreshCost() {
        try {
            const r = await fetch('/api/llm/usage');
            if (!r.ok) return;
            const d = await r.json();
            const chip = document.getElementById('fpCostChip');
            if (chip && d.total_tokens) {
                chip.textContent = `LLM ${(d.total_tokens / 1000).toFixed(1)}k`;
                chip.classList.remove('hidden');
            }
        } catch (_) {}
    }

    /* ─── Global search ─── */
    function openGlobalSearch() {
        if (document.getElementById('fpSearchOverlay')) return;
        const overlay = document.createElement('div');
        overlay.id = 'fpSearchOverlay';
        overlay.className = 'fp-search-overlay';
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
        overlay.innerHTML = `
            <div class="fp-search-box">
                <input type="search" id="fpSearchInput" placeholder="Поиск разделов, команд, агентов…" autofocus>
                <div class="fp-search-results" id="fpSearchResults"></div>
            </div>`;
        document.body.appendChild(overlay);
        const input = overlay.querySelector('#fpSearchInput');
        const results = overlay.querySelector('#fpSearchResults');
        const allItems = [
            ...VIEWS.map((v) => ({ label: v.label, run: () => sw(v.id), type: 'Раздел' })),
            ...getCommands().slice(0, 30).map((c) => ({ label: c.label, run: c.run, type: 'Команда' })),
        ];
        function render(q) {
            const qq = (q || '').toLowerCase();
            const list = qq ? allItems.filter((i) => i.label.toLowerCase().includes(qq)) : allItems.slice(0, 12);
            results.innerHTML = list.map((item, i) =>
                `<button type="button" class="fp-search-item${i === 0 ? ' active' : ''}" data-i="${i}">${item.label}<small>${item.type}</small></button>`
            ).join('') || '<div style="padding:16px;color:var(--text-muted)">Ничего не найдено</div>';
            results.querySelectorAll('.fp-search-item').forEach((btn) => {
                btn.onclick = () => {
                    list[+btn.dataset.i].run();
                    overlay.remove();
                };
            });
        }
        input.addEventListener('input', () => render(input.value));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') overlay.remove();
            if (e.key === 'Enter') results.querySelector('.fp-search-item')?.click();
        });
        render('');
    }

    /* ─── Notifications ─── */
    function toggleNotifyPanel() {
        const existing = document.getElementById('fpNotifyPanel');
        if (existing) { existing.remove(); return; }
        unreadCount = 0;
        updateNotifyBadge();
        notifications.forEach((n) => { n.unread = false; });
        const panel = document.createElement('div');
        panel.id = 'fpNotifyPanel';
        panel.className = 'fp-notify-panel';
        panel.innerHTML = `<div class="fp-notify-head"><span>🔔 Уведомления</span><button type="button" class="icon-btn" id="fpNotifyClose">×</button></div><div id="fpNotifyList"></div>`;
        document.body.appendChild(panel);
        panel.querySelector('#fpNotifyClose').onclick = () => panel.remove();
        const list = panel.querySelector('#fpNotifyList');
        if (!notifications.length) {
            list.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">Пока пусто</div>';
        } else {
            list.innerHTML = notifications.map((n) =>
                `<div class="fp-notify-item${n.unread ? ' unread' : ''}"><strong>${n.title}</strong><br>${n.body}<div class="fp-notify-time">${n.time}</div></div>`
            ).join('');
        }
    }

    /* ─── Command palette (50 commands) ─── */
    function openCommandPalette() {
        let pal = document.getElementById('commandPalette');
        if (pal) { pal.remove(); return; }
        const commands = getCommands();
        pal = document.createElement('div');
        pal.id = 'commandPalette';
        pal.className = 'command-palette-overlay';
        pal.onclick = (e) => { if (e.target === pal) pal.remove(); };
        pal.innerHTML = `
            <div class="command-palette">
                <input type="text" id="cmdSearch" placeholder="50+ команд — поиск…" autofocus>
                <div class="cmd-list" id="cmdList">${commands.map((a, i) =>
                    `<button type="button" class="cmd-item" data-i="${i}">${a.label}</button>`
                ).join('')}</div>
            </div>`;
        document.body.appendChild(pal);
        pal.querySelectorAll('.cmd-item').forEach((btn) => {
            btn.onclick = () => { commands[+btn.dataset.i].run(); pal.remove(); };
        });
        const search = pal.querySelector('#cmdSearch');
        search?.addEventListener('input', () => {
            const q = search.value.toLowerCase();
            pal.querySelectorAll('.cmd-item').forEach((btn, i) => {
                btn.style.display = commands[i].label.toLowerCase().includes(q) ? '' : 'none';
            });
        });
        search?.addEventListener('keydown', (e) => { if (e.key === 'Escape') pal.remove(); });
    }

    function showShortcutsModal() {
        if (document.querySelector('.fp-shortcuts-modal')) return;
        const m = document.createElement('div');
        m.className = 'fp-shortcuts-modal';
        m.onclick = (e) => { if (e.target === m) m.remove(); };
        const shortcuts = [
            ['Ctrl+1…6', 'Вкладки'],
            ['Ctrl+K', '50+ команд'],
            ['Ctrl+G', 'Глобальный поиск'],
            ['Ctrl+F', 'Поиск в чате'],
            ['Ctrl+Enter', 'Отправить'],
            ['Ctrl+/', 'Подсказка'],
            ['Alt+←/→', 'Вкладки'],
            ['F', 'Фокус-режим'],
            ['Esc', 'Закрыть модалки'],
        ];
        m.innerHTML = `<div class="fp-shortcuts-grid"><h3 style="grid-column:1/-1">⌨️ Горячие клавиши</h3>${shortcuts.map(([k, l]) =>
            `<div class="fp-shortcut-row"><span>${l}</span><kbd>${k}</kbd></div>`
        ).join('')}<button type="button" class="btn-secondary" style="grid-column:1/-1;margin-top:8px" onclick="this.closest('.fp-shortcuts-modal').remove()">Закрыть</button></div>`;
        document.body.appendChild(m);
    }

    /* ─── Toggles ─── */
    function toggleFocusMode() {
        prefs.focusMode = !prefs.focusMode;
        savePrefs();
        toast(prefs.focusMode ? '🎯 Фокус включён' : 'Фокус выключен', 'info');
    }

    function toggleCompact() {
        prefs.compact = !prefs.compact;
        savePrefs();
        toast(prefs.compact ? '📐 Компактный UI' : 'Обычный UI', 'info');
    }

    function toggleCinematic() {
        prefs.cinematic = !prefs.cinematic;
        savePrefs();
        toast(prefs.cinematic ? '🎬 Кино-режим 3D' : 'Кино-режим off', 'info');
    }

    function toggleAmbient() {
        prefs.ambient = !prefs.ambient;
        savePrefs();
    }

    function setAccent(name) {
        prefs.accent = name;
        savePrefs();
        toast(`Акцент: ${name}`, 'success');
    }

    function setWorkspace(mode) {
        prefs.workspaceMode = mode;
        savePrefs();
        const labels = { focus: 'Focus', creative: 'Creative', meeting: 'Meeting' };
        toast(`Режим: ${labels[mode] || mode}`, 'info');
    }

    function applyPrefs() {
        document.body.classList.toggle('fp-ambient', prefs.ambient);
        document.body.classList.toggle('fp-focus', prefs.focusMode);
        document.body.classList.toggle('fp-compact', prefs.compact);
        document.body.classList.toggle('fp-cinematic', prefs.cinematic);
        document.documentElement.setAttribute('data-fp-accent', prefs.accent === 'purple' ? '' : prefs.accent);
        document.querySelector('.header')?.classList.add('fp-glass');
        const badge = document.getElementById('fpModeBadge');
        if (badge) badge.textContent = prefs.workspaceMode || 'creative';
        if (prefs.particles) initParticles(); else document.getElementById('fpParticles')?.remove();
    }

    /* ─── Particles ─── */
    function initParticles() {
        if (document.getElementById('fpParticles') || !prefs.particles) return;
        const c = document.createElement('canvas');
        c.id = 'fpParticles';
        document.body.prepend(c);
        const ctx = c.getContext('2d');
        let w, h, pts = [];
        function resize() {
            w = c.width = window.innerWidth;
            h = c.height = window.innerHeight;
            pts = Array.from({ length: 35 }, () => ({
                x: Math.random() * w, y: Math.random() * h,
                vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3, r: Math.random() * 2 + 0.5,
            }));
        }
        resize();
        window.addEventListener('resize', resize);
        function draw() {
            if (!document.getElementById('fpParticles')) return;
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = 'rgba(199,125,255,0.35)';
            pts.forEach((p) => {
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0 || p.x > w) p.vx *= -1;
                if (p.y < 0 || p.y > h) p.vy *= -1;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
            });
            requestAnimationFrame(draw);
        }
        draw();
    }

    /* ─── Scroll progress ─── */
    function bindScrollProgress() {
        document.addEventListener('scroll', () => {
            const el = document.activeElement?.closest('.messages, .learning-messages, .tasks-list');
            const scrollEl = el || document.documentElement;
            const max = scrollEl.scrollHeight - scrollEl.clientHeight;
            const pct = max > 0 ? (scrollEl.scrollTop / max) * 100 : 0;
            const bar = document.getElementById('fpScrollProgress');
            if (bar) bar.style.width = `${pct}%`;
        }, true);
    }

    /* ─── Ripple on buttons ─── */
    function bindRipples() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.hdr-btn, .view-tab, .fp-fab, .type-btn, .tpl-btn');
            if (!btn) return;
            btn.classList.add('fp-ripple-host');
            const r = document.createElement('span');
            r.className = 'fp-ripple';
            const rect = btn.getBoundingClientRect();
            r.style.left = `${e.clientX - rect.left}px`;
            r.style.top = `${e.clientY - rect.top}px`;
            r.style.width = r.style.height = '20px';
            btn.appendChild(r);
            setTimeout(() => r.remove(), 600);
        });
    }

    /* ─── Export helpers ─── */
    function exportChat() {
        const msgs = document.querySelectorAll('#messages .message');
        const lines = [];
        msgs.forEach((m) => {
            const who = m.querySelector('.msg-header')?.textContent?.trim() || '';
            const text = m.querySelector('.msg-text')?.textContent?.trim() || '';
            if (text) lines.push(`${who}\n${text}\n---`);
        });
        const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `chat-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast('💬 Чат экспортирован', 'success');
    }

    function printTasks() {
        sw('tasks');
        setTimeout(() => window.print(), 400);
    }

    function showRandomTip(showToast) {
        const tip = TIPS[Math.floor(Math.random() * TIPS.length)];
        const el = document.getElementById('fpTipText');
        if (el) el.textContent = tip;
        if (showToast !== false) toast(`💡 ${tip}`, 'info', 5000);
    }

    /* ─── Offline ─── */
    function bindOffline() {
        function update() {
            document.getElementById('fpOffline')?.remove();
            if (navigator.onLine) return;
            const b = document.createElement('div');
            b.id = 'fpOffline';
            b.className = 'fp-offline';
            b.textContent = '⚠️ Нет сети — часть функций недоступна';
            document.body.appendChild(b);
        }
        window.addEventListener('online', () => { document.getElementById('fpOffline')?.remove(); toast('Сеть восстановлена', 'success'); });
        window.addEventListener('offline', update);
        update();
    }

    /* ─── Konami easter egg ─── */
    function bindKonami() {
        document.addEventListener('keydown', (e) => {
            if (e.key === KONAMI[konamiStep]) {
                konamiStep++;
                if (konamiStep === KONAMI.length) {
                    konamiStep = 0;
                    if (global.StudioApp?.burstConfetti) {
                        Object.keys(global.agents || {}).forEach((id) => StudioApp.burstConfetti(id));
                    }
                    toast('🎉 Konami! Feature Pack activated!', 'success', 6000);
                    pushNotify('Easter egg', 'Konami code — confetti!', null);
                }
            } else konamiStep = 0;
        });
    }

    /* ─── Keyboard extras ─── */
    function bindKeyboard() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'g') {
                e.preventDefault();
                openGlobalSearch();
            }
            if (e.key === 'f' && !e.ctrlKey && !e.metaKey && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
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
        });
    }

    /* ─── Hook view switch ─── */
    function hookViewSwitch() {
        const orig = global.switchView;
        if (!orig || orig._fpHooked) return;
        global.switchView = function (view) {
            orig(view);
            updateBreadcrumb(view);
            document.querySelectorAll('.main > [id$="View"]').forEach((el) => {
                if (!el.classList.contains('hidden')) {
                    el.classList.add('fp-view-enter');
                    setTimeout(() => el.classList.remove('fp-view-enter'), 400);
                }
            });
        };
        global.switchView._fpHooked = true;
    }

    /* ─── Public API ─── */
    function onTaskStats(stats) {
        updateTaskProgress(stats);
        if (stats.completed > (dailyGoal._last || 0)) {
            pushNotify('Задача выполнена', `Всего: ${stats.completed}`, () => sw('tasks'));
        }
        dailyGoal._last = stats.completed;
    }

    function onWsMessage(data) {
        if (data.type === 'task_done') {
            pushNotify(data.agent_name || 'Агент', String(data.message || '').slice(0, 100), () => sw('tasks'));
        }
        if (data.type === 'artifact_created') {
            pushNotify('📦 Артефакт', data.title || 'Новый проект', () => sw('projects'));
        }
    }

    function init() {
        injectHeaderWidgets();
        buildTicker();
        applyPrefs();
        bindScrollProgress();
        bindRipples();
        bindOffline();
        bindKonami();
        bindKeyboard();
        hookViewSwitch();
        updateClock();
        setInterval(updateClock, 1000);
        setInterval(refreshIntegrations, 15000);
        refreshIntegrations();
        refreshCost();
        updateBreadcrumb('studio');
        pushNotify('Feature Pack v2', '50+ функций загружено — Ctrl+K', null);
        toast('✨ Feature Pack: 50+ функций активно', 'success', 3500);
    }

    global.FeaturePack = {
        init,
        getCommands,
        openCommandPalette,
        openGlobalSearch,
        toggleNotifyPanel,
        showShortcutsModal,
        onTaskStats,
        onWsMessage,
        pushNotify,
        showRandomTip,
        VERSION: 50,
    };
})(window);
