/**
 * Slash-команды в чате — автодополнение /
 */
(function (global) {
    let commands = [];
    let activeIdx = 0;

    async function loadCommands() {
        try {
            const r = await fetch('/api/chat/commands');
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

    function hide() {
        getDropdown()?.classList.add('hidden');
        activeIdx = 0;
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

    function renderDropdown(query) {
        const dd = getDropdown();
        if (!dd) return;
        const q = query.toLowerCase();
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
        renderDropdown(query);
    }

    function onKeydown(e) {
        const dd = getDropdown();
        if (!dd || dd.classList.contains('hidden')) return;
        const items = dd.querySelectorAll('.slash-item');
        if (!items.length) return;
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIdx = (activeIdx + 1) % items.length;
            renderDropdown(getInput()?.value.slice(getInput().value.lastIndexOf('/') + 1).split(' ')[0] || '');
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIdx = (activeIdx - 1 + items.length) % items.length;
            renderDropdown(getInput()?.value.slice(getInput().value.lastIndexOf('/') + 1).split(' ')[0] || '');
        } else if (e.key === 'Tab' || (e.key === 'Enter' && dd.classList.contains('visible-on-enter'))) {
            const active = items[activeIdx];
            if (active && e.key === 'Tab') {
                e.preventDefault();
                const cmd = commands.find((c) => c.cmd === active.dataset.cmd);
                if (cmd) applyCommand(cmd);
            }
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

    global.ChatCommands = { init, loadCommands, hide };
    document.addEventListener('DOMContentLoaded', init);
})(window);
