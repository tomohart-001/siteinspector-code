
/**
 * Dashboard Configuration Module
 * 
 * Centralized configuration for dashboard components
 */

class DashboardConfig {
    /**
     * Pagination settings
     */
    static PAGINATION = {
        ITEMS_PER_PAGE: 12,
        MAX_VISIBLE_PAGES: 5,
        DEBOUNCE_DELAY: 150
    };

    /**
     * Search settings
     */
    static SEARCH = {
        MIN_CHARS: 3,
        DEBOUNCE_DELAY: 150,
        ESCAPE_KEY: 'Escape'
    };

    /**
     * Table settings
     */
    static TABLE = {
        MIN_HEIGHT: 320,
        MAX_HEIGHT: 720,
        BASE_HEIGHT: 120,
        ROW_HEIGHT: 50,
        EMPTY_HEIGHT: 300
    };

    /**
     * Animation settings
     */
    static ANIMATION = {
        MODAL_DELAY: 100,
        MAP_SPIN_SPEED: 0.2,
        MAP_SPIN_DURATION: 100,
        MAP_FLY_DURATION: 2500,
        USER_INTERACTION_DELAY: 2000
    };

    /**
     * Map settings
     */
    static MAP = {
        DEFAULT_CENTER: [135, -25],
        DEFAULT_ZOOM: 1.0,
        LOCATE_ZOOM: 16,
        MIN_ADDRESS_LENGTH: 3,
        MARKER_COLOR: '#4f7cff'
    };

    /**
     * Project type mappings
     */
    static PROJECT_TYPES = {
        MAPPINGS: {
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
        },
        DEFAULT: 'building'
    };

    /**
     * Project icons
     */
    static PROJECT_ICONS = {
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
        'industrial': '🏭',
        'default': '📋'
    };

    /**
     * Status mappings
     */
    static STATUS_MAPPINGS = {
        'site-selection': 'Site Selection',
        'site-inspector': 'Site Inspector',
        'terrain-analysis': 'Terrain Analysis',
        'structure-designer': 'Structure Designer',
        'structural-analyser': 'Structural Analyser',
        'active': 'Active',
        'completed': 'Completed',
        'pending': 'Pending'
    };

    /**
     * UI Classes
     */
    static UI_CLASSES = {
        SEARCH_HIGHLIGHT: {
            BACKGROUND: '#f0f9ff',
            BORDER: '2px solid #547bf7'
        },
        SEARCH_NORMAL: {
            BACKGROUND: '',
            BORDER: '1px solid #e2e8f0'
        }
    };

    /**
     * API settings
     */
    static API = {
        TIMEOUT: 30000,
        MAX_RETRIES: 3,
        BASE_URL: '/api'
    };

    /**
     * Validation rules
     */
    static VALIDATION = {
        PROJECT_NAME: {
            REQUIRED: true,
            MIN_LENGTH: 1,
            MAX_LENGTH: 100
        },
        SITE_ADDRESS: {
            REQUIRED: true,
            MIN_LENGTH: 3,
            MAX_LENGTH: 200
        }
    };
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardConfig };
}

// Make available globally
window.DashboardConfig = DashboardConfig;
