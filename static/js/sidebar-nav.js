/**
 * Sidebar navigation — role-based (guest / member / admin / investor)
 * Workspace (/workspace) и Portal (/portal) — разные меню
 */
(function (global) {
    const NAV_GUEST = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Обучение', items: [
            { view: 'agent-learning', icon: '📚', label: 'Обучение' },
        ]},
    ];

    const NAV_MEMBER = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Аналитика', items: [
            { view: 'dashboard', icon: '📊', label: 'Панель' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
            { view: 'sites', icon: '🌐', label: 'Сайты' },
        ]},
        { group: 'Планирование', items: [
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
        ]},
        { group: 'Обучение', advanced: true, items: [
            { view: 'agent-learning', icon: '📚', label: 'Обучение' },
            { view: 'sonya-studio', icon: '✨', label: 'Sonya Studio' },
        ]},
        { group: 'Обзор', items: [
            { view: 'investor', icon: '💼', label: 'Investor', investor: true },
        ]},
    ];

    const NAV_SUPPORT_WS = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
        ]},
    ];

    const NAV_ADMIN = [
        { group: 'Работа', items: [
            { view: 'tasks', icon: '📋', label: 'Inbox', primary: true },
            { view: 'chat', icon: '💬', label: 'Чат' },
            { view: 'kanban', icon: '📌', label: 'Kanban' },
        ]},
        { group: 'Аналитика', items: [
            { view: 'dashboard', icon: '📊', label: 'Панель' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
            { view: 'sites', icon: '🌐', label: 'Сайты' },
            { view: 'timeline', icon: '⏱', label: 'Timeline', adminLearning: true },
        ]},
        { group: 'Планирование', items: [
            { view: 'sprint', icon: '🏃', label: 'Sprint' },
        ]},
        { group: 'Обучение', items: [
            { view: 'agent-learning', icon: '📚', label: 'Обучение' },
            { view: 'sonya-studio', icon: '✨', label: 'Sonya Studio' },
            { view: 'design', icon: '🎨', label: 'Design Lab', adminLearning: true },
        ]},
        { group: 'Система', advanced: true, items: [
            { view: 'investor', icon: '💼', label: 'Investor', investor: true },
        ]},
    ];

    const NAV_INVESTOR = [
        { group: 'Обзор', items: [
            { view: 'investor', icon: '💼', label: 'Investor', primary: true },
            { view: 'dashboard', icon: '📊', label: 'Панель' },
        ]},
        { group: 'Просмотр', items: [
            { view: 'agent-learning', icon: '📚', label: 'Обучение' },
            { view: 'projects', icon: '📦', label: 'Проекты' },
        ]},
    ];

    const NAV_PORTAL_MEMBER = [
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет', primary: true },
        ]},
    ];

    const NAV_PORTAL_SUPPORT = [
        { group: 'Поддержка', items: [
            { view: 'support', icon: '💬', label: 'Тикеты', primary: true, supportPanel: true },
        ]},
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет' },
        ]},
    ];

    const NAV_PORTAL_ADMIN = [
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет', primary: true },
        ]},
        { group: 'Управление', items: [
            { view: 'admin', icon: '🛡', label: 'Admin', admin: true },
        ]},
    ];

    const NAV_PORTAL_FULL = [
        { group: 'Аккаунт', items: [
            { view: 'profile', icon: '👤', label: 'Кабинет', primary: true },
        ]},
        { group: 'Управление', items: [
            { view: 'admin', icon: '🛡', label: 'Admin', admin: true },
            { view: 'support', icon: '💬', label: 'Поддержка', supportPanel: true },
        ]},
    ];

    function isPortalShell() {
        return global.AppShell?.isPortal?.() || global.APP_SHELL === 'portal';
    }

    function getNav(user) {
        if (isPortalShell()) {
            const showAdmin = global.Auth?.canAccessAdmin?.(user);
            const showSupport = global.Auth?.canManageTickets?.(user) || user?.is_support;
            if (showAdmin && showSupport) return NAV_PORTAL_FULL;
            if (showAdmin) return NAV_PORTAL_ADMIN;
            if (showSupport) return NAV_PORTAL_SUPPORT;
            return NAV_PORTAL_MEMBER;
        }
        const mode = global.UICore?.getUiMode?.(user) || 'guest';
        if (mode === 'guest') return NAV_GUEST;
        if (mode === 'investor') return NAV_INVESTOR;
        if (mode === 'support') return NAV_SUPPORT_WS;
        if (mode === 'admin') return NAV_ADMIN;
        return NAV_MEMBER;
    }

    function isMobileNav() {
        return window.matchMedia('(max-width: 900px)').matches;
    }

    function openMobileSidebar() {
        if (isPortalShell()) {
            document.getElementById('portalMobileDrawer')?.classList.remove('hidden');
            document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'true');
            return;
        }
        document.body.classList.add('sidebar-open');
        document.getElementById('sidebarOverlay')?.classList.remove('hidden');
        document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'true');
    }

    function closeMobileSidebar() {
        if (isPortalShell()) {
            document.getElementById('portalMobileDrawer')?.classList.add('hidden');
            document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'false');
            return;
        }
        document.body.classList.remove('sidebar-open');
        document.getElementById('sidebarOverlay')?.classList.add('hidden');
        document.getElementById('mobileNavToggle')?.setAttribute('aria-expanded', 'false');
    }

    function canShow(item, user) {
        if (item.admin && !global.Auth?.canAccessAdmin?.(user)) return false;
        if (item.supportPanel && !global.Auth?.canManageTickets?.(user) && !user?.is_support) return false;
        if (item.adminLearning && !global.Auth?.canViewAgentLearning?.(user)) return false;
        if (item.view === 'agent-learning') return true;
        if (item.investor && !global.Auth?.canViewInvestorPortal?.(user)) return false;
        if (item.role === 'investor') {
            if (!user) return false;
            return user.is_investor || user.can_view_investor_portal || global.Auth?.canAccessAdmin?.(user);
        }
        if (user?.role === 'investor' || user?.is_investor) {
            if (!['investor', 'agent-learning', 'dashboard', 'projects'].includes(item.view)) return false;
        }
        if (user && global.ProfileCabinet?.canAccessView && !ProfileCabinet.canAccessView(user, item.view)) {
            if (!['tasks', 'chat', 'kanban', 'agent-learning'].includes(item.view)) return false;
        }
        return true;
    }

    function renderItem(i) {
        if (i.action === 'search') {
            return `<button type="button" class="sb-item sb-action" onclick="FeaturePack?.openGlobalSearch?.()" title="Поиск">
                <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span></button>`;
        }
        if (i.action === 'commands') {
            return `<button type="button" class="sb-item sb-action" onclick="FeaturePack?.openCommandPalette?.()" title="Команды">
                <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span></button>`;
        }
        return `<button type="button" class="sb-item${i.primary ? ' sb-primary' : ''}" data-view="${i.view}" onclick="SidebarNav.onNavClick('${i.view}')" title="${i.label}">
            <span class="sb-icon">${i.icon}</span><span class="sb-label">${i.label}</span>
        </button>`;
    }

    function renderPortalTopNav(user) {
        const top = document.getElementById('portalTopNav');
        if (!top) return;
        const NAV = getNav(user);
        const buttons = NAV.flatMap((g) => g.items.filter((i) => canShow(i, user))).map((i) =>
            `<button type="button" class="portal-topnav-btn" data-view="${i.view}" onclick="SidebarNav.onNavClick('${i.view}')">${i.icon} ${i.label}</button>`
        ).join('');
        top.innerHTML = buttons + `<a href="/download?reason=desktop-only" class="portal-topnav-dl"><span>⬇</span><span class="ptn-dl-text">Приложение</span></a>`;

        const drawer = document.getElementById('portalDrawerPanel');
        if (drawer) {
            drawer.innerHTML = buttons + `<a href="/download?reason=desktop-only" class="portal-topnav-dl" style="margin-top:12px"><span>⬇</span> Скачать приложение</a>`;
        }
    }

    function render() {
        const user = global.Auth?.getUser?.();
        if (isPortalShell()) {
            renderPortalTopNav(user);
            const showAdmin = global.Auth?.canAccessAdmin?.(user);
            const showSupport = global.Auth?.canManageTickets?.(user) || user?.is_support;
            document.getElementById('portalMobileAdmin')?.classList.toggle('hidden', !showAdmin);
            document.getElementById('portalMobileSupport')?.classList.toggle('hidden', !showSupport);
            return;
        }
        const el = document.getElementById('appSidebarNav');
        if (!el) return;
        const NAV = getNav(user);
        const quickBar = isPortalShell() ? '' : `<div class="sb-quick">
            <button type="button" class="sb-quick-btn sb-quick-unified" onclick="FeaturePack?.openCommandPalette?.()" title="Разделы, команды и поиск — Ctrl+K">
                <span class="sb-quick-icon" aria-hidden="true">⌘</span>
                <span class="sb-quick-label">Быстрый доступ</span>
                <kbd class="sb-quick-kbd">K</kbd>
            </button>
        </div>`;
        el.innerHTML = quickBar + NAV.map((g) => {
            const items = g.items.filter((i) => canShow(i, user));
            if (!items.length) return '';
            const adv = g.advanced ? ' sb-group-advanced' : '';
            return `<div class="sb-group${adv}"><div class="sb-group-label">${g.group}</div>${items.map(renderItem).join('')}</div>`;
        }).join('');

        if (isPortalShell()) return;
    }

    function onNavClick(view) {
        if (isMobileNav()) closeMobileSidebar();
        if (typeof global.switchView === 'function') global.switchView(view);
    }

    function setActive(view) {
        document.querySelectorAll('.sb-item[data-view]').forEach((b) => {
            b.classList.toggle('active', b.dataset.view === view || (view === 'agent-learning' && b.dataset.view === 'agent-learning') || (view === 'agent-learning' && b.dataset.view === 'design'));
        });
        document.querySelectorAll('.portal-topnav-btn[data-view]').forEach((b) => {
            b.classList.toggle('active', b.dataset.view === view);
        });
        if (global.UICore) UICore.setMobileTabActive(view);
    }

    function updateBadges(counts = {}) {
        if (isPortalShell()) return;
        document.querySelectorAll('.sb-item[data-view="tasks"] .sb-badge').forEach((b) => b.remove());
        const n = counts.awaiting || 0;
        if (n > 0) {
            const btn = document.querySelector('.sb-item[data-view="tasks"]');
            if (btn) {
                const badge = document.createElement('span');
                badge.className = 'sb-badge';
                badge.textContent = n > 99 ? '99+' : String(n);
                badge.title = 'Ждут вашего решения';
                btn.appendChild(badge);
            }
        }
        if (global.UICore) UICore.updateMobileBadges?.(n);
    }

    function setDensity(mode) {
        document.documentElement.setAttribute('data-density', mode);
        localStorage.setItem('ai-team-density', mode);
    }

    function updateCollapseBtn() {
        const btn = document.getElementById('sidebarToggle');
        if (!btn || isMobileNav()) return;
        const collapsed = document.body.classList.contains('sidebar-collapsed');
        btn.textContent = collapsed ? '▶' : '◀';
        btn.title = collapsed ? 'Развернуть панель' : 'Свернуть панель';
        btn.setAttribute('aria-label', btn.title);
    }

    function initDensity() {
        setDensity(localStorage.getItem('ai-team-density') || 'comfortable');
    }

    function toggleSidebar() {
        if (isMobileNav()) {
            if (document.body.classList.contains('sidebar-open')) closeMobileSidebar();
            else openMobileSidebar();
            return;
        }
        document.body.classList.toggle('sidebar-collapsed');
        localStorage.setItem('ai-team-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed') ? '1' : '');
        updateCollapseBtn();
    }

    function init() {
        if (!isPortalShell()) {
            if (localStorage.getItem('ai-team-sidebar-collapsed') === '1') {
                document.body.classList.add('sidebar-collapsed');
            }
            updateCollapseBtn();
            document.getElementById('sidebarToggle')?.addEventListener('click', toggleSidebar);
            document.getElementById('sidebarOverlay')?.addEventListener('click', closeMobileSidebar);
        } else {
            document.getElementById('portalDrawerBackdrop')?.addEventListener('click', closeMobileSidebar);
        }
        initDensity();
        render();
        document.getElementById('mobileNavToggle')?.addEventListener('click', toggleSidebar);
        window.addEventListener('resize', () => {
            if (!isMobileNav()) closeMobileSidebar();
        });
    }

    global.SidebarNav = { render, setActive, init, setDensity, onNavClick, closeMobileSidebar, updateBadges, getNav };
    document.addEventListener('DOMContentLoaded', init);
})(window);
