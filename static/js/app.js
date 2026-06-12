/**
 * AI Team Room — чат, личные диалоги, WebSocket
 */
(function () {
    const THEME_KEY = 'ai-team-room-theme';
    const AGENT_ORDER = ['pm', 'architect', 'backend', 'frontend', 'qa', 'reviewer', 'doc_writer', 'devops', 'cursor'];
    const LEARNING_TYPES = new Set(['learning', 'learning_result', 'reflection', 'rest']);

    let ws = null;
    let msgType = 'task';
    let selectedAgent = null;
    let agents = {};
    let reconnectTimer = null;
    let studioInited = false;
    const privateChats = {};
    let taskHistory = [];
    let taskFilter = 'all';
    let taskStats = { total: 0, completed: 0, active: 0 };

    // ─── Theme ───────────────────────────────────────────
    function getPreferredTheme() {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved === 'light' || saved === 'dark') return saved;
        return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.getElementById('themeToggle');
        if (btn) {
            btn.textContent = theme === 'dark' ? '☀️' : '🌙';
            btn.title = theme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
        }
        if (window.StudioApp) StudioApp.setTheme(theme === 'dark');
    }

    window.toggleTheme = function () {
        const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem(THEME_KEY, next);
        applyTheme(next);
    };

    // ─── Views ───────────────────────────────────────────
    window.switchView = function (view) {
        document.querySelectorAll('.view-tab').forEach((t) => {
            t.classList.toggle('active', t.dataset.view === view);
        });
        document.getElementById('studioView').classList.toggle('hidden', view !== 'studio');
        document.getElementById('chatView').classList.toggle('hidden', view !== 'chat');
        document.getElementById('learningView').classList.toggle('hidden', view !== 'learning');
        document.getElementById('tasksView').classList.toggle('hidden', view !== 'tasks');
        document.getElementById('designView')?.classList.toggle('hidden', view !== 'design');

        if (view === 'tasks') loadTasks();
        if (view === 'design' && window.Integrations) {
            Integrations.loadCursorStatus();
            Integrations.loadDefaultFigmaUrl();
        }

        if (view === 'studio' && !studioInited) {
            initStudio();
        }
        if (view === 'studio' && studioInited) {
            const canvas = document.getElementById('studioCanvas');
            if (canvas && window.StudioApp) StudioApp.resize(canvas);
        }
    };

    function initStudio() {
        const canvas = document.getElementById('studioCanvas');
        if (!canvas || !window.StudioApp) return;

        const tryInit = () => {
            const ok = StudioApp.init(canvas, openPrivateChat);
            if (!ok) return;
            studioInited = true;
            if (Object.keys(agents).length) {
                StudioApp.updateAgents(Object.values(agents));
            }
            updateStudioLegend();
        };

        if (typeof THREE === 'undefined') {
            setTimeout(initStudio, 200);
            return;
        }

        requestAnimationFrame(() => requestAnimationFrame(tryInit));
    }

    // ─── Private chat windows ────────────────────────────
    window.openPrivateChat = async function (agentId) {
        const agent = agents[agentId];
        if (!agent) return;

        if (privateChats[agentId]) {
            privateChats[agentId].el.classList.remove('minimized');
            privateChats[agentId].input.focus();
            return;
        }

        const container = document.getElementById('privateChatsContainer');
        const win = document.createElement('div');
        win.className = 'private-chat';
        win.innerHTML = `
            <div class="pc-header" data-drag>
                <span>${agent.emoji} ${agent.name}</span>
                <div class="pc-actions">
                    <button type="button" onclick="minimizePrivateChat('${agentId}')">—</button>
                    <button type="button" onclick="closePrivateChat('${agentId}')">×</button>
                </div>
            </div>
            <div class="pc-messages"></div>
            <div class="pc-input-row">
                <input type="text" placeholder="Сообщение ${agent.name}…" />
                <button type="button">↑</button>
            </div>`;
        container.appendChild(win);

        const messagesEl = win.querySelector('.pc-messages');
        const input = win.querySelector('input');
        const sendBtn = win.querySelector('.pc-input-row button');

        privateChats[agentId] = { el: win, messagesEl, input };

        try {
            const resp = await fetch(`/api/agents/${agentId}/direct-chat`);
            if (resp.ok) {
                const data = await resp.json();
                data.messages.forEach((m) => appendPrivateMessage(agentId, m.role, m.text, agent));
            }
        } catch (_) {}

        const send = () => {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';
            appendPrivateMessage(agentId, 'user', text, agent);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'direct_chat', text, target: agentId }));
            }
        };

        sendBtn.addEventListener('click', send);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') send();
        });

        makeDraggable(win);
        input.focus();
    };

    window.closePrivateChat = function (agentId) {
        const pc = privateChats[agentId];
        if (pc) {
            pc.el.remove();
            delete privateChats[agentId];
        }
    };

    window.minimizePrivateChat = function (agentId) {
        const pc = privateChats[agentId];
        if (pc) pc.el.classList.add('minimized');
    };

    function appendPrivateMessage(agentId, role, text, agent) {
        const pc = privateChats[agentId];
        if (!pc) return;
        const div = document.createElement('div');
        div.className = `pc-msg ${role}`;
        div.innerHTML = role === 'user'
            ? escapeHtml(text)
            : `<strong>${agent?.emoji || ''} ${agent?.name || ''}</strong><br>${formatText(text)}`;
        pc.messagesEl.appendChild(div);
        pc.messagesEl.scrollTop = pc.messagesEl.scrollHeight;
    }

    function makeDraggable(el) {
        const header = el.querySelector('[data-drag]');
        let ox, oy, dragging = false;

        header.addEventListener('mousedown', (e) => {
            if (e.target.tagName === 'BUTTON') return;
            dragging = true;
            ox = e.clientX - el.offsetLeft;
            oy = e.clientY - el.offsetTop;
            el.style.position = 'fixed';
        });

        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            el.style.left = `${e.clientX - ox}px`;
            el.style.top = `${e.clientY - oy}px`;
        });

        document.addEventListener('mouseup', () => { dragging = false; });
    }

    // ─── WebSocket ───────────────────────────────────────
    function connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${protocol}//${location.host}/ws`);

        ws.onopen = () => {
            setConnStatus(true);
            clearTimeout(reconnectTimer);
        };
        ws.onclose = () => {
            setConnStatus(false);
            reconnectTimer = setTimeout(connect, 3000);
        };
        ws.onerror = () => setConnStatus(false);
        ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
    }

    function setConnStatus(ok) {
        const dot = document.getElementById('connDot');
        const text = document.getElementById('connText');
        if (dot) dot.className = 'conn-dot' + (ok ? ' connected' : '');
        if (text) text.textContent = ok ? 'Онлайн' : 'Оффлайн';
    }

    function handleMessage(data) {
        switch (data.type) {
            case 'agents_state':
                updateAgents(data.agents);
                break;
            case 'history':
                if (data.channel === 'learning') {
                    data.messages.forEach((m) => addLearningMessage(m));
                } else {
                    data.messages.forEach((m) => addWorkMessage(m));
                }
                break;
            case 'user_message':
                addUserMessage(data.message, data.target);
                break;
            case 'system':
                addSystemMessage(data.message);
                break;
            case 'direct_agent_message':
                if (privateChats[data.agent_id]) {
                    appendPrivateMessage(data.agent_id, 'agent', data.message, agents[data.agent_id]);
                }
                break;
            case 'react_preview':
                if (window.ReactPreview) ReactPreview.onMessage(data);
                break;
            case 'task_history':
                updateTaskHistory(data);
                break;
            case 'pm_plan':
                addPlanMessage(data);
                break;
            case 'site_ready':
                addSystemMessage(data.message || '🌐 Сайт готов! Откройте React Preview.');
                fetch('/api/agents/frontend/preview').then((r) => r.json()).then((d) => {
                    if (d.preview && window.ReactPreview) {
                        ReactPreview.onMessage({
                            ...d.preview,
                            is_site: true,
                            site_url: data.site_url || '/api/sites/latest',
                        });
                    }
                }).catch(() => {});
                break;
            case 'cursor_progress':
            case 'cursor_run_done':
                if (window.Integrations) Integrations.onCursorMessage(data);
                addAgentMessage({ ...data, type: data.type, message: data.message || '' });
                break;
            case 'figma_import':
                if (window.Integrations) Integrations.onFigmaMessage(data);
                addSystemMessage(data.message || `🎨 Figma: ${data.title || 'импорт'}`);
                break;
            case 'github_sync_started':
            case 'github_sync_done':
                addSystemMessage(data.message || '🔗 GitHub Sync');
                if (window.Integrations) Integrations.onCursorMessage(data);
                break;
            case 'direct_user_echo':
                break;
            default:
                if (data.channel === 'learning' || LEARNING_TYPES.has(data.type)) {
                    if (data.agent_id) addLearningAgentMessage(data);
                } else if (data.agent_id) {
                    addAgentMessage(data);
                }
        }
    }

    function updateAgents(agentsList) {
        agentsList.forEach((a) => { agents[a.agent_id] = a; });
        renderAgents();
        if (selectedAgent && agents[selectedAgent]) renderAgentDetail(agents[selectedAgent]);
        if (studioInited && window.StudioApp) StudioApp.updateAgents(agentsList);
        updateStudioLegend();
    }

    function updateStudioLegend() {
        const el = document.getElementById('studioLegend');
        if (!el) return;
        el.innerHTML = AGENT_ORDER.map((id) => {
            const a = agents[id];
            if (!a) return '';
            const loc = a.location_label || a.location || 'студия';
            return `<button type="button" class="legend-item" onclick="openPrivateChat('${id}')">
                ${a.emoji} ${a.name}
                <small>${statusLabel(a.status)} · ${loc}</small>
            </button>`;
        }).join('');
    }

    // ─── Work chat ───────────────────────────────────────
    function removeWelcome(containerId) {
        const el = document.getElementById(containerId || 'messages');
        el?.querySelector('[data-welcome]')?.remove();
    }

    function removeLearningWelcome() {
        document.querySelector('[data-learning-welcome]')?.remove();
    }

    function addWorkMessage(msg) {
        if (msg.type === 'user_message') addUserMessage(msg.message, msg.target);
        else if (msg.type === 'system') addSystemMessage(msg.message);
        else if (msg.type === 'pm_plan') addPlanMessage(msg);
        else if (msg.agent_id) addAgentMessage(msg);
    }

    function addLearningMessage(msg) {
        if (msg.agent_id) addLearningAgentMessage(msg);
    }

    function addAgentMessage(data) {
        removeWelcome('messages');
        const div = document.createElement('div');
        const extraClass = data.type === 'pm_plan' ? ' pm-plan' : (data.type === 'assignment' ? ' assignment' : '');
        div.className = `message ${data.type || ''}${extraClass}`;
        div.innerHTML = `
            <div class="msg-avatar">${data.agent_emoji || '🤖'}</div>
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name">${data.agent_name || 'Агент'}</span>
                    <span class="msg-time">${formatTime(data.timestamp)}</span>
                    <button type="button" class="msg-dm-btn" onclick="openPrivateChat('${data.agent_id}')" title="Личный чат">💬</button>
                </div>
                <div class="msg-text">${formatText(data.message || '')}</div>
            </div>`;
        document.getElementById('messages').appendChild(div);
        scrollToBottom('messages');
    }

    function addPlanMessage(data) {
        removeWelcome('messages');
        const div = document.createElement('div');
        div.className = 'message pm_plan pm-plan';
        div.innerHTML = `
            <div class="msg-avatar">${data.agent_emoji || '🎯'}</div>
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name">${data.agent_name || 'Виктор'} · План</span>
                    <span class="msg-time">${formatTime(data.timestamp)}</span>
                </div>
                <div class="msg-text plan-text">${formatText(data.message || '')}</div>
            </div>`;
        document.getElementById('messages').appendChild(div);
        scrollToBottom('messages');
    }

    function addLearningAgentMessage(data) {
        removeLearningWelcome();
        const div = document.createElement('div');
        div.className = `message learning-msg ${data.type || ''}`;
        div.innerHTML = `
            <div class="msg-avatar">${data.agent_emoji || '🤖'}</div>
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name">${data.agent_name || 'Агент'}</span>
                    <span class="msg-time">${formatTime(data.timestamp)}</span>
                    <span class="learning-badge">${learningTypeLabel(data.type)}</span>
                </div>
                <div class="msg-text">${formatText(data.message || '')}</div>
            </div>`;
        document.getElementById('learningMessages').appendChild(div);
        scrollToBottom('learningMessages');
    }

    function learningTypeLabel(type) {
        return ({
            learning: 'изучает',
            learning_result: 'находка',
            reflection: 'размышление',
            rest: 'отдых',
        }[type] || 'обучение');
    }

    function addUserMessage(text, target) {
        removeWelcome('messages');
        const div = document.createElement('div');
        div.className = 'message user-msg';
        div.innerHTML = `
            <div class="msg-avatar">👤</div>
            <div class="msg-body">
                <div class="msg-header">
                    <span class="msg-name">Вы</span>
                    <span class="msg-time">${target === 'all' ? 'Команда' : target}</span>
                </div>
                <div class="msg-text">${escapeHtml(text)}</div>
            </div>`;
        document.getElementById('messages').appendChild(div);
        scrollToBottom('messages');
    }

    function addSystemMessage(text) {
        removeWelcome('messages');
        const div = document.createElement('div');
        div.className = 'message system';
        div.innerHTML = `<div class="msg-body"><div class="msg-text">${escapeHtml(text)}</div></div>`;
        document.getElementById('messages').appendChild(div);
        scrollToBottom('messages');
    }

    function renderAgents() {
        const list = document.getElementById('agentsList');
        if (!list) return;
        list.innerHTML = AGENT_ORDER.map((id) => {
            const a = agents[id];
            if (!a) return '';
            const topic = a.last_topics?.length ? a.last_topics[a.last_topics.length - 1] : null;
            return `
                <div class="agent-card ${selectedAgent === id ? 'selected' : ''}" onclick="selectAgent('${id}')">
                    <div class="agent-top">
                        <div class="agent-emoji">${a.emoji}</div>
                        <div class="agent-info">
                            <div class="agent-name">${a.name}</div>
                            <div class="agent-role">${a.location_label || a.role}</div>
                        </div>
                        <div class="status-dot status-${a.status}"></div>
                    </div>
                    <div class="agent-meta">
                        <span>${a.learned_count || 0} тем</span>
                        <span>${a.memory_count || 0} задач</span>
                    </div>
                    ${topic ? `<div class="last-topics">${escapeHtml(topic)}</div>` : ''}
                    <button type="button" class="agent-dm" onclick="event.stopPropagation();openPrivateChat('${id}')">Личный чат</button>
                    ${id === 'frontend' ? `<button type="button" class="agent-preview-btn" onclick="event.stopPropagation();openSonyaPreview()">⚛️ React Preview</button>` : ''}
                </div>`;
        }).join('');

        const learnList = document.getElementById('learningAgentsList');
        if (learnList) {
            learnList.innerHTML = AGENT_ORDER.map((id) => {
                const a = agents[id];
                if (!a) return '';
                const isLearning = a.status === 'learning' || a.location === 'library';
                const topic = a.last_topics?.length ? a.last_topics[a.last_topics.length - 1] : '—';
                return `
                    <div class="agent-card compact ${isLearning ? 'learning-active' : ''}">
                        <div class="agent-top">
                            <div class="agent-emoji">${a.emoji}</div>
                            <div class="agent-info">
                                <div class="agent-name">${a.name}</div>
                                <div class="agent-role">${statusLabel(a.status)} · ${a.learned_count || 0} тем</div>
                            </div>
                        </div>
                        <div class="last-topics">${escapeHtml(topic)}</div>
                    </div>`;
            }).join('');
        }
    }

    window.selectAgent = function (id) {
        selectedAgent = id;
        renderAgents();
        if (agents[id]) {
            renderAgentDetail(agents[id]);
            document.getElementById('targetSelect').value = id;
        }
    };

    function renderAgentDetail(a) {
        const topics = a.last_topics?.length
            ? a.last_topics.map((t) => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')
            : '<span class="muted">Пока пусто</span>';
        const sources = a.knowledge_sources?.length ? a.knowledge_sources.join(', ') : '—';

        document.getElementById('agentDetail').innerHTML = `
            <div class="detail-hero">
                <div class="detail-emoji">${a.emoji}</div>
                <div class="detail-name">${a.name}</div>
                <div class="detail-role">${a.role}</div>
                <div class="detail-status">
                    <span class="status-dot status-${a.status}"></span>
                    ${statusLabel(a.status)} · ${a.location_label || 'Студия'}
                </div>
            </div>
            <div class="detail-section">
                <div class="detail-section-title">Описание</div>
                <p>${escapeHtml(a.description || '')}</p>
            </div>
            <div class="detail-section">
                <div class="detail-section-title">Статистика</div>
                <p>Изучено: <strong>${a.learned_count || 0}</strong></p>
                <p>Задач: <strong>${a.memory_count || 0}</strong></p>
                <p>Личных сообщений: <strong>${a.direct_chat_count || 0}</strong></p>
                <p>Источники: <strong>${escapeHtml(sources)}</strong></p>
            </div>
            <div class="detail-section">
                <div class="detail-section-title">Темы</div>
                <div>${topics}</div>
            </div>
            <button class="action-btn" onclick="openPrivateChat('${a.agent_id}')">Личный чат с ${a.name}</button>
            ${a.agent_id === 'frontend' ? `<button class="action-btn secondary" onclick="openSonyaPreview()">⚛️ React Preview</button>` : ''}
            <button class="action-btn secondary" onclick="sendToAgent('${a.agent_id}')">Задача в общий чат</button>`;
    }

    window.openSonyaPreview = function () {
        if (window.ReactPreview) {
            ReactPreview.loadLatest().then(() => ReactPreview.open());
        }
        selectAgent('frontend');
    };

    window.sendToAgent = function (agentId) {
        document.getElementById('targetSelect').value = agentId;
        switchView('chat');
        document.getElementById('messageInput').focus();
    };

    window.sendMessage = function () {
        const input = document.getElementById('messageInput');
        const text = input.value.trim();
        if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
        const target = document.getElementById('targetSelect').value;
        ws.send(JSON.stringify({ type: msgType, text, target }));
        if (msgType === 'task') {
            switchView('tasks');
        }
        input.value = '';
        input.style.height = 'auto';
    };

    // ─── Tasks tab ─────────────────────────────────────────
    const STATUS_LABELS = {
        submitted: 'отправлена',
        queued: 'в очереди',
        in_progress: 'выполняется',
        completed: 'выполнена',
        failed: 'ошибка',
    };

    function updateTaskHistory(data) {
        if (data.stats) taskStats = data.stats;
        if (data.tasks) taskHistory = data.tasks;
        renderTasks();
    }

    async function loadTasks() {
        try {
            const resp = await fetch('/api/tasks');
            if (resp.ok) {
                const data = await resp.json();
                taskStats = data.stats || taskStats;
                taskHistory = data.tasks || [];
                renderTasks();
            }
        } catch (_) {}
    }

    window.filterTasks = function (filter) {
        taskFilter = filter;
        document.querySelectorAll('.filter-btn').forEach((b) => {
            b.classList.toggle('active', b.dataset.filter === filter);
        });
        renderTasks();
    };

    function renderTasks() {
        const list = document.getElementById('tasksList');
        if (!list) return;

        document.getElementById('statCompleted').textContent = taskStats.completed || 0;
        document.getElementById('statActive').textContent = taskStats.active || 0;
        document.getElementById('statTotal').textContent = taskStats.total || 0;

        let items = taskHistory;
        if (taskFilter === 'completed') items = items.filter((t) => t.status === 'completed');
        if (taskFilter === 'active') {
            items = items.filter((t) => ['submitted', 'queued', 'in_progress'].includes(t.status));
        }

        if (!items.length) {
            list.innerHTML = '<div class="tasks-empty">Нет задач в этой категории</div>';
            return;
        }

        list.innerHTML = items.map((t) => {
            const agent = t.agent_emoji && t.agent_name
                ? `${t.agent_emoji} ${t.agent_name}` : (t.target === 'all' ? '👥 Команда' : t.target || '—');
            const time = t.completed_at || t.started_at || t.created_at;
            const timeStr = time ? formatTime(time) : '';
            const isSite = (t.task || '').toLowerCase().match(/сайт|website|лендинг|landing|портал/);
            const siteLink = (t.status === 'completed' && t.agent_id === 'frontend' && isSite)
                ? `<a href="/api/sites/latest" target="_blank" class="site-open-link" style="margin-top:8px">🌐 Открыть готовый сайт</a>`
                : '';
            const response = t.response
                ? `<div class="task-response">${escapeHtml(t.response.slice(0, 400))}${t.response.length > 400 ? '…' : ''}</div>${siteLink}`
                : siteLink;
            return `
                <div class="task-item ${t.status}">
                    <div class="task-item-header">
                        <span class="task-status ${t.status}">${STATUS_LABELS[t.status] || t.status}</span>
                        <span class="task-meta">${agent} · ${timeStr}</span>
                    </div>
                    <div class="task-text">${escapeHtml(t.task || '')}</div>
                    ${response}
                </div>`;
        }).join('');
    }

    window.setMsgType = function (type) {
        msgType = type;
        document.getElementById('typeTask').classList.toggle('active', type === 'task');
        document.getElementById('typeChat').classList.toggle('active', type === 'chat');
    };

    window.clearMessages = function () {
        document.getElementById('messages').innerHTML = `
            <div class="welcome" data-welcome>
                <div class="welcome-icon">✨</div>
                <h2>Рабочий чат очищен</h2>
                <p>Напишите новую задачу — Виктор составит план</p>
            </div>`;
    };

    window.clearLearningMessages = function () {
        document.getElementById('learningMessages').innerHTML = `
            <div class="welcome" data-learning-welcome>
                <div class="welcome-icon">📚</div>
                <h2>Чат обучения очищен</h2>
                <p>Агенты продолжат публиковать находки здесь</p>
            </div>`;
    };

    window.showSettings = async function () {
        document.getElementById('settingsModal').classList.add('show');
        try {
            const resp = await fetch('/api/config');
            if (resp.ok) {
                const cfg = await resp.json();
                document.getElementById('learnMinInput').value = cfg.learning_interval_min || 15;
                document.getElementById('learnMaxInput').value = cfg.learning_interval_max || 45;
                document.getElementById('persistInput').checked = cfg.persist_knowledge !== false;
                document.getElementById('cursorRepoInput').value = cfg.cursor_repo_url || '';
                document.getElementById('cursorRefInput').value = cfg.cursor_repo_ref || 'main';
                document.getElementById('cursorEnabledInput').checked = cfg.cursor_enabled !== false;
                document.getElementById('cursorGithubSyncInput').checked = cfg.cursor_github_sync !== false;
                document.getElementById('cursorAutoPrInput').checked = cfg.cursor_auto_create_pr !== false;
            }
        } catch (_) {}
        if (window.Integrations) Integrations.loadCursorStatus();
    };

    window.hideSettings = function () {
        document.getElementById('settingsModal').classList.remove('show');
    };

    window.saveSettings = async function () {
        try {
            const resp = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    learning_interval_min: parseInt(document.getElementById('learnMinInput').value, 10),
                    learning_interval_max: parseInt(document.getElementById('learnMaxInput').value, 10),
                    persist_knowledge: document.getElementById('persistInput').checked,
                    cursor_repo_url: document.getElementById('cursorRepoInput').value,
                    cursor_repo_ref: document.getElementById('cursorRefInput').value,
                    cursor_enabled: document.getElementById('cursorEnabledInput').checked,
                    cursor_github_sync: document.getElementById('cursorGithubSyncInput').checked,
                    cursor_auto_create_pr: document.getElementById('cursorAutoPrInput').checked,
                }),
            });
            if (resp.ok) {
                hideSettings();
                addSystemMessage('Настройки обучения сохранены');
            }
        } catch (_) {
            addSystemMessage('Ошибка сохранения');
        }
    };

    function statusLabel(s) {
        return ({ idle: 'ожидание', working: 'работает', learning: 'учится', thinking: 'думает', resting: 'отдых' }[s] || s);
    }

    function formatTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
        } catch { return ''; }
    }

    function formatText(text) {
        text = escapeHtml(text);
        text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        text = text.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
        return text;
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function scrollToBottom(containerId) {
        const c = document.getElementById(containerId || 'messages');
        if (c) c.scrollTop = c.scrollHeight;
    }

    // ─── Init ────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', () => {
        applyTheme(getPreferredTheme());
        connect();
        switchView('studio');
        if (window.ReactPreview) ReactPreview.loadLatest();
        if (window.Integrations) Integrations.loadCursorStatus();

        document.getElementById('messageInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.getElementById('messageInput')?.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
        });
    });
})();
