/** Страница входа — /login */
(function () {
    const form = document.getElementById('loginForm');
    const errorEl = document.getElementById('loginError');
    const passwordInput = document.getElementById('loginPassword');
    const toggleBtn = document.getElementById('togglePassword');
    const submitBtn = document.getElementById('loginSubmit');

    toggleBtn?.addEventListener('click', () => {
        const isPassword = passwordInput.type === 'password';
        passwordInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁';
        toggleBtn.setAttribute('aria-label', isPassword ? 'Скрыть пароль' : 'Показать пароль');
    });

    async function checkSession() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                const user = await r.json();
                const view = user.default_view && user.default_view !== 'profile'
                    ? user.default_view
                    : 'dashboard';
                location.replace(`/app?view=${encodeURIComponent(view)}`);
            }
        } catch (_) { /* guest */ }
    }

    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.classList.add('hidden');

        const email = document.getElementById('loginEmail').value.trim();
        const password = passwordInput.value;

        if (!email || !password) {
            errorEl.textContent = 'Заполните email и пароль';
            errorEl.classList.remove('hidden');
            return;
        }

        if (password.length < 6) {
            errorEl.textContent = 'Пароль должен быть не короче 6 символов';
            errorEl.classList.remove('hidden');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Вход…';

        try {
            const r = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ email, password }),
            });
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || 'Неверный email или пароль');

            const params = new URLSearchParams(location.search);
            const next = params.get('next');
            if (next && next.startsWith('/') && !next.startsWith('//')) {
                location.href = next;
            } else {
                location.href = '/app?view=dashboard';
            }
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Войти';
        }
    });

    checkSession();
})();
