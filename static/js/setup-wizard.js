/** Мастер первой настройки — для новых пользователей после регистрации */
(function (global) {
    const STEPS = [
        {
            id: 'welcome',
            title: 'Добро пожаловать!',
            html: (u) => `
                <p>Расскажите, как к вам обращаться — команда будет видеть ваше имя в чате.</p>
                <label class="sw-label">Ваше имя</label>
                <input id="swName" class="design-input" value="${escape(u?.name || '')}" placeholder="Алексей">`,
        },
        {
            id: 'goal',
            title: 'Цель проекта',
            html: () => `
                <p>Кратко опишите задачу — все агенты получат этот контекст.</p>
                <label class="sw-label">Brief проекта</label>
                <textarea id="swGoal" class="design-input sw-textarea" rows="4" placeholder="SaaS для управления задачами команды…"></textarea>`,
        },
        {
            id: 'prefs',
            title: 'Интерфейс',
            html: () => `
                <p>Выберите стартовый экран и тему.</p>
                <label class="sw-label">Стартовая вкладка</label>
                <select id="swView" class="design-input">
                    <option value="dashboard" selected>📊 Dashboard</option>
                    <option value="studio">🎮 3D Студия</option>
                    <option value="chat">💬 Рабочий чат</option>
                    <option value="kanban">📌 Kanban</option>
                </select>
                <label class="sw-label">Тема</label>
                <select id="swTheme" class="design-input">
                    <option value="auto">Системная</option>
                    <option value="dark" selected>Тёмная</option>
                    <option value="light">Светлая</option>
                </select>`,
        },
        {
            id: 'done',
            title: 'Готово!',
            html: () => `
                <p>Команда из 11 агентов готова к работе. Отправьте первую задачу в чате или выберите шаблон.</p>
                <ul class="sw-checklist">
                    <li>✅ PM Виктор координирует задачи</li>
                    <li>✅ Соня делает UI и React Preview</li>
                    <li>✅ Лео подключает Cursor SDK</li>
                </ul>`,
        },
    ];

    let step = 0;
    let overlay = null;

    async function maybeStart(user) {
        if (!user || user.setup_complete) return false;
        start(user);
        return true;
    }

    function start(user) {
        step = 0;
        overlay = document.createElement('div');
        overlay.className = 'setup-overlay';
        overlay.innerHTML = `
            <div class="setup-card">
                <div class="setup-progress"><div class="setup-bar" id="swBar"></div></div>
                <h2 id="swTitle"></h2>
                <div id="swBody" class="setup-body"></div>
                <div class="setup-footer">
                    <span id="swStepLabel" class="muted"></span>
                    <div class="setup-btns">
                        <button type="button" class="btn-secondary" id="swBack">Назад</button>
                        <button type="button" class="btn-primary" id="swNext">Далее</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        document.getElementById('swBack').onclick = prev;
        document.getElementById('swNext').onclick = next;
        render(user);
    }

    function render(user) {
        const s = STEPS[step];
        document.getElementById('swTitle').textContent = s.title;
        document.getElementById('swBody').innerHTML = s.html(user);
        document.getElementById('swStepLabel').textContent = `Шаг ${step + 1} из ${STEPS.length}`;
        document.getElementById('swBar').style.width = `${((step + 1) / STEPS.length) * 100}%`;
        document.getElementById('swBack').style.visibility = step === 0 ? 'hidden' : 'visible';
        document.getElementById('swNext').textContent = step === STEPS.length - 1 ? 'Начать работу' : 'Далее';
    }

    function prev() {
        if (step > 0) {
            step--;
            render(global.Auth?.getUser());
        }
    }

    async function next() {
        if (step < STEPS.length - 1) {
            step++;
            render(global.Auth?.getUser());
            return;
        }
        await finish();
    }

    async function finish() {
        const name = document.getElementById('swName')?.value || global.Auth?.getUser()?.name || '';
        const goal = document.getElementById('swGoal')?.value || '';
        const defaultView = document.getElementById('swView')?.value || 'dashboard';
        const theme = document.getElementById('swTheme')?.value || 'dark';

        try {
            await fetch('/api/auth/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ name, goal, default_view: defaultView, theme }),
            });
            if (goal) {
                await fetch('/api/project-memory', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brief: goal, goals: [], constraints: [] }),
                });
            }
            if (theme === 'light' || theme === 'dark') {
                localStorage.setItem('ai-team-room-theme', theme);
                if (window.applyTheme) applyTheme(theme);
            }
            await global.Auth?.fetchMe();
            overlay?.remove();
            if (window.switchView) switchView(defaultView);
            if (window.Onboarding) Onboarding.start();
            if (window.UIEnhancements) UIEnhancements.toast('🎉 Настройка завершена', 'success');
        } catch (e) {
            alert(e.message || 'Ошибка сохранения');
        }
    }

    function escape(s) {
        return String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    }

    global.SetupWizard = { maybeStart, start };
})(window);
