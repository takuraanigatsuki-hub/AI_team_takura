/** Onboarding tour — первый визит */
(function (global) {
    const KEY = 'ai_team_onboarding_v2';
    const STEPS = [
        { title: '3D Студия', text: 'Живая команда агентов. Кликните на аватар — личный чат.', view: 'studio' },
        { title: 'Рабочий чат', text: 'Режим «Задача» → Enter. «Вся команда» идёт через PM Виктора.', view: 'chat' },
        { title: 'Kanban & Timeline', text: 'Следите за задачами и replay активности команды.', view: 'kanban' },
        { title: 'Дизайн-лаб', text: 'Соня изучает Figma и запоминает паттерны. React Preview и Compare.', view: 'design' },
        { title: 'Готово!', text: 'Ctrl+K — палитра команд. Standup и Deploy в шапке.', view: 'studio' },
    ];

    function start() {
        if (localStorage.getItem(KEY)) return;
        let step = 0;
        const overlay = document.createElement('div');
        overlay.className = 'onboard-overlay';
        overlay.innerHTML = `<div class="onboard-card"><h3 id="obTitle"></h3><p id="obText"></p><div class="onboard-dots" id="obDots"></div><div class="onboard-btns"><button type="button" class="btn-secondary" id="obSkip">Пропустить</button><button type="button" class="btn-primary" id="obNext">Далее</button></div></div>`;
        document.body.appendChild(overlay);

        function show() {
            const s = STEPS[step];
            document.getElementById('obTitle').textContent = s.title;
            document.getElementById('obText').textContent = s.text;
            document.getElementById('obDots').textContent = `${step + 1} / ${STEPS.length}`;
            if (s.view && window.switchView) switchView(s.view);
        }

        document.getElementById('obSkip').onclick = finish;
        document.getElementById('obNext').onclick = () => {
            step++;
            if (step >= STEPS.length) finish();
            else show();
        };
        show();

        function finish() {
            localStorage.setItem(KEY, '1');
            overlay.remove();
        }
    }

    global.Onboarding = { start };
})(window);
