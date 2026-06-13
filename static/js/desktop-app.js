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
    const nameLabel = document.getElementById('dsNameLabel');
    const nameInput = document.getElementById('dsName');
    const tabs = document.querySelectorAll('.ds-tab');

    let mode = 'login';
    let devicePollTimer = null;

    const steps = [
        { pct: 15, sub: 'Инициализация модулей…', step: 'init' },
        { pct: 45, sub: 'Подключение 13 агентов…', step: 'agents' },
        { pct: 75, sub: '3D-студия и Kanban…', step: 'studio' },
        { pct: 100, sub: 'Готово!', step: 'ready' },
    ];

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
                location.href = '/workspace?desktop=1';
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
        nameLabel.classList.toggle('hidden', !isReg);
        nameInput.classList.toggle('hidden', !isReg);
        nameInput.required = isReg;
        submitBtn.textContent = isReg ? 'Создать аккаунт' : 'Войти';
    }

    tabs.forEach((t) => t.addEventListener('click', () => setMode(t.dataset.mode)));

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.classList.add('hidden');
        const email = document.getElementById('dsEmail').value.trim();
        const password = document.getElementById('dsPassword').value;
        const name = nameInput.value.trim();
        const url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        const body = mode === 'register' ? { email, password, name } : { email, password };
        submitBtn.disabled = true;
        try {
            const r = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка входа');
            location.href = mode === 'register' ? '/workspace?setup=1&desktop=1' : '/workspace?desktop=1';
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
            if (!r.ok) throw new Error(d.detail || 'Не удалось начать вход');
            const url = d.verify_url;
            browserHint.innerHTML = `Код: <strong>${d.user_code}</strong> · откройте браузер и подтвердите вход`;
            if (window.pywebview?.api?.open_external) {
                window.pywebview.api.open_external(url);
            } else {
                window.open(url, '_blank', 'noopener');
            }
            pollDevice(d.device_id, d.poll_interval || 2);
        } catch (err) {
            browserHint.textContent = err.message || String(err);
            browserBtn.disabled = false;
        }
    }

    function pollDevice(deviceId, intervalSec) {
        if (devicePollTimer) clearInterval(devicePollTimer);
        devicePollTimer = setInterval(async () => {
            try {
                const r = await fetch(`/api/auth/device/poll/${encodeURIComponent(deviceId)}`, { credentials: 'same-origin' });
                const d = await r.json();
                if (d.status === 'ok' && d.handoff_token) {
                    clearInterval(devicePollTimer);
                    browserHint.textContent = 'Вход подтверждён! Открываем приложение…';
                    location.href = `/desktop/handoff?t=${encodeURIComponent(d.handoff_token)}`;
                } else if (d.status === 'expired') {
                    clearInterval(devicePollTimer);
                    browserHint.textContent = 'Время истекло. Нажмите «Войти через браузер» снова.';
                    browserBtn.disabled = false;
                }
            } catch (_) { /* retry */ }
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
})();
