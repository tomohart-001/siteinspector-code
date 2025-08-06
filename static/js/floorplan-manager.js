/**
 * Floor Plan Manager - Refactored
 * Handles floor plan upload, processing, and interactive manipulation
 */

class FloorplanManager extends BaseManager {
    constructor(map, draw) {
        super('FloorplanManager');
        this.map = map;
        this.draw = draw;

        // State management
        this.state = {
            floorplanData: null,
            geojsonPolygon: null,
            isUploading: false,
            isLocked: false,
            isDrawing: false,
            drawingPoints: [],
            currentTransform: {
                position: null,
                rotation: 0,
                scale: 1.0
            },
            building3d: {
                isEnabled: false,
                storeys: 2,
                storeyHeight: 3.0,
                totalHeight: 6.0,
                isVisible: false
            }
        };

        // Interaction state
        this.interaction = {
            isDragging: false,
            isRotating: false,
            isScaling: false,
            dragStart: null,
            rotationCenter: null,
            initialRotation: 0,
            scalingStart: null
        };

        // Event handlers
        this.handlers = {
            fileHandler: null,
            buttonHandler: null
        };

        // Configuration
        this.config = {
            defaultScale: 30,
            scaleFactors: {
                small: 20,
                medium: 30,
                large: 50
            },
            rotationSensitivity: 0.1, // 10% sensitivity for rotation
            layerIds: {
                fill: 'floorplan-fill',
                outline: 'floorplan-outline',
                center: 'floorplan-center',
                drawing: 'floorplan-drawing',
                drawingPoints: 'floorplan-drawing-points',
                previewLine: 'floorplan-preview-line',
                previewPolygon: 'floorplan-preview-polygon',
                extrusion: 'floorplan-3d-extrusion'
            },
            sourceIds: {
                polygon: 'floorplan-polygon',
                center: 'floorplan-center',
                drawing: 'floorplan-drawing',
                drawingPoints: 'floorplan-drawing-points',
                previewLine: 'floorplan-preview-line',
                previewPolygon: 'floorplan-preview-polygon',
                extrusion: 'floorplan-3d-extrusion'
            },
            drawingStyle: {
                fillColor: '#ff6b35',
                strokeColor: '#ff6b35',
                fillOpacity: 0.3,
                strokeWidth: 2
            },
            extrusion: {
                defaultStoreys: 2,
                defaultStoreyHeight: 3.0,
                minStoreys: 1,
                maxStoreys: 10,
                minStoreyHeight: 1.8,
                maxStoreyHeight: 5.0
            }
        };

        this.opencvProcessor = null;
        this.fileInputInitialized = false;

        this.initialize();
    }

    /**
     * Initialize the floor plan manager
     */
    initialize() {
        try {
            this.resetUploadButtonState();
            this.setupEventListeners();
            this.setupDrawingButton();
            this.clearStoredFloorplanData(); // Clear any previous session data
            this.info('FloorplanManager initialized successfully');
        } catch (error) {
            this.error('Failed to initialize FloorplanManager', error);
        }
    }

    /**
     * Setup drawing button
     */
    setupDrawingButton() {
        const drawButton = document.getElementById('drawFloorplanButton');
        if (drawButton) {
            // Remove any existing listeners
            drawButton.replaceWith(drawButton.cloneNode(true));
            const newDrawButton = document.getElementById('drawFloorplanButton');

            newDrawButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                this.debug('Draw button clicked, current drawing state:', this.state.isDrawing);

                if (this.state.isDrawing) {
                    this.stopDrawingMode();
                } else {
                    this.startDrawingMode();
                }
            });

            // Ensure button is visible and enabled
            newDrawButton.style.display = 'block';
            newDrawButton.disabled = false;

