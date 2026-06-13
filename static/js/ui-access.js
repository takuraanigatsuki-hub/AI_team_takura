/**
 * UI Access — видимость меню по роли и тарифу
 */
(function (global) {
    function user() {
        return global.Auth?.getUser?.() || null;
    }

    function canAccessConsole(u) {
        if (!u) return false;
        if (u.is_owner || u.role === 'owner') return true;
        if (u.role === 'admin' || u.role === 'tech_admin') return true;
        const p = u.privileges || [];
        return p.includes('admin') || p.includes('manage_settings') || p.includes('manage_users');
    }

    function canAccessAdmin(u) {
        return global.Auth?.canAccessAdmin?.(u) || canAccessConsole(u);
    }

    function canOpenTechnicalSettings(u) {
        return canAccessConsole(u) || global.Auth?.canViewAgentLearning?.(u);
    }

    function hasFeature(u, feature) {
        if (!u) return false;
        if (u.is_owner || u.subscription?.unlimited) return true;
        const feats = u.subscription?.features_unlocked || [];
        return feats.includes(feature);
    }

    function toggle(sel, show) {
        document.querySelectorAll(sel).forEach((el) => el.classList.toggle('hidden', !show));
    }

    function applyMenuVisibility(u) {
        u = u === undefined ? user() : u;
        const admin = canAccessConsole(u);
        const learning = global.Auth?.canViewAgentLearning?.(u);
        const techSettings = canOpenTechnicalSettings(u);

        toggle('[data-ui="console"]', admin);
        toggle('[data-ui="admin-tools"]', admin);
        toggle('[data-ui="team-tools"]', admin);
        toggle('[data-ui="learning-settings"]', learning);
        toggle('[data-ui="tech-settings"]', techSettings);

        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) settingsBtn.classList.toggle('hidden', !techSettings);

        document.querySelectorAll('[data-ui="settings-entry"]').forEach((el) => {
            el.classList.toggle('hidden', !techSettings);
        });

        document.getElementById('cursorPanel')?.classList.toggle('hidden', !admin);

        document.body.classList.toggle('user-guest', !u);
        document.body.classList.toggle('user-member', !!u && !admin);
        document.body.classList.toggle('user-admin', admin);

        document.querySelectorAll('.dropdown-section-label[data-ui]').forEach((label) => {
            const section = label.dataset.ui;
            const hasVisible = [...document.querySelectorAll(`.dropdown-item[data-ui="${section}"]`)]
                .some((el) => !el.classList.contains('hidden'));
            label.classList.toggle('hidden', !hasVisible);
        });
    }

    function filterCommands(commands) {
        const u = user();
        const admin = canAccessConsole(u);
        const learning = global.Auth?.canViewAgentLearning?.(u);
        const investor = global.Auth?.canViewInvestorPortal?.(u);
        const blocked = [];
        if (!learning) blocked.push('Обучение', 'Дизайн-лаб', 'Timeline', '⏱ Timeline');
        if (!admin) {
            blocked.push(
                'Pipeline', 'Deploy', 'Cursor SDK', 'Cursor Panel', 'Cursor',
                'Backup', 'View-link', 'GitHub', 'Консоль', 'Admin',
                'Настройки платформы',
            );
        }
        if (!global.Auth?.canManageTickets?.(u)) blocked.push('Тикеты');
        if (!investor) blocked.push('Investor Portal', '💼 Investor');
        if (!canOpenTechnicalSettings(u)) blocked.push('⚙️ Настройки');
        return commands.filter((c) => !blocked.some((b) => c.label.includes(b)));
    }

    global.UIAccess = {
        canAccessConsole,
        canAccessAdmin,
        canOpenTechnicalSettings,
        canUseTeamTools: canAccessConsole,
        applyMenuVisibility,
        filterCommands,
    };

    document.addEventListener('DOMContentLoaded', () => {
        if (global.Auth?.getUser) UIAccess.applyMenuVisibility(global.Auth.getUser());
    });
})(window);
