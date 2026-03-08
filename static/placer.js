import * as THREE from '/static/vendor/three/three.module.js';
import { OrbitControls } from '/static/vendor/three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from '/static/vendor/three/examples/jsm/loaders/STLLoader.js';
import { TransformControls } from '/static/vendor/three/examples/jsm/controls/TransformControls.js';

export default class SlicerUI {
    constructor(container, config = {}) {
        this.materialProfiles = {
            pla: { label: "PLA", normal: 0xfacc15, overhang: 0xef4444 },
            petg: { label: "PETG", normal: 0x38bdf8, overhang: 0xf97316 },
            abs: { label: "ABS", normal: 0xa3e635, overhang: 0xfb7185 },
            tpu: { label: "TPU", normal: 0x22d3ee, overhang: 0xe11d48 }
        };
        const materialKey = config.projectMaterial || "pla";
        this.currentMaterial = this.materialProfiles[materialKey] ? materialKey : "pla";

        this.container = container;
        this.config = {
            plateSize: config.plateSize || 220,
            buildHeight: config.buildHeight || 250,
            padding: config.padding || 50,
            overhangAngle: config.overhangAngle || 50
        };

        this.models = new Map();
        this.plates = [];
        this.plateGroups = [];
        this.textLabels = [];
        this.activePlateIndex = 0;
        this.toolMode = 'transform';
        this.pendingTextPlacement = null;
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

    _getMaterialProfile() {
        return this.materialProfiles[this.currentMaterial] || this.materialProfiles.pla;
    }

    getProjectMaterial() {
        return this.currentMaterial;
    }

    setProjectMaterial(materialKey) {
        if (!this.materialProfiles[materialKey]) return;
        this.currentMaterial = materialKey;
        this.models.forEach(mesh => this._recolorMesh(mesh));
        this._recolorTextLabels();
        this.validate();
        this._notifyStateChanged();
    }

    setToolMode(mode) {
        if (!['transform', 'supportPaint', 'supportErase', 'textPlace'].includes(mode)) return;
        this.toolMode = mode;
        if (this.toolMode !== 'transform' && this.transform) {
            this.transform.detach();
        }
    }

    _applyOverhangColors(geometry, supportFaceSet = new Set()) {
        let geo = geometry;
        if (geo.index) {
            geo = geo.toNonIndexed();
        }

        geo.computeVertexNormals();

        const positions = geo.attributes.position.array;
        const triCount = positions.length / 9;
        const colors = new Float32Array((positions.length / 3) * 3);

        const profile = this._getMaterialProfile();
        const normalColor = new THREE.Color(profile.normal);
        const overhangColor = new THREE.Color(profile.overhang);
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

            const isOverhang = faceNormal.y < thresholdDot || supportFaceSet.has(i);
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
        mesh.userData.supportFaces = [];

        colorizedGeometry.computeBoundingBox();
        const center = new THREE.Vector3();
        colorizedGeometry.boundingBox.getCenter(center);
        colorizedGeometry.translate(-center.x, -colorizedGeometry.boundingBox.min.y, -center.z);
        return mesh;
    }

    _recolorMesh(mesh) {
        if (!mesh || !mesh.geometry) return;
        const supportFaces = new Set(Array.isArray(mesh.userData.supportFaces) ? mesh.userData.supportFaces : []);
        const recolored = this._applyOverhangColors(mesh.geometry, supportFaces);
        mesh.geometry = recolored;
    }

    _paintSupportFace(intersection, erase = false) {
        if (!intersection || !intersection.object || !this.models.has(intersection.object.uuid)) return;
        const mesh = intersection.object;
        const faceIndex = intersection.faceIndex;
        if (faceIndex === undefined || faceIndex === null) return;
        const set = new Set(Array.isArray(mesh.userData.supportFaces) ? mesh.userData.supportFaces : []);
        if (erase) {
            set.delete(faceIndex);
        } else {
            set.add(faceIndex);
        }
        mesh.userData.supportFaces = Array.from(set);
        this._recolorMesh(mesh);
        this._notifyStateChanged();
    }

    _createTextSprite(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 320;
        canvas.height = 96;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 60px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, canvas.width / 2, canvas.height / 2);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const step = 4;
        const cols = Math.floor(canvas.width / step);
        const rows = Math.floor(canvas.height / step);
        const points = [];

        for (let y = 0; y < rows; y += 1) {
            for (let x = 0; x < cols; x += 1) {
                const px = x * step;
                const py = y * step;
                const idx = ((py * canvas.width) + px) * 4;
                const alpha = imageData[idx + 3];
                if (alpha > 40) {
                    points.push({ x, y });
                }
            }
        }

        if (points.length === 0) {
            points.push({ x: Math.floor(cols / 2), y: Math.floor(rows / 2) });
        }

        const voxel = 0.9;
        const depth = 2.2;
        const geometry = new THREE.BoxGeometry(voxel, voxel, depth);
        const color = this._getMaterialProfile().normal;
        const material = new THREE.MeshStandardMaterial({ color });
        const mesh = new THREE.InstancedMesh(geometry, material, points.length);
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);

