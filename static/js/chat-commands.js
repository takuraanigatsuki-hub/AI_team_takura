/**
 * Slash-команды в чате — автодополнение /
 */
(function (global) {
    let commands = [];
    let activeIdx = 0;

    async function loadCommands() {
        try {
            const r = await fetch('/api/chat/commands', { credentials: 'same-origin' });
            if (r.ok) {
                const d = await r.json();
                commands = d.commands || [];
            }
        } catch (_) { /* ignore */ }
    }

    function getInput() {
        return document.getElementById('messageInput');
    }

    function getDropdown() {
        return document.getElementById('slashDropdown');
    }

    function isDropdownVisible() {
        const dd = getDropdown();
        return !!(dd && !dd.classList.contains('hidden'));
    }

    function hide() {
        getDropdown()?.classList.add('hidden');
        activeIdx = 0;
    }

    function currentSlashQuery(val) {
        val = val ?? getInput()?.value ?? '';
        const slash = val.lastIndexOf('/');
        if (slash < 0) return '';
        const after = val.slice(slash + 1);
        const space = after.indexOf(' ');
        return (space >= 0 ? after.slice(0, space) : after).toLowerCase();
    }

    function isSlashComposing(text) {
        const val = (text || '').trim();
        if (!val.startsWith('/')) return false;
        if (isDropdownVisible()) return true;
        const body = val.slice(1).trim();
        if (!body) return true;
        if (!body.includes(' ')) {
            const key = body.toLowerCase();
            const exact = commands.some((c) => c.cmd === key);
            if (!exact) return true;
        }
        return false;
    }

    function applyCommand(cmd) {
        const input = getInput();
        if (!input || !cmd) return;
        const val = input.value;
        const slash = val.lastIndexOf('/');
        const prefix = slash >= 0 ? val.slice(0, slash) : '';
        const rest = cmd.prefix && !val.slice(slash + 1).includes(' ')
            ? cmd.prefix
            : '';
        input.value = `${prefix}/${cmd.cmd}${rest ? ` ${rest}` : ' '}`;
        hide();
        if (cmd.msg_type === 'task' && global.setMsgType) setMsgType('task');
        if (cmd.msg_type === 'chat' && global.setMsgType) setMsgType('chat');
        if (cmd.target && document.getElementById('targetSelect')) {
            document.getElementById('targetSelect').value = cmd.target;
        }
        input.focus();
    }

    function applyActive() {
        const dd = getDropdown();
        if (!dd || dd.classList.contains('hidden')) return false;
        const items = dd.querySelectorAll('.slash-item');
        if (!items.length) return false;
        const cmdKey = items[activeIdx]?.dataset.cmd;
        const cmd = commands.find((c) => c.cmd === cmdKey);
        if (cmd) applyCommand(cmd);
        return !!cmd;
    }

    function renderDropdown(query) {
        const dd = getDropdown();
        if (!dd) return;
        const q = (query || '').toLowerCase();
        const matches = commands.filter((c) =>
            c.cmd.startsWith(q) || (c.label || '').toLowerCase().includes(q)
        ).slice(0, 10);
        if (!matches.length) {
            hide();
            return;
        }
        if (activeIdx >= matches.length) activeIdx = 0;
        dd.innerHTML = matches.map((c, i) => `
            <button type="button" class="slash-item${i === activeIdx ? ' active' : ''}" data-cmd="${c.cmd}">
                <span class="slash-icon">${c.icon || '⌘'}</span>
                <span class="slash-body">
                    <strong>/${c.cmd}</strong>
                    <small>${c.label || ''} · ${c.hint || ''}</small>
                </span>
            </button>`).join('');
        dd.classList.remove('hidden');
        dd.querySelectorAll('.slash-item').forEach((btn, i) => {
            btn.onclick = () => applyCommand(matches[i]);
        });
    }

    function updateDropdown(input) {
        const dd = getDropdown();
        if (!dd || !input) return;
        const val = input.value;
        const slash = val.lastIndexOf('/');
        if (slash < 0 || (slash > 0 && /\S/.test(val.slice(0, slash)))) {
            hide();
            return;
        }
        const after = val.slice(slash + 1);
        if (after.includes('\n')) {
            hide();
            return;
        }
        const space = after.indexOf(' ');
        const query = space >= 0 ? after.slice(0, space) : after;
        activeIdx = 0;
        renderDropdown(query);
    }

    function handleEnter(e) {
        if (isDropdownVisible()) {
            e.preventDefault();
            applyActive();
            return true;
        }
        const text = getInput()?.value.trim() || '';
        if (isSlashComposing(text)) {
            e.preventDefault();
            return true;
        }
        return false;
    }

    function onKeydown(e) {
        const dd = getDropdown();
        if (!dd || dd.classList.contains('hidden')) return;
        const items = dd.querySelectorAll('.slash-item');
        if (!items.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIdx = (activeIdx + 1) % items.length;
            renderDropdown(currentSlashQuery());
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIdx = (activeIdx - 1 + items.length) % items.length;
            renderDropdown(currentSlashQuery());
        } else if (e.key === 'Tab') {
            e.preventDefault();
            applyActive();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            e.stopPropagation();
            applyActive();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            hide();
        }
    }

    function init() {
        loadCommands();
        const input = getInput();
        if (!input) return;
        input.addEventListener('input', () => updateDropdown(input));
        input.addEventListener('keydown', onKeydown);
        input.addEventListener('blur', () => setTimeout(hide, 150));
    }

    global.ChatCommands = {
        init,
        loadCommands,
        hide,
        handleEnter,
        isSlashComposing,
        applyActive,
    };
    document.addEventListener('DOMContentLoaded', init);
})(window);
