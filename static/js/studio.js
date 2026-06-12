/**
 * 3D Studio — офис, комната отдыха, библиотека
 * Совместимость: Three.js r128+
 */
(function (global) {
    const AGENT_ORDER = ['pm', 'architect', 'backend', 'frontend', 'qa', 'reviewer', 'doc_writer', 'devops', 'cursor'];

    const AGENT_EMOJIS = {
        pm: '🎯', architect: '🏛️', backend: '⚙️', frontend: '🎨',
        qa: '🧪', reviewer: '🔍', doc_writer: '📝', devops: '🔧', cursor: '⚡',
    };

    const AGENT_COLORS = {
        pm: 0xe8b84a, architect: 0x6c9eff, backend: 0x5ecf8a, frontend: 0xc792ea,
        qa: 0xf07178, reviewer: 0xffa657, doc_writer: 0x82aaff, devops: 0x56d4dd,
        cursor: 0xffd866,
    };

    const STUDIO_SLOTS = {
        pm: { x: -7, z: -4 }, architect: { x: -3.5, z: -4 },
        backend: { x: 0, z: -4 }, frontend: { x: 3.5, z: -4 },
        qa: { x: -7, z: 0 }, reviewer: { x: -3.5, z: 0 },
        doc_writer: { x: 0, z: 0 }, devops: { x: 3.5, z: 0 },
        cursor: { x: 7, z: -2 },
    };

    const REST_SLOTS = {
        pm: { x: 9, z: 5 }, architect: { x: 11, z: 5 }, backend: { x: 13, z: 5 },
        frontend: { x: 9, z: 7.5 }, qa: { x: 11, z: 7.5 }, reviewer: { x: 13, z: 7.5 },
        doc_writer: { x: 10, z: 10 }, devops: { x: 12, z: 10 }, cursor: { x: 14, z: 10 },
    };

    const LIBRARY_SLOTS = {
        pm: { x: -11, z: 6 }, architect: { x: -9, z: 6 },
        backend: { x: -11, z: 8.5 }, frontend: { x: -9, z: 8.5 },
        qa: { x: -11, z: 11 }, reviewer: { x: -9, z: 11 },
        doc_writer: { x: -10, z: 13 }, devops: { x: -8, z: 13 }, cursor: { x: -6, z: 13 },
    };

    let scene, camera, renderer, controls, raycaster, mouse;
    let agentMeshes = {};
    let clock;
    let onAgentClick = null;
    let animId = null;
    let resizeObserver = null;
    let canvasEl = null;
    let isDark = true;

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
        const parent = canvas.parentElement;
        const w = parent ? parent.clientWidth : canvas.clientWidth;
        const h = parent ? parent.clientHeight : canvas.clientHeight;
        return {
            width: Math.max(w || window.innerWidth, 320),
            height: Math.max(h || window.innerHeight - 60, 240),
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
            new THREE.MeshStandardMaterial({ color: 0x3a3f4a, roughness: 0.9 })
        );
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);

        const grid = new THREE.GridHelper(36, 36, 0x5a6270, 0x2e333c);
        grid.position.y = 0.02;
        scene.add(grid);

        addZoneFloor(-2, -2, 16, 10, 0x4a5060);
        addZoneFloor(11, 7.5, 8, 8, 0x3d5248);
        addZoneFloor(-10, 9, 6, 10, 0x454050);

        addZoneSign('СТУДИЯ', -2, -7.2, 0x6c9eff);
        addZoneSign('ОТДЫХ', 11, 3.2, 0x5ecf8a);
        addZoneSign('БИБЛИОТЕКА', -10, 3.5, 0xc792ea);

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

    function addZoneFloor(x, z, w, d, color) {
        const mesh = new THREE.Mesh(
            new THREE.PlaneGeometry(w, d),
            new THREE.MeshStandardMaterial({ color, roughness: 0.85 })
        );
        mesh.rotation.x = -Math.PI / 2;
        mesh.position.set(x, 0.03, z);
        scene.add(mesh);
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
        mesh.position.x += (slot.x - mesh.position.x) * 0.06;
        mesh.position.z += (slot.z - mesh.position.z) * 0.06;

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
        scene.add(new THREE.AmbientLight(0xffffff, 0.65));
        scene.add(new THREE.HemisphereLight(0xddeeff, 0x3a3f4a, 0.55));

        const sun = new THREE.DirectionalLight(0xffffff, 0.9);
        sun.position.set(10, 20, 8);
        sun.castShadow = true;
        scene.add(sun);

        const fill = new THREE.DirectionalLight(0xaaccff, 0.35);
        fill.position.set(-8, 12, -6);
        scene.add(fill);

        const restLight = new THREE.PointLight(0x5ecf8a, 0.6, 20);
        restLight.position.set(11, 4, 7);
        scene.add(restLight);

        const libLight = new THREE.PointLight(0xc792ea, 0.5, 18);
        libLight.position.set(-10, 4, 9);
        scene.add(libLight);
    }

    function animate() {
        animId = requestAnimationFrame(animate);
        if (!renderer || !scene || !camera) return;

        const t = clock.getElapsedTime();
        const particles = scene.getObjectByName('ambientParticles');
        if (particles) particles.rotation.y = t * 0.015;
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

        try {
            hideError();
            canvasEl = canvas;
            onAgentClick = clickCallback;
            clock = new THREE.Clock();

            const { width, height } = getCanvasSize(canvas);

            scene = new THREE.Scene();
            setTheme(isDark);

            camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 200);
            camera.position.set(0, 16, 20);
            camera.lookAt(0, 0, 2);

            renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            renderer.setSize(width, height, false);
            renderer.outputEncoding = THREE.sRGBEncoding || undefined;
            renderer.shadowMap.enabled = true;

            if (typeof THREE.OrbitControls !== 'undefined') {
                controls = new THREE.OrbitControls(camera, canvas);
                controls.enableDamping = true;
                controls.dampingFactor = 0.08;
                controls.maxPolarAngle = Math.PI / 2.05;
                controls.minDistance = 6;
                controls.maxDistance = 40;
                controls.target.set(0, 0, 2);
            } else {
                console.warn('[Studio] OrbitControls недоступен — камера статична');
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

            canvas.addEventListener('click', onCanvasClick);

            if (resizeObserver) resizeObserver.disconnect();
            resizeObserver = new ResizeObserver(() => resize(canvas));
            resizeObserver.observe(canvas.parentElement || canvas);

            resize(canvas);
            animate();
            return true;
        } catch (err) {
            showError('Ошибка 3D: ' + (err.message || err));
            return false;
        }
    }

    let pipelineHighlightId = null;

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
        const bg = dark ? 0x1a1d24 : 0xd8dce6;
        scene.background = new THREE.Color(bg);
        if (scene.fog) scene.fog.color.setHex(bg);
        else scene.fog = new THREE.Fog(bg, 30, 70);
    }

    function destroy() {
        if (animId) cancelAnimationFrame(animId);
        if (resizeObserver) resizeObserver.disconnect();
        if (renderer) renderer.dispose();
    }

    global.StudioApp = { init, updateAgents, resize, setTheme, destroy, setPipelineHighlight };
})(window);
