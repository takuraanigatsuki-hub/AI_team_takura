/**
 * Процедурные текстуры для 3D-студии (canvas, без внешних файлов)
 */
(function (global) {
    const cache = {};

    function setRepeat(tex, rx, ry) {
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        tex.repeat.set(rx, ry);
        if (THREE.sRGBEncoding) tex.encoding = THREE.sRGBEncoding;
        tex.needsUpdate = true;
        return tex;
    }

    function make(name, w, h, draw) {
        if (cache[name]) return cache[name];
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        draw(ctx, w, h);
        const tex = new THREE.CanvasTexture(canvas);
        tex.name = name;
        if (THREE.sRGBEncoding) tex.encoding = THREE.sRGBEncoding;
        tex.needsUpdate = true;
        cache[name] = tex;
        return tex;
    }

    function drawCarpet(ctx, w, h) {
        ctx.fillStyle = '#3a3e48';
        ctx.fillRect(0, 0, w, h);
        const step = 8;
        for (let y = 0; y < h; y += step) {
            for (let x = 0; x < w; x += step) {
                const n = ((x * 17 + y * 31) % 100) / 100;
                ctx.fillStyle = n > 0.55 ? '#424650' : '#353942';
                ctx.fillRect(x, y, step, step);
            }
        }
        for (let i = 0; i < 900; i++) {
            const x = Math.random() * w;
            const y = Math.random() * h;
            ctx.fillStyle = `rgba(255,255,255,${Math.random() * 0.025})`;
            ctx.fillRect(x, y, 1, 1);
        }
    }

    function drawWall(ctx, w, h) {
        const g = ctx.createLinearGradient(0, 0, w, h);
        g.addColorStop(0, '#3a404a');
        g.addColorStop(1, '#323840');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < 4000; i++) {
            const x = Math.random() * w;
            const y = Math.random() * h;
            const a = Math.random() * 0.06;
            ctx.fillStyle = Math.random() > 0.5 ? `rgba(255,255,255,${a})` : `rgba(0,0,0,${a})`;
            ctx.fillRect(x, y, 1, 1);
        }
    }

    function drawCeiling(ctx, w, h) {
        ctx.fillStyle = '#eceef2';
        ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < 2500; i++) {
            const x = Math.random() * w;
            const y = Math.random() * h;
            ctx.fillStyle = `rgba(0,0,0,${Math.random() * 0.04})`;
            ctx.fillRect(x, y, 1, 1);
        }
    }

    function drawSky(ctx, w, h) {
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, '#6eb5e8');
        g.addColorStop(0.45, '#a8d4f0');
        g.addColorStop(0.72, '#d8e8f0');
        g.addColorStop(1, '#889898');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = 'rgba(60,70,85,0.55)';
        [[0.08, 0.52, 0.12, 0.48], [0.22, 0.45, 0.1, 0.55], [0.38, 0.5, 0.14, 0.5],
         [0.55, 0.42, 0.11, 0.58], [0.7, 0.48, 0.13, 0.52], [0.85, 0.44, 0.1, 0.56]].forEach(([x, y, bw, bh]) => {
            ctx.fillRect(x * w, y * h, bw * w, bh * h);
        });
        ctx.fillStyle = 'rgba(255,255,255,0.35)';
        ctx.beginPath();
        ctx.ellipse(w * 0.72, h * 0.18, w * 0.08, h * 0.05, 0, 0, Math.PI * 2);
        ctx.fill();
    }

    function drawWood(ctx, w, h) {
        ctx.fillStyle = '#5a4838';
        ctx.fillRect(0, 0, w, h);
        for (let y = 0; y < h; y += 3) {
            const shade = 90 + ((y * 7) % 25);
            ctx.strokeStyle = `rgb(${shade + 20},${shade + 5},${shade - 15})`;
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, y + Math.sin(y * 0.08) * 2);
            ctx.bezierCurveTo(w * 0.3, y + 2, w * 0.7, y - 1, w, y);
            ctx.stroke();
        }
    }

    function drawConcrete(ctx, w, h) {
        ctx.fillStyle = '#4a5058';
        ctx.fillRect(0, 0, w, h);
        for (let i = 0; i < 1200; i++) {
            ctx.fillStyle = `rgba(255,255,255,${Math.random() * 0.05})`;
            ctx.fillRect(Math.random() * w, Math.random() * h, 2, 1);
        }
    }

    function get(name) {
        switch (name) {
            case 'carpet':
                return setRepeat(make('carpet', 512, 512, drawCarpet), 4, 3);
            case 'wall':
                return setRepeat(make('wall', 512, 512, drawWall), 2.5, 1.2);
            case 'ceiling':
                return setRepeat(make('ceiling', 512, 512, drawCeiling), 3, 2.2);
            case 'sky':
                return make('sky', 512, 384, drawSky);
            case 'wood':
                return setRepeat(make('wood', 256, 256, drawWood), 2, 1);
            case 'concrete':
                return setRepeat(make('concrete', 256, 128, drawConcrete), 2, 1);
            default:
                return null;
        }
    }

    function material(name, opts) {
        const map = get(name);
        return new THREE.MeshStandardMaterial(Object.assign({
            map,
            roughness: 0.82,
            metalness: 0.04,
        }, opts || {}));
    }

    global.StudioTextures = { get, material };
})(window);
