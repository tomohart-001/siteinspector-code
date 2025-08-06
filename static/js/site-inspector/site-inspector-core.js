/**
 * Site Inspector Core
 * Main orchestrator for the modular site inspector system
 */

class SiteInspectorCore extends BaseManager {
    constructor() {
        super('SiteInspectorCore');

        this.map = null;
        this.draw = null;
        this.siteData = {};

        // Manager instances
        this.siteBoundaryManager = null;
        this.propertySetbacksManager = null;
        this.floorplanManager = null;
        this.mapFeaturesManager = null;
        this.uiPanelManager = null;

        this.isInitialized = false;
    }

    async initialize() {
        try {
            this.info('🚀 Starting Site Inspector initialization...');

            // Validate required dependencies first
            if (!this.validateDependencies()) {
                throw new Error('Required dependencies not available');
            }

            // Load site data from template
            this.loadSiteData();

            // Load project address FIRST before map initialization
            const addressLoaded = await this.loadProjectAddress();

            if (!addressLoaded) {
                this.warn('⚠️ Project address could not be loaded, proceeding with default location');
                // Set a default center for Auckland, New Zealand if no project address found
                if (!this.siteData.center) {
                    this.siteData.center = {
                        lat: -36.8485,
                        lng: 174.7633
                    };
                    this.info('Using default Auckland location for map center');
                }
            }

            // Always initialize map - this is critical for site inspector functionality
            await this.initializeMap();

            // Initialize all managers with error handling
            await this.initializeManagers();

            // Setup inter-manager communication
            this.setupEventHandlers();

            this.isInitialized = true;

            // Hide loading state
            const mapLoading = document.getElementById('mapLoading');
            if (mapLoading) {
                mapLoading.style.display = 'none';
            }

            this.info('✅ Site Inspector initialization completed successfully');

        } catch (error) {
            this.error('❌ Site Inspector initialization failed:', error);
            this.showMapError(error.message || 'Unknown initialization error');

            // Attempt recovery
            this.attemptRecovery();
        }
    }

    loadSiteData() {
        // Get site data from template
        if (typeof window.siteData !== 'undefined' && window.siteData) {
            this.siteData = window.siteData;
            this.info('Site data loaded from template');
        } else {
            this.siteData = {
                ready_for_new_polygon: true,
                area: 0,
                area_m2: 0,
                type: 'residential',
                coordinates: [],
                center: null
            };
        }
    }

    validateDependencies() {
        return typeof mapboxgl !== 'undefined';
    }

    async loadProjectAddress() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            let projectId = urlParams.get('project_id') || urlParams.get('project');

            // Clean up malformed project IDs (remove any extra parameters)
            if (projectId && projectId.includes('?')) {
                projectId = projectId.split('?')[0];
                this.info('Cleaned malformed project ID:', projectId);
            }

            this.info('URL parameters check:', {
                'project_id': urlParams.get('project_id'),
                'project': urlParams.get('project'),
                'cleaned_project_id': projectId,
                'full_url': window.location.href
            });

            // If no project ID in URL, try session storage (for newly created projects)
            if (!projectId) {
                projectId = sessionStorage.getItem('project_id');
                if (projectId && projectId.includes('?')) {
                    projectId = projectId.split('?')[0];
                }
                this.info('No project ID in URL, trying session storage:', {
                    'session_project_id': projectId,
                    'all_session_keys': Object.keys(sessionStorage)
                });
            }

            // Convert to string and validate
            if (projectId) {
                projectId = String(projectId).trim();
                // Ensure it's numeric
                if (!/^\d+$/.test(projectId)) {
                    this.warn('Invalid project ID format:', projectId);
                    return false;
                }
                this.info('Found valid project ID:', projectId);
            } else {
                this.info('No project ID found in URL parameters or session storage');
                return false;
            }

            this.info('Using project ID:', projectId);

            // Check cache first
            const cacheKey = `project_address_${projectId}`;
            const cached = this.getFromCache(cacheKey);
            if (cached && cached.timestamp > Date.now() - 300000) { // 5 minute cache
                this.info('Using cached project address data');
                this.siteData.project_address = cached.address;
                if (cached.center) {
                    this.siteData.center = cached.center;
                    return true;
                }
            }

            this.info('Loading project address for project ID:', projectId);

            // Use fetch with timeout and retry
            const response = await this.fetchWithRetry(`/api/project-address?project_id=${projectId}`, {
                timeout: 10000,
                retries: 2
            });

            if (!response.ok) {
                this.error(`API request failed with status ${response.status}: ${response.statusText}`);
                return false;
            }

            const data = await response.json();
            this.info('API response received:', data);

