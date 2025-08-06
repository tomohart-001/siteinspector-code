/**
 * Site Boundary Manager
 * Handles polygon drawing, validation, and site boundary operations
 */

class SiteBoundaryManager extends BaseManager {
    constructor(map, draw) {
        super('SiteBoundaryManager');
        this.map = map;
        this.draw = draw;
        this.sitePolygon = null;
        this.polygonEdges = [];
        this.isLocked = false;
        this.sitePolygonId = null;
        this.sitePolygonCoords = null;
        this.lockedFeatureId = null;

        // Enhanced drawing state
        this.isDrawing = false;
        this.drawingPoints = [];
        this.previewSourceId = 'boundary-drawing-preview';
        this.pointsSourceId = 'boundary-drawing-points';
    }

    async initialize() {
        this.info('Initializing Site Boundary Manager...');
        this.setupEventListeners();

        // Auto-load existing boundary if available
        await this.loadExistingSiteBoundary();

        this.info('Site Boundary Manager initialized successfully');
    }

    setupEventListeners() {
        // Listen for drawing events
        this.map.on('draw.create', (e) => this.handlePolygonCreated(e));
        this.map.on('draw.update', (e) => this.handlePolygonUpdated(e));
        this.map.on('draw.delete', (e) => this.handlePolygonDeleted(e));

        // Listen for drawing mode changes
        this.map.on('draw.modechange', (e) => this.handleModeChange(e));

        // Setup UI event handlers
        this.setupUIEventHandlers();

        // Setup enhanced drawing visualization
        this.setupDrawingVisualization();

        this.info('Event listeners setup completed');
    }

    setupUIEventHandlers() {
        // Draw Polygon Button
        const drawPolygonBtn = document.getElementById('drawPolygonButton');
        if (drawPolygonBtn) {
            drawPolygonBtn.addEventListener('click', () => this.toggleDrawingMode());
        }

        // Stop Drawing Button
        const stopDrawingBtn = document.getElementById('stopDrawingButton');
        if (stopDrawingBtn) {
            stopDrawingBtn.addEventListener('click', () => this.stopDrawingMode());
        }

        // Clear Boundary Button (in drawing row)
        const clearBoundaryBtn = document.getElementById('clearBoundaryButton');
        if (clearBoundaryBtn) {
            clearBoundaryBtn.addEventListener('click', () => this.clearBoundary());
        }

        // Clear Boundary Button (in action buttons area)
        const clearBoundaryBtn2 = document.getElementById('clearBoundaryButton2');
        if (clearBoundaryBtn2) {
            clearBoundaryBtn2.addEventListener('click', () => this.clearBoundary());
        }

        // Confirm Boundary Button
        const confirmBoundaryBtn = document.getElementById('confirmBoundaryButton');
        if (confirmBoundaryBtn) {
            confirmBoundaryBtn.addEventListener('click', () => this.confirmBoundary());
        }

        // Lock Boundary Button
        const lockBoundaryBtn = document.getElementById('lockBoundaryButton');
        if (lockBoundaryBtn) {
            lockBoundaryBtn.addEventListener('click', () => this.toggleBoundaryLock());
        }

        this.info('UI event handlers setup completed');
    }

    setupDrawingVisualization() {
        // Add sources for drawing visualization
        if (!this.map.getSource(this.previewSourceId)) {
            this.map.addSource(this.previewSourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });
        }

        if (!this.map.getSource(this.pointsSourceId)) {
            this.map.addSource(this.pointsSourceId, {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });
        }

        // Add source for dimension labels
        if (!this.map.getSource('boundary-dimensions')) {
            this.map.addSource('boundary-dimensions', {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });
        }

        // Add preview line layer
        if (!this.map.getLayer('boundary-preview-line')) {
            this.map.addLayer({
                id: 'boundary-preview-line',
                type: 'line',
                source: this.previewSourceId,
                paint: {
                    'line-color': '#007cbf',
                    'line-width': 2,
                    'line-dasharray': [4, 4],
                    'line-opacity': 0.8
                },
                filter: ['==', ['get', 'type'], 'preview-line']
            });
        }

