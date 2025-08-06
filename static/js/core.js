/**
 * Core JavaScript Module for EngineRoom Application
 * 
 * This module provides foundational classes and utilities used throughout
 * the EngineRoom application. It includes base managers, API clients,
 * and essential utility classes.
 * 
 * @author EngineRoom Development Team
 * @version 1.0.0
 * @since 2025-06-27
 * 
 * Features:
 * - BaseManager class for consistent logging and error handling
 * - ApiClient for standardized API communications
 * - EventEmitter for decoupled component communication
 * - Automatic backend error logging
 * 
 * Dependencies:
 * - Fetch API for network requests
 * - ES6+ JavaScript features
 */

/**
 * Base Manager Class
 * 
 * Provides a foundation for all manager classes in the application with:
 * - Consistent logging interface
 * - Automatic backend error reporting
 * - Standardized initialization patterns
 * - Error handling best practices
 * 
 * All manager classes should extend this base class to ensure
 * consistent behavior across the application.
 */
if (typeof BaseManager === 'undefined') {
class BaseManager {
    /**
     * Initialize the BaseManager
     * 
     * @param {string} name - The name of the manager for logging purposes
     */
    constructor(name) {
        this.name = name;
        this.initialized = false;

        // Log manager creation
        console.log(`[${this.name}] Manager created`);
    }

    /**
     * Core logging method with backend integration
     * 
     * Provides structured logging with automatic backend error reporting
     * for production monitoring and debugging.
     * 
     * @param {string} level - Log level (info, warn, error, debug)
     * @param {string} message - The log message
     * @param {any} data - Additional data to log (optional)
     */
    log(level, message, data) {
        data = data || null;
        const timestamp = new Date().toISOString();
        const logData = {
            timestamp,
            level: level.toUpperCase(),
            module: this.name,
            message,
            data
        };

        // Enhanced console logging with structured format
        const logMessage = `[${this.name}] ${level.toUpperCase()}: ${message}`;

        switch (level.toLowerCase()) {
            case 'error':
                console.error(logMessage, data || '');
                break;
            case 'warn':
                console.warn(logMessage, data || '');
                break;
            case 'debug':
                console.debug(logMessage, data || '');
                break;
            default:
                console.log(logMessage, data || '');
        }

        // Send to backend for centralized logging (async, non-blocking)
        this._sendLogToBackend(logData);
    }

    /**
     * Send log data to backend for centralized monitoring
     * 
     * This method sends log data to the backend asynchronously and
     * handles any failures gracefully to prevent disrupting the main application.
     * 
     * @param {Object} logData - Structured log data object
     * @private
     */
    async _sendLogToBackend(logData) {
        try {
            // Only send warnings and errors to backend to reduce noise
            if (!['ERROR', 'WARN'].includes(logData.level)) {
                return;
            }

            await fetch('/api/log-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    level: logData.level,
                    message: logData.message,
                    context: logData.data,
                    timestamp: logData.timestamp,
                    module: logData.module,
                    url: window.location.href,
                    userAgent: navigator.userAgent,
                    frontend_log: true
                })
            });
        } catch (error) {
            // Silently fail - don't disrupt the application if logging fails
            console.error('Failed to send log to backend:', error);
        }
    }

    /**
     * Log informational messages
     * 
     * @param {string} message - The message to log
     * @param {any} data - Optional additional data
     */
    info(message, data) {
        data = data || null;
        this.log('info', message, data);
    }

    /**
     * Log warning messages
     * 
     * @param {string} message - The message to log
     * @param {any} data - Optional additional data
     */
    warn(message, data) {
        data = data || null;
        this.log('warn', message, data);
    }

    /**
     * Log error messages
     * 
     * @param {string} message - The message to log
     * @param {any} data - Optional additional data
     */
    error(message, data) {
        data = data || null;
        this.log('error', message, data);
    }

    /**
     * Log debug messages
     * 
     * @param {string} message - The message to log
     * @param {any} data - Optional additional data
     */
    debug(message, data) {
        data = data || null;
        this.log('debug', message, data);
    }
}

// Export BaseManager to global scope
window.BaseManager = BaseManager;
}

/**
 * ApiClient class for handling HTTP requests
 */
