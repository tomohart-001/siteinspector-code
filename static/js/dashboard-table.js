/**
 * Dashboard Table JavaScript Module
 * 
 * Handles table-related functionality including:
 * - Project table population
 * - Pagination controls
 * - Filtering
 * - Table height management
 */

class DashboardTableManager extends BaseManager {
    constructor() {
        super('DashboardTableManager');
        this.currentPage = 1;
        this.projectsPerPage = 12;
        this.allProjects = [];
        this.filteredProjects = [];
        this.initialized = false;
    }

    /**
     * Initialize table functionality
     */
    async initialize() {
        if (this.initialized) {
            this.warn('Table manager already initialized');
            return;
        }

        this.info('Initializing table functionality');

        try {
            this.setupFileFiltering();
            await this.loadInitialData();
            this.initialized = true;
            this.info('Table functionality initialized successfully');
        } catch (error) {
            this.error('Failed to initialize table functionality', error);
            throw error;
        }
    }

    /**
     * Setup file filtering functionality
     */
    setupFileFiltering() {
        const fileFilterSelect = document.getElementById('fileFilterSelect');
        if (!fileFilterSelect) {
            this.warn('File filter select not found');
            return;
        }

        fileFilterSelect.addEventListener('change', (e) => {
            const selectedFilter = e.target.value;
            this.info(`Files filter changed to: ${selectedFilter}`);
            this.currentPage = 1;
            this.populateFilesTable(this.allProjects, selectedFilter);
        });

        this.debug('File filtering setup complete');
    }

    /**
     * Load initial table data
     */
    async loadInitialData() {
        try {
            this.debug('Loading initial table data...');
            const projects = await this.loadAllProjects();
            this.debug(`Loaded ${projects.length} projects for table`);

            // Always try to populate, even with empty array
            this.populateFilesTable(projects, 'all');

            // Update table height after a brief delay to ensure DOM is ready
            setTimeout(() => {
                this.updateTableHeight(Math.min(projects.length, this.projectsPerPage));
            }, 100);
        } catch (error) {
            this.error('Failed to load initial table data', error);
            // Show empty state on error
            this.populateFilesTable([], 'all');
        }
    }

    /**
     * Populate the files table with project data and pagination
     */
    populateFilesTable(projects = [], filter = 'all') {
        const tableBody = document.getElementById('filesTableBody');
        const paginationContainer = document.getElementById('paginationContainer');

        if (!tableBody) {
            this.warn('Table body not found');
            return;
        }

        this.debug(`Populating table with ${projects.length} projects, filter: ${filter}`);

        // Store projects and apply filter
        this.allProjects = projects;
        this.filteredProjects = this.applyFilter(projects, filter);

        // Ensure current page is valid
        const totalPages = Math.ceil(this.filteredProjects.length / this.projectsPerPage);
        if (this.currentPage > totalPages && totalPages > 0) {
            this.currentPage = totalPages;
        }
        if (this.currentPage < 1) {
            this.currentPage = 1;
        }

        // Handle empty state
        if (this.filteredProjects.length === 0) {
            this.showNoDataMessage(tableBody);
            if (paginationContainer) {
                paginationContainer.style.display = 'none';
            }
            this.updateTableHeight(0);
            this.updateProjectCounter(0);
            return;
        }

        // Calculate pagination
        const totalProjects = this.filteredProjects.length;
        const startIndex = (this.currentPage - 1) * this.projectsPerPage;
        const endIndex = Math.min(startIndex + this.projectsPerPage, totalProjects);
        const projectsToShow = this.filteredProjects.slice(startIndex, endIndex);

        this.debug(`Showing projects ${startIndex + 1}-${endIndex} of ${totalProjects}`);

        // Generate table rows
        const rows = projectsToShow.map(project => this.createTableRow(project)).join('');
        tableBody.innerHTML = rows;

        // Update UI elements
        this.updateTableHeight(projectsToShow.length);
        this.updateProjectCounter(totalProjects);

        // Handle pagination
        if (paginationContainer) {
            if (totalProjects > this.projectsPerPage) {
                paginationContainer.style.display = 'flex';
                this.updatePaginationControls(totalPages, startIndex + 1, endIndex, totalProjects);
            } else {
                paginationContainer.style.display = 'none';
            }
        }

        this.info(`Table populated with ${projectsToShow.length} projects (${totalProjects} total)`);
    }

    /**
     * Apply filter to projects
     */
    applyFilter(projects, filter) {
        if (!Array.isArray(projects)) {
            this.warn('Projects is not an array:', projects);
            return [];
        }

        switch (filter) {
            case 'my':
                return projects.filter(p => p.type === 'my' || !p.type);
            case 'team':
                return projects.filter(p => p.type === 'team');
            default:
                return projects;
        }
    }

