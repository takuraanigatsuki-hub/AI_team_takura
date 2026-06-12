/** Mini-map 3D студии */
(function (global) {
    let canvas, ctx;

    function init() {
        canvas = document.getElementById('studioMinimap');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        canvas.width = 140;
        canvas.height = 100;
        draw({});
        setInterval(refresh, 2000);
    }

    async function refresh() {
        try {
            const r = await fetch('/api/agents');
            const d = await r.json();
            draw(d.agents || []);
        } catch (_) { /* ignore */ }
    }

    function draw(agents) {
        if (!ctx) return;
        ctx.fillStyle = '#1a1d24';
        ctx.fillRect(0, 0, 140, 100);
        ctx.strokeStyle = '#3a4050';
        ctx.strokeRect(8, 8, 124, 84);
        ctx.fillStyle = '#6c63ff';
        ctx.font = '9px Inter,sans-serif';
        ctx.fillText('STUDIO', 12, 18);
        const slots = {
            pm: [30, 35], architect: [45, 35], backend: [60, 35], frontend: [75, 35],
            qa: [30, 55], reviewer: [45, 55], doc_writer: [60, 55], devops: [75, 55],
            cursor: [95, 40],
        };
        (agents.length ? agents : Object.keys(slots).map((id) => ({ agent_id: id, status: 'idle' }))).forEach((a) => {
            const p = slots[a.agent_id];
            if (!p) return;
            const active = ['working', 'learning'].includes(a.status);
            ctx.beginPath();
            ctx.arc(p[0], p[1], active ? 5 : 3, 0, Math.PI * 2);
            ctx.fillStyle = active ? '#5ecf8a' : '#8890a0';
            ctx.fill();
        });
    }

    global.StudioMinimap = { init, refresh };
})(window);
