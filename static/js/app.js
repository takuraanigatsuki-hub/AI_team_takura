/**
 * AI Team Room — чат, личные диалоги, WebSocket
 */
(function () {
    const THEME_KEY = 'ai-team-room-theme';
    const AGENT_ORDER = ['pm', 'architect', 'backend', 'frontend', 'qa', 'reviewer', 'doc_writer', 'devops', 'cursor', 'security', 'evaluator'];
    const LEARNING_AGENT_ORDER = ['evaluator', 'pm', 'architect', 'backend', 'frontend', 'qa', 'reviewer', 'doc_writer', 'devops', 'cursor'];
    const LEARNING_TYPES = new Set([
        'learning', 'learning_result', 'reflection', 'rest', 'figma_study',
        'peer_learning', 'peer_discussion', 'skill_evaluation', 'learning_project',
    ]);

    let ws = null;
    let msgType = 'task';
    let selectedAgent = null;
    let agents = {};
    let reconnectTimer = null;
    let studioInited = false;
    const privateChats = {};
    let privateChatZIndex = 350;
    let taskHistory = [];
    let taskFilter = 'all';
    let taskSearchQuery = '';
    let learningSearchQuery = '';
    let taskStats = { total: 0, completed: 0, active: 0 };

    // ─── Theme ───────────────────────────────────────────
    function getPreferredTheme() {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved === 'light' || saved === 'dark') return saved;
        return 'dark';
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
    window.applyTheme = applyTheme;

    // ─── Views ───────────────────────────────────────────
    let dashboardRefreshTimer = null;
    let agentLearningPanel = 'learning';

    const AGENT_LEARNING_VIEWS = new Set(['agent-learning', 'learning', 'design', 'masha']);
    const INVESTOR_VIEWS = new Set(['investor', 'profile', 'studio', 'dashboard', 'projects']);

    function canViewAgentLearning(user) {
        if (!user) return false;
        if (user.can_view_agent_learning) return true;
        return ['owner', 'admin', 'tech_admin'].includes(user.role);
    }

    function isPrivilegedUser(user) {
        if (!user) return false;
        if (user.is_owner) return true;
        return ['owner', 'admin', 'tech_admin'].includes(user.role);
    }

    function filterAgentsForViewer(agents) {
        if (isPrivilegedUser(window.Auth?.getUser())) return agents || [];
        return (agents || []).filter((a) => (a.agent_id || '') !== 'security');
    }

    function shouldShowWsMessage(data) {
        if (isPrivilegedUser(window.Auth?.getUser())) return true;
        const hiddenTypes = new Set([
            'security_alert', 'github_sync_started', 'github_sync_done',
            'git_sync_done', 'cursor_progress',
        ]);
        if (hiddenTypes.has(data.type)) return false;
        if ((data.agent_id || '').toLowerCase() === 'security') return false;
        const text = (data.message || data.text || '').toLowerCase();
        if (/github sync|git sync|security alert|threat:|ip заблок/.test(text)) return false;
        return true;
    }

    window.switchAgentLearningPanel = function (panel) {
        if (panel === 'design') agentLearningPanel = 'design';
        else if (panel === 'masha') agentLearningPanel = 'masha';
        else agentLearningPanel = 'learning';
        switchView('agent-learning');
    };

    window.switchView = function (view) {
        const user = window.Auth?.getUser();
        if (view === 'admin') {
            if (!window.AdminPanel?.canAccess(user)) {
                const msg = 'Панель Admin доступна только владельцу и администраторам';
                if (window.UIEnhancements) UIEnhancements.toast(msg, 'warn');
                else alert(msg);
                switchView('profile');
                return;
            }
        } else if (view === 'investor') {
            if (!window.Auth?.canViewInvestorPortal?.(user)) {
                const msg = 'Investor Portal — войдите с ролью investor или admin';
                if (window.UIEnhancements) UIEnhancements.toast(msg, 'warn');
                else alert(msg);
                switchView(user ? 'profile' : 'tasks');
                return;
            }
        } else if (user && (user.role === 'investor' || user.is_investor) && !INVESTOR_VIEWS.has(view)) {
            if (window.UIEnhancements) UIEnhancements.toast('Investor — доступны только разделы просмотра', 'warn');
            switchView('investor');
            return;
        } else if (AGENT_LEARNING_VIEWS.has(view)) {
            if (!canViewAgentLearning(user)) {
                const msg = 'Обучение агентов доступно только администраторам';
                if (window.UIEnhancements) UIEnhancements.toast(msg, 'warn');
                else alert(msg);
                switchView('studio');
                return;
            }
            if (view === 'learning' || view === 'design' || view === 'masha') {
                agentLearningPanel = view === 'design' ? 'design' : (view === 'masha' ? 'masha' : 'learning');
                view = 'agent-learning';
            }
        } else if (user && window.ProfileCabinet && !ProfileCabinet.canAccessView(user, view)) {
            const sub = user.subscription || {};
            const msg = `Нужен тариф выше. Ваш: ${sub.tier_name || 'Free'} (ур. ${sub.level || 1})`;
            if (window.UIEnhancements) UIEnhancements.toast(msg, 'warn');
            else alert(msg);
            switchView('profile');
            if (window.ProfileCabinet) ProfileCabinet.switchTab('subscription');
            return;
        }

        document.querySelectorAll('.view-tab').forEach((t) => {
            const v = t.dataset.view;
            const active = v === view || (view === 'agent-learning' && v === 'agent-learning');
            t.classList.toggle('active', active);
        });
        document.querySelectorAll('.main > [id$="View"]').forEach((el) => {
            el.classList.remove('view-enter');
        });
        const isAgentLearning = view === 'agent-learning';
        document.getElementById('agentLearningSubnav')?.classList.toggle('hidden', !isAgentLearning);
        document.getElementById('alTabLearning')?.classList.toggle('active', isAgentLearning && agentLearningPanel === 'learning');
        document.getElementById('alTabMasha')?.classList.toggle('active', isAgentLearning && agentLearningPanel === 'masha');
        document.getElementById('alTabDesign')?.classList.toggle('active', isAgentLearning && agentLearningPanel === 'design');

        document.getElementById('studioView').classList.toggle('hidden', view !== 'studio');
        document.getElementById('chatView').classList.toggle('hidden', view !== 'chat');
        document.getElementById('learningView').classList.toggle('hidden', !isAgentLearning || agentLearningPanel !== 'learning');
        document.getElementById('tasksView').classList.toggle('hidden', view !== 'tasks');
        document.getElementById('mashaView')?.classList.toggle('hidden', !isAgentLearning || agentLearningPanel !== 'masha');
        document.getElementById('designView')?.classList.toggle('hidden', !isAgentLearning || agentLearningPanel !== 'design');
        document.getElementById('sonyaStudioView')?.classList.toggle('hidden', view !== 'sonya-studio');
        document.getElementById('dashboardView')?.classList.toggle('hidden', view !== 'dashboard');
        document.getElementById('kanbanView')?.classList.toggle('hidden', view !== 'kanban');
        document.getElementById('sprintView')?.classList.toggle('hidden', view !== 'sprint');
        document.getElementById('timelineView')?.classList.toggle('hidden', view !== 'timeline');
        document.getElementById('projectsView')?.classList.toggle('hidden', view !== 'projects');
        document.getElementById('profileView')?.classList.toggle('hidden', view !== 'profile');
        document.getElementById('adminView')?.classList.toggle('hidden', view !== 'admin');
        document.getElementById('investorView')?.classList.toggle('hidden', view !== 'investor');

        if (window.SidebarNav) SidebarNav.setActive(view);
        if (window.UICore) UICore.setMobileTabActive(view);
        if (view === 'tasks') {
            loadTasks();
            if (window.UICore) {
                UICore.initGuestOnboarding();
                const aw = taskStats?.awaiting_approval || 0;
                if (aw > 0) setTimeout(() => UICore.checkAwaitingCoachmark(aw), 400);
            }
        }
        if (view === 'projects' && window.ProjectsUI) ProjectsUI.load();
        if (view === 'kanban' && window.KanbanUI) KanbanUI.refresh();
        if (view === 'sprint' && window.SprintUI) SprintUI.load();
        if (view === 'timeline' && window.TimelineUI) TimelineUI.load(1);
        if (isAgentLearning && agentLearningPanel === 'learning') {
            loadLearningHistory(true);
        }
        if (isAgentLearning && agentLearningPanel === 'design' && window.SonyaDesignLab) {
            SonyaDesignLab.load();
        }
        if (isAgentLearning && agentLearningPanel === 'masha' && window.MashaLearningLab) {
            MashaLearningLab.load();
        }
        if (view === 'sonya-studio' && window.SonyaStudio) SonyaStudio.load();
        if (view === 'dashboard' && window.Dashboard) Dashboard.load();
        if (view === 'dashboard' && window.PowerPack) PowerPack.loadCostWidget();
        if (view === 'investor' && window.InvestorPortal) InvestorPortal.load();
        if (view === 'profile' && window.ProfileCabinet) ProfileCabinet.load();
        if (view === 'admin' && window.AdminPanel) AdminPanel.load();

        clearInterval(dashboardRefreshTimer);
        if (view === 'dashboard') {
            dashboardRefreshTimer = setInterval(() => {
                if (window.Dashboard) Dashboard.load();
            }, 30000);
        }

        if (view === 'studio') {
            document.getElementById('studioView')?.classList.add('view-enter');
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    if (!studioInited) {
                        initStudio();
                    } else if (window.StudioApp) {
                        const canvas = document.getElementById('studioCanvas');
                        StudioApp.wake(canvas);
                        if (window.StudioMinimap) StudioMinimap.update(Object.values(agents));
                    }
                });
            });
        } else {
            const viewElId = {
                chat: 'chatView', tasks: 'tasksView', dashboard: 'dashboardView',
                kanban: 'kanbanView', sprint: 'sprintView', timeline: 'timelineView',
                projects: 'projectsView', profile: 'profileView', admin: 'adminView',
                investor: 'investorView', 'sonya-studio': 'sonyaStudioView',
                'agent-learning': 'agentLearningSubnav',
            }[view];
            const viewEl = viewElId ? document.getElementById(viewElId) : null;
            if (viewEl && !viewEl.classList.contains('hidden')) {
                viewEl.classList.add('view-enter');
            }
        }
    };

    function updateChatWelcome() {
        const welcome = document.querySelector('[data-welcome]');
        if (!welcome) return;
        const user = window.Auth?.getUser?.();
        const h2 = welcome.querySelector('h2');
        const p = welcome.querySelector('p');
        if (!h2 || !p) return;
        if (user) {
            const name = user.name || user.email?.split('@')[0] || 'друг';
            h2.textContent = `Привет, ${name}!`;
            p.textContent = 'Опишите задачу — Виктор распределит её по команде. Ваши задачи видны только вам.';
        } else {
            h2.textContent = 'Рабочий чат';
            p.textContent = 'Задачи, планы Виктора и результаты работы. Войдите, чтобы сохранять историю.';
        }
    }

    function hideStudioLoading() {
        document.getElementById('studioLoading')?.classList.add('hidden');
    }

    function showStudioLoading() {
        document.getElementById('studioLoading')?.classList.remove('hidden');
    }

    let threeWaitAttempts = 0;

    function initStudio() {
        const canvas = document.getElementById('studioCanvas');
        if (!canvas || !window.StudioApp) return;

        if (typeof THREE === 'undefined') {
            threeWaitAttempts += 1;
            if (threeWaitAttempts > 40) {
                hideStudioLoading();
                const err = document.getElementById('studioError');
                if (err) {
                    err.textContent = 'Three.js не загружен. Обновите страницу (Ctrl+F5) или очистите кэш PWA.';
                    err.style.display = 'flex';
                }
                return;
            }
            setTimeout(initStudio, 150);
            return;
        }

        showStudioLoading();
        let attempts = 0;
        const tryInit = () => {
            attempts += 1;
            const ok = StudioApp.init(canvas, openPrivateChat);
            if (ok) {
                studioInited = true;
                hideStudioLoading();
                if (Object.keys(agents).length) {
                    StudioApp.updateAgents(Object.values(agents));
                }
                updateStudioLegend();
                if (window.StudioMinimap) StudioMinimap.update(Object.values(agents));
                return;
            }
            if (attempts < 60) {
                requestAnimationFrame(tryInit);
                return;
            }
            hideStudioLoading();
            const err = document.getElementById('studioError');
            if (err) {
                err.textContent = 'Не удалось запустить 3D-сцену. Обновите страницу (Ctrl+F5).';
                err.style.display = 'flex';
            }
        };

        requestAnimationFrame(tryInit);
    }

    // ─── Private chat windows ────────────────────────────
    window.openPrivateChat = async function (agentId) {
        const agent = agents[agentId];
        if (!agent) return;

        if (privateChats[agentId]) {
            const pc = privateChats[agentId];
            pc.el.classList.remove('minimized');
            pc.el.style.zIndex = String(++privateChatZIndex);
            pc.input.focus();
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
                <input type="text" placeholder="Задача или вопрос ${agent.name}…" />
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
        const normalized = String(text || '').trim();
        if (normalized) {
            const last = pc.messagesEl.querySelector('.pc-msg:last-child');
            if (last && last.dataset.msgText === normalized && last.classList.contains(role)) {
                return;
            }
        }
        const div = document.createElement('div');
        div.className = `pc-msg ${role}`;
        if (normalized) div.dataset.msgText = normalized;
        div.innerHTML = role === 'user'
            ? escapeHtml(text)
            : `<strong>${agent?.emoji || ''} ${agent?.name || ''}</strong><br>${formatText(text)}`;
        pc.messagesEl.appendChild(div);
        pc.messagesEl.scrollTop = pc.messagesEl.scrollHeight;
    }

    function makeDraggable(el) {
        const header = el.querySelector('[data-drag]');
        if (!header) return;

        let dragging = false;
        let startX = 0;
        let startY = 0;
        let startLeft = 0;
        let startTop = 0;

        const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

        const onMouseMove = (e) => {
            if (!dragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            const w = el.offsetWidth;
            const h = el.offsetHeight;
            const left = clamp(startLeft + dx, 8, window.innerWidth - w - 8);
            const top = clamp(startTop + dy, 8, window.innerHeight - h - 8);
            el.style.left = `${left}px`;
            el.style.top = `${top}px`;
        };

        const onMouseUp = () => {
            dragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        header.addEventListener('mousedown', (e) => {
            if (e.button !== 0 || e.target.tagName === 'BUTTON') return;
            e.preventDefault();

            const rect = el.getBoundingClientRect();
            dragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = rect.left;
            startTop = rect.top;

            if (el.parentElement?.id === 'privateChatsContainer') {
                document.body.appendChild(el);
            }

            el.style.position = 'fixed';
            el.style.left = `${startLeft}px`;
            el.style.top = `${startTop}px`;
            el.style.width = `${rect.width}px`;
            el.style.right = 'auto';
            el.style.bottom = 'auto';
            el.style.margin = '0';
            el.style.zIndex = String(++privateChatZIndex);
            el.classList.add('private-chat-floating');

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
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
            setConnStatus(false, 'reconnecting');
            reconnectTimer = setTimeout(connect, 3000);
        };
        ws.onerror = () => setConnStatus(false, 'reconnecting');
        ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
    }

    function setConnStatus(ok, mode) {
        const dot = document.getElementById('connDot');
        const text = document.getElementById('connText');
        const wasOk = dot?.classList.contains('connected');
        if (dot) {
            dot.className = 'conn-dot' + (ok ? ' connected' : (mode === 'reconnecting' ? ' reconnecting' : ''));
        }
        if (text) {
            text.textContent = ok ? 'Онлайн' : (mode === 'reconnecting' ? 'Переподключение…' : 'Оффлайн');
        }
        if (window.UIEnhancements && wasOk && !ok) {
            UIEnhancements.toast('🔴 Соединение потеряно — переподключение…', 'error');
        }
        if (window.UICore) {
            UICore.updateHeaderContext({
                online: ok,
                reconnecting: !ok && mode === 'reconnecting',
            });
        }
        if (ok && window.SoundFX) SoundFX.connect();
    }

    function onAgentEffects(data) {
        if (!data.agent_id) return;
        const plain = String(data.message || '').replace(/[*#_`]/g, '').slice(0, 48);
        if (plain && window.StudioApp) StudioApp.showSpeechBubble(data.agent_id, plain);
        if (data.type === 'task_done') {
            if (window.StudioApp) StudioApp.burstConfetti(data.agent_id);
            if (window.SoundFX) SoundFX.taskDone();
        }
    }

    function handleMessage(data) {
        if (window.UICore?.ActivityStream) UICore.ActivityStream.onWsMessage(data);
        if (window.FeaturePack) FeaturePack.onWsMessage(data);
        if (!shouldShowWsMessage(data) && data.type !== 'agents_state' && data.type !== 'task_history' && data.type !== 'history') {
            return;
        }
        switch (data.type) {
            case 'agents_state':
                updateAgents(filterAgentsForViewer(data.agents));
                break;
            case 'history':
                if (data.channel === 'learning') {
                    if (canViewAgentLearning(window.Auth?.getUser())) {
                        data.messages.forEach((m) => {
                            if (shouldShowWsMessage(m)) addLearningMessage(m);
                        });
                    }
                } else {
                    data.messages.forEach((m) => {
                        if (shouldShowWsMessage(m)) addWorkMessage(m);
                    });
                }
                break;
            case 'user_message':
                addUserMessage(data.message, data.target);
                break;
            case 'system':
                addSystemMessage(data.message);
                break;
            case 'direct_agent_message':
                (async () => {
                    await openPrivateChat(data.agent_id);
                    appendPrivateMessage(
                        data.agent_id,
                        'agent',
                        data.message,
                        agents[data.agent_id]
                    );
                })();
                break;
            case 'react_preview':
                if (window.ReactPreview) ReactPreview.onMessage(data);
                if (window.StudioApp?.pulseScreen) StudioApp.pulseScreen('frontend');
                break;
            case 'task_history':
                updateTaskHistory(data);
                break;
            case 'pm_plan':
                addPlanMessage(data);
                break;
            case 'pipeline_update':
                if (window.PipelineUI) PipelineUI.onUpdate(data);
                if (data.pipeline?.finished_at && window.SoundFX) SoundFX.pipelineDone();
                break;
            case 'presence_update':
                if (window.WowFeatures) WowFeatures.updatePresence(data);
                break;
            case 'deploy_ready':
                addSystemMessage(data.message || '🚀 Deploy готов');
                if (window.SoundFX) SoundFX.deploy();
                notifyPush('Deploy готов', data.message || 'ZIP bundle создан');
                break;
            case 'agent_stream_start':
                if (window.AgentStream) AgentStream.onStart(data);
                break;
            case 'agent_stream':
                if (window.AgentStream) AgentStream.onChunk(data);
                break;
            case 'agent_debate':
                if (window.DebateUI) DebateUI.show(data);
                break;
            case 'pr_ready':
                addLinkMessage(data.message || '🔗 PR / Commit готов', data.pr_url || data.commit_url);
                break;
            case 'artifact_created':
                addSystemMessage(data.message || `📦 ${data.title || 'Проект'}`);
                if (window.ProjectsUI && document.getElementById('projectsView') && !document.getElementById('projectsView').classList.contains('hidden')) {
                    ProjectsUI.load();
                }
                break;
            case 'site_ready':
                addResultReadyMessage(data);
                fetch('/api/agents/frontend/preview', { credentials: 'same-origin' }).then((r) => r.json()).then((d) => {
                    if (d.preview && window.ReactPreview) {
                        ReactPreview.onMessage({
                            ...d.preview,
                            is_site: true,
                            site_url: data.site_url || '/api/sites/latest',
                        });
                    }
                }).catch(() => {});
                break;
            case 'task_awaiting_approval':
                loadTasks().then(() => {
                    if (window.PipelineUI?.onTaskHistory && taskHistory) {
                        PipelineUI.onTaskHistory(taskHistory, taskStats);
                    }
                });
                addAgentMessage({
                    ...data,
                    agent_id: data.agent_id || 'pm',
                    agent_name: data.agent_name || 'Виктор',
                    agent_emoji: data.agent_emoji || '🎯',
                    type: 'message',
                    message: data.message || '⏳ Задача ждёт подтверждения',
                });
                const tasksOpen = document.getElementById('tasksView') && !document.getElementById('tasksView').classList.contains('hidden');
                if (!tasksOpen && window.UIEnhancements) {
                    UIEnhancements.toast('⏳ Виктор ждёт вашего решения', 'info');
                }
                break;
            case 'task_approved':
            case 'task_revision':
                if (window.UICore) UICore.dismissAwaitingCoachmark();
                if (data.agent_id) {
                    addAgentMessage({ ...data, type: 'message', message: data.message || '' });
                } else {
                    addSystemMessage(data.message || '');
                }
                if (window.UIEnhancements) {
                    UIEnhancements.toast(
                        data.type === 'task_approved' ? '✅ Задача принята' : '✎ Отправлено на доработку',
                        data.type === 'task_approved' ? 'success' : 'info',
                    );
                }
                loadTasks();
                break;
            case 'role_triage':
                addAgentMessage({ ...data, type: 'message', message: data.message || '' });
                break;
            case 'peer_learning':
            case 'peer_discussion':
            case 'learning':
            case 'learning_result':
            case 'reflection':
            case 'rest':
            case 'figma_study':
            case 'learning_project':
                if (canViewAgentLearning(window.Auth?.getUser())) {
                    addLearningAgentMessage(data);
                }
                if (data.type === 'figma_study' && window.SonyaDesignLab) SonyaDesignLab.loadLab();
                if (window.MashaLearningLab) MashaLearningLab.onMessage(data);
                break;
            case 'skill_evaluation':
                if (canViewAgentLearning(window.Auth?.getUser()) && window.MashaLearningLab) {
                    MashaLearningLab.onEvalMessage(data);
                }
                break;
            case 'result_ready':
                addResultReadyMessage(data);
                if (data.open_preview && window.ReactPreview) {
                    fetch('/api/agents/frontend/preview', { credentials: 'same-origin' }).then((r) => r.json()).then((d) => {
                        if (d.preview) ReactPreview.onMessage({ ...d.preview, is_site: data.is_site, site_url: data.site_url });
                    }).catch(() => {});
                }
                break;
            case 'm365_ready':
                addLinkMessage(data.message || '📎 Microsoft 365', data.web_url);
                if (window.UIEnhancements) UIEnhancements.toast(data.title || 'M365', 'success');
                break;
            case 'm365_hint':
                addSystemMessage(data.message || 'Microsoft 365 не настроен');
                break;
            case 'cursor_progress':
            case 'cursor_run_done':
                if (!isPrivilegedUser(window.Auth?.getUser())) break;
                if (window.Integrations) Integrations.onCursorMessage(data);
                addAgentMessage({ ...data, type: data.type, message: data.message || '' });
                break;
            case 'figma_import':
                if (window.Integrations) Integrations.onFigmaMessage(data);
                addSystemMessage(data.message || `🎨 Figma: ${data.title || 'импорт'}`);
                break;
            case 'figma_portfolio':
                if (window.UIEnhancements) UIEnhancements.toast(`✨ ${data.title || 'Новый проект'}`, 'success');
                if (window.Integrations) Integrations.loadSonyaStudio();
                addAgentMessage({ ...data, type: 'figma_portfolio', message: data.message || '' });
                break;
            case 'sonya_studio_project':
            case 'sonya_studio_update':
            case 'sonya_studio_published':
                if (window.SonyaStudio) SonyaStudio.onMessage(data);
                if (window.UIEnhancements) UIEnhancements.toast(data.message || 'Sonya Studio', 'success');
                addAgentMessage({ ...data, type: data.type, message: data.message || '' });
                if (data.preview && window.ReactPreview) ReactPreview.onMessage(data.preview);
                break;
            case 'sonya_studio_hint':
                if (data.open_view) switchView(data.open_view);
                if (window.UIEnhancements) UIEnhancements.toast(data.message || 'Sonya Studio', 'info');
                addAgentMessage({ ...data, type: 'message', message: data.message || '' });
                break;
            case 'github_sync_started':
            case 'github_sync_done':
            case 'git_sync_done':
                if (!isPrivilegedUser(window.Auth?.getUser())) break;
                if (data.type !== 'git_sync_done') {
                    addLinkMessage(data.message || '🔗 GitHub Sync', data.pr_url || data.branch_url);
                } else {
                    addLinkMessage(data.message || '📤 Изменения на GitHub', data.commit_url);
                }
                if (window.Integrations) Integrations.onCursorMessage(data);
                if (data.type === 'github_sync_done' && window.SoundFX) SoundFX.gitPush();
                if (data.type === 'git_sync_done') {
                    if (window.UIEnhancements) UIEnhancements.onGitSync(data);
                    if (window.SoundFX) SoundFX.gitPush();
                }
                notifyPush('GitHub Sync', data.message || 'Синхронизация завершена');
                break;
            case 'direct_user_echo':
                break;
            default:
                if (data.channel === 'learning' || (LEARNING_TYPES.has(data.type) && data.type !== 'skill_evaluation')) {
                    if (!canViewAgentLearning(window.Auth?.getUser())) break;
                    if (data.type === 'figma_study') {
                        addLearningAgentMessage({ ...data, type: 'figma_study', message: data.message || '' });
                        if (window.SonyaDesignLab) SonyaDesignLab.loadLab();
                    } else if (data.agent_id) addLearningAgentMessage(data);
                } else if (data.agent_id) {
                    if ((data.agent_id || '').toLowerCase() === 'security' && !isPrivilegedUser(window.Auth?.getUser())) break;
                    addAgentMessage(data);
                    onAgentEffects(data);
                    if (data.type === 'task_done') notifyPush(data.agent_name || 'Агент', String(data.message || '').slice(0, 80));
                }
        }
    }

    function addLinkMessage(text, url) {
        const container = document.getElementById('messages');
        if (!container) return;
        const welcome = container.querySelector('[data-welcome]');
        if (welcome) welcome.remove();
        const div = document.createElement('div');
        div.className = 'message system';
        let html = formatText(text);
        if (url) {
            html += ` <a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="pr-link">Открыть →</a>`;
        }
        div.innerHTML = `<div class="msg-body">${html}</div>`;
        container.appendChild(div);
        scrollToBottom('messages');
    }

    function addResultReadyMessage(data) {
        const container = document.getElementById('messages');
        if (!container) return;
        const welcome = container.querySelector('[data-welcome]');
        if (welcome) welcome.remove();
        const div = document.createElement('div');
        div.className = 'message result-ready';
        const who = data.agent_emoji && data.agent_name ? `${data.agent_emoji} ${data.agent_name}` : 'Команда';
        let html = `<div class="msg-header">${escapeHtml(who)}</div><div class="msg-body">${formatText(data.message || 'Готово')}</div>`;
        html += '<div class="result-ready-actions">';
        if (data.download_url) {
            const dlLabel = data.is_presentation ? '📥 PowerPoint (.pptx)' : '📥 Скачать файл';
            html += `<a class="btn-primary btn-sm" href="${escapeHtml(data.download_url)}" target="_blank" rel="noopener">${dlLabel}</a>`;
        }
        if (data.site_url && !data.is_presentation) {
            html += `<a class="btn-secondary btn-sm" href="${escapeHtml(data.site_url)}" target="_blank" rel="noopener">🌐 Открыть сайт</a>`;
        }
        if (data.preview_url) {
            const pl = data.is_presentation ? '📽️ Слайды' : '👁 Preview';
            html += `<a class="btn-secondary btn-sm" href="${escapeHtml(data.preview_url)}" target="_blank" rel="noopener">${pl}</a>`;
        }
        if (data.open_preview && window.ReactPreview && !data.is_presentation) {
            html += `<button type="button" class="btn-primary btn-sm" onclick="ReactPreview.toggle()">🎨 React Preview</button>`;
        }
        html += '</div>';
        div.innerHTML = html;
        container.appendChild(div);
        scrollToBottom('messages');
        if (window.UIEnhancements) UIEnhancements.toast(data.title || 'Готово', 'success');
    }

    async function notifyPush(title, body) {
        if (!('Notification' in window) || Notification.permission !== 'granted') return;
        try {
            const reg = await navigator.serviceWorker?.ready;
            if (reg?.showNotification) {
                reg.showNotification(title || 'AI Team', { body: body || '', icon: '/static/icons/icon-192.png' });
            } else {
                new Notification(title || 'AI Team', { body: body || '', icon: '/static/icons/icon-192.png' });
            }
        } catch (_) { /* ignore */ }
    }

    function updateAgents(agentsList) {
        agentsList.forEach((a) => { agents[a.agent_id] = a; });
        renderAgents();
        if (selectedAgent && agents[selectedAgent]) renderAgentDetail(agents[selectedAgent]);
        if (studioInited && window.StudioApp) StudioApp.updateAgents(agentsList);
        updateStudioLegend();
        if (window.StudioMinimap) StudioMinimap.update(agentsList);
        const working = agentsList.filter((a) => ['working', 'learning', 'thinking'].includes(a.status)).length;
        if (window.UIEnhancements) UIEnhancements.updateAgentFooter(working);
        if (window.UICore) UICore.updateHeaderContext({ agentsWorking: working });
    }

    function updateStudioLegend() {
        const el = document.getElementById('studioLegend');
        if (!el) return;
        el.innerHTML = AGENT_ORDER.map((id) => {
            const a = agents[id];
            if (!a) return '';
            return `<button type="button" class="legend-item" onclick="openPrivateChat('${id}')">
                <span class="legend-emoji">${a.emoji}</span>
                <span class="legend-name">${a.name}</span>
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
        if (msg.type === 'skill_evaluation') return;
        if (LEARNING_TYPES.has(msg.type) && msg.type !== 'skill_evaluation') return;
        if (msg.channel === 'learning') return;
        if (msg.type === 'user_message') addUserMessage(msg.message, msg.target);
        else if (msg.type === 'system') addSystemMessage(msg.message);
        else if (msg.type === 'pm_plan') addPlanMessage(msg);
        else if (msg.agent_id) addAgentMessage(msg);
    }

    function addLearningMessage(msg) {
        if (msg.type === 'skill_evaluation') {
            if (canViewAgentLearning(window.Auth?.getUser()) && window.MashaLearningLab) {
                MashaLearningLab.onEvalMessage(msg);
            }
            return;
        }
        if (msg.agent_id) addLearningAgentMessage(msg);
    }

    function addAgentMessage(data) {
        removeWelcome('messages');
        const div = document.createElement('div');
        const extraClass = data.type === 'pm_plan' ? ' pm-plan' : (data.type === 'assignment' ? ' assignment' : '');
        div.className = `message ${data.type || ''}${extraClass}`;
        const searchText = `${data.agent_name || ''} ${data.message || ''}`.toLowerCase();
        div.dataset.searchText = searchText;
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
        if (data.type === 'task_done' && window.UIEnhancements) {
            UIEnhancements.toast(`✅ ${data.agent_name || 'Агент'}: задача выполнена`, 'success');
        }
        applyChatSearchFilter();
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
        if (data.type === 'skill_evaluation') {
            if (canViewAgentLearning(window.Auth?.getUser()) && window.MashaLearningLab) {
                MashaLearningLab.onEvalMessage(data);
            }
            return;
        }
        removeLearningWelcome();
        const div = document.createElement('div');
        div.className = `message learning-msg ${data.type || ''}`;
        div.dataset.searchText = `${data.agent_name || ''} ${data.message || ''}`.toLowerCase();
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
        applyLearningSearchFilter();
    }

    function learningTypeLabel(type) {
        return ({
            learning: 'изучает',
            learning_result: 'находка',
            reflection: 'размышление',
            rest: 'отдых',
            figma_study: '🎨 дизайн',
            peer_learning: 'практика',
            peer_discussion: 'диалог',
            skill_evaluation: '🎓 оценка',
            learning_project: '🎓 упражнение',
        }[type] || 'обучение');
    }

    let learningHistoryLoaded = false;

    async function loadLearningHistory(force = false) {
        if (!canViewAgentLearning(window.Auth?.getUser())) return;
        try {
            const r = await fetch('/api/history', { credentials: 'same-origin' });
            if (!r.ok) return;
            const data = await r.json();
            const msgs = data.learning || [];
            const container = document.getElementById('learningMessages');
            if (!container) return;
            if (!force && learningHistoryLoaded) return;
            learningHistoryLoaded = true;
            if (msgs.length) {
                container.innerHTML = '';
                msgs.slice(-120).forEach((m) => addLearningAgentMessage(m));
                scrollToBottom('learningMessages');
            }
        } catch (_) { /* ignore */ }
    }

    function addUserMessage(text, target) {
        removeWelcome('messages');
        const div = document.createElement('div');
        div.className = 'message user-msg';
        div.dataset.searchText = `вы ${text} ${target}`.toLowerCase();
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
        applyChatSearchFilter();
    }

    function addSystemMessage(text) {
        removeWelcome('messages');
        const div = document.createElement('div');
        div.className = 'message system';
        div.dataset.searchText = String(text).toLowerCase();
        div.innerHTML = `<div class="msg-body"><div class="msg-text">${escapeHtml(text)}</div></div>`;
        document.getElementById('messages').appendChild(div);
        scrollToBottom('messages');
        applyChatSearchFilter();
    }

    let chatSearchQuery = '';

    function applyChatSearchFilter() {
        const q = chatSearchQuery;
        document.querySelectorAll('#messages .message').forEach((el) => {
            if (!q) {
                el.classList.remove('search-hidden');
                return;
            }
            const text = el.dataset.searchText || el.textContent.toLowerCase();
            el.classList.toggle('search-hidden', !text.includes(q));
        });
    }

    window.filterChatMessages = function (query) {
        chatSearchQuery = query.trim().toLowerCase();
        applyChatSearchFilter();
    };

    function applyLearningSearchFilter() {
        const q = learningSearchQuery;
        document.querySelectorAll('#learningMessages .message').forEach((el) => {
            if (!q) {
                el.classList.remove('search-hidden');
                return;
            }
            const text = el.dataset.searchText || el.textContent.toLowerCase();
            el.classList.toggle('search-hidden', !text.includes(q));
        });
    }

    window.filterLearningMessages = function (query) {
        learningSearchQuery = query.trim().toLowerCase();
        applyLearningSearchFilter();
    };

    function renderAgents() {
        const list = document.getElementById('agentsList');
        if (!list) return;
        list.innerHTML = AGENT_ORDER.map((id) => {
            const a = agents[id];
            if (!a) return '';
            return `
                <div class="agent-card agent-card-compact ${selectedAgent === id ? 'selected' : ''}" onclick="selectAgent('${id}')">
                    <div class="agent-top">
                        <div class="agent-emoji">${a.emoji}</div>
                        <div class="agent-info">
                            <div class="agent-name">${a.name}</div>
                        </div>
                        <div class="status-dot status-${a.status}"></div>
                    </div>
                    <button type="button" class="agent-dm" onclick="event.stopPropagation();openPrivateChat('${id}')">Личный чат</button>
                    ${id === 'frontend' ? `<button type="button" class="agent-preview-btn" onclick="event.stopPropagation();openSonyaPreview()">⚛️ React Preview</button>` : ''}
                </div>`;
        }).join('');

        const learnList = document.getElementById('learningAgentsList');
        if (learnList) {
            learnList.innerHTML = LEARNING_AGENT_ORDER.map((id) => {
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

        const caps = a.capabilities || {};
        const skills = (caps.skills || []).map((s) => `<span class="topic-tag">${escapeHtml(s)}</span>`).join('') || '—';

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
                <div class="detail-section-title">Возможности</div>
                <p>${escapeHtml(caps.label || '')}</p>
                <div>${skills}</div>
            </div>
            <div class="detail-section">
                <div class="detail-section-title">Статистика</div>
                <p>Изучено: <strong>${a.learned_count || 0}</strong></p>
                <p>Проектов: <strong>${a.artifact_count || 0}</strong></p>
                <p>Задач: <strong>${a.memory_count || 0}</strong></p>
                ${a.agent_id === 'frontend' ? `<p>Figma макетов: <strong>${a.figma_studied_count || 0}</strong></p><p>Своих проектов: <strong>${a.figma_portfolio_count || 0}</strong></p>` : ''}
                <p>Личных сообщений: <strong>${a.direct_chat_count || 0}</strong></p>
                <p>Источники: <strong>${escapeHtml(sources)}</strong></p>
            </div>
            <div class="detail-section">
                <div class="detail-section-title">Темы</div>
                <div>${topics}</div>
            </div>
            <button class="action-btn" onclick="AgentActivity.open('${a.agent_id}')">📊 Деятельность</button>
            <button class="action-btn" onclick="openPrivateChat('${a.agent_id}')">💬 Обсудить / доработать</button>
            ${a.agent_id === 'frontend' ? `<button class="action-btn secondary" onclick="openSonyaPreview()">⚛️ React Preview</button>` : ''}
            ${a.agent_id === 'cursor' ? `<button class="action-btn secondary" onclick="Integrations.toggleCursorPanel()">⚡ Cursor Panel</button>` : ''}
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
        if (window.ChatCommands) ChatCommands.hide();
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
        triaging: 'проверка ролей',
        in_progress: 'выполняется',
        awaiting_approval: '⏳ на проверке',
        revision_requested: '✎ правки',
        cancelled: 'отменено',
        completed: '✓ готово',
        failed: 'ошибка',
    };
    const PRIO_LABELS = { urgent: '🔴', high: '🟠', medium: '🟡', low: '⚪' };

    function updateTaskBadges() {
        const awaiting = taskStats.awaiting_approval
            || taskHistory.filter((t) => t.status === 'awaiting_approval' && !t.parent_id).length;
        if (window.SidebarNav) SidebarNav.updateBadges({ awaiting });
        document.title = awaiting > 0
            ? `(${awaiting}) AI Team Room`
            : 'AI Team Room — Inbox';
        const chip = document.getElementById('awaitingChip');
        if (chip) {
            chip.classList.toggle('hidden', awaiting <= 0);
            chip.textContent = awaiting > 0 ? `⏳ ${awaiting} на проверке` : '';
        }
        if (window.UICore) UICore.updateHeaderContext({ taskStats: { ...taskStats, awaiting_approval: awaiting } });
        if (window.UICore && awaiting > 0) UICore.checkAwaitingCoachmark(awaiting);
    }

    function updateTaskHistory(data) {
        if (data.stats) taskStats = data.stats;
        if (data.tasks) taskHistory = data.tasks;
        if (window.FeaturePack && data.stats) FeaturePack.onTaskStats(data.stats);
        updateTaskBadges();
        renderTasks();
        if (window.PipelineUI?.onTaskHistory) {
            PipelineUI.onTaskHistory(taskHistory, taskStats);
        }
        if (window.KanbanUI && document.getElementById('kanbanView') && !document.getElementById('kanbanView').classList.contains('hidden')) {
            KanbanUI.refresh();
        }
        if (window.Dashboard && document.getElementById('dashboardView') && !document.getElementById('dashboardView').classList.contains('hidden')) {
            Dashboard.load();
        }
    }

    async function loadTasks() {
        const user = window.Auth?.getUser?.();
        if (!user) {
            if (!taskHistory.length) {
                taskStats = { total: 0, completed: 0, active: 0, awaiting_approval: 0 };
            }
            updateTaskBadges();
            renderTasks();
            return;
        }
        try {
            const resp = await fetch('/api/tasks', { credentials: 'same-origin' });
            if (resp.ok) {
                const data = await resp.json();
                taskStats = data.stats || taskStats;
                taskHistory = data.tasks || [];
                updateTaskBadges();
                renderTasks();
                if (window.PipelineUI?.onTaskHistory) {
                    PipelineUI.onTaskHistory(taskHistory, taskStats);
                }
            }
        } catch (_) {}
    }

    window.filterTasks = function (filter) {
        taskFilter = filter;
        document.querySelectorAll('.tasks-filters .filter-btn[data-filter]').forEach((b) => {
            b.classList.toggle('active', b.dataset.filter === filter);
        });
        renderTasks();
    };

    window.filterTasksSearch = function (query) {
        taskSearchQuery = query.trim().toLowerCase();
        renderTasks();
    };

    window.exportTasks = function () {
        const payload = { exported_at: new Date().toISOString(), stats: taskStats, tasks: taskHistory };
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `ai-team-tasks-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(a.href);
        if (window.UIEnhancements) UIEnhancements.toast('📥 Задачи экспортированы', 'success');
    };

    window.copyTaskById = function (taskId) {
        const t = taskHistory.find((x) => x.id === taskId);
        const text = t?.task || '';
        if (!text) return;
        navigator.clipboard?.writeText(text).then(() => {
            if (window.UIEnhancements) UIEnhancements.toast('📋 Скопировано', 'success');
        }).catch(() => {});
    };

    window.rerunTaskById = function (taskId) {
        const t = taskHistory.find((x) => x.id === taskId);
        const text = t?.task || '';
        if (!text) return;
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = text;
            input.focus();
            setMsgType('task');
        }
        switchView('chat');
        if (window.UIEnhancements) UIEnhancements.toast('↻ Задача готова к отправке', 'info');
    };

    window.copyTaskByIndex = function (idx) {
        copyTaskById(taskHistory[idx]?.id);
    };

    window.rerunTaskByIndex = function (idx) {
        rerunTaskById(taskHistory[idx]?.id);
    };

    function refreshKanbanIfVisible() {
        if (window.KanbanUI && document.getElementById('kanbanView') && !document.getElementById('kanbanView').classList.contains('hidden')) {
            KanbanUI.refresh();
        }
    }

    function patchTaskOptimistic(taskId, patch) {
        const t = taskHistory.find((x) => x.id === taskId);
        if (!t) return () => {};
        const prev = { ...t };
        Object.assign(t, patch);
        updateTaskBadges();
        renderTasks();
        refreshKanbanIfVisible();
        return () => {
            Object.assign(t, prev);
            updateTaskBadges();
            renderTasks();
            refreshKanbanIfVisible();
        };
    }

    function patchTasksOptimistic(updater) {
        const snapshots = new Map();
        taskHistory.forEach((t) => {
            const patch = updater(t);
            if (patch) {
                snapshots.set(t.id, { ...t });
                Object.assign(t, patch);
            }
        });
        const apply = () => {
            updateTaskBadges();
            renderTasks();
            refreshKanbanIfVisible();
        };
        apply();
        return () => {
            snapshots.forEach((prev, id) => {
                const t = taskHistory.find((x) => x.id === id);
                if (t) Object.assign(t, prev);
            });
            apply();
        };
    }

    window.approveTask = async function (taskId) {
        const now = new Date().toISOString();
        const revert = patchTaskOptimistic(taskId, { status: 'completed', completed_at: now });
        if (window.UICore) UICore.announceLive('Задача принята');
        const user = window.Auth?.getUser?.();
        if (!user && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'task_approve', task_id: taskId, note: '' }));
            if (window.UIEnhancements) UIEnhancements.toast('✅ Задача принята', 'success');
            return;
        }
        try {
            const r = await fetch(`/api/tasks/${taskId}/approve`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ note: '' }),
            });
            if (r.ok) {
                if (window.UIEnhancements) UIEnhancements.toast('✅ Задача принята', 'success');
            } else {
                revert();
                const d = await r.json().catch(() => ({}));
                if (window.UIEnhancements) UIEnhancements.toast(d.detail || 'Нет доступа', 'warn');
            }
        } catch (_) {
            revert();
        }
    };

    window.requestTaskRevision = async function (taskId) {
        const feedback = prompt('Что исправить?');
        if (!feedback?.trim()) return;
        const revert = patchTaskOptimistic(taskId, { status: 'revision_requested' });
        if (window.UICore) UICore.announceLive('Задача отправлена на доработку');
        const user = window.Auth?.getUser?.();
        if (!user && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'task_revision', task_id: taskId, feedback: feedback.trim() }));
            if (window.UIEnhancements) UIEnhancements.toast('✎ Отправлено на доработку', 'info');
            return;
        }
        try {
            const r = await fetch(`/api/tasks/${taskId}/revision`, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ feedback: feedback.trim() }),
            });
            if (r.ok) {
                if (window.UIEnhancements) UIEnhancements.toast('✎ Отправлено на доработку', 'info');
            } else {
                revert();
                const d = await r.json().catch(() => ({}));
                if (window.UIEnhancements) UIEnhancements.toast(d.detail || 'Нет доступа', 'warn');
            }
        } catch (_) {
            revert();
        }
    };

    window.addTaskComment = async function (taskId) {
        const input = document.getElementById('task-comment-input-' + taskId);
        const text = input?.value?.trim();
        if (!text) return;
        try {
            const r = await fetch('/api/tasks/' + taskId + '/comments', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            if (r.ok) {
                if (input) input.value = '';
                loadTasks();
            } else {
                const d = await r.json().catch(() => ({}));
                if (window.UIEnhancements) UIEnhancements.toast(d.detail || 'Нужен вход', 'warn');
            }
        } catch (_) {}
    };

    window.cancelAllTasks = async function () {
        if (!confirm('Отменить все активные задачи и очистить очереди агентов?')) return;
        const activeStatuses = new Set([
            'submitted', 'queued', 'in_progress', 'triaging', 'awaiting_approval', 'revision_requested',
        ]);
        const revert = patchTasksOptimistic((t) => (
            activeStatuses.has(t.status) ? { status: 'cancelled' } : null
        ));
        if (window.UICore) UICore.announceLive('Активные задачи отменены');
        const user = window.Auth?.getUser?.();
        if (!user && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'task_cancel_all' }));
            if (window.UIEnhancements) UIEnhancements.toast('🛑 Задачи отменены', 'success');
            return;
        }
        try {
            const r = await fetch('/api/tasks/cancel-all', { method: 'POST', credentials: 'same-origin' });
            if (r.ok) {
                const data = await r.json();
                if (window.UIEnhancements) {
                    UIEnhancements.toast(`🛑 Отменено: ${data.cancelled || 0}`, 'success');
                }
            } else {
                revert();
                const d = await r.json().catch(() => ({}));
                if (window.UIEnhancements) UIEnhancements.toast(d.detail || 'Нет доступа', 'warn');
            }
        } catch (_) {
            revert();
        }
    };

    window.clearTasksHistory = async function () {
        if (!confirm('Полностью удалить всю историю задач? Это нельзя отменить.')) return;
        try {
            const r = await fetch('/api/tasks/clear', { method: 'POST', credentials: 'same-origin' });
            if (r.ok) {
                const data = await r.json();
                if (window.UIEnhancements) {
                    UIEnhancements.toast(`🗑 Удалено записей: ${data.cleared || 0}`, 'success');
                }
                loadTasks();
            } else {
                const d = await r.json().catch(() => ({}));
                if (window.UIEnhancements) UIEnhancements.toast(d.detail || 'Только для администраторов', 'warn');
            }
        } catch (_) {}
    };

    function renderTasks() {
        const list = document.getElementById('tasksList');
        if (!list) return;

        const user = window.Auth?.getUser?.();
        if (!user && !taskHistory.length) {
            document.getElementById('statCompleted').textContent = '0';
            document.getElementById('statActive').textContent = '0';
            document.getElementById('statTotal').textContent = '0';
            const awEl = document.getElementById('statAwaiting');
            if (awEl) awEl.textContent = '0';
            list.innerHTML = window.UICore ? UICore.emptyState({
                icon: '💬',
                title: 'Гостевая сессия',
                text: 'Отправьте задачу в чат — она появится здесь. Войдите, чтобы сохранить историю между визитами.',
                primaryLabel: 'В чат',
                primaryOnclick: "switchView('chat')",
                secondaryLabel: 'Войти',
                secondaryHref: '/?auth=login',
            }) : '';
            return;
        }

        const awaiting = taskStats.awaiting_approval || taskHistory.filter((t) => t.status === 'awaiting_approval').length;
        document.getElementById('statCompleted').textContent = taskStats.completed || 0;
        document.getElementById('statActive').textContent = taskStats.active || 0;
        document.getElementById('statTotal').textContent = taskStats.total || 0;
        const awEl = document.getElementById('statAwaiting');
        if (awEl) awEl.textContent = awaiting;

        let items = taskHistory.filter((t) => !t.parent_id);
        if (taskFilter === 'completed') items = items.filter((t) => t.status === 'completed');
        if (taskFilter === 'awaiting') items = items.filter((t) => t.status === 'awaiting_approval');
        if (taskFilter === 'active') {
            items = items.filter((t) => [
                'submitted', 'queued', 'in_progress', 'triaging', 'revision_requested',
            ].includes(t.status));
        }
        if (taskSearchQuery) {
            items = items.filter((t) => {
                const hay = `${t.task || ''} ${t.response || ''} ${t.agent_name || ''} ${t.target || ''}`.toLowerCase();
                return hay.includes(taskSearchQuery);
            });
        }

        if (!items.length) {
            const msg = taskFilter === 'all' && !taskSearchQuery
                ? 'Задач пока нет — отправьте первую в чате'
                : 'Нет задач в этой категории';
            list.innerHTML = window.UICore ? UICore.emptyState({
                icon: '📋',
                title: msg,
                text: '',
                primaryLabel: '+ Новая задача',
                primaryOnclick: "switchView('chat')",
            }) : `<div class="tasks-empty"><p>${msg}</p></div>`;
            return;
        }

        const fmt = formatTime;
        list.innerHTML = items.map((t) =>
            (window.UICore ? UICore.renderTaskCard(t, { formatTimeFn: fmt }) : '')
        ).join('');
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
        const user = window.Auth?.getUser();
        const admin = window.UIAccess?.canAccessConsole?.(user);
        const learning = window.Auth?.canViewAgentLearning?.(user);
        if (window.UIAccess) UIAccess.applyMenuVisibility(user);
        document.getElementById('settingsUserHint')?.classList.toggle('hidden', admin || learning);
        document.getElementById('settingsGrid')?.classList.toggle('hidden', !admin && !learning);
        document.getElementById('settingsLearningSection')?.classList.toggle('hidden', !learning);
        if (!admin && !learning) return;
        try {
            const resp = await fetch('/api/config', { credentials: 'same-origin' });
            if (resp.ok) {
                const cfg = await resp.json();
                document.getElementById('learnMinInput').value = cfg.learning_interval_min || 15;
                document.getElementById('learnMaxInput').value = cfg.learning_interval_max || 45;
                document.getElementById('persistInput').checked = cfg.persist_knowledge !== false;
                document.getElementById('cursorRepoInput').value = cfg.cursor_repo_url || '';
                document.getElementById('cursorRefInput').value = cfg.cursor_repo_ref || 'main';
                document.getElementById('cursorEnabledInput').checked = cfg.cursor_enabled !== false;
                document.getElementById('cursorGithubSyncInput').checked = cfg.cursor_github_sync === true;
                document.getElementById('githubSyncOnTasksInput').checked = cfg.github_sync_on_tasks === true;
                document.getElementById('cursorAutoPrInput').checked = cfg.cursor_auto_create_pr !== false;
                document.getElementById('gitAutoSyncInput').checked = cfg.git_auto_sync !== false;
                document.getElementById('m365EnabledInput').checked = cfg.m365_enabled !== false;
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
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    learning_interval_min: parseInt(document.getElementById('learnMinInput').value, 10),
                    learning_interval_max: parseInt(document.getElementById('learnMaxInput').value, 10),
                    persist_knowledge: document.getElementById('persistInput').checked,
                    cursor_repo_url: document.getElementById('cursorRepoInput').value,
                    cursor_repo_ref: document.getElementById('cursorRefInput').value,
                    cursor_enabled: document.getElementById('cursorEnabledInput').checked,
                    cursor_github_sync: document.getElementById('cursorGithubSyncInput').checked,
                    github_sync_on_tasks: document.getElementById('githubSyncOnTasksInput').checked,
                    cursor_auto_create_pr: document.getElementById('cursorAutoPrInput').checked,
                    git_auto_sync: document.getElementById('gitAutoSyncInput').checked,
                    m365_enabled: document.getElementById('m365EnabledInput').checked,
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

    window.applyMention = function (text) {
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = (input.value ? `${input.value} ` : '') + text;
            input.focus();
            input.dispatchEvent(new Event('input'));
        }
        const alias = text.trim().replace(/^@/, '').toLowerCase();
        const map = {
            pm: 'pm', соня: 'frontend', sonia: 'frontend', frontend: 'frontend',
            макс: 'backend', backend: 'backend', все: 'all', all: 'all',
            маша: 'evaluator', evaluator: 'evaluator',
        };
        const sel = document.getElementById('targetSelect');
        if (sel && map[alias]) sel.value = map[alias];
    };

    window.applySlash = function (text) {
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = text;
            input.focus();
            input.dispatchEvent(new Event('input'));
        }
    };

    window.applyTemplate = function (text) {
        const input = document.getElementById('messageInput');
        if (input) {
            input.value = text;
            input.focus();
            input.dispatchEvent(new Event('input'));
        }
        setMsgType('task');
    };

    window.applyProjectTemplate = async function (templateId) {
        try {
            const r = await fetch('/api/templates/apply', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_id: templateId }),
            });
            const d = await r.json();
            if (d.ok) {
                switchView('chat');
                addSystemMessage(`📋 Шаблон «${templateId}» запущен командой`);
            }
        } catch (e) {
            addSystemMessage('Ошибка шаблона: ' + e);
        }
    };

    // ─── Init ────────────────────────────────────────────
    async function initApp() {
        applyTheme(getPreferredTheme());
        fetch('/api/config', { credentials: 'same-origin' }).then((r) => r.json()).then((cfg) => {
            if (cfg.auto_theme && window.AutoTheme) AutoTheme.start();
            else if (window.AutoTheme) AutoTheme.stop?.();
        }).catch(() => {});
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().catch(() => {});
        }

        const user = window.Auth ? await Auth.fetchMe() : null;
        const params = new URLSearchParams(location.search);
        const viewParam = params.get('view');
        const setupParam = params.get('setup');

        if (setupParam === '1' && !user) {
            location.href = '/?auth=register';
            return;
        }

        connect();

        let startView = viewParam || (user?.default_view) || 'tasks';
        const allowedViews = ['studio', 'chat', 'agent-learning', 'learning', 'design', 'masha', 'sonya-studio', 'tasks', 'projects', 'kanban', 'sprint', 'timeline', 'dashboard', 'profile', 'admin', 'investor'];
        if (!allowedViews.includes(startView)) {
            startView = 'tasks';
        }
        if (startView === 'admin' && !window.AdminPanel?.canAccess?.(user)) {
            startView = user ? 'tasks' : 'tasks';
        }
        if (AGENT_LEARNING_VIEWS.has(startView) && !canViewAgentLearning(user)) {
            startView = 'tasks';
        }
        if (user?.role === 'investor' && !viewParam) {
            startView = 'investor';
        }
        switchView(startView);

        if (window.UICore) {
            UICore.initMobileNav();
            UICore.initActivityPanel();
        }

        if (window.Auth) Auth.updateNavVisibility(user);
        if (window.AdminPanel && user) AdminPanel.updateNavVisibility(user);
        if (window.UIAccess) UIAccess.applyMenuVisibility(user);

        if (window.ReactPreview) ReactPreview.loadLatest({ autoOpen: false });
        if (window.Integrations) {
            Integrations.loadCursorStatus();
            Integrations.loadFigmaStatus();
        }
        if (window.UIEnhancements) UIEnhancements.init();
        if (window.FeaturePack) FeaturePack.init();
        if (window.SiteSearch) SiteSearch.init();
        if (window.PipelineUI) PipelineUI.load();
        if (window.StudioMinimap) StudioMinimap.init();
        if (window.SonyaStudio) SonyaStudio.init();

        updateChatWelcome();

        document.addEventListener('auth:updated', () => {
            loadTasks();
            updateChatWelcome();
        });

        const needsSetup = user && !user.setup_complete;
        if (needsSetup || setupParam === '1') {
            if (window.SetupWizard) await SetupWizard.maybeStart(user);
        } else if (window.CinematicOnboarding) {
            CinematicOnboarding.start();
        } else if (window.Onboarding) {
            Onboarding.start();
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        initApp();

        document.addEventListener('click', (e) => {
            document.querySelectorAll('.header-dropdown[open]').forEach((d) => {
                if (!d.contains(e.target)) d.removeAttribute('open');
            });
        });

        document.getElementById('messageInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.getElementById('messageInput')?.addEventListener('input', (e) => {
            e.target.style.height = 'auto';
            e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
            updateMentionDropdown(e.target);
        });

        initMentionAutocomplete();
    });

    // ─── @mention autocomplete ────────────────────────────
    let mentionAliases = {};

    async function initMentionAutocomplete() {
        try {
            const r = await fetch('/api/mentions/aliases', { credentials: 'same-origin' });
            const d = await r.json();
            mentionAliases = d.aliases || {};
        } catch (_) {}
    }

    function updateMentionDropdown(input) {
        const dd = document.getElementById('mentionDropdown');
        if (!dd || !input) return;
        const val = input.value;
        const at = val.lastIndexOf('@');
        if (at < 0) {
            dd.classList.add('hidden');
            return;
        }
        const query = val.slice(at + 1).toLowerCase();
        const matches = Object.keys(mentionAliases)
            .filter((k) => k.startsWith(query))
            .slice(0, 8);
        if (!matches.length) {
            dd.classList.add('hidden');
            return;
        }
        dd.innerHTML = matches.map((m) =>
            `<button type="button" class="mention-item" data-alias="${m}">@${m} → ${mentionAliases[m]}</button>`
        ).join('');
        dd.classList.remove('hidden');
        dd.querySelectorAll('.mention-item').forEach((btn) => {
            btn.onclick = () => {
                input.value = val.slice(0, at) + '@' + btn.dataset.alias + ' ';
                dd.classList.add('hidden');
                input.focus();
            };
        });
    }

    global.AITeamTasks = {
        getSnapshot: () => ({ stats: { ...taskStats }, tasks: taskHistory.slice() }),
        sendWs: (payload) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify(payload));
                return true;
            }
            return false;
        },
        isConnected: () => !!(ws && ws.readyState === WebSocket.OPEN),
        patchOptimistic: patchTaskOptimistic,
    };
})();
