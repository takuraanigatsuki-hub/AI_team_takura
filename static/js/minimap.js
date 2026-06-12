/** Mini-map 3D студии — компактный open-plan офис */
(function (global) {
    const MAP = { minX: -7.5, maxX: 7.5, minZ: -5.5, maxZ: 5.5 };
    const PAD = 14;
    const CSS_W = 200;
    const CSS_H = 150;

    const STUDIO = {
        pm: { x: -3.5, z: -2.6 }, architect: { x: -1.75, z: -2.6 },
        backend: { x: 0, z: -2.6 }, frontend: { x: 1.75, z: -2.6 },
        qa: { x: -3.5, z: -0.5 }, reviewer: { x: -1.75, z: -0.5 },
        doc_writer: { x: 0, z: -0.5 }, devops: { x: 1.75, z: -0.5 },
        cursor: { x: 3.1, z: -2.1 }, presenter: { x: 3.1, z: 0 }, modeler: { x: 3.1, z: 2.1 },
    };
    const REST = {
        pm: { x: 4.2, z: 2.6 }, architect: { x: 5.3, z: 2.6 }, backend: { x: 6.2, z: 2.6 },
        frontend: { x: 4.2, z: 3.5 }, qa: { x: 5.3, z: 3.5 }, reviewer: { x: 6.2, z: 3.5 },
        doc_writer: { x: 4.7, z: 4.2 }, devops: { x: 5.7, z: 4.2 },
        cursor: { x: 6.4, z: 4.2 }, presenter: { x: 6.4, z: 3.2 }, modeler: { x: 6.4, z: 2.4 },
    };
    const LIBRARY = {
        pm: { x: -5.4, z: 2.5 }, architect: { x: -4.2, z: 2.5 },
        backend: { x: -5.4, z: 3.4 }, frontend: { x: -4.2, z: 3.4 },
        qa: { x: -5.4, z: 4.1 }, reviewer: { x: -4.2, z: 4.1 },
        doc_writer: { x: -4.8, z: 4.6 }, devops: { x: -3.8, z: 4.6 },
        cursor: { x: -3.2, z: 4.6 }, presenter: { x: -3.2, z: 3.6 }, modeler: { x: -3.2, z: 2.7 },
    };

    const EMOJI = {
        pm: '🎯', architect: '🏛️', backend: '⚙️', frontend: '🎨',
        qa: '🧪', reviewer: '🔍', doc_writer: '📝', devops: '🔧',
        cursor: '⚡', presenter: '📽️', modeler: '🧊',
    };

    const ZONES = [
        { label: 'Работа', x: 0, z: -1.5, w: 8.2, h: 4.2, fill: 'rgba(130,145,165,0.18)', stroke: '#8899aa' },
        { label: 'Лаунж', x: 5.2, z: 3.4, w: 3.2, h: 2.4, fill: 'rgba(120,150,130,0.16)', stroke: '#7a9888' },
        { label: 'Библ.', x: -4.5, z: 3.4, w: 3.2, h: 2.8, fill: 'rgba(150,135,120,0.16)', stroke: '#988878' },
    ];

    let canvas, ctx, hitAreas = [];

    function setupCanvas() {
        if (!canvas || !ctx) return;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = Math.round(CSS_W * dpr);
        canvas.height = Math.round(CSS_H * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function worldToCanvas(x, z) {
        const nx = (x - MAP.minX) / (MAP.maxX - MAP.minX);
        const nz = (z - MAP.minZ) / (MAP.maxZ - MAP.minZ);
        return [
            PAD + nx * (CSS_W - PAD * 2),
            PAD + nz * (CSS_H - PAD * 2),
        ];
    }

    function rectFromZone(zone) {
        const tl = worldToCanvas(zone.x - zone.w / 2, zone.z - zone.h / 2);
        const br = worldToCanvas(zone.x + zone.w / 2, zone.z + zone.h / 2);
        return { x: tl[0], y: tl[1], w: br[0] - tl[0], h: br[1] - tl[1] };
    }

    function getSlot(agent) {
        const id = agent.agent_id || agent.id;
        const loc = agent.location || 'studio';
        if (loc === 'rest_room') return REST[id] || REST.pm;
        if (loc === 'library') return LIBRARY[id] || LIBRARY.pm;
        return STUDIO[id] || STUDIO.pm;
    }

    function agentColor(agent) {
        const loc = agent.location || 'studio';
        const active = ['working', 'learning', 'thinking'].includes(agent.status);
        if (loc === 'rest_room') return active ? '#7a9888' : '#6a8070';
        if (loc === 'library') return active ? '#988878' : '#807060';
        return active ? '#8899aa' : '#6a7588';
    }

    function draw(agents) {
        if (!ctx) return;
        setupCanvas();
        hitAreas = [];

        ctx.fillStyle = '#0a0c12';
        ctx.fillRect(0, 0, CSS_W, CSS_H);

        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 1;
        ctx.strokeRect(PAD - 2, PAD - 2, CSS_W - PAD * 2 + 4, CSS_H - PAD * 2 + 4);

        ZONES.forEach((zone) => {
            const r = rectFromZone(zone);
            ctx.fillStyle = zone.fill;
            ctx.fillRect(r.x, r.y, r.w, r.h);
            ctx.strokeStyle = zone.stroke;
            ctx.lineWidth = 1;
            ctx.strokeRect(r.x, r.y, r.w, r.h);
            ctx.fillStyle = zone.stroke;
            ctx.font = '600 8px Inter, Segoe UI, sans-serif';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillText(zone.label, r.x + 3, r.y + 3);
        });

        const list = Array.isArray(agents) && agents.length
            ? agents
            : Object.keys(STUDIO).map((id) => ({ agent_id: id, status: 'idle', location: 'studio' }));

        list.forEach((agent) => {
            const id = agent.agent_id || agent.id;
            const slot = getSlot(agent);
            const [cx, cy] = worldToCanvas(slot.x, slot.z);
            const active = ['working', 'learning', 'thinking'].includes(agent.status);
            const r = active ? 5.5 : 4;
            const color = agentColor(agent);

            if (active) {
                ctx.beginPath();
                ctx.arc(cx, cy, r + 3, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.globalAlpha = 0.28;
                ctx.fill();
                ctx.globalAlpha = 1;
            }

            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.strokeStyle = 'rgba(255,255,255,0.35)';
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.font = '9px "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(EMOJI[id] || '•', cx, cy - 0.5);

            hitAreas.push({ id, x: cx, y: cy, r: r + 4 });
        });
    }

    function init() {
        canvas = document.getElementById('studioMinimap');
        if (!canvas) return;
        ctx = canvas.getContext('2d');
        setupCanvas();
        draw([]);

        canvas.addEventListener('click', (e) => {
            const rect = canvas.getBoundingClientRect();
            const sx = CSS_W / rect.width;
            const sy = CSS_H / rect.height;
            const x = (e.clientX - rect.left) * sx;
            const y = (e.clientY - rect.top) * sy;
            for (const h of hitAreas) {
                const dx = x - h.x;
                const dy = y - h.y;
                if (dx * dx + dy * dy <= h.r * h.r && global.openPrivateChat) {
                    global.openPrivateChat(h.id);
                    break;
                }
            }
        });

        refresh();
        setInterval(refresh, 4000);
    }

    async function refresh() {
        try {
            const r = await fetch('/api/agents');
            const d = await r.json();
            draw(d.agents || []);
        } catch (_) { /* ignore */ }
    }

    global.StudioMinimap = { init, refresh, update: draw };
})(window);