            if (data.success && data.site_address) {
                this.info('✅ Project address loaded:', data.site_address);

                // Store project address
                this.siteData.project_address = data.site_address;

                // Check if coordinates are already available
                if (data.location && data.location.lat && data.location.lng) {
                    this.siteData.center = {
                        lat: parseFloat(data.location.lat),
                        lng: parseFloat(data.location.lng)
                    };
                    this.info('✅ Project coordinates loaded:', this.siteData.center);

                    // Cache the result
                    this.setCache(cacheKey, {
                        address: data.site_address,
                        center: this.siteData.center,
                        timestamp: Date.now()
                    });

                    return true;
                } else {
                    this.warn('⚠️ Project address found but no coordinates - will geocode');

                    // Geocode the address
                    const geocoded = await this.geocodeProjectAddress(data.site_address);
                    if (geocoded) {
                        // Cache the result
                        this.setCache(cacheKey, {
                            address: data.site_address,
                            center: this.siteData.center,
                            timestamp: Date.now()
                        });
                        return true;
                    }
                }
            } else {
                this.warn('⚠️ Failed to load project address:', data.error || 'Unknown error');
            }
            return false;
        } catch (error) {
            this.error('❌ Error loading project address:', error);
            return false;
        }
    }

    async geocodeProjectAddress(address) {
        try {
            this.info('Geocoding project address:', address);

            // Check geocode cache
            const geocodeCacheKey = `geocode_${btoa(address)}`;
            const cached = this.getFromCache(geocodeCacheKey);
            if (cached && cached.timestamp > Date.now() - 86400000) { // 24 hour cache for geocoding
                this.info('Using cached geocoding result');
                this.siteData.center = cached.center;
                return cached.center;
            }

            const response = await this.fetchWithRetry('/api/geocode-location', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: address }),
                timeout: 15000, // Longer timeout for geocoding
                retries: 2
            });

            if (!response.ok) {
                throw new Error(`Geocoding failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success && data.location) {
                this.siteData.center = {
                    lat: parseFloat(data.location.lat),
                    lng: parseFloat(data.location.lng)
                };
                this.siteData.project_address = address;

                // Cache the geocoding result
                this.setCache(geocodeCacheKey, {
                    center: this.siteData.center,
                    timestamp: Date.now()
                });

                this.info('✅ Project address geocoded successfully:', this.siteData.center);
                return this.siteData.center;
            } else {
                this.warn('Failed to geocode project address:', data.error);
                return null;
            }
        } catch (error) {
            this.error('Error geocoding project address:', error);
            return null;
        }
    }

    async fetchWithRetry(url, options = {}) {
        const {
            timeout = 10000,
            retries = 2,
            ...fetchOptions
        } = options;

        for (let attempt = 1; attempt <= retries + 1; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), timeout);

                const response = await fetch(url, {
                    ...fetchOptions,
                    signal: controller.signal
                });

                clearTimeout(timeoutId);
                return response;

            } catch (error) {
                if (attempt === retries + 1) {
                    throw error;
                }

                this.warn(`Request attempt ${attempt} failed, retrying:`, error.message);
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }

    getFromCache(key) {
        try {
            const cached = localStorage.getItem(`siteInspector_${key}`);
            return cached ? JSON.parse(cached) : null;
        } catch {
            return null;
        }
    }

    setCache(key, data) {
        try {
            localStorage.setItem(`siteInspector_${key}`, JSON.stringify(data));
        } catch (error) {
            this.warn('Failed to cache data:', error);
        }
    }



    async initializeMap() {
        this.info('Initializing Mapbox map...');

        try {
            // Check if map container exists
            const mapContainer = document.getElementById('inspectorMap');
            if (!mapContainer) {
                throw new Error('Map container element not found');
            }

            // Validate required dependencies with better error messages
            if (typeof mapboxgl === 'undefined') {
                throw new Error('MapboxGL library not loaded - check CDN connection');
            }

            // MapboxDraw is not critical for basic map functionality
            if (typeof MapboxDraw === 'undefined') {
                this.warn('MapboxDraw library not loaded - drawing features will be limited');
            }

            // Get Mapbox token with caching and retry logic
            let tokenData;
            try {
                tokenData = await this.getMapboxTokenWithRetry();
            } catch (tokenError) {
                this.error('Failed to get Mapbox token after retries:', tokenError);
                throw new Error('Unable to authenticate with Mapbox services');
            }

            mapboxgl.accessToken = tokenData.token;
            this.info('✅ Mapbox token set successfully');

            // Determine map center - use project coordinates if available
            let center = [174.7633, -36.8485]; // Default Auckland fallback
            let zoom = 13; // Default zoom

            if (this.siteData.center) {
                center = [this.siteData.center.lng, this.siteData.center.lat];
                zoom = 16; // Higher zoom for specific locations
                this.info('✅ Using project location for map center:', center, 'for address:', this.siteData.project_address);
            } else {
                this.warn('⚠️ No project coordinates available, using Auckland fallback:', center);
            }

            // Initialize map with timeout and better error handling
            this.map = new mapboxgl.Map({
                container: 'inspectorMap',
                style: 'mapbox://styles/mapbox/outdoors-v12',
                center: center,
                zoom: zoom,
                pitch: 0,
                bearing: 0,
                attributionControl: false, // Disable to reduce clutter
                logoPosition: 'bottom-left',
                maxZoom: 22,
                minZoom: 8
            });

            // Wait for map to load with simple timeout
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Map loading timeout'));
                }, 15000);

                this.map.on('load', () => {
                    clearTimeout(timeout);
                    this.setupMapControls();
                    this.setup3DTerrain();
                    this.info('Map loaded successfully');
                    resolve();
                });

                this.map.on('error', (e) => {
                    clearTimeout(timeout);
                    reject(new Error(`Map error: ${e.error?.message || 'Unknown map error'}`));
                });
            });

        } catch (error) {
            this.error('Failed to initialize map:', error);
            throw error;
        }
    }

    async getMapboxTokenWithRetry() {
        try {
            const tokenResponse = await fetch('/api/mapbox-token');

            if (!tokenResponse.ok) {
                throw new Error(`HTTP ${tokenResponse.status}: ${tokenResponse.statusText}`);
            }

            const tokenData = await tokenResponse.json();

            if (!tokenData.success || !tokenData.token) {
                throw new Error(tokenData.error || 'No token in response');
            }

            return tokenData;
        } catch (error) {
            this.error('Failed to get Mapbox token:', error);
            throw error;
        }
    }

    setupMapControls() {
        try {
            // Add scale control at bottom-right, 120px from bottom to avoid ADAM chat widget
            this.map.addControl(new mapboxgl.ScaleControl({
                maxWidth: 100,
                unit: 'metric'
            }), 'bottom-right');

            // Add navigation controls at bottom-right, 120px from bottom to avoid ADAM chat widget
            this.map.addControl(new mapboxgl.NavigationControl({
                showCompass: true,
                showZoom: true,
                visualizePitch: true
            }), 'bottom-right');

            this.info('✅ Map controls added successfully');
        } catch (error) {
            this.error('Failed to add map controls:', error);
            // Don't throw - basic map still works
        }
    }

    async initializeManagers() {
        this.info('Initializing manager modules...');

        try {
            // Validate map is ready
            if (!this.map) {
                throw new Error('Map not initialized before managers');
            }

            // Initialize MapboxGL Draw with better error handling
            this.info('Creating MapboxDraw instance...');
            try {
                this.draw = new MapboxDraw({
                    displayControlsDefault: false,
                    controls: {},
                    styles: [
                        {
                            'id': 'gl-draw-polygon-fill-inactive',
                            'type': 'fill',
                            'filter': ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
                            'paint': {
                                'fill-color': '#007cbf',
                                'fill-opacity': 0.2
                            }
                        },
                        {
                            'id': 'gl-draw-polygon-stroke-inactive',
                            'type': 'line',
                            'filter': ['all', ['==', 'active', 'false'], ['==', '$type', 'Polygon'], ['!=', 'mode', 'static']],
                            'paint': {
                                'line-color': '#007cbf',
                                'line-width': 3
                            }
                        },
                        {
                            'id': 'gl-draw-polygon-fill-active',
                            'type': 'fill',
                            'filter': ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
                            'paint': {
                                'fill-color': '#007cbf',
                                'fill-opacity': 0.3
                            }
                        },
                        {
                            'id': 'gl-draw-polygon-stroke-active',
                            'type': 'line',
                            'filter': ['all', ['==', 'active', 'true'], ['==', '$type', 'Polygon']],
                            'paint': {
                                'line-color': '#007cbf',
                                'line-width': 3
                            }
                        }
                    ]
                });

                // Add Draw control to map
                this.info('Adding Draw control to map...');
                this.map.addControl(this.draw);
                this.info('✅ Draw control added successfully');
            } catch (drawError) {
                this.error('Failed to initialize MapboxDraw:', drawError);
                this.draw = null; // Fallback to null
            }

            // Initialize managers with better error handling and fallbacks
            this.info('Creating manager instances...');

            const managerInitResults = {};

            // Initialize SiteBoundaryManager (critical)
            try {
                this.siteBoundaryManager = new SiteBoundaryManager(this.map, this.draw);
                await this.siteBoundaryManager.initialize();
                managerInitResults.siteBoundary = 'success';
                this.info('✅ SiteBoundaryManager initialized');
            } catch (error) {
                this.error('Failed to initialize SiteBoundaryManager:', error);
                managerInitResults.siteBoundary = 'failed';
            }

            // Initialize PropertySetbacksManager (critical)
            try {
                this.propertySetbacksManager = new PropertySetbacksManager(this.map);
                await this.propertySetbacksManager.initialize();
                managerInitResults.propertySetbacks = 'success';
                this.info('✅ PropertySetbacksManager initialized');
            } catch (error) {
                this.error('Failed to initialize PropertySetbacksManager:', error);
                managerInitResults.propertySetbacks = 'failed';
            }

            // Initialize FloorplanManager with fallback check
            try {
                if (typeof FloorplanManager !== 'undefined') {
                    this.floorplanManager = new FloorplanManager(this.map);
                    await this.floorplanManager.initialize();
                    managerInitResults.floorplan = 'success';
                    this.info('✅ FloorplanManager initialized');
                } else {
                    throw new Error('FloorplanManager class not available');
                }
            } catch (error) {
                this.error('Failed to initialize FloorplanManager:', error);
                this.floorplanManager = null;
                managerInitResults.floorplan = 'failed';
                // Create minimal floorplan fallback
                this.createFloorplanFallback();
            }

            // Initialize Map Features Manager
            try {
                this.mapFeaturesManager = new MapFeaturesManager(this.map);
                await this.mapFeaturesManager.initialize();

                // Make mapFeaturesManager globally accessible
                window.mapFeaturesManager = this.mapFeaturesManager;

                managerInitResults.mapFeatures = 'success';
                this.info('✅ MapFeaturesManager initialized');
            } catch (error) {
                this.error('Failed to initialize MapFeaturesManager:', error);
                managerInitResults.mapFeatures = 'failed';

                // Create a minimal fallback for dimensions functionality
                this.createFallbackDimensionsHandler();
            }

            // Initialize UIPanelManager (critical for UI)
            try {
                this.uiPanelManager = new UIPanelManager();
                await this.uiPanelManager.initialize();
                managerInitResults.uiPanel = 'success';
                this.info('✅ UIPanelManager initialized');
            } catch (error) {
                this.error('Failed to initialize UIPanelManager:', error);
                managerInitResults.uiPanel = 'failed';
            }

            // Check if critical managers failed
            const criticalManagers = ['siteBoundary', 'propertySetbacks', 'uiPanel'];
            const failedCritical = criticalManagers.filter(manager => managerInitResults[manager] === 'failed');

            if (failedCritical.length > 0) {
                this.warn(`Some critical managers failed to initialize: ${failedCritical.join(', ')}`);
                // Continue anyway but with reduced functionality
            }

            this.info('Manager initialization completed with results:', managerInitResults);

        } catch (error) {
            this.error('Failed to initialize managers:', error);
            throw error;
        }
    }

    createFloorplanFallback() {
        this.info('Creating FloorplanManager fallback');

        // Hide floorplan-related UI elements
        const floorplanCard = document.querySelector('.inspector-card[data-card="floorplan"]');
        if (floorplanCard) {
            floorplanCard.style.display = 'none';
        }

        // Create minimal floorplan manager with essential methods
        this.floorplanManager = {
            initialize: () => Promise.resolve(),
            cleanup: () => {},
            isDrawing: false,
            stopDrawing: () => {},
            removeFloorplanFromMap: () => {}
        };
    }

    setupEventHandlers() {
        this.info('Setting up inter-manager event handlers...');

        // Handle setback calculations
        window.eventBus.on('recalculate-buildable-area', async (data) => {
            await this.handleBuildableAreaCalculation(data);
        });

        // Handle preview buildable area calculations
        window.eventBus.on('preview-buildable-area', async (data) => {
            await this.handleBuildableAreaPreview(data);
        });

        // Handle setback updates
        window.eventBus.on('setbacks-updated', (data) => {
            this.handleSetbacksUpdated(data);
        });

        // Handle site boundary changes
        window.eventBus.on('site-boundary-created', (data) => {
            this.handleSiteBoundaryCreated(data);
        });

        // Handle site boundary loaded
        window.eventBus.on('site-boundary-loaded', (data) => {
            this.handleSiteBoundaryLoaded(data);
        });

        // Handle tool conflicts
        window.eventBus.on('tool-activated', (toolName) => {
            this.handleToolActivated(toolName);
        });

        // Handle panel state changes
        window.eventBus.on('inspector-panel-toggled', (data) => {
            this.handlePanelToggled(data);
        });

        this.info('Event handlers setup completed');
    }

    async handleBuildableAreaPreview(data) {
        // Skip logging for preview to reduce console noise
        try {
            // Get site coordinates from the Site Boundary Manager
            const boundaryManager = this.siteBoundaryManager;
            if (!boundaryManager || !boundaryManager.hasSiteBoundary()) {
                return; // Silently return for preview - no error needed
            }

            const sitePolygon = boundaryManager.getSitePolygon();
            if (!sitePolygon || !sitePolygon.geometry || !sitePolygon.geometry.coordinates) {
                return; // Silently return for preview
            }

            const siteCoords = sitePolygon.geometry.coordinates[0];

            // Create edge classifications with precise setback mapping
            const edgeClassifications = [];
            if (data.selectedEdges.front && data.selectedEdges.back) {
                data.polygonEdges.forEach((edge, index) => {
                    let type = 'side';
                    let setback = parseFloat(data.sideSetback) || 0; // Default to 0 if NaN

                    if (index === data.selectedEdges.front.index) {
                        type = 'front';
                        setback = parseFloat(data.frontSetback) || 0; // Default to 0 if NaN
                    } else if (index === data.selectedEdges.back.index) {
                        type = 'back';
                        setback = parseFloat(data.backSetback) || 0; // Default to 0 if NaN
                    }
                    // All other edges remain as 'side' with sideSetback

                    edgeClassifications.push({
                        index: index,
                        type: type,
                        setback: setback // Always include the exact setback value
                    });
                });
            } else {
                // If no specific edges selected, all edges use side setback
                data.polygonEdges.forEach((edge, index) => {
                    let setback = parseFloat(data.sideSetback) || 0; // Default to 0 if NaN

                    edgeClassifications.push({
                        index: index,
                        type: 'side',
                        setback: setback // Always include the exact setback value
                    });
                });
            }

            const requirements = {
                front_setback: data.frontSetback,
                side_setback: data.sideSetback,
                rear_setback: data.backSetback,
                ...(this.siteData.council_requirements || {})
            };

            // Use AbortController for faster cancellation of previous requests
            if (this.previewAbortController) {
                this.previewAbortController.abort();
            }
            this.previewAbortController = new AbortController();

            const response = await fetch('/api/calculate-buildable-area', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    site_coords: siteCoords,
                    frontage: 'north', // Default frontage
                    requirements: requirements,
                    edge_classifications: edgeClassifications
                }),
                signal: this.previewAbortController.signal
            });

            if (!response.ok) {
                return; // Silently return for preview
            }

            const result = await response.json();

            if (result.buildable_coords && result.buildable_coords.length > 0) {
                this.updateBuildableAreaDisplay(result, true); // Pass true to indicate this is a preview
            }

        } catch (error) {
            // Silently handle errors for preview calculations (including aborted requests)
            if (error.name !== 'AbortError') {
                // Only log non-abort errors for debugging
                console.debug('Preview calculation failed (non-critical):', error.message);
            }
        }
    }

    async handleBuildableAreaCalculation(data) {
        this.info('Handling buildable area calculation with data:', data);

        try {
            // Get site coordinates from the Site Boundary Manager
            const boundaryManager = this.siteBoundaryManager;
            if (!boundaryManager || !boundaryManager.hasSiteBoundary()) {
                throw new Error('No site boundary available for calculation');
            }

            const sitePolygon = boundaryManager.getSitePolygon();
            if (!sitePolygon || !sitePolygon.geometry || !sitePolygon.geometry.coordinates) {
                throw new Error('Invalid site polygon data');
            }

            const siteCoords = sitePolygon.geometry.coordinates[0];
            this.info('Using site coordinates:', siteCoords.length, 'points');

            // Create edge classifications with precise setback mapping
            const edgeClassifications = [];
            if (data.selectedEdges.front && data.selectedEdges.back) {
                data.polygonEdges.forEach((edge, index) => {
                    let type = 'side';
                    let setback = parseFloat(data.sideSetback) || 0; // Default to 0 if NaN

                    if (index === data.selectedEdges.front.index) {
                        type = 'front';
                        setback = parseFloat(data.frontSetback) || 0; // Default to 0 if NaN
                    } else if (index === data.selectedEdges.back.index) {
                        type = 'back';
                        setback = parseFloat(data.backSetback) || 0; // Default to 0 if NaN
                    }
                    // All other edges remain as 'side' with sideSetback

                    edgeClassifications.push({
                        index: index,
                        type: type,
                        setback: setback // Always include the exact setback value
                    });
                });
            } else {
                // If no specific edges selected, all edges use side setback
                data.polygonEdges.forEach((edge, index) => {
                    let setback = parseFloat(data.sideSetback) || 0; // Default to 0 if NaN

                    edgeClassifications.push({
                        index: index,
                        type: 'side',
                        setback: setback // Always include the exact setback value
                    });
                });
            }

            const requirements = {
                front_setback: data.frontSetback,
                side_setback: data.sideSetback,
                rear_setback: data.backSetback,
                ...(this.siteData.council_requirements || {})
            };

            this.info('Sending buildable area calculation request with edge classifications:', edgeClassifications);

            const response = await fetch('/api/calculate-buildable-area', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    site_coords: siteCoords,
                    frontage: 'north', // Default frontage
                    requirements: requirements,
                    edge_classifications: edgeClassifications
                })
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            this.info('Buildable area calculation result:', result);

            if (result.buildable_coords && result.buildable_coords.length > 0) {
                this.info('Buildable area calculated successfully with', result.buildable_coords.length, 'coordinates');
                this.updateBuildableAreaDisplay(result);

                // Save buildable area to project
                await this.saveBuildableAreaToProject(result, data);

                if (this.uiPanelManager && this.uiPanelManager.showSuccess) {
                    this.uiPanelManager.showSuccess('Buildable area calculated successfully');
                }

                // Emit success event
                window.eventBus.emit('setbacks-applied');

            } else {
                throw new Error(result.error || 'No buildable area calculated - result may be empty');
            }

        } catch (error) {
            this.error('Buildable area calculation failed:', error);

            if (this.uiPanelManager && this.uiPanelManager.showError) {
                this.uiPanelManager.showError('Failed to calculate buildable area: ' + error.message);
            } else{
                alert('Failed to calculate buildable area: ' + error.message);
            }
        }
    }

    handleSetbacksUpdated(data) {
        this.info('Setbacks updated:', data);
        // Additional logic for handling setback updates can be added here
    }

    handleSiteBoundaryCreated(data) {
        this.info('Site boundary created, updating site data');
        this.siteData.coordinates = data.coordinates;
        this.siteData.area = data.area;
        this.siteData.center = {
            lng: data.coordinates.reduce((sum, coord) => sum + coord[0], 0) / data.coordinates.length,
            lat: data.coordinates.reduce((sum, coord) => sum + coord[1], 0) / data.coordinates.length
        };
    }

    handleSiteBoundaryLoaded(data) {
        this.info('Site boundary loaded, updating site data');
        this.siteData.coordinates = data.coordinates;
        this.siteData.area = data.area;

        // Calculate center point for the loaded boundary
        if (data.coordinates && data.coordinates.length > 0) {
            const coords = data.coordinates;
            this.siteData.center = {
                lng: coords.reduce((sum, coord) => sum + coord[0], 0) / coords.length,
                lat: coords.reduce((sum, coord) => sum + coord[1], 0) / coords.length
            };
        }

        // Emit boundary applied event to update UI flow
        window.eventBus.emit('boundary-applied');
    }

    handleToolActivated(toolName) {
        this.info('Tool activated:', toolName);

        // Stop conflicting tools
        if (toolName === 'floorplan' && this.mapFeaturesManager.isMeasuringActive()) {
            // Measuring tool will stop itself via event listener
        }

        if (toolName === 'measure' && this.floorplanManager) {
            // Stop floor plan drawing if active
            if (this.floorplanManager.stopDrawing) {
                this.floorplanManager.stopDrawing();
            }
        }
    }

    handlePanelToggled(data) {
        // Update any managers that need to know about panel state
        if (this.propertySetbacksManager && this.propertySetbacksManager.updateOverlayPosition) {
            this.propertySetbacksManager.updateOverlayPosition();
        }
    }

    updateBuildableAreaDisplay(result, isPreview = false) {
        try {
            // Remove existing buildable area layers efficiently
            const layersToRemove = ['buildable-area-fill', 'buildable-area-stroke'];
            layersToRemove.forEach(layerId => {
                if (this.map.getLayer(layerId)) {
                    this.map.removeLayer(layerId);
                }
            });

            if (this.map.getSource('buildable-area')) {
                this.map.removeSource('buildable-area');
            }

            if (result.buildable_coords && result.buildable_coords.length > 0) {
                // Convert coordinates to proper format [lng, lat] if needed
                let coordinates = result.buildable_coords;

                // More robust coordinate format detection
                if (coordinates[0] && coordinates[0].length === 2) {
                    const firstCoord = coordinates[0];
                    // Check if coordinates are in [lat, lng] format (latitude typically between -90 and 90)
                    if (Math.abs(firstCoord[0]) <= 90 && Math.abs(firstCoord[1]) > 90) {
                        // Likely [lat, lng] format, flip to [lng, lat]
                        coordinates = coordinates.map(coord => [coord[1], coord[0]]);
                        if (!isPreview) {
                            this.info('Corrected coordinate format from [lat, lng] to [lng, lat]');
                        }
                    }
                }

                // Ensure coordinates form a closed polygon
                const firstCoord = coordinates[0];
                const lastCoord = coordinates[coordinates.length - 1];
                if (firstCoord[0] !== lastCoord[0] || firstCoord[1] !== lastCoord[1]) {
                    coordinates.push([...firstCoord]);
                }

                this.map.addSource('buildable-area', {
                    'type': 'geojson',
                    'data': {
                        'type': 'Feature',
                        'geometry': {
                            'type': 'Polygon',
                            'coordinates': [coordinates]
                        },
                        'properties': {
                            'area_m2': result.buildable_area_m2 || 0,
                            'type': 'buildable-area',
                            'is_preview': isPreview
                        }
                    }
                });

                // Different styling for preview vs confirmed with better visual feedback
                const fillColor = isPreview ? '#002040' : '#002040';
                const fillOpacity = isPreview ? 0.2 : 0.4;
                const strokeColor = isPreview ? '#002040' : '#002040';
                const strokeOpacity = isPreview ? 0.7 : 0.8;
                const strokeWidth = isPreview ? 2 : 3;

                // Add fill layer
                this.map.addLayer({
                    'id': 'buildable-area-fill',
                    'type': 'fill',
                    'source': 'buildable-area',
                    'layout': {},
                    'paint': {
                        'fill-color': fillColor,
                        'fill-opacity': fillOpacity
                    }
                });

                // Add stroke layer for better visibility
                this.map.addLayer({
                    'id': 'buildable-area-stroke',
                    'type': 'line',
                    'source': 'buildable-area',
                    'layout': {},
                    'paint': {
                        'line-color': strokeColor,
                        'line-width': strokeWidth,
                        'line-opacity': strokeOpacity
                    }
                });

                if (!isPreview) {
                    this.info(`Buildable area displayed on map with ${coordinates.length - 1} vertices`);
                }

                // Update legend to show buildable area
                this.updateBuildableAreaLegend(true);
            } else {
                if (!isPreview) {
                    this.warn('No buildable coordinates to display');
                }
                this.updateBuildableAreaLegend(false);
            }
        } catch (error) {
            this.error('Error updating buildable area display:', error);
        }
    }

    setup3DTerrain() {
        // Make 3D terrain optional and non-blocking
        try {
            // Ensure map is ready before adding sources
            if (!this.map.isStyleLoaded()) {
                this.map.once('styledata', () => {
                    this.setup3DTerrain();
                });
                return;
            }

            // Add terrain source with timeout
            setTimeout(() => {
                try {
                    if (!this.map.getSource('mapbox-dem')) {
                        this.map.addSource('mapbox-dem', {
                            'type': 'raster-dem',
                            'url': 'mapbox://mapbox.terrain-rgb',
                            'tileSize': 512,
                            'maxzoom': 14
                        });
                    }

                    // Add terrain layer with moderate exaggeration
                    this.map.setTerrain({ 
                        'source': 'mapbox-dem', 
                        'exaggeration': 1.2 
                    });

                    // Add sky layer with improved settings
                    if (!this.map.getLayer('sky')) {
                        this.map.addLayer({
                            'id': 'sky',
                            'type': 'sky',
                            'paint': {
                                'sky-type': 'atmosphere',
                                'sky-atmosphere-sun': [0.0, 90.0],
                                'sky-atmosphere-sun-intensity': 15
                            }
                        });
                    }

                    // Add fog for better 3D effect
                    this.map.setFog({
                        'range': [1, 20],
                        'horizon-blend': 0.3,
                        'color': 'white',
                        'high-color': '#add8e6',
                        'space-color': '#d8f2ff',
                        'star-intensity': 0.0
                    });

                    this.info('✅ 3D terrain, sky layer, and fog added to map');
                } catch (terrainError) {
                    this.warn('Failed to add 3D terrain features:', terrainError.message);
                    // Don't throw - basic map still works
                }
            }, 2000); // Delay 3D terrain to not block map loading

        } catch (error) {
            this.warn('Error setting up 3D terrain:', error.message);
            // Don't throw - basic map still works
        }
    }

    showMapError(message) {
        this.error('Map error:', message);

        const mapLoading = document.getElementById('mapLoading');
        const mapError = document.getElementById('mapError');
        const errorDetails = document.getElementById('errorDetails');

        if (mapLoading) mapLoading.style.display = 'none';
        if (mapError) mapError.style.display = 'flex';
        if (errorDetails) errorDetails.textContent = message;
    }

    // Public API methods
    getSiteData() {
        const siteData = {
            ...this.siteData
        };

        // Add current site boundary if available
        if (this.siteBoundaryManager && this.siteBoundaryManager.hasSiteBoundary()) {
            const sitePolygon = this.siteBoundaryManager.getSitePolygon();
            if (sitePolygon && sitePolygon.geometry && sitePolygon.geometry.coordinates) {
                siteData.coordinates = sitePolygon.geometry.coordinates[0];

                // Calculate terrain bounds if not already present
                if (!siteData.terrainBounds) {
                    siteData.terrainBounds = this.siteBoundaryManager.calculateTerrainBounds(siteData.coordinates);
                    this.info('Generated terrain bounds for site data:', siteData.terrainBounds);
                }
            }
        }

        // Add current buildable area if available
        if (this.propertySetbacksManager) {
            const buildableArea = this.propertySetbacksManager.getCurrentBuildableArea();
            if (buildableArea) {
                siteData.buildable_area = buildableArea;
            }
        }

        return siteData;
    }

    getMap() {
        return this.map;
    }

    getDraw() {
        return this.draw;
    }

    /**
     * Get manager instance by name
     * @param {string} managerName - Name of the manager
     * @returns {Object|null} Manager instance or null
     */
    getManager(managerName) {
        const managerMap = {
            'siteBoundary': this.siteBoundaryManager,
            'propertySetbacks': this.propertySetbacksManager,
            'floorplan': this.floorplanManager,
            'mapFeatures': this.mapFeaturesManager,
            'uiPanel': this.uiPanelManager
        };

        return managerMap[managerName] || null;
    }

    /**
     * Create fallback dimensions handler when MapFeaturesManager fails
     */
    createFallbackDimensionsHandler() {
        this.info('Creating fallback dimensions handler');

        window.mapFeaturesManager = {
            toggleDimensions: () => {
                this.info('Fallback dimensions toggle called');

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

                // Check current state by looking at button/toggle state first, then layers
                const dimensionsBtn = document.querySelector('.dimensions-toggle-btn');
                const dimensionsToggle = document.querySelector('.dimensions-toggle-switch input');
                
                let isCurrentlyVisible = false;
                
                // Check toggle state first
                if (dimensionsToggle) {
                    isCurrentlyVisible = dimensionsToggle.checked;
                } else {
                    // Fallback: check layer visibility
                    for (const layerId of dimensionLayers) {
                        if (this.map.getLayer(layerId)) {
                            const visibility = this.map.getLayoutProperty(layerId, 'visibility');
                            if (visibility !== 'none') {
                                isCurrentlyVisible = true;
                                break;
                            }
                        }
                    }
                }

                // Toggle to opposite state
                const newVisibility = isCurrentlyVisible ? 'none' : 'visible';
                const newToggleState = !isCurrentlyVisible;

                this.info(`Toggling dimensions from ${isCurrentlyVisible ? 'visible' : 'hidden'} to ${newToggleState ? 'visible' : 'hidden'}`);

                // Apply new visibility to all dimension layers
                let layersUpdated = 0;
                dimensionLayers.forEach(layerId => {
                    if (this.map.getLayer(layerId)) {
                        this.map.setLayoutProperty(layerId, 'visibility', newVisibility);
                        layersUpdated++;
                    }
                });

                // Update button and toggle states
                if (dimensionsBtn) {
                    if (newToggleState) {
                        dimensionsBtn.classList.add('active');
                    } else {
                        dimensionsBtn.classList.remove('active');
                    }
                }

                if (dimensionsToggle) {
                    dimensionsToggle.checked = newToggleState;
                }

                // Force map repaint to ensure changes are visible
                if (this.map) {
                    this.map.triggerRepaint();
                }

                this.info(`Fallback dimensions toggled: ${layersUpdated} layers set to ${newVisibility}, toggle state: ${newToggleState}`);
            },

            // Helper method to check if dimensions are visible
            areDimensionsVisible: () => {
                const dimensionsToggle = document.querySelector('.dimensions-toggle-switch input');
                if (dimensionsToggle) {
                    return dimensionsToggle.checked;
                }
                
                // Fallback: check actual layer visibility
                const primaryLayers = ['boundary-dimension-labels', 'buildable-area-dimension-labels'];
                for (const layerId of primaryLayers) {
                    if (this.map.getLayer(layerId)) {
                        const visibility = this.map.getLayoutProperty(layerId, 'visibility');
                        if (visibility !== 'none') {
                            return true;
                        }
                    }
                }
                return false;
            }
        };
    }

    updateBuildableAreaLegend(show) {
        const legendContent = document.getElementById('legendContent');
        if (!legendContent) return;

        // Find or create buildable area legend item
        let buildableAreaItem = legendContent.querySelector('.legend-buildable-area-item');

        if (show) {
            if (!buildableAreaItem) {
                buildableAreaItem = document.createElement('div');
                buildableAreaItem.className = 'legend-item legend-buildable-area-item';
                buildableAreaItem.innerHTML = `
                    <div class="legend-color" style="background-color: #002040; opacity: 0.4;"></div>
                    <span class="legend-label">Buildable Area</span>
                `;
                legendContent.appendChild(buildableAreaItem);
            }
            buildableAreaItem.style.display = 'flex';
        } else if (buildableAreaItem) {
            buildableAreaItem.style.display = 'none';
        }
    }

    isReady() {
        return this.isInitialized;
    }

    getProjectIdFromUrl() {
        const urlParams = new URLSearchParams(window.location.search);
        let projectId = urlParams.get('project_id') || urlParams.get('project');

        // Clean up any malformed project IDs that might have extra parameters
        if (projectId && projectId.includes('?')) {
            projectId = projectId.split('?')[0];
            this.info('Cleaned malformed project ID from URL:', projectId);
        }

        // Validate project ID format
        if (projectId) {
            projectId = String(projectId).trim();
            if (!/^\d+$/.test(projectId)) {
                this.warn('Invalid project ID format in URL:', projectId);
                return null;
            }
        }

        return projectId;
    }

    captureTerrainBounds() {
        // Capture current map view bounds for terrain analysis
        if (!this.map) {
            this.warn('Map not available for terrain bounds capture');
            return null;
        }

        try {
            const bounds = this.map.getBounds();
            const center = this.map.getCenter();
            const zoom = this.map.getZoom();

            // Calculate approximate dimensions in degrees
            const width = bounds.getEast() - bounds.getWest();
            const height = bounds.getNorth() - bounds.getSouth();

            return {
                bounds: {
                    north: bounds.getNorth(),
                    south: bounds.getSouth(),
                    east: bounds.getEast(),
                    west: bounds.getWest()
                },
                center: [center.lng, center.lat],
                zoom: zoom,
                width: width,
                height: height,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            this.error('Error capturing terrain bounds:', error);
            return null;
        }
    }

    async saveBuildableAreaToProject(result, setbackData) {
        try {
            const projectId = this.getProjectIdFromUrl();

            if (!projectId) {
                this.warn('No project ID found, cannot save buildable area');
                return;
            }

            // Capture current map view for terrain analysis
            const terrainBounds = this.captureTerrainBounds();

            // Get site coordinates from the boundary manager for reconstruction
            let siteCoords = null;
            let siteArea = null;
            if (this.siteBoundaryManager && this.siteBoundaryManager.hasSiteBoundary()) {
                const sitePolygon = this.siteBoundaryManager.getSitePolygon();
                if (sitePolygon && sitePolygon.geometry && sitePolygon.geometry.coordinates) {
                    siteCoords = sitePolygon.geometry.coordinates[0];
                    siteArea = this.siteBoundaryManager.calculatePolygonArea(siteCoords);
                    this.info('Site coordinates captured for snapshot:', siteCoords.length, 'points');
                }
            }

            const snapshotData = {
                buildable_coords: result.buildable_coords,
                buildable_area_m2: result.buildable_area_m2,
                site_area_m2: result.site_area_m2,
                coverage_ratio: result.coverage_ratio,
                front_setback: setbackData.frontSetback,
                rear_setback: setbackData.backSetback,
                side_setback: setbackData.sideSetback,
                selected_edges: setbackData.selectedEdges,
                calculation_method: result.calculation_method,
                terrain_bounds: terrainBounds,
                site_coords: siteCoords, // Include original site coordinates for boundary reconstruction
                site_area_calculated: siteArea, // Include calculated site area
                timestamp: new Date().toISOString()
            };

            const response = await fetch(`/api/project/${projectId}/snapshot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    snapshot_type: 'buildable_area',
                    snapshot_data: JSON.stringify(snapshotData)
                })
            });

            const data = await response.json();

            if (!data.success) {
                this.error('Failed to save buildable area', data.error);
            } else {
                this.info('Buildable area saved successfully to project', projectId);
            }

        } catch (error) {
            this.error('Error saving buildable area:', error);
        }
    }

    async loadProjectData() {
        // Get project ID from URL parameter
        const projectId = this.getProjectIdFromUrl();
        this.info(`Project ID from URL: ${projectId || 'none'}`, '');

        if (projectId) {
            try {
                // Load project data from API
                const projectResponse = await window.apiClient.get(`/project/${projectId}`);
                if (projectResponse.success) {
                    const project = projectResponse.project;
                    this.info(`✅ Project loaded: ${project.name} at ${project.address}`, '');

                    // Try to geocode the project address
                    const geocodeResponse = await window.apiClient.post('/geocode-location', {
                        query: project.address
                    });

                    if (geocodeResponse.success && geocodeResponse.location) {
                        const coords = [geocodeResponse.location.lng, geocodeResponse.location.lat];
                        this.info(`✅ Project geocoded successfully to: ${coords}`, '');
                        this.map.flyTo({
                            center: coords,
                            zoom: 16,
                            essential: true
                        });
                        return;
                    }
                }
            } catch (error) {
                this.warn(`Failed to load project data: ${error.message}`, '');
            }
        }

        // Fallback: try session storage for backward compatibility
        const projectAddress = sessionStorage.getItem('project_site_address');
        const projectName = sessionStorage.getItem('project_name');

        if (projectAddress) {
            this.info(`Project address from session: ${projectAddress}`, '');

            try {
                const response = await window.apiClient.post('/geocode-location', {
                    query: projectAddress
                });

                if (response.success && response.location) {
                    const coords = [response.location.lng, response.location.lat];
                    this.info(`✅ Project geocoded successfully to: ${coords}`, '');
                    this.map.flyTo({
                        center: coords,
                        zoom: 16,
                        essential: true
                    });
                    return;
                }
            } catch (error) {
                this.warn(`Geocoding failed for project address: ${error.message}`, '');
            }
        }

        this.warn('⚠️ Project address could not be loaded, proceeding with default location', '');
    }
}

