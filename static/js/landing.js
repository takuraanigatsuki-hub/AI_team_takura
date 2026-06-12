/** Landing page — вход, регистрация, переход в Dashboard */
(function () {
    let mode = 'login';

    const modal = document.getElementById('authModal');
    const form = document.getElementById('authForm');
    const errorEl = document.getElementById('authError');

    function openModal(m) {
        mode = m || 'login';
        updateModalUI();
        modal.classList.remove('hidden');
        document.getElementById('authEmail').focus();
    }

    function closeModal() {
        modal.classList.add('hidden');
        errorEl.classList.add('hidden');
        form.reset();
    }

    function updateModalUI() {
        const isReg = mode === 'register';
        document.getElementById('authTitle').textContent = isReg ? 'Регистрация' : 'Вход';
        document.getElementById('authSub').textContent = isReg
            ? 'Создайте аккаунт — откроется мастер первой настройки'
            : 'Войдите, чтобы сохранить настройки и проекты';
        document.getElementById('authSubmit').textContent = isReg ? 'Создать аккаунт' : 'Войти';
        document.getElementById('nameLabel').style.display = isReg ? 'block' : 'none';
        document.getElementById('authName').style.display = isReg ? 'block' : 'none';
        document.getElementById('authSwitchText').textContent = isReg ? 'Уже есть аккаунт?' : 'Нет аккаунта?';
        document.getElementById('authSwitch').textContent = isReg ? 'Войти' : 'Зарегистрироваться';
    }

    async function goDashboard() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                location.href = '/app?view=dashboard';
            } else {
                openModal('login');
            }
        } catch (_) {
            location.href = '/app?view=dashboard';
        }
    }

    document.getElementById('btnLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('btnRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnDashboard')?.addEventListener('click', goDashboard);
    document.getElementById('btnHeroStart')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnCtaRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnCtaLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('authClose')?.addEventListener('click', closeModal);
    document.getElementById('authBackdrop')?.addEventListener('click', closeModal);
    document.getElementById('authSwitch')?.addEventListener('click', () => {
        mode = mode === 'login' ? 'register' : 'login';
        updateModalUI();
    });

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.classList.add('hidden');
        const email = document.getElementById('authEmail').value.trim();
        const password = document.getElementById('authPassword').value;
        const name = document.getElementById('authName').value.trim();
        const url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        const body = mode === 'register' ? { email, password, name } : { email, password };

        try {
            const r = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            location.href = mode === 'register' ? '/app?setup=1' : '/app?view=dashboard';
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    });

    const params = new URLSearchParams(location.search);
    if (params.get('auth') === 'login') openModal('login');
    if (params.get('auth') === 'register') openModal('register');

    fetch('/api/auth/me', { credentials: 'same-origin' }).then((r) => {
        if (r.ok) {
            document.getElementById('btnDashboard')?.classList.add('logged-in');
        }
    }).catch(() => {});
})();
