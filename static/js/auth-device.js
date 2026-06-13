(function () {
    const params = new URLSearchParams(location.search);
    const deviceId = params.get('id') || '';
    const userCode = params.get('code') || '';
    const codeEl = document.getElementById('deviceCode');
    const statusEl = document.getElementById('deviceStatus');
    const guestEl = document.getElementById('deviceGuest');
    const approveBtn = document.getElementById('deviceApproveBtn');
    const successEl = document.getElementById('deviceSuccess');
    const loginBtn = document.getElementById('deviceLoginBtn');
    const registerBtn = document.getElementById('deviceRegisterBtn');

    if (userCode) codeEl.textContent = userCode.replace(/(\d{3})(\d{3})/, '$1 $2');

    async function checkAuth() {
        if (!deviceId) {
            statusEl.textContent = 'Неверная ссылка. Запустите вход из приложения снова.';
            return;
        }
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                const user = await r.json();
                statusEl.textContent = `Вы вошли как ${user.name || user.email}`;
                guestEl.classList.add('hidden');
                approveBtn.classList.remove('hidden');
            } else {
                statusEl.textContent = 'Войдите на сайте, затем подтвердите вход в приложение';
                guestEl.classList.remove('hidden');
            }
        } catch (_) {
            statusEl.textContent = 'Ошибка соединения с сервером';
        }
    }

    loginBtn?.addEventListener('click', () => {
        location.href = `/?auth=login&next=${encodeURIComponent(location.pathname + location.search)}`;
    });
    registerBtn?.addEventListener('click', () => {
        location.href = `/?auth=register&next=${encodeURIComponent(location.pathname + location.search)}`;
    });

    approveBtn?.addEventListener('click', async () => {
        approveBtn.disabled = true;
        statusEl.textContent = 'Подтверждение…';
        try {
            const r = await fetch('/api/auth/device/approve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ device_id: deviceId }),
            });
            const d = await r.json();
            if (!r.ok) throw new Error(d.detail || 'Ошибка');
            approveBtn.classList.add('hidden');
            successEl.classList.remove('hidden');
            statusEl.textContent = 'Приложение авторизовано';
        } catch (err) {
            statusEl.textContent = err.message || String(err);
            approveBtn.disabled = false;
        }
    });

    checkAuth();
})();
