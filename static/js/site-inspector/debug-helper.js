
/**
 * Debug Helper for Site Inspector
 * Provides comprehensive debugging and validation tools
 */

class SiteInspectorDebugger {
    constructor() {
        this.debugEnabled = true;
        this.errorCount = 0;
        this.warningCount = 0;
        this.validationResults = {};
    }

    // Comprehensive system validation
    validateSystem() {
        console.log('🔍 Starting Site Inspector System Validation...');
        
        const results = {
            dependencies: this.validateDependencies(),
            dom: this.validateDOMElements(),
            managers: this.validateManagers(),
            api: this.validateAPIEndpoints(),
            errors: this.checkForErrors()
        };

        this.validationResults = results;
        this.displayValidationReport(results);
        return results;
    }

    validateDependencies() {
        const deps = {
            mapboxgl: typeof mapboxgl !== 'undefined',
            MapboxDraw: typeof MapboxDraw !== 'undefined',
            turf: typeof turf !== 'undefined',
            BaseManager: typeof BaseManager !== 'undefined'
        };

        console.log('📦 Dependencies Check:', deps);
        return deps;
    }

    validateDOMElements() {
        const elements = {
            inspectorMap: !!document.getElementById('inspectorMap'),
            inspectorPanel: !!document.getElementById('inspectorPanel'),
            siteBoundaryControls: !!document.getElementById('siteBoundaryControls'),
            boundaryControls: !!document.getElementById('boundaryControls'),
            floorplanControls: !!document.getElementById('floorplanControls'),
            searchControl: !!document.getElementById('searchControl'),
            measureToolButton: !!document.getElementById('measureToolButton')
        };

        console.log('🎯 DOM Elements Check:', elements);
        return elements;
    }

    validateManagers() {
        const core = window.siteInspectorCore;
        if (!core) {
            console.log('❌ SiteInspectorCore not found');
            return { core: false };
        }

        const managers = {
            core: !!core,
            map: !!core.map,
            draw: !!core.draw,
            siteBoundaryManager: !!core.siteBoundaryManager,
            propertySetbacksManager: !!core.propertySetbacksManager,
            floorplanManager: !!core.floorplanManager,
            mapFeaturesManager: !!core.mapFeaturesManager,
            uiPanelManager: !!core.uiPanelManager
        };

        console.log('🏗️ Managers Check:', managers);
        return managers;
    }

    async validateAPIEndpoints() {
        const endpoints = [
            '/api/mapbox-token',
            '/api/geocode-location',
            '/api/get-project-address'
        ];

        const results = {};
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(endpoint, {
                    method: endpoint === '/api/geocode-location' ? 'POST' : 'GET',
                    headers: { 'Content-Type': 'application/json' },
                    body: endpoint === '/api/geocode-location' ? 
                        JSON.stringify({ query: 'test' }) : undefined
                });
                results[endpoint] = response.status;
            } catch (error) {
                results[endpoint] = `Error: ${error.message}`;
            }
        }

        console.log('🌐 API Endpoints Check:', results);
        return results;
    }

    checkForErrors() {
        const errors = [];
        const warnings = [];

        // Check console for errors
        if (window.console && console.error.toString().includes('[native code]')) {
            // Override console.error temporarily to catch errors
            const originalError = console.error;
            console.error = (...args) => {
                errors.push(args.join(' '));
                originalError.apply(console, args);
            };
        }

        return { errors, warnings, count: errors.length };
    }

    displayValidationReport(results) {
        console.log('\n🎯 SITE INSPECTOR VALIDATION REPORT');
        console.log('====================================');
        
        // Dependencies
        const depsOk = Object.values(results.dependencies).every(v => v);
        console.log(`📦 Dependencies: ${depsOk ? '✅ PASS' : '❌ FAIL'}`);
        
        // DOM Elements
        const domOk = Object.values(results.dom).every(v => v);
        console.log(`🎯 DOM Elements: ${domOk ? '✅ PASS' : '❌ FAIL'}`);
        
        // Managers
        const managersOk = Object.values(results.managers).every(v => v);
        console.log(`🏗️ Managers: ${managersOk ? '✅ PASS' : '❌ FAIL'}`);
        
        // Overall status
        const overallOk = depsOk && domOk && managersOk;
        console.log(`\n🎯 OVERALL STATUS: ${overallOk ? '✅ HEALTHY' : '❌ ISSUES DETECTED'}`);
        
        if (!overallOk) {
            console.log('\n🔧 RECOMMENDATIONS:');
            
            if (!depsOk) {
                Object.entries(results.dependencies).forEach(([dep, ok]) => {
                    if (!ok) console.log(`   - Load ${dep} library`);
                });
            }
            
            if (!domOk) {
                Object.entries(results.dom).forEach(([elem, ok]) => {
                    if (!ok) console.log(`   - Check DOM element: ${elem}`);
                });
            }
            
            if (!managersOk) {
                Object.entries(results.managers).forEach(([mgr, ok]) => {
                    if (!ok) console.log(`   - Initialize manager: ${mgr}`);
                });
            }
        }
        
        console.log('====================================\n');
    }

    // Performance monitoring
    startPerformanceMonitoring() {
        this.performanceMarks = {};
        
        // Monitor initialization time
        performance.mark('site-inspector-start');
        
        // Monitor map loading
        if (window.siteInspectorCore?.map) {
            window.siteInspectorCore.map.on('load', () => {
                performance.mark('map-loaded');
                performance.measure('map-load-time', 'site-inspector-start', 'map-loaded');
                console.log('📊 Map load time:', performance.getEntriesByName('map-load-time')[0].duration + 'ms');
            });
        }
    }

    // Memory usage monitoring
    logMemoryUsage() {
        if (performance.memory) {
            console.log('💾 Memory Usage:', {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB',
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024) + 'MB',
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024) + 'MB'
            });
        }
    }

    // Export debug data
    exportDebugData() {
        const debugData = {
            timestamp: new Date().toISOString(),
            validation: this.validationResults,
            userAgent: navigator.userAgent,
            url: window.location.href,
            performance: performance.getEntries(),
            errors: this.errorCount,
            warnings: this.warningCount
        };

        console.log('📋 Debug data exported:', debugData);
        return debugData;
    }
}

// Global debug instance
window.siteInspectorDebugger = new SiteInspectorDebugger();

// Auto-validate on load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.siteInspectorDebugger.validateSystem();
        window.siteInspectorDebugger.startPerformanceMonitoring();
    }, 2000);
});

// Periodic health checks
setInterval(() => {
    window.siteInspectorDebugger.logMemoryUsage();
}, 30000);

console.log('🐛 Site Inspector Debugger loaded and ready');
