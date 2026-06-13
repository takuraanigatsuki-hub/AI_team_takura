(function () {
    const splash = document.getElementById('dsSplash');
    const auth = document.getElementById('dsAuth');
    const progressBar = document.getElementById('dsProgressBar');
    const splashSub = document.getElementById('dsSplashSub');
    const bootSteps = document.querySelectorAll('#dsBootSteps li');
    const form = document.getElementById('dsAuthForm');
    const errorEl = document.getElementById('dsError');
    const submitBtn = document.getElementById('dsSubmit');
    const browserBtn = document.getElementById('dsBrowserLogin');
    const browserHint = document.getElementById('dsBrowserHint');
    const loginLabel = document.getElementById('dsLoginLabel');
    const loginInput = document.getElementById('dsLogin');
    const emailLabel = document.getElementById('dsEmailLabel');
    const emailInput = document.getElementById('dsEmail');
    const usernameLabel = document.getElementById('dsUsernameLabel');
    const usernameInput = document.getElementById('dsUsername');
    const usernameHint = document.getElementById('dsUsernameHint');
    const nameLabel = document.getElementById('dsNameLabel');
    const nameInput = document.getElementById('dsName');
    const nameHint = document.getElementById('dsNameHint');
    const tabs = document.querySelectorAll('.ds-tab');

    let mode = 'login';
    let devicePollTimer = null;
    const POLL_FAIL_MAX = 8;

    const steps = [
        { pct: 15, sub: 'Инициализация модулей…', step: 'init' },
        { pct: 45, sub: 'Подключение 13 агентов…', step: 'agents' },
        { pct: 75, sub: '3D-студия и Kanban…', step: 'studio' },
        { pct: 100, sub: 'Готово!', step: 'ready' },
    ];

    function parseApiError(d, fallback) {
        const detail = d?.detail;
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) return detail.map((x) => x.msg || String(x)).join(', ');
        return fallback || 'Ошибка';
    }

    function setBootStep(activeStep) {
        bootSteps.forEach((li) => {
            const s = li.dataset.step;
            li.classList.toggle('active', s === activeStep);
            li.classList.toggle('done', steps.findIndex((x) => x.step === s) < steps.findIndex((x) => x.step === activeStep));
        });
    }

    async function runSplash() {
        for (const s of steps) {
            progressBar.style.width = `${s.pct}%`;
            splashSub.textContent = s.sub;
            setBootStep(s.step);
            await new Promise((r) => setTimeout(r, s.pct === 100 ? 400 : 550));
        }
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                location.href = '/workspace';
                return;
            }
        } catch (_) { /* show auth */ }
        splash.classList.add('hide');
        setTimeout(() => {
            splash.classList.add('hidden');
            auth.classList.remove('hidden');
        }, 480);
    }

    function setMode(m) {
        mode = m;
        tabs.forEach((t) => {
            const on = t.dataset.mode === m;
            t.classList.toggle('active', on);
            t.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        const isReg = m === 'register';
        loginLabel.classList.toggle('hidden', isReg);
        loginInput.classList.toggle('hidden', isReg);
        loginInput.required = !isReg;
        emailLabel.classList.toggle('hidden', !isReg);
        emailInput.classList.toggle('hidden', !isReg);
        emailInput.required = isReg;
        usernameLabel.classList.toggle('hidden', !isReg);
        usernameInput.classList.toggle('hidden', !isReg);
        usernameInput.required = isReg;
        usernameHint.classList.toggle('hidden', !isReg);
        nameLabel.classList.toggle('hidden', !isReg);
        nameInput.classList.toggle('hidden', !isReg);
        nameInput.required = isReg;
        nameHint.classList.toggle('hidden', !isReg);
        submitBtn.textContent = isReg ? 'Создать аккаунт' : 'Войти';
    }

    tabs.forEach((t) => t.addEventListener('click', () => setMode(t.dataset.mode)));

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.classList.add('hidden');
        const password = document.getElementById('dsPassword').value;
        const url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        let body;
        if (mode === 'register') {
            const email = emailInput.value.trim();
            const username = usernameInput.value.trim();
            const name = nameInput.value.trim();
            if (!window.AuthFields?.fieldsAvailable(usernameInput, nameInput)) {
                errorEl.textContent = 'Исправьте логин или имя — они уже заняты';
                errorEl.classList.remove('hidden');
                return;
            }
            body = { email, password, name, username };
        } else {
            body = { login: loginInput.value.trim(), password };
        }
        submitBtn.disabled = true;
        try {
            const r = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(parseApiError(d, 'Ошибка входа'));
            location.href = mode === 'register' ? '/workspace?setup=1' : '/workspace';
        } catch (err) {
            errorEl.textContent = err.message || String(err);
            errorEl.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
        }
    });

    async function startBrowserLogin() {
        browserBtn.disabled = true;
        browserHint.classList.remove('hidden');
        browserHint.textContent = 'Открываем браузер…';
        try {
            const r = await fetch('/api/auth/device/start', { method: 'POST', credentials: 'same-origin' });
            const d = await r.json();
            if (!r.ok) throw new Error(parseApiError(d, 'Не удалось начать вход'));
            const url = d.verify_url;
            browserHint.innerHTML = `Код: <strong>${d.user_code}</strong> · откройте браузер и подтвердите вход`;
            if (window.pywebview && window.pywebview.api && window.pywebview.api.open_external) {
                window.pywebview.api.open_external(url);
            } else {
                window.open(url, '_blank', 'noopener');
            }
            pollDevice(d.device_id, d.poll_secret, d.poll_interval || 2);
        } catch (err) {
            browserHint.textContent = err.message || String(err);
            browserBtn.disabled = false;
        }
    }

    function pollDevice(deviceId, pollSecret, intervalSec) {
        if (devicePollTimer) clearInterval(devicePollTimer);
        let fails = 0;
        devicePollTimer = setInterval(async () => {
            try {
                const qs = new URLSearchParams({ secret: pollSecret || '' });
                const r = await fetch(`/api/auth/device/poll/${encodeURIComponent(deviceId)}?${qs}`, { credentials: 'same-origin' });
                if (!r.ok) throw new Error('poll HTTP ' + r.status);
                const d = await r.json();
                fails = 0;
                if (d.status === 'ok' && d.handoff_token) {
                    clearInterval(devicePollTimer);
                    browserHint.textContent = 'Вход подтверждён! Открываем приложение…';
                    location.href = `/desktop/handoff?t=${encodeURIComponent(d.handoff_token)}`;
                } else if (d.status === 'expired') {
                    clearInterval(devicePollTimer);
                    browserHint.textContent = 'Время истекло. Нажмите «Войти через браузер» снова.';
                    browserBtn.disabled = false;
                }
            } catch (_) {
                fails += 1;
                if (fails >= POLL_FAIL_MAX) {
                    clearInterval(devicePollTimer);
                    browserHint.textContent = 'Не удалось связаться с сервером. Проверьте сеть и попробуйте снова.';
                    browserBtn.disabled = false;
                }
            }
        }, intervalSec * 1000);
    }

    browserBtn?.addEventListener('click', startBrowserLogin);

    const params = new URLSearchParams(location.search);
    if (params.get('error') === 'handoff_expired') {
        splash.classList.add('hidden');
        auth.classList.remove('hidden');
        errorEl.textContent = 'Ссылка входа устарела. Войдите снова.';
        errorEl.classList.remove('hidden');
    } else {
        runSplash();
    }

    if (window.AuthFields) {
        AuthFields.bindUsernameCheck(usernameInput, usernameHint);
        AuthFields.bindNameCheck(nameInput, nameHint);
    }
})();
