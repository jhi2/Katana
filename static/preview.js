import * as THREE from './vendor/three/three.module.js';
import { OrbitControls } from './vendor/three/examples/jsm/controls/OrbitControls.js';

/**
 * Local G-Code Previewer using Three.js r160.
 * Parses G-Code and renders extrusion / travel toolpaths.
 */
export default class PreviewUI {
    constructor(canvas, config = {}) {
        this.canvas = canvas;
        this.config = Object.assign({
            plateSize: 220,
            buildHeight: 250,
            extrusionColor: 0x00d1b2,
            travelColor: 0x222222,
            backgroundColor: 0x0a0a0a
        }, config);

        this.layers = [];
        this.maxLayerIndex = 0;
        this.currentLayerCount = 0;

        this._initThree();
    }

    _initThree() {
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(this.config.backgroundColor);

        // Camera
        const aspect = this.canvas.clientWidth / this.canvas.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 5000);
        this.camera.position.set(0, this.config.buildHeight * 0.6, this.config.plateSize * 1.5);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true });
        this.renderer.setPixelRatio(window.devicePixelRatio || 1);
        this.renderer.setSize(this.canvas.clientWidth, this.canvas.clientHeight, false);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.1;
        this.controls.target.set(0, this.config.buildHeight / 4, 0);

        // Grid & Build Volume
        this._buildPlatform();

        // Layer group
        this.layerGroup = new THREE.Group();
        this.scene.add(this.layerGroup);

        // Animation Loop
        this.animate = this.animate.bind(this);
        this.reqId = requestAnimationFrame(this.animate);
    }

    _buildPlatform() {
        const gridHelper = new THREE.GridHelper(this.config.plateSize, 20, 0x444444, 0x222222);
        gridHelper.position.y = 0;
        this.scene.add(gridHelper);

        // Optional transparent box for max volume
        const geo = new THREE.BoxGeometry(this.config.plateSize, this.config.buildHeight, this.config.plateSize);
        geo.translate(0, this.config.buildHeight / 2, 0);
        const mat = new THREE.MeshBasicMaterial({ color: 0x444444, wireframe: true, transparent: true, opacity: 0.1 });
        const box = new THREE.Mesh(geo, mat);
        this.scene.add(box);
    }

    animate() {
        this.reqId = requestAnimationFrame(this.animate);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    onResize() {
        if (!this.canvas) return;
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        if (width === 0 || height === 0) return;

        this.renderer.setSize(width, height, false);
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
    }

    clear() {
        // Delete all geometries in layer group
        while (this.layerGroup.children.length > 0) {
            const child = this.layerGroup.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
                else child.material.dispose();
            }
            this.layerGroup.remove(child);
        }
        this.layers = [];
        this.currentLayerCount = 0;
        this.maxLayerIndex = 0;
    }

    async processGCode(gcodeStr) {
        this.clear();
        console.log(`[PreviewUI] Parsing GCode (${gcodeStr.length} chars)`);

        const lines = gcodeStr.split('\n');

        // Parse State
        let x = 0, y = 0, z = 0, e = 0;
        let isRelative = false;
        let isRelativeE = false;
        let currentLayerIdx = 0;

        let currentLayer = { extrusions: [], travels: [], z: 0 };
        this.layers.push(currentLayer);

        // Helper to parse value from command like X10.5
        const p = (cmd, char) => {
            const idx = cmd.indexOf(char);
            if (idx === -1) return null;
            let end = cmd.indexOf(' ', idx);
            if (end === -1) end = cmd.length;
            const res = parseFloat(cmd.substring(idx + 1, end));
            return isNaN(res) ? null : res;
        };

        const centerPt = this.config.plateSize / 2;

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].split(';')[0].trim().toUpperCase();
            if (!line) continue;

            // Check commands
            if (line.startsWith('G90')) { isRelative = false; }
            else if (line.startsWith('G91')) { isRelative = true; }
            else if (line.startsWith('M82')) { isRelativeE = false; }
            else if (line.startsWith('M83')) { isRelativeE = true; }
            else if (line.startsWith('G0') || line.startsWith('G1')) {
                const nx = p(line, 'X');
                const ny = p(line, 'Y');
                const nz = p(line, 'Z');
                const ne = p(line, 'E');

                const prevX = x; const prevY = y; const prevZ = z; const prevE = e;

                if (nx !== null) x = isRelative ? x + nx : nx;
                if (ny !== null) y = isRelative ? y + ny : ny;
                if (nz !== null) z = isRelative ? z + nz : nz;
                if (ne !== null) e = isRelativeE ? e + ne : ne;

                // Center coordinates for display (assuming slicer outputs origin at 0,0 bottom left)
                // Katana/IceSL normally slice with origin in center for delta, or bottom left for cartesian
                // We'll trust the gcode absolute values and just apply a -plateSize/2 offset so 0,0 is center of the grid visually.
                let drawPrevX = prevX - centerPt;
                let drawPrevY = prevY - centerPt;
                let drawX = x - centerPt;
                let drawY = y - centerPt;

                // If Z changed (and we've actually printed something), start new layer
                if (z !== prevZ && currentLayer.extrusions.length > 0) {
                    currentLayerIdx++;
                    currentLayer = { extrusions: [], travels: [], z: z };
                    this.layers.push(currentLayer);
                }

                // Extruding vs Travel
                const isExtruding = ne !== null && e > prevE;

                // Only save line if it actually moved
                if (x !== prevX || y !== prevY || z !== prevZ) {
                    if (isExtruding) {
                        currentLayer.extrusions.push(drawPrevX, prevZ, -drawPrevY, drawX, z, -drawY); // Note: Threejs is Y-up, Gcode Z-up
                    } else {
                        currentLayer.travels.push(drawPrevX, prevZ, -drawPrevY, drawX, z, -drawY);
                    }
                }
            }
        }

        this.currentLayerCount = this.layers.length;
        console.log(`[PreviewUI] Finished parsing, building ${this.currentLayerCount} layers...`);
        this._buildGeometries();
    }

    _buildGeometries() {
        const extMat = new THREE.LineBasicMaterial({ color: this.config.extrusionColor, linewidth: 1 });
        const trvMat = new THREE.LineBasicMaterial({ color: this.config.travelColor, linewidth: 1 });

        for (let i = 0; i < this.layers.length; i++) {
            const layer = this.layers[i];
            const group = new THREE.Group();
            group.name = `layer_${i}`;

            if (layer.extrusions.length > 0) {
                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(layer.extrusions, 3));
                const line = new THREE.LineSegments(geo, extMat);
                group.add(line);
            }
            if (layer.travels.length > 0) {
                const geo = new THREE.BufferGeometry();
                geo.setAttribute('position', new THREE.Float32BufferAttribute(layer.travels, 3));
                const line = new THREE.LineSegments(geo, trvMat);
                group.add(line);
            }

            // Initially visible
            group.visible = true;
            this.layerGroup.add(group);
            layer.group = group;
        }

        this.maxLayerIndex = this.layers.length - 1;
    }

    getLayerCount() {
        return this.currentLayerCount;
    }

    setLayer(index) {
        if (!this.layers) return;
        if (index < 0) index = 0;
        if (index >= this.layers.length) index = this.layers.length - 1;

        for (let i = 0; i < this.layers.length; i++) {
            if (this.layers[i].group) {
                this.layers[i].group.visible = (i <= index);
            }
        }
        this.maxLayerIndex = index;
    }

    toggleTubes(show) {
        // Just a stub for compatibility with former tube toggle. Real 3D tubes are slow for big GCode.
        console.log("[PreviewUI] Tubes mode not available in local renderer");
    }

    render() {
        // Redraw is handled by requestAnimationFrame loop automatically
    }

    dispose() {
        cancelAnimationFrame(this.reqId);
        this.clear();
        if (this.renderer) {
            this.renderer.dispose();
            this.renderer.forceContextLoss();
        }
        if (this.controls) this.controls.dispose();
    }
}
