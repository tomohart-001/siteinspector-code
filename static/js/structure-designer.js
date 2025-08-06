/**
 * Structure Designer 3D - Main Integration Class
 * Integrates core engine, drawing tools, and structural elements
 */

class StructureDesigner3D {
    constructor() {
        // Initialize core module
        this.core = new StructureDesigner3DCore();

        // Initialize drawing module
        this.drawing = new StructureDesignerDrawing(this.core);

        // Initialize structures module
        this.structures = new StructureDesignerStructures(this.core);

        // Bind methods to maintain context
        this.initialize = this.initialize.bind(this);
        this.onMouseDown = this.onMouseDown.bind(this);
        this.onMouseMove = this.onMouseMove.bind(this);
        this.onMouseUp = this.onMouseUp.bind(this);
        this.onDoubleClick = this.onDoubleClick.bind(this);

        console.log('[StructureDesigner3D] Integrated designer initialized with all modules');
    }

    initialize() {
        try {
            // Initialize core first
            this.core.initialize();

            // Setup event listeners for all modules
            this.setupIntegratedEventListeners();

            console.log('[StructureDesigner3D] All modules initialized successfully');

        } catch (error) {
            console.error('[StructureDesigner3D] Failed to initialize integrated designer:', error);
            throw error;
        }
    }

    setupIntegratedEventListeners() {
        // Setup drawing tools event listeners
        this.drawing.setupDrawingEventListeners();

        // Setup structural elements event listeners
        this.structures.setupStructuralEventListeners();

        // Override core mouse events to include drawing functionality
        if (this.core.renderer && this.core.renderer.domElement) {
            // Remove existing listeners
            this.core.renderer.domElement.removeEventListener('mousedown', this.core.onMouseDown);
            this.core.renderer.domElement.removeEventListener('mousemove', this.core.onMouseMove);
            this.core.renderer.domElement.removeEventListener('mouseup', this.core.onMouseUp);
            this.core.renderer.domElement.removeEventListener('dblclick', this.core.onDoubleClick);

            // Add integrated listeners
            this.core.renderer.domElement.addEventListener('mousedown', this.onMouseDown);
            this.core.renderer.domElement.addEventListener('mousemove', this.onMouseMove);
            this.core.renderer.domElement.addEventListener('mouseup', this.onMouseUp);
            this.core.renderer.domElement.addEventListener('dblclick', this.onDoubleClick);

            console.log('[StructureDesigner3D] Integrated mouse events attached');
        }
    }

    // Integrated mouse event handlers
    onMouseDown(event) {
        // Handle core selection first
        this.core.onMouseDown(event);

        // Then handle drawing tools
        this.drawing.onMouseDown(event);
    }

    onMouseMove(event) {
        // Handle core mouse move
        this.core.onMouseMove(event);

        // Then handle drawing preview
        this.drawing.onMouseMove(event);
    }

    onMouseUp(event) {
        // Handle core mouse up
        this.core.onMouseUp(event);

        // Then handle drawing completion
        this.drawing.onMouseUp(event);
    }

    onDoubleClick(event) {
        // Handle drawing double click (polygon completion)
        this.drawing.onDoubleClick(event);
    }

    // Convenience methods that delegate to appropriate modules
    setView(viewMode) {
        return this.core.setView(viewMode);
    }

    setTool(tool) {
        return this.core.setTool(tool);
    }

    autoFitCamera() {
        return this.core.autoFitCamera();
    }

    showError(message) {
        return this.core.showError(message);
    }

    showSuccess(message) {
        return this.core.showSuccess(message);
    }

    // Access to module states
    get state() {
        return {
            core: this.core.state,
            drawing: this.drawing.state,
            structures: this.structures.state
        };
    }

    // Access to scene and camera for external use
    get scene() {
        return this.core.scene;
    }

    get camera() {
        return this.core.camera;
    }

    get renderer() {
        return this.core.renderer;
    }

    // Update UI across all modules
    updateUI() {
        this.core.updateUI();
        this.drawing.updateUI();
        this.structures.updateUI();
    }

    // Export functionality
    exportModel() {
        const modelData = {
            sketches: this.drawing.state.sketches.map(s => ({
                id: s.id,
                type: s.type,
                points: s.points.map(p => ({ x: p.x, y: p.y, z: p.z })),
                plane: s.plane,
                width: s.width,
                height: s.height,
                radius: s.radius
            })),
            objects3D: this.structures.state.objects3D.map(o => ({
                id: o.id,
                type: o.type,
                height: o.height
            })),
            slab: this.structures.state.slab ? {
                width: this.structures.state.slab.width,
                length: this.structures.state.slab.length,
                position: this.structures.state.slab.position,
                thickness: this.structures.state.slab.thickness
            } : null,
            columns: this.structures.state.columns.map(c => ({
                position: c.position,
                dimensions: c.dimensions,
                gridPosition: c.gridPosition
            }))
        };

        const dataStr = JSON.stringify(modelData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = 'complete-structure-model.json';
        link.click();

        URL.revokeObjectURL(url);
        console.log('[StructureDesigner3D] Complete model exported');
    }
}

// Export for global use
window.StructureDesigner3D = StructureDesigner3D;