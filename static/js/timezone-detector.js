
/**
 * Timezone Detection Utility
 * Detects user's timezone and sends it to the server
 */

class TimezoneDetector {
    static init() {
        // Detect user's timezone
        const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        
        // Send to server
        TimezoneDetector.setUserTimezone(timezone);
        
        console.log('[TimezoneDetector] Detected timezone:', timezone);
    }
    
    static setUserTimezone(timezone) {
        // Set in session storage for persistence
        sessionStorage.setItem('user_timezone', timezone);
        
        // Send to server via AJAX
        fetch('/api/set-timezone', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Timezone': timezone
            },
            body: JSON.stringify({ timezone: timezone })
        }).catch(error => {
            console.warn('[TimezoneDetector] Failed to set timezone on server:', error);
        });
    }
    
    static getUserTimezone() {
        return sessionStorage.getItem('user_timezone') || 
               Intl.DateTimeFormat().resolvedOptions().timeZone;
    }
    
    static formatDateTime(dateString, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        };
        
        const formatOptions = { ...defaultOptions, ...options };
        const timezone = TimezoneDetector.getUserTimezone();
        
        try {
            const date = new Date(dateString);
            return date.toLocaleString('en-NZ', { 
                ...formatOptions, 
                timeZone: timezone 
            });
        } catch (error) {
            console.error('[TimezoneDetector] Date formatting error:', error);
            return 'Invalid date';
        }
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    TimezoneDetector.init();
});

// Export for use in other modules
window.TimezoneDetector = TimezoneDetector;
