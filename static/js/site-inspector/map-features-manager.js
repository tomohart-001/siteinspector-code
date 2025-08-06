/**
 * Map Features Manager
 * Handles 3D buildings, measure tools, style controls, and other map features
 */

class MapFeaturesManager extends BaseManager {
    constructor(map) {
        super('MapFeaturesManager');
        this.map = map;
        this.isMeasuring = false;
        this.measurePoints = [];
        this.measurePopups = [];
        this.livePopup = null;
        this.has3DBuildings = false;
    }

    async initialize() {
        this.info('Initializing Map Features Manager...');
        this.setupEventListeners();
        this.setup3DBuildingsControl();
        this.setupMeasureTool();
        this.setupStyleControls();
        this.setupDimensionsControl();

        // Check initial state of dimensions toggle and apply it
        setTimeout(() => {
            const dimensionsToggle = document.querySelector('.dimensions-toggle-switch input');
            if (dimensionsToggle && dimensionsToggle.checked) {
                this.showDimensions();
                this.info('Applied initial dimensions visibility state: ON');
            } else {
                this.hideDimensions();
                this.info('Applied initial dimensions visibility state: OFF');
            }
        }, 1000); // Delay to ensure layers are loaded

        this.info('Map Features Manager initialized successfully');
    }

    setupEventListeners() {
        // Style selector
        const styleSelector = document.getElementById('styleSelector');
        if (styleSelector) {
            styleSelector.addEventListener('change', (e) => {
                this.changeMapStyle(e.target.value);
            });
        }

        // Measure tool button
        const measureBtn = document.getElementById('measureToolButton');
        if (measureBtn) {
            measureBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMeasureTool();
            });
        }

        // 3D Buildings toggle
        const buildingsBtn = document.getElementById('buildingsToggle');
        if (buildingsBtn) {
            buildingsBtn.addEventListener('click', () => {
                this.toggle3DBuildings();
            });
        }

        // Listen for inspector panel toggle to shift controls
        window.eventBus.on('inspector-panel-toggled', (data) => {
            this.handlePanelToggle(data.expanded);
        });

        // Dimensions control is handled in setupDimensionsControl()

        // 3D Buildings opacity slider
        const opacitySlider = document.getElementById('buildingsOpacity');
        const opacityValue = document.getElementById('buildingsOpacityValue');
        if (opacitySlider && opacityValue) {
            opacitySlider.addEventListener('input', (e) => {
                const opacity = parseFloat(e.target.value);
                opacityValue.textContent = Math.round(opacity * 100) + '%';

                // Update buildings opacity in real-time
                if (this.map.getLayer('3d-buildings')) {
                    this.map.setPaintProperty('3d-buildings', 'fill-extrusion-opacity', opacity);
                    this.info(`3D Buildings opacity updated to ${Math.round(opacity * 100)}%`);
                }
            });

            // Also handle change event for final value
            opacitySlider.addEventListener('change', (e) => {
                const opacity = parseFloat(e.target.value);
                this.info(`3D Buildings opacity set to ${Math.round(opacity * 100)}%`);
            });
        }

        // Listen for other tool activations to stop measuring
        if (window.eventBus) {
            window.eventBus.on('tool-activated', (toolName) => {
                if (toolName !== 'measure' && this.isMeasuring) {
                    this.stopMeasuring();
                }
            });
        }
    }

    setup3DBuildingsControl() {
        // 3D Buildings control is already set up in the HTML
        // This method can handle any additional initialization
        this.info('3D Buildings control ready');
    }

    setupMeasureTool() {
        this.info('Measure tool ready');
    }

    setupStyleControls() {
        this.info('Style controls ready');
    }

    changeMapStyle(styleValue) {
        this.info('Changing map style', styleValue);

        if (this.map) {
            let fullStyleUrl = styleValue;
            if (!styleValue.startsWith('mapbox://')) {
                fullStyleUrl = `mapbox://styles/mapbox/${styleValue}`;
            }

            // Store current state before style change
            const had3DBuildings = this.has3DBuildings;

            this.map.setStyle(fullStyleUrl);

            // Restore 3D terrain and buildings after style loads
            this.map.once('styledata', () => {
                // Re-add 3D terrain
                this.restore3DTerrain();

                // Restore 3D buildings if they were enabled
                if (had3DBuildings) {
                    this.add3DBuildings();
                }
            });

            this.info('Map style changed to:', fullStyleUrl);
        }
    }

    restore3DTerrain() {
        // Wait for style to be fully loaded
        if (!this.map.isStyleLoaded()) {
            this.map.once('styledata', () => {
                this.restore3DTerrain();
            });
            return;
        }

        try {
            // Re-add terrain source
            if (!this.map.getSource('mapbox-dem')) {
                this.map.addSource('mapbox-dem', {
                    'type': 'raster-dem',
                    'url': 'mapbox://mapbox.terrain-rgb',
                    'tileSize': 512,
                    'maxzoom': 14
                });
            }

            // Re-add terrain layer
            this.map.setTerrain({ 
                'source': 'mapbox-dem', 
                'exaggeration': 1.5 
            });

            // Re-add sky layer
            if (!this.map.getLayer('sky')) {
                this.map.addLayer({
                    'id': 'sky',
                    'type': 'sky',
                    'paint': {
                        'sky-type': 'atmosphere',
                        'sky-atmosphere-sun': [0.0, 0.0],
                        'sky-atmosphere-sun-intensity': 15
                    }
                });
            }

            // Verify composite source is available for 3D buildings
            if (!this.map.getSource('composite')) {
                this.warn('Composite source not available after style change');
            } else {
                this.info('Composite source confirmed available after style change');
            }

            this.info('3D terrain restored after style change');
        } catch (error) {
            this.error('Error restoring 3D terrain:', error);
        }
    }

    toggle3DBuildings() {
        const buildingsBtn = document.getElementById('buildingsToggle');
        const buildingsControl = document.getElementById('buildingsControl');

        if (!buildingsBtn || !buildingsControl) {
            this.error('3D Buildings elements not found');
            return;
        }

        const isExpanded = buildingsControl.classList.contains('expanded');
        const has3DLayer = this.map.getLayer('3d-buildings');

        try {
            if (has3DLayer) {
                // Buildings are currently visible
                if (isExpanded) {
                    // Control is expanded, hide buildings and collapse
                    this.remove3DBuildings();
                    buildingsBtn.classList.remove('active');
                    buildingsBtn.textContent = '3D Buildings';
                    buildingsControl.classList.remove('expanded');
                    this.info('3D Buildings disabled');
                } else {
                    // Control is collapsed, just expand to show opacity controls
                    buildingsBtn.classList.add('active');
                    buildingsControl.classList.add('expanded');
                    this.info('3D Buildings control expanded');
                }
            } else {
                // Buildings are not visible
                if (isExpanded) {
                    // Control is expanded but no buildings, collapse
                    buildingsBtn.classList.remove('active');
                    buildingsBtn.textContent = '3D Buildings';
                    buildingsControl.classList.remove('expanded');
                    this.info('Control collapsed');
                } else {
                    // Control is collapsed, add buildings and expand
                    this.add3DBuildings();

                    // Check if buildings were actually added after a short delay
                    setTimeout(() => {
                        if (!this.map.getLayer('3d-buildings')) {
                            this.warn('Regular 3D buildings failed, trying force method...');
                            this.force3DBuildings();
                        }
                    }, 1000);

                    // Animate to optimal viewing position for 3D buildings
                    this.animateToOptimal3DView();

                    buildingsBtn.classList.add('active');
                    buildingsControl.classList.add('expanded');
                    this.info('3D Buildings enabled');
                }
            }
        } catch (error) {
            this.error('Error toggling 3D buildings:', error);
        }
    }

    add3DBuildings() {
        // Check if buildings layer already exists
        if (this.map.getLayer('3d-buildings')) {
            this.info('3D Buildings layer already exists');
            return;
        }

        const opacitySlider = document.getElementById('buildingsOpacity');
        const currentOpacity = opacitySlider ? parseFloat(opacitySlider.value) : 0.6;

        // Wait for map to be fully loaded before adding layer
        if (!this.map.isStyleLoaded()) {
            this.map.once('styledata', () => {
                this.add3DBuildings();
            });
            return;
        }

        // Debug: Check what sources are available
        const sources = this.map.getStyle().sources;
        this.info('Available map sources:', Object.keys(sources));

        // Verify composite source is available
        if (!this.map.getSource('composite')) {
            this.error('Composite source not available - cannot add 3D buildings');
            this.info('Available sources:', Object.keys(sources));
            return;
        }

        try {
            // Use proper 3D buildings configuration with wider zoom range
            this.map.addLayer({
                'id': '3d-buildings',
                'source': 'composite',
                'source-layer': 'building',
                'filter': ['==', 'extrude', 'true'],
                'type': 'fill-extrusion',
                'minzoom': 8,
                'paint': {
                    'fill-extrusion-color': [
                        'case',
                        ['has', 'underground'],
                        'rgba(120, 120, 120, 0.8)',
                        '#4a4a4a'
                    ],
                    'fill-extrusion-height': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        8, 0,
                        10, ['*', ['to-number', ['get', 'height']], 0.5],
                        12, ['*', ['to-number', ['get', 'height']], 1],
                        22, ['*', ['to-number', ['get', 'height']], 1]
                    ],
                    'fill-extrusion-base': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        8, 0,
                        10, ['*', ['to-number', ['get', 'min_height']], 0.5],
                        12, ['*', ['to-number', ['get', 'min_height']], 1],
                        22, ['*', ['to-number', ['get', 'min_height']], 1]
                    ],
                    'fill-extrusion-opacity': currentOpacity
                }
            });

            // Validate layer was added successfully
            if (this.map.getLayer('3d-buildings')) {
                this.has3DBuildings = true;
                this.info('3D Buildings layer added successfully');

                // Force minimum zoom and pitch for visibility
                const currentZoom = this.map.getZoom();
                const currentPitch = this.map.getPitch();

                if (currentZoom < 10) {
                    this.map.easeTo({
                        zoom: 14,
                        pitch: 45,
                        duration: 1500,
                        essential: true
                    });
                    this.info('Adjusting zoom to 14 and pitch to 45° for 3D buildings visibility');
                } else if (currentPitch < 20) {
                    this.map.easeTo({
                        pitch: 45,
                        duration: 1000,
                        essential: true
                    });
                    this.info('Adjusting pitch to 45° for better 3D buildings view');
                }

                // Debug: Query features to see if building data exists
                setTimeout(() => {
                    if (this.map.getLayer('3d-buildings')) {
                        // Query all building features in the area
                        const center = this.map.getCenter();
                        const zoom = this.map.getZoom();

                        const allBuildingFeatures = this.map.querySourceFeatures('composite', {
                            sourceLayer: 'building'
                        });

                        const extrudableFeatures = this.map.querySourceFeatures('composite', {
                            sourceLayer: 'building',
                            filter: ['==', 'extrude', 'true']
                        });

                        const heightFeatures = this.map.querySourceFeatures('composite', {
                            sourceLayer: 'building',
                            filter: ['has', 'height']
                        });

                        this.info(`Building features debug - Total: ${allBuildingFeatures.length}, Extrudable: ${extrudableFeatures.length}, With height: ${heightFeatures.length}`);
                        this.info(`Current zoom: ${zoom.toFixed(2)}, Center: [${center.lng.toFixed(6)}, ${center.lat.toFixed(6)}]`);

                        if (allBuildingFeatures.length > 0) {
                            const sample = allBuildingFeatures[0];
                            this.info('Sample building properties:', sample.properties);
                        }

                        // Force map repaint and layer visibility check
                        this.map.triggerRepaint();

                        // Check if layer is actually visible
                        const layerVisibility = this.map.getLayoutProperty('3d-buildings', 'visibility');
                        this.info('3D Buildings layer visibility:', layerVisibility || 'visible');

                        // Log paint properties
                        const opacity = this.map.getPaintProperty('3d-buildings', 'fill-extrusion-opacity');
                        const height = this.map.getPaintProperty('3d-buildings', 'fill-extrusion-height');
                        this.info('3D Buildings paint properties - Opacity:', opacity, 'Height expression:', height);
                    }
                }, 2000);

            } else {
                this.error('3D Buildings layer was not added successfully');
            }

        } catch (error) {
            this.error('Failed to add 3D buildings layer:', error);

            // Try ultra-simple fallback configuration
            try {
                this.map.addLayer({
                    'id': '3d-buildings',
                    'source': 'composite',
                    'source-layer': 'building',
                    'filter': ['all', ['==', '$type', 'Polygon'], ['has', 'height']],
                    'type': 'fill-extrusion',
                    'minzoom': 8,
                    'paint': {
                        'fill-extrusion-color': '#9a9a9a',
                        'fill-extrusion-height': [
                            'case',
                            ['has', 'height'],
                            ['to-number', ['get', 'height']],
                            10
                        ],
                        'fill-extrusion-base': [
                            'case',
                            ['has', 'min_height'],
                            ['to-number', ['get', 'min_height']],
                            0
                        ],
                        'fill-extrusion-opacity': 0.8
                    }
                });

                if (this.map.getLayer('3d-buildings')) {
                    this.has3DBuildings = true;
                    this.info('3D Buildings layer added with ultra-simple fallback configuration');
                }
            } catch (fallbackError) {
                this.error('All 3D buildings configurations failed:', fallbackError);
                // Try to determine why composite source isn't working
                this.checkMapCapabilities();
            }
        }
    }

    remove3DBuildings() {
        if (this.map.getLayer('3d-buildings')) {
            this.map.removeLayer('3d-buildings');
            this.has3DBuildings = false;
            this.info('3D Buildings layer removed');
        }

        // Update UI state
        const buildingsBtn = document.getElementById('buildingsToggle');
        const buildingsControl = document.getElementById('buildingsControl');

        if (buildingsBtn) {
            buildingsBtn.classList.remove('active');
            buildingsBtn.textContent = '3D Buildings';
        }

        if (buildingsControl) {
            buildingsControl.classList.remove('expanded');
        }
    }

    toggleMeasureTool() {
        const button = document.getElementById('measureToolButton');

        if (this.isMeasuring) {
            this.stopMeasuring();
            button.classList.remove('active');
            button.innerHTML = '📐';
        } else {
            this.startMeasuring();
            button.classList.add('active');
            button.innerHTML = '✖';

            // Notify other tools
            window.eventBus.emit('tool-activated', 'measure');
        }
    }

    startMeasuring() {
        this.isMeasuring = true;
        this.measurePoints = [];
        this.measurePopups = [];
        this.measureClickCount = 0;

        this.map.getCanvas().style.cursor = 'crosshair';
        this.map.on('click', this.handleMeasureClick);

        this.addMeasureToolExitListeners();
        this.info('Measurement tool started - click two points to measure');
    }

    stopMeasuring() {
        this.isMeasuring = false;

        // Remove all event listeners safely
        if (this.handleMeasureClick) {
            this.map.off('click', this.handleMeasureClick);
        }
        if (this.handleMeasureMouseMove) {
            this.map.off('mousemove', this.handleMeasureMouseMove);
        }

        // Reset cursor
        if (this.map.getCanvas()) {
            this.map.getCanvas().style.cursor = '';
        }

        this.clearLiveMeasurement();
        this.clearMeasurements();
        this.removeMeasureToolExitListeners();

        const button = document.getElementById('measureToolButton');
        if (button) {
            button.classList.remove('active');
            button.innerHTML = '📐';
        }

        // Clear measurement state
        this.measurePoints = [];
        this.measureClickCount = 0;

        this.info('Measurement tool stopped');
    }

    // Add cleanup method for proper disposal
    dispose() {
        this.info('Disposing Map Features Manager...');

        // Stop any active tools
        if (this.isMeasuring) {
            this.stopMeasuring();
        }

        // Remove all event listeners
        this.removeMeasureToolExitListeners();

        // Clear any remaining popups
        if (this.measurePopups) {
            this.measurePopups.forEach(popup => {
                if (popup && popup.remove) {
                    popup.remove();
                }
            });
            this.measurePopups = [];
        }

        if (this.livePopup && this.livePopup.remove) {
            this.livePopup.remove();
            this.livePopup = null;
        }

        this.info('Map Features Manager disposed');
    }

    addMeasureToolExitListeners() {
        const uiElements = [
            '#inspectorPanel',
            '#edgeSelectionButton',
            '#recalculateButton',
            '#uploadFloorplanButton',
            '#drawFloorplanButton',
            '#buildingsToggle',
            '#styleSelector',
            '#siteInfoToggleBtn',
            '.boundary-option',
            '.setback-input'
        ];

        uiElements.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.addEventListener('click', this.handleUIClick);
            });
        });

        document.addEventListener('keydown', this.handleKeyDown);
    }

    removeMeasureToolExitListeners() {
        const uiElements = [
            '#inspectorPanel',
            '#edgeSelectionButton',
            '#recalculateButton',
            '#uploadFloorplanButton',
            '#drawFloorplanButton',
            '#buildingsToggle',
            '#styleSelector',
            '#siteInfoToggleBtn',
            '.boundary-option',
            '.setback-input'
        ];

        uiElements.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                element.removeEventListener('click', this.handleUIClick);
            });
        });

        document.removeEventListener('keydown', this.handleKeyDown);
    }

    handleUIClick = (e) => {
        if (this.isMeasuring) {
            this.info('UI element clicked, stopping measurement tool');
            this.stopMeasuring();
        }
    }

    handleKeyDown = (e) => {
        if (this.isMeasuring && e.key === 'Escape') {
            this.info('Escape pressed, stopping measurement tool');
            this.stopMeasuring();
        }
    }

    handleMeasureClick = (e) => {
        if (!this.isMeasuring) return;

        e.preventDefault();
        if (e.originalEvent) {
            e.originalEvent.stopPropagation();
        }

        if (this.measurePoints.length >= 2) {
            this.info('Maximum two points allowed, stopping measurement');
            this.stopMeasuring();
            return;
        }

        const point = [e.lngLat.lng, e.lngLat.lat];
        this.measurePoints.push(point);
        this.measureClickCount++;

        this.addPointMarker(point);

        if (this.measurePoints.length === 1) {
            this.map.on('mousemove', this.handleMeasureMouseMove);
            this.info('First point placed, move mouse for live measurement');
        } else if (this.measurePoints.length === 2) {
            this.map.off('mousemove', this.handleMeasureMouseMove);
            this.clearLiveMeasurement();
            this.updateMeasureLines();
            this.showMeasureDistance();

            this.info('Second point placed, measurement complete');

            setTimeout(() => {
                if (this.isMeasuring) {
                    this.stopMeasuring();
                }
            }, 2000);
        }

        this.info('Measure point added:', e.lngLat, `(${this.measurePoints.length}/2)`);
    }

    addPointMarker(point) {
        const pointFeature = {
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: point
            },
            properties: {
                id: this.measurePoints.length - 1
            }
        };

        const existingPoints = this.map.getSource('measure-points');
        if (existingPoints) {
            const currentData = existingPoints._data;
            currentData.features.push(pointFeature);
            existingPoints.setData(currentData);
        } else {
            this.map.addSource('measure-points', {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: [pointFeature]
                }
            });

            this.map.addLayer({
                id: 'measure-points',
                type: 'circle',
                source: 'measure-points',
                paint: {
                    'circle-radius': 6,
                    'circle-color': '#ff6b35',
                    'circle-stroke-color': '#ffffff',
                    'circle-stroke-width': 2
                }
            });
        }
    }

    handleMeasureMouseMove = (e) => {
        if (!this.isMeasuring || this.measurePoints.length !== 1) return;

        const mousePoint = [e.lngLat.lng, e.lngLat.lat];
        const startPoint = this.measurePoints[0];

        this.updateLiveLine(startPoint, mousePoint);
        this.updateLivePopup(startPoint, mousePoint);
    }

    updateLiveLine(startPoint, mousePoint) {
        let liveSource = this.map.getSource('measure-live');
        if (!liveSource) {
            this.map.addSource('measure-live', {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: []
                }
            });

            this.map.addLayer({
                id: 'measure-live',
                type: 'line',
                source: 'measure-live',
                paint: {
                    'line-color': '#ff6b35',
                    'line-width': 2,
                    'line-dasharray': [3, 3],
                    'line-opacity': 0.8
                }
            });

            liveSource = this.map.getSource('measure-live');
        }

        liveSource.setData({
            type: 'FeatureCollection',
            features: [{
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: [startPoint, mousePoint]
                }
            }]
        });
    }

    updateLivePopup(startPoint, mousePoint) {
        const distance = this.calculateDistance(
            { lng: startPoint[0], lat: startPoint[1] },
            { lng: mousePoint[0], lat: mousePoint[1] }
        );

        if (this.livePopup) {
            this.livePopup.remove();
        }

        const midpoint = [
            (startPoint[0] + mousePoint[0]) / 2,
            (startPoint[1] + mousePoint[1]) / 2
        ];

        this.livePopup = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
            className: 'measure-popup live-measure',
            anchor: 'bottom',
            offset: [0, -10]
        })
        .setLngLat(midpoint)
        .setHTML(`<div class="measure-distance live-distance">${distance.toFixed(1)}m</div>`)
        .addTo(this.map);
    }

    clearLiveMeasurement() {
        const liveSource = this.map.getSource('measure-live');
        if (liveSource) {
            liveSource.setData({
                type: 'FeatureCollection',
                features: []
            });
        }

        if (this.livePopup) {
            this.livePopup.remove();
            this.livePopup = null;
        }
    }

    updateMeasureLines() {
        if (this.measurePoints.length < 2) return;

        const lineFeatures = [];
        for (let i = 0; i < this.measurePoints.length - 1; i++) {
            lineFeatures.push({
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: [this.measurePoints[i], this.measurePoints[i + 1]]
                },
                properties: {
                    segmentId: i
                }
            });
        }

        const lineSource = this.map.getSource('measure-lines');
        if (lineSource) {
            lineSource.setData({
                type: 'FeatureCollection',
                features: lineFeatures
            });
        } else {
            this.map.addSource('measure-lines', {
                type: 'geojson',
                data: {
                    type: 'FeatureCollection',
                    features: lineFeatures
                }
            });

            this.map.addLayer({
                id: 'measure-lines',
                type: 'line',
                source: 'measure-lines',
                paint: {
                    'line-color': '#ff6b35',
                    'line-width': 3,
                    'line-dasharray': [5, 5]
                }
            });
        }
    }

    showMeasureDistance() {
        this.measurePopups.forEach(popup => popup.remove());
        this.measurePopups = [];

        for (let i = 0; i < this.measurePoints.length - 1; i++) {
            const start = this.measurePoints[i];
            const end = this.measurePoints[i + 1];
            const distance = this.calculateDistance(
                { lng: start[0], lat: start[1] },
                { lng: end[0], lat: end[1] }
            );

            const midpoint = [
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2
            ];

            const popup = new mapboxgl.Popup({
                closeButton: false,
                closeOnClick: false,
                className: 'measure-popup measure-final'
            })
            .setLngLat(midpoint)
            .setHTML(`<div class="measure-distance">${distance.toFixed(1)}m</div>`)
            .addTo(this.map);

            this.measurePopups.push(popup);
        }
    }

    calculateDistance(point1, point2) {
        const R = 6371000; // Earth's radius in meters
        const lat1 = point1.lat * Math.PI / 180;
        const lat2 = point2.lat * Math.PI / 180;
        const deltaLat = (point2.lat - point1.lat) * Math.PI / 180;
        const deltaLng = (point2.lng - point1.lng) * Math.PI / 180;

        const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                 Math.cos(lat1) * Math.cos(lat2) *
                 Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        const distance = R * c;
        return distance;
    }

    clearMeasurements() {
        this.measurePoints = [];

        if (this.measurePopups && this.measurePopups.length > 0) {
            this.measurePopups.forEach(popup => {
                if (popup && popup.remove) {
                    popup.remove();
                }
            });
        }
        this.measurePopups = [];

        const layersToRemove = ['measure-points', 'measure-lines'];
        const sourcesToRemove = ['measure-points', 'measure-lines'];

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

    isMeasuringActive() {
        return this.isMeasuring;
    }

    checkMapCapabilities() {
        this.info('Checking map capabilities for 3D buildings...');

        // Check map style and sources
        const style = this.map.getStyle();
        this.info('Current map style:', style.name || 'Unknown');
        this.info('Map sources available:', Object.keys(style.sources || {}));

        // Check if we can query composite source features
        if (this.map.getSource('composite')) {
            try {
                const features = this.map.querySourceFeatures('composite', {
                    sourceLayer: 'building'
                });
                this.info(`Composite source has ${features.length} building features`);

                if (features.length > 0) {
                    const sample = features[0];
                    this.info('Sample building feature properties:', sample.properties);
                    this.info('Sample building geometry type:', sample.geometry?.type);
                }
            } catch (queryError) {
                this.error('Failed to query composite source:', queryError);
            }
        } else {
            this.error('Composite source not available');
        }

        // Check if 3D terrain is affecting things
        const terrain = this.map.getTerrain();
        this.info('Map terrain settings:', terrain);
    }

    // Handle inspector panel toggle to shift controls
    handlePanelToggle(isExpanded) {
        const mapControlsContainer = document.getElementById('mapControlsContainer');

        // Shift the entire map controls container
        if (mapControlsContainer) {
            if (isExpanded) {
                mapControlsContainer.classList.add('shifted');
            } else {
                mapControlsContainer.classList.remove('shifted');
            }
        }

        this.info(`Map controls container ${isExpanded ? 'shifted' : 'reset'} due to panel toggle`);
    }

    // Animate to optimal viewing position for 3D buildings
    animateToOptimal3DView() {
        const currentZoom = this.map.getZoom();
        const currentPitch = this.map.getPitch();

        if (currentZoom < 16) {
            this.map.easeTo({
                zoom: 16,
                pitch: 45,
                duration: 1500,
                essential: true
            });
            this.info('Animating to zoom 16 and pitch 45° for optimal 3D buildings view');
        } else if (currentPitch < 20) {
            this.map.easeTo({
                pitch: 45,
                duration: 1000,
                essential: true
            });
            this.info('Adjusting pitch to 45° for better 3D buildings view');
        } else {
            this.info('Map already at good zoom/pitch for 3D buildings');
        }
    }

    // Force 3D buildings with minimal configuration
    force3DBuildings() {
        this.info('Forcing 3D buildings with minimal configuration...');

        // Remove existing layer first
        if (this.map.getLayer('3d-buildings')) {
            this.map.removeLayer('3d-buildings');
        }

        // Get current opacity setting
        const opacitySlider = document.getElementById('buildingsOpacity');
        const currentOpacity = opacitySlider ?```text
 parseFloat(opacitySlider.value) : 0.8;

        try {
            // Add ultra-minimal 3D buildings layer
            this.map.addLayer({
                'id': '3d-buildings',
                'source': 'composite',
                'source-layer': 'building',
                'type': 'fill-extrusion',
                'minzoom': 8,
                'paint': {
                    'fill-extrusion-color': '#9a9a9a',
                    'fill-extrusion-height': 15,
                    'fill-extrusion-base': 0,
                    'fill-extrusion-opacity': currentOpacity
                }
            });

            this.has3DBuildings = true;
            this.info('Force 3D buildings added with fixed height');

            // Ensure good viewing angle
            this.map.easeTo({
                zoom: 16,
                pitch: 45,
                duration: 1500,
                essential: true
            });
            this.info('Animating to optimal view for force 3D buildings');

        } catch (error) {
            this.error('Failed to force 3D buildings:', error);
        }
    }

    setupDimensionsControl() {
        // Wait for DOM to be ready
        setTimeout(() => {
            const dimensionsControl = document.getElementById('dimensionsControl');
            const dimensionsBtn = document.querySelector('.dimensions-toggle-btn');
            const dimensionsToggle = document.querySelector('.dimensions-toggle-switch input');

            if (!dimensionsControl || !dimensionsBtn || !dimensionsToggle) {
                this.warn('Dimensions control elements not found, retrying...');
                // Try again after a longer delay
                setTimeout(() => this.setupDimensionsControl(), 2000);
                return;
            }

            // Initialize toggle in ON state since dimensions are visible by default
            dimensionsToggle.checked = true;
            dimensionsBtn.classList.add('active');

            // Remove any existing event listeners first
            const newBtn = dimensionsBtn.cloneNode(true);
            dimensionsBtn.parentNode.replaceChild(newBtn, dimensionsBtn);
            
            const newToggle = dimensionsToggle.cloneNode(true);
            dimensionsToggle.parentNode.replaceChild(newToggle, dimensionsToggle);

            // Add click handler for the dimensions button
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleDimensions();
            });

            // Add change handler for the toggle switch
            newToggle.addEventListener('change', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleDimensions();
            });

            // Also add a direct onclick handler as backup
            newBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleDimensions();
            };

            this.info('Dimensions control setup completed with event handlers');
        }, 500);
    }

    // Toggle dimensions feature
    toggleDimensions() {
        this.info('toggleDimensions called');
        
        const dimensionsBtn = document.querySelector('.dimensions-toggle-btn');
        const dimensionsToggle = document.querySelector('.dimensions-toggle-switch input');

        if (!dimensionsBtn || !dimensionsToggle) {
            this.warn('Dimensions button or toggle not found');
            // Try to show/hide dimensions anyway based on current state
            const isCurrentlyVisible = this.areDimensionsVisible();
            if (isCurrentlyVisible) {
                this.hideDimensions();
            } else {
                this.showDimensions();
            }
            return;
        }

        // Get current state from the toggle checkbox
        const currentState = dimensionsToggle.checked;
        const newState = !currentState;

        // Update both button and toggle states
        dimensionsToggle.checked = newState;

        this.info(`Toggling dimensions: ${currentState ? 'ON' : 'OFF'} -> ${newState ? 'ON' : 'OFF'}`);

        if (newState) {
            dimensionsBtn.classList.add('active');
            this.showDimensions();
            this.info('Dimensions feature activated');
        } else {
            dimensionsBtn.classList.remove('active');
            this.hideDimensions();
            this.info('Dimensions feature deactivated');
        }

        // Force map repaint to ensure changes are visible
        if (this.map) {
            this.map.triggerRepaint();
        }
    }

    // Show all polygon dimensions on the map
    showDimensions() {
        // Define all dimension layer types for comprehensive control
        const dimensionLayers = [
            // Site boundary dimensions
            'boundary-dimension-labels',
            'site-dimension-labels',
            'site-dimensions',

            // Buildable area dimensions
            'buildable-area-dimension-labels',
            'buildable-dimension-labels',
            'buildable-dimensions',
            'setback-dimension-labels',
            'setback-dimensions',

            // Structure footprint dimensions
            'structure-dimension-labels',
            'structure-dimensions',
            'footprint-dimension-labels',
            'footprint-dimensions',
            'building-dimension-labels',
            'building-dimensions',
            'floorplan-dimension-labels',
            'floorplan-dimensions',

            // Measurement tool dimensions
            'measure-dimension-labels',
            'measure-dimensions',

            // Generic polygon dimensions
            'polygon-dimensions',
            'polygon-dimension-labels'
        ];

        let shownCount = 0;
        dimensionLayers.forEach(layerId => {
            if (this.map.getLayer(layerId)) {
                this.map.setLayoutProperty(layerId, 'visibility', 'visible');
                this.info(`Made ${layerId} visible`);
                shownCount++;
            }
        });

        this.info(`All polygon dimensions are now visible - ${shownCount} layers made visible`);

        // Try to regenerate buildable area dimensions if they don't exist but should
        const propertyManager = window.siteInspectorCore?.propertySetbacksManager;
        if (propertyManager && propertyManager.currentBuildableArea) {
            const buildableSource = this.map.getSource('buildable-area-dimensions');
            if (!buildableSource || !buildableSource._data || !buildableSource._data.features || buildableSource._data.features.length === 0) {
                this.info('Buildable area dimensions missing, regenerating...');
                const buildableCoords = propertyManager.currentBuildableArea.buildable_coords;
                if (buildableCoords && buildableCoords.length > 0) {
                    propertyManager.generateBuildableAreaDimensions(buildableCoords);
                    this.info('Buildable area dimensions regenerated');
                }
            }
        }

        // Force map repaint to ensure dimensions appear
        this.map.triggerRepaint();

        this.info('Dimensions feature activated - map repainted');
    }

    // Hide all polygon dimensions on the map
    hideDimensions() {
        // Define all dimension layer types for comprehensive control
        const dimensionLayers = [
            // Site boundary dimensions
            'boundary-dimension-labels',
            'site-dimension-labels',
            'site-dimensions',

            // Buildable area dimensions
            'buildable-area-dimension-labels',
            'buildable-dimension-labels',
            'buildable-dimensions',
            'setback-dimension-labels',
            'setback-dimensions',

            // Structure footprint dimensions
            'structure-dimension-labels',
            'structure-dimensions',
            'footprint-dimension-labels',
            'footprint-dimensions',
            'building-dimension-labels',
            'building-dimensions',
            'floorplan-dimension-labels',
            'floorplan-dimensions',

            // Measurement tool dimensions
            'measure-dimension-labels',
            'measure-dimensions',

            // Generic polygon dimensions
            'polygon-dimensions',
            'polygon-dimension-labels'
        ];

        let hiddenCount = 0;
        dimensionLayers.forEach(layerId => {
            if (this.map.getLayer(layerId)) {
                this.map.setLayoutProperty(layerId, 'visibility', 'none');
                hiddenCount++;
            }
        });

        this.info(`All polygon dimensions are now hidden - ${hiddenCount} layers hidden`);
    }

    // Get current dimensions visibility state
    areDimensionsVisible() {
        // Check multiple dimension layer types to determine overall visibility
        const primaryDimensionLayers = [
            'boundary-dimension-labels',
            'buildable-dimension-labels',
            'structure-dimension-labels',
            'floorplan-dimension-labels'
        ];

        // Return true if any primary dimension layer is visible
        for (const layerId of primaryDimensionLayers) {
            if (this.map.getLayer(layerId)) {
                const visibility = this.map.getLayoutProperty(layerId, 'visibility');
                if (visibility !== 'none') {
                    return true;
                }
            }
        }

        return false;
    }
}

window.MapFeaturesManager = MapFeaturesManager;