if (typeof window.ApiClient === 'undefined') {
class ApiClient extends BaseManager {
    /**
     * Initialize the ApiClient
     */
    constructor() {
        super('ApiClient');

        this.baseUrl = '/api';
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };

        // Request timeout in milliseconds
        this.timeout = 30000; // 30 seconds

        // Maximum retry attempts for failed requests
        this.maxRetries = 3;

        this.info('ApiClient initialized', {
            baseUrl: this.baseUrl,
            timeout: this.timeout,
            maxRetries: this.maxRetries
        });
    }

    /**
     * Make an HTTP request with comprehensive error handling
     * 
     * This is the core request method that handles:
     * - Request logging
     * - Timeout handling
     * - Response validation
     * - Error reporting
     * - Retry logic for failed requests
     * 
     * @param {string} endpoint - The API endpoint (relative to baseUrl)
     * @param {Object} options - Fetch options (method, headers, body, etc.)
     * @param {number} retryCount - Current retry attempt (used internally)
     * @returns {Promise<Object>} Parsed JSON response
     */
    async request(endpoint, options, retryCount) {
        options = options || {};
        retryCount = retryCount || 0;

        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        config.signal = controller.signal;

        try {
            this.debug(`Making ${config.method || 'GET'} request to ${endpoint}`, {
                url,
                method: config.method || 'GET',
                retryCount
            });

            const response = await fetch(url, config);
            clearTimeout(timeoutId);

            // Log response details
            this.debug(`Response received from ${endpoint}`, {
                status: response.status,
                ok: response.ok,
                statusText: response.statusText
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.debug(`Request successful for ${endpoint}`, { 
                endpoint, 
                status: response.status,
                dataSize: JSON.stringify(data).length 
            });

            return data;

        } catch (error) {
            clearTimeout(timeoutId);

            // Handle different types of errors
            let errorType = 'UNKNOWN_ERROR';
            let shouldRetry = false;

            if (error.name === 'AbortError') {
                errorType = 'TIMEOUT_ERROR';
                shouldRetry = true;
            } else if (error.message.includes('Failed to fetch')) {
                errorType = 'NETWORK_ERROR';
                shouldRetry = true;
            } else if (error.message.includes('HTTP 5')) {
                errorType = 'SERVER_ERROR';
                shouldRetry = true;
            }

            this.error(`Request failed for ${endpoint}`, { 
                error: error.message,
                errorType,
                retryCount,
                config: {
                    method: config.method,
                    url
                }
            });

            // Retry logic for recoverable errors
            if (shouldRetry && retryCount < this.maxRetries) {
                this.warn(`Retrying request to ${endpoint}`, {
                    retryCount: retryCount + 1,
                    maxRetries: this.maxRetries
                });

                // Exponential backoff: wait 1s, 2s, 4s between retries
                const delay = Math.pow(2, retryCount) * 1000;
                await new Promise(resolve => setTimeout(resolve, delay));

                return this.request(endpoint, options, retryCount + 1);
            }

            throw error;
        }
    }

    /**
     * Make a GET request
     * 
     * @param {string} endpoint - The API endpoint
     * @param {Object} params - Query parameters as key-value pairs
     * @returns {Promise<Object>} API response data
     */
    async get(endpoint, params) {
        params = params || {};
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;

        return this.request(url, { method: 'GET' });
    }

    /**
     * Make a POST request
     * 
     * @param {string} endpoint - The API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise<Object>} API response data
     */
    async post(endpoint, data) {
        data = data || {};
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Make a PUT request
     * 
     * @param {string} endpoint - The API endpoint
     * @param {Object} data - Request body data
     * @returns {Promise<Object>} API response data
     */
    async put(endpoint, data) {
        data = data || {};
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * Make a DELETE request
     * 
     * @param {string} endpoint - The API endpoint
     * @returns {Promise<Object>} API response data
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    /**
     * Check API health status
     * 
     * @returns {Promise<boolean>} True if API is healthy
     */
    async checkHealth() {
        try {
            this.info('Checking API health...');
            await this.get('/health');
            this.info('API health check passed');
            return true;
        } catch (error) {
            this.error('API health check failed', error);
            return false;
        }
    }

    /**
     * Debug gradient calculation
     * 
     * @param {Object} siteData - Site data for gradient calculation
     * @returns {Promise<Object>} Gradient debug response
     */
    async debugGradient(siteData) {
        try {
            this.info('Running gradient debug...', {
                siteDataKeys: siteData ? Object.keys(siteData) : [],
                hasCoordinates: !!(siteData && siteData.coordinates),
                hasCenter: !!(siteData && siteData.center),
                hasArea: !!(siteData && siteData.area)
            });

            const response = await this.post('/debug-gradient', siteData);

            this.info('Gradient debug completed', {
                success: response.success,
                method: response.gradient_data?.method,
                calculated: response.gradient_data?.calculated,
                slope: response.gradient_data?.slope,
                aspect: response.gradient_data?.aspect
            });

            return response;
        } catch (error) {
            this.error('Gradient debug failed', {
                error: error.message,
                siteDataProvided: !!siteData
            });
            throw error;
        }
    }

    /**
     * Test gradient calculation with current site data
     * 
     * @returns {Promise<Object>} Test results
     */
    async testGradientCalculation() {
        try {
            // Get site data from session storage or current page
            let siteData = null;

            if (typeof window !== 'undefined' && window.siteInspector && window.siteInspector.siteData) {
                siteData = window.siteInspector.siteData;
            } else if (typeof sessionStorage !== 'undefined') {
                try {
                    const stored = sessionStorage.getItem('site_data');
                    if (stored) {
                        siteData = JSON.parse(stored);
                    }
                } catch (e) {
                    this.warn('Failed to parse stored site data', e);
                }
            }

            if (!siteData) {
                throw new Error('No site data available for gradient testing');
            }

            this.info('Testing gradient calculation with current site data');
            const result = await this.debugGradient(siteData);

            return result;
        } catch (error) {
            this.error('Gradient test failed', error);
            throw error;
        }
    }

    async makeRequest(endpoint, options = {}) {
            const url = `${this.baseUrl}${endpoint}`;
            const requestOptions = {
                ...this.defaultOptions,
                ...options,
                headers: {
                    ...this.defaultOptions.headers,
                    ...(options.headers || {})
                }
            };

            let lastError;
            for (let attempt = 0; attempt < this.maxRetries; attempt++) {
                try {
                    this.log('DEBUG', `Making ${requestOptions.method || 'GET'} request to ${endpoint}`, {
                        url,
                        method: requestOptions.method || 'GET',
                        retryCount: attempt
                    });

                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

                    const response = await fetch(url, {
                        ...requestOptions,
                        signal: controller.signal
                    });

                    clearTimeout(timeoutId);

                    this.log('DEBUG', `Response received from ${endpoint}`, {
                        status: response.status,
                        ok: response.ok,
                        statusText: response.statusText
                    });

                    if (response.ok) {
                        const data = await response.json();
                        this.log('DEBUG', `Request successful for ${endpoint}`, {
                            endpoint,
                            status: response.status,
                            dataSize: JSON.stringify(data).length
                        });
                        return data;
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                } catch (error) {
                    lastError = error;

                    // Don't retry for certain error types
                    if (error.name === 'AbortError') {
                        this.log('WARN', `Request timeout for ${endpoint}`, { timeout: this.timeout });
                        break;
                    }

                    this.log('WARN', `Request attempt ${attempt + 1} failed for ${endpoint}`, {
                        error: error.message,
                        attempt: attempt + 1,
                        maxRetries: this.maxRetries
                    });

                    if (attempt < this.maxRetries - 1) {
                        await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
                    }
                }
            }

            // Try direct fetch as fallback
            try {
                this.log('WARN', 'ApiClient failed, trying direct fetch');
                const directResponse = await fetch(url, requestOptions);
                if (directResponse.ok) {
                    return await directResponse.json();
                }
            } catch (fallbackError) {
                this.log('ERROR', 'Direct fetch also failed', { error: fallbackError.message });
            }

            this.log('ERROR', `All retry attempts failed for ${endpoint}`, {
                error: lastError.message,
                totalAttempts: this.maxRetries
            });
            throw lastError;
        }
}

window.ApiClient = ApiClient;
}

/**
 * EventEmitter for managing custom events
 */
window.EventEmitter = class EventEmitter {
    /**
     * Initialize the EventEmitter
     */
    constructor() {
        this.events = {};
        this.maxListeners = 10; // Prevent memory leaks

        console.log('[EventEmitter] Created new EventEmitter instance');
    }

    /**
     * Register an event listener
     * 
     * @param {string} event - Event name to listen for
     * @param {function} listener - Callback function to execute
     */
    on(event, listener) {
        if (!this.events[event]) {
            this.events[event] = [];
        }

        // Check for too many listeners (potential memory leak)
        if (this.events[event].length >= this.maxListeners) {
            console.warn(`[EventEmitter] Warning: Event '${event}' has ${this.events[event].length} listeners. Possible memory leak?`);
        }

        this.events[event].push(listener);

        console.debug(`[EventEmitter] Listener added for event '${event}'. Total listeners: ${this.events[event].length}`);
    }

    /**
     * Emit an event to all registered listeners
     * 
     * @param {string} event - Event name to emit
     * @param {...any} args - Arguments to pass to listeners
     */
    emit(event, ...args) {
        if (!this.events[event]) {
            console.debug(`[EventEmitter] No listeners for event '${event}'`);
            return;
        }

        const listeners = this.events[event];
        console.debug(`[EventEmitter] Emitting event '${event}' to ${listeners.length} listeners`);

        listeners.forEach((listener, index) => {
            try {
                listener(...args);
            } catch (error) {
                console.error(`[EventEmitter] Error in listener ${index} for event '${event}':`, error);

                // Send error to backend if available
                if (window.EngineRoomApp && window.EngineRoomApp.sendErrorToBackend) {
                    window.EngineRoomApp.sendErrorToBackend(error, `EVENT_LISTENER_ERROR:${event}`);
                }
            }
        });
    }

    /**
     * Remove a specific event listener
     * 
     * @param {string} event - Event name
     * @param {function} listenerToRemove - Specific listener function to remove
     */
    off(event, listenerToRemove) {
        if (!this.events[event]) {
            console.debug(`[EventEmitter] No listeners found for event '${event}' to remove`);
            return;
        }

        const initialLength = this.events[event].length;
        this.events[event] = this.events[event].filter(listener => listener !== listenerToRemove);

        const removedCount = initialLength - this.events[event].length;
        console.debug(`[EventEmitter] Removed ${removedCount} listeners for event '${event}'. Remaining: ${this.events[event].length}`);

        // Clean up empty event arrays
        if (this.events[event].length === 0) {
            delete this.events[event];
        }
    }

    /**
     * Remove all listeners for a specific event
     * 
     * @param {string} event - Event name
     */
    removeAllListeners(event) {
        if (event) {
            const count = this.events[event] ? this.events[event].length : 0;
            delete this.events[event];
            console.debug(`[EventEmitter] Removed all ${count} listeners for event '${event}'`);
        } else {
            // Remove all listeners for all events
            const totalCount = Object.values(this.events).reduce((sum, listeners) => sum + listeners.length, 0);
            this.events = {};
            console.debug(`[EventEmitter] Removed all ${totalCount} listeners for all events`);
        }
    }

    /**
     * Get the number of listeners for an event
     * 
     * @param {string} event - Event name
     * @returns {number} Number of listeners
     */
    listenerCount(event) {
        return this.events[event] ? this.events[event].length : 0;
    }

    /**
     * Get all registered event names
     * 
     * @returns {string[]} Array of event names
     */
    eventNames() {
        return Object.keys(this.events);
    }

    /**
     * Set maximum number of listeners per event
     * 
     * @param {number} n - Maximum number of listeners
     */
    setMaxListeners(n) {
        this.maxListeners = n;
        console.debug(`[EventEmitter] Max listeners set to ${n}`);
    }
}

/**
 * Utility Functions
 */

/**
 * Debounce function to limit function calls
 * 
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function} Debounced function
 */
function debounce(func, wait) {
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
 * Throttle function to limit function calls
 * 
 * @param {function} func - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {function} Throttled function
 */
function throttle(func, limit) {
    let lastFunc;
    let lastRan;
    return function(...args) {
        if (!lastRan) {
            func(...args);
            lastRan = Date.now();
        } else {
            clearTimeout(lastFunc);
            lastFunc = setTimeout(() => {
                if ((Date.now() - lastRan) >= limit) {
                    func(...args);
                    lastRan = Date.now();
                }
            }, limit - (Date.now() - lastRan));
        }
    };
}

/**
 * Initialize Core Module
 * 
 * Create global instances and expose utilities
 */
function initializeCoreModule() {
    try {
        // Create global API client instance
        window.apiClient = new ApiClient();

        // Create global event emitter for cross-component communication
        window.eventBus = new EventEmitter();

        // Expose utility functions
        window.debounce = debounce;
        window.throttle = throttle;

        console.log('✅ Core JavaScript module loaded successfully');

        // Defer logging to avoid blocking
        setTimeout(() => {
            if (window.apiClient) {
                window.apiClient.info('Core module initialized', {
                    apiClient: 'ready',
                    eventBus: 'ready',
                    utilities: 'ready'
                });
            }
        }, 100);

    } catch (error) {
        console.error('❌ Failed to initialize core module:', error);

        // Defer error reporting to avoid blocking
        setTimeout(() => {
            if (typeof fetch !== 'undefined') {
                fetch('/api/log-error', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        frontend_error: true,
                        level: 'CRITICAL',
                        message: 'Core module initialization failed',
                        stack: error.stack,
                        context: 'CORE_MODULE_INIT_FAILURE',
                        timestamp: new Date().toISOString()
                    })
                }).catch(() => {
                    console.error('Could not report core module failure to backend');
                });
            }
        }, 100);
    }
}

// Use requestIdleCallback for better performance, fallback to setTimeout
if (window.requestIdleCallback) {
    document.addEventListener('DOMContentLoaded', function() {
        requestIdleCallback(initializeCoreModule, { timeout: 1000 });
    });
} else {
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(initializeCoreModule, 50);
    });
}

/**
 * Export classes for module environments
 */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        BaseManager,
        ApiClient,
        EventEmitter,
        debounce,
        throttle
    };
}