    /**
     * Show no data message
     */
    showNoDataMessage(tableBody) {
        tableBody.innerHTML = `
            <tr class="no-data-row">
                <td colspan="6" class="no-data-message">
                    <div class="no-data-content">
                        <div style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;">📋</div>
                        <p style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">No projects found</p>
                        <p style="font-size: 0.9rem;">Create your first project to get started</p>
                    </div>
                </td>
            </tr>
        `;
    }

    /**
     * Create table row HTML
     */
    createTableRow(project) {
        // Ensure project has required fields
        const projectId = project.id || 0;
        const projectName = project.name || 'Untitled Project';
        const client = project.client || project.client_name || 'N/A';
        const owner = project.owner || project.created_by || 'Unknown';
        const modified = project.modified || project.last_modified || project.created || new Date().toISOString();
        const status = project.status || 'active';

        return `
            <tr data-project-id="${projectId}">
                <td class="project-name-cell">
                    <a href="#" onclick="openProject(${projectId}); return false;" style="color: #547bf7; text-decoration: none; font-weight: 600;">
                        ${this.escapeHtml(projectName)}
                    </a>
                </td>
                <td>${this.escapeHtml(client)}</td>
                <td>${this.escapeHtml(owner)}</td>
                <td>${this.formatDate(modified)}</td>
                <td>
                    <span class="project-status-badge ${status}">
                        ${this.getStatusText(status)}
                    </span>
                </td>
                <td>
                    <div class="project-actions">
                        <button class="action-btn share" onclick="shareProject(${projectId})" title="Share project">Share</button>
                        <button class="action-btn delete" onclick="deleteProject(${projectId})" title="Delete project">Delete</button>
                    </div>
                </td>
            </tr>
        `;
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
     * Update table height based on number of projects
     */
    updateTableHeight(projectCount) {
        const allFilesCard = document.getElementById('allFilesView');
        if (!allFilesCard) return;

        // Constants for height calculation
        const baseHeight = 120; // Header + padding
        const rowHeight = 50;   // Height per row
        const emptyHeight = 300; // Height when no projects
        const minHeight = 320;
        const maxHeight = 720;

        let finalHeight;

        if (projectCount === 0) {
            finalHeight = emptyHeight;
        } else {
            const contentHeight = Math.max(200, projectCount * rowHeight + 100);
            const totalHeight = baseHeight + contentHeight;
            finalHeight = Math.max(minHeight, Math.min(totalHeight, maxHeight));
        }

        allFilesCard.style.height = `${finalHeight}px`;
        this.debug(`Table height set to ${finalHeight}px for ${projectCount} projects`);
    }

    /**
     * Update pagination controls
     */
    updatePaginationControls(totalPages, startIndex, endIndex, totalProjects) {
        const paginationInfo = document.getElementById('paginationInfo');
        const paginationPages = document.getElementById('paginationPages');
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');

        // Update info text
        if (paginationInfo) {
            paginationInfo.textContent = `Showing ${startIndex}-${endIndex} of ${totalProjects} projects`;
        }

        // Update navigation buttons
        if (prevBtn && nextBtn) {
            prevBtn.disabled = this.currentPage === 1;
            nextBtn.disabled = this.currentPage === totalPages;

            // Update button styles based on state
            prevBtn.style.opacity = prevBtn.disabled ? '0.5' : '1';
            nextBtn.style.opacity = nextBtn.disabled ? '0.5' : '1';
        }

        // Generate page numbers
        if (paginationPages) {
            const maxVisiblePages = 5;
            let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
            let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

            // Adjust start page if we're near the end
            if (endPage - startPage + 1 < maxVisiblePages) {
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }

            let pagesHtml = '';
            for (let i = startPage; i <= endPage; i++) {
                pagesHtml += `
                    <button class="pagination-page ${i === this.currentPage ? 'active' : ''}" 
                            data-page="${i}" title="Go to page ${i}">
                        ${i}
                    </button>
                `;
            }

            paginationPages.innerHTML = pagesHtml;

            // Add click event listeners to page buttons
            const pageButtons = paginationPages.querySelectorAll('.pagination-page');
            pageButtons.forEach(button => {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    const page = parseInt(button.getAttribute('data-page'));
                    this.goToPage(page);
                });
            });
        }
    }

    /**
     * Change page by offset
     */
    changePage(offset) {
        const totalPages = Math.ceil(this.filteredProjects.length / this.projectsPerPage);
        const newPage = this.currentPage + offset;

        this.debug(`Attempting to change page from ${this.currentPage} to ${newPage} (total pages: ${totalPages})`);

        if (newPage >= 1 && newPage <= totalPages) {
            this.currentPage = newPage;
            this.info(`Page changed to ${this.currentPage}`);
            this.populateFilesTable(this.allProjects, this.getCurrentFilter());
        } else {
            this.warn(`Invalid page number: ${newPage}. Must be between 1 and ${totalPages}`);
        }
    }

    /**
     * Go to specific page
     */
    goToPage(page) {
        const totalPages = Math.ceil(this.filteredProjects.length / this.projectsPerPage);

        this.debug(`Attempting to go to page ${page} (total pages: ${totalPages})`);

        if (page >= 1 && page <= totalPages) {
            this.currentPage = page;
            this.info(`Navigated to page ${this.currentPage}`);
            this.populateFilesTable(this.allProjects, this.getCurrentFilter());
        } else {
            this.warn(`Invalid page number: ${page}. Must be between 1 and ${totalPages}`);
        }
    }

    /**
     * Get current filter value
     */
    getCurrentFilter() {
        const filterSelect = document.getElementById('fileFilterSelect');
        return filterSelect ? filterSelect.value : 'all';
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
     * Load projects from API
     */
    async loadAllProjects() {
        try {
            this.debug('Loading user projects from API...');

            const response = await fetch('/api/get-user-projects');
            const data = await response.json();

            if (data && data.success && Array.isArray(data.projects)) {
                this.debug(`Loaded ${data.projects.length} projects from API`);
                return data.projects;
            } else {
                this.warn('API returned invalid project data:', data);
                return [];
            }
        } catch (error) {
            this.error('Error loading projects from API', error);
            return [];
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
            this.warn('Error formatting date:', dateString);
            return 'Unknown';
        }
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
     * Filter table rows based on search term
     */
    filterTable(searchTerm) {
        if (!searchTerm) {
            this.clearTableFilter();
            return;
        }

        const tableRows = document.querySelectorAll('#filesTableBody tr:not(.no-data-row)');
        let visibleTableCount = 0;

        tableRows.forEach(row => {
            const projectNameCell = row.querySelector('.project-name-cell a');
            const clientCell = row.children[1];
            const ownerCell = row.children[2];
            const statusCell = row.querySelector('.project-status-badge');

            if (!projectNameCell) return;

            const projectName = projectNameCell.textContent.toLowerCase();
            const client = clientCell ? clientCell.textContent.toLowerCase() : '';
            const owner = ownerCell ? ownerCell.textContent.toLowerCase() : '';
            const status = statusCell ? statusCell.textContent.toLowerCase() : '';

            const isMatch = projectName.includes(searchTerm) ||
                          client.includes(searchTerm) ||
                          owner.includes(searchTerm) ||
                          status.includes(searchTerm);

            if (isMatch) {
                row.style.display = '';
                visibleTableCount++;
                // Highlight search matches
                row.style.backgroundColor = '#f0f9ff';
            } else {
                row.style.display = 'none';
            }
        });

        this.debug(`Table filtered: ${visibleTableCount} visible rows for term "${searchTerm}"`);
    }

    /**
     * Clear table filter
     */
    clearTableFilter() {
        const tableRows = document.querySelectorAll('#filesTableBody tr:not(.no-data-row)');
        tableRows.forEach(row => {
            row.style.display = '';
            row.style.backgroundColor = '';
        });
    }

    /**
     * Refresh table data
     */
    async refreshTable() {
        try {
            this.info('Refreshing table data...');
            const projects = await this.loadAllProjects();
            const currentFilter = this.getCurrentFilter();
            this.populateFilesTable(projects, currentFilter);
            this.info('Table data refreshed successfully');
        } catch (error) {
            this.error('Failed to refresh table data', error);
        }
    }

    /**
     * Remove project from table
     */
    removeProject(projectId) {
        // Remove from data arrays
        this.allProjects = this.allProjects.filter(p => p.id !== projectId);
        this.filteredProjects = this.filteredProjects.filter(p => p.id !== projectId);

        // Remove from DOM
        const row = document.querySelector(`tr[data-project-id="${projectId}"]`);
        if (row) {
            row.remove();
        }

        // Refresh pagination if needed
        const currentFilter = this.getCurrentFilter();
        this.populateFilesTable(this.allProjects, currentFilter);

        this.info(`Project ${projectId} removed from table`);
    }
}

// Global functions needed by HTML - define them directly on window
window.changePage = function(offset) {
    console.log('[Dashboard] changePage called with offset:', offset);
    if (window.dashboardTableManager && typeof window.dashboardTableManager.changePage === 'function') {
        window.dashboardTableManager.changePage(offset);
    } else {
        console.error('[Dashboard] Table manager not available for changePage:', window.dashboardTableManager);
    }
};

window.goToPage = function(page) {
    console.log('[Dashboard] goToPage called with page:', page);
    if (window.dashboardTableManager && typeof window.dashboardTableManager.goToPage === 'function') {
        window.dashboardTableManager.goToPage(page);
    } else {
        console.error('[Dashboard] Table manager not available for goToPage:', window.dashboardTableManager);
    }
};

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardTableManager };
}