        const centerX = (cols - 1) / 2;
        const centerY = (rows - 1) / 2;
        const matrix = new THREE.Matrix4();

        points.forEach((p, i) => {
            const px = (p.x - centerX) * voxel;
            const py = (centerY - p.y) * voxel;
            matrix.makeTranslation(px, py, 0);
            mesh.setMatrixAt(i, matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;

        mesh.userData.isText = true;
        mesh.userData.text = text;
        mesh.userData.is3DText = true;
        mesh.userData.mode = "emboss";
        return mesh;
    }

    _recolorTextLabels() {
        const color = this._getMaterialProfile().normal;
        this.textLabels.forEach(label => {
            if (label.material && label.material.color) {
                label.material.color.setHex(color);
                label.material.needsUpdate = true;
            }
        });
    }

    _displayNameForObject(obj) {
        if (obj?.userData?.isText) {
            return `Text: ${obj.userData.text || "Label"}`;
        }
        return obj?.name || "Model";
    }

    addTextLabel(text) {
        if (!text || !text.trim()) return;
        const sprite = this._createTextSprite(text.trim());
        const x = this.plates[this.activePlateIndex]?.xOffset || 0;
        sprite.position.set(x, 12, 0);
        sprite.scale.set(1.6, 1.6, 1.6);
        this.scene.add(sprite);
        this.textLabels.push(sprite);
        this._attachTransformToObject(sprite);
        this._notifyStateChanged();
    }

    startTextPlacement(text, mode = "emboss") {
        if (!text || !text.trim()) return;
        this.pendingTextPlacement = { text: text.trim(), mode: mode === "deboss" ? "deboss" : "emboss" };
        this.setToolMode('textPlace');
    }

    _placeTextOnIntersection(intersection) {
        if (!this.pendingTextPlacement || !intersection || !intersection.object) return;
        const { text, mode } = this.pendingTextPlacement;
        const mesh = this._createTextSprite(text);
        mesh.userData.mode = mode;
        mesh.scale.set(1.35, 1.35, 1.35);

        const normal = intersection.face?.normal ? intersection.face.normal.clone() : new THREE.Vector3(0, 1, 0);
        normal.transformDirection(intersection.object.matrixWorld).normalize();
        const offset = mode === "deboss" ? -0.55 : 0.85;

        mesh.position.copy(intersection.point).add(normal.clone().multiplyScalar(offset));
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);

        this.scene.add(mesh);
        this.textLabels.push(mesh);
        this._attachTransformToObject(mesh);
        this.pendingTextPlacement = null;
        this.setToolMode('transform');
        this.validate();
        this._notifyStateChanged();
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
        this.setToolMode('transform');
        this.transform.setMode(mode);
    }

    _attachTransformToObject(obj) {
        if (!this.transform || !obj) return;
        this.transform.attach(obj);
        const bounds = new THREE.Box3().setFromObject(obj);
        const size = new THREE.Vector3();
        bounds.getSize(size);
        const diag = size.length();
        const gizmoSize = Math.min(1.2, Math.max(0.18, diag / 90));
        this.transform.setSize(gizmoSize);
    }

    removeSelectedModel() {
        const selected = this.transform ? this.transform.object : null;
        if (!selected) return;
        this.scene.remove(selected);
        if (this.models.has(selected.uuid)) {
            this.models.delete(selected.uuid);
        } else {
            this.textLabels = this.textLabels.filter(label => label !== selected);
        }
        this.transform.detach();
        this.validate();
        this._notifyStateChanged();
    }

    clearModels() {
        this.models.forEach(m => this.scene.remove(m));
        this.models.clear();
        this.textLabels.forEach(label => this.scene.remove(label));
        this.textLabels = [];
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
                scale: { x: mesh.scale.x, y: mesh.scale.y, z: mesh.scale.z },
                supportFaces: Array.isArray(mesh.userData.supportFaces) ? mesh.userData.supportFaces : []
            });
        });
        const texts = this.textLabels.map(label => ({
            text: label.userData.text || '',
            mode: label.userData.mode || "emboss",
            position: { x: label.position.x, y: label.position.y, z: label.position.z },
            rotation: { x: label.rotation.x, y: label.rotation.y, z: label.rotation.z },
            scale: { x: label.scale.x, y: label.scale.y, z: label.scale.z }
        }));
        return {
            models: state,
            plateCount: this.plates.length,
            activePlateIndex: this.activePlateIndex,
            projectMaterial: this.currentMaterial,
            texts
        };
    }

    async importState(projectState) {
        const legacyModels = Array.isArray(projectState) ? projectState : null;
        const modelsData = legacyModels || (projectState && Array.isArray(projectState.models) ? projectState.models : []);
        const plateCount = legacyModels ? 1 : Math.max(1, parseInt(projectState?.plateCount || 1, 10));
        const activePlateIndex = legacyModels ? 0 : Math.max(0, parseInt(projectState?.activePlateIndex || 0, 10));
        const projectMaterial = legacyModels ? this.currentMaterial : (projectState?.projectMaterial || this.currentMaterial);
        const texts = legacyModels ? [] : (Array.isArray(projectState?.texts) ? projectState.texts : []);

        // Clear existing
        this.models.forEach(m => this.scene.remove(m));
        this.models.clear();
        this.textLabels.forEach(label => this.scene.remove(label));
        this.textLabels = [];
        if (this.transform) this.transform.detach();
        this.resetPlates(plateCount);
        this.setProjectMaterial(projectMaterial);

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
                mesh.userData.supportFaces = Array.isArray(m.supportFaces) ? m.supportFaces : [];
                this._recolorMesh(mesh);

                this.scene.add(mesh);
                this.models.set(mesh.uuid, mesh);
            } catch (err) {
                console.error("Failed to load model during import:", m.name, err);
            }
        }

        for (const t of texts) {
            if (!t || !t.text) continue;
            const sprite = this._createTextSprite(t.text);
            sprite.userData.mode = t.mode || "emboss";
            sprite.position.set(t.position?.x || 0, t.position?.y || 12, t.position?.z || 0);
            sprite.rotation.set(t.rotation?.x || 0, t.rotation?.y || 0, t.rotation?.z || 0);
            sprite.scale.set(t.scale?.x || 1.6, t.scale?.y || 1.6, t.scale?.z || 1.6);
            this.scene.add(sprite);
            this.textLabels.push(sprite);
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
            this._attachTransformToObject(mesh);
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
        const modelIntersects = this.raycaster.intersectObjects(Array.from(this.models.values()), true);
        if (this.toolMode === 'supportPaint' || this.toolMode === 'supportErase') {
            if (modelIntersects.length > 0) {
                this._paintSupportFace(modelIntersects[0], this.toolMode === 'supportErase' || event.shiftKey);
                this.validate();
            }
            return;
        }

        if (this.toolMode === 'textPlace') {
            if (modelIntersects.length > 0) {
                this._placeTextOnIntersection(modelIntersects[0]);
            }
            return;
        }

        const selectable = [...Array.from(this.models.values()), ...this.textLabels];
        const intersects = this.raycaster.intersectObjects(selectable, true);

        if (intersects.length > 0) {
            this._attachTransformToObject(intersects[0].object);
            this.validate();
        }
    }

    validate() {
        const modelList = Array.from(this.models.values());
        const textList = Array.from(this.textLabels);
        const allObjects = [...modelList, ...textList];
        const offPlate = new Set();
        const colliding = new Set();
        allObjects.forEach(obj => {
            const box = new THREE.Box3().setFromObject(obj);
            const isOnPlate = this.plates.some(p => p.bounds.containsBox(box));
            const isColliding = allObjects.some(other => (other.uuid !== obj.uuid && box.intersectsBox(new THREE.Box3().setFromObject(other))));

            const displayName = this._displayNameForObject(obj);
            if (!isOnPlate) offPlate.add(displayName);
            if (isColliding) colliding.add(displayName);

            if (obj?.userData?.isText && obj.material?.color) {
                const color = (!isOnPlate || isColliding)
                    ? this._getMaterialProfile().overhang
                    : this._getMaterialProfile().normal;
                obj.material.color.setHex(color);
                obj.material.needsUpdate = true;
            }
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
