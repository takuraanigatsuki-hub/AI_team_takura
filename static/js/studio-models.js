/**
 * CC0-мебель Kenney для 3D-студии (без SkinnedMesh — стабильно в Three.js r128)
 */
(function (global) {
    const OBJ_FURNITURE = '/static/models/kenney_furniture/Models/OBJ%20format/';

    const FURNITURE_KEYS = [
        'desk', 'chairDesk', 'computerScreen', 'computerKeyboard',
        'loungeSofa', 'loungeSofaLong', 'televisionModern',
        'bookcaseClosedWide', 'bookcaseOpen', 'pottedPlant', 'lampSquareFloor',
    ];

    const prototypes = {};
    let ready = false;

    function toStandardMat(mat) {
        if (!mat) {
            return new THREE.MeshStandardMaterial({ color: 0x888899, roughness: 0.65 });
        }
        if (mat.type === 'MeshStandardMaterial') return mat;
        return new THREE.MeshStandardMaterial({
            color: mat.color ? mat.color.clone() : new THREE.Color(0x888899),
            roughness: 0.62,
            metalness: mat.name && /metal/i.test(mat.name) ? 0.35 : 0.08,
        });
    }

    function fixMaterials(root) {
        root.traverse((c) => {
            if (!c.isMesh) return;
            if (Array.isArray(c.material)) {
                c.material = c.material.map(toStandardMat);
            } else {
                c.material = toStandardMat(c.material);
            }
        });
    }

    function prepMesh(root) {
        fixMaterials(root);
        root.traverse((c) => {
            if (c.isMesh) {
                c.castShadow = true;
                c.receiveShadow = true;
            }
        });
        return root;
    }

    function loadOBJ(name) {
        return new Promise((resolve, reject) => {
            if (typeof THREE.OBJLoader === 'undefined') {
                reject(new Error('OBJLoader missing'));
                return;
            }
            const objLoader = new THREE.OBJLoader();
            const mtlLoader = new THREE.MTLLoader();
            mtlLoader.setPath(OBJ_FURNITURE);
            mtlLoader.load(`${name}.mtl`, (materials) => {
                materials.preload();
                objLoader.setMaterials(materials);
                objLoader.setPath(OBJ_FURNITURE);
                objLoader.load(`${name}.obj`, (obj) => resolve(prepMesh(obj)), undefined, reject);
            }, undefined, () => {
                objLoader.setPath(OBJ_FURNITURE);
                objLoader.load(`${name}.obj`, (obj) => resolve(prepMesh(obj)), undefined, reject);
            });
        });
    }

    function cloneProp(name, x, y, z, rotY) {
        const src = prototypes[name];
        if (!src) return null;
        const g = src.clone(true);
        g.position.set(x, y, z);
        if (rotY) g.rotation.y = rotY;
        return g;
    }

    async function loadAll() {
        await Promise.all(FURNITURE_KEYS.map(async (key) => {
            try {
                prototypes[key] = await loadOBJ(key);
            } catch (e) {
                console.warn('[StudioModels]', key, e.message);
            }
        }));
        ready = Object.keys(prototypes).length >= 4;
        return { furniture: Object.keys(prototypes).length };
    }

    function spawnOffice(scene, slots) {
        if (!ready) return false;
        const root = new THREE.Group();
        root.name = 'officeProps';

        Object.values(slots).forEach(({ x, z }) => {
            const desk = cloneProp('desk', x, 0, z + 0.38, 0);
            if (desk) root.add(desk);
            const chair = cloneProp('chairDesk', x, 0, z - 0.05, Math.PI);
            if (chair) root.add(chair);
            const screen = cloneProp('computerScreen', x, 0.74, z + 0.62, 0);
            if (screen) root.add(screen);
            const kb = cloneProp('computerKeyboard', x, 0.72, z + 0.48, 0);
            if (kb) root.add(kb);
        });

        [[9, 5], [11, 5], [13, 5]].forEach(([x, z]) => {
            const sofa = cloneProp('loungeSofa', x, 0, z, 0);
            if (sofa) root.add(sofa);
        });
        const tv = cloneProp('televisionModern', 11, 0.35, 3.4, Math.PI);
        if (tv) root.add(tv);

        [[-11.2, 8.5], [-10, 11]].forEach(([x, z], i) => {
            const shelf = cloneProp(i ? 'bookcaseOpen' : 'bookcaseClosedWide', x, 0, z, Math.PI / 2);
            if (shelf) root.add(shelf);
        });

        [[-7, -5], [5, -4], [-13, 3]].forEach(([x, z]) => {
            const plant = cloneProp('pottedPlant', x, 0, z, Math.random() * 0.3);
            if (plant) root.add(plant);
        });

        scene.add(root);
        return true;
    }

    function isReady() {
        return ready;
    }

    global.StudioModels = {
        loadAll,
        spawnOffice,
        isReady,
        updateMixers() {},
        setAgentStatus() {},
        createAgent() { return null; },
        hasSoldier() { return false; },
    };
})(window);
