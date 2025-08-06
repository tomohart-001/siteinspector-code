/**
 * Project Snapshot Manager
 * Handles capturing and managing project snapshots at different stages
 */
class SnapshotManager {
    constructor(projectId) {
        this.projectId = projectId;
    }

    /**
     * Capture a site boundary snapshot
     */
    async captureSiteBoundary(coordinates, area = null) {
        const snapshotData = {
            coordinates: coordinates,
            area_m2: area,
            timestamp: new Date().toISOString()
        };

        return await this.saveSnapshot('site_boundary', JSON.stringify(snapshotData), 'Site boundary defined');
    }

    /**
     * Capture a buildable area snapshot
     */
    async captureBuildableArea(buildableAreaData) {
        const snapshotData = {
            buildable_area_m2: buildableAreaData.buildable_area_m2,
            coverage_ratio: buildableAreaData.coverage_ratio,
            setbacks: buildableAreaData.setbacks,
            timestamp: new Date().toISOString()
        };

        return await this.saveSnapshot('buildable_area', snapshotData, `Buildable area: ${Math.round(buildableAreaData.buildable_area_m2)} m²`);
    }

    /**
     * Capture a structure design snapshot
     */
    async captureStructureDesign(structureData) {
        const snapshotData = {
            structure_type: structureData.structure_type,
            spans: structureData.spans,
            dimensions: structureData.dimensions,
            materials: structureData.materials,
            timestamp: new Date().toISOString()
        };

        return await this.saveSnapshot('structure_design', snapshotData, `${structureData.structure_type} structure designed`);
    }

    /**
     * Capture a structural analysis snapshot
     */
    async captureStructuralAnalysis(analysisData) {
        const snapshotData = {
            max_deflection: analysisData.max_deflection,
            max_stress: analysisData.max_stress,
            status: analysisData.status,
            safety_factor: analysisData.safety_factor,
            timestamp: new Date().toISOString()
        };

        return await this.saveSnapshot('structural_analysis', snapshotData, `Analysis completed - ${analysisData.status}`);
    }

    /**
     * Capture a terrain analysis snapshot
     */
    async captureTerrainAnalysis(terrainData) {
        const snapshotData = {
            elevation_data: terrainData.elevation_data,
            slope_analysis: terrainData.slope_analysis,
            cut_fill_volumes: terrainData.cut_fill_volumes,
            timestamp: new Date().toISOString()
        };

        return await this.saveSnapshot('terrain_analysis', snapshotData, 'Terrain analysis completed');
    }

    /**
     * Save snapshot to the server
     */
    async saveSnapshot(snapshotType, snapshotData, description) {
        try {
            const response = await fetch(`/api/project/${this.projectId}/snapshot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    snapshot_type: snapshotType,
                    snapshot_data: JSON.stringify(snapshotData),
                    description: description
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log(`[SnapshotManager] Snapshot saved: ${snapshotType}`, result);
                return result;
            } else {
                console.error(`[SnapshotManager] Failed to save snapshot: ${snapshotType}`);
                return null;
            }
        } catch (error) {
            console.error(`[SnapshotManager] Error saving snapshot:`, error);
            return null;
        }
    }

    /**
     * Get the latest snapshot
     */
    async getLatestSnapshot(snapshotType = null) {
        try {
            const url = snapshotType 
                ? `/api/project/${this.projectId}/snapshot?type=${snapshotType}`
                : `/api/project/${this.projectId}/snapshot`;

            const response = await fetch(url);
            if (response.ok) {
                const result = await response.json();
                return result.snapshot;
            }
            return null;
        } catch (error) {
            console.error(`[SnapshotManager] Error getting snapshot:`, error);
            return null;
        }
    }
}

// Auto-initialize snapshot manager when project ID is available
window.initializeSnapshotManager = function(projectId) {
    window.snapshotManager = new SnapshotManager(projectId);
    console.log(`[SnapshotManager] Initialized for project ${projectId}`);
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SnapshotManager;
}