            this.debug('Drawing button setup completed');
        } else {
            this.error('Draw floorplan button not found in DOM');
        }

        // Setup clear button
        const clearButton = document.getElementById('clearFloorplanButton');
        if (clearButton) {
            clearButton.replaceWith(clearButton.cloneNode(true));
            const newClearButton = document.getElementById('clearFloorplanButton');

            newClearButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.clearStructure();
            });

            this.debug('Clear button setup completed');
        }

        // Setup lock button
        const lockButton = document.getElementById('lockFloorplanButton');
        if (lockButton) {
            lockButton.replaceWith(lockButton.cloneNode(true));
            const newLockButton = document.getElementById('lockFloorplanButton');

            newLockButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleLock();
            });

            this.debug('Lock button setup completed');
        }

        // Initial button state update
        this.updateFloorplanButtons();
    }

    /**
     * Clear structure footprint
     */
    clearStructure() {
        if (!this.state.geojsonPolygon) {
            this.warn('No structure to clear');
            return;
        }

        const shouldClear = confirm('Are you sure you want to clear the structure footprint?');
        if (!shouldClear) {
            return;
        }

        this.removeFloorplanFromMap();
        this.resetState();
        this.updateFloorplanButtons();
        this.updateUI('info', 'Structure footprint cleared');
        this.info('Structure footprint cleared by user');
    }

    /**
     * Setup 3D building controls
     */
    //setup3DControls() {
    //    // Storey count slider
    //    const storeySlider = document.getElementById('storeyCount');
    //    const storeyValue = document.getElementById('storeyCountValue');

    //    if (storeySlider && storeyValue) {
    //        storeySlider.addEventListener('input', (e) => {
    //            const storeys = parseInt(e.target.value);
    //            this.state.building3d.storeys = storeys;
    //            storeyValue.textContent = storeys;
    //            this.updateTotalHeight();
    //            this.update3DBuilding();
    //        });
    //    }

    //    // Storey height slider
    //    const heightSlider = document.getElementById('storeyHeight');
    //    const heightValue = document.getElementById('storeyHeightValue');

    //    if (heightSlider && heightValue) {
    //        heightSlider.addEventListener('input', (e) => {
    //            const height = parseFloat(e.target.value);
    //            this.state.building3d.storeyHeight = height;
    //            heightValue.textContent = height.toFixed(1);
    //            this.updateTotalHeight();
    //            this.update3DBuilding();
    //        });
    //    }

    //    // Create 3D button
    //    const create3dButton = document.getElementById('create3dButton');
    //    if (create3dButton) {
    //        create3dButton.addEventListener('click', () => {
    //            this.create3DBuilding();
    //        });
    //    }

    //    // Remove 3D button
    //    const remove3dButton = document.getElementById('remove3dButton');
    //    if (remove3dButton) {
    //        remove3dButton.addEventListener('click', () => {
    //            this.remove3DBuilding();
    //        });
    //    }
    //}

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        this.setupFileHandlers();
        this.setupMapHandlers();
        this.setupKeyboardHandlers();
    }

    /**
     * Setup file upload handlers
     */
    setupFileHandlers() {
        // File upload functionality removed - only drawing mode available
        this.debug('File upload handlers skipped - drawing mode only');
    }

    /**
     * Remove file upload handlers
     */
    removeFileHandlers() {
        const floorplanInput = document.getElementById('floorplanInput');
        const uploadButton = document.getElementById('uploadFloorplanButton');

        if (floorplanInput && this.handlers.fileHandler) {
            floorplanInput.removeEventListener('change', this.handlers.fileHandler);
        }

        if (uploadButton && this.handlers.buttonHandler) {
            uploadButton.removeEventListener('click', this.handlers.buttonHandler);
        }

        this.handlers.fileHandler = null;
        this.handlers.buttonHandler = null;
        this.fileInputInitialized = false;
    }

    /**
     * Setup map interaction handlers
     */
    setupMapHandlers() {
        if (!this.map) return;

        this.map.on('mousedown', this.handleMouseDown.bind(this));
        this.map.on('mousemove', this.handleMouseMove.bind(this));
        this.map.on('mouseup', this.handleMouseUp.bind(this));
        this.map.on('contextmenu', this.handleRightClick.bind(this));
        this.map.on('click', this.handleMapClick.bind(this));
        this.map.on('dblclick', this.handleMapDoubleClick.bind(this));

        // Add specific drawing mode mouse move handler
        this.map.on('mousemove', this.handleDrawingMouseMove.bind(this));
    }

    /**
     * Setup keyboard handlers
     */
    setupKeyboardHandlers() {
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        document.addEventListener('keyup', this.handleKeyUp.bind(this));
    }

    /**
     * Handle file selection - automatically process and upload
     */
    handleFileSelection(event) {
        const file = event.target.files?.[0];

        if (!file) {
            this.debug('No file selected');
            return;
        }

        if (this.state.isUploading) {
            this.warn('Upload already in progress, ignoring new file selection');
            return;
        }

        this.info('File selected, automatically starting processing and upload', { 
            fileName: file.name, 
            fileSize: file.size 
        });

        // Automatically process the file once selected
        this.processFile(file);
    }

    /**
     * Handle upload button click - triggers file selection
     */
    handleUploadButtonClick(event) {
        event.preventDefault();
        event.stopPropagation();

        if (this.state.isUploading) {
            this.warn('Processing in progress, please wait');
            return;
        }

        // Clear previous selection and trigger file picker
        const input = document.getElementById('floorplanInput');
        if (input) {
            // Clear the value to ensure change event fires even for the same file
            input.value = '';

            // Trigger file picker immediately - no delay needed
            input.click();

            this.debug('File picker triggered');
        }
    }

    /**
     * Process uploaded file
     */
    async processFile(file) {
        if (!this.validateFile(file)) return;

        try {
            this.setUploadingState(true, `Processing ${file.name}...`);

            await this.initializeOpenCVProcessor();

            const result = await this.processFloorplanImage(file);

            if (result.success) {
                this.state.floorplanData = result;
                await this.convertToGeojsonAndDisplay();
                this.updateUI('success', `Floor plan processed: ${result.boundaries.length} boundary points detected`);
            } else {
                throw new Error(result.error || 'Processing failed');
            }

        } catch (error) {
            this.handleProcessingError(error);
        } finally {
            this.setUploadingState(false);
        }
    }

    /**
     * Validate uploaded file
     */
    validateFile(file) {
        if (!file || file.size === 0) {
            this.updateUI('error', 'Invalid file selected');
            return false;
        }

        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            this.updateUI('error', 'File too large. Maximum size is 10MB');
            return false;
        }

        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        if (!allowedTypes.includes(file.type)) {
            this.updateUI('error', 'Unsupported file type. Please use JPEG, PNG, GIF, or WebP');
            return false;
        }

        return true;
    }

    /**
     * Initialize OpenCV processor if needed
     */
    async initializeOpenCVProcessor() {
        if (!this.opencvProcessor) {
            this.opencvProcessor = new window.OpenCVProcessor();
            this.updateUI('info', 'Loading image processing library...');
            await this.opencvProcessor.loadOpenCV();
        }
    }

    /**
     * Process floor plan image
     */
    async processFloorplanImage(file) {
        this.updateUI('info', 'Analyzing floor plan image...');

        try {
            // Try OpenCV processing first
            const imageElement = await this.opencvProcessor.fileToImage(file);
            const opencvResult = await this.opencvProcessor.processFloorplanImage(imageElement);

            if (opencvResult.success) {
                this.info('OpenCV processing successful', {
                    boundaryPoints: opencvResult.boundaries?.length
                });

                return {
                    success: true,
                    boundaries: opencvResult.boundaries,
                    coordinates: this.boundariesToCoordinates(opencvResult.boundaries),
                    metrics: this.calculateMetrics(opencvResult.boundaries),
                    processed_image: opencvResult.processedImage,
                    processing_method: 'opencv'
                };
            }
        } catch (error) {
            this.warn('OpenCV processing failed, trying server fallback', error);
        }

        // Fallback to server processing
        return await this.processOnServer(file);
    }

    /**
     * Process file on server as fallback
     */
    async processOnServer(file) {
        this.updateUI('info', 'Using server-side processing...');

        const imageData = await this.fileToBase64(file);
        const response = await window.apiClient.post('/upload-floorplan', {
            image: imageData,
            scale_reference: null
        });

        if (response.success) {
            this.info('Server processing successful', {
                boundaryPoints: response.boundaries?.length
            });
            return response;
        } else {
            throw new Error(response.error || 'Server processing failed');
        }
    }

    /**
     * Convert to GeoJSON and display on map
     */
    async convertToGeojsonAndDisplay() {
        try {
            const siteData = window.siteInspector?.siteData;
            if (!siteData?.center) {
                throw new Error('Site center not available');
            }

            const response = await window.apiClient.post('/convert-floorplan-to-geojson', {
                center_lat: siteData.center.lat,
                center_lng: siteData.center.lng,
                scale_meters: this.config.defaultScale
            });

            if (response.success) {
                this.state.geojsonPolygon = response.geojson_polygon;
                this.displayFloorplanOnMap();
                this.info('Floor plan converted to GeoJSON and displayed');
            } else {
                throw new Error(response.error || 'Failed to convert to GeoJSON');
            }

        } catch (error) {
            this.error('GeoJSON conversion failed', error);
            throw error;
        }
    }

    /**
     * Display floor plan on map
     */
    displayFloorplanOnMap() {
        if (!this.state.geojsonPolygon || !this.map) return;

        this.removeFloorplanFromMap();
        this.addFloorplanSources();
        this.addFloorplanLayers();
        this.addCenterPoint();
        this.generateStructureDimensions(); // Add dimensions for the completed structure
        this.check3DControlsAvailability();
        this.updateFloorplanButtons(); // Update button visibility
        this.updateStructureLegend(true); // Add to legend

        this.info('Floor plan displayed on map');
    }

    /**
     * Check if 3D controls should be available
     */
    check3DControlsAvailability() {
        const controls = document.getElementById('building3dControls');
        if (!controls) return;

        const hasFloorplan = this.state.geojsonPolygon !== null;
        const isLocked = this.state.isLocked;

        if (hasFloorplan) {
            controls.style.display = 'block';
            this.state.building3d.isEnabled = true;

            // Enable/disable based on lock status
            const create3dButton = document.getElementById('create3dButton');
            const sliders = controls.querySelectorAll('input[type="range"]');

            if (isLocked) {
                if (create3dButton) create3dButton.disabled = false;
                sliders.forEach(slider => slider.disabled = false);
            } else {
                if (create3dButton) create3dButton.disabled = false; // Allow even when unlocked
                sliders.forEach(slider => slider.disabled = false);
                sliders.forEach(slider => slider.disabled = false);
            }
        } else {
            controls.style.display = 'none';
            this.state.building3d.isEnabled = false;
            this.remove3DBuilding();
        }
    }

    /**
     * Update total height display - removed
     */
    updateTotalHeight() {
        // 3D building functionality removed
    }

    /**
     * Create 3D building extrusion - removed
     */
    create3DBuilding() {
        // 3D building functionality removed
    }

    /**
     * Update existing 3D building - removed
     */
    update3DBuilding() {
        // 3D building functionality removed
    }

    /**
     * Remove 3D building extrusion - removed
     */
    remove3DBuilding() {
        // 3D building functionality removed
    }

    /**
     * Update 3D control button states - removed
     */
    update3DControlButtons() {
        // 3D building functionality removed
    }

    /**
     * Add floor plan sources to map
     */
    addFloorplanSources() {
        this.map.addSource(this.config.sourceIds.polygon, {
            type: 'geojson',
            data: this.state.geojsonPolygon
        });
    }

    /**
     * Add floor plan layers to map
     */
    addFloorplanLayers() {
        // Fill layer
        this.map.addLayer({
            id: this.config.layerIds.fill,
            type: 'fill',
            source: this.config.sourceIds.polygon,
            paint: {
                'fill-color': this.config.drawingStyle.fillColor,
                'fill-opacity': this.config.drawingStyle.fillOpacity
            }
        });

        // Outline layer - solid line for both uploaded and drawn floor plans
        this.map.addLayer({
            id: this.config.layerIds.outline,
            type: 'line',
            source: this.config.sourceIds.polygon,
            paint: {
                'line-color': this.config.drawingStyle.strokeColor,
                'line-width': this.config.drawingStyle.strokeWidth
            }
        });
    }

    /**
     * Add center point for rotation (invisible - used for calculations only)
     */
    addCenterPoint() {
        const center = this.getPolygonCenter(this.state.geojsonPolygon);

        this.map.addSource(this.config.sourceIds.center, {
            type: 'geojson',
            data: {
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [center.lng, center.lat]
                }
            }
        });

        // Center point layer removed - kept invisible for rotation calculations
        // No visible marker needed for user experience
    }

    /**
     * Remove floor plan from map
     */
    removeFloorplanFromMap() {
        const layers = [
            ...Object.values(this.config.layerIds),
            this.config.layerIds.drawing + '-line', // Additional drawing line layer
            'structure-dimension-labels' // Structure dimension labels
        ];
        const sources = [
            ...Object.values(this.config.sourceIds),
            'structure-dimensions' // Structure dimensions source
        ];

        layers.forEach(layerId => {
            if (this.map.getLayer(layerId)) {
                this.map.removeLayer(layerId);
            }
        });

        sources.forEach(sourceId => {
            if (this.map.getSource(sourceId)) {
                this.map.removeSource(sourceId);
            }
        });

        // Clean up 3D state
        this.state.building3d.isVisible = false;
        this.check3DControlsAvailability();
        this.updateFloorplanButtons(); // Update button visibility
        this.updateStructureLegend(false); // Remove from legend
    }

    /**
     * Handle mouse interactions
     */
    handleMouseDown(event) {
        if (this.state.isDrawing) return; // Don't handle mouse down in drawing mode
        if (this.state.isLocked || !this.state.geojsonPolygon) return;

        const features = this.map.queryRenderedFeatures(event.point, {
            layers: [this.config.layerIds.fill, this.config.layerIds.center]
        });

        if (features.length > 0) {
            event.preventDefault();
            this.startInteraction(event);
        }
    }

    /**
     * Handle map clicks for drawing mode
     */
    handleMapClick(event) {
        if (!this.state.isDrawing) return;

        event.preventDefault();

        // Check if point is within site boundary
        if (!this.isPointWithinSiteBoundary(event.lngLat)) {
            this.info('Drawing outside site boundary is not allowed');
            return;
        }

        this.addDrawingPoint(event.lngLat);
    }

    /**
     * Handle mouse move for preview line
     */
    handleDrawingMouseMove(event) {
        if (!this.state.isDrawing) return;

        this.updatePreviewLine(event.lngLat);
    }

    /**
     * Handle double click to finish drawing
     */
    handleMapDoubleClick(event) {
        if (!this.state.isDrawing) return;

        event.preventDefault();
        this.finishDrawing();
    }

    /**
     * Start drawing mode
     */
    startDrawingMode() {
        try {
            this.debug('Starting drawing mode...');

            if (this.state.geojsonPolygon) {
                const shouldReplace = confirm('This will replace your current floor plan. Continue?');
                if (!shouldReplace) {
                    this.debug('User cancelled drawing mode');
                    return;
                }
                this.removeFloorplanFromMap();
            }

            this.state.isDrawing = true;
            this.state.drawingPoints = [];

            // Disable map interactions
            if (this.map.boxZoom) this.map.boxZoom.disable();
            if (this.map.scrollZoom) this.map.scrollZoom.disable();
            if (this.map.dragPan) this.map.dragPan.disable();
            if (this.map.dragRotate) this.map.dragRotate.disable();
            if (this.map.doubleClickZoom) this.map.doubleClickZoom.disable();
            if (this.map.touchZoomRotate) this.map.touchZoomRotate.disable();

            this.map.getCanvas().style.cursor = 'crosshair';

            this.initializeDrawingSources();
            this.updateDrawingButton(true);
            this.updateStructureLegend(true); // Add to legend during drawing

            this.info('Structure placement mode started. Click to add points, double-click to finish');
            this.debug('Drawing mode initialization completed');

        } catch (error) {
            this.error('Failed to start drawing mode:', error);
            this.state.isDrawing = false;
            this.updateDrawingButton(false);
        }
    }

    /**
     * Stop drawing mode
     */
    stopDrawingMode() {
        this.state.isDrawing = false;
        this.state.drawingPoints = [];

        // Re-enable map interactions
        this.map.boxZoom.enable();
        this.map.scrollZoom.enable();
        this.map.dragPan.enable();
        this.map.dragRotate.enable();
        this.map.doubleClickZoom.enable();
        this.map.touchZoomRotate.enable();

        this.map.getCanvas().style.cursor = '';

        this.clearPreviews();
        this.clearDrawingSources();
        this.updateDrawingButton(false);

        // Only remove from legend if no completed structure exists
        if (!this.state.geojsonPolygon) {
            this.updateStructureLegend(false);
        }

        this.info('Drawing mode stopped');
    }

    /**
     * Add a point to the current drawing
     */
    addDrawingPoint(lngLat) {
        this.state.drawingPoints.push([lngLat.lng, lngLat.lat]);
        this.updateDrawingDisplay();
        this.clearPreviews(); // Clear previews when point is added

        this.debug(`Added drawing point: ${lngLat.lng}, ${lngLat.lat}`);
    }

    /**
     * Finish the current drawing
     */
    finishDrawing() {
        if (this.state.drawingPoints.length < 3) {
            this.warn('Need at least 3 points to create a floor plan');
            return;
        }

        // Store the point count before clearing
        const pointCount = this.state.drawingPoints.length;

        // Use the exact points as drawn - no smoothing to preserve user intent
        const exactPoints = [...this.state.drawingPoints];

        // Ensure polygon is properly closed
        const closedPoints = [...exactPoints];
        const firstPoint = closedPoints[0];
        const lastPoint = closedPoints[closedPoints.length - 1];

        // Only add closing point if not already closed
        if (firstPoint[0] !== lastPoint[0] || firstPoint[1] !== lastPoint[1]) {
            closedPoints.push([firstPoint[0], firstPoint[1]]);
        }

        // Create GeoJSON polygon
        this.state.geojsonPolygon = {
            type: 'Feature',
            properties: {
                type: 'floorplan',
                method: 'drawn',
                locked: false
            },
            geometry: {
                type: 'Polygon',
                coordinates: [closedPoints]
            }
        };

        this.clearPreviews();
        this.stopDrawingMode();
        this.displayFloorplanOnMap();
        this.saveDrawnFloorplan();
        this.check3DControlsAvailability();
        this.updateFloorplanButtons(); // Update button visibility

        this.info(`Structure footprint drawn with ${pointCount} points`);
    }

    /**
     * Check if point is within site boundary
     */
    isPointWithinSiteBoundary(lngLat) {
        // Get site data from parent inspector
        const siteData = window.siteInspector?.siteData;
        if (!siteData || !siteData.coordinates) return true;

        // Use simple point-in-polygon check
        const point = [lngLat.lng, lngLat.lat];
        const polygon = siteData.coordinates.map(coord => [coord.lng, coord.lat]);

        return this.pointInPolygon(point, polygon);
    }

    /**
     * Point-in-polygon algorithm
     */
    pointInPolygon(point, polygon) {
        const x = point[0], y = point[1];
        let inside = false;

        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const xi = polygon[i][0], yi = polygon[i][1];
            const xj = polygon[j][0], yj = polygon[j][1];

            if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
                inside = !inside;
            }
        }

        return inside;
    }

    /**
     * Initialize drawing sources
     */
    initializeDrawingSources() {
        this.clearDrawingSources();

        this.map.addSource(this.config.sourceIds.drawing, {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });

        this.map.addSource(this.config.sourceIds.drawingPoints, {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });

        // Initialize preview sources
        this.map.addSource(this.config.sourceIds.previewLine, {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });

        this.map.addSource(this.config.sourceIds.previewPolygon, {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });

        // Initialize dimensions source
        this.map.addSource('floorplan-dimensions', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: []
            }
        });
    }

    /**
     * Update preview line from last point to cursor
     */
    updatePreviewLine(lngLat) {
        if (this.state.drawingPoints.length === 0) return;

        const lastPoint = this.state.drawingPoints[this.state.drawingPoints.length - 1];
        const currentPoint = [lngLat.lng, lngLat.lat];

        // Create preview line
        const previewLineFeature = {
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: [lastPoint, currentPoint]
            },
            properties: {
                preview: true
            }
        };

        const previewLineSource = this.map.getSource(this.config.sourceIds.previewLine);
        if (previewLineSource) {
            previewLineSource.setData({
                type: 'FeatureCollection',
                features: [previewLineFeature]
            });
        }

        // Update preview polygon if we have 2 or more points
        if (this.state.drawingPoints.length >= 2) {
            this.updatePreviewPolygon(currentPoint);
        }

        // Update live dimensions
        this.updateLiveDimensions(currentPoint);
    }

    /**
     * Update preview polygon with current cursor position
     */
    updatePreviewPolygon(currentPoint) {
        if (this.state.drawingPoints.length < 2) return;

        // Create polygon coordinates including current cursor position
        const previewCoords = [...this.state.drawingPoints, currentPoint];

        // Close the polygon by adding the first point at the end
        previewCoords.push(this.state.drawingPoints[0]);

        const previewPolygonFeature = {
            type: 'Feature',
            geometry: {
                type: 'Polygon',
                coordinates: [previewCoords]
            },
            properties: {
                preview: true
            }
        };

        const previewPolygonSource = this.map.getSource(this.config.sourceIds.previewPolygon);
        if (previewPolygonSource) {
            previewPolygonSource.setData({
                type: 'FeatureCollection',
                features: [previewPolygonFeature]
            });
        }
    }

    /**
     * Update live dimensions during drawing
     */
    updateLiveDimensions(currentPoint) {
        const dimensionFeatures = [];

        // Only add dimensions for edges (lines), not for individual points
        // Add dimensions for all existing complete edges
        for (let i = 0; i < this.state.drawingPoints.length - 1; i++) {
            const start = this.state.drawingPoints[i];
            const end = this.state.drawingPoints[i + 1];
            const distance = this.calculateDistance(start[0], start[1], end[0], end[1]);

            // Only show dimension if distance is greater than 0
            if (distance > 0) {
                const midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: midpoint
                    },
                    properties: {
                        distance: `${distance.toFixed(1)}m`,
                        type: 'edge-dimension'
                    }
                });
            }
        }

        // Add dimension for current preview line (from last point to cursor)
        if (this.state.drawingPoints.length > 0) {
            const lastPoint = this.state.drawingPoints[this.state.drawingPoints.length - 1];
            const distance = this.calculateDistance(lastPoint[0], lastPoint[1], currentPoint[0], currentPoint[1]);

            // Only show preview dimension if distance is greater than 0
            if (distance > 0) {
                const midpoint = [(lastPoint[0] + currentPoint[0]) / 2, (lastPoint[1] + currentPoint[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: midpoint
                    },
                    properties: {
                        distance: `${distance.toFixed(1)}m`,
                        type: 'preview-dimension'
                    }
                });
            }
        }

        // Add closing dimension if we have 2 or more points (line from cursor to first point)
        if (this.state.drawingPoints.length >= 2) {
            const firstPoint = this.state.drawingPoints[0];
            const closingDistance = this.calculateDistance(currentPoint[0], currentPoint[1], firstPoint[0], firstPoint[1]);

            // Only show closing dimension if distance is greater than 0
            if (closingDistance > 0) {
                const closingMidpoint = [(currentPoint[0] + firstPoint[0]) / 2, (currentPoint[1] + firstPoint[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: closingMidpoint
                    },
                    properties: {
                        distance: `${closingDistance.toFixed(1)}m`,
                        type: 'closing-dimension'
                    }
                });
            }
        }

        // Update dimension source
        const dimensionSource = this.map.getSource('floorplan-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        }
    }

    /**
     * Clear preview displays
     */
    clearPreviews() {
        const previewLineSource = this.map.getSource(this.config.sourceIds.previewLine);
        if (previewLineSource) {
            previewLineSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        const previewPolygonSource = this.map.getSource(this.config.sourceIds.previewPolygon);
        if (previewPolygonSource) {
            previewPolygonSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        // Clear live dimensions
        const dimensionSource = this.map.getSource('floorplan-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }
    }

    /**
     * Return exact polygon points without smoothing to preserve user intent
     */
    smoothPolygonPoints(points) {
        // Return points exactly as drawn - no smoothing to avoid unwanted edge modifications
        return points;
    }

    /**
     * Update drawing display
     */
    updateDrawingDisplay() {
        if (this.state.drawingPoints.length === 0) return;

        // Update drawing points
        const pointFeatures = this.state.drawingPoints.map((point, index) => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: point
            },
            properties: {
                index: index
            }
        }));

        const pointSource = this.map.getSource(this.config.sourceIds.drawingPoints);
        if (pointSource) {
            pointSource.setData({
                type: 'FeatureCollection',
                features: pointFeatures
            });
        }

        // Update drawing polygon if we have enough points
        if (this.state.drawingPoints.length >= 3) {
            const polygonCoords = [...this.state.drawingPoints, this.state.drawingPoints[0]];

            const polygonFeature = {
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [polygonCoords]
                }
            };

            const polygonSource = this.map.getSource(this.config.sourceIds.drawing);
            if (polygonSource) {
                polygonSource.setData(polygonFeature);
            }
        } else if (this.state.drawingPoints.length === 2) {
            // Show line for 2 points
            const lineFeature = {
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: this.state.drawingPoints
                }
            };

            const polygonSource = this.map.getSource(this.config.sourceIds.drawing);
            if (polygonSource) {
                polygonSource.setData(lineFeature);
            }
        }

        // Update static dimensions for existing edges
        this.updateStaticDimensions();

        // Add drawing layers if they don't exist
        this.addDrawingLayers();
    }

    /**
     * Add drawing layers
     */
    addDrawingLayers() {
        // Add polygon/line layer
        if (!this.map.getLayer(this.config.layerIds.drawing)) {
            this.map.addLayer({
                id: this.config.layerIds.drawing,
                type: 'fill',
                source: this.config.sourceIds.drawing,
                paint: {
                    'fill-color': this.config.drawingStyle.fillColor,
                    'fill-opacity': this.config.drawingStyle.fillOpacity
                },
                filter: ['==', '$type', 'Polygon']
            });

            // Add line layer for incomplete polygons
            this.map.addLayer({
                id: this.config.layerIds.drawing + '-line',
                type: 'line',
                source: this.config.sourceIds.drawing,
                paint: {
                    'line-color': this.config.drawingStyle.strokeColor,
                    'line-width': this.config.drawingStyle.strokeWidth,
                    'line-dasharray': [2, 2]
                }
            });
        }

        // Add points layer
        if (!this.map.getLayer(this.config.layerIds.drawingPoints)) {
            this.map.addLayer({
                id: this.config.layerIds.drawingPoints,
                type: 'circle',
                source: this.config.sourceIds.drawingPoints,
                paint: {
                    'circle-radius': 4,
                    'circle-color': this.config.drawingStyle.strokeColor,
                    'circle-stroke-color': '#ffffff',
                    'circle-stroke-width': 2
                }
            });
        }

        // Add preview line layer
        if (!this.map.getLayer(this.config.layerIds.previewLine)) {
            this.map.addLayer({
                id: this.config.layerIds.previewLine,
                type: 'line',
                source: this.config.sourceIds.previewLine,
                paint: {
                    'line-color': this.config.drawingStyle.strokeColor,
                    'line-width': 2,
                    'line-opacity': 0.6,
                    'line-dasharray': [4, 4]
                }
            });
        }

        // Add preview polygon layer
        if (!this.map.getLayer(this.config.layerIds.previewPolygon)) {
            this.map.addLayer({
                id: this.config.layerIds.previewPolygon,
                type: 'fill',
                source: this.config.sourceIds.previewPolygon,
                paint: {
                    'fill-color': this.config.drawingStyle.fillColor,
                    'fill-opacity': 0.15
                }
            });

            // Add preview polygon outline
            this.map.addLayer({
                id: this.config.layerIds.previewPolygon + '-line',
                type: 'line',
                source: this.config.sourceIds.previewPolygon,
                paint: {
                    'line-color': this.config.drawingStyle.strokeColor,
                    'line-width': 2,
                    'line-opacity': 0.6,
                    'line-dasharray': [4, 4]
                }
            });
        }

        // Add live dimensions layer
        if (!this.map.getLayer('floorplan-dimension-labels')) {
            this.map.addLayer({
                id: 'floorplan-dimension-labels',
                type: 'symbol',
                source: 'floorplan-dimensions',
                layout: {
                    'text-field': ['get', 'distance'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-size': 12,
                    'text-offset': [0, -1],
                    'text-anchor': 'center',
                    'text-allow-overlap': true,
                    'text-ignore-placement': true,
                    'visibility': 'visible'
                },
                paint: {
                    'text-color': this.config.drawingStyle.strokeColor,
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2
                }
            });
        }
    }

    /**
     * Update static dimensions for existing drawing edges
     */
    updateStaticDimensions() {
        if (this.state.drawingPoints.length < 2) return;

        const dimensionFeatures = [];

        // Add dimensions for all existing complete edges (lines only, not points)
        for (let i = 0; i < this.state.drawingPoints.length - 1; i++) {
            const start = this.state.drawingPoints[i];
            const end = this.state.drawingPoints[i + 1];
            const distance = this.calculateDistance(start[0], start[1], end[0], end[1]);

            // Only add dimension if distance is greater than 0 to prevent 0.0m labels
            if (distance > 0) {
                const midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: midpoint
                    },
                    properties: {
                        distance: `${distance.toFixed(1)}m`,
                        type: 'static-dimension'
                    }
                });
            }
        }

        // Update dimension source with static dimensions only
        const dimensionSource = this.map.getSource('floorplan-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        }
    }

    /**
     * Generate dimensions for completed structure footprint
     */
    generateStructureDimensions() {
        if (!this.state.geojsonPolygon || !this.map) return;

        const coordinates = this.state.geojsonPolygon.geometry.coordinates[0];
        const dimensionFeatures = [];

        // Generate dimensions for each edge of the completed structure
        for (let i = 0; i < coordinates.length - 1; i++) {
            const start = coordinates[i];
            const end = coordinates[i + 1];
            const distance = this.calculateDistance(start[0], start[1], end[0], end[1]);

            if (distance > 0) {
                const midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: midpoint
                    },
                    properties: {
                        distance: `${distance.toFixed(1)}m`,
                        type: 'structure-dimension',
                        edge_index: i
                    }
                });
            }
        }

        // Add or update the structure dimensions source
        const sourceId = 'structure-dimensions';
        if (this.map.getSource(sourceId)) {
            this.map.getSource(sourceId).setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        } else {
            this.map.addSource(sourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: dimensionFeatures
                }
            });
        }

        // Add dimension labels layer if it doesn't exist
        const layerId = 'structure-dimension-labels';
        if (!this.map.getLayer(layerId)) {
            this.map.addLayer({
                id: layerId,
                type: 'symbol',
                source: sourceId,
                layout: {
                    'text-field': ['get', 'distance'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-size': 12,
                    'text-offset': [0, -1],
                    'text-anchor': 'center',
                    'text-allow-overlap': true,
                    'text-ignore-placement': true,
                    'visibility': 'visible'
                },
                paint: {
                    'text-color': this.config.drawingStyle.strokeColor,
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2
                }
            });
        }

        this.info('Structure footprint dimensions generated:', dimensionFeatures.length, 'dimensions');
    }

    /**
     * Clear drawing sources and layers
     */
    clearDrawingSources() {
        const layersToRemove = [
            this.config.layerIds.drawing,
            this.config.layerIds.drawing + '-line',
            this.config.layerIds.drawingPoints,
            this.config.layerIds.previewLine,
            this.config.layerIds.previewPolygon,
            this.config.layerIds.previewPolygon + '-line',
            'floorplan-dimension-labels'
        ];

        const sourcesToRemove = [
            this.config.sourceIds.drawing,
            this.config.sourceIds.drawingPoints,
            this.config.sourceIds.previewLine,
            this.config.sourceIds.previewPolygon,
            'floorplan-dimensions'
        ];

        layersToRemove.forEach(layerId => {
            if (this.map.getLayer(layerId)) {
                this.map.removeLayer(layerId);
            }
        });

        sourcesToRemove.forEach(sourceId => {
            if (this.map.getSource(sourceId)) {
                this.map.removeSource(sourceId);
            }
        });
    }

    /**
     * Save drawn floor plan
     */
    async saveDrawnFloorplan() {
        try {
            // Store in localStorage
            const floorplanData = {
                type: 'drawn',
                geojsonPolygon: this.state.geojsonPolygon,
                timestamp: Date.now()
            };

            localStorage.setItem('drawnFloorplan', JSON.stringify(floorplanData));

            // Also save to backend if available
            if (window.apiClient) {
                await window.apiClient.post('/update-floorplan-transform', {
                    geojson_polygon: this.state.geojsonPolygon,
                    transform: {
                        method: 'drawn',
                        timestamp: Date.now()
                    }
                });
            }

            this.info('Drawn floor plan saved');
        } catch (error) {
            this.error('Failed to save drawn floor plan', error);
        }
    }

    /**
     * Clear stored floor plan data to ensure fresh session
     */
    clearStoredFloorplanData() {
        try {
            // Clear localStorage
            localStorage.removeItem('drawnFloorplan');

            // Clear any session data via API if available
            if (window.apiClient) {
                window.apiClient.post('/clear-floorplan', {}).catch(error => {
                    this.debug('Failed to clear server floor plan data', error);
                });
            }

            this.info('Cleared stored floor plan data for fresh session');
        } catch (error) {
            this.error('Failed to clear stored floor plan data', error);
        }
    }

    /**
     * Load drawn floor plan from storage
     */
    loadDrawnFloorplan() {
        try {
            const saved = localStorage.getItem('drawnFloorplan');
            if (saved) {
                const data = JSON.parse(saved);
                if (data.geojsonPolygon) {
                    this.state.geojsonPolygon = data.geojsonPolygon;
                    this.displayFloorplanOnMap();
                    this.info('Loaded saved drawn floor plan');
                    return true;
                }
            }
        } catch (error) {
            this.error('Failed to load drawn floor plan', error);
        }
        return false;
    }

    /**
     * Update drawing button state
     */
    updateDrawingButton(isActive) {
        const button = document.getElementById('drawFloorplanButton');
        if (button) {
            if (isActive) {
                button.textContent = 'Stop Drawing';
                button.classList.add('active');
                button.style.backgroundColor = '#dc3545';
            } else {
                button.textContent = 'Draw Structure Footprint';
                button.classList.remove('active');
                button.style.backgroundColor = '';
            }
            this.debug('Drawing button updated:', { isActive, text: button.textContent });
        } else {
            this.error('Cannot update drawing button - element not found');
        }
    }

    /**
     * Update floorplan button visibility and states
     */
    updateFloorplanButtons() {
        const drawBtn = document.getElementById('drawFloorplanButton');
        const clearBtn = document.getElementById('clearFloorplanButton');
        const lockBtn = document.getElementById('lockFloorplanButton');
        const actionButtonsContainer = document.querySelector('.floorplan-action-buttons');

        const hasFloorplan = this.state.geojsonPolygon !== null;

        if (hasFloorplan) {
            // Show action buttons when floorplan exists
            if (actionButtonsContainer) {
                actionButtonsContainer.style.display = 'flex';
            }

            // Show clear and lock buttons
            if (clearBtn) {
                clearBtn.style.display = 'inline-block';
            }
            if (lockBtn) {
                lockBtn.style.display = 'inline-block';
                // Update lock button state
                if (this.state.isLocked) {
                    lockBtn.classList.add('locked');
                    lockBtn.innerHTML = '🔒';
                    lockBtn.title = 'Unlock structure footprint';
                } else {
                    lockBtn.classList.remove('locked');
                    lockBtn.innerHTML = '🔓';
                    lockBtn.title = 'Lock structure footprint';
                }
            }

            // Hide draw button when structure exists
            if (drawBtn) {
                drawBtn.style.display = 'none';
            }

        } else {
            // Hide action buttons when no floorplan
            if (actionButtonsContainer) {
                actionButtonsContainer.style.display = 'none';
            }

            // Hide clear and lock buttons
            if (clearBtn) {
                clearBtn.style.display = 'none';
            }
            if (lockBtn) {
                lockBtn.style.display = 'none';
            }

            // Show draw button when no structure
            if (drawBtn) {
                drawBtn.style.display = 'inline-block';
            }
        }

        this.debug('Floorplan buttons updated:', { 
            hasFloorplan, 
            isLocked: this.state.isLocked,
            drawBtnVisible: !hasFloorplan,
            clearBtnVisible: hasFloorplan,
            lockBtnVisible: hasFloorplan
        });
    }

    /**
     * Show/hide 3D building controls based on floor plan state
     */
    check3DControlsAvailability() {
        // 3D building controls removed - no longer available
        this.state.building3d.isEnabled = false;
    }

    /**
     * Update structure placement legend
     */
    updateStructureLegend(show) {
        const legendContent = document.getElementById('legendContent');
        if (!legendContent) return;

        // Find or create structure placement legend item
        let structureItem = legendContent.querySelector('.legend-structure-item');

        if (show) {
            if (!structureItem) {
                structureItem = document.createElement('div');
                structureItem.className = 'legend-item legend-structure-item';
                structureItem.innerHTML = `
                    <div class="legend-color" style="background-color: ${this.config.drawingStyle.fillColor}; opacity: 0.3; border: 1px solid ${this.config.drawingStyle.strokeColor};"></div>
                    <span class="legend-label">Structure Placement</span>
                `;
                legendContent.appendChild(structureItem);
            }
            structureItem.style.display = 'flex';
            this.info('Structure placement added to legend');
        } else if (structureItem) {
            structureItem.style.display = 'none';
            this.info('Structure placement removed from legend');
        }
    }

    handleMouseMove(event) {
        if (this.state.isDrawing) {
            this.handleDrawingMouseMove(event);
            return;
        }

        if (this.state.isLocked) return;
        this.updateInteraction(event);
    }

    handleMouseUp(event) {
        this.stopInteraction();
    }

    handleRightClick(event) {
        event.preventDefault();
        if (this.state.geojsonPolygon && !this.state.isLocked) {
            this.showContextMenu(event);
        }
    }

    handleKeyDown(event) {
        switch (event.key) {
            case 'Escape':
                this.stopInteraction();
                break;
            case 'l':
            case 'L':
                this.toggleLock();
                break;
        }
    }

    handleKeyUp(event) {
        // Handle key releases if needed
    }

    /**
     * Start interaction based on modifier keys
     */
    startInteraction(event) {
        if (event.originalEvent.ctrlKey || event.originalEvent.metaKey) {
            this.startRotation(event);
        } else if (event.originalEvent.shiftKey) {
            this.startScaling(event);
        } else {
            this.startDragging(event);
        }
    }

    /**
     * Update current interaction
     */
    updateInteraction(event) {
        if (this.interaction.isDragging) {
            this.updateDragging(event);
        } else if (this.interaction.isRotating) {
            this.updateRotation(event);
        } else if (this.interaction.isScaling) {
            this.updateScaling(event);
        }
    }

    /**
     * Stop all interactions
     */
    stopInteraction() {
        this.interaction.isDragging = false;
        this.interaction.isRotating = false;
        this.interaction.isScaling = false;
        this.map.getCanvas().style.cursor = '';
        this.saveTransformState();
        this.info('Stopped floor plan manipulation');
    }

    /**
     * Dragging operations
     */
    startDragging(event) {
        this.interaction.isDragging = true;
        this.interaction.dragStart = event.lngLat;
        this.map.getCanvas().style.cursor = 'move';
        this.info('Started dragging floor plan');
    }

    updateDragging(event) {
        if (!this.interaction.isDragging || !this.interaction.dragStart) return;

        const deltaLng = event.lngLat.lng - this.interaction.dragStart.lng;
        const deltaLat = event.lngLat.lat - this.interaction.dragStart.lat;

        this.translatePolygon(deltaLng, deltaLat);
        this.updateMapDisplay();
        this.interaction.dragStart = event.lngLat;
    }

    /**
     * Rotation operations
     */
    startRotation(event) {
        this.interaction.isRotating = true;
        this.interaction.rotationCenter = this.getPolygonCenter(this.state.geojsonPolygon);
        this.interaction.initialRotation = this.calculateAngle(this.interaction.rotationCenter, event.lngLat);
        this.map.getCanvas().style.cursor = 'grab';
        this.info('Started rotating floor plan');
    }

    updateRotation(event) {
        if (!this.interaction.isRotating || !this.interaction.rotationCenter) return;

        const currentAngle = this.calculateAngle(this.interaction.rotationCenter, event.lngLat);
        const rotationDelta = (currentAngle - this.interaction.initialRotation) * this.config.rotationSensitivity;

        this.rotatePolygon(rotationDelta);
        this.updateMapDisplay();
    }

    /**
     * Scaling operations
     */
    startScaling(event) {
        this.interaction.isScaling = true;
        this.interaction.scalingStart = event.lngLat;
        this.interaction.rotationCenter = this.getPolygonCenter(this.state.geojsonPolygon);
        this.map.getCanvas().style.cursor = 'nw-resize';
        this.info('Started scaling floor plan');
    }

    updateScaling(event) {
        if (!this.interaction.isScaling || !this.interaction.scalingStart || !this.interaction.rotationCenter) return;

        const startDistance = this.calculateDistance(this.interaction.rotationCenter, this.interaction.scalingStart);
        const currentDistance = this.calculateDistance(this.interaction.rotationCenter, event.lngLat);
        const scaleFactor = currentDistance / startDistance;

        this.scalePolygon(scaleFactor);
        this.updateMapDisplay();
        this.interaction.scalingStart = event.lngLat;
    }

    /**
     * Geometric transformations
     */
    translatePolygon(deltaLng, deltaLat) {
        const coords = this.state.geojsonPolygon.geometry.coordinates[0];
        this.state.geojsonPolygon.geometry.coordinates[0] = coords.map(coord => [
            coord[0] + deltaLng,
            coord[1] + deltaLat
        ]);
    }

    rotatePolygon(rotationDelta) {
        const center = this.interaction.rotationCenter;
        const coords = this.state.geojsonPolygon.geometry.coordinates[0];

        this.state.geojsonPolygon.geometry.coordinates[0] = coords.map(coord => {
            const x = coord[0] - center.lng;
            const y = coord[1] - center.lat;

            const rotatedX = x * Math.cos(rotationDelta) - y * Math.sin(rotationDelta);
            const rotatedY = x * Math.sin(rotationDelta) + y * Math.cos(rotationDelta);

            return [rotatedX + center.lng, rotatedY + center.lat];
        });

        this.state.currentTransform.rotation += rotationDelta;
        this.state.geojsonPolygon.properties.rotation = this.state.currentTransform.rotation;
    }

    scalePolygon(scaleFactor) {
        const center = this.interaction.rotationCenter;
        const coords = this.state.geojsonPolygon.geometry.coordinates[0];

        this.state.geojsonPolygon.geometry.coordinates[0] = coords.map(coord => {
            const x = (coord[0] - center.lng) * scaleFactor;
            const y = (coord[1] - center.lat) * scaleFactor;

            return [x + center.lng, y + center.lat];
        });

        this.state.currentTransform.scale *= scaleFactor;
        this.state.geojsonPolygon.properties.scale = this.state.currentTransform.scale;
    }

    /**
     * Toggle lock state
     */
    toggleLock() {
        this.state.isLocked = !this.state.isLocked;
        if (this.state.geojsonPolygon) {
            this.state.geojsonPolygon.properties.locked = this.state.isLocked;
        }

        this.updateUI('info', this.state.isLocked ? 'Floor plan locked' : 'Floor plan unlocked');
        this.check3DControlsAvailability();
        this.saveTransformState();
        this.info(`Floor plan ${this.state.isLocked ? 'locked' : 'unlocked'}`);
    }

    /**
     * Save transform state to server
     */
    async saveTransformState() {
        if (!this.state.geojsonPolygon) return;

        try {
            const center = this.getPolygonCenter(this.state.geojsonPolygon);
            const transform = {
                position: center,
                rotation: this.state.currentTransform.rotation,
                scale: this.state.currentTransform.scale,
                locked: this.state.isLocked
            };

            await window.apiClient.post('/update-floorplan-transform', {
                transform: transform,
                geojson_polygon: this.state.geojsonPolygon
            });

            this.debug('Transform state saved', transform);

        } catch (error) {
            this.error('Failed to save transform state', error);
        }
    }

    /**
     * Update map display
     */
    updateMapDisplay() {
        const polygonSource = this.map.getSource(this.config.sourceIds.polygon);
        if (polygonSource) {
            polygonSource.setData(this.state.geojsonPolygon);
        }

        const center = this.getPolygonCenter(this.state.geojsonPolygon);
        const centerSource = this.map.getSource(this.config.sourceIds.center);
        if (centerSource) {
            centerSource.setData({
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [center.lng, center.lat]
                }
            });
        }
    }

    /**
     * Show context menu
     */
    showContextMenu(event) {
        const menu = this.createContextMenu(event);
        document.body.appendChild(menu);

        // Auto-remove menu
        setTimeout(() => {
            document.addEventListener('click', function removeMenu() {
                if (document.body.contains(menu)) {
                    document.body.removeChild(menu);
                }
                document.removeEventListener('click', removeMenu);
            });
        }, 0);
    }

    /**
     * Create context menu element
     */
    createContextMenu(event) {
        const menu = document.createElement('div');
        menu.className = 'floorplan-context-menu';
        menu.style.cssText = `
            position: fixed;
            top: ${event.originalEvent.clientY}px;
            left: ${event.originalEvent.clientX}px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 10000;
            padding: 8px 0;
            min-width: 140px;
        `;

        const lockOption = this.createMenuOption(
            this.state.isLocked ? 'Unlock' : 'Lock Position',
            () => this.toggleLock()
        );

        const drawNewOption = this.createMenuOption(
            'Draw New Structure',
            () => this.startDrawingMode(),
            '#28a745'
        );

        const removeOption = this.createMenuOption(
            'Remove Structure',
            () => this.removeFloorplan(),
            '#d32f2f'
        );

        menu.appendChild(lockOption);
        menu.appendChild(drawNewOption);
        menu.appendChild(removeOption);

        return menu;
    }

    /**
     * Create context menu option
     */
    createMenuOption(text, onClick, color = null) {
        const option = document.createElement('div');
        option.textContent = text;
        option.style.cssText = `
            padding: 8px 16px; 
            cursor: pointer; 
            ${color ? `color: ${color};` : ''}
        `;
        option.onmouseover = () => option.style.background = '#f0f0f0';
        option.onmouseout = () => option.style.background = '';
        option.onclick = () => {
            onClick();
            document.body.removeChild(option.parentElement);
        };
        return option;
    }

    /**
     * Remove floor plan
     */
    async removeFloorplan() {
        try {
            await window.apiClient.post('/clear-floorplan', {});
            this.removeFloorplanFromMap();
            this.resetState();
            this.updateUI('info', 'Floor plan removed');
            this.info('Floor plan removed');
        } catch (error) {
            this.error('Failed to remove floor plan', error);
        }
    }

    /**
     * Reset internal state
     */
    resetState() {
        this.state.floorplanData = null;
        this.state.geojsonPolygon = null;
        this.state.isLocked = false;
        this.state.isDrawing = false;
        this.state.drawingPoints = [];
        this.state.currentTransform = {
            position: null,
            rotation: 0,
            scale: 1.0
        };
        this.state.building3d = {
            isEnabled: false,
            storeys: 2,
            storeyHeight: 3.0,
            totalHeight: 6.0,
            isVisible: false
        };

        this.interaction = {
            isDragging: false,
            isRotating: false,
            isScaling: false,
            dragStart: null,
            rotationCenter: null,
            initialRotation: 0,
            scalingStart: null
        };

        this.check3DControlsAvailability();
        this.updateStructureLegend(false); // Remove from legend when resetting
    }

    /**
     * Handle processing errors
     */
    handleProcessingError(error) {
        this.error('Floor plan processing failed', error);
        this.updateUI('error', `Processing failed: ${error.message}`);
    }

    /**
     * Utility methods
     */
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    getPolygonCenter(polygon) {
        const coords = polygon.geometry.coordinates[0];
        const count = coords.length - 1; // Exclude closing point

        const center = coords.slice(0, count).reduce(
            (acc, coord) => ({
                lng: acc.lng + coord[0],
                lat: acc.lat + coord[1]
            }),
            { lng: 0, lat: 0 }
        );

        return {
            lng: center.lng / count,
            lat: center.lat / count
        };
    }

    calculateAngle(center, point) {
        return Math.atan2(point.lat - center.lat, point.lng - center.lng);
    }

    calculateDistance(lng1, lat1, lng2, lat2) {
        if (arguments.length === 2) {
            // Handle point objects (existing usage)
            const point1 = arguments[0];
            const point2 = arguments[1];
            const dx = point2.lng - point1.lng;
            const dy = point2.lat - point1.lat;
            return Math.sqrt(dx * dx + dy * dy);
        }

        // Handle coordinate pairs for distance calculation in meters
        const R = 6371000; // Earth's radius in meters
        const lat1Rad = lat1 * Math.PI / 180;
        const lat2Rad = lat2 * Math.PI / 180;
        const deltaLat = (lat2 - lat1) * Math.PI / 180;
        const deltaLng = (lng2 - lng1) * Math.PI / 180;

        const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                 Math.cos(lat1Rad) * Math.cos(lat2Rad) *
                 Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        const distance = R * c;
        return distance;
    }

    boundariesToCoordinates(boundaries) {
        if (!boundaries || boundaries.length === 0) {
            return [];
        }

        const bounds = this.getBounds(boundaries);
        const { width, height } = this.getDimensions(bounds);

        return boundaries.map(([x, y]) => ({
            x: width > 0 ? (x - bounds.minX) / width : 0,
            y: height > 0 ? (y - bounds.minY) / height : 0
        }));
    }

    getBounds(boundaries) {
        const xs = boundaries.map(point => point[0]);
        const ys = boundaries.map(point => point[1]);

        return {
            minX: Math.min(...xs),
            maxX: Math.max(...xs),
            minY: Math.min(...ys),
            maxY: Math.max(...ys)
        };
    }

    getDimensions(bounds) {
        return {
            width: bounds.maxX - bounds.minX,
            height: bounds.maxY - bounds.minY
        };
    }

    calculateMetrics(boundaries) {
        if (!boundaries || boundaries.length < 3) {
            return { area: 0, perimeter: 0, boundary_points: 0 };
        }

        const perimeter = this.calculatePerimeter(boundaries);
        const area = this.calculateArea(boundaries);

        return {
            area: area,
            perimeter: perimeter,
            boundary_points: boundaries.length,
            complexity_score: boundaries.length / 4
        };
    }

    calculatePerimeter(boundaries) {
        let perimeter = 0;
        for (let i = 0; i < boundaries.length; i++) {
            const current = boundaries[i];
            const next = boundaries[(i + 1) % boundaries.length];
            const dx = next[0] - current[0];
            const dy = next[1] - current[1];
            perimeter += Math.sqrt(dx * dx + dy * dy);
        }
        return perimeter;
    }

    calculateArea(boundaries) {
        let area = 0;
        for (let i = 0; i < boundaries.length; i++) {
            const current = boundaries[i];
            const next = boundaries[(i + 1) % boundaries.length];
            area += current[0] * next[1] - next[0] * current[1];
        }
        return Math.abs(area) / 2;
    }

    /**
     * UI Management
     */
    resetUploadButtonState() {
        const uploadButton = document.getElementById('uploadFloorplanButton');
        if (uploadButton) {
            uploadButton.textContent = 'Select Floor Plan';
            uploadButton.disabled = false;
        }
    }

    setUploadingState(isUploading, message = null) {
        this.state.isUploading = isUploading;

        const uploadButton = document.getElementById('uploadFloorplanButton');
        const floorplanInput = document.getElementById('floorplanInput');

        if (isUploading) {
            if (uploadButton) {
                uploadButton.textContent = message || 'Processing...';
                uploadButton.disabled = true;
            }
            if (floorplanInput) {
                floorplanInput.disabled = true;
            }
        } else {
            if (uploadButton) {
                uploadButton.textContent = 'Select Floor Plan';
                uploadButton.disabled = false;
            }
            if (floorplanInput) {
                floorplanInput.disabled = false;
                floorplanInput.value = '';
            }
        }
    }

    updateUI(type, message) {
        const statusElement = document.querySelector('.floorplan-status');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `floorplan-status ${type}`;
            statusElement.style.display = 'block';
        }

        const uploadButton = document.getElementById('uploadFloorplanButton');
        if (uploadButton && this.state.floorplanData?.success) {
            const method = this.state.floorplanData.processing_method || 'server';
            uploadButton.innerHTML = `
                <span style="color: #155724;">✓ Floor plan loaded (${method})</span>
                <br><small>Click to select new plan</small>
            `;
        }
    }

    /**
     * Add final dimensions for the completed structure
     */
    addFinalDimensions() {
        if (!this.state.geojsonPolygon) return;

        const coords = this.state.geojsonPolygon.geometry.coordinates[0];
        const dimensionFeatures = [];

        // Group collinear points into edges to avoid showing dimensions for every point segment
        const edges = this.groupPointsIntoEdges(coords.slice(0, -1)); // Remove duplicate closing point

        // Add dimensions for each detected edge
        edges.forEach(edge => {
            const distance = this.calculateDistance(edge.start[0], edge.start[1], edge.end[0], edge.end[1]);

            // Only add dimension if distance is greater than 0
            if (distance > 0) {
                const midpoint = [(edge.start[0] + edge.end[0]) / 2, (edge.start[1] + edge.end[1]) / 2];
                dimensionFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'Point',
                        coordinates: midpoint
                    },
                    properties: {
                        distance: `${distance.toFixed(1)}m`,
                        type: 'final-dimension'
                    }
                });
            }
        });

        // Create or update the dimensions source
        if (!this.map.getSource('floorplan-dimensions')) {
            this.map.addSource('floorplan-dimensions', {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: dimensionFeatures
                }
            });
        } else {
            const dimensionSource = this.map.getSource('floorplan-dimensions');
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        }

        // Add structure dimension labels if they don't exist
        if (!this.map.getLayer('floorplan-dimension-labels')) {
            this.map.addLayer({
                id: 'floorplan-dimension-labels',
                type: 'symbol',
                source: 'floorplan-dimensions',
                layout: {
                    'text-field': ['get', 'distance'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-size': 12,
                    'text-offset': [0, -1],
                    'text-anchor': 'center',
                    'text-allow-overlap': true,
                    'text-ignore-placement': true,
                    'visibility': 'visible'
                },
                paint: {
                    'text-color': this.config.drawingStyle.strokeColor,
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2
                }
            });
        }

        // Also add structure/footprint dimension alias layers for comprehensive control
        if (!this.map.getLayer('structure-dimension-labels')) {
            this.map.addLayer({
                id: 'structure-dimension-labels',
                type: 'symbol',
                source: 'floorplan-dimensions',
                layout: {
                    'text-field': ['get', 'distance'],
                    'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
                    'text-size': 12,
                    'text-offset': [0, -1],
                    'text-anchor': 'center',
                    'text-allow-overlap': true,
                    'text-ignore-placement': true,
                    'visibility': 'visible'
                },
                paint: {
                    'text-color': this.config.drawingStyle.strokeColor,
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2
                }
            });
        }

        this.debug('Final dimensions added for completed structure:', dimensionFeatures.length, 'edges from', coords.length - 1, 'points');
    }

    /**
     * Group consecutive collinear points into single edges
     */
    groupPointsIntoEdges(points) {
        if (points.length < 2) return [];

        const edges = [];
        let edgeStart = points[0];

        for (let i = 1; i < points.length; i++) {
            const current = points[i];
            const next = points[(i + 1) % points.length]; // Wrap around for the last point

            // Check if the next point continues the same line (is collinear)
            const isCollinear = this.arePointsCollinear(edgeStart, current, next);

            // If not collinear or we're at the last point, finish this edge
            if (!isCollinear || i === points.length - 1) {
                edges.push({
                    start: edgeStart,
                    end: current
                });
                edgeStart = current;
            }
        }

        // Handle the closing edge from last point back to first
        if (edges.length > 0) {
            const lastEdge = edges[edges.length - 1];
            const firstPoint = points[0];

            // Check if we need to close back to the first point
            if (lastEdge.end[0] !== firstPoint[0] || lastEdge.end[1] !== firstPoint[1]) {
                edges.push({
                    start: lastEdge.end,
                    end: firstPoint
                });
            }
        }

        return edges;
    }

    /**
     * Check if three points are approximately collinear
     */
    arePointsCollinear(p1, p2, p3, tolerance = 0.0001) {
        // Calculate the cross product to determine if points are collinear
        const crossProduct = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0]);
        return Math.abs(crossProduct) < tolerance;
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.removeEventListeners();
        this.removeFloorplanFromMap();
        this.resetState();
        this.info('FloorplanManager cleaned up');
    }

    removeEventListeners() {
        // Remove file handlers
        this.removeFileHandlers();

        // Remove map handlers (would need to store references to remove properly)
        // For now, we'll leave them as they'll be cleaned up when the map is destroyed
    }
}

// Export for module system
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FloorplanManager;
}

// Make available globally for template usage
window.FloorplanManager = FloorplanManager;