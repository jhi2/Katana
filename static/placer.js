import * as THREE from '/static/vendor/three/three.module.js';
import { OrbitControls } from '/static/vendor/three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from '/static/vendor/three/examples/jsm/loaders/STLLoader.js';
import { TransformControls } from '/static/vendor/three/examples/jsm/controls/TransformControls.js';

export default class SlicerUI {
    constructor(container, config = {}) {
        this.container = container;
        this.config = {
            plateSize: config.plateSize || 220,
            buildHeight: config.buildHeight || 250,
            padding: config.padding || 50,
            colors: { normal: 0xfacc15, overhang: 0xef4444 },
            overhangAngle: config.overhangAngle || 50
        };

        this.models = new Map();
        this.plates = [];
        this.plateGroups = [];
        this.activePlateIndex = 0;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.onStateChange = null;
        this.onValidationChange = null;
        this._stateChangeTimer = null;
        this._lastValidationState = "";

        this._init();
        this.addPlate(); // Create initial plate
        this._animate();
    }

    _applyOverhangColors(geometry) {
        let geo = geometry;
        if (geo.index) {
            geo = geo.toNonIndexed();
        }

        geo.computeVertexNormals();

        const positions = geo.attributes.position.array;
        const triCount = positions.length / 9;
        const colors = new Float32Array((positions.length / 3) * 3);

        const normalColor = new THREE.Color(this.config.colors.normal);
        const overhangColor = new THREE.Color(this.config.colors.overhang);
        const thresholdDot = -Math.sin((this.config.overhangAngle * Math.PI) / 180);

        const a = new THREE.Vector3();
        const b = new THREE.Vector3();
        const c = new THREE.Vector3();
        const ab = new THREE.Vector3();
        const ac = new THREE.Vector3();
        const faceNormal = new THREE.Vector3();

        for (let i = 0; i < triCount; i += 1) {
            const p = i * 9;
            a.set(positions[p], positions[p + 1], positions[p + 2]);
            b.set(positions[p + 3], positions[p + 4], positions[p + 5]);
            c.set(positions[p + 6], positions[p + 7], positions[p + 8]);

            ab.subVectors(b, a);
            ac.subVectors(c, a);
            faceNormal.crossVectors(ab, ac).normalize();

            const isOverhang = faceNormal.y < thresholdDot;
            const color = isOverhang ? overhangColor : normalColor;

            const base = i * 9;
            for (let j = 0; j < 3; j += 1) {
                const ci = base + (j * 3);
                colors[ci] = color.r;
                colors[ci + 1] = color.g;
                colors[ci + 2] = color.b;
            }
        }

        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        return geo;
    }

    _createPrintableMesh(geometry, name, url = "") {
        const colorizedGeometry = this._applyOverhangColors(geometry);
        const mesh = new THREE.Mesh(
            colorizedGeometry,
            new THREE.MeshStandardMaterial({ vertexColors: true })
        );
        mesh.uuid = THREE.MathUtils.generateUUID();
        mesh.name = name;
        mesh.userData.url = url;

        colorizedGeometry.computeBoundingBox();
        const center = new THREE.Vector3();
        colorizedGeometry.boundingBox.getCenter(center);
        colorizedGeometry.translate(-center.x, -colorizedGeometry.boundingBox.min.y, -center.z);
        return mesh;
    }

    _init() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0f0f0f);

        this.camera = new THREE.PerspectiveCamera(45, this.container.clientWidth / this.container.clientHeight, 1, 10000);
        this.camera.position.set(400, 400, 400);

        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            preserveDrawingBuffer: true
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        this.scene.add(new THREE.AmbientLight(0xffffff, 1.2));
        const sun = new THREE.DirectionalLight(0xffffff, 1.5);
        sun.position.set(500, 1000, 500);
        this.scene.add(sun);

        this.orbit = new OrbitControls(this.camera, this.renderer.domElement);
        this.orbit.enableDamping = true;

        this.transform = new TransformControls(this.camera, this.renderer.domElement);
        this.transform.addEventListener('dragging-changed', (e) => this.orbit.enabled = !e.value);
        this.transform.addEventListener('change', () => this.validate());
        this.transform.addEventListener('objectChange', () => this._notifyStateChanged());
        this.scene.add(this.transform);

        this.container.addEventListener('pointerdown', (e) => this._onPointerDown(e));
        window.addEventListener('resize', () => this.onResize());
    }

    // --- PLATE MANAGEMENT ---

    addPlate() {
        const index = this.plates.length;
        const xOffset = index * (this.config.plateSize + this.config.padding);
        const group = new THREE.Group();

        const grid = new THREE.GridHelper(this.config.plateSize, 20, 0x444444, 0x222222);
        group.add(grid);

        const cage = new THREE.LineSegments(
            new THREE.EdgesGeometry(new THREE.BoxGeometry(this.config.plateSize, this.config.buildHeight, this.config.plateSize)),
            new THREE.LineBasicMaterial({ color: 0x333333, transparent: true, opacity: 0.4 })
        );
        cage.position.y = this.config.buildHeight / 2;
        group.add(cage);
        group.position.x = xOffset;
        this.scene.add(group);
        this.plateGroups.push(group);

        const plate = {
            id: `plate_${index}`,
            bounds: new THREE.Box3().setFromCenterAndSize(
                new THREE.Vector3(xOffset, this.config.buildHeight / 2, 0),
                new THREE.Vector3(this.config.plateSize, this.config.buildHeight, this.config.plateSize)
            ),
            xOffset
        };
        this.plates.push(plate);
        this._notifyStateChanged();
        return index;
    }

    resetPlates(count = 1) {
        this.plateGroups.forEach(group => this.scene.remove(group));
        this.plateGroups = [];
        this.plates = [];
        this.activePlateIndex = 0;

        const plateCount = Math.max(1, Number.isInteger(count) ? count : 1);
        for (let i = 0; i < plateCount; i += 1) {
            this.addPlate();
        }
        this.focusPlate(0);
    }

    focusPlate(index) {
        if (!this.plates[index]) return;
        this.activePlateIndex = index;
        const plate = this.plates[index];
        this.orbit.target.set(plate.xOffset, 0, 0);
        this.orbit.update();
    }

    setTransformMode(mode) {
        if (!this.transform) return;
        if (!['translate', 'rotate', 'scale'].includes(mode)) return;
        this.transform.setMode(mode);
    }

    removeSelectedModel() {
        const selected = this.transform ? this.transform.object : null;
        if (!selected) return;
        this.scene.remove(selected);
        this.models.delete(selected.uuid);
        this.transform.detach();
        this.validate();
        this._notifyStateChanged();
    }

    clearModels() {
        this.models.forEach(m => this.scene.remove(m));
        this.models.clear();
        if (this.transform) this.transform.detach();
        this.validate();
        this._notifyStateChanged();
    }

    _notifyStateChanged() {
        if (typeof this.onStateChange !== 'function') return;
        if (this._stateChangeTimer) clearTimeout(this._stateChangeTimer);
        this._stateChangeTimer = setTimeout(() => {
            this.onStateChange();
        }, 250);
    }

    exportState() {
        const state = [];
        this.models.forEach((mesh, uuid) => {
            state.push({
                name: mesh.name,
                url: mesh.userData.url || '', // We need to store URL in userData when loading
                position: { x: mesh.position.x, y: mesh.position.y, z: mesh.position.z },
                rotation: { x: mesh.rotation.x, y: mesh.rotation.y, z: mesh.rotation.z },
                scale: { x: mesh.scale.x, y: mesh.scale.y, z: mesh.scale.z }
            });
        });
        return {
            models: state,
            plateCount: this.plates.length,
            activePlateIndex: this.activePlateIndex
        };
    }

    async importState(projectState) {
        const legacyModels = Array.isArray(projectState) ? projectState : null;
        const modelsData = legacyModels || (projectState && Array.isArray(projectState.models) ? projectState.models : []);
        const plateCount = legacyModels ? 1 : Math.max(1, parseInt(projectState?.plateCount || 1, 10));
        const activePlateIndex = legacyModels ? 0 : Math.max(0, parseInt(projectState?.activePlateIndex || 0, 10));

        // Clear existing
        this.models.forEach(m => this.scene.remove(m));
        this.models.clear();
        if (this.transform) this.transform.detach();
        this.resetPlates(plateCount);

        const loader = new STLLoader();
        for (const m of modelsData) {
            if (!m.url) continue;

            try {
                const geometry = await new Promise((resolve, reject) => {
                    loader.load(m.url, resolve, undefined, reject);
                });

                const mesh = this._createPrintableMesh(geometry, m.name, m.url);

                mesh.position.set(m.position.x, m.position.y, m.position.z);
                mesh.rotation.set(m.rotation.x, m.rotation.y, m.rotation.z);
                mesh.scale.set(m.scale.x, m.scale.y, m.scale.z);

                this.scene.add(mesh);
                this.models.set(mesh.uuid, mesh);
            } catch (err) {
                console.error("Failed to load model during import:", m.name, err);
            }
        }
        this.validate();
        this.focusPlate(Math.min(activePlateIndex, this.plates.length - 1));
        this._notifyStateChanged();
    }

    // --- REMOTE LOADING ---

    /**
     * Loads STL from a server URL
     * @param {string} url - The direct link to your STL file
     * @param {string} name - Internal name for the model
     */
    loadFromUrl(url, name = "RemoteModel") {
        const loader = new STLLoader();

        loader.load(url, (geometry) => {
            const mesh = this._createPrintableMesh(geometry, name, url);

            // Place on currently focused plate
            mesh.position.set(this.plates[this.activePlateIndex].xOffset, 0, 0);

            this.scene.add(mesh);
            this.models.set(mesh.uuid, mesh);
            this.transform.attach(mesh);
            this.validate();
            this._notifyStateChanged();
        },
            (xhr) => { console.log((xhr.loaded / xhr.total * 100) + '% loaded'); },
            (error) => { console.error('An error happened during download', error); });
    }

    // --- LOGIC ---

    _onPointerDown(event) {
        const rect = this.container.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(Array.from(this.models.values()), true);

        if (intersects.length > 0) {
            this.transform.attach(intersects[0].object);
            this.validate();
        }
    }

    validate() {
        const modelList = Array.from(this.models.values());
        const offPlate = new Set();
        const colliding = new Set();
        modelList.forEach(m => {
            const box = new THREE.Box3().setFromObject(m);
            const isOnPlate = this.plates.some(p => p.bounds.containsBox(box));
            const isColliding = modelList.some(other => (other.uuid !== m.uuid && box.intersectsBox(new THREE.Box3().setFromObject(other))));

            if (!isOnPlate) offPlate.add(m.name || "Model");
            if (isColliding) colliding.add(m.name || "Model");
        });

        if (typeof this.onValidationChange === 'function') {
            const stateKey = JSON.stringify({
                offPlate: Array.from(offPlate).sort(),
                colliding: Array.from(colliding).sort()
            });
            if (stateKey !== this._lastValidationState) {
                this._lastValidationState = stateKey;
                this.onValidationChange({
                    hasIssues: offPlate.size > 0 || colliding.size > 0,
                    offPlate: Array.from(offPlate),
                    colliding: Array.from(colliding)
                });
            }
        }
    }

    getScreenshot() {
        return this.renderer.domElement.toDataURL('image/png');
    }

    onResize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }

    _animate() {
        requestAnimationFrame(() => this._animate());
        this.orbit.update();
        this.renderer.render(this.scene, this.camera);
    }
}
