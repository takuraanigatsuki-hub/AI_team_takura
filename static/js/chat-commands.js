/**
 * Slash-команды в чате — автодополнение /
 * Enter → применить команду в поле и дописать промпт (без отправки)
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

    function findCommand(token) {
        const q = (token || '').toLowerCase();
        if (!q) return commands[0] || null;
        return commands.find((c) => c.cmd === q)
            || commands.find((c) => c.cmd.startsWith(q))
            || null;
    }

    /** Незавершённая команда — Enter должен применить, а не отправить */
    function isIncompleteSlashInput(text) {
        const val = (text || '').trim();
        if (!val.startsWith('/')) return false;
        if (isDropdownVisible()) return true;

        const body = val.slice(1).trim();
        if (!body) return true;

        const sp = body.indexOf(' ');
        const cmdToken = (sp >= 0 ? body.slice(0, sp) : body).toLowerCase();
        const rest = sp >= 0 ? body.slice(sp + 1).trim() : '';

        const cmd = findCommand(cmdToken);
        if (!cmd || cmd.cmd !== cmdToken) return true;
        if (!rest) return true;

        const prefix = (cmd.prefix || '').trim();
        if (prefix && rest === prefix.replace(/:\s*$/, '').trim()) return true;

        return false;
    }

    function isSlashComposing(text) {
        return isIncompleteSlashInput(text);
    }

    function resolveCommandForInput(text) {
        if (isDropdownVisible()) {
            const dd = getDropdown();
            const items = dd?.querySelectorAll('.slash-item');
            const cmdKey = items?.[activeIdx]?.dataset.cmd;
            if (cmdKey) return commands.find((c) => c.cmd === cmdKey) || null;
        }
        const val = (text || getInput()?.value || '').trim();
        const slash = val.lastIndexOf('/');
        const body = slash >= 0 ? val.slice(slash + 1).trim() : val.slice(1).trim();
        if (!body) return commands[0] || null;
        const sp = body.indexOf(' ');
        const cmdToken = (sp >= 0 ? body.slice(0, sp) : body).toLowerCase();
        return findCommand(cmdToken) || commands[0] || null;
    }

    function applyCommand(cmd) {
        const input = getInput();
        if (!input || !cmd) return;

        const val = input.value;
        const slash = val.lastIndexOf('/');
        const before = slash >= 0 ? val.slice(0, slash) : '';

        let userRest = '';
        if (slash >= 0) {
            const afterSlash = val.slice(slash + 1);
            const sp = afterSlash.indexOf(' ');
            if (sp >= 0) userRest = afterSlash.slice(sp + 1).trim();
        }

        const prompt = (cmd.prefix || '').trim();
        let newVal = before;
        if (prompt) {
            newVal += prompt + (userRest ? ` ${userRest}` : ' ');
        } else if (userRest) {
            newVal += userRest;
        } else {
            newVal += `${cmd.label || cmd.cmd}: `;
        }

        input.value = newVal;
        hide();

        if (cmd.target && document.getElementById('targetSelect')) {
            document.getElementById('targetSelect').value = cmd.target;
        }
        if (cmd.msg_type === 'learning' && global.setMsgType) {
            setMsgType('learning');
        } else if (cmd.msg_type === 'chat' && global.setMsgType) {
            setMsgType('chat');
        } else if (global.setMsgType) {
            setMsgType('task');
        }

        input.focus();
        const len = input.value.length;
        input.setSelectionRange(len, len);
    }

    function applyActive() {
        const cmd = resolveCommandForInput();
        if (cmd) applyCommand(cmd);
        return !!cmd;
    }

    function applyIfIncomplete(text) {
        if (!isIncompleteSlashInput(text)) return false;
        applyActive();
        return true;
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
        const text = getInput()?.value ?? '';
        if (!isIncompleteSlashInput(text) && !isDropdownVisible()) return false;
        e.preventDefault();
        applyActive();
        return true;
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
        isIncompleteSlashInput,
        applyIfIncomplete,
        applyActive,
    };
    document.addEventListener('DOMContentLoaded', init);
})(window);
