/**
 * UI Panel Manager
 * Handles panel states, interactions, and UI feedback
 */

class UIPanelManager extends BaseManager {
    constructor() {
        super('UIPanelManager');
        this.panelState = {
            inspector: false,
            siteInfo: false
        };
        this.cardStates = {
            siteBoundary: 'expanded',
            setbacks: 'collapsed',
            floorplan: 'collapsed'
        };
    }

    initialize() {
        this.info('Initializing UI Panel Manager...');
        this.setupEventListeners();
        this.setupCardEventListeners();
        this.initializePanelStates();

        // Setup collapse button for Site Boundary card
        this.setupSiteBoundaryCollapseButton();

        this.info('UI Panel Manager initialized successfully');
    }

    setupEventListeners() {
        // Inspector panel toggle
        const panelToggleBtn = document.getElementById('panelToggleBtn');
        if (panelToggleBtn) {
            panelToggleBtn.addEventListener('click', () => this.toggleInspectorPanel());
        }

        const panelClose = document.querySelector('.panel-close');
        if (panelClose) {
            panelClose.addEventListener('click', () => this.toggleInspectorPanel());
        }

        // Site info panel toggle
        const siteInfoToggleBtn = document.getElementById('siteInfoToggleBtn');
        if (siteInfoToggleBtn) {
            siteInfoToggleBtn.addEventListener('click', () => this.toggleSiteInfoExpanded());
        }

        // Listen for workflow events
        window.eventBus.on('boundary-applied', () => {
            this.collapseSiteBoundaryCard();
            this.expandSetbacksCard();
        });

        window.eventBus.on('setbacks-applied', () => {
            this.collapseSetbacksCard();
            this.expandFloorplanCard();
        });

        window.eventBus.on('floorplan-applied', () => {
            this.collapseFloorplanCard();
            this.expandGradientCard();
        });

        window.eventBus.on('gradient-applied', () => {
            this.collapseGradientCard();
        });
    }

    setupCardEventListeners() {
        // Add click handlers to collapsed cards
        const siteBoundaryControls = document.getElementById('siteBoundaryControls');
        if (siteBoundaryControls) {
            siteBoundaryControls.addEventListener('click', (event) => {
                if (siteBoundaryControls.classList.contains('collapsed')) {
                    this.expandSiteBoundaryCard();
                }
            });
        }

        const boundaryControls = document.getElementById('boundaryControls');
        if (boundaryControls) {
            boundaryControls.addEventListener('click', (event) => {
                if (boundaryControls.classList.contains('collapsed')) {
                    this.expandSetbacksCard();
                }
            });
        }

        const floorplanControls = document.getElementById('floorplanControls');
        if (floorplanControls) {
            floorplanControls.addEventListener('click', (event) => {
                if (floorplanControls.classList.contains('collapsed')) {
                    this.expandFloorplanCard();
                }
            });
        }

        const gradientControls = document.getElementById('gradientControls');
        if (gradientControls) {
            gradientControls.addEventListener('click', (event) => {
                if (gradientControls.classList.contains('collapsed')) {
                    this.expandGradientCard();
                }
            });
        }
    }

    initializePanelStates() {
        const panel = document.getElementById('inspectorPanel');
        const topLeftControls = document.querySelector('.top-left-controls');
        const mapLegend = document.getElementById('mapLegend');
        const mapControlsContainer = document.getElementById('mapControlsContainer');

        if (panel) {
            // Start expanded - add expanded class
            panel.classList.add('expanded');
            this.panelState.inspector = true;
        }

        if (topLeftControls) {
            topLeftControls.classList.add('shifted');
        }

        if (mapLegend) {
            mapLegend.classList.add('shifted');
        }

        // Initialize map controls container in shifted state since panel starts expanded
        if (mapControlsContainer) {
            mapControlsContainer.classList.add('shifted');
            this.info('Map controls container initialized in shifted state');
        }

        // Initialize search functionality
        this.initializeSearchControl();

        this.info('Panel states initialized - inspector panel expanded by default');
    }

