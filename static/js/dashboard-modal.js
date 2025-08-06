/**
 * Dashboard Modal JavaScript Module
 * 
 * Handles all modal-related functionality including:
 * - Add Project modal
 * - Form validation
 * - Tab switching
 * - Map integration
 * - Project creation
 */

class DashboardModalManager extends BaseManager {
    constructor() {
        super('DashboardModalManager');
        this.projectSetupMap = null;
        this.projectSetupMapInitialized = false;
        this.mapUpdateTimeout = null;
        this.userInteracting = false;
        this.spinEnabled = true;
    }

    /**
     * Initialize modal functionality
     */
    initialize() {
        this.info('Initializing modal functionality');
        this.setupAddProjectModal();
        this.setupFormValidation();
        this.info('Modal functionality initialized');
    }

    /**
     * Setup Add Project modal functionality
     */
    setupAddProjectModal() {
        const modal = document.getElementById('addProjectModal');
        if (!modal) {
            this.warn('Add Project modal not found');
            return;
        }

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeAddProjectModal();
            }
        });

        this.debug('Add Project modal setup complete');
    }

    /**
     * Show the Add Project modal
     */
    showAddProjectModal() {
        this.info('Opening Add Project modal');
        const modal = document.getElementById('addProjectModal');
        const form = document.getElementById('addProjectForm');

        if (modal) {
            modal.style.display = 'flex';

            setTimeout(() => {
                this.initializeProjectSetupMap();
            }, 100);

            if (form) {
                form.reset();
                this.switchProjectTab('overview');
            }
        }
    }

    /**
     * Close the Add Project modal
     */
    closeAddProjectModal() {
        this.info('Closing Add Project modal');
        const modal = document.getElementById('addProjectModal');
        if (modal) {
            modal.style.display = 'none';

            if (this.projectSetupMap) {
                const existingMarkers = document.querySelectorAll('.project-setup-marker');
                existingMarkers.forEach(marker => marker.remove());
            }
        }
        this.clearErrors();
    }

    /**
     * Switch between project tab sections
     */
    switchProjectTab(tab) {
        this.debug(`Switching to project tab: ${tab}`);

        const overviewBtn = document.getElementById('overviewBtn');
        const settingsBtn = document.getElementById('settingsBtn');
        const overviewSection = document.getElementById('projectOverviewSection');
        const settingsSection = document.getElementById('projectSettingsSection');

        // Reset button states
        overviewBtn.classList.remove('active');
        settingsBtn.classList.remove('active');
        overviewSection.classList.remove('active');
        settingsSection.classList.remove('active');

        if (tab === 'overview') {
            overviewBtn.classList.add('active');
            overviewSection.classList.add('active');
        } else if (tab === 'settings') {
            settingsBtn.classList.add('active');
            settingsSection.classList.add('active');
        }
    }

    /**
     * Clear form validation errors
     */
    clearErrors() {
        const errorElements = document.querySelectorAll('.error-message');
        errorElements.forEach(element => {
            element.textContent = '';
        });
    }

    /**
     * Setup form validation and submission
     */
    setupFormValidation() {
        const form = document.getElementById('addProjectForm');
        if (!form) {
            this.warn('Add Project form not found');
            return;
        }

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmission();
        });

        this.debug('Form validation setup complete');
    }

    /**
     * Handle form submission
     */
    async handleFormSubmission() {
        this.info('Processing Add Project form submission');

        this.clearErrors();

        const projectName = document.getElementById('projectName').value.trim();
        const projectNumber = document.getElementById('projectNumber').value.trim();
        const clientName = document.getElementById('clientName').value.trim();
        const siteAddress = document.getElementById('siteAddress').value.trim();
        const siteInformation = document.getElementById('siteInformation').value.trim();

        let hasErrors = false;

        // Client-side validation
        if (!projectName) {
            document.getElementById('projectNameError').textContent = 'Project name is required';
            hasErrors = true;
        }

        if (!siteAddress) {
            document.getElementById('siteAddressError').textContent = 'Site address is required';
            hasErrors = true;
        }

        if (hasErrors) {
            this.warn('Form validation failed');
            return;
        }

        // Get project settings data with defaults
        const projectType = document.getElementById('projectType').value.trim() || null;
        const projectUnits = document.getElementById('projectUnits').value.trim() || 'metric';
        const projectVisibility = document.querySelector('input[name="projectVisibility"]:checked').value || 'private';
        const teamMembers = document.getElementById('teamMembers').value.trim();

        const projectData = {
            name: projectName,
            projectNumber: projectNumber,
            clientName: clientName,
            address: siteAddress,
            siteInformation: siteInformation,
            projectType: projectType,
            projectUnits: projectUnits,
            projectVisibility: projectVisibility,
            teamMembers: teamMembers
        };

        try {
            this.info('Sending project creation request', {
                name: projectName,
                address: siteAddress
            });

            const response = await window.apiClient.post('/create-project', projectData);

            if (response.success) {
                        this.info('Project created successfully, preparing redirect');

                        this.info('Project ID for redirect:', response.project.id);

                        // Close modal first
                        this.closeAddProjectModal();

                        // Small delay to ensure modal is closed, then redirect to project detail page
                        setTimeout(() => {
                            const redirectUrl = `/project/${response.project.id}`;
                            this.info('Redirecting to project detail page:', redirectUrl);
                            window.location.href = redirectUrl;
                        }, 100);
                    } else {
                this.error('Project creation failed', response);
                alert('Error creating project: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            this.error('API request failed', error);
            alert('Error creating project. Please try again.');
        }
    }

    /**
     * Initialize project setup map
     */
    async initializeProjectSetupMap() {
        if (this.projectSetupMapInitialized) return;

        try {
            // Check if mapboxgl is available
            if (typeof mapboxgl === 'undefined') {
                this.error('MapboxGL JS library not loaded');
                return;
            }

            const tokenResponse = await window.apiClient.get('/mapbox-token');

            if (!tokenResponse.success || !tokenResponse.token) {
                this.warn('No Mapbox token available for project setup map');
                return;
            }

            mapboxgl.accessToken = tokenResponse.token;

            // Check if container exists
            const mapContainer = document.getElementById('projectSetupMap');
            if (!mapContainer) {
                this.error('Map container #projectSetupMap not found');
                return;
            }

            this.projectSetupMap = new mapboxgl.Map({
                container: 'projectSetupMap',
                style: 'mapbox://styles/mapbox/streets-v12',
                projection: 'globe',
                center: DashboardConfig.MAP.DEFAULT_CENTER,
                zoom: DashboardConfig.MAP.DEFAULT_ZOOM,
                attributionControl: false,
                scrollZoom: true,
                boxZoom: false,
                doubleClickZoom: false,
                touchZoomRotate: false,
            });

            this.projectSetupMap.on('style.load', () => {
                this.projectSetupMap.setFog({
                    'range': [0.5, 10],
                    'color': '#ffffff',
                    'horizon-blend': 0.1
                });
            });

            this.setupMapInteractionHandlers();
            this.startMapSpinning();

            this.projectSetupMap.on('load', () => {
                this.projectSetupMapInitialized = true;
                this.info('Project setup map initialized successfully');
            });

        } catch (error) {
            this.error('Failed to initialize project setup map', error);
        }
    }

    /**
     * Setup map interaction handlers
     */
    setupMapInteractionHandlers() {
        this.projectSetupMap.on('mousedown', () => {
            this.userInteracting = true;
        });

        this.projectSetupMap.on('dragstart', () => {
            this.userInteracting = true;
        });

        this.projectSetupMap.on('dragend', () => {
            this.userInteracting = false;
            setTimeout(() => {
                if (!this.userInteracting) {
                    this.spinEnabled = true;
                }
            }, 2000);
        });
    }

    /**
     * Start map spinning animation
     */
    startMapSpinning() {
        const spinGlobe = () => {
            if (this.spinEnabled && !this.userInteracting && this.projectSetupMap.loaded()) {
                const center = this.projectSetupMap.getCenter();
                center.lng -= 0.2;
                this.projectSetupMap.easeTo({ center, duration: 100 });
            }
            requestAnimationFrame(spinGlobe);
        };

        spinGlobe();
    }

    /**
     * Update project setup map based on address input
     */
    updateProjectSetupMap(address) {
        const locateBtn = document.getElementById('locateAddressBtn');

        if (locateBtn) {
            if (address && address.trim().length >= 3) {
                locateBtn.disabled = false;
                locateBtn.style.opacity = '1';
            } else {
                locateBtn.disabled = true;
                locateBtn.style.opacity = '0.5';
            }
        }

        if (!address || address.trim().length < 3) return;
        if (!this.projectSetupMapInitialized || !this.projectSetupMap) return;

        if (this.mapUpdateTimeout) {
            clearTimeout(this.mapUpdateTimeout);
        }

        // Auto-geocode and update map after user stops typing (but don't auto-fly)
        this.mapUpdateTimeout = setTimeout(async () => {
            this.debug('Auto-enabling locate button for:', address);
            // Just ensure the button is enabled, don't auto-locate
        }, DashboardConfig.ANIMATION.USER_INTERACTION_DELAY);
    }

    /**
     * Locate address on map
     */
    async locateAddress() {
        const address = document.getElementById('siteAddress').value.trim();
        const locateBtn = document.getElementById('locateAddressBtn');

        if (!address || address.length < 3) return;
        if (!this.projectSetupMapInitialized || !this.projectSetupMap) return;

        if (locateBtn) {
            locateBtn.disabled = true;
            locateBtn.textContent = '...';
            locateBtn.style.opacity = '0.7';
        }

        try {
            this.info('Geocoding address for project setup map:', address);

            const response = await window.apiClient.post('/geocode-location', { query: address });

            if (response.success && response.location) {
                const { lat, lng } = response.location;

                this.spinEnabled = false;
                this.userInteracting = true;

                this.projectSetupMap.flyTo({
                    center: [lng, lat],
                    zoom: 16,
                    duration: 2500,
                    essential: true,
                    curve: 1.2,
                    easing: function(t) {
                        return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
                    }
                });

                const existingMarkers = document.querySelectorAll('.project-setup-marker');
                existingMarkers.forEach(marker => marker.remove());

                const marker = new mapboxgl.Marker({
                    color: '#4f7cff',
                    className: 'project-setup-marker'
                })
                .setLngLat([lng, lat])
                .addTo(this.projectSetupMap);

                this.info('Project setup map updated to:', response.location.display_name || address);
            } else {
                this.warn('Geocoding failed for project setup:', response.error);
            }
        } catch (error) {
            this.error('Error updating project setup map', error);
        } finally {
            // Re-enable button if it was manually clicked
            if (locateBtn) {
                locateBtn.disabled = false;
                locateBtn.textContent = 'Locate';
                locateBtn.style.opacity = '1';
            }
        }
    }
}
const siteInspectorBtn = document.getElementById('siteInspectorBtn');tn');
if (siteInspectorBtn) {
    siteInspectorBtn.addEventListener('click', () => {
        const projectId = document.getElementById('projectId')?.value;
        if (projectId) {
            window.location.href = `/site-inspector?project_id=${projectId}`;
        } else {
            window.location.href = '/site-inspector';
        }
    });
}

// Global functions needed by HTML
function showAddProjectModal() {
    if (window.dashboardModalManager) {
        window.dashboardModalManager.showAddProjectModal();
    }
}

function closeAddProjectModal() {
    if (window.dashboardModalManager) {
        window.dashboardModalManager.closeAddProjectModal();
    }
}

function switchProjectTab(tab) {
    if (window.dashboardModalManager) {
        window.dashboardModalManager.switchProjectTab(tab);
    }
}

function updateProjectSetupMap(address) {
    if (window.dashboardModalManager) {
        window.dashboardModalManager.updateProjectSetupMap(address);
    }
}

function locateAddress() {
    if (window.dashboardModalManager) {
        window.dashboardModalManager.locateAddress();
    }
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardModalManager };
}