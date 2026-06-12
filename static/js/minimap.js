/** Mini-map 3D студии — зоны и позиции агентов */
(function (global) {
    const MAP = { minX: -17, maxX: 17, minZ: -13, maxZ: 13 };
    const PAD = 14;
    const CSS_W = 200;
    const CSS_H = 150;

    const STUDIO = {
        pm: { x: -7, z: -4 }, architect: { x: -3.5, z: -4 },
        backend: { x: 0, z: -4 }, frontend: { x: 3.5, z: -4 },
        qa: { x: -7, z: 0 }, reviewer: { x: -3.5, z: 0 },
        doc_writer: { x: 0, z: 0 }, devops: { x: 3.5, z: 0 },
        cursor: { x: 7, z: -2 }, presenter: { x: 7, z: 1 }, modeler: { x: 7, z: 4 },
    };
    const REST = {
        pm: { x: 9, z: 5 }, architect: { x: 11, z: 5 }, backend: { x: 13, z: 5 },
        frontend: { x: 9, z: 7.5 }, qa: { x: 11, z: 7.5 }, reviewer: { x: 13, z: 7.5 },
        doc_writer: { x: 10, z: 10 }, devops: { x: 12, z: 10 },
        cursor: { x: 14, z: 10 }, presenter: { x: 15, z: 10 }, modeler: { x: 16, z: 10 },
    };
    const LIBRARY = {
        pm: { x: -11, z: 6 }, architect: { x: -9, z: 6 },
        backend: { x: -11, z: 8.5 }, frontend: { x: -9, z: 8.5 },
        qa: { x: -11, z: 11 }, reviewer: { x: -9, z: 11 },
        doc_writer: { x: -10, z: 13 }, devops: { x: -8, z: 13 },
        cursor: { x: -6, z: 13 }, presenter: { x: -5, z: 11 }, modeler: { x: -4, z: 9 },
    };

    const EMOJI = {
        pm: '🎯', architect: '🏛️', backend: '⚙️', frontend: '🎨',
        qa: '🧪', reviewer: '🔍', doc_writer: '📝', devops: '🔧',
        cursor: '⚡', presenter: '📽️', modeler: '🧊',
    };

    const ZONES = [
        { label: 'Студия', x: -2, z: -2, w: 16, h: 10, fill: 'rgba(108,158,255,0.2)', stroke: '#6c9eff' },
        { label: 'Отдых', x: 11, z: 7.5, w: 8, h: 8, fill: 'rgba(94,207,138,0.16)', stroke: '#5ecf8a' },
        { label: 'Библ.', x: -10, z: 9, w: 6, h: 10, fill: 'rgba(199,146,234,0.16)', stroke: '#c792ea' },
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
        if (loc === 'rest_room') return active ? '#5ecf8a' : '#7a9a82';
        if (loc === 'library') return active ? '#c792ea' : '#9a7ab0';
        return active ? '#5ecf8a' : '#7aa2ff';
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
