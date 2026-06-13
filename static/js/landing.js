/** Landing page — вход, регистрация, скачивание приложения */
(function () {
    let mode = 'login';
    let currentUser = null;
    let downloadUrl = '/api/downloads/desktop/win/setup';

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

    function applyDownloadLinks(url) {
        downloadUrl = url || downloadUrl;
        document.querySelectorAll(
            '#lpBtnDownload, #lpBtnDownloadUser, #lpHeroDownload, #lpHeroDownloadUser, #lpSectionDownload, #lpCtaDownload, #lpFooterDownload'
        ).forEach((el) => {
            if (el) el.setAttribute('href', downloadUrl);
        });
    }

    async function initDownloadLinks() {
        try {
            const r = await fetch('/api/downloads/desktop/info');
            const info = await r.json();
            const setup = info.platforms?.find((p) => p.id === 'win-setup' && p.url);
            const portable = info.platforms?.find((p) => p.id === 'win-portable' && p.url);
            applyDownloadLinks((setup || portable)?.url || downloadUrl);
        } catch (_) {
            applyDownloadLinks(downloadUrl);
        }
    }

    function showGuestUI() {
        document.getElementById('lpAuthGuest')?.classList.remove('hidden');
        document.getElementById('lpAuthUser')?.classList.add('hidden');
        document.getElementById('lpHeroCtaGuest')?.classList.remove('hidden');
        document.getElementById('lpHeroCtaUser')?.classList.add('hidden');
        document.getElementById('lpCtaGuest')?.classList.remove('hidden');
        document.getElementById('lpCtaUser')?.classList.add('hidden');
    }

    function showUserUI(user) {
        currentUser = user;
        document.getElementById('lpAuthGuest')?.classList.add('hidden');
        document.getElementById('lpAuthUser')?.classList.remove('hidden');
        document.getElementById('lpHeroCtaGuest')?.classList.add('hidden');
        document.getElementById('lpHeroCtaUser')?.classList.remove('hidden');
        document.getElementById('lpCtaGuest')?.classList.add('hidden');
        document.getElementById('lpCtaUser')?.classList.remove('hidden');

        const name = user.name || user.email?.split('@')[0] || 'Пользователь';
        const pill = document.getElementById('lpUserPill');
        if (pill) {
            const tierLabel = user.is_owner
                ? (user.role_label || 'Владелец')
                : (user.subscription?.tier_name || '');
            const tierEmoji = user.subscription?.tier_emoji || '';
            const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
            const tierClass = user.is_owner ? ' lp-user-pill-tier--owner' : '';
            pill.innerHTML = `
                <span class="lp-user-pill-name" title="${esc(name)}">👤 ${esc(name)}</span>
                ${tierLabel ? `<span class="lp-user-pill-tier${tierClass}" title="${esc(tierLabel)}">${tierEmoji} ${esc(tierLabel)}</span>` : ''}`;
        }
    }

    async function initAuth() {
        try {
            const r = await fetch('/api/auth/me', { credentials: 'same-origin' });
            if (r.ok) {
                const user = await r.json();
                showUserUI(user);
                return user;
            }
        } catch (_) { /* guest */ }
        showGuestUI();
        return null;
    }

    async function logout() {
        await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' });
        currentUser = null;
        showGuestUI();
    }

    document.getElementById('btnLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('btnRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnHeroStart')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnHeroDemo')?.addEventListener('click', () => {
        document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' });
        setTimeout(() => window.LandingDemo?.playGuidedDemo?.(), 600);
    });
    document.getElementById('btnCtaRegister')?.addEventListener('click', () => openModal('register'));
    document.getElementById('btnCtaLogin')?.addEventListener('click', () => openModal('login'));
    document.getElementById('btnLogout')?.addEventListener('click', logout);
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
            const next = new URLSearchParams(location.search).get('next');
            if (next && next.startsWith('/')) {
                location.href = next;
                return;
            }
            location.href = mode === 'register' ? '/portal?setup=1' : '/portal?view=profile';
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    });

    const params = new URLSearchParams(location.search);
    initDownloadLinks();
    initAuth().then((user) => {
        if (user && !params.get('auth')) {
            closeModal();
        }
        if (params.get('auth') === 'login') openModal('login');
        if (params.get('auth') === 'register') openModal('register');
        if (window.LandingDemo) LandingDemo.init();
    });

    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener('click', (e) => {
            const id = link.getAttribute('href').slice(1);
            const target = document.getElementById(id);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                document.getElementById('lpNav')?.classList.remove('open');
                document.getElementById('lpNavToggle')?.setAttribute('aria-expanded', 'false');
            }
        });
    });

    const navToggle = document.getElementById('lpNavToggle');
    const nav = document.getElementById('lpNav');
    navToggle?.addEventListener('click', () => {
        const open = nav?.classList.toggle('open');
        navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
})();