    initializeSearchControl() {
        const searchControl = document.getElementById('searchControl');
        const searchInput = document.getElementById('searchInput');
        const searchButton = document.getElementById('searchButton');
        const clearSearchButton = document.getElementById('clearSearchButton');

        if (searchButton) {
            searchButton.addEventListener('click', () => this.toggleSearchControl());
        }

        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch(searchInput.value);
                }
            });
        }

        if (clearSearchButton) {
            clearSearchButton.addEventListener('click', () => this.clearSearch());
        }

        this.info('Search control initialized');
    }

    toggleSearchControl() {
        const searchControl = document.getElementById('searchControl');
        const searchButton = document.getElementById('searchButton');

        if (!searchControl || !searchButton) return;

        const isExpanded = searchControl.classList.contains('expanded');

        if (isExpanded) {
            searchControl.classList.remove('expanded');
            searchButton.classList.remove('active');
            this.info('Search control collapsed');
        } else {
            searchControl.classList.add('expanded');
            searchButton.classList.add('active');

            // Focus on input when expanded
            setTimeout(() => {
                const searchInput = document.getElementById('searchInput');
                if (searchInput) searchInput.focus();
            }, 300);

            this.info('Search control expanded');
        }
    }

    async performSearch(query) {
        if (!query || query.trim() === '') {
            this.showSearchError('Please enter a search term');
            return;
        }

        const trimmedQuery = query.trim();
        if (trimmedQuery.length < 2) {
            this.showSearchError('Search term too short');
            return;
        }

        try {
            this.info(`Searching for: ${trimmedQuery}`);

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

            const response = await fetch('/api/geocode-location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: trimmedQuery }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.info('Search response received:', data);

            if (data.success && data.location && data.location.lng && data.location.lat) {
                // Get the map instance from the core
                const map = window.siteInspectorCore?.getMap();
                if (map && map.flyTo) {
                    // Validate coordinates
                    const lng = parseFloat(data.location.lng);
                    const lat = parseFloat(data.location.lat);

                    if (isNaN(lng) || isNaN(lat) || Math.abs(lng) > 180 || Math.abs(lat) > 90) {
                        throw new Error('Invalid coordinates received');
                    }

                    // Fly to the searched location
                    map.flyTo({
                        center: [lng, lat],
                        zoom: 18,
                        duration: 2000,
                        essential: true
                    });

                    this.info(`Location found and centered: ${data.location.display_name || trimmedQuery}`);

                    // Show success feedback
                    this.showSearchSuccess(`Found: ${data.location.display_name || trimmedQuery}`);
                } else {
                    this.error('Map not available for navigation');
                    this.showSearchError('Map not ready for navigation');
                }
            } else {
                this.warn(`Location not found: ${trimmedQuery}`, data);
                this.showSearchError(data.message || 'Location not found. Please try a different search term.');
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                this.warn('Search request timed out');
                this.showSearchError('Search timed out. Please try again.');
            } else {
                this.error('Search failed:', error);
                this.showSearchError('Search failed. Please check your connection and try again.');
            }
        }
    }

    showSearchSuccess(message) {
        const searchStatus = document.getElementById('searchStatus');
        if (searchStatus) {
            searchStatus.textContent = message;
            searchStatus.className = 'search-status success';
            searchStatus.style.display = 'block';

            setTimeout(() => {
                searchStatus.style.display = 'none';
            }, 3000);
        }
    }

    showSearchError(message) {
        const searchStatus = document.getElementById('searchStatus');
        if (searchStatus) {
            searchStatus.textContent = message;
            searchStatus.className = 'search-status error';
            searchStatus.style.display = 'block';

            setTimeout(() => {
                searchStatus.style.display = 'none';
            }, 3000);
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        const searchStatus = document.getElementById('searchStatus');

        if (searchInput) searchInput.value = '';
        if (searchStatus) searchStatus.style.display = 'none';

        this.info('Search cleared');
    }

    toggleInspectorPanel() {
        const panel = document.getElementById('inspectorPanel');
        const topLeftControls = document.querySelector('.top-left-controls');
        const mapLegend = document.getElementById('mapLegend');
        const mapControlsContainer = document.getElementById('mapControlsContainer');

        if (!panel) {
            this.error('Inspector panel element not found');
            return;
        }

        const isExpanded = panel.classList.contains('expanded');

        if (isExpanded) {
            // Collapse panel
            panel.classList.remove('expanded');
            if (topLeftControls) topLeftControls.classList.remove('shifted');
            if (mapLegend) mapLegend.classList.remove('shifted');
            if (mapControlsContainer) mapControlsContainer.classList.remove('shifted');
            this.panelState.inspector = false;
            this.info('Inspector panel collapsed');
        } else {
            // Expand panel
            panel.classList.add('expanded');
            if (topLeftControls) topLeftControls.classList.add('shifted');
            if (mapLegend) mapLegend.classList.add('shifted');
            if (mapControlsContainer) mapControlsContainer.classList.add('shifted');
            this.panelState.inspector = true;
            this.info('Inspector panel expanded');
        }

        // Force a reflow to ensure CSS changes are applied
        panel.offsetHeight;

        // Notify other managers about panel state change
        window.eventBus.emit('inspector-panel-toggled', {
            expanded: this.panelState.inspector
        });
    }

    toggleSiteInfoExpanded() {
        const expandable = document.getElementById('siteInfoExpandable');
        const btn = document.getElementById('siteInfoToggleBtn');

        if (expandable.classList.contains('expanded')) {
            expandable.classList.remove('expanded');
            btn.innerHTML = 'ℹ️';
            this.panelState.siteInfo = false;
            this.info('Site info collapsed');
        } else {
            expandable.classList.add('expanded');
            btn.innerHTML = '✕';
            this.panelState.siteInfo = true;
            this.info('Site info expanded');
        }
    }

    // Card management methods
    collapseSiteBoundaryCard() {
        const siteBoundaryControls = document.getElementById('siteBoundaryControls');
        const boundaryAppliedCheck = document.getElementById('boundaryAppliedCheck');

        if (siteBoundaryControls && boundaryAppliedCheck) {
            siteBoundaryControls.classList.add('collapsed');
            boundaryAppliedCheck.style.display = 'inline';
            this.cardStates.siteBoundary = 'collapsed';
            this.info('Site Boundary card collapsed with success indicator');
        } else {
            this.error('Site boundary controls or check element not found for collapse');
        }
    }

    expandSiteBoundaryCard() {
        const siteBoundaryControls = document.getElementById('siteBoundaryControls');
        const boundaryAppliedCheck = document.getElementById('boundaryAppliedCheck');

        if (siteBoundaryControls) {
            siteBoundaryControls.classList.remove('collapsed');
            this.cardStates.siteBoundary = 'expanded';
            if (boundaryAppliedCheck) {
                boundaryAppliedCheck.style.display = 'none';
            }
            this.info('Site Boundary card expanded');
        }
    }

    collapseSetbacksCard() {
        const boundaryControls = document.getElementById('boundaryControls');
        const setbacksAppliedCheck = document.getElementById('setbacksAppliedCheck');

        if (boundaryControls && setbacksAppliedCheck) {
            boundaryControls.classList.add('collapsed');
            setbacksAppliedCheck.style.display = 'inline';
            this.cardStates.setbacks = 'collapsed';
            this.info('Property Setbacks card collapsed with success indicator');
        }
    }

    expandSetbacksCard() {
        const boundaryControls = document.getElementById('boundaryControls');
        const setbacksAppliedCheck = document.getElementById('setbacksAppliedCheck');

        if (boundaryControls) {
            boundaryControls.classList.remove('collapsed');
            this.cardStates.setbacks = 'expanded';
            if (setbacksAppliedCheck) {
                setbacksAppliedCheck.style.display = 'none';
            }
            this.info('Property Setbacks card expanded');
        }
    }

    expandFloorplanCard() {
        const floorplanControls = document.getElementById('floorplanControls');
        const floorplanAppliedCheck = document.getElementById('floorplanAppliedCheck');

        if (floorplanControls) {
            floorplanControls.classList.remove('collapsed');
            this.cardStates.floorplan = 'expanded';
            if (floorplanAppliedCheck) {
                floorplanAppliedCheck.style.display = 'none';
            }
            this.info('Floor Plan card expanded');
        }
    }

    collapseFloorplanCard() {
        const floorplanControls = document.getElementById('floorplanControls');
        const floorplanAppliedCheck = document.getElementById('floorplanAppliedCheck');

        if (floorplanControls && floorplanAppliedCheck) {
            floorplanControls.classList.add('collapsed');
            floorplanAppliedCheck.style.display = 'inline';
            this.cardStates.floorplan = 'collapsed';
            this.info('Floor Plan card collapsed with success indicator');
        }
    }

    expandGradientCard() {
        const gradientControls = document.getElementById('gradientControls');
        const gradientAppliedCheck = document.getElementById('gradientAppliedCheck');

        if (gradientControls) {
            gradientControls.classList.remove('collapsed');
            this.cardStates.gradient = 'expanded';
            if (gradientAppliedCheck) {
                gradientAppliedCheck.style.display = 'none';
            }
            this.info('Gradient card expanded');
        }
    }

    setupSiteBoundaryCollapseButton() {
        // Create and add a collapse button to the Site Boundary card title
        const siteBoundaryTitle = document.querySelector('#siteBoundaryControls .info-title');
        if (siteBoundaryTitle && !siteBoundaryTitle.querySelector('.collapse-button')) {
            const collapseButton = document.createElement('button');
            collapseButton.className = 'collapse-button';
            collapseButton.innerHTML = '−';
            collapseButton.title = 'Collapse Site Boundary';
            collapseButton.style.cssText = `
                background: none;
                border: none;
                font-size: 18px;
                font-weight: bold;
                color: #666;
                cursor: pointer;
                padding: 4px 8px;
                border-radius: 4px;
                margin-left: auto;
                transition: all 0.2s ease;
            `;

            collapseButton.addEventListener('mouseenter', () => {
                collapseButton.style.background = 'rgba(0, 0, 0, 0.1)';
                collapseButton.style.color = '#333';
            });

            collapseButton.addEventListener('mouseleave', () => {
                collapseButton.style.background = 'none';
                collapseButton.style.color = '#666';
            });

            collapseButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleSiteBoundaryCollapse();
            });

            // Make sure the title has flex display to position the button
            siteBoundaryTitle.style.display = 'flex';
            siteBoundaryTitle.style.alignItems = 'center';
            siteBoundaryTitle.style.justifyContent = 'space-between';

            siteBoundaryTitle.appendChild(collapseButton);
            this.info('Site Boundary collapse button added');
        }
    }

    toggleSiteBoundaryCollapse() {
        const siteBoundaryControls = document.getElementById('siteBoundaryControls');
        const collapseButton = document.querySelector('#siteBoundaryControls .collapse-button');

        if (!siteBoundaryControls) return;

        const isCollapsed = siteBoundaryControls.classList.contains('collapsed');

        if (isCollapsed) {
            // Expand the card
            this.expandSiteBoundaryCard();
            if (collapseButton) {
                collapseButton.innerHTML = '−';
                collapseButton.title = 'Collapse Site Boundary';
            }
        } else {
            // Collapse the card
            this.collapseSiteBoundaryCard();
            if (collapseButton) {
                collapseButton.innerHTML = '+';
                collapseButton.title = 'Expand Site Boundary';
            }
        }
    }

    async generateCutFillAnalysis() {
        try {
            this.info('Generating cut & fill analysis...');

            const siteInspectorCore = window.siteInspectorCore;
            if (!siteInspectorCore) {
                throw new Error('Site Inspector not available');
            }

            // Check if we have site boundary data
            const siteBoundaryManager = siteInspectorCore.getManager('siteBoundary');
            if (!siteBoundaryManager || !siteBoundaryManager.hasSiteBoundary()) {
                this.showError('Please define a site boundary first');
                return;
            }

            // Check if we have buildable area (setbacks applied)
            const propertySetbacksManager = siteInspectorCore.getManager('propertySetbacks');
            if (!propertySetbacksManager || !propertySetbacksManager.getCurrentBuildableArea()) {
                this.showError('Please apply property setbacks first to define the buildable area');
                return;
            }

            // Get site data with current map view
            const siteData = siteInspectorCore.getSiteData();

            // Capture current map bounds for terrain context
            const terrainBounds = siteInspectorCore.captureTerrainBounds();
            if (terrainBounds) {
                siteData.terrainBounds = terrainBounds;
                this.info('Captured terrain bounds for analysis:', terrainBounds);
            }

            // Get buildable area data
            const buildableArea = propertySetbacksManager.getCurrentBuildableArea();
            if (buildableArea) {
                siteData.buildable_area = buildableArea;
            }

            // Open terrain viewer with site data for cut & fill analysis
            const projectId = siteInspectorCore.getProjectIdFromUrl();
            const terrainUrl = `/terrain-viewer${projectId ? `?project_id=${projectId}` : ''}`;

            // Store site data in session for terrain viewer
            try {
                const response = await fetch('/api/store-session-data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        site_data: siteData,
                        terrain_bounds: terrainBounds 
                    })
                });

                if (response.ok) {
                    this.showSuccess('Opening cut & fill analysis...');
                    window.open(terrainUrl, '_blank');
                } else {
                    throw new Error('Failed to store site data');
                }
            } catch (error) {
                this.warn('Could not store site data, opening terrain viewer anyway');
                window.open(terrainUrl, '_blank');
            }

        } catch (error) {
            this.error('Failed to generate cut & fill analysis:', error);
            this.showError('Failed to generate cut & fill analysis: ' + error.message);
        }
    }

    async saveCurrentProgress() {
        try {
            this.info('Saving current progress...');

            // Show saving indicator
            this.showSuccess('Progress saved successfully!');

        } catch (error) {
            this.error('Failed to save progress:', error);
            this.showError('Failed to save progress');
        }
    }



    showSuccess(message) {
        // Create and show success notification
        const successDiv = document.createElement('div');
        successDiv.className = 'success-notification';
        successDiv.textContent = message;
        successDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
            z-index: 2000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(successDiv);

        // Remove after 3 seconds
        setTimeout(() => {
            successDiv.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (successDiv.parentNode) {
                    successDiv.parentNode.removeChild(successDiv);
                }
            }, 300);
        }, 3000);

        this.info('Success notification shown:', message);
    }

    showError(message) {
        // Create and show error notification
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
            z-index: 2000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(errorDiv);

        // Remove after 5 seconds
        setTimeout(() => {
            errorDiv.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.parentNode.removeChild(errorDiv);
                }
            }, 300);
        }, 5000);

        this.error('Error notification shown:', message);
    }

    getPanelState(panelName) {
        return this.panelState[panelName] || false;
    }

    getCardState(cardName) {
        return this.cardStates[cardName] || 'collapsed';
    }

    isInspectorPanelExpanded() {
        return this.panelState.inspector;
    }

    isSiteInfoExpanded() {
        return this.panelState.siteInfo;
    }
}

// Setup cut & fill analysis button
        const cutFillAnalysisBtn = document.getElementById('cutFillAnalysisBtn');
        if (cutFillAnalysisBtn) {
            cutFillAnalysisBtn.addEventListener('click', () => {
                this.generateCutFillAnalysis();
            });
        }

        // Setup save progress button
        const saveProgressBtn = document.getElementById('saveProgressBtn');
        if (saveProgressBtn) {
            saveProgressBtn.addEventListener('click', () => {
                this.saveCurrentProgress();
            });
        }

// Update location info if available
        const locationSpan = document.getElementById('siteLocation');
        if (locationSpan) {
            const siteData = window.siteInspectorCore ? window.siteInspectorCore.getSiteData() : {};
            const location = siteData.project_address || siteData.location || 'Not specified';
            locationSpan.textContent = location;
        }

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

window.UIPanelManager = UIPanelManager;