// Global helper functions (for template compatibility)
window.toggleInspectorPanel = function() {
    if (window.siteInspectorCore && window.siteInspectorCore.uiPanelManager) {
        window.siteInspectorCore.uiPanelManager.toggleInspectorPanel();
    }
};

window.toggleSiteInfoExpanded = function() {
    if (window.siteInspectorCore && window.siteInspectorCore.uiPanelManager) {
        window.siteInspectorCore.uiPanelManager.toggleSiteInfoExpanded();
    }
};

window.toggle3DBuildings = function() {
    if (window.siteInspectorCore && window.siteInspectorCore.mapFeaturesManager) {
        window.siteInspectorCore.mapFeaturesManager.toggle3DBuildings();
    }
};



// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async function() {
    console.log('[SiteInspectorCore] DOM loaded, initializing modular site inspector...');

    try {
        // Wait for core dependencies
        if (typeof BaseManager === 'undefined') {
            console.log('[SiteInspectorCore] Waiting for core dependencies...');
            await new Promise(resolve => {
                const checkDeps = () => {
                    if (typeof BaseManager !== 'undefined') {
                        resolve();
                    } else {
                        setTimeout(checkDeps, 100);
                    }
                };
                checkDeps();
            });
        }

        // Only create site inspector if it doesn't already exist
        if (!window.siteInspectorCore) {
            window.siteInspectorCore = new SiteInspectorCore();
            await window.siteInspectorCore.initialize();
        }

        console.log('[SiteInspectorCore] ✅ Modular site inspector initialized successfully');

    } catch (error) {
        console.error('[SiteInspectorCore] ❌ Initialization failed:', error);

        // Show user-friendly error message
        const mapContainer = document.getElementById('inspectorMap');
        if (mapContainer) {
            mapContainer.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; background: #f8f9fa; color: #666; flex-direction: column; text-align: center; padding: 20px;">
                    <h3 style="margin-bottom: 10px;">Map Loading Error</h3>
                    <p style="margin-bottom: 15px;">Unable to initialize the map. Please refresh the page to try again.</p>
                    <button onclick="location.reload()" style="padding: 10px 20px; background: #007cbf; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        Refresh Page
                    </button>
                    <p style="margin-top: 15px; font-size: 12px; color: #999;">Error: ${error.message}</p>
                </div>
            `;
        }
    }
});

window.SiteInspectorCore = SiteInspectorCore;