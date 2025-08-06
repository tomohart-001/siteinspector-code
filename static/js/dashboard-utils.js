
/**
 * Dashboard Utilities Module
 * 
 * Shared utility functions used across dashboard components
 */

class DashboardUtils {
    /**
     * Format date for display
     */
    static formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    /**
     * Get project type CSS class
     */
    static getProjectTypeClass(type) {
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
    static getProjectIcon(type) {
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
    static getStatusText(status) {
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
        return statusMap[status] || status;
    }

    /**
     * Debounce utility function
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Escape HTML to prevent XSS
     */
    static escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, (m) => map[m]);
    }

    /**
     * Truncate text with ellipsis
     */
    static truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    }

    /**
     * Generate unique ID
     */
    static generateId(prefix = 'id') {
        return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DashboardUtils };
}

// Make available globally
window.DashboardUtils = DashboardUtils;
