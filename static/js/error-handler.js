
/**
 * Frontend Error Handler
 * Handles JavaScript syntax errors and runtime exceptions
 */

class FrontendErrorHandler {
    constructor() {
        this.setupGlobalErrorHandling();
        this.setupUnhandledRejectionHandling();
        this.errorCount = 0;
        this.maxErrors = 50;
    }

    setupGlobalErrorHandling() {
        window.addEventListener('error', (event) => {
            this.handleError({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                line: event.lineno,
                column: event.colno,
                error: event.error,
                stack: event.error?.stack
            });
        });
    }

    setupUnhandledRejectionHandling() {
        window.addEventListener('unhandledrejection', (event) => {
            this.handleError({
                type: 'unhandled_promise_rejection',
                message: event.reason?.message || 'Unhandled promise rejection',
                error: event.reason,
                stack: event.reason?.stack
            });
        });
    }

    handleError(errorData) {
        if (this.errorCount >= this.maxErrors) {
            console.warn('Maximum error count reached, stopping error logging');
            return;
        }

        this.errorCount++;

        // Enhanced error data
        const enhancedErrorData = {
            ...errorData,
            url: window.location.href,
            userAgent: navigator.userAgent,
            timestamp: new Date().toISOString(),
            level: this.getErrorLevel(errorData)
        };

        // Log to console for development
        console.error('[FrontendErrorHandler]', enhancedErrorData);

        // Send to backend for logging
        this.logToBackend(enhancedErrorData);

        // Check if this is a critical error type
        const criticalErrors = ['ChunkLoadError', 'TypeError', 'ReferenceError', 'SyntaxError'];
        const isCritical = criticalErrors.some(type => 
            errorData.message?.includes(type) || errorData.type?.includes(type)
        );

        if (isCritical && this.errorCount <= 3) {
            this.showErrorNotification('A technical issue occurred. The page may not work correctly. Please refresh if needed.');
        }
    }

    getErrorLevel(errorData) {
        const criticalErrors = ['ChunkLoadError', 'TypeError', 'ReferenceError', 'SyntaxError'];
        const warningErrors = ['404', 'Network'];
        
        if (criticalErrors.some(type => errorData.message?.includes(type) || errorData.type?.includes(type))) {
            return 'ERROR';
        }
        if (warningErrors.some(type => errorData.message?.includes(type) || errorData.type?.includes(type))) {
            return 'WARNING';
        }
        return 'INFO';
    }

    async logToBackend(errorData) {
        try {
            await fetch('/api/log-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(errorData)
            });
        } catch (error) {
            console.error('Failed to log error to backend:', error);
        }
    }

    showErrorNotification(message) {
        // Create a simple notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            padding: 12px 20px;
            border-radius: 4px;
            z-index: 10000;
            max-width: 300px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

        // Log to console with enhanced formatting
        console.error(`🚨 [FrontendError #${this.errorCount}] ${errorData.type}:`, {
            message: errorData.message,
            location: errorData.filename ? `${errorData.filename}:${errorData.line}:${errorData.column}` : 'Unknown',
            stack: errorData.stack,
            timestamp: new Date().toISOString()
        });

        // Send to backend for logging
        this.sendErrorToBackend(errorData);

        // Show user-friendly message for critical errors
        this.showUserFriendlyError(errorData);
    }

    async sendErrorToBackend(errorData) {
        try {
            const response = await fetch('/api/log-error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    level: 'ERROR',
                    message: errorData.message,
                    error: errorData.type,
                    stack: errorData.stack,
                    context: {
                        filename: errorData.filename,
                        line: errorData.line,
                        column: errorData.column,
                        userAgent: navigator.userAgent,
                        url: window.location.href,
                        timestamp: new Date().toISOString()
                    }
                }),
                timeout: 5000
            });
            
            if (!response.ok) {
                console.warn(`Error logging failed with status: ${response.status}`);
            }
        } catch (error) {
            console.warn('Failed to send error to backend:', error);
        }
    }

    showUserFriendlyError(errorData) {
        // Only show messages for critical errors that affect user experience
        const criticalErrors = [
            'TypeError',
            'ReferenceError',
            'SyntaxError'
        ];

        const isCritical = criticalErrors.some(type => 
            errorData.message?.includes(type) || errorData.type?.includes(type)
        );

        if (isCritical && this.errorCount <= 3) {
            this.showErrorNotification('A technical issue occurred. The page may not work correctly. Please refresh if needed.');
        }
    }

    showErrorNotification(message) {
        // Create or update error notification
        let notification = document.getElementById('error-notification');
        
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'error-notification';
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ff4444;
                color: white;
                padding: 12px 16px;
                border-radius: 4px;
                font-size: 14px;
                z-index: 10000;
                max-width: 300px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                cursor: pointer;
            `;
            
            notification.onclick = () => notification.remove();
            document.body.appendChild(notification);
            
            // Auto-remove after 10 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 10000);
        }
        
        notification.textContent = message;
    }

    // Safe function wrapper to catch errors
    safeExecute(fn, context = 'unknown') {
        try {
            return fn();
        } catch (error) {
            this.handleError({
                type: 'safe_execute_error',
                message: `Error in ${context}: ${error.message}`,
                error: error,
                stack: error.stack
            });
            return null;
        }
    }

    // Safe async function wrapper
    async safeExecuteAsync(fn, context = 'unknown') {
        try {
            return await fn();
        } catch (error) {
            this.handleError({
                type: 'safe_execute_async_error',
                message: `Async error in ${context}: ${error.message}`,
                error: error,
                stack: error.stack
            });
            return null;
        }
    }

    // Validate and fix common syntax issues
    validateFunction(fn, name) {
        if (typeof fn !== 'function') {
            this.handleError({
                type: 'validation_error',
                message: `Expected function but got ${typeof fn} for ${name}`
            });
            return false;
        }
        return true;
    }
}

// Create global error handler instance
window.errorHandler = new FrontendErrorHandler();

// Utility functions for safe execution
window.safeExecute = (fn, context) => window.errorHandler.safeExecute(fn, context);
window.safeExecuteAsync = (fn, context) => window.errorHandler.safeExecuteAsync(fn, context);

console.log('🛡️ Frontend error handler initialized successfully');t)lized');
