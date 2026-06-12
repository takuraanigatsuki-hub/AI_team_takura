/**
 * 3D Studio — офис, комната отдыха, библиотека
 * Совместимость: Three.js r128+
 */
(function (global) {
    const AGENT_ORDER = ['pm', 'architect', 'backend', 'frontend', 'qa', 'reviewer', 'doc_writer', 'devops', 'cursor', 'presenter', 'modeler'];

    const AGENT_EMOJIS = {
        pm: '🎯', architect: '🏛️', backend: '⚙️', frontend: '🎨',
        qa: '🧪', reviewer: '🔍', doc_writer: '📝', devops: '🔧', cursor: '⚡',
        presenter: '📽️', modeler: '🧊',
    };

    const AGENT_COLORS = {
        pm: 0xe8b84a, architect: 0x6c9eff, backend: 0x5ecf8a, frontend: 0xc792ea,
        qa: 0xf07178, reviewer: 0xffa657, doc_writer: 0x82aaff, devops: 0x56d4dd,
        cursor: 0xffd866, presenter: 0xff6b9d, modeler: 0x56cfe1,
    };

    const STUDIO_SLOTS = {
        pm: { x: -7, z: -4 }, architect: { x: -3.5, z: -4 },
        backend: { x: 0, z: -4 }, frontend: { x: 3.5, z: -4 },
        qa: { x: -7, z: 0 }, reviewer: { x: -3.5, z: 0 },
        doc_writer: { x: 0, z: 0 }, devops: { x: 3.5, z: 0 },
        cursor: { x: 7, z: -2 }, presenter: { x: 7, z: 1 }, modeler: { x: 7, z: 4 },
    };

    const REST_SLOTS = {
        pm: { x: 9, z: 5 }, architect: { x: 11, z: 5 }, backend: { x: 13, z: 5 },
        frontend: { x: 9, z: 7.5 }, qa: { x: 11, z: 7.5 }, reviewer: { x: 13, z: 7.5 },
        doc_writer: { x: 10, z: 10 }, devops: { x: 12, z: 10 },
        cursor: { x: 14, z: 10 }, presenter: { x: 15, z: 10 }, modeler: { x: 16, z: 10 },
    };

    const LIBRARY_SLOTS = {
        pm: { x: -11, z: 6 }, architect: { x: -9, z: 6 },
        backend: { x: -11, z: 8.5 }, frontend: { x: -9, z: 8.5 },
        qa: { x: -11, z: 11 }, reviewer: { x: -9, z: 11 },
        doc_writer: { x: -10, z: 13 }, devops: { x: -8, z: 13 },
        cursor: { x: -6, z: 13 }, presenter: { x: -5, z: 11 }, modeler: { x: -4, z: 9 },
    };

    let scene, camera, renderer, controls, raycaster, mouse;
    let agentMeshes = {};
    let clock;
    let onAgentClick = null;
    let animId = null;
    let resizeObserver = null;
    let canvasEl = null;
    let isDark = true;
    let sunLight = null;
    let restLightPt = null;

    let initialized = false;
    let onCanvasClickBound = null;

    function showError(msg) {
        const el = document.getElementById('studioError');
        if (el) {
            el.textContent = msg;
            el.style.display = 'flex';
        }
        console.error('[Studio]', msg);
    }

    function hideError() {
        const el = document.getElementById('studioError');
        if (el) el.style.display = 'none';
    }

    function getCanvasSize(canvas) {
        const parent = canvas?.parentElement;
        let w = parent?.clientWidth || canvas?.clientWidth || 0;
        let h = parent?.clientHeight || canvas?.clientHeight || 0;
        if (w < 200 || h < 150) {
            const headerH = document.querySelector('.header')?.offsetHeight || 104;
            const footerH = document.getElementById('statusFooter')?.offsetHeight || 28;
            w = Math.max(w, window.innerWidth);
            h = Math.max(h, window.innerHeight - headerH - footerH - 8);
        }
        return {
            width: Math.max(w, 320),
            height: Math.max(h, 240),
        };
    }

    function showLoading(show) {
        const el = document.getElementById('studioLoading');
        if (el) el.classList.toggle('hidden', !show);
    }

    function createFallbackControls(cam, dom) {
        const target = new THREE.Vector3(0, 0, 1);
        let theta = 0.4;
        let phi = 1.05;
        let radius = 20;
        let dragging = false;
        let lastX = 0;
        let lastY = 0;

        function syncCamera() {
            cam.position.x = target.x + radius * Math.sin(phi) * Math.sin(theta);
            cam.position.y = target.y + radius * Math.cos(phi);
            cam.position.z = target.z + radius * Math.sin(phi) * Math.cos(theta);
            cam.lookAt(target);
        }
        syncCamera();

        dom.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            dragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
        });
        window.addEventListener('mouseup', () => { dragging = false; });
        dom.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            theta -= (e.clientX - lastX) * 0.005;
            phi = Math.max(0.25, Math.min(1.45, phi + (e.clientY - lastY) * 0.005));
            lastX = e.clientX;
            lastY = e.clientY;
            syncCamera();
        });
        dom.addEventListener('wheel', (e) => {
            e.preventDefault();
            radius = Math.max(6, Math.min(38, radius + e.deltaY * 0.02));
            syncCamera();
        }, { passive: false });

        return {
            target,
            update() {},
            enabled: true,
        };
    }

    function createBodyMesh(color) {
        const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0.1 });
        const group = new THREE.Group();

        const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.24, 0.5, 12), mat);
        torso.position.y = 0.6;
        group.add(torso);

        const head = new THREE.Mesh(
            new THREE.SphereGeometry(0.2, 14, 14),
            new THREE.MeshStandardMaterial({ color: 0xffdbac, roughness: 0.6 })
        );
        head.position.y = 1.05;
        group.add(head);

        return group;
    }

    function createLabelSprite(emoji) {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, 128, 64);
        ctx.font = '40px "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(emoji, 64, 34);

        const tex = new THREE.CanvasTexture(canvas);
        tex.needsUpdate = true;
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
        sprite.scale.set(0.85, 0.42, 1);
        sprite.position.y = 1.45;
        sprite.renderOrder = 10;
        return sprite;
    }

    function createAgentAvatar(id, emoji, color) {
        const group = new THREE.Group();
        group.userData.agentId = id;

        const body = createBodyMesh(color);
        group.add(body);

        const desk = new THREE.Mesh(
            new THREE.BoxGeometry(0.9, 0.05, 0.55),
            new THREE.MeshStandardMaterial({ color: 0x4a5060 })
        );
        desk.position.set(0, 0.42, 0.35);
        desk.visible = false;
        desk.name = 'desk';
        group.add(desk);

        const screen = new THREE.Mesh(
            new THREE.BoxGeometry(0.5, 0.32, 0.03),
            new THREE.MeshStandardMaterial({ color: 0x1a2030, emissive: 0x3366cc, emissiveIntensity: 0.5 })
        );
        screen.position.set(0, 0.68, 0.58);
        screen.visible = false;
        screen.name = 'screen';
        group.add(screen);

        const glow = new THREE.Mesh(
            new THREE.RingGeometry(0.35, 0.42, 24),
            new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, side: THREE.DoubleSide })
        );
        glow.rotation.x = -Math.PI / 2;
        glow.position.y = 0.02;
        glow.visible = false;
        glow.name = 'glow';
        group.add(glow);

        group.add(createLabelSprite(emoji));
        group.userData.baseY = 0;
        group.userData.phase = Math.random() * Math.PI * 2;
        group.userData.status = 'idle';
        return group;
    }

    function buildRoom() {
        const floor = new THREE.Mesh(
            new THREE.PlaneGeometry(36, 28),
            new THREE.MeshStandardMaterial({ color: 0x454b58, roughness: 0.82, metalness: 0.05 })
        );
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);

        const grid = new THREE.GridHelper(36, 18, 0x6a7390, 0x323842);
        grid.position.y = 0.02;
        scene.add(grid);

        addZoneFloor(-2, -2, 16, 10, 0x3a3548, 0x9d4edd);
        addZoneFloor(11, 7.5, 8, 8, 0x2d4038, 0x5ecf8a);
        addZoneFloor(-10, 9, 6, 10, 0x3a3540, 0xe8b84a);

        addZoneSign('СТУДИЯ', -2, -7.2, 0x9d4edd);
        addZoneSign('ОТДЫХ', 11, 3.2, 0x5ecf8a);
        addZoneSign('БИБЛИОТЕКА', -10, 3.5, 0xe8b84a);

        buildDesks();
        buildRestRoom();
        buildLibrary();
        buildWalls();
        addAmbientParticles();
    }

    function addAmbientParticles() {
        const count = 120;
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 34;
            positions[i * 3 + 1] = 0.5 + Math.random() * 8;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 26;
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const mat = new THREE.PointsMaterial({
            color: 0x7aa2ff, size: 0.08, transparent: true, opacity: 0.45,
            blending: THREE.AdditiveBlending, depthWrite: false,
        });
        const points = new THREE.Points(geo, mat);
        points.name = 'ambientParticles';
        scene.add(points);
    }

    function addZoneFloor(x, z, w, d, color, accent) {
        const mesh = new THREE.Mesh(
            new THREE.PlaneGeometry(w, d),
            new THREE.MeshStandardMaterial({
                color,
                roughness: 0.78,
                emissive: accent || 0x000000,
                emissiveIntensity: accent ? 0.08 : 0,
            })
        );
        mesh.rotation.x = -Math.PI / 2;
        mesh.position.set(x, 0.03, z);
        scene.add(mesh);

        const ring = new THREE.Mesh(
            new THREE.RingGeometry(Math.min(w, d) * 0.32, Math.min(w, d) * 0.36, 32),
            new THREE.MeshBasicMaterial({ color: accent || 0x888888, transparent: true, opacity: 0.35, side: THREE.DoubleSide })
        );
        ring.rotation.x = -Math.PI / 2;
        ring.position.set(x, 0.04, z);
        scene.add(ring);
    }

    function addZoneSign(text, x, z, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 48;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.fillRect(0, 0, 256, 48);
        ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
        ctx.font = 'bold 22px Segoe UI, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, 128, 24);

        const tex = new THREE.CanvasTexture(canvas);
        const plane = new THREE.Mesh(
            new THREE.PlaneGeometry(3.2, 0.55),
            new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide })
        );
        plane.position.set(x, 1.2, z);
        scene.add(plane);
    }

    function buildDesks() {
        Object.values(STUDIO_SLOTS).forEach(({ x, z }) => {
            const desk = new THREE.Mesh(
                new THREE.BoxGeometry(1.2, 0.08, 0.7),
                new THREE.MeshStandardMaterial({ color: 0x5a6070 })
            );
            desk.position.set(x, 0.42, z + 0.4);
            scene.add(desk);
        });
    }

    function buildRestRoom() {
        [[9, 5], [11, 5], [13, 5]].forEach(([x, z]) => {
            const sofa = new THREE.Mesh(
                new THREE.BoxGeometry(1.8, 0.45, 0.8),
                new THREE.MeshStandardMaterial({ color: 0x5a9a6a })
            );
            sofa.position.set(x, 0.35, z);
            scene.add(sofa);
        });
    }

    function buildLibrary() {
        for (let i = 0; i < 3; i++) {
            const shelf = new THREE.Mesh(
                new THREE.BoxGeometry(0.2, 1.3, 2),
                new THREE.MeshStandardMaterial({ color: 0x6a5848 })
            );
            shelf.position.set(-11.5 + i * 1.1, 0.65, 8 + (i % 2) * 2.5);
            scene.add(shelf);
        }
    }

    function buildWalls() {
        const wallMat = new THREE.MeshStandardMaterial({ color: 0x2a2e38, roughness: 0.95 });
        [[0, 1.5, -14, 36, 3, 0.15], [0, 1.5, 14, 36, 3, 0.15],
         [-18, 1.5, 0, 0.15, 3, 28], [18, 1.5, 0, 0.15, 3, 28]].forEach(([x, y, z, w, h, d]) => {
            const wall = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat);
            wall.position.set(x, y, z);
            scene.add(wall);
        });
    }

    function getSlot(agent, location) {
        const id = agent.agent_id;
        if (location === 'rest_room') return REST_SLOTS[id] || REST_SLOTS.pm;
        if (location === 'library') return LIBRARY_SLOTS[id] || LIBRARY_SLOTS.pm;
        return STUDIO_SLOTS[id] || STUDIO_SLOTS.pm;
    }

    function updateAgentVisual(mesh, agent) {
        const slot = getSlot(agent, agent.location || 'studio');
        mesh.position.x += (slot.x - mesh.position.x) * 0.035;
        mesh.position.z += (slot.z - mesh.position.z) * 0.035;

        const desk = mesh.getObjectByName('desk');
        const screen = mesh.getObjectByName('screen');
        const inStudio = (agent.location || 'studio') === 'studio';

        if (desk) desk.visible = inStudio;
        if (screen) {
            screen.visible = inStudio && (agent.status === 'working' || agent.status === 'thinking');
            if (screen.material) {
                const intensity = agent.status === 'working' ? 1.2 : agent.status === 'thinking' ? 0.8 : 0.3;
                screen.material.emissiveIntensity = intensity;
            }
        }

        const glow = mesh.getObjectByName('glow');
        if (glow) {
            const active = ['working', 'learning', 'thinking'].includes(agent.status);
            glow.visible = active;
            if (glow.material) {
                glow.material.opacity = agent.status === 'working' ? 0.45 : 0.25;
            }
        }

        mesh.userData.status = agent.status || 'idle';
        mesh.userData.location = agent.location || 'studio';
    }

    function setupLights() {
        scene.add(new THREE.AmbientLight(0xffffff, 0.72));
        scene.add(new THREE.HemisphereLight(0xb8d4ff, 0x2a3038, 0.62));

        const sun = new THREE.DirectionalLight(0xfff4e6, 1.05);
        sun.position.set(10, 22, 8);
        sun.castShadow = true;
        sun.shadow.mapSize.set(1024, 1024);
        scene.add(sun);
        sunLight = sun;

        const fill = new THREE.DirectionalLight(0x88aaff, 0.42);
        fill.position.set(-8, 14, -6);
        scene.add(fill);

        const studioLight = new THREE.PointLight(0xc77dff, 0.85, 22);
        studioLight.position.set(-2, 5, -2);
        scene.add(studioLight);

        const restLight = new THREE.PointLight(0x5ecf8a, 0.7, 20);
        restLight.position.set(11, 4, 7);
        scene.add(restLight);
        restLightPt = restLight;

        const libLight = new THREE.PointLight(0xe8b84a, 0.65, 18);
        libLight.position.set(-10, 4, 9);
        scene.add(libLight);
    }

    function animate() {
        animId = requestAnimationFrame(animate);
        if (!renderer || !scene || !camera) return;

        const t = clock.getElapsedTime();
        const particles = scene.getObjectByName('ambientParticles');
        if (particles) particles.rotation.y = t * 0.015;

        Object.entries(speechSprites).forEach(([id, sprite) => {
            const mesh = agentMeshes[id];
            if (mesh) sprite.position.set(mesh.position.x, mesh.position.y + 2.1 + Math.sin(t * 3) * 0.05, mesh.position.z);
            if (sprite.userData.expires && performance.now() > sprite.userData.expires) {
                scene.remove(sprite);
                delete speechSprites[id];
            }
        });

        if (confettiGroup) {
            for (let i = confettiGroup.children.length - 1; i >= 0; i--) {
                const p = confettiGroup.children[i];
                p.userData.life -= 0.016;
                p.position.x += p.userData.vx;
                p.position.y += p.userData.vy;
                p.position.z += p.userData.vz;
                p.userData.vy -= 0.004;
                p.rotation.x += 0.1;
                p.rotation.z += 0.08;
                if (p.userData.life <= 0) confettiGroup.remove(p);
            }
            if (!confettiGroup.children.length) { scene.remove(confettiGroup); confettiGroup = null; }
        }

        if (flyTarget && flyProgress < 1 && controls) {
            flyProgress = Math.min(1, flyProgress + 0.025);
            const e = 1 - Math.pow(1 - flyProgress, 3);
            camera.position.x += (flyTarget.tx - camera.position.x) * e * 0.08;
            camera.position.y += (flyTarget.ty - camera.position.y) * e * 0.08;
            camera.position.z += (flyTarget.tz - camera.position.z) * e * 0.08;
            controls.target.x += (flyTarget.cx - controls.target.x) * e * 0.12;
            controls.target.z += (flyTarget.cz - controls.target.z) * e * 0.12;
            if (flyProgress >= 1) flyTarget = null;
        }

        Object.values(agentMeshes).forEach((mesh) => {
            const status = mesh.userData.status || 'idle';
            const phase = mesh.userData.phase;
            let bob = Math.sin(t * 2 + phase) * 0.02;
            if (status === 'working') bob = Math.sin(t * 8 + phase) * 0.035;
            if (status === 'learning') bob = Math.sin(t * 3 + phase) * 0.025;
            mesh.position.y = mesh.userData.baseY + bob;
        });

        if (controls) controls.update();
        renderer.render(scene, camera);
    }

    function onCanvasClick(event) {
        if (!raycaster || !camera || !renderer) return;
        const rect = renderer.domElement.getBoundingClientRect();
        if (!rect.width || !rect.height) return;

        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects(Object.values(agentMeshes), true);

        for (const hit of hits) {
            let obj = hit.object;
            while (obj && !obj.userData.agentId) obj = obj.parent;
            if (obj && obj.userData.agentId && onAgentClick) {
                flyToAgent(obj.userData.agentId);
                onAgentClick(obj.userData.agentId);
                break;
            }
        }
    }

    function resize(canvas) {
        if (!renderer || !camera || !canvas) return;
        const { width, height } = getCanvasSize(canvas);
        if (width < 10 || height < 10) return;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height, false);
    }

    function init(canvas, clickCallback) {
        if (!canvas) {
            showError('Canvas не найден');
            return false;
        }

        if (typeof THREE === 'undefined') {
            showError('Three.js не загружен. Проверьте интернет.');
            return false;
        }

        const { width, height } = getCanvasSize(canvas);

        if (initialized && renderer) {
            onAgentClick = clickCallback;
            resize(canvas);
            showLoading(false);
            return true;
        }

        try {
            hideError();
            showLoading(true);
            canvasEl = canvas;
            onAgentClick = clickCallback;
            clock = new THREE.Clock();

            scene = new THREE.Scene();
            setTheme(isDark);

            camera = new THREE.PerspectiveCamera(52, width / height, 0.1, 200);
            camera.position.set(2, 15, 18);
            camera.lookAt(0, 0, 1);

            renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            renderer.setSize(width, height, false);
            renderer.setClearColor(0x12141a, 1);
            if (THREE.sRGBEncoding) renderer.outputEncoding = THREE.sRGBEncoding;
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;

            if (typeof THREE.OrbitControls !== 'undefined') {
                controls = new THREE.OrbitControls(camera, canvas);
                controls.enableDamping = true;
                controls.dampingFactor = 0.08;
                controls.maxPolarAngle = Math.PI / 2.08;
                controls.minDistance = 5;
                controls.maxDistance = 38;
                controls.target.set(0, 0, 1);
            } else {
                console.warn('[Studio] OrbitControls недоступен — fallback-управление');
                controls = createFallbackControls(camera, canvas);
            }

            setupLights();
            raycaster = new THREE.Raycaster();
            mouse = new THREE.Vector2();

            buildRoom();

            AGENT_ORDER.forEach((id) => {
                const mesh = createAgentAvatar(id, AGENT_EMOJIS[id] || '👤', AGENT_COLORS[id] || 0x888888);
                const slot = STUDIO_SLOTS[id];
                mesh.position.set(slot.x, 0, slot.z);
                scene.add(mesh);
                agentMeshes[id] = mesh;
            });

            if (onCanvasClickBound) canvas.removeEventListener('click', onCanvasClickBound);
            onCanvasClickBound = onCanvasClick;
            canvas.addEventListener('click', onCanvasClickBound);

            if (resizeObserver) resizeObserver.disconnect();
            resizeObserver = new ResizeObserver(() => resize(canvas));
            resizeObserver.observe(canvas.parentElement || canvas);

            resize(canvas);
            if (!animId) animate();
            initialized = true;
            showLoading(false);
            renderer.render(scene, camera);
            return true;
        } catch (err) {
            showLoading(false);
            showError('Ошибка 3D: ' + (err.message || err));
            return false;
        }
    }

    function wake(canvas) {
        canvas = canvas || canvasEl || document.getElementById('studioCanvas');
        if (!canvas) return false;
        if (!initialized) return init(canvas, onAgentClick);
        resize(canvas);
        if (renderer && scene && camera) renderer.render(scene, camera);
        return true;
    }

    let pipelineHighlightId = null;
    const speechSprites = {};
    let confettiGroup = null;
    let flyTarget = null;
    let flyProgress = 0;

    function makeSpeechSprite(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        const msg = String(text).slice(0, 42);
        ctx.fillStyle = 'rgba(20,21,25,0.92)';
        ctx.strokeStyle = '#7aa2ff';
        ctx.lineWidth = 2;
        roundRect(ctx, 4, 8, 248, 44, 10);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = '#f0f0f5';
        ctx.font = '14px Inter, Segoe UI, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(msg, 128, 36);
        const tex = new THREE.CanvasTexture(canvas);
        const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
        sprite.scale.set(2.2, 0.55, 1);
        sprite.renderOrder = 20;
        sprite.userData.expires = performance.now() + 4500;
        return sprite;
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.arcTo(x + w, y, x + w, y + h, r);
        ctx.arcTo(x + w, y + h, x, y + h, r);
        ctx.arcTo(x, y + h, x, y, r);
        ctx.arcTo(x, y, x + w, y, r);
        ctx.closePath();
    }

    function showSpeechBubble(agentId, text) {
        if (!scene || !text) return;
        const mesh = agentMeshes[agentId];
        if (!mesh) return;
        if (speechSprites[agentId]) {
            scene.remove(speechSprites[agentId]);
        }
        const sprite = makeSpeechSprite(text);
        sprite.position.set(mesh.position.x, mesh.position.y + 2.1, mesh.position.z);
        scene.add(sprite);
        speechSprites[agentId] = sprite;
    }

    function burstConfetti(agentId) {
        if (!scene) return;
        const mesh = agentMeshes[agentId];
        if (!mesh) return;
        if (confettiGroup) scene.remove(confettiGroup);
        confettiGroup = new THREE.Group();
        const colors = [0x6c63ff, 0x5ecf8a, 0xffd866, 0xc792ea, 0xf07178];
        for (let i = 0; i < 40; i++) {
            const m = new THREE.Mesh(
                new THREE.BoxGeometry(0.06, 0.06, 0.02),
                new THREE.MeshBasicMaterial({ color: colors[i % colors.length] })
            );
            m.position.copy(mesh.position);
            m.position.y += 1.2;
            m.userData.vx = (Math.random() - 0.5) * 0.15;
            m.userData.vy = Math.random() * 0.12 + 0.05;
            m.userData.vz = (Math.random() - 0.5) * 0.15;
            m.userData.life = 1.5 + Math.random();
            confettiGroup.add(m);
        }
        scene.add(confettiGroup);
    }

    function flyToAgent(agentId) {
        const mesh = agentMeshes[agentId];
        if (!mesh || !camera || !controls) return;
        flyTarget = {
            tx: mesh.position.x,
            tz: mesh.position.z + 4,
            ty: 12,
            cx: mesh.position.x,
            cz: mesh.position.z,
        };
        flyProgress = 0;
    }

    function updateAgents(agentsList) {
        if (!agentsList || !Object.keys(agentMeshes).length) return;
        agentsList.forEach((agent) => {
            const mesh = agentMeshes[agent.agent_id];
            if (mesh) updateAgentVisual(mesh, agent);
        });
        if (pipelineHighlightId) setPipelineHighlight(pipelineHighlightId);
    }

    function setPipelineHighlight(agentId) {
        pipelineHighlightId = agentId;
        Object.entries(agentMeshes).forEach(([id, mesh]) => {
            const s = id === agentId ? 1.12 : 1;
            mesh.scale.set(s, s, s);
            const glow = mesh.getObjectByName('glow');
            if (glow?.material && id === agentId) {
                glow.visible = true;
                glow.material.opacity = 0.65;
            }
        });
    }

    function setTheme(dark) {
        isDark = dark;
        if (!scene) return;
        const bg = dark ? 0x12141a : 0xd4dae6;
        const fogColor = dark ? 0x181b24 : 0xe0e5ef;
        scene.background = new THREE.Color(bg);
        if (scene.fog) {
            scene.fog.color.setHex(fogColor);
        } else {
            scene.fog = new THREE.Fog(fogColor, 28, 85);
        }
        if (renderer) renderer.setClearColor(bg, 1);
    }

    function setDayNight(isDay) {
        if (sunLight) sunLight.intensity = isDay ? 1.15 : 0.55;
        if (restLightPt) restLightPt.intensity = isDay ? 0.35 : 0.75;
        setTheme(!isDay);
    }

    function pulseScreen(agentId) {
        const mesh = agentMeshes[agentId];
        const screen = mesh?.getObjectByName('screen');
        if (!screen?.material) return;
        screen.visible = true;
        screen.material.emissive.setHex(0x44ffaa);
        screen.material.emissiveIntensity = 2;
        setTimeout(() => {
            if (screen.material) {
                screen.material.emissive.setHex(0x3366cc);
                screen.material.emissiveIntensity = 0.9;
            }
        }, 900);
    }

    function destroy() {
        if (animId) cancelAnimationFrame(animId);
        animId = null;
        if (resizeObserver) resizeObserver.disconnect();
        if (renderer) renderer.dispose();
        initialized = false;
    }

    global.StudioApp = {
        init, wake, updateAgents, resize, setTheme, destroy, setPipelineHighlight,
        showSpeechBubble, burstConfetti, flyToAgent, setDayNight, pulseScreen,
        isReady: () => initialized,
    };
})(window);
