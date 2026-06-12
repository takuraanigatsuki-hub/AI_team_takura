/**
 * Landing — 3D hero, guided demo, activity feed, mini-chat
 */
(function (global) {
    const AGENT_META = {
        pm: { name: 'Виктор', emoji: '🎯', role: 'PM' },
        frontend: { name: 'Соня', emoji: '🎨', role: 'Frontend' },
        cursor: { name: 'Лео', emoji: '⚡', role: 'Cursor SDK' },
        backend: { name: 'Макс', emoji: '⚙️', role: 'Backend' },
        qa: { name: 'Рита', emoji: '🧪', role: 'QA' },
    };

    const DEMO_AGENTS_BASE = [
        { agent_id: 'pm', status: 'working', location: 'studio', name: 'Виктор', emoji: '🎯' },
        { agent_id: 'frontend', status: 'working', location: 'studio', name: 'Соня', emoji: '🎨' },
        { agent_id: 'cursor', status: 'idle', location: 'studio', name: 'Лео', emoji: '⚡' },
        { agent_id: 'backend', status: 'idle', location: 'studio', name: 'Макс', emoji: '⚙️' },
        { agent_id: 'architect', status: 'idle', location: 'studio', name: 'Алекс', emoji: '🏛️' },
        { agent_id: 'qa', status: 'idle', location: 'studio', name: 'Рита', emoji: '🧪' },
        { agent_id: 'reviewer', status: 'idle', location: 'rest_room', name: 'Дэн', emoji: '🔍' },
        { agent_id: 'doc_writer', status: 'learning', location: 'library', name: 'Лена', emoji: '📝' },
        { agent_id: 'devops', status: 'idle', location: 'studio', name: 'Кирилл', emoji: '🔧' },
        { agent_id: 'presenter', status: 'idle', location: 'rest_room', name: 'Ника', emoji: '📽️' },
        { agent_id: 'modeler', status: 'idle', location: 'library', name: 'Зоя', emoji: '🧊' },
    ];

    const CHAT_REPLIES = {
        pm: ['Разобью на спринт и распределю по команде.', 'Landing — приоритет #1, стартую план.'],
        frontend: ['Уже верстаю hero и CTA. React Preview через минуту.', 'Подтянула цвета из Figma — 94% match.'],
        cursor: ['Открою PR с компонентами landing.', 'GitHub sync — ветка main, CI зелёный.'],
        backend: ['REST API для формы регистрации — в работе.', 'Эндпоинты /api/auth готовы.'],
        qa: ['Пишу e2e на landing и форму.', 'Тест-план в Kanban — колонка Review.'],
    };

    const ACTIVITY_POOL = [
        { team: 'NovaTech', action: 'deploy landing', ago: '2 мин' },
        { team: 'PixelFlow', action: 'Figma → React 96%', ago: '4 мин' },
        { team: 'StartHub', action: 'PR merged · Cursor', ago: '6 мин' },
        { team: 'DataLift', action: 'Sprint закрыт · 12 задач', ago: '8 мин' },
        { team: 'CloudKit', action: '3D studio · 11 агентов', ago: '11 мин' },
        { team: 'Finora', action: 'pitch deck · Ника', ago: '14 мин' },
        { team: 'BuildAI', action: 'Kanban → Done: API', ago: '17 мин' },
    ];

    let demoTimer = null;
    let activityTimer = null;
    let studioReady = false;

    function initStudioHero() {
        const canvas = document.getElementById('landingCanvas');
        if (!canvas || !global.StudioApp) return;

        const started = StudioApp.init(canvas, onAgentClick, {
            uiIds: { loading: 'landingStudioLoading', error: 'landingStudioError' },
            autoOrbit: true,
        });

        if (!started) return;

        const tryAgents = () => {
            if (StudioApp.isReady()) {
                studioReady = true;
                StudioApp.updateAgents(DEMO_AGENTS_BASE);
                StudioApp.showSpeechBubble('pm', 'Команда на связи — кликни на агента');
                startAmbientDemo();
            } else {
                setTimeout(tryAgents, 200);
            }
        };
        tryAgents();
    }

    function onAgentClick(agentId) {
        const meta = AGENT_META[agentId] || { name: agentId, emoji: '👤', role: 'Агент' };
        openMiniChat(agentId, meta);
        if (studioReady) {
            StudioApp.setAutoOrbit(false);
            StudioApp.flyToAgent(agentId);
        }
    }

    function openMiniChat(agentId, meta) {
        const panel = document.getElementById('lpMiniChat');
        const title = document.getElementById('lpMiniChatTitle');
        const msgs = document.getElementById('lpMiniChatMsgs');
        const input = document.getElementById('lpMiniChatInput');
        if (!panel || !msgs) return;

        panel.classList.remove('hidden');
        panel.dataset.agent = agentId;
        if (title) title.textContent = `${meta.emoji} ${meta.name} · ${meta.role}`;
        msgs.innerHTML = `<div class="lp-mini-msg bot">${meta.emoji} Привет! Это demo — напиши «landing» или «figma».</div>`;
        input?.focus();
    }

    function handleMiniChatSend() {
        const panel = document.getElementById('lpMiniChat');
        const input = document.getElementById('lpMiniChatInput');
        const msgs = document.getElementById('lpMiniChatMsgs');
        if (!panel || !input || !msgs) return;

        const text = input.value.trim();
        if (!text) return;
        const agentId = panel.dataset.agent || 'frontend';

        msgs.insertAdjacentHTML('beforeend', `<div class="lp-mini-msg user">${escape(text)}</div>`);
        input.value = '';

        const lower = text.toLowerCase();
        let reply = (CHAT_REPLIES[agentId] || CHAT_REPLIES.frontend)[0];
        if (lower.includes('landing')) reply = 'Сделаю hero + CTA + pricing. React Preview уже собирается…';
        if (lower.includes('figma')) reply = 'Compare 94% — могу подтянуть отступы из макета.';
        if (lower.includes('api') || lower.includes('backend')) reply = 'Макс подключит REST — задача в Kanban.';

        setTimeout(() => {
            const meta = AGENT_META[agentId] || AGENT_META.frontend;
            msgs.insertAdjacentHTML('beforeend', `<div class="lp-mini-msg bot">${meta.emoji} ${reply}</div>`);
            msgs.scrollTop = msgs.scrollHeight;
            if (studioReady) StudioApp.showSpeechBubble(agentId, reply.slice(0, 40));
        }, 600);
    }

    function startAmbientDemo() {
        if (demoTimer) clearInterval(demoTimer);
        let tick = 0;
        demoTimer = setInterval(() => {
            if (!StudioApp.isReady()) return;
            tick++;
            const agents = DEMO_AGENTS_BASE.map((a) => ({ ...a }));
            if (tick % 4 === 0) {
                agents.find((a) => a.agent_id === 'frontend').status = 'working';
                agents.find((a) => a.agent_id === 'cursor').status = tick % 8 === 0 ? 'working' : 'idle';
                StudioApp.showSpeechBubble('frontend', 'Верстаю секцию features…');
            }
            if (tick % 7 === 0) {
                StudioApp.pulseScreen('frontend');
            }
            StudioApp.updateAgents(agents);
        }, 4500);
    }

    /* ─── Guided demo (2 min compressed ~40s) ─── */
    const DEMO_STEPS = [
        { t: 0, step: 0, label: 'Задача', action: demoStepTask },
        { t: 4, step: 1, label: 'PM план', action: demoStepPm },
        { t: 9, step: 2, label: 'Figma → UI', action: demoStepFigma },
        { t: 16, step: 3, label: 'Код + PR', action: demoStepCode },
        { t: 24, step: 4, label: 'Deploy', action: demoStepDeploy },
        { t: 32, step: 5, label: 'Готово', action: demoStepDone },
    ];

    let demoPlaying = false;
    let demoTimeouts = [];

    function demoStepTask() {
        setDemoPanel('task', '📋 «Сделай landing для SaaS» → команда');
        typeInDemoInput('Сделай landing page для SaaS-стартапа');
    }

    function demoStepPm() {
        setDemoPanel('kanban', '📌 Kanban: 4 задачи · Sprint W24');
        if (studioReady) {
            StudioApp.showSpeechBubble('pm', 'План готов — Соня UI, Лео код');
            StudioApp.setPipelineHighlight('pm');
        }
        bumpStat('lpStatTasks', 4);
    }

    function demoStepFigma() {
        setDemoPanel('figma', '🎨 Figma Compare · match растёт…');
        animateFigmaMatch(72, 94);
        if (studioReady) {
            StudioApp.setPipelineHighlight('frontend');
            StudioApp.showSpeechBubble('frontend', 'React Preview из Figma');
            StudioApp.pulseScreen('frontend');
        }
    }

    function demoStepCode() {
        setDemoPanel('code', '⚡ PR #42 · Cursor SDK · +847 −12');
        if (studioReady) {
            StudioApp.setPipelineHighlight('cursor');
            StudioApp.showSpeechBubble('cursor', 'PR готов к review');
        }
        bumpStat('lpStatPr', 1);
    }

    function demoStepDeploy() {
        setDemoPanel('deploy', '🚀 Deploy bundle · preview live');
        if (studioReady) {
            StudioApp.burstConfetti('frontend');
            StudioApp.showSpeechBubble('frontend', 'Landing live!');
        }
        bumpStat('lpStatDeploy', 1);
    }

    function demoStepDone() {
        setDemoPanel('done', '✅ Landing за ~2 мин · без регистрации в demo');
        highlightDemoStep(5);
    }

    function setDemoPanel(mode, caption) {
        const cap = document.getElementById('lpDemoCaption');
        if (cap) cap.textContent = caption;
        document.querySelectorAll('.lp-demo-panel').forEach((p) => {
            p.classList.toggle('active', p.dataset.mode === mode);
        });
    }

    function typeInDemoInput(text) {
        const el = document.getElementById('lpDemoInput');
        if (!el) return;
        el.textContent = '';
        let i = 0;
        const iv = setInterval(() => {
            el.textContent = text.slice(0, ++i);
            if (i >= text.length) clearInterval(iv);
        }, 35);
    }

    function highlightDemoStep(idx) {
        document.querySelectorAll('.lp-demo-step').forEach((s, i) => {
            s.classList.toggle('active', i === idx);
            s.classList.toggle('done', i < idx);
        });
    }

    function animateFigmaMatch(from, to) {
        const el = document.getElementById('lpFigmaMatch');
        if (!el) return;
        let v = from;
        const iv = setInterval(() => {
            v = Math.min(to, v + 2);
            el.textContent = `${v}%`;
            if (v >= to) clearInterval(iv);
        }, 60);
    }

    function bumpStat(id, add) {
        const el = document.getElementById(id);
        if (!el) return;
        const n = parseInt(el.textContent.replace(/\D/g, ''), 10) || 0;
        el.textContent = String(n + add);
    }

    function playGuidedDemo() {
        if (demoPlaying) return;
        demoPlaying = true;
        demoTimeouts.forEach(clearTimeout);
        demoTimeouts = [];

        const btn = document.getElementById('lpDemoPlay');
        if (btn) { btn.disabled = true; btn.textContent = '▶ Demo идёт…'; }

        highlightDemoStep(0);
        DEMO_STEPS.forEach(({ t, step, action }) => {
            demoTimeouts.push(setTimeout(() => {
                highlightDemoStep(step);
                action();
            }, t * 1000));
        });

        demoTimeouts.push(setTimeout(() => {
            demoPlaying = false;
            if (btn) { btn.disabled = false; btn.textContent = '▶ Смотреть demo ещё раз'; }
        }, 38000));
    }

    /* ─── Live activity feed ─── */
    function initActivityFeed() {
        const list = document.getElementById('lpActivityList');
        if (!list) return;

        let idx = 0;
        const render = () => {
            const items = [];
            for (let i = 0; i < 5; i++) {
                const a = ACTIVITY_POOL[(idx + i) % ACTIVITY_POOL.length];
                items.push(`<li class="lp-activity-item"><span class="lp-act-team">${a.team}</span> ${a.action} <time>${a.ago}</time></li>`);
            }
            list.innerHTML = items.join('');
            idx = (idx + 1) % ACTIVITY_POOL.length;
        };
        render();
        activityTimer = setInterval(render, 4000);

        animateCounter('lpLiveTasks', 847, 920);
        animateCounter('lpLiveRooms', 124, 131);
        animateCounter('lpLivePr', 23, 28);
    }

    function animateCounter(id, from, to) {
        const el = document.getElementById(id);
        if (!el) return;
        const start = Date.now();
        const dur = 2500;
        const tick = () => {
            const p = Math.min(1, (Date.now() - start) / dur);
            const v = Math.round(from + (to - from) * p);
            el.textContent = v.toLocaleString('ru');
            if (p < 1) requestAnimationFrame(tick);
        };
        tick();
    }

    function escape(s) {
        return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    function bindUI() {
        document.getElementById('lpMiniChatSend')?.addEventListener('click', handleMiniChatSend);
        document.getElementById('lpMiniChatInput')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); handleMiniChatSend(); }
        });
        document.getElementById('lpMiniChatClose')?.addEventListener('click', () => {
            document.getElementById('lpMiniChat')?.classList.add('hidden');
            StudioApp?.setAutoOrbit(true);
        });
        document.getElementById('lpDemoPlay')?.addEventListener('click', playGuidedDemo);

        const hero = document.querySelector('.lp-hero-visual');
        if (hero && 'IntersectionObserver' in window) {
            const io = new IntersectionObserver((entries) => {
                entries.forEach((e) => {
                    if (e.isIntersecting && !studioReady) initStudioHero();
                });
            }, { threshold: 0.15 });
            io.observe(hero);
        } else {
            initStudioHero();
        }
    }

    function init() {
        bindUI();
        initActivityFeed();
    }

    global.LandingDemo = { init, playGuidedDemo };
})(window);
