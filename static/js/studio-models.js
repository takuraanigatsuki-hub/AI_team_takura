/**
 * Загрузка CC0-моделей для 3D-студии
 * Kenney Furniture Kit · Kenney Blocky Characters · Three.js Soldier (MIT)
 */
(function (global) {
    const OBJ_FURNITURE = '/static/models/kenney_furniture/Models/OBJ%20format/';
    const OBJ_CHARS = '/static/models/kenney_characters/Models/OBJ%20format/';
    const GLTF_SOLDIER = '/static/models/office/Soldier.glb';

    const FURNITURE_KEYS = [
        'desk', 'chairDesk', 'computerScreen', 'computerKeyboard', 'computerMouse',
        'loungeSofa', 'loungeSofaLong', 'lampSquareFloor', 'lampSquareTable',
        'bookcaseClosedWide', 'bookcaseOpen', 'pottedPlant', 'plantSmall1',
        'tableRound', 'televisionModern', 'sideTable',
    ];

    const prototypes = {};
    let soldierTemplate = null;
    let soldierClips = [];
    let agentMixers = {};
    let ready = false;

    function enc(path) {
        return path.replace(/ /g, '%20');
    }

    function prepMesh(root) {
        root.traverse((c) => {
            if (c.isMesh) {
                c.castShadow = true;
                c.receiveShadow = true;
            }
        });
        return root;
    }

    function loadOBJ(base, name) {
        return new Promise((resolve, reject) => {
            if (typeof THREE.OBJLoader === 'undefined') {
                reject(new Error('OBJLoader missing'));
                return;
            }
            const objLoader = new THREE.OBJLoader();
            const mtlLoader = new THREE.MTLLoader();
            mtlLoader.setPath(base);
            const mtlFile = `${name}.mtl`;
            const objFile = `${name}.obj`;

            mtlLoader.load(mtlFile, (materials) => {
                materials.preload();
                objLoader.setMaterials(materials);
                objLoader.setPath(base);
                objLoader.load(objFile, (obj) => resolve(prepMesh(obj)), undefined, reject);
            }, undefined, () => {
                objLoader.setPath(base);
                objLoader.load(objFile, (obj) => resolve(prepMesh(obj)), undefined, reject);
            });
        });
    }

    function loadGLTF(url) {
        return new Promise((resolve, reject) => {
            if (typeof THREE.GLTFLoader === 'undefined') {
                reject(new Error('GLTFLoader missing'));
                return;
            }
            new THREE.GLTFLoader().load(url, resolve, undefined, reject);
        });
    }

    function cloneProp(name, x, y, z, rotY, scale) {
        const src = prototypes[name];
        if (!src) return null;
        const g = src.clone(true);
        g.position.set(x, y, z);
        if (rotY) g.rotation.y = rotY;
        const s = scale || 1;
        g.scale.set(s, s, s);
        return g;
    }

    function pickClip(candidates) {
        for (const c of candidates) {
            const f = soldierClips.find((a) => a.name.toLowerCase() === c.toLowerCase());
            if (f) return f;
        }
        return soldierClips[0] || null;
    }

    const STATUS_CLIPS = {
        idle: ['Idle', 'Stand', 'Standing'],
        working: ['Run', 'Walk', 'Walking'],
        thinking: ['Idle', 'Stand'],
        learning: ['Idle', 'Walk'],
        resting: ['Idle', 'Sit', 'Sitting'],
    };

    function playAnim(agentId, status) {
        const entry = agentMixers[agentId];
        if (!entry) return;
        const clip = pickClip(STATUS_CLIPS[status] || STATUS_CLIPS.idle);
        if (!clip) return;
        const next = entry.mixer.clipAction(clip);
        if (entry.current === next) return;
        if (entry.current) entry.current.fadeOut(0.25);
        next.reset().fadeIn(0.25).play();
        entry.current = next;
    }

    async function loadAll() {
        const tasks = FURNITURE_KEYS.map(async (key) => {
            try {
                prototypes[key] = await loadOBJ(OBJ_FURNITURE, key);
            } catch (e) {
                console.warn('[StudioModels] furniture', key, e.message);
            }
        });
        await Promise.all(tasks);

        try {
            const gltf = await loadGLTF(GLTF_SOLDIER);
            soldierTemplate = gltf.scene;
            soldierClips = gltf.animations || [];
            soldierTemplate.traverse((c) => {
                if (c.isMesh) {
                    c.castShadow = true;
                    c.receiveShadow = true;
                }
            });
        } catch (e) {
            console.warn('[StudioModels] Soldier GLB', e.message);
        }

        ready = true;
        return { furniture: Object.keys(prototypes).length, soldier: !!soldierTemplate };
    }

    function spawnOffice(scene, slots) {
        if (!ready) return;
        const root = new THREE.Group();
        root.name = 'officeProps';

        Object.values(slots).forEach(({ x, z }) => {
            const desk = cloneProp('desk', x, 0, z + 0.35, 0, 0.01);
            if (desk) root.add(desk);
            const chair = cloneProp('chairDesk', x, 0, z - 0.15, Math.PI, 0.01);
            if (chair) root.add(chair);
            const screen = cloneProp('computerScreen', x, 0.78, z + 0.55, 0, 0.012);
            if (screen) root.add(screen);
            const kb = cloneProp('computerKeyboard', x, 0.76, z + 0.42, 0, 0.015);
            if (kb) root.add(kb);
            const mouse = cloneProp('computerMouse', x + 0.25, 0.76, z + 0.42, -0.4, 0.015);
            if (mouse) root.add(mouse);
        });

        [[9, 5], [11, 5], [13, 5]].forEach(([x, z]) => {
            const sofa = cloneProp('loungeSofa', x, 0, z, 0, 0.01);
            if (sofa) root.add(sofa);
        });
        const sofaL = cloneProp('loungeSofaLong', 11, 0, 8, Math.PI / 2, 0.01);
        if (sofaL) root.add(sofaL);
        const tv = cloneProp('televisionModern', 11, 0.4, 3.2, Math.PI, 0.012);
        if (tv) root.add(tv);

        [[-11.5, 8], [-10.2, 10], [-9, 12]].forEach(([x, z], i) => {
            const shelf = cloneProp(i % 2 ? 'bookcaseOpen' : 'bookcaseClosedWide', x, 0, z, Math.PI / 2, 0.01);
            if (shelf) root.add(shelf);
        });
        const libTable = cloneProp('tableRound', -8, 0, 12, 0, 0.012);
        if (libTable) root.add(libTable);
        const libLamp = cloneProp('lampSquareTable', -8, 0.72, 12, 0, 0.012);
        if (libLamp) root.add(libLamp);

        [[-8, -6], [6, -5], [14, 2], [-14, 4], [0, 6]].forEach(([x, z], i) => {
            const plant = cloneProp(i % 2 ? 'pottedPlant' : 'plantSmall1', x, 0, z, Math.random() * 0.5, 0.012);
            if (plant) root.add(plant);
        });
        [[-2, 6], [11, 7], [-10, 9]].forEach(([x, z]) => {
            const lamp = cloneProp('lampSquareFloor', x, 0, z, 0, 0.012);
            if (lamp) root.add(lamp);
        });
        const meet = cloneProp('tableRound', 0, 0, 6, 0, 0.014);
        if (meet) root.add(meet);

        scene.add(root);
    }

    function createAgent(id, emoji, color, emojiFactory) {
        if (soldierTemplate) {
            const group = new THREE.Group();
            group.userData.agentId = id;
            const model = soldierTemplate.clone(true);
            model.scale.set(0.011, 0.011, 0.011);
            model.position.y = 0;
            model.traverse((c) => {
                if (c.isMesh && c.material) {
                    c.material = c.material.clone();
                    if (c.material.emissive) {
                        c.material.emissive.setHex(color);
                        c.material.emissiveIntensity = 0.15;
                    }
                }
            });
            group.add(model);
            if (emojiFactory) group.add(emojiFactory(emoji));

            const mixer = new THREE.AnimationMixer(model);
            agentMixers[id] = { mixer, current: null };
            playAnim(id, 'idle');

            group.userData.baseY = 0;
            group.userData.phase = Math.random() * Math.PI * 2;
            group.userData.idlePhase = Math.random() * 100;
            group.userData.status = 'idle';
            group.userData.faceAngle = 0;
            group.userData.targetX = 0;
            group.userData.targetZ = 0;
            group.userData.useGltf = true;
            return group;
        }

        return null;
    }

    function updateMixers(delta) {
        Object.values(agentMixers).forEach((e) => e.mixer.update(delta));
    }

    function setAgentStatus(agentId, status) {
        playAnim(agentId, status || 'idle');
    }

    function isReady() {
        return ready && (!!soldierTemplate || Object.keys(prototypes).length > 3);
    }

    global.StudioModels = {
        loadAll,
        spawnOffice,
        createAgent,
        updateMixers,
        setAgentStatus,
        isReady,
        hasSoldier: () => !!soldierTemplate,
    };
})(window);
