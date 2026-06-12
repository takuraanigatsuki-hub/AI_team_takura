/** Мастер первой настройки — для новых пользователей после регистрации */
(function (global) {
    const STEPS = ['welcome', 'goal', 'prefs', 'done'];
    let step = 0;
    let overlay = null;
    let formData = { name: '', goal: '', default_view: 'dashboard', theme: 'dark' };

    async function maybeStart(user) {
        if (!user || user.setup_complete) return false;
        formData.name = user.name || '';
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

    function saveCurrentStep() {
        if (step === 0) formData.name = document.getElementById('swName')?.value || formData.name;
        if (step === 1) formData.goal = document.getElementById('swGoal')?.value || '';
        if (step === 2) {
            formData.default_view = document.getElementById('swView')?.value || 'dashboard';
            formData.theme = document.getElementById('swTheme')?.value || 'dark';
        }
    }

    function render(user) {
        const bodies = {
            welcome: `
                <p>Расскажите, как к вам обращаться — команда будет видеть ваше имя в чате.</p>
                <label class="sw-label">Ваше имя</label>
                <input id="swName" class="design-input" value="${escape(formData.name || user?.name || '')}" placeholder="Алексей">`,
            goal: `
                <p>Кратко опишите задачу — все агенты получат этот контекст.</p>
                <label class="sw-label">Brief проекта</label>
                <textarea id="swGoal" class="design-input sw-textarea" rows="4" placeholder="SaaS для управления задачами команды…">${escape(formData.goal)}</textarea>`,
            prefs: `
                <p>Выберите стартовый экран и тему.</p>
                <label class="sw-label">Стартовая вкладка</label>
                <select id="swView" class="design-input">
                    <option value="dashboard" ${formData.default_view === 'dashboard' ? 'selected' : ''}>📊 Dashboard</option>
                    <option value="studio" ${formData.default_view === 'studio' ? 'selected' : ''}>🎮 3D Студия</option>
                    <option value="chat" ${formData.default_view === 'chat' ? 'selected' : ''}>💬 Рабочий чат</option>
                    <option value="kanban" ${formData.default_view === 'kanban' ? 'selected' : ''}>📌 Kanban</option>
                </select>
                <label class="sw-label">Тема</label>
                <select id="swTheme" class="design-input">
                    <option value="auto" ${formData.theme === 'auto' ? 'selected' : ''}>Системная</option>
                    <option value="dark" ${formData.theme === 'dark' ? 'selected' : ''}>Тёмная</option>
                    <option value="light" ${formData.theme === 'light' ? 'selected' : ''}>Светлая</option>
                </select>`,
            done: `
                <p>Команда из 11 агентов готова к работе. Отправьте первую задачу в чате или выберите шаблон.</p>
                <ul class="sw-checklist">
                    <li>✅ PM Виктор координирует задачи</li>
                    <li>✅ Соня делает UI и React Preview</li>
                    <li>✅ Лео подключает Cursor SDK</li>
                </ul>`,
        };
        const titles = { welcome: 'Добро пожаловать!', goal: 'Цель проекта', prefs: 'Интерфейс', done: 'Готово!' };
        const id = STEPS[step];
        document.getElementById('swTitle').textContent = titles[id];
        document.getElementById('swBody').innerHTML = bodies[id];
        document.getElementById('swStepLabel').textContent = `Шаг ${step + 1} из ${STEPS.length}`;
        document.getElementById('swBar').style.width = `${((step + 1) / STEPS.length) * 100}%`;
        document.getElementById('swBack').style.visibility = step === 0 ? 'hidden' : 'visible';
        document.getElementById('swNext').textContent = step === STEPS.length - 1 ? 'Начать работу' : 'Далее';
    }

    function prev() {
        saveCurrentStep();
        if (step > 0) {
            step--;
            render(global.Auth?.getUser());
        }
    }

    async function next() {
        saveCurrentStep();
        if (step < STEPS.length - 1) {
            step++;
            render(global.Auth?.getUser());
            return;
        }
        await finish();
    }

    async function finish() {
        try {
            await fetch('/api/auth/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(formData),
            });
            if (formData.goal) {
                await fetch('/api/project-memory', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ brief: formData.goal, goals: [], constraints: [] }),
                });
            }
            if (formData.theme === 'light' || formData.theme === 'dark') {
                localStorage.setItem('ai-team-room-theme', formData.theme);
                if (window.applyTheme) applyTheme(formData.theme);
            }
            await global.Auth?.fetchMe();
            overlay?.remove();
            if (window.switchView) switchView(formData.default_view);
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
