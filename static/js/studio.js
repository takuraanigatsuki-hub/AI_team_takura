/**
 * 3D Studio — компактный open-plan офис (~14×10 м)
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

    const ROOM = { w: 14, d: 10, h: 2.75, hw: 7, hd: 5 };

    const STUDIO_SLOTS = {
        pm: { x: -3.5, z: -2.6 }, architect: { x: -1.75, z: -2.6 },
        backend: { x: 0, z: -2.6 }, frontend: { x: 1.75, z: -2.6 },
        qa: { x: -3.5, z: -0.5 }, reviewer: { x: -1.75, z: -0.5 },
        doc_writer: { x: 0, z: -0.5 }, devops: { x: 1.75, z: -0.5 },
        cursor: { x: 3.1, z: -2.1 }, presenter: { x: 3.1, z: 0 }, modeler: { x: 3.1, z: 2.1 },
    };

    const REST_SLOTS = {
        pm: { x: 4.2, z: 2.6 }, architect: { x: 5.3, z: 2.6 }, backend: { x: 6.2, z: 2.6 },
        frontend: { x: 4.2, z: 3.5 }, qa: { x: 5.3, z: 3.5 }, reviewer: { x: 6.2, z: 3.5 },
        doc_writer: { x: 4.7, z: 4.2 }, devops: { x: 5.7, z: 4.2 },
        cursor: { x: 6.4, z: 4.2 }, presenter: { x: 6.4, z: 3.2 }, modeler: { x: 6.4, z: 2.4 },
    };

    const LIBRARY_SLOTS = {
        pm: { x: -5.4, z: 2.5 }, architect: { x: -4.2, z: 2.5 },
        backend: { x: -5.4, z: 3.4 }, frontend: { x: -4.2, z: 3.4 },
        qa: { x: -5.4, z: 4.1 }, reviewer: { x: -4.2, z: 4.1 },
        doc_writer: { x: -4.8, z: 4.6 }, devops: { x: -3.8, z: 4.6 },
        cursor: { x: -3.2, z: 4.6 }, presenter: { x: -3.2, z: 3.6 }, modeler: { x: -3.2, z: 2.7 },
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
    let windowLight = null;
    let ambientLight = null;
    let hemiLight = null;
    let fillLight = null;
    let restLightPt = null;
    let libLightPt = null;
    const ceilingLights = [];
    let isDaytime = true;

    let initialized = false;
    let onCanvasClickBound = null;
    let uiIds = { loading: 'studioLoading', error: 'studioError' };

    function showError(msg) {
        const el = document.getElementById(uiIds.error);
        if (el) {
            el.textContent = msg;
            el.style.display = 'flex';
        }
        console.error('[Studio]', msg);
    }

    function hideError() {
        const el = document.getElementById(uiIds.error);
        if (el) el.style.display = 'none';
    }

    function getCanvasSize(canvas) {
        const parent = canvas?.parentElement;
        let w = parent?.clientWidth || canvas?.clientWidth || 0;
        let h = parent?.clientHeight || canvas?.clientHeight || 0;
        if (w < 200 || h < 150) {
            const headerH = document.querySelector('.header')?.offsetHeight || 104;
            const footerH = document.getElementById('statusFooter')?.offsetHeight || 28;
            const pipelineH = document.getElementById('pipelineBar')?.offsetHeight || 0;
            w = Math.max(w, window.innerWidth);
            h = Math.max(h, window.innerHeight - headerH - footerH - pipelineH - 8);
        }
        return {
            width: Math.max(w, 320),
            height: Math.max(h, 240),
        };
    }

    function showLoading(show) {
        const el = document.getElementById(uiIds.loading);
        if (el) el.classList.toggle('hidden', !show);
    }

    function createFallbackControls(cam, dom) {
        const target = new THREE.Vector3(0, 0.4, 0);
        let theta = 0.35;
        let phi = 1.12;
        let radius = 11;
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
            radius = Math.max(4, Math.min(16, radius + e.deltaY * 0.02));
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
            new THREE.TorusGeometry(0.1, 0.018, 8, 22),
            new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.15, roughness: 0.4 })
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

    function wallMaterial() {
        if (global.StudioTextures) {
            return StudioTextures.material('wall', { roughness: 0.88, metalness: 0.02 });
        }
        return new THREE.MeshStandardMaterial({ color: 0x323840, roughness: 0.88 });
    }

    function addWallBox(cx, cy, cz, ww, hh, dd, mat) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(ww, hh, dd), mat);
        m.position.set(cx, cy, cz);
        m.receiveShadow = true;
        scene.add(m);
        return m;
    }

    function buildRoom() {
        addCarpetFloor();
        addZoneFloor(0, -1.5, 8.2, 4.2, 0x343842, null);
        addZoneFloor(5.2, 3.4, 3.2, 2.4, 0x323840, null);
        addZoneFloor(-4.5, 3.4, 3.2, 2.8, 0x343840, null);

        addZoneSign('РАБОЧАЯ ЗОНА', 0, -4.35, 0x8899aa);
        addZoneSign('ЛАУНЖ', 5.2, 1.55, 0x7a9888);
        addZoneSign('БИБЛИОТЕКА', -4.5, 1.55, 0x988878);

        buildWalls();
        buildOverheadLights();
        buildOfficeDecor();
        buildPartitions();
        addAmbientParticles();
    }

    function addCarpetFloor() {
        const floorMat = global.StudioTextures
            ? StudioTextures.material('carpet', { roughness: 0.94, metalness: 0.01 })
            : new THREE.MeshStandardMaterial({ color: 0x3a3e48, roughness: 0.92, metalness: 0.02 });
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(ROOM.w, ROOM.d), floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.receiveShadow = true;
        scene.add(floor);
    }

    function buildOverheadLights() {
        const y = ROOM.h - 0.08;
        const lightPositions = [
            [-2.5, -2], [0.5, -2], [3, -2],
            [-2.5, 0.5], [0.5, 0.5], [3, 0.5],
            [-4, 3.2], [5, 3.2],
        ];
        lightPositions.forEach(([x, z]) => {
            const spot = new THREE.SpotLight(0xfff4e8, 0.55, 18, Math.PI / 3.4, 0.5, 1);
            spot.position.set(x, y, z);
            spot.castShadow = false;
            spot.target.position.set(x, 0, z);
            scene.add(spot);
            scene.add(spot.target);
            ceilingLights.push(spot);
        });
    }

    function buildWindowUnit(cx, bottom, top) {
        const w = 1.85;
        const h = top - bottom;
        const cy = (bottom + top) / 2;
        const fw = 0.055;
        const frameMat = new THREE.MeshStandardMaterial({ color: 0xe8eaef, roughness: 0.32, metalness: 0.72 });
        const zGlass = -ROOM.hd + 0.03;
        const zSky = -ROOM.hd - 0.45;

        if (global.StudioTextures) {
            const sky = new THREE.Mesh(
                new THREE.PlaneGeometry(w - 0.12, h - 0.12),
                new THREE.MeshBasicMaterial({ map: StudioTextures.get('sky') })
            );
            sky.position.set(cx, cy, zSky);
            scene.add(sky);
        }

        const glassMat = new THREE.MeshStandardMaterial({
            color: 0x9cb8d8,
            transparent: true,
            opacity: 0.32,
            roughness: 0.04,
            metalness: 0.25,
            side: THREE.DoubleSide,
        });
        const paneW = (w - 0.16) / 2;
        const paneH = (h - 0.16) / 2;
        [[-0.5, -0.5], [0.5, -0.5], [-0.5, 0.5], [0.5, 0.5]].forEach(([gx, gy]) => {
            const pane = new THREE.Mesh(new THREE.PlaneGeometry(paneW - 0.02, paneH - 0.02), glassMat);
            pane.position.set(cx + gx * (paneW + 0.02), cy + gy * (paneH + 0.02), zGlass);
            scene.add(pane);
        });

        const addFrame = (fx, fy, fz, ww, hh, fd) => {
            const f = new THREE.Mesh(new THREE.BoxGeometry(ww, hh, fd), frameMat);
            f.position.set(fx, fy, fz);
            f.castShadow = true;
            scene.add(f);
        };
        const fz = -ROOM.hd + 0.07;
        addFrame(cx, top - fw / 2, fz, w + fw * 2, fw, 0.12);
        addFrame(cx, bottom + fw / 2, fz, w + fw * 2, fw, 0.12);
        addFrame(cx - w / 2 - fw / 2, cy, fz, fw, h, 0.12);
        addFrame(cx + w / 2 + fw / 2, cy, fz, fw, h, 0.12);
        addFrame(cx, cy, fz, 0.035, h - 0.08, 0.1);
        addFrame(cx, cy, fz, w - 0.08, 0.035, 0.1);

        const sillMat = global.StudioTextures
            ? StudioTextures.material('concrete', { roughness: 0.55 })
            : new THREE.MeshStandardMaterial({ color: 0x454a54, roughness: 0.45 });
        const sill = new THREE.Mesh(new THREE.BoxGeometry(w + 0.22, 0.07, 0.24), sillMat);
        sill.position.set(cx, bottom - 0.035, -ROOM.hd + 0.2);
        sill.castShadow = true;
        scene.add(sill);
    }

    function buildNorthWallWithWindows() {
        const wallMat = wallMaterial();
        const z = -ROOM.hd + 0.08;
        const t = 0.16;
        const h = ROOM.h;
        const winBot = 0.9;
        const winTop = 2.35;
        const spanL = -5.275;
        const spanR = 5.275;
        const spanW = spanR - spanL;
        const midX = (spanL + spanR) / 2;

        addWallBox(midX, winBot / 2, z, spanW, winBot, t, wallMat);
        addWallBox(midX, winTop + (h - winTop) / 2, z, spanW, h - winTop, t, wallMat);
        addWallBox(-ROOM.hw + (ROOM.hw + spanL) / 2, h / 2, z, ROOM.hw + spanL, h, t, wallMat);
        addWallBox(ROOM.hw - (ROOM.hw - spanR) / 2, h / 2, z, ROOM.hw - spanR, h, t, wallMat);

        [[-3.425, -2.375], [-0.525, 0.525], [2.375, 3.425]].forEach(([l, r]) => {
            addWallBox((l + r) / 2, (winBot + winTop) / 2, z, r - l, winTop - winBot, t, wallMat);
        });

        [-4.35, -1.45, 1.45, 4.35].forEach((cx) => buildWindowUnit(cx, winBot, winTop));
    }

    function buildOfficeDecor() {
        const board = addProp(new THREE.Mesh(
            new THREE.BoxGeometry(2.4, 1.1, 0.04),
            new THREE.MeshStandardMaterial({ color: 0xf2f2ee, roughness: 0.88 })
        ), false, true);
        board.position.set(-ROOM.hw + 0.2, 1.45, -0.5);
        board.rotation.y = Math.PI / 2;
        const boardFrame = new THREE.Mesh(
            new THREE.BoxGeometry(2.55, 1.22, 0.03),
            new THREE.MeshStandardMaterial({ color: 0x3a4048, metalness: 0.25, roughness: 0.5 })
        );
        boardFrame.position.set(-ROOM.hw + 0.16, 1.45, -0.5);
        boardFrame.rotation.y = Math.PI / 2;
        scene.add(boardFrame);

        const credenzaMat = global.StudioTextures
            ? StudioTextures.material('wood', { roughness: 0.58 })
            : new THREE.MeshStandardMaterial({ color: 0x4a4038, roughness: 0.55 });
        const credenza = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.75, 0.45), credenzaMat);
        credenza.position.set(-5.8, 0.375, -3.8);
        credenza.castShadow = true;
        credenza.receiveShadow = true;
        scene.add(credenza);
    }

    function buildPartitions() {
        const glassMat = new THREE.MeshStandardMaterial({
            color: 0x8899aa,
            transparent: true,
            opacity: 0.12,
            roughness: 0.08,
            metalness: 0.2,
            side: THREE.DoubleSide,
        });
        const frameMat = new THREE.MeshStandardMaterial({ color: 0x505660, metalness: 0.45, roughness: 0.4 });
        [[2.35, 0, 0.06, 4.8], [-2.8, 3.2, 3.6, 0.06]].forEach(([x, z, w, d]) => {
            const part = new THREE.Mesh(new THREE.BoxGeometry(w, 1.35, d), glassMat);
            part.position.set(x, 0.72, z);
            scene.add(part);
            const topRail = new THREE.Mesh(new THREE.BoxGeometry(w + 0.06, 0.04, d + 0.06), frameMat);
            topRail.position.set(x, 1.42, z);
            scene.add(topRail);
        });
    }

    function addAmbientParticles() {
        const count = 35;
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * ROOM.w * 0.9;
            positions[i * 3 + 1] = 0.8 + Math.random() * (ROOM.h - 0.5);
            positions[i * 3 + 2] = (Math.random() - 0.5) * ROOM.d * 0.9;
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const mat = new THREE.PointsMaterial({
            color: 0x99aabb, size: 0.04, transparent: true, opacity: 0.22,
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
                roughness: 0.88,
                emissive: accent || 0x000000,
                emissiveIntensity: accent ? 0.04 : 0,
            })
        );
        mesh.rotation.x = -Math.PI / 2;
        mesh.position.set(x, 0.025, z);
        scene.add(mesh);
    }

    function addZoneSign(text, x, z, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 40;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0,0,0,0.35)';
        ctx.fillRect(0, 0, 256, 40);
        ctx.fillStyle = `#${color.toString(16).padStart(6, '0')}`;
        ctx.font = '600 18px Segoe UI, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, 128, 20);

        const tex = new THREE.CanvasTexture(canvas);
        const plane = new THREE.Mesh(
            new THREE.PlaneGeometry(2.2, 0.38),
            new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide })
        );
        plane.position.set(x, 1.05, z);
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
        const wallMat = wallMaterial();
        const trimMat = new THREE.MeshStandardMaterial({ color: 0x454a54, roughness: 0.7 });
        const { hw, hd, h, w, d } = ROOM;

        buildNorthWallWithWindows();

        [[0, h / 2, hd, w, h, 0.16],
         [-hw, h / 2, 0, 0.16, h, d], [hw, h / 2, 0, 0.16, h, d]].forEach(([x, y, z, ww, hh, dd]) => {
            addWallBox(x, y, z, ww, hh, dd, wallMat);
        });

        const baseboardMat = new THREE.MeshStandardMaterial({ color: 0x252830 });
        [[0, 0.06, -hd + 0.1, w - 0.2, 0.1, 0.08], [0, 0.06, hd - 0.1, w - 0.2, 0.1, 0.08]].forEach(([x, y, z, ww, hh, dd]) => {
            addProp(new THREE.Mesh(new THREE.BoxGeometry(ww, hh, dd), baseboardMat), false, true).position.set(x, y, z);
        });
        addProp(new THREE.Mesh(new THREE.BoxGeometry(w, 0.06, d), trimMat), false, true).position.set(0, 0.03, 0);
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
            mesh.userData.faceAngle = Math.atan2(5.2 - slot.x, 1.8 - slot.z);
        } else if (inLib) {
            mesh.userData.baseY = 0;
            mesh.userData.faceAngle = Math.atan2(-5.2 - slot.x, 3.2 - slot.z);
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
        ambientLight = new THREE.AmbientLight(0xa0a8b8, 0.45);
        scene.add(ambientLight);

        hemiLight = new THREE.HemisphereLight(0xd8e4f0, 0x3a4048, 0.5);
        scene.add(hemiLight);

        sunLight = new THREE.DirectionalLight(0xfff6ea, 0.8);
        sunLight.position.set(1, 14, -6);
        sunLight.castShadow = true;
        sunLight.shadow.mapSize.set(2048, 2048);
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 28;
        sunLight.shadow.camera.left = -9;
        sunLight.shadow.camera.right = 9;
        sunLight.shadow.camera.top = 9;
        sunLight.shadow.camera.bottom = -9;
        sunLight.shadow.bias = -0.0002;
        scene.add(sunLight);

        windowLight = new THREE.DirectionalLight(0xb8d8f0, 0.7);
        windowLight.position.set(0, 5, -14);
        scene.add(windowLight);

        fillLight = new THREE.DirectionalLight(0x8899aa, 0.3);
        fillLight.position.set(-8, 10, 8);
        scene.add(fillLight);

        restLightPt = new THREE.PointLight(0xffe8c8, 0.25, 0, 1);
        restLightPt.position.set(5.2, 2.2, 3.2);
        scene.add(restLightPt);

        libLightPt = new THREE.PointLight(0xffe0b0, 0.22, 0, 1);
        libLightPt.position.set(-4.5, 2.2, 3.5);
        scene.add(libLightPt);
    }

    function applyLightingPreset(isDay) {
        isDaytime = isDay;
        if (ambientLight) ambientLight.intensity = isDay ? 0.45 : 0.3;
        if (hemiLight) {
            hemiLight.intensity = isDay ? 0.5 : 0.32;
            hemiLight.color.setHex(0xd8e4f0);
            hemiLight.groundColor.setHex(isDay ? 0x3a4048 : 0x1a1e26);
        }
        if (sunLight) {
            sunLight.intensity = isDay ? 0.8 : 0.1;
            sunLight.color.setHex(isDay ? 0xfff6ea : 0x8090a8);
        }
        if (windowLight) {
            windowLight.intensity = isDay ? 0.7 : 0.06;
            windowLight.color.setHex(isDay ? 0xb8d8f0 : 0x446688);
        }
        if (fillLight) fillLight.intensity = isDay ? 0.3 : 0.18;
        if (restLightPt) restLightPt.intensity = isDay ? 0.22 : 0.38;
        if (libLightPt) libLightPt.intensity = isDay ? 0.2 : 0.34;
        ceilingLights.forEach((l) => {
            l.intensity = isDay ? 0.55 : 0.78;
        });
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

    function init(canvas, clickCallback, options) {
        options = options || {};
        if (options.uiIds) uiIds = { ...uiIds, ...options.uiIds };
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
            const loadEl = document.querySelector(`#${uiIds.loading} span`);
            if (loadEl) loadEl.textContent = 'Загрузка офиса…';
            canvasEl = canvas;
            onAgentClick = clickCallback;
            clock = new THREE.Clock();

            scene = new THREE.Scene();
            setTheme(isDark);

            camera = new THREE.PerspectiveCamera(48, width / height, 0.1, 80);
            camera.position.set(0, 7.5, 9.5);
            camera.lookAt(0, 0.5, 0);

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
                controls.minDistance = 3.5;
                controls.maxDistance = 16;
                controls.target.set(0, 0.5, 0);
                if (options.autoOrbit) {
                    controls.autoRotate = true;
                    controls.autoRotateSpeed = 0.45;
                }
            } else {
                console.warn('[Studio] OrbitControls недоступен — fallback-управление');
                controls = createFallbackControls(camera, canvas);
            }

            setupLights();
            raycaster = new THREE.Raycaster();
            mouse = new THREE.Vector2();

            buildRoom();
            applyLightingPreset(global.AutoTheme ? AutoTheme.hourTheme() === 'light' : isDaytime);

            const spawnAgents = () => {
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
            };

            const finishInit = () => {
                if (global.StudioModels?.isReady?.()) {
                    StudioModels.spawnOffice(scene, STUDIO_SLOTS);
                }
                spawnAgents();
                applyLightingPreset(global.AutoTheme ? AutoTheme.hourTheme() === 'light' : isDaytime);
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
            };

            if (global.StudioModels) {
                StudioModels.loadAll()
                    .then((info) => console.log('[Studio] CC0 models loaded', info))
                    .catch((e) => console.warn('[Studio] models fallback', e))
                    .finally(finishInit);
            } else {
                finishInit();
            }
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
            tz: mesh.position.z + 2.8,
            ty: 5.5,
            cx: mesh.position.x,
            cz: mesh.position.z,
        };
        flyProgress = 0;
    }

    function flyCameraIntro() {
        if (!camera || !controls) return;
        camera.position.set(0, 14, 18);
        controls.target.set(0, 0.5, 0);
        flyTarget = { tx: 0, ty: 7.5, tz: 9.5, cx: 0, cz: 0 };
        flyProgress = 0.02;
    }

    function setAutoOrbit(on) {
        if (controls) {
            controls.autoRotate = !!on;
            controls.autoRotateSpeed = 0.45;
        }
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
        pipelineHighlightId = agentId || null;
        Object.entries(agentMeshes).forEach(([id, mesh]) => {
            const active = agentId && id === agentId;
            const s = active ? 1.12 : 1;
            mesh.scale.set(s, s, s);
            const glow = mesh.getObjectByName('glow');
            if (glow?.material) {
                glow.visible = !!active;
                if (active) glow.material.opacity = 0.65;
            }
        });
    }

    function setTheme(dark) {
        isDark = dark;
        if (!scene) return;
        const bg = dark ? 0x12141a : 0xd4dae6;
        const fogColor = dark ? 0x161a22 : 0xe0e5ef;
        scene.background = new THREE.Color(bg);
        if (scene.fog) {
            scene.fog.color.setHex(fogColor);
            scene.fog.near = 12;
            scene.fog.far = 38;
        } else {
            scene.fog = new THREE.Fog(fogColor, 12, 38);
        }
        if (renderer) renderer.setClearColor(bg, 1);
    }

    function setDayNight(isDay) {
        applyLightingPreset(isDay);
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
        showSpeechBubble, burstConfetti, flyToAgent, flyCameraIntro, setAutoOrbit, setDayNight, pulseScreen,
        isReady: () => initialized,
    };
})(window);
