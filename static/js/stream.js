/** Streaming LLM ответов агентов в чате */
(function (global) {
    const buffers = {};

    function ensureStreamEl(agentId, data) {
        let el = document.getElementById(`stream-${agentId}`);
        if (el) return el;
        const container = document.getElementById('messages');
        if (!container) return null;
        const welcome = container.querySelector('[data-welcome]');
        if (welcome) welcome.remove();
        el = document.createElement('div');
        el.id = `stream-${agentId}`;
        el.className = 'message agent stream-message';
        el.innerHTML = `
            <div class="msg-header">
                <span class="msg-emoji">${data.agent_emoji || '🤖'}</span>
                <span class="msg-name">${data.agent_name || agentId}</span>
                <span class="stream-badge">▌ streaming</span>
            </div>
            <div class="msg-body stream-body"></div>`;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
        return el;
    }

    function onStart(data) {
        buffers[data.agent_id] = '';
        ensureStreamEl(data.agent_id, data);
    }

    function onChunk(data) {
        if (data.done) {
            finalize(data.agent_id);
            return;
        }
        const el = ensureStreamEl(data.agent_id, data);
        if (!el) return;
        buffers[data.agent_id] = (buffers[data.agent_id] || '') + (data.chunk || '');
        const body = el.querySelector('.stream-body');
        if (body) {
            body.textContent = buffers[data.agent_id];
            const c = document.getElementById('messages');
            if (c) c.scrollTop = c.scrollHeight;
        }
    }

    function finalize(agentId) {
        const el = document.getElementById(`stream-${agentId}`);
        if (el) {
            const badge = el.querySelector('.stream-badge');
            if (badge) badge.remove();
            el.classList.remove('stream-message');
            el.removeAttribute('id');
        }
        delete buffers[agentId];
    }

    global.AgentStream = { onStart, onChunk, finalize };
})(window);
