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

    function hasFeature(u, feature) {
        if (!u) return false;
        if (u.is_owner || u.subscription?.unlimited) return true;
        const feats = u.subscription?.features_unlocked || [];
        return feats.includes(feature);
    }

    function canUseTeamTools(u) {
        return hasFeature(u, 'pipeline') || hasFeature(u, 'deploy') || hasFeature(u, 'cursor');
    }

    function toggle(sel, show) {
        document.querySelectorAll(sel).forEach((el) => el.classList.toggle('hidden', !show));
    }

    function applyMenuVisibility(u) {
        u = u === undefined ? user() : u;
        const admin = canAccessConsole(u);
        const team = canUseTeamTools(u);
        const learning = global.Auth?.canViewAgentLearning?.(u);

        toggle('[data-ui="console"]', admin);
        toggle('[data-ui="admin-tools"]', admin);
        toggle('[data-ui="team-tools"]', team || admin);
        toggle('[data-ui="learning-settings"]', learning);

        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) settingsBtn.classList.toggle('hidden', !u);

        document.body.classList.toggle('user-guest', !u);
        document.body.classList.toggle('user-member', !!u && !admin);
        document.body.classList.toggle('user-admin', admin);
    }

    function filterCommands(commands) {
        const u = user();
        const admin = canAccessConsole(u);
        const team = canUseTeamTools(u);
        const learning = global.Auth?.canViewAgentLearning?.(u);
        const blocked = [];
        if (!learning) blocked.push('Обучение', 'Дизайн-лаб');
        if (!team && !admin) blocked.push('Pipeline', 'Deploy', 'Cursor SDK');
        return commands.filter((c) => !blocked.some((b) => c.label.includes(b)));
    }

    global.UIAccess = {
        canAccessConsole,
        canAccessAdmin,
        canUseTeamTools,
        applyMenuVisibility,
        filterCommands,
    };
})(window);