        // Add preview polygon fill layer
        if (!this.map.getLayer('boundary-preview-fill')) {
            this.map.addLayer({
                id: 'boundary-preview-fill',
                type: 'fill',
                source: this.previewSourceId,
                paint: {
                    'fill-color': '#007cbf',
                    'fill-opacity': 0.15
                },
                filter: ['==', ['get', 'type'], 'preview-polygon']
            });
        }

        // Add points layer with markers
        if (!this.map.getLayer('boundary-drawing-points')) {
            this.map.addLayer({
                id: 'boundary-drawing-points',
                type: 'circle',
                source: this.pointsSourceId,
                paint: {
                    'circle-radius': 6,
                    'circle-color': '#007cbf',
                    'circle-stroke-color': '#ffffff',
                    'circle-stroke-width': 2,
                    'circle-opacity': 0.9
                }
            });
        }

        // Add dimension labels layer
        if (!this.map.getLayer('boundary-dimension-labels')) {
            this.map.addLayer({
                id: 'boundary-dimension-labels',
                type: 'symbol',
                source: 'boundary-dimensions',
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
                    'text-color': '#007cbf',
                    'text-halo-color': '#ffffff',
                    'text-halo-width': 2
                }
            });
        }

        // Setup mouse move listener for live preview
        this.mouseMoveHandler = (e) => this.handleMouseMove(e);
        this.map.on('mousemove', this.mouseMoveHandler);

        this.clickHandler = (e) => this.handleMapClick(e);
        this.map.on('click', this.clickHandler);
    }

    handleModeChange(e) {
        if (e.mode === 'draw_polygon') {
            this.isDrawing = true;
            this.drawingPoints = [];
            this.info('Polygon drawing mode activated');
        } else {
            if (this.isDrawing) {
                this.isDrawing = false;
                this.clearDrawingVisualization();
                this.info('Polygon drawing mode deactivated');
            }
        }
    }

    handleMouseMove(e) {
        // Only show preview during drawing mode with MapboxDraw
        const drawMode = this.draw.getMode();
        if (drawMode !== 'draw_polygon' || this.drawingPoints.length === 0) {
            return;
        }

        const currentPoint = [e.lngLat.lng, e.lngLat.lat];
        this.updatePreviewLine(currentPoint);
    }

    handleMapClick(e) {
        // Only track points during draw_polygon mode
        const drawMode = this.draw.getMode();
        if (drawMode !== 'draw_polygon') return;

        // Prevent adding the same point twice
        const newPoint = [e.lngLat.lng, e.lngLat.lat];
        const lastPoint = this.drawingPoints[this.drawingPoints.length - 1];

        if (lastPoint && Math.abs(lastPoint[0] - newPoint[0]) < 0.000001 && 
            Math.abs(lastPoint[1] - newPoint[1]) < 0.000001) {
            return;
        }

        this.drawingPoints.push(newPoint);
        this.updatePointsVisualization();

        this.info(`Drawing point ${this.drawingPoints.length} added`);
    }

    updatePreviewLine(currentPoint) {
        if (this.drawingPoints.length === 0) return;

        let features = [];
        let dimensionFeatures = [];

        // Create line from last point to current mouse position
        if (this.drawingPoints.length >= 1) {
            const lastPoint = this.drawingPoints[this.drawingPoints.length - 1];
            features.push({
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: [lastPoint, currentPoint]
                },
                properties: { type: 'preview-line' }
            });

            // Add dimension for the preview line
            const distance = this.calculateDistance(lastPoint[0], lastPoint[1], currentPoint[0], currentPoint[1]);
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

        // Add dimensions for all existing edges
        for (let i = 0; i < this.drawingPoints.length - 1; i++) {
            const start = this.drawingPoints[i];
            const end = this.drawingPoints[i + 1];
            const distance = this.calculateDistance(start[0], start[1], end[0], end[1]);
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

        // Create preview polygon if we have 2+ points
        if (this.drawingPoints.length >= 2) {
            const previewCoords = [...this.drawingPoints, currentPoint, this.drawingPoints[0]];
            features.push({
                type: 'Feature',
                geometry: {
                    type: 'Polygon',
                    coordinates: [previewCoords]
                },
                properties: { type: 'preview-polygon' }
            });

            // Add dimension for closing edge (from current point back to first point)
            if (this.drawingPoints.length >= 3) {
                const firstPoint = this.drawingPoints[0];
                const closingDistance = this.calculateDistance(currentPoint[0], currentPoint[1], firstPoint[0], firstPoint[1]);
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

        // Update preview features
        const source = this.map.getSource(this.previewSourceId);
        if (source) {
            source.setData({
                type: 'FeatureCollection',
                features: features
            });
        }

        // Update dimension features
        const dimensionSource = this.map.getSource('boundary-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        }
    }

    updatePointsVisualization() {
        const pointFeatures = this.drawingPoints.map((point, index) => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: point
            },
            properties: {
                index: index,
                type: 'drawing-point'
            }
        }));

        const source = this.map.getSource(this.pointsSourceId);
        if (source) {
            source.setData({
                type: 'FeatureCollection',
                features: pointFeatures
            });
        }
    }

    clearDrawingVisualization() {
        const previewSource = this.map.getSource(this.previewSourceId);
        if (previewSource) {
            previewSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        const pointsSource = this.map.getSource(this.pointsSourceId);
        if (pointsSource) {
            pointsSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        const dimensionSource = this.map.getSource('boundary-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        this.drawingPoints = [];
    }

    handlePolygonCreated(e) {
        try {
            if (!e.features || e.features.length === 0) {
                this.error('No features in polygon creation event');
                return;
            }

            const feature = e.features[0];
            if (!feature || !feature.geometry || !feature.geometry.coordinates) {
                this.error('Invalid feature geometry in polygon creation');
                return;
            }

            this.sitePolygon = feature;
            this.siteBoundary = feature;

            // Clear drawing visualization
            this.clearDrawingVisualization();

            // Validate and calculate metrics
            const coordinates = feature.geometry.coordinates[0];
            if (!coordinates || coordinates.length < 4) {
                this.error('Invalid coordinates in created polygon');
                return;
            }

            const area = this.calculatePolygonArea(coordinates);
            const perimeter = this.calculatePolygonPerimeter(coordinates);

            // Validate calculated values
            if (isNaN(area) || isNaN(perimeter) || area <= 0) {
                this.warn('Invalid area or perimeter calculated, using fallback values');
            }

            // Store polygon edges for setbacks
            this.polygonEdges = this.calculatePolygonEdges(coordinates);

            // Calculate terrain bounding box (50m buffer)
            const terrainBounds = this.calculateTerrainBounds(coordinates);

            // Add final dimensions to the completed polygon
            this.showFinalDimensions(coordinates);

            this.info(`Site boundary created - Area: ${area.toFixed(2)} m², Perimeter: ${perimeter.toFixed(2)} m`);

            // Update UI safely
            this.updateBoundaryDisplay(area, perimeter, coordinates.length - 1);

            // Switch to select mode safely
            if (this.draw && this.draw.changeMode) {
                this.draw.changeMode('simple_select');
            }
            this.isDrawing = false;

            // Update buttons safely
            this.updateButtonStates(true);

            // Emit boundary created event with terrain bounds
            if (window.eventBus && window.eventBus.emit) {
                this.info('Emitting site-boundary-created event with edges:', this.polygonEdges.length);
                window.eventBus.emit('site-boundary-created', {
                    coordinates: coordinates,
                    area: area,
                    perimeter: perimeter,
                    edges: this.polygonEdges,
                    terrainBounds: terrainBounds
                });
            }

        } catch (error) {
            this.error('Error handling polygon creation:', error);
            this.clearDrawingVisualization();
        }
    }

    updateButtonStates(polygonCreated = false, boundaryExists = false) {
        const drawBtn = document.getElementById('drawPolygonButton');
        const confirmBtn = document.getElementById('confirmBoundaryButton');
        const lockBtn = document.getElementById('lockBoundaryButton');
        const clearBtn = document.getElementById('clearBoundaryButton');
        const clearBtn2 = document.getElementById('clearBoundaryButton2');

        if (drawBtn) {
            drawBtn.textContent = 'Draw Site Boundary';
            drawBtn.classList.remove('active');
        }

        if (polygonCreated || boundaryExists) {
            // Show/hide confirm button - only show for newly created polygons, not existing ones
            if (confirmBtn) confirmBtn.style.display = boundaryExists ? 'none' : 'inline-block';

            // Always show lock and clear buttons when boundary exists
            if (lockBtn) lockBtn.style.display = 'inline-block';
            if (clearBtn) clearBtn.style.display = 'inline-block';
            if (clearBtn2) clearBtn2.style.display = boundaryExists ? 'inline-block' : 'none';

            // Hide draw button when boundary already exists
            if (drawBtn && boundaryExists) drawBtn.style.display = 'none';
        } else {
            // No boundary exists - show only draw button
            if (confirmBtn) confirmBtn.style.display = 'none';
            if (lockBtn) lockBtn.style.display = 'none';
            if (clearBtn) clearBtn.style.display = 'none';
            if (clearBtn2) clearBtn2.style.display = 'none';
            if (drawBtn) drawBtn.style.display = 'inline-block';
        }
    }

    updateBoundaryDisplay(area, perimeter, pointCount) {
        const infoDisplay = document.getElementById('boundaryInfoDisplay');
        const areaDisplay = document.getElementById('boundaryAreaDisplay');
        const perimeterDisplay = document.getElementById('boundaryPerimeterDisplay');
        const pointsDisplay = document.getElementById('boundaryPointsDisplay');

        if (infoDisplay) infoDisplay.style.display = 'block';
        if (areaDisplay) areaDisplay.textContent = `${area.toFixed(2)} m²`;
        if (perimeterDisplay) perimeterDisplay.textContent = `${perimeter.toFixed(2)} m`;
        if (pointsDisplay) pointsDisplay.textContent = pointCount.toString();
    }

    handlePolygonUpdated(e) {
        this.onPolygonComplete(e);
    }

    handlePolygonDeleted(e) {
        this.sitePolygon = null;
        this.polygonEdges = [];
        window.eventBus.emit('site-boundary-deleted');
        this.info('Site boundary deleted');
    }

    calculatePolygonEdges(coordinates) {
        const edges = [];
        if (!coordinates || coordinates.length < 3) return edges;

        try {
            const coordsToProcess = coordinates.length > 3 && 
                coordinates[0][0] === coordinates[coordinates.length - 1][0] && 
                coordinates[0][1] === coordinates[coordinates.length - 1][1] 
                ? coordinates.slice(0, -1)
                : coordinates;

            for (let i = 0; i < coordsToProcess.length; i++) {
                const start = coordsToProcess[i];
                const end = coordsToProcess[(i + 1) % coordsToProcess.length];

                if (start && end && start.length >= 2 && end.length >= 2) {
                    edges.push({
                        index: i,
                        start: start,
                        end: end,
                        midpoint: [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
                    });
                }
            }

            return edges;
        } catch (error) {
            this.error('Error calculating polygon edges:', error);
            return edges;
        }
    }

    calculatePolygonAreaFallback(coordinates) {
        if (!coordinates || coordinates.length < 3) return 0;

        let area = 0;
        const n = coordinates.length;

        for (let i = 0; i < n - 1; i++) {
            const j = (i + 1) % (n - 1);
            area += coordinates[i][0] * coordinates[j][1];
            area -= coordinates[j][0] * coordinates[i][1];
        }

        return Math.abs(area) / 2;
    }

    async loadExistingSiteBoundary() {
        try {
            // Get project ID from URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            let projectId = urlParams.get('project') || urlParams.get('project_id');

            // Clean up malformed project IDs that might have extra parameters
            if (projectId && (projectId.includes('?') || projectId.includes('&'))) {
                projectId = projectId.split('?')[0].split('&')[0];
                this.info('Cleaned malformed project ID:', projectId);
            }

            // Validate project ID is numeric
            if (projectId) {
                projectId = String(projectId).trim();
                if (!/^\d+$/.test(projectId)) {
                    this.warn('Invalid project ID format:', projectId);
                    projectId = null;
                }
            }

            if (!projectId) {
                this.info('No valid project ID found, skipping site boundary load');
                return;
            }

            // Fetch project snapshot - try site_boundary first, then buildable_area
            const response = await fetch(`/api/project/${projectId}/snapshot`);
            const data = await response.json();

            let snapshotData = null;
            let siteCoordinates = null;
            let siteArea = null;

            if (data.success && data.snapshot) {
                // Try to parse the snapshot data
                try {
                    snapshotData = JSON.parse(data.snapshot.snapshot_data);
                } catch (jsonError) {
                    try {
                        let jsonString = data.snapshot.snapshot_data.replace(/'/g, '"');
                        snapshotData = JSON.parse(jsonString);
                    } catch (conversionError) {
                        this.error('Failed to parse snapshot data', conversionError);
                        return;
                    }
                }

                // Check snapshot type and extract site coordinates
                if (data.snapshot.snapshot_type === 'site_boundary') {
                    // Direct site boundary snapshot
                    if (snapshotData.coordinates && snapshotData.coordinates.length > 0) {
                        siteCoordinates = snapshotData.coordinates;
                        siteArea = snapshotData.area_m2;
                        this.info('Found site boundary snapshot');
                    }
                } else if (data.snapshot.snapshot_type === 'buildable_area') {
                    // Extract site coordinates from buildable area snapshot
                    this.info('Found buildable area snapshot, checking for site coordinates');
                    
                    // Check for site coordinates in the snapshot data
                    if (snapshotData.site_coords && snapshotData.site_coords.length > 0) {
                        siteCoordinates = snapshotData.site_coords;
                        siteArea = snapshotData.site_area_m2 || snapshotData.site_area_calculated;
                        this.info('Site coordinates found in buildable area snapshot:', siteCoordinates.length, 'points');
                    } else {
                        this.warn('Buildable area snapshot found but no site coordinates available for reconstruction');
                        this.info('Available snapshot data keys:', Object.keys(snapshotData));
                        return;
                    }
                }

                // Load the site boundary if we found coordinates
                if (siteCoordinates && siteCoordinates.length > 0) {
                    this.info('Loading existing site boundary from snapshot...');

                    const polygonFeature = {
                        type: 'Feature',
                        properties: {},
                        geometry: {
                            type: 'Polygon',
                            coordinates: [siteCoordinates]
                        }
                    };

                    // Add to map
                    this.draw.add(polygonFeature);
                    this.sitePolygon = polygonFeature;
                    this.polygonEdges = this.calculatePolygonEdges(siteCoordinates);

                    // Calculate area and perimeter for UI display
                    const area = siteArea || this.calculatePolygonArea(siteCoordinates);
                    const perimeter = this.calculatePolygonPerimeter(siteCoordinates);

                    // Update UI display
                    this.updateBoundaryDisplay(area, perimeter, siteCoordinates.length - 1);
                    this.updateButtonStates(false, true); // false for polygonCreated, true for boundaryExists

                    // Show final dimensions
                    this.showFinalDimensions(siteCoordinates);

                    // Zoom to the site boundary
                    const bounds = turf.bbox(polygonFeature);
                    this.map.fitBounds(bounds, { padding: 50 });

                    // Emit event
                    this.info('Emitting site-boundary-loaded event with edges:', this.polygonEdges.length);
                    window.eventBus.emit('site-boundary-loaded', {
                        coordinates: siteCoordinates,
                        area: area,
                        edges: this.polygonEdges
                    });

                    this.info('Existing site boundary loaded successfully from', data.snapshot.snapshot_type, 'snapshot');
                } else {
                    this.info('No site coordinates found in snapshot');
                }
            } else {
                this.info('No project snapshot found');
            }
        } catch (error) {
            this.error('Failed to load existing site boundary', error);
        }
    }

    addStaticSitePolygon(coords) {
        try {
            if (!this.map || !coords || coords.length < 3) return;

            if (this.map.getLayer('site-polygon-fill')) {
                this.map.removeLayer('site-polygon-fill');
            }
            if (this.map.getSource('site-polygon')) {
                this.map.removeSource('site-polygon');
            }

            this.map.addSource('site-polygon', {
                'type': 'geojson',
                'data': {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [coords]
                    }
                }
            });

            this.map.addLayer({
                'id': 'site-polygon-fill',
                'type': 'fill',
                'source': 'site-polygon',
                'layout': {},
                'paint': {
                    'fill-color': '#007cbf',
                    'fill-opacity': 0.2
                }
            });

            this.info('Static site polygon added successfully');
        } catch (error) {
            this.error('Error adding static site polygon:', error);
        }
    }

    getSitePolygon() {
        return this.sitePolygon;
    }

    getPolygonEdges() {
        return this.polygonEdges;
    }

    hasSiteBoundary() {
        return this.sitePolygon !== null;
    }

    toggleDrawingMode() {
        const drawBtn = document.getElementById('drawPolygonButton');
        const buttonRow = document.getElementById('drawingButtonRow');

        if (!drawBtn) return;

        if (this.isDrawing) {
            // Stop drawing
            this.draw.changeMode('simple_select');
            drawBtn.style.display = 'block';
            drawBtn.textContent = 'Draw Site Boundary';
            drawBtn.classList.remove('active');
            this.isDrawing = false;
            this.clearDrawingVisualization();
            if (buttonRow) buttonRow.style.display = 'none';
            this.info('Drawing mode disabled');
        } else {
            // Clear any existing boundary first
            this.draw.deleteAll();
            this.sitePolygon = null;
            this.clearDrawingVisualization();

            // Start drawing
            this.draw.changeMode('draw_polygon');
            drawBtn.style.display = 'none';
            this.isDrawing = true;
            this.drawingPoints = [];
            if (buttonRow) buttonRow.style.display = 'flex';

            // Hide boundary info display until polygon is created
            const infoDisplay = document.getElementById('boundaryInfoDisplay');
            if (infoDisplay) infoDisplay.style.display = 'none';

            this.info('Drawing mode enabled - click to place polygon points, double-click to finish');

            // Emit tool activation event
            window.eventBus.emit('tool-activated', 'boundary-drawing');
        }
    }

    stopDrawingMode() {
        const drawBtn = document.getElementById('drawPolygonButton');
        const buttonRow = document.getElementById('drawingButtonRow');

        // Stop drawing
        this.draw.changeMode('simple_select');
        drawBtn.style.display = 'block';
        drawBtn.textContent = 'Draw Site Boundary';
        drawBtn.classList.remove('active');
        this.isDrawing = false;
        this.clearDrawingVisualization();
        if (buttonRow) buttonRow.style.display = 'none';
        this.info('Drawing mode stopped');
    }

    clearBoundary() {
        this.draw.deleteAll();
        this.sitePolygon = null;
        this.clearDrawingVisualization();

        // Clear final dimensions
        const dimensionSource = this.map.getSource('boundary-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        // Update UI
        const drawBtn = document.getElementById('drawPolygonButton');
        const buttonRow = document.getElementById('drawingButtonRow');
        const confirmBtn = document.getElementById('confirmBoundaryButton');
        const lockBtn = document.getElementById('lockBoundaryButton');
        const clearBtn2 = document.getElementById('clearBoundaryButton2');
        const infoDisplay = document.getElementById('boundaryInfoDisplay');

        if (drawBtn) {
            drawBtn.style.display = 'inline-block';
            drawBtn.textContent = 'Draw Site Boundary';
            drawBtn.classList.remove('active');
        }
        if (buttonRow) buttonRow.style.display = 'none';
        if (confirmBtn) confirmBtn.style.display = 'none';
        if (clearBtn2) clearBtn2.style.display = 'none';
        if (lockBtn) {
            lockBtn.style.display = 'none';
            lockBtn.classList.remove('locked');
            lockBtn.innerHTML = '🔓';
        }
        if (infoDisplay) infoDisplay.style.display = 'none';

        // Reset lock status
        this.isLocked = false;
        this.updateLegendLockStatus();

        this.isDrawing = false;
        this.info('Site boundary cleared');

        // Emit deletion event
        window.eventBus.emit('site-boundary-deleted');
    }

    confirmBoundary() {
        if (!this.sitePolygon) {
            alert('No boundary to confirm. Please draw a boundary first.');
            return;
        }

        // Calculate final metrics
        const coordinates = this.sitePolygon.geometry.coordinates[0];
        const area = this.calculatePolygonArea(coordinates);
        const perimeter = this.calculatePolygonPerimeter(coordinates);

        // Save to project
        this.saveBoundaryToProject(coordinates, area);

        this.info('Site boundary confirmed and saved');

        // Emit boundary created event
        window.eventBus.emit('site-boundary-created', {
            coordinates: coordinates,
            area: area,
            perimeter: perimeter
        });

        // Enable next step - this will trigger the UI card management
        window.eventBus.emit('boundary-applied');
    }

    calculatePolygonArea(coordinates) {
        if (!coordinates || coordinates.length < 3) return 0;

        try {
            const polygon = turf.polygon([coordinates]);
            return turf.area(polygon);
        } catch (error) {
            this.error('Area calculation error:', error);
            return this.calculatePolygonAreaFallback(coordinates);
        }
    }

    calculatePolygonPerimeter(coordinates) {
        if (!coordinates || coordinates.length < 3) return 0;

        let perimeter = 0;
        for (let i = 0; i < coordinates.length - 1; i++) {
            const start = coordinates[i];
            const end = coordinates[i + 1];
            perimeter += this.calculateDistance(start[0], start[1], end[0], end[1]);
        }
        return perimeter;
    }

    calculateDistance(lon1, lat1, lon2, lat2) {
        const R = 6371e3; // metres
        const φ1 = lat1 * Math.PI / 180; // φ, λ in radians
        const φ2 = lat2 * Math.PI / 180;
        const Δφ = (lat2 - lat1) * Math.PI / 180;
        const Δλ = (lon2 - lon1) * Math.PI / 180;

        const a = Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        const d = R * c;
        return d;
    }

    calculateTerrainBounds(coordinates) {
        // Calculate bounding box of site boundary
        let minLng = Infinity, maxLng = -Infinity;
        let minLat = Infinity, maxLat = -Infinity;

        coordinates.forEach(coord => {
            const lng = coord[0];
            const lat = coord[1];
            minLng = Math.min(minLng, lng);
            maxLng = Math.max(maxLng, lng);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
        });

        // Convert 50m buffer to degrees (approximate)
        // At equator: 1 degree ≈ 111,320 m
        // For latitude: buffer is consistent
        // For longitude: buffer varies by latitude
        const latBuffer = 50 / 111320; // ~0.00045 degrees
        const lngBuffer = 50 / (111320 * Math.cos((minLat + maxLat) / 2 * Math.PI / 180));

        const bounds = {
            southwest: [minLng - lngBuffer, minLat - latBuffer],
            northeast: [maxLng + lngBuffer, maxLat + latBuffer],
            center: [(minLng + maxLng) / 2, (minLat + maxLat) / 2],
            width: maxLng - minLng + (2 * lngBuffer),
            height: maxLat - minLat + (2 * latBuffer)
        };

        this.info('Calculated terrain bounds with 50m buffer:', bounds);
        return bounds;
    }

    showFinalDimensions(coordinates) {
        // Remove the duplicate last coordinate if present
        const coords = coordinates.length > 0 && 
            coordinates[0][0] === coordinates[coordinates.length - 1][0] && 
            coordinates[0][1] === coordinates[coordinates.length - 1][1] 
            ? coordinates.slice(0, -1) 
            : coordinates;

        const dimensionFeatures = [];

        // Add dimension labels for each edge
        for (let i = 0; i < coords.length; i++) {
            const start = coords[i];
            const end = coords[(i + 1) % coords.length];
            const distance = this.calculateDistance(start[0], start[1], end[0], end[1]);
            const midpoint = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2];

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

        // Update dimension source with final dimensions
        const dimensionSource = this.map.getSource('boundary-dimensions');
        if (dimensionSource) {
            dimensionSource.setData({
                type: 'FeatureCollection',
                features: dimensionFeatures
            });
        }
    }

    toggleBoundaryLock() {
        const lockBtn = document.getElementById('lockBoundaryButton');

        if (!lockBtn) return;

        this.isLocked = !this.isLocked;

        if (this.isLocked) {
            // Lock the boundary
            this.lockBoundary();
            lockBtn.innerHTML = '🔒';
            lockBtn.title = 'Unlock site boundary';
            lockBtn.classList.add('locked');
            this.info('Site boundary locked - protected from editing');
        } else {
            // Unlock the boundary
            this.unlockBoundary();
            lockBtn.innerHTML = '🔓';
            lockBtn.title = 'Lock site boundary';
            lockBtn.classList.remove('locked');
            this.info('Site boundary unlocked - editing enabled');
        }

        // Update legend lock status
        this.updateLegendLockStatus();
    }

    lockBoundary() {
        if (!this.sitePolygon) return;

        try {
            // Switch to simple_select mode to prevent drawing
            this.draw.changeMode('simple_select');

            // Disable drawing tools
            const drawBtn = document.getElementById('drawPolygonButton');
            const clearBtn = document.getElementById('clearBoundaryButton');

            if (drawBtn) {
                drawBtn.disabled = true;
                drawBtn.style.opacity = '0.5';
            }
            if (clearBtn) {
                clearBtn.disabled = true;
                clearBtn.style.opacity = '0.5';
            }

            // Disable polygon editing by removing from draw control and making it non-interactive
            const features = this.draw.getAll();
            if (features.features.length > 0) {
                // Store the feature ID for potential unlock
                this.lockedFeatureId = features.features[0].id;
                // Delete from draw control to prevent editing
                this.draw.delete(this.lockedFeatureId);
                // Add as static layer instead
                this.addStaticSitePolygon(this.sitePolygon.geometry.coordinates[0]);
            }

            this.info('Boundary locked successfully');
        } catch (error) {
            this.error('Error locking boundary:', error);
        }
    }

    unlockBoundary() {
        try {
            // Re-enable drawing tools
            const drawBtn = document.getElementById('drawPolygonButton');
            const clearBtn = document.getElementById('clearBoundaryButton');

            if (drawBtn) {
                drawBtn.disabled = false;
                drawBtn.style.opacity = '1';
            }
            if (clearBtn && this.sitePolygon) {
                clearBtn.disabled = false;
                clearBtn.style.opacity = '1';
            }

            // Restore editable polygon if it was locked
            if (this.sitePolygon) {
                // Remove static layer
                if (this.map.getLayer('site-polygon-fill')) {
                    this.map.removeLayer('site-polygon-fill');
                }
                if (this.map.getSource('site-polygon')) {
                    this.map.removeSource('site-polygon');
                }

                // Add back to draw control
                this.draw.add(this.sitePolygon);
                this.draw.changeMode('simple_select');
            }

            this.info('Boundary unlocked successfully');
        } catch (error) {
            this.error('Error unlocking boundary:', error);
        }
    }

    updateLegendLockStatus() {
        const legendLockIcon = document.getElementById('legendLockIcon');
        if (legendLockIcon) {
            legendLockIcon.style.display = this.isLocked ? 'inline' : 'none';
        }
    }

    getBoundaryLockStatus() {
        return this.isLocked;
    }

    async saveBoundaryToProject(coordinates, area) {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            let projectId = urlParams.get('project') || urlParams.get('project_id');

            // Clean up malformed project IDs that might have extra parameters
            if (projectId && (projectId.includes('?') || projectId.includes('&'))) {
                projectId = projectId.split('?')[0].split('&')[0];
                this.info('Cleaned malformed project ID:', projectId);
            }

            // Validate project ID is numeric
            if (projectId) {
                projectId = String(projectId).trim();
                if (!/^\d+$/.test(projectId)) {
                    this.warn('Invalid project ID format:', projectId);
                    projectId = null;
                }
            }

            if (!projectId) {
                this.warn('No valid project ID found, cannot save boundary.');
                return;
            }

            const snapshotData = {
                coordinates: coordinates,
                area_m2: area
            };

            const response = await fetch(`/api/project/${projectId}/snapshot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    snapshot_type: 'site_boundary',
                    snapshot_data: JSON.stringify(snapshotData)
                })
            });

            const data = await response.json();

            if (!data.success) {
                this.error('Failed to save site boundary', data.error);
            } else {
                this.info('Site boundary saved successfully');
            }

        } catch (error) {
            this.error('Error saving site boundary:', error);
        }
    }
}

window.SiteBoundaryManager = SiteBoundaryManager;