
/**
 * Structure Designer Drawing - 2D Drawing Tools and Sketching
 * Handles line, rectangle, circle, polygon drawing and sketch management
 */

class StructureDesignerDrawing {
    constructor(core) {
        this.core = core;
        this.state = {
            sketches: [],
            isDrawing: false,
            drawingPoints: []
        };
    }

    setupDrawingEventListeners() {
        // Clear sketch
        const clearSketchBtn = document.getElementById('clearSketchBtn');
        if (clearSketchBtn) {
            clearSketchBtn.addEventListener('click', () => this.clearSketches());
        }

        // Sketch properties
        const sketchWidth = document.getElementById('sketchWidth');
        const sketchHeight = document.getElementById('sketchHeight');

        if (sketchWidth) {
            sketchWidth.addEventListener('input', (e) => {
                this.updateSelectedSketchProperty('width', parseFloat(e.target.value));
            });
        }

        if (sketchHeight) {
            sketchHeight.addEventListener('input', (e) => {
                this.updateSelectedSketchProperty('height', parseFloat(e.target.value));
            });
        }

        // Extrusion
        const extrudeBtn = document.getElementById('extrudeBtn');
        if (extrudeBtn) {
            extrudeBtn.addEventListener('click', () => this.extrudeSelected());
        }

        // Export
        const exportModelBtn = document.getElementById('exportModelBtn');
        if (exportModelBtn) {
            exportModelBtn.addEventListener('click', () => this.exportModel());
        }
    }

    onMouseDown(event) {
        if (this.core.state.currentView === '3D') return;

        const intersect = this.core.getIntersectionWithWorkingPlane();
        if (!intersect) return;

        switch (this.core.state.currentTool) {
            case 'line':
                this.startLineDrawing(intersect.point);
                break;
            case 'rect':
                this.startRectangleDrawing(intersect.point);
                break;
            case 'circle':
                this.startCircleDrawing(intersect.point);
                break;
            case 'polygon':
                this.addPolygonPoint(intersect.point);
                break;
        }
    }

    onMouseMove(event) {
        if (this.state.isDrawing && this.core.state.currentView !== '3D') {
            const intersect = this.core.getIntersectionWithWorkingPlane();
            if (intersect) {
                this.updateDrawingPreview(intersect.point);
            }
        }
    }

    onMouseUp(event) {
        if (this.state.isDrawing && this.core.state.currentView !== '3D') {
            const intersect = this.core.getIntersectionWithWorkingPlane();
            if (intersect) {
                const snappedPoint = this.core.snapToGrid(intersect.point);

                if (this.core.state.currentTool === 'line' || 
                    this.core.state.currentTool === 'rect' || 
                    this.core.state.currentTool === 'circle') {

                    if (this.state.drawingPoints.length === 1) {
                        this.state.drawingPoints.push(snappedPoint);
                    }
                    this.finishDrawing();
                }
            }
        }
    }

    onDoubleClick(event) {
        if (this.core.state.currentTool === 'polygon') {
            this.finishPolygon();
        }
    }

    startLineDrawing(point) {
        const snappedPoint = this.core.snapToGrid(point);
        this.state.isDrawing = true;
        this.state.drawingPoints = [snappedPoint];
    }

    startRectangleDrawing(point) {
        const snappedPoint = this.core.snapToGrid(point);
        this.state.isDrawing = true;
        this.state.drawingPoints = [snappedPoint];
    }

    startCircleDrawing(point) {
        const snappedPoint = this.core.snapToGrid(point);
        this.state.isDrawing = true;
        this.state.drawingPoints = [snappedPoint];
    }

    addPolygonPoint(point) {
        const snappedPoint = this.core.snapToGrid(point);

        if (!this.state.isDrawing) {
            this.state.isDrawing = true;
            this.state.drawingPoints = [];
        }

        this.state.drawingPoints.push(snappedPoint);
    }

    finishDrawing() {
        this.clearDrawingPreview();

        if (this.state.drawingPoints.length < 2) {
            this.cancelDrawing();
            return;
        }

        let sketch = null;

        switch (this.core.state.currentTool) {
            case 'line':
                sketch = this.createLineSketch();
                break;
            case 'rect':
                sketch = this.createRectangleSketch();
                break;
            case 'circle':
                sketch = this.createCircleSketch();
                break;
        }

        if (sketch) {
            this.state.sketches.push(sketch);
            this.core.scene.add(sketch.object);
            console.log(`[StructureDesigner3D] Created ${sketch.type} sketch with ID: ${sketch.id}`);
        }

        this.state.isDrawing = false;
        this.state.drawingPoints = [];
        this.updateUI();
    }

