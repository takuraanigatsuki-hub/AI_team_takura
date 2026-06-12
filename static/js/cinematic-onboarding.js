/**
 * Cinematic onboarding — первый заход в /app
 */
(function (global) {
    const KEY = 'ai_team_cinematic_v1';

    function start(initialTask) {
        if (localStorage.getItem(KEY)) return;
        localStorage.setItem(KEY, '1');

        global.switchView?.('studio');

        const run = () => {
            if (!global.StudioApp?.isReady?.()) {
                setTimeout(run, 300);
                return;
            }
            StudioApp.flyCameraIntro();
            setTimeout(() => StudioApp.showSpeechBubble('pm', 'Добро пожаловать! Одна задача — и команда стартует.'), 800);
            setTimeout(() => showOverlay(initialTask), 1600);
        };

        setTimeout(run, 400);
    }

    function showOverlay(taskText) {
        const existing = document.getElementById('cinematicOverlay');
        if (existing) existing.remove();

        const task = taskText || 'Сделай landing page для моего продукта';
        const overlay = document.createElement('div');
        overlay.id = 'cinematicOverlay';
        overlay.className = 'cinematic-overlay';
        overlay.innerHTML = `
            <div class="cinematic-card">
                <div class="cinematic-badge">🎬 Первая сессия</div>
                <h2>Виктор · PM</h2>
                <p class="cinematic-lead">Камера пролетела над офисом — команда ждёт вашу задачу. Нажмите «Запустить» или измените текст.</p>
                <textarea id="cinematicTask" class="cinematic-input" rows="2">${escape(task)}</textarea>
                <div class="cinematic-actions">
                    <button type="button" class="btn-secondary" id="cinematicSkip">Позже</button>
                    <button type="button" class="btn-primary" id="cinematicGo">🚀 Запустить команду</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        document.getElementById('cinematicSkip').onclick = () => {
            overlay.remove();
            global.switchView?.('chat');
        };

        document.getElementById('cinematicGo').onclick = () => {
            const text = document.getElementById('cinematicTask')?.value?.trim() || task;
            overlay.remove();
            launchTask(text);
        };
    }

    function launchTask(text) {
        global.switchView?.('chat');
        const inp = document.getElementById('messageInput');
        const sel = document.getElementById('targetSelect');
        if (sel) sel.value = 'all';
        if (global.setMsgType) setMsgType('task');
        if (inp) {
            inp.value = text;
            inp.focus();
        }
        if (global.StudioApp) {
            StudioApp.showSpeechBubble('pm', 'Принял — распределяю задачи');
            StudioApp.setPipelineHighlight('pm');
            setTimeout(() => {
                StudioApp.showSpeechBubble('frontend', 'Беру UI на себя');
                StudioApp.setPipelineHighlight('frontend');
            }, 1200);
        }
        if (global.UIEnhancements) UIEnhancements.toast('Задача готова — Enter для отправки', 'info', 5000);
    }

    function escape(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.CinematicOnboarding = { start };
})(window);
