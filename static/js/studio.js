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

    const WALK_SPEED = 0.048;

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
        const group = new THREE.Group();
        group.name = 'body';
        const skinMat = new THREE.MeshStandardMaterial({ color: 0xffdbac, roughness: 0.52 });
        const shirtMat = new THREE.MeshStandardMaterial({ color, roughness: 0.42, metalness: 0.12 });
        const pantsMat = new THREE.MeshStandardMaterial({ color: 0x252a38, roughness: 0.72 });

        const legGeo = new THREE.CylinderGeometry(0.075, 0.085, 0.32, 8);
        const legL = new THREE.Mesh(legGeo, pantsMat);
        legL.position.set(-0.09, 0.18, 0);
        legL.name = 'legL';
        const legR = legL.clone();
        legR.position.x = 0.09;
        legR.name = 'legR';
        group.add(legL, legR);

        const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.21, 0.4, 14), shirtMat);
        torso.position.y = 0.54;
        torso.name = 'torso';
        torso.castShadow = true;
        group.add(torso);

        const armGeo = new THREE.CylinderGeometry(0.055, 0.048, 0.26, 8);
        const armL = new THREE.Mesh(armGeo, shirtMat);
        armL.position.set(-0.26, 0.5, 0.04);
        armL.rotation.z = 0.35;
        armL.name = 'armL';
        armL.userData.baseRot = { x: 0, z: 0.35 };
        const armR = armL.clone();
        armR.position.x = 0.26;
        armR.rotation.z = -0.35;
        armR.name = 'armR';
        armR.userData.baseRot = { x: 0, z: -0.35 };
        group.add(armL, armR);

        const head = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), skinMat);
        head.position.y = 0.9;
        head.name = 'head';
        head.castShadow = true;
        group.add(head);

        const halo = new THREE.Mesh(
            new THREE.TorusGeometry(0.11, 0.022, 8, 22),
            new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.4, roughness: 0.3 })
        );
        halo.rotation.x = Math.PI / 2;
        halo.position.y = 1.02;
        halo.name = 'halo';
        group.add(halo);

        return group;
    }

    function createOfficeChair(accentColor) {
        const chair = new THREE.Group();
        chair.name = 'chair';
        const frameMat = new THREE.MeshStandardMaterial({ color: 0x3a4050, metalness: 0.55, roughness: 0.35 });
        const seatMat = new THREE.MeshStandardMaterial({ color: 0x2e3340, roughness: 0.65 });
        const accentMat = new THREE.MeshStandardMaterial({ color: accentColor, roughness: 0.5, emissive: accentColor, emissiveIntensity: 0.08 });

        const base = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.26, 0.04, 16), frameMat);
        base.position.y = 0.02;
        chair.add(base);
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.22, 8), frameMat);
        pole.position.y = 0.14;
        chair.add(pole);
        const seat = new THREE.Mesh(new THREE.BoxGeometry(0.46, 0.07, 0.44), seatMat);
        seat.position.y = 0.28;
        chair.add(seat);
        const back = new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.38, 0.06), accentMat);
        back.position.set(0, 0.52, -0.18);
        back.name = 'chairBack';
        chair.add(back);
        return chair;
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

        const chair = createOfficeChair(color);
        chair.position.set(0, 0, -0.08);
        group.add(chair);

        const desk = new THREE.Mesh(
            new THREE.BoxGeometry(1.05, 0.05, 0.62),
            new THREE.MeshStandardMaterial({ color: 0x3d4455, roughness: 0.35, metalness: 0.15 })
        );
        desk.position.set(0, 0.4, 0.38);
        desk.castShadow = true;
        desk.receiveShadow = true;
        desk.visible = false;
        desk.name = 'desk';
        group.add(desk);

        const deskLegMat = new THREE.MeshStandardMaterial({ color: 0x2a2e38, metalness: 0.4, roughness: 0.5 });
        [[-0.42, 0.2, 0.12], [0.42, 0.2, 0.12], [-0.42, 0.2, 0.58], [0.42, 0.2, 0.58]].forEach(([x, y, z]) => {
            const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.38, 6), deskLegMat);
            leg.position.set(x, y, z);
            leg.visible = false;
            leg.name = 'deskPart';
            group.add(leg);
        });

        const screenFrame = new THREE.Mesh(
            new THREE.BoxGeometry(0.52, 0.34, 0.025),
            new THREE.MeshStandardMaterial({ color: 0x111520, roughness: 0.4, metalness: 0.3 })
        );
        screenFrame.position.set(0, 0.66, 0.62);
        screenFrame.visible = false;
        screenFrame.name = 'screenFrame';
        group.add(screenFrame);

        const screen = new THREE.Mesh(
            new THREE.BoxGeometry(0.46, 0.28, 0.02),
            new THREE.MeshStandardMaterial({
                color: 0x0a1020,
                emissive: 0x4488ff,
                emissiveIntensity: 0.55,
                roughness: 0.2,
            })
        );
        screen.position.set(0, 0.66, 0.635);
        screen.visible = false;
        screen.name = 'screen';
        group.add(screen);

        const keyboard = new THREE.Mesh(
            new THREE.BoxGeometry(0.28, 0.015, 0.1),
            new THREE.MeshStandardMaterial({ color: 0x222830, emissive: 0x223344, emissiveIntensity: 0.15 })
        );
        keyboard.position.set(0, 0.435, 0.48);
        keyboard.visible = false;
        keyboard.name = 'keyboard';
        group.add(keyboard);

        const glow = new THREE.Mesh(
            new THREE.RingGeometry(0.38, 0.48, 28),
            new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0, side: THREE.DoubleSide })
        );
        glow.rotation.x = -Math.PI / 2;
        glow.position.y = 0.02;
        glow.visible = false;
        glow.name = 'glow';
        group.add(glow);

        const book = new THREE.Mesh(
            new THREE.BoxGeometry(0.18, 0.22, 0.04),
            new THREE.MeshStandardMaterial({ color: 0xe8b84a, roughness: 0.6 })
        );
        book.position.set(0.15, 0.55, 0.2);
        book.rotation.y = -0.4;
        book.visible = false;
        book.name = 'book';
        group.add(book);

        group.add(createLabelSprite(emoji));
        group.userData.baseY = 0;
        group.userData.phase = Math.random() * Math.PI * 2;
        group.userData.idlePhase = Math.random() * 100;
        group.userData.status = 'idle';
        group.userData.faceAngle = 0;
        group.userData.targetX = 0;
        group.userData.targetZ = 0;
        return group;
    }

    function addProp(mesh, cast, receive) {
        if (cast) mesh.castShadow = true;
        if (receive) mesh.receiveShadow = true;
        scene.add(mesh);
        return mesh;
    }

    function buildRoom() {
        const floorMat = new THREE.MeshStandardMaterial({
            color: 0x2a2e38,
            roughness: 0.55,
            metalness: 0.08,
        });
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(36, 28), floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);

        addWoodPlanks(-2, -2, 16, 10, 0x3d3548);
        addWoodPlanks(11, 7.5, 8, 8, 0x2a3832);
        addWoodPlanks(-10, 9, 6, 10, 0x38342e);

        addZoneFloor(-2, -2, 16, 10, 0x3a3548, 0x9d4edd);
        addZoneFloor(11, 7.5, 8, 8, 0x2d4038, 0x5ecf8a);
        addZoneFloor(-10, 9, 6, 10, 0x3a3540, 0xe8b84a);

        addZoneSign('СТУДИЯ', -2, -7.2, 0x9d4edd);
        addZoneSign('ОТДЫХ', 11, 3.2, 0x5ecf8a);
        addZoneSign('БИБЛИОТЕКА', -10, 3.5, 0xe8b84a);

        buildCeiling();
        buildWindows();
        buildDesks();
        buildRestRoom();
        buildLibrary();
        buildOfficeDecor();
        buildWalls();
        addAmbientParticles();
    }

    function addWoodPlanks(cx, cz, w, d, baseColor) {
        const plankMat = new THREE.MeshStandardMaterial({ color: baseColor, roughness: 0.65, metalness: 0.05 });
        const rows = Math.floor(d / 0.8);
        for (let i = 0; i < rows; i++) {
            const plank = new THREE.Mesh(new THREE.PlaneGeometry(w * 0.96, 0.35), plankMat.clone());
            plank.material.color.offsetHSL(0, 0, (i % 2) * 0.03 - 0.015);
            plank.rotation.x = -Math.PI / 2;
            plank.position.set(cx, 0.015 + (i % 2) * 0.002, cz - d / 2 + 0.4 + i * 0.8);
            scene.add(plank);
        }
    }

    function buildCeiling() {
        const ceilMat = new THREE.MeshStandardMaterial({ color: 0x1e222c, roughness: 0.9 });
        const ceil = new THREE.Mesh(new THREE.PlaneGeometry(35, 27), ceilMat);
        ceil.rotation.x = Math.PI / 2;
        ceil.position.y = 3.2;
        scene.add(ceil);

        [[-2, -2], [11, 7], [-10, 9], [0, 0]].forEach(([x, z], i) => {
            const lightPanel = new THREE.Mesh(
                new THREE.BoxGeometry(1.8, 0.04, 0.9),
                new THREE.MeshStandardMaterial({
                    color: 0xffffff,
                    emissive: i === 0 ? 0xc77dff : 0xfff4e0,
                    emissiveIntensity: 0.85,
                    roughness: 0.2,
                })
            );
            lightPanel.position.set(x, 3.15, z);
            scene.add(lightPanel);
        });
    }

    function buildWindows() {
        const glassMat = new THREE.MeshStandardMaterial({
            color: 0x88bbff,
            transparent: true,
            opacity: 0.35,
            roughness: 0.05,
            metalness: 0.1,
            emissive: 0x224466,
            emissiveIntensity: 0.25,
            side: THREE.DoubleSide,
        });
        for (let i = 0; i < 5; i++) {
            const pane = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 2.2), glassMat);
            pane.position.set(-7 + i * 3.5, 1.6, -13.92);
            scene.add(pane);
            const frame = new THREE.Mesh(
                new THREE.BoxGeometry(2.9, 2.3, 0.08),
                new THREE.MeshStandardMaterial({ color: 0x1a1e28, roughness: 0.4, metalness: 0.5 })
            );
            frame.position.set(-7 + i * 3.5, 1.6, -13.88);
            scene.add(frame);
        }
        const cityGlow = new THREE.Mesh(
            new THREE.PlaneGeometry(34, 8),
            new THREE.MeshBasicMaterial({
                color: 0x4488cc,
                transparent: true,
                opacity: 0.12,
                blending: THREE.AdditiveBlending,
            })
        );
        cityGlow.position.set(0, 2, -13.5);
        scene.add(cityGlow);
    }

    function buildOfficeDecor() {
        const plantPot = new THREE.MeshStandardMaterial({ color: 0x5a4030, roughness: 0.8 });
        const plantLeaf = new THREE.MeshStandardMaterial({ color: 0x3d8a55, roughness: 0.7 });
        [[-8, -6], [6, -5], [14, 2], [-14, 4]].forEach(([x, z]) => {
            const pot = addProp(new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 0.28, 10), plantPot), false, true);
            pot.position.set(x, 0.14, z);
            for (let i = 0; i < 5; i++) {
                const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.14 + Math.random() * 0.08, 8, 8), plantLeaf);
                leaf.position.set(x + (Math.random() - 0.5) * 0.25, 0.35 + i * 0.12, z + (Math.random() - 0.5) * 0.25);
                leaf.scale.y = 1.4;
                scene.add(leaf);
            }
        });

        const coffeeBase = addProp(new THREE.Mesh(
            new THREE.BoxGeometry(0.7, 0.85, 0.55),
            new THREE.MeshStandardMaterial({ color: 0x3a4048, metalness: 0.4, roughness: 0.45 })
        ), true, true);
        coffeeBase.position.set(15, 0.42, 6);

        const board = addProp(new THREE.Mesh(
            new THREE.BoxGeometry(3.5, 1.4, 0.06),
            new THREE.MeshStandardMaterial({ color: 0xf5f5f0, roughness: 0.85 })
        ), false, true);
        board.position.set(-2, 1.5, -6.8);
        const boardFrame = new THREE.Mesh(
            new THREE.BoxGeometry(3.7, 1.55, 0.04),
            new THREE.MeshStandardMaterial({ color: 0x2a2e38, metalness: 0.3 })
        );
        boardFrame.position.set(-2, 1.5, -6.75);
        scene.add(boardFrame);

        const table = addProp(new THREE.Mesh(
            new THREE.CylinderGeometry(0.9, 0.9, 0.06, 24),
            new THREE.MeshStandardMaterial({ color: 0x4a5060, roughness: 0.35, metalness: 0.2 })
        ), true, true);
        table.position.set(0, 0.75, 6);
        for (let i = 0; i < 4; i++) {
            const chairAngle = (i / 4) * Math.PI * 2;
            const c = createOfficeChair(0x6c63ff);
            c.position.set(0 + Math.sin(chairAngle) * 1.3, 0, 6 + Math.cos(chairAngle) * 1.3);
            c.rotation.y = chairAngle;
            scene.add(c);
        }
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
        const topMat = new THREE.MeshStandardMaterial({ color: 0x454c5c, roughness: 0.32, metalness: 0.18 });
        const legMat = new THREE.MeshStandardMaterial({ color: 0x2a2e38, metalness: 0.45, roughness: 0.45 });
        Object.values(STUDIO_SLOTS).forEach(({ x, z }) => {
            const desk = addProp(new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.06, 0.72), topMat), true, true);
            desk.position.set(x, 0.72, z + 0.42);
            [[-0.52, 0.36, 0.1], [0.52, 0.36, 0.1], [-0.52, 0.36, 0.62], [0.52, 0.36, 0.62]].forEach(([lx, ly, lz]) => {
                const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.72, 6), legMat);
                leg.position.set(x + lx, ly, z + lz);
                leg.castShadow = true;
                scene.add(leg);
            });
            const monitor = new THREE.Mesh(
                new THREE.BoxGeometry(0.55, 0.36, 0.03),
                new THREE.MeshStandardMaterial({ color: 0x0c1018, emissive: 0x3366aa, emissiveIntensity: 0.35 })
            );
            monitor.position.set(x, 1.02, z + 0.68);
            scene.add(monitor);
            const stand = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.12, 0.06), legMat);
            stand.position.set(x, 0.88, z + 0.65);
            scene.add(stand);
        });
    }

    function buildRestRoom() {
        const sofaMat = new THREE.MeshStandardMaterial({ color: 0x4a8068, roughness: 0.75 });
        const cushionMat = new THREE.MeshStandardMaterial({ color: 0x5ecf8a, roughness: 0.8, emissive: 0x2a5038, emissiveIntensity: 0.1 });
        [[9, 5], [11, 5], [13, 5]].forEach(([x, z]) => {
            const base = addProp(new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.35, 0.85), sofaMat), true, true);
            base.position.set(x, 0.28, z);
            const back = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.55, 0.18), sofaMat);
            back.position.set(x, 0.55, z - 0.38);
            back.castShadow = true;
            scene.add(back);
            const cushion = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.12, 0.5), cushionMat);
            cushion.position.set(x, 0.48, z + 0.05);
            scene.add(cushion);
        });
        const tv = new THREE.Mesh(
            new THREE.BoxGeometry(2.2, 1.2, 0.06),
            new THREE.MeshStandardMaterial({ color: 0x111520, emissive: 0x4488ff, emissiveIntensity: 0.4 })
        );
        tv.position.set(11, 1.4, 3.5);
        scene.add(tv);
        const tvStand = new THREE.Mesh(
            new THREE.BoxGeometry(2.4, 0.5, 0.4),
            new THREE.MeshStandardMaterial({ color: 0x2a3038, roughness: 0.5 })
        );
        tvStand.position.set(11, 0.25, 3.5);
        scene.add(tvStand);
    }

    function buildLibrary() {
        const shelfMat = new THREE.MeshStandardMaterial({ color: 0x5a4838, roughness: 0.75 });
        const bookColors = [0xe8b84a, 0x6c63ff, 0x5ecf8a, 0xf07178, 0x56cfe1, 0xc792ea];
        for (let s = 0; s < 4; s++) {
            const sx = -11.8 + s * 1.05;
            for (let row = 0; row < 3; row++) {
                const shelf = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.04, 2.2), shelfMat);
                shelf.position.set(sx, 0.45 + row * 0.55, 8.5);
                scene.add(shelf);
                for (let b = 0; b < 6; b++) {
                    const book = new THREE.Mesh(
                        new THREE.BoxGeometry(0.08, 0.28 + Math.random() * 0.12, 0.18),
                        new THREE.MeshStandardMaterial({ color: bookColors[(s + b + row) % bookColors.length], roughness: 0.6 })
                    );
                    book.position.set(sx - 0.3 + b * 0.12, 0.58 + row * 0.55, 8.2 + (b % 3) * 0.35);
                    book.rotation.y = (Math.random() - 0.5) * 0.15;
                    scene.add(book);
                }
            }
        }
        const table = new THREE.Mesh(
            new THREE.BoxGeometry(1.6, 0.06, 0.9),
            new THREE.MeshStandardMaterial({ color: 0x4a4035, roughness: 0.55 })
        );
        table.position.set(-8, 0.72, 12);
        table.castShadow = true;
        scene.add(table);
        const lamp = new THREE.PointLight(0xffe8b0, 0.5, 6);
        lamp.position.set(-8, 1.8, 12);
        scene.add(lamp);
    }

    function buildWalls() {
        const wallMat = new THREE.MeshStandardMaterial({ color: 0x232830, roughness: 0.92 });
        const accentMat = new THREE.MeshStandardMaterial({ color: 0x2e3340, roughness: 0.85 });
        [[0, 1.6, -14, 36, 3.2, 0.18], [0, 1.6, 14, 36, 3.2, 0.18],
         [-18, 1.6, 0, 0.18, 3.2, 28], [18, 1.6, 0, 0.18, 3.2, 28]].forEach(([x, y, z, w, h, d]) => {
            addProp(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), wallMat), false, true).position.set(x, y, z);
        });
        [[-2, 1.6, -13.85, 16, 3.2, 0.06], [11, 1.6, 7.85, 8, 3.2, 0.06]].forEach(([x, y, z, w, h, d], i) => {
            const glass = new THREE.Mesh(
                new THREE.BoxGeometry(w, h * 0.7, d),
                new THREE.MeshStandardMaterial({
                    color: i === 0 ? 0x9d4edd : 0x5ecf8a,
                    transparent: true,
                    opacity: 0.08,
                    roughness: 0.1,
                    side: THREE.DoubleSide,
                })
            );
            glass.position.set(x, y, z);
            scene.add(glass);
        });
        const baseboardMat = new THREE.MeshStandardMaterial({ color: 0x1a1e26 });
        [[0, 0.08, -13.9, 35, 0.12, 0.1], [0, 0.08, 13.9, 35, 0.12, 0.1]].forEach(([x, y, z, w, h, d]) => {
            addProp(new THREE.Mesh(new THREE.BoxGeometry(w, h, d), baseboardMat), false, true).position.set(x, y, z);
        });
        addProp(new THREE.Mesh(new THREE.BoxGeometry(36, 0.15, 28), accentMat), false, true).position.set(0, 0.075, 0);
    }

    function getSlot(agent, location) {
        const id = agent.agent_id;
        if (location === 'rest_room') return REST_SLOTS[id] || REST_SLOTS.pm;
        if (location === 'library') return LIBRARY_SLOTS[id] || LIBRARY_SLOTS.pm;
        return STUDIO_SLOTS[id] || STUDIO_SLOTS.pm;
    }

    function updateAgentVisual(mesh, agent) {
        const slot = getSlot(agent, agent.location || 'studio');
        mesh.userData.targetX = slot.x;
        mesh.userData.targetZ = slot.z;
        mesh.position.x += (slot.x - mesh.position.x) * WALK_SPEED;
        mesh.position.z += (slot.z - mesh.position.z) * WALK_SPEED;

        const loc = agent.location || 'studio';
        const inStudio = loc === 'studio';
        const inRest = loc === 'rest_room';
        const inLib = loc === 'library';
        const status = agent.status || 'idle';

        ['screen', 'screenFrame', 'keyboard'].forEach((name) => {
            const o = mesh.getObjectByName(name);
            if (o) o.visible = inStudio;
        });
        const agentDesk = mesh.getObjectByName('desk');
        if (agentDesk) agentDesk.visible = false;
        mesh.traverse((c) => {
            if (c.name === 'deskPart') c.visible = false;
        });

        const chair = mesh.getObjectByName('chair');
        if (chair) chair.visible = !inRest;

        const book = mesh.getObjectByName('book');
        if (book) book.visible = inLib || status === 'learning';

        if (inRest) {
            mesh.userData.baseY = 0.12;
            mesh.userData.faceAngle = Math.atan2(11 - slot.x, 3.5 - slot.z);
        } else if (inLib) {
            mesh.userData.baseY = 0;
            mesh.userData.faceAngle = Math.atan2(-11.5 - slot.x, 8.5 - slot.z);
        } else {
            mesh.userData.baseY = 0;
            mesh.userData.faceAngle = 0;
        }

        const screen = mesh.getObjectByName('screen');
        const screenFrame = mesh.getObjectByName('screenFrame');
        if (screen) {
            screen.visible = inStudio && ['working', 'thinking', 'learning'].includes(status);
            if (screen.material) {
                const hues = { working: 0x4488ff, thinking: 0xaa66ff, learning: 0x44ccaa };
                screen.material.emissive.setHex(hues[status] || 0x3366cc);
                screen.material.emissiveIntensity = status === 'working' ? 1.1 : status === 'thinking' ? 0.75 : 0.5;
            }
        }
        if (screenFrame) screenFrame.visible = screen?.visible;

        const keyboard = mesh.getObjectByName('keyboard');
        if (keyboard) {
            keyboard.visible = inStudio && status === 'working';
            if (keyboard.material && status === 'working') {
                keyboard.material.emissiveIntensity = 0.25 + Math.sin(performance.now() * 0.008) * 0.12;
            }
        }

        const glow = mesh.getObjectByName('glow');
        if (glow) {
            const active = ['working', 'learning', 'thinking'].includes(status);
            glow.visible = active;
            if (glow.material) {
                glow.material.opacity = status === 'working' ? 0.5 : status === 'thinking' ? 0.35 : 0.28;
            }
        }

        const halo = mesh.getObjectByName('halo');
        if (halo?.material) {
            halo.material.emissiveIntensity = status === 'working' ? 0.65 : 0.35;
        }

        mesh.userData.status = status;
        mesh.userData.location = loc;
    }

    function animateAgent(mesh, t) {
        const status = mesh.userData.status || 'idle';
        const loc = mesh.userData.location || 'studio';
        const phase = mesh.userData.phase;
        const idlePhase = mesh.userData.idlePhase || 0;

        const dx = (mesh.userData.targetX ?? mesh.position.x) - mesh.position.x;
        const dz = (mesh.userData.targetZ ?? mesh.position.z) - mesh.position.z;
        const moving = Math.hypot(dx, dz) > 0.06;

        const armL = mesh.getObjectByName('armL');
        const armR = mesh.getObjectByName('armR');
        const head = mesh.getObjectByName('head');
        const torso = mesh.getObjectByName('torso');
        const legL = mesh.getObjectByName('legL');
        const legR = mesh.getObjectByName('legR');
        const chairBack = mesh.getObjectByName('chairBack');

        const resetLimb = () => {
            if (armL) {
                armL.rotation.x = armL.userData.baseRot?.x || 0;
                armL.rotation.z = armL.userData.baseRot?.z || 0.35;
            }
            if (armR) {
                armR.rotation.x = armR.userData.baseRot?.x || 0;
                armR.rotation.z = armR.userData.baseRot?.z || -0.35;
            }
            if (head) { head.rotation.x = 0; head.rotation.y = 0; }
            if (torso) torso.rotation.x = 0;
            if (legL) legL.rotation.x = 0;
            if (legR) legR.rotation.x = 0;
        };

        if (moving) {
            const walkPhase = t * 11 + phase;
            mesh.position.y = mesh.userData.baseY + Math.abs(Math.sin(walkPhase)) * 0.045;
            mesh.rotation.y += (Math.atan2(dx, dz) - mesh.rotation.y) * 0.12;
            if (legL) legL.rotation.x = Math.sin(walkPhase) * 0.55;
            if (legR) legR.rotation.x = Math.sin(walkPhase + Math.PI) * 0.55;
            if (armL) armL.rotation.x = Math.sin(walkPhase + Math.PI) * 0.35;
            if (armR) armR.rotation.x = Math.sin(walkPhase) * 0.35;
            return;
        }

        resetLimb();
        const face = mesh.userData.faceAngle || 0;
        mesh.rotation.y += (face - mesh.rotation.y) * 0.08;

        if (loc === 'rest_room' || status === 'resting') {
            mesh.position.y = mesh.userData.baseY + Math.sin(t * 1.2 + phase) * 0.012;
            if (torso) torso.rotation.x = -0.22;
            if (chairBack) chairBack.rotation.x = -0.15;
            if (head) head.rotation.x = -0.08;
            return;
        }

        if (status === 'working' && loc === 'studio') {
            mesh.position.y = mesh.userData.baseY + Math.sin(t * 8 + phase) * 0.018;
            const typePhase = t * 14 + phase;
            if (armL) { armL.rotation.x = Math.sin(typePhase) * 0.42 - 0.2; armL.rotation.z = 0.15; }
            if (armR) { armR.rotation.x = Math.sin(typePhase + 1.2) * 0.42 - 0.2; armR.rotation.z = -0.15; }
            if (head) head.rotation.x = Math.sin(t * 5 + phase) * 0.06;
            if (torso) torso.rotation.x = 0.06;
            return;
        }

        if (status === 'thinking') {
            mesh.position.y = mesh.userData.baseY + Math.sin(t * 2.5 + phase) * 0.015;
            if (head) {
                head.rotation.y = Math.sin(t * 1.2 + idlePhase) * 0.3;
                head.rotation.x = -0.1;
            }
            if (armR) { armR.rotation.x = -0.55; armR.rotation.z = -0.1; }
            return;
        }

        if (status === 'learning' || loc === 'library') {
            mesh.position.y = mesh.userData.baseY + Math.sin(t * 2 + phase) * 0.01;
            if (armR) { armR.rotation.x = -0.45; armR.rotation.z = -0.2; }
            if (head) head.rotation.x = 0.15;
            return;
        }

        mesh.position.y = mesh.userData.baseY + Math.sin(t * 1.8 + phase) * 0.014;
        mesh.rotation.y = face + Math.sin(t * 0.6 + idlePhase) * 0.15;
        if (Math.sin(t * 0.3 + idlePhase) > 0.92) {
            if (armL) armL.rotation.z = 0.35 + Math.sin(t * 4) * 0.2;
            if (armR) armR.rotation.z = -0.35 - Math.sin(t * 4) * 0.2;
        }
    }

    function setupLights() {
        scene.add(new THREE.AmbientLight(0x8899bb, 0.45));
        scene.add(new THREE.HemisphereLight(0xa8c8ff, 0x1a2030, 0.55));

        const sun = new THREE.DirectionalLight(0xfff0d8, 1.15);
        sun.position.set(8, 24, 10);
        sun.castShadow = true;
        sun.shadow.mapSize.set(2048, 2048);
        sun.shadow.camera.near = 0.5;
        sun.shadow.camera.far = 60;
        sun.shadow.camera.left = -20;
        sun.shadow.camera.right = 20;
        sun.shadow.camera.top = 20;
        sun.shadow.camera.bottom = -20;
        scene.add(sun);
        sunLight = sun;

        const fill = new THREE.DirectionalLight(0x6688cc, 0.35);
        fill.position.set(-12, 16, -8);
        scene.add(fill);

        const rim = new THREE.DirectionalLight(0xc77dff, 0.25);
        rim.position.set(0, 8, -15);
        scene.add(rim);

        const studioLight = new THREE.PointLight(0xc77dff, 1.0, 24);
        studioLight.position.set(-2, 4.5, -2);
        scene.add(studioLight);

        const restLight = new THREE.PointLight(0x5ecf8a, 0.85, 22);
        restLight.position.set(11, 4, 7);
        scene.add(restLight);
        restLightPt = restLight;

        const libLight = new THREE.PointLight(0xe8b84a, 0.75, 20);
        libLight.position.set(-10, 4, 9);
        scene.add(libLight);
    }

    function animate() {
        animId = requestAnimationFrame(animate);
        if (!renderer || !scene || !camera) return;

        const t = clock.getElapsedTime();
        const particles = scene.getObjectByName('ambientParticles');
        if (particles) particles.rotation.y = t * 0.015;

        Object.entries(speechSprites).forEach(([id, sprite]) => {
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
            animateAgent(mesh, t);
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
                mesh.userData.targetX = slot.x;
                mesh.userData.targetZ = slot.z;
                mesh.castShadow = true;
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
        const bg = dark ? 0x0e1018 : 0xd4dae6;
        const fogColor = dark ? 0x141820 : 0xe0e5ef;
        scene.background = new THREE.Color(bg);
        if (scene.fog) {
            scene.fog.color.setHex(fogColor);
            scene.fog.near = 22;
            scene.fog.far = 72;
        } else {
            scene.fog = new THREE.Fog(fogColor, 22, 72);
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