    finishPolygon() {
        if (this.state.drawingPoints.length < 3) {
            this.cancelDrawing();
            return;
        }

        const sketch = this.createPolygonSketch();
        if (sketch) {
            this.state.sketches.push(sketch);
            this.core.scene.add(sketch.object);
        }

        this.state.isDrawing = false;
        this.state.drawingPoints = [];
        this.updateUI();
    }

    cancelDrawing() {
        this.clearDrawingPreview();
        this.state.isDrawing = false;
        this.state.drawingPoints = [];
        console.log('[StructureDesigner3D] Drawing cancelled');
    }

    createLineSketch() {
        const points = this.state.drawingPoints;
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, this.core.materials.sketch);

        return {
            id: `line_${Date.now()}`,
            type: 'line',
            object: line,
            points: points,
            plane: this.core.state.workingPlane
        };
    }

    createRectangleSketch() {
        const [start, end] = this.state.drawingPoints;
        const width = Math.abs(end.x - start.x);
        const height = Math.abs(end.y - start.y);

        const points = [
            new THREE.Vector3(start.x, start.y, start.z),
            new THREE.Vector3(end.x, start.y, start.z),
            new THREE.Vector3(end.x, end.y, start.z),
            new THREE.Vector3(start.x, end.y, start.z),
            new THREE.Vector3(start.x, start.y, start.z)
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, this.core.materials.sketch);

        return {
            id: `rect_${Date.now()}`,
            type: 'rectangle',
            object: line,
            points: points,
            plane: this.core.state.workingPlane,
            width: width,
            height: height
        };
    }

    createCircleSketch() {
        const [center, edge] = this.state.drawingPoints;
        const radius = center.distanceTo(edge);

        const points = [];
        const segments = 32;
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            points.push(new THREE.Vector3(
                center.x + Math.cos(angle) * radius,
                center.y + Math.sin(angle) * radius,
                center.z
            ));
        }

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, this.core.materials.sketch);

        return {
            id: `circle_${Date.now()}`,
            type: 'circle',
            object: line,
            points: points,
            plane: this.core.state.workingPlane,
            radius: radius
        };
    }

    createPolygonSketch() {
        const points = [...this.state.drawingPoints, this.state.drawingPoints[0]];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, this.core.materials.sketch);

        return {
            id: `polygon_${Date.now()}`,
            type: 'polygon',
            object: line,
            points: points,
            plane: this.core.state.workingPlane
        };
    }

    clearSketches() {
        this.state.sketches.forEach(sketch => {
            this.core.scene.remove(sketch.object);
        });
        this.state.sketches = [];
        this.core.state.selectedObject = null;
        this.updateUI();
        console.log('[StructureDesigner3D] All sketches cleared');
    }

    updateDrawingPreview(point) {
        this.clearDrawingPreview();

        const snappedPoint = this.core.snapToGrid(point);

        if (this.core.state.currentTool === 'line' && this.state.drawingPoints.length === 1) {
            this.createLinePreview(this.state.drawingPoints[0], snappedPoint);
        } else if (this.core.state.currentTool === 'rect' && this.state.drawingPoints.length === 1) {
            this.createRectanglePreview(this.state.drawingPoints[0], snappedPoint);
        } else if (this.core.state.currentTool === 'circle' && this.state.drawingPoints.length === 1) {
            this.createCirclePreview(this.state.drawingPoints[0], snappedPoint);
        } else if (this.core.state.currentTool === 'polygon' && this.state.drawingPoints.length > 0) {
            this.createPolygonPreview([...this.state.drawingPoints, snappedPoint]);
        }
    }

    clearDrawingPreview() {
        const objectsToRemove = [];
        this.core.scene.traverse((child) => {
            if (child.userData && child.userData.isPreview) {
                objectsToRemove.push(child);
            }
        });
        objectsToRemove.forEach(obj => this.core.scene.remove(obj));
    }

    createLinePreview(start, end) {
        const points = [start, end];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ 
            color: 0xffffff, 
            linewidth: 2, 
            transparent: true, 
            opacity: 0.6 
        });
        const line = new THREE.Line(geometry, material);
        line.userData.isPreview = true;
        this.core.scene.add(line);
    }

    createRectanglePreview(start, end) {
        const points = [
            new THREE.Vector3(start.x, start.y, start.z),
            new THREE.Vector3(end.x, start.y, start.z),
            new THREE.Vector3(end.x, end.y, start.z),
            new THREE.Vector3(start.x, end.y, start.z),
            new THREE.Vector3(start.x, start.y, start.z)
        ];
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ 
            color: 0xffffff, 
            linewidth: 2, 
            transparent: true, 
            opacity: 0.6 
        });
        const line = new THREE.Line(geometry, material);
        line.userData.isPreview = true;
        this.core.scene.add(line);
    }

    createCirclePreview(center, edge) {
        const radius = center.distanceTo(edge);
        const points = [];
        const segments = 32;
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            points.push(new THREE.Vector3(
                center.x + Math.cos(angle) * radius,
                center.y + Math.sin(angle) * radius,
                center.z
            ));
        }
        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ 
            color: 0xffffff, 
            linewidth: 2, 
            transparent: true, 
            opacity: 0.6 
        });
        const line = new THREE.Line(geometry, material);
        line.userData.isPreview = true;
        this.core.scene.add(line);
    }

    createPolygonPreview(points) {
        if (points.length < 2) return;

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const material = new THREE.LineBasicMaterial({ 
            color: 0xffffff, 
            linewidth: 2, 
            transparent: true, 
            opacity: 0.6 
        });
        const line = new THREE.Line(geometry, material);
        line.userData.isPreview = true;
        this.core.scene.add(line);
    }

    extrudeSelected() {
        if (!this.core.state.selectedObject || this.core.state.selectedObject.type === 'line') {
            this.core.showError('Please select a closed shape to extrude');
            return;
        }

        const height = parseFloat(document.getElementById('extrusionHeight').value) || 3.0;
        const extruded = this.createExtrudedGeometry(this.core.state.selectedObject, height);

        if (extruded) {
            this.core.scene.add(extruded.object);
            this.core.autoFitCamera();
            this.updateUI();
            console.log('[StructureDesigner3D] Extruded object created');
        }
    }

    createExtrudedGeometry(sketch, height) {
        let geometry = null;
        let mesh = null;
        const plane = sketch.plane;

        switch (sketch.type) {
            case 'rectangle':
                if (plane === 'XY') {
                    geometry = new THREE.BoxGeometry(sketch.width, sketch.height, height);
                    mesh = new THREE.Mesh(geometry, this.core.materials.extrusion);
                    const rectCenter = this.getRectangleCenter(sketch);
                    mesh.position.set(rectCenter.x, rectCenter.y, height / 2);
                }
                break;

            case 'circle':
                if (plane === 'XY') {
                    geometry = new THREE.CylinderGeometry(sketch.radius, sketch.radius, height, 32);
                    mesh = new THREE.Mesh(geometry, this.core.materials.extrusion);
                    mesh.rotation.x = Math.PI / 2;
                    const circleCenter = sketch.points[0];
                    mesh.position.set(circleCenter.x, circleCenter.y, height / 2);
                }
                break;

            case 'polygon':
                const shape = new THREE.Shape();
                const points = sketch.points.slice(0, -1);

                if (points.length > 0 && plane === 'XY') {
                    shape.moveTo(points[0].x, points[0].y);
                    for (let i = 1; i < points.length; i++) {
                        shape.lineTo(points[i].x, points[i].y);
                    }
                }

                const extrudeSettings = {
                    depth: height,
                    bevelEnabled: false
                };
                geometry = new THREE.ExtrudeGeometry(shape, extrudeSettings);
                mesh = new THREE.Mesh(geometry, this.core.materials.extrusion);

                const polygonCenter = this.getPolygonCenter(sketch);
                mesh.position.set(polygonCenter.x, polygonCenter.y, height / 2);
                break;

            case 'line':
                return null;
        }

        if (!mesh) return null;

        mesh.castShadow = true;
        mesh.receiveShadow = true;

        return {
            id: `extrusion_${Date.now()}`,
            type: 'extrusion',
            object: mesh,
            sourceSketch: sketch.id,
            height: height,
            extrusionPlane: plane
        };
    }

    getRectangleCenter(sketch) {
        const points = sketch.points;
        let centerX = 0, centerY = 0, centerZ = 0;

        for (let i = 0; i < 4; i++) {
            centerX += points[i].x;
            centerY += points[i].y;
            centerZ += points[i].z;
        }

        return {
            x: centerX / 4,
            y: centerY / 4,
            z: centerZ / 4
        };
    }

    getPolygonCenter(sketch) {
        const points = sketch.points.slice(0, -1);
        let centerX = 0, centerY = 0, centerZ = 0;

        for (let point of points) {
            centerX += point.x;
            centerY += point.y;
            centerZ += point.z;
        }

        return {
            x: centerX / points.length,
            y: centerY / points.length,
            z: centerZ / points.length
        };
    }

    updateSelectedSketchProperty(property, value) {
        if (!this.core.state.selectedObject) return;

        if (property === 'width' && this.core.state.selectedObject.type === 'rectangle') {
            this.core.state.selectedObject.width = value;
            this.regenerateRectangle(this.core.state.selectedObject);
        } else if (property === 'height' && this.core.state.selectedObject.type === 'rectangle') {
            this.core.state.selectedObject.height = value;
            this.regenerateRectangle(this.core.state.selectedObject);
        }
    }

    regenerateRectangle(sketch) {
        this.core.scene.remove(sketch.object);

        const center = sketch.points[0];
        const points = [
            new THREE.Vector3(center.x, center.y, center.z),
            new THREE.Vector3(center.x + sketch.width, center.y, center.z),
            new THREE.Vector3(center.x + sketch.width, center.y + sketch.height, center.z),
            new THREE.Vector3(center.x, center.y + sketch.height, center.z),
            new THREE.Vector3(center.x, center.y, center.z)
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        sketch.object = new THREE.Line(geometry, this.core.materials.selected);
        sketch.points = points;

        this.core.scene.add(sketch.object);
    }

    exportModel() {
        const modelData = {
            sketches: this.state.sketches.map(s => ({
                id: s.id,
                type: s.type,
                points: s.points.map(p => ({ x: p.x, y: p.y, z: p.z })),
                plane: s.plane,
                width: s.width,
                height: s.height,
                radius: s.radius
            }))
        };

        const dataStr = JSON.stringify(modelData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = '3d-sketches.json';
        link.click();

        URL.revokeObjectURL(url);
        console.log('[StructureDesigner3D] Sketches exported');
    }

    updateUI() {
        const sketchStatus = document.getElementById('sketchStatus');
        if (sketchStatus) {
            if (this.core.state.selectedObject) {
                sketchStatus.textContent = `Selected: ${this.core.state.selectedObject.type} (${this.core.state.selectedObject.id})`;
                sketchStatus.className = 'status-display status-success';

                if (this.core.state.selectedObject.width !== undefined) {
                    const sketchWidth = document.getElementById('sketchWidth');
                    if (sketchWidth) sketchWidth.value = this.core.state.selectedObject.width.toFixed(1);
                }
                if (this.core.state.selectedObject.height !== undefined) {
                    const sketchHeight = document.getElementById('sketchHeight');
                    if (sketchHeight) sketchHeight.value = this.core.state.selectedObject.height.toFixed(1);
                }
            } else {
                sketchStatus.textContent = 'No sketch selected';
                sketchStatus.className = 'status-display';
            }
        }

        const extrusionStatus = document.getElementById('extrusionStatus');
        const extrudeBtn = document.getElementById('extrudeBtn');

        if (extrusionStatus && extrudeBtn) {
            if (this.core.state.selectedObject && this.core.state.selectedObject.type !== 'line') {
                extrusionStatus.textContent = `Ready to extrude ${this.core.state.selectedObject.type}`;
                extrusionStatus.className = 'status-display status-success';
                extrudeBtn.disabled = false;
            } else {
                extrusionStatus.textContent = 'Select a closed shape to extrude';
                extrusionStatus.className = 'status-display';
                extrudeBtn.disabled = true;
            }
        }
    }
}

// Export for use by other modules
window.StructureDesignerDrawing = StructureDesignerDrawing;
