
/**
 * Dashboard Core JavaScript Module
 * 
 * Handles main dashboard functionality including:
 * - Search functionality
 * - Project filtering
 * - User dropdown management
 * - Team management
 * - Core initialization
 */

class DashboardManager extends BaseManager {
    constructor() {
        super('DashboardManager');
        this.searchTimeout = null;
        this.initialized = false;
    }

    /**
     * Initialize the dashboard
     */
    async initialize() {
        if (this.initialized) {
            this.warn('Dashboard already initialized');
            return;
        }

        try {
            this.info('Initializing dashboard components');

            this.setupSearchFunctionality();
            this.setupUserDropdown();
            this.setupTeamManagement();
            this.setupEventListeners();

            this.initialized = true;
            this.info('Dashboard initialization complete');

        } catch (error) {
            this.error('Failed to initialize dashboard', error);
            throw error;
        }
    }

    /**
     * Setup search functionality with debouncing
     */
    setupSearchFunctionality() {
        const searchInput = document.getElementById('projectSearch');
        if (!searchInput) {
            this.warn('Search input not found');
            return;
        }

        // Remove any existing event listeners to prevent conflicts
        const newSearchInput = searchInput.cloneNode(true);
        searchInput.parentNode.replaceChild(newSearchInput, searchInput);

        const handleSearch = this.debounce((e) => {
            const searchTerm = e.target.value.toLowerCase().trim();
            this.filterProjects(searchTerm);

            // Also filter the table if it exists
            if (window.dashboardTableManager) {
                window.dashboardTableManager.filterTable(searchTerm);
            }
        }, 300);

        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                newSearchInput.value = '';
                this.filterProjects('');
                if (window.dashboardTableManager) {
                    window.dashboardTableManager.clearTableFilter();
                }
            }
        };

        newSearchInput.addEventListener('input', handleSearch);
        newSearchInput.addEventListener('keydown', handleKeydown);

        this.debug('Search functionality initialized successfully');
    }

    /**
     * Debounce utility function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Filter project list based on search input
     */
    filterProjects(searchTerm) {
        const projectCards = document.querySelectorAll('.project-card');
        let visibleCount = 0;

        projectCards.forEach(card => {
            const projectTitle = card.querySelector('.project-card-title');
            const projectMeta = card.querySelector('.project-card-meta');
            const projectStatus = card.querySelector('.project-card-status');

            if (!projectTitle || !projectMeta || !projectStatus) return;

            const titleText = projectTitle.textContent.toLowerCase();
            const metaText = projectMeta.textContent.toLowerCase();
            const statusText = projectStatus.textContent.toLowerCase();

            const isMatch = searchTerm === '' ||
                          titleText.includes(searchTerm) ||
                          metaText.includes(searchTerm) ||
                          statusText.includes(searchTerm);

            if (isMatch) {
                card.style.display = 'block';
                visibleCount++;

                if (searchTerm !== '') {
                    card.style.backgroundColor = '#f0f9ff';
                    card.style.border = '2px solid #547bf7';
                } else {
                    card.style.backgroundColor = '';
                    card.style.border = '1px solid #e2e8f0';
                }
            } else {
                card.style.display = 'none';
            }
        });

        this.debug(`Search filtered projects: ${visibleCount} visible of ${projectCards.length} total`);
    }

    /**
     * Setup user profile dropdown functionality
     */
    setupUserDropdown() {
        const userProfileDropdownToggle = document.getElementById('userProfileDropdownToggle');
        const userProfileDropdownMenu = document.getElementById('userProfileDropdownMenu');

        if (!userProfileDropdownToggle || !userProfileDropdownMenu) {
            this.warn('User dropdown elements not found');
            return;
        }

        // Toggle dropdown on click
        userProfileDropdownToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isCurrentlyVisible = userProfileDropdownMenu.classList.contains('show');

            // Close all other dropdowns first
            document.querySelectorAll('.user-dropdown-menu.show').forEach(menu => {
                menu.classList.remove('show');
            });
            document.querySelectorAll('.user-dropdown-toggle.active').forEach(toggle => {
                toggle.classList.remove('active');
            });

            // Toggle current dropdown
            if (!isCurrentlyVisible) {
                userProfileDropdownToggle.classList.add('active');
                userProfileDropdownMenu.classList.add('show');
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!userProfileDropdownToggle.contains(e.target) &&
                !userProfileDropdownMenu.contains(e.target)) {
                userProfileDropdownToggle.classList.remove('active');
                userProfileDropdownMenu.classList.remove('show');
            }
        });

        // Prevent dropdown from closing when clicking inside
        userProfileDropdownMenu.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        this.debug('User dropdown functionality initialized');
    }

    /**
     * Setup team management functionality
     */
    setupTeamManagement() {
        this.updateTeamMenuName();
        this.setupTeamModal();
    }

    /**
     * Update team menu name dynamically
     */
    async updateTeamMenuName() {
        try {
            const response = await fetch('/api/get-team-name');
            const data = await response.json();
            
            const teamMenuText = document.getElementById('teamMenuText');
            const teamMenuItem = document.getElementById('teamMenuItem');
            const fileFilterSelect = document.getElementById('fileFilterSelect');

            if (data && data.success && data.team_name) {
                if (teamMenuText) {
                    teamMenuText.textContent = data.team_name;
                    teamMenuText.title = data.team_name;
                    this.debug(`Team menu updated with name: ${data.team_name}`);
                }
                if (teamMenuItem) {
                    teamMenuItem.style.display = 'flex';
                }
                if (fileFilterSelect) {
                    fileFilterSelect.style.display = 'block';
                }
            } else {
                if (teamMenuItem) {
                    teamMenuItem.style.display = 'none';
                }
                if (fileFilterSelect) {
                    fileFilterSelect.style.display = 'none';
                }
            }
        } catch (error) {
            this.warn('Could not load team name', error);
            const teamMenuItem = document.getElementById('teamMenuItem');
            const fileFilterSelect = document.getElementById('fileFilterSelect');
            if (teamMenuItem) {
                teamMenuItem.style.display = 'none';
            }
            if (fileFilterSelect) {
                fileFilterSelect.style.display = 'none';
            }
        }
    }

    /**
     * Setup team creation modal
     */
    setupTeamModal() {
        const teamSetupModal = document.getElementById('teamSetupModal');
        const closeTeamSetup = document.getElementById('closeTeamSetup');
        const teamSetupForm = document.getElementById('teamSetupForm');

        if (closeTeamSetup) {
            closeTeamSetup.addEventListener('click', () => {
                teamSetupModal.style.display = 'none';
            });
        }

        if (teamSetupForm) {
            teamSetupForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(teamSetupForm);
                const teamData = {
                    teamName: formData.get('teamName'),
                    teamDescription: '',
                    teamSize: formData.get('teamSize')
                };

                try {
                    const response = await fetch('/api/setup-team', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(teamData)
                    });

                    if (response.ok) {
                        teamSetupModal.style.display = 'none';
                        this.updateTeamMenuName();
                        location.reload();
                    } else {
                        throw new Error('Team setup failed');
                    }
                } catch (error) {
                    this.error('Team setup failed', error);
                    alert('Failed to create team. Please try again.');
                }
            });
        }

        this.debug('Team modal functionality initialized');
    }

    /**
     * Setup additional event listeners
     */
    setupEventListeners() {
        // Project visibility radio button handling
        const visibilityRadios = document.querySelectorAll('input[name="projectVisibility"]');
        const teamMembersGroup = document.getElementById('teamMembersGroup');

        visibilityRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (this.value === 'team') {
                    teamMembersGroup.style.display = 'block';
                } else {
                    teamMembersGroup.style.display = 'none';
                    document.getElementById('teamMembers').value = '';
                }
            });
        });

        this.debug('Additional event listeners initialized');
    }

    /**
     * Update project counter in sidebar
     */
    updateProjectCounter(count) {
        const projectCounter = document.getElementById('projectCounter');
        if (projectCounter) {
            projectCounter.textContent = count;
        }
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) {
                return 'Unknown';
            }
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return 'Unknown';
        }
    }

    /**
     * Get project type CSS class
     */
    getProjectTypeClass(type) {
        const typeMap = {
            'structural': 'structural',
            'structural-analyser': 'structural',
            'structure-designer': 'structural',
            'site': 'site',
            'site-selection': 'site',
            'site-inspector': 'site',
            'terrain-analysis': 'site',
            'building': 'building',
            'residential': 'building',
            'commercial': 'building',
            'industrial': 'building'
        };
        return typeMap[type] || 'building';
    }

    /**
     * Get project icon
     */
    getProjectIcon(type) {
        const iconMap = {
            'structural': '🏗️',
            'structural-analyser': '⚙️',
            'structure-designer': '🏗️',
            'site': '🗺️',
            'site-selection': '📍',
            'site-inspector': '🔍',
            'terrain-analysis': '🏔️',
            'building': '🏢',
            'residential': '🏠',
            'commercial': '🏢',
            'industrial': '🏭'
        };
        return iconMap[type] || '📋';
    }

    /**
     * Get status text
     */
    getStatusText(status) {
        const statusMap = {
            'site-selection': 'Site Selection',
            'site-inspector': 'Site Inspector',
            'terrain-analysis': 'Terrain Analysis',
            'structure-designer': 'Structure Designer',
            'structural-analyser': 'Structural Analyser',
            'active': 'Active',
            'completed': 'Completed',
            'pending': 'Pending'
        };
        return statusMap[status] || (status ? String(status).charAt(0).toUpperCase() + String(status).slice(1) : 'Active');
    }

    /**
     * Populate recent projects section
     */
    populateRecentProjects(projects) {
        const container = document.getElementById('recentProjectsContainer');
        const noProjectsMessage = container ? container.querySelector('.no-recent-projects') : null;

        if (!container) {
            this.warn('Recent projects container not found');
            return;
        }

        if (!projects || projects.length === 0) {
            if (noProjectsMessage) {
                noProjectsMessage.style.display = 'flex';
            }
            this.debug('No recent projects to display');
            return;
        }

        if (noProjectsMessage) {
            noProjectsMessage.style.display = 'none';
        }

        const recentProjects = projects
            .sort((a, b) => new Date(b.modified || b.created || 0) - new Date(a.modified || a.created || 0))
            .slice(0, 5);

        const projectCards = recentProjects.map(project => {
            const projectType = this.getProjectTypeClass(project.type || project.status);
            const icon = this.getProjectIcon(project.type || project.status);
            const projectName = project.name || 'Untitled Project';
            const modifiedDate = project.modified || project.created || new Date().toISOString();

            return `
                <div class="project-card" onclick="openProject(${project.id})" style="cursor: pointer;">
                    <div class="project-card-header ${projectType}">
                        <div class="project-card-icon">${icon}</div>
                    </div>
                    <div class="project-card-content">
                        <h4 class="project-card-title">${this.escapeHtml(projectName)}</h4>
                        <p class="project-card-meta">Modified: ${this.formatDate(modifiedDate)}</p>
                        <span class="project-card-status ${project.status || 'active'}">${this.getStatusText(project.status || 'active')}</span>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = projectCards;
        this.debug(`Populated ${recentProjects.length} recent projects`);
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (typeof text !== 'string') {
            return String(text);
        }
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Load projects from API
     */
    async loadAllProjects() {
        try {
            this.debug('Loading user projects from API...');

            const response = await fetch('/api/get-user-projects');
            const data = await response.json();

            if (data && data.success && Array.isArray(data.projects)) {
                this.debug(`Loaded ${data.projects.length} projects`);
                return data.projects;
            } else {
                this.warn('API returned invalid project data:', data);
                return [];
            }
        } catch (error) {
            this.error('Error loading projects', error);
            return [];
        }
    }

    /**
     * Refresh project lists after changes
     */
    async refreshProjectLists() {
        try {
            const projects = await this.loadAllProjects();

            // Update recent projects
            this.populateRecentProjects(projects);

            // Update table if dashboard table manager exists
            if (window.dashboardTableManager) {
                await window.dashboardTableManager.refreshTable();
            }

            // Update project counter
            this.updateProjectCounter(projects.length);

            this.debug('Project lists refreshed successfully');
        } catch (error) {
            this.error('Failed to refresh project lists', error);
        }
    }

    /**
     * Remove a specific project from UI without full refresh
     */
    removeProjectFromUI(projectId) {
        // Remove from recent projects
        const recentProjectCard = document.querySelector(`.project-card[onclick*="${projectId}"]`);
        if (recentProjectCard) {
            recentProjectCard.remove();
        }

        // Remove from table using table manager
        if (window.dashboardTableManager) {
            window.dashboardTableManager.removeProject(projectId);
        }

        // Check if recent projects section is now empty
        const recentContainer = document.getElementById('recentProjectsContainer');
        if (recentContainer) {
            const remainingCards = recentContainer.querySelectorAll('.project-card');
            if (remainingCards.length === 0) {
                const noProjectsMessage = recentContainer.querySelector('.no-recent-projects');
                if (noProjectsMessage) {
                    noProjectsMessage.style.display = 'flex';
                }
            }
        }

        this.debug(`Removed project ${projectId} from UI`);
    }
}

// Project action handlers (global functions needed by HTML)
function openProject(projectId) {
    console.log(`[Dashboard] Opening project ${projectId}`);
    window.location.href = `/project/${projectId}`;
}

function shareProject(projectId) {
    console.log(`[Dashboard] Sharing project ${projectId}`);
    const row = document.querySelector(`tr[data-project-id="${projectId}"]`);
    const projectName = row ? row.querySelector('.project-name-cell a').textContent : 'Project';

    const shareUrl = `${window.location.origin}/site-selection?project=${projectId}&shared=true`;

    navigator.clipboard.writeText(shareUrl).then(() => {
        alert(`Share link for "${projectName}" has been copied to your clipboard!`);
    }).catch(() => {
        prompt(`Share this link for "${projectName}":`, shareUrl);
    });
}

// Global variables for delete confirmation
let pendingDeleteProjectId = null;
let pendingDeleteProjectName = null;

async function deleteProject(projectId) {
    console.log(`[Dashboard] Delete requested for project ${projectId}`);
    const row = document.querySelector(`tr[data-project-id="${projectId}"]`);
    const projectName = row ? row.querySelector('.project-name-cell a').textContent : 'this project';

    // Store the project details for the modal
    pendingDeleteProjectId = projectId;
    pendingDeleteProjectName = projectName;

    // Update modal content and show it
    document.getElementById('deleteProjectName').textContent = projectName;
    document.getElementById('deleteProjectModal').style.display = 'flex';
}

function closeDeleteProjectModal() {
    document.getElementById('deleteProjectModal').style.display = 'none';
    pendingDeleteProjectId = null;
    pendingDeleteProjectName = null;
}

async function confirmDeleteProject() {
    if (!pendingDeleteProjectId) return;

    const projectId = pendingDeleteProjectId;
    const projectName = pendingDeleteProjectName;

    // Close modal immediately
    closeDeleteProjectModal();

    try {
        console.log(`[Dashboard] Confirming deletion of project ${projectId}`);

        const response = await fetch(`/api/project/${projectId}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data && data.success) {
            console.log(`[Dashboard] Project ${projectId} deleted successfully`);

            // Remove from UI immediately
            if (window.dashboardManager) {
                window.dashboardManager.removeProjectFromUI(projectId);
            }

            alert(`Project "${projectName}" has been deleted successfully.`);
        } else {
            console.error(`[Dashboard] Failed to delete project ${projectId}:`, data);
            alert(`Failed to delete project "${projectName}". Please try again.`);
        }
    } catch (error) {
        console.error(`[Dashboard] Error deleting project ${projectId}:`, error);
        alert(`Error deleting project "${projectName}". Please try again.`);
    }
}

// Global function to refresh project lists
async function refreshProjectLists() {
    if (window.dashboardManager) {
        await window.dashboardManager.refreshProjectLists();
    }
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardManager };
}
