/**
 * Structure Designer Structures - Structural Elements Management
 * Handles columns, beams, slabs, and rigid frame generation
 */

class StructureDesignerStructures {
    constructor(core) {
        this.core = core;
        this.state = {
            slab: null,
            columns: [],
            ridgeBeam: null,
            rafterBeams: [],
            objects3D: [],
            columnLayout: {
                numRows: 3,
                numCols: 4,
                xOffset: 1.0,
                yOffset: 1.0,
                columnWidth: 0.4,
                columnLength: 0.4,
                crossSectionType: 'i-beam',
                iBeamDimensions: {
                    depth: 400,
                    width: 200,
                    flangeThickness: 12,
                    webThickness: 12
                }
            },
            rigidFrameParams: null,
            rafterBeamDimensions: {
                depth: 300,
                width: 150,
                flangeThickness: 10,
                webThickness: 8
            }
        };
    }

    setupStructuralEventListeners() {
        // Slab controls
        const drawSlabBtn = document.getElementById('drawSlabBtn');
        const createCompleteStructureBtn = document.getElementById('createCompleteStructureBtn');
        const clearLayoutBtn = document.getElementById('clearLayoutBtn');

        if (drawSlabBtn) drawSlabBtn.addEventListener('click', () => this.drawSlab());
        if (createCompleteStructureBtn) createCompleteStructureBtn.addEventListener('click', () => this.createCompleteStructure());
        if (clearLayoutBtn) clearLayoutBtn.addEventListener('click', () => this.clearLayout());

        // Column controls
        const generateColumnsBtn = document.getElementById('generateColumnsBtn');
        const extrudeColumnsBtn = document.getElementById('extrudeColumnsBtn');
        const clearExtrudedColumnsBtn = document.getElementById('clearExtrudedColumnsBtn');

        if (generateColumnsBtn) generateColumnsBtn.addEventListener('click', () => this.generateColumnLayout());
        if (extrudeColumnsBtn) extrudeColumnsBtn.addEventListener('click', () => this.extrudeAllColumns());
        if (clearExtrudedColumnsBtn) clearExtrudedColumnsBtn.addEventListener('click', () => this.clearExtrudedColumns());

        // Column layout parameters
        ['numRows', 'numCols', 'xOffset', 'yOffset', 'columnWidth', 'columnLength'].forEach(paramId => {
            const element = document.getElementById(paramId);
            if (element) {
                element.addEventListener('input', (e) => {
                    this.updateColumnLayoutParameter(paramId, parseFloat(e.target.value));
                });
            }
        });

        // Beam controls
        const generateRidgeBeamBtn = document.getElementById('generateRidgeBeamBtn');
        const clearRidgeBeamBtn = document.getElementById('clearRidgeBeamBtn');
        const generateRafterBeamsBtn = document.getElementById('generateRafterBeamsBtn');
        const clearRafterBeamsBtn = document.getElementById('clearRafterBeamsBtn');

        if (generateRidgeBeamBtn) generateRidgeBeamBtn.addEventListener('click', () => this.generateRidgeBeam());
        if (clearRidgeBeamBtn) clearRidgeBeamBtn.addEventListener('click', () => this.clearRidgeBeam());
        if (generateRafterBeamsBtn) generateRafterBeamsBtn.addEventListener('click', () => this.generateRafterBeams());
        if (clearRafterBeamsBtn) clearRafterBeamsBtn.addEventListener('click', () => this.clearRafterBeams());

        // Rigid frame controls
        const generateRigidFrameBtn = document.getElementById('generateRigidFrameBtn');
        const generateHybridFrameBtn = document.getElementById('generateHybridFrameBtn');
        const generatePortalFrameBtn = document.getElementById('generatePortalFrameBtn');
        const autoGenerateSlabBtn = document.getElementById('autoGenerateSlabBtn');
        const clearAllObjectsBtn = document.getElementById('clearAllObjectsBtn');

        if (generateRigidFrameBtn) generateRigidFrameBtn.addEventListener('click', () => this.generateRigidFrame());
        if (generateHybridFrameBtn) generateHybridFrameBtn.addEventListener('click', () => this.generateHybridFrame());
        if (generatePortalFrameBtn) generatePortalFrameBtn.addEventListener('click', () => this.generatePortalFrame());
        if (autoGenerateSlabBtn) autoGenerateSlabBtn.addEventListener('click', () => this.autoGenerateSlab());
        if (clearAllObjectsBtn) clearAllObjectsBtn.addEventListener('click', () => this.clearAllObjects());

        // Load beam specifications
        this.loadBeamSpecifications();

        // Structural system type change handler
        const structuralSystemType = document.getElementById('structuralSystemType');
        if (structuralSystemType) {
            structuralSystemType.addEventListener('change', (e) => {
                this.updateStructuralSystemParameters(e.target.value);
            });
            this.updateStructuralSystemParameters(structuralSystemType.value);
        }
    }

    drawSlab() {
        const width = parseFloat(document.getElementById('slabWidth').value) || 20;
        const length = parseFloat(document.getElementById('slabLength').value) || 15;

        this.clearSlab();

        if (this.core.state.currentView !== 'XY') {
            this.core.setView('XY');
        }

        const points = [
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(width, 0, 0),
            new THREE.Vector3(width, length, 0),
            new THREE.Vector3(0, length, 0),
            new THREE.Vector3(0, 0, 0)
        ];

        const geometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(geometry, this.core.materials.sketch);

        const slabSketch = {
            id: `slab_${Date.now()}`,
            type: 'rectangle',
            object: line,
            points: points,
            plane: 'XY',
            width: width,
            height: length,
            isSlab: true
        };

        this.core.scene.add(line);

        this.state.slab = {
            sketch: slabSketch,
            width: width,
            length: length,
            position: { x: 0, y: 0, z: 0 },
            thickness: 0
        };

        this.updateUI();
        console.log(`[StructureDesigner3D] Slab sketch created: ${width}m x ${length}m`);
    }

    generateColumnLayout() {
        if (!this.state.slab) {
            this.core.showError('Please draw a slab first');
            return;
        }

        this.clearColumns();

        const numRows = parseInt(document.getElementById('numRows').value) || 3;
        const numCols = parseInt(document.getElementById('numCols').value) || 4;
        const xOffset = parseFloat(document.getElementById('xOffset').value) || 2.0;
        const yOffset = parseFloat(document.getElementById('yOffset').value) || 2.0;
        const columnWidth = parseFloat(document.getElementById('columnWidth').value) || 0.4;
        const columnLength = parseFloat(document.getElementById('columnLength').value) || 0.4;

        const slabWidth = this.state.slab.width;
        const slabLength = this.state.slab.length;

        const availableWidth = slabWidth - (2 * xOffset);
        const availableLength = slabLength - (2 * yOffset);

        if (availableWidth <= 0 || availableLength <= 0) {
            this.core.showError('Offsets are too large for the slab dimensions');
            return;
        }

        const xSpacing = numCols > 1 ? availableWidth / (numCols - 1) : 0;
        const ySpacing = numRows > 1 ? availableLength / (numRows - 1) : 0;

        const baseColumnHeight = parseFloat(document.getElementById('baseColumnHeight').value) || 3.0;
        const roofPitchAngle = parseFloat(document.getElementById('roofPitchAngle').value) || 15.0;
        const pitchAngleRadians = roofPitchAngle * Math.PI / 180;

        const centreToCentreYSpacing = numRows > 1 ? availableLength / (numRows - 1) : 0;
        const roofRise = Math.tan(pitchAngleRadians) * (centreToCentreYSpacing * (numRows - 1) / 2);

        const rowHeights = [];
        for (let row = 0; row < numRows; row++) {
            const distanceFromCenter = Math.abs(row - (numRows - 1) / 2);
            const rowOffsetFactor = 1 - (2 * distanceFromCenter) / (numRows - 1);
            const height = baseColumnHeight + roofRise * rowOffsetFactor;
            rowHeights.push(height);
        }

        const columns = [];
        const crossSectionType = this.state.columnLayout.crossSectionType;

        for (let row = 0; row < numRows; row++) {
            for (let col = 0; col < numCols; col++) {
                let x, z;

                if (numCols === 1) {
                    x = 0;
                } else {
                    x = xOffset + (col * xSpacing);
                }

                if (numRows === 1) {
                    z = 0;
                } else {
                    z = yOffset + (row * ySpacing);
                }

                const slabThickness = this.state.slab && this.state.slab.thickness ? this.state.slab.thickness : 0;

                let points, sketchWidth, sketchHeight;

                if (crossSectionType === 'i-beam') {
                    const beamWidthM = this.state.columnLayout.iBeamDimensions.width / 1000;
                    const beamDepthM = this.state.columnLayout.iBeamDimensions.depth / 1000;

                    points = [
                        new THREE.Vector3(x - beamWidthM/2, z - beamDepthM/2, slabThickness),
                        new THREE.Vector3(x + beamWidthM/2, z - beamDepthM/2, slabThickness),
                        new THREE.Vector3(x + beamWidthM/2, z + beamDepthM/2, slabThickness),
                        new THREE.Vector3(x - beamWidthM/2, z + beamDepthM/2, slabThickness),
                        new THREE.Vector3(x - beamWidthM/2, z - beamDepthM/2, slabThickness)
                    ];
                    sketchWidth = beamWidthM;
                    sketchHeight = beamDepthM;
                } else {
                    points = [
                        new THREE.Vector3(x - columnWidth/2, z - columnLength/2, slabThickness),
                        new THREE.Vector3(x + columnWidth/2, z - columnLength/2, slabThickness),
                        new THREE.Vector3(x + columnWidth/2, z + columnLength/2, slabThickness),
                        new THREE.Vector3(x - columnWidth/2, z + columnLength/2, slabThickness),
                        new THREE.Vector3(x - columnWidth/2, z - columnLength/2, slabThickness)
                    ];
                    sketchWidth = columnWidth;
                    sketchHeight = columnLength;
                }

                const geometry = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geometry, this.core.materials.column);

                const columnSketch = {
                    id: `column_${row}_${col}_${Date.now()}`,
                    type: 'rectangle',
                    object: line,
                    points: points,
                    plane: 'XY',
                    width: sketchWidth,
                    height: sketchHeight,
                    isColumn: true,
                    crossSectionType: crossSectionType,
                    iBeamDimensions: crossSectionType === 'i-beam' ? {...this.state.columnLayout.iBeamDimensions} : null,
                    gridPosition: { row: row, col: col },
                    baseHeight: slabThickness,
                    centerPosition: { x: x, z: z }
                };

                this.core.scene.add(line);

                const columnData = {
                    sketch: columnSketch,
                    position: { x: x, y: slabThickness, z: z },
                    dimensions: { width: columnWidth, length: columnLength, height: rowHeights[row] },
                    gridPosition: { row: row, col: col },
                    baseHeight: slabThickness,
                    pitchedHeight: rowHeights[row]
                };

                columns.push(columnData);
            }
        }

        this.state.columns = columns;
        this.updateUI();

        console.log(`[StructureDesigner3D] Generated ${columns.length} column sketches in ${numRows}x${numCols} grid`);
    }

    extrudeAllColumns() {
        if (this.state.columns.length === 0) {
            this.core.showError('No columns to extrude. Generate column layout first.');
            return;
        }

        let extrudedCount = 0;
        const baseHeight = parseFloat(document.getElementById('columnHeight').value) || 3.0;

        this.state.columns.forEach((columnData, index) => {
            if (columnData.extrudedObject) {
                return;
            }

            if (!columnData.sketch) {
                return;
            }

            const height = columnData.pitchedHeight || baseHeight;
            const extruded = this.createExtrudedGeometry(columnData.sketch, height);

            if (extruded) {
                columnData.extrudedObject = extruded;
                columnData.dimensions.height = height;
                this.state.objects3D.push(extruded);
                this.core.scene.add(extruded.object);
                extrudedCount++;
            }
        });

        this.core.autoFitCamera();
        this.updateUI();

        if (extrudedCount > 0) {
            console.log(`[StructureDesigner3D] Successfully extruded ${extrudedCount} columns`);
            this.core.showSuccess(`Extruded ${extrudedCount} columns successfully`);
        }
    }

    createExtrudedGeometry(sketch, height) {
        let geometry = null;
        let mesh = null;

        switch (sketch.type) {
            case 'rectangle':
                if (sketch.isColumn) {
                    const rectCenter = this.getRectangleCenter(sketch);

                    if (sketch.crossSectionType === 'i-beam') {
                        const iBeamShape = this.createIBeamShape(sketch.iBeamDimensions);
                        const extrudeSettings = {
                            depth: height,
                            bevelEnabled: false
                        };
                        geometry = new THREE.ExtrudeGeometry(iBeamShape, extrudeSettings);
                        mesh = new THREE.Mesh(geometry, this.core.materials.column);
                        mesh.position.set(rectCenter.x, rectCenter.y, rectCenter.z);
                    } else {
                        geometry = new THREE.BoxGeometry(sketch.width, sketch.height, height);
                        mesh = new THREE.Mesh(geometry, this.core.materials.column);
                        mesh.position.set(rectCenter.x, rectCenter.y, rectCenter.z + (height / 2));
                    }
                } else {
                    geometry = new THREE.BoxGeometry(sketch.width, sketch.height, height);
                    mesh = new THREE.Mesh(geometry, this.core.materials.extrusion);
                    const rectCenter = this.getRectangleCenter(sketch);
                    mesh.position.set(rectCenter.x, rectCenter.y, height / 2);
                }
                break;
        }

        if (!mesh) return null;

        mesh.castShadow = true;
        mesh.receiveShadow = true;

        return {
            id: `extrusion_${Date.now()}`,
            type: 'extrusion',
            object: mesh,
            sourceSketch: sketch.id,
            height: height
        };
    }

    createIBeamShape(dimensions) {
        const depth = dimensions.depth / 1000;
        const width = dimensions.width / 1000;
        const flangeThickness = dimensions.flangeThickness / 1000;
        const webThickness = dimensions.webThickness / 1000;

        const shape = new THREE.Shape();
        const halfWidth = width / 2;
        const halfWebThickness = webThickness / 2;

        shape.moveTo(-halfWidth, 0);
        shape.lineTo(halfWidth, 0);
        shape.lineTo(halfWidth, flangeThickness);
        shape.lineTo(halfWebThickness, flangeThickness);
        shape.lineTo(halfWebThickness, depth - flangeThickness);
        shape.lineTo(halfWidth, depth - flangeThickness);
        shape.lineTo(halfWidth, depth);
        shape.lineTo(-halfWidth, depth);
        shape.lineTo(-halfWidth, depth - flangeThickness);
        shape.lineTo(-halfWebThickness, depth - flangeThickness);
        shape.lineTo(-halfWebThickness, flangeThickness);
        shape.lineTo(-halfWidth, flangeThickness);
        shape.lineTo(-halfWidth, 0);

        return shape;
    }

    getRectangleCenter(sketch) {
        const points = sketch.points;
        let centerX = 0, centerY = 0, centerZ = 0;

        for (let i = 0; i < 4; i++) {
            centerX += points[i].x;
            centerY += points[i].y;
            centerZ += points[i].z;
        }

        return {
            x: centerX / 4,
            y: centerY / 4,
            z: centerZ / 4
        };
    }

    generateRidgeBeam() {
        // Ridge beam generation logic placeholder
        console.log('[StructureDesigner3D] Ridge beam generation not fully implemented in refactored version');
        this.core.showSuccess('Ridge beam generation placeholder');
    }

    generateRafterBeams() {
        if (!this.state.ridgeBeam) {
            this.core.showError('Please generate ridge beam first');
            return;
        }

        // Rafter beam generation logic placeholder
        console.log('[StructureDesigner3D] Rafter beam generation not fully implemented in refactored version');
        this.core.showSuccess('Rafter beam generation placeholder');
    }

    async generateRigidFrame() {
        try {
            console.log('[StructureDesigner3D] Starting rigid frame generation');

            const statusElement = document.getElementById('rigidFrameStatus');
            if (statusElement) {
                statusElement.textContent = 'Generating rigid frame structure...';
                statusElement.className = 'status-display status-warning';
            }

            const parameters = {
                building_length: parseFloat(document.getElementById('buildingLength').value) || 20,
                building_width: parseFloat(document.getElementById('buildingWidth').value) || 10,
                bay_spacing_x: parseFloat(document.getElementById('baySpacingX').value) || 5,
                bay_spacing_y: parseFloat(document.getElementById('baySpacingY').value) || 5,
                num_storeys: parseInt(document.getElementById('numStoreys').value) || 2,
                storey_height: parseFloat(document.getElementById('storeyHeight').value) || 3.5,
                structural_system_type: 'rigid_frame'
            };

            const response = await fetch('/api/generate-rigid-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(parameters)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.clearAllObjects();
                this.state.rigidFrameParams = parameters;

                const figureData = JSON.parse(result.figure);
                
                // Store member metadata for later use (if provided)
                this.memberMetadata = result.members || [];
                
                await this.loadRigidFrameVisualization(figureData, 0);

                if (statusElement) {
                    statusElement.textContent = `Rigid frame generated successfully`;
                    statusElement.className = 'status-display status-success';
                }

                // Enable slab auto-generation controls
                this.enableSlabAutoGeneration();

                this.core.autoFitCamera();
                console.log('[StructureDesigner3D] Rigid frame generated successfully');
                this.core.showSuccess('Rigid frame structure generated successfully');

            } else {
                throw new Error(result.error || 'Failed to generate rigid frame');
            }

        } catch (error) {
            console.error('[StructureDesigner3D] Error generating rigid frame:', error);
            this.core.showError(`Failed to generate rigid frame: ${error.message}`);

            if (statusElement) {
                statusElement.textContent = `Error: ${error.message}`;
                statusElement.className = 'status-display status-error';
            }
        }
    }

    async generatePortalFrame() {
        try {
            console.log('[StructureDesigner3D] Starting portal frame generation');

            // Read portal frame parameters from UI inputs
            const span = parseFloat(document.getElementById('portalSpan')?.value) || 20;
            const eaveHeight = parseFloat(document.getElementById('eaveHeight')?.value) || 6;
            const ridgeHeight = parseFloat(document.getElementById('ridgeHeight')?.value) || 9;
            const portalSpacing = parseFloat(document.getElementById('portalSpacing')?.value) || 6;
            const numPortals = parseInt(document.getElementById('numPortals')?.value) || 4;
            const purlinSpacing = parseFloat(document.getElementById('purlinSpacing')?.value) || 1.5;
            const girtSpacing = parseFloat(document.getElementById('girtSpacing')?.value) || 1.5;
            const endColumnOffset = parseFloat(document.getElementById('endColumnOffset')?.value) || 3.0;
            const addEndColumns = document.getElementById('addEndColumns')?.checked !== false;

            console.log('[DEBUG] Portal frame UI parameters:', { 
                span, eaveHeight, ridgeHeight, portalSpacing, numPortals, 
                purlinSpacing, girtSpacing, endColumnOffset, addEndColumns
            });

            const parameters = {
                span: span,
                eave_height: eaveHeight,
                ridge_height: ridgeHeight,
                portal_spacing: portalSpacing,
                num_portals: numPortals,
                purlin_spacing: purlinSpacing,
                girt_spacing: girtSpacing,
                end_column_y_offset: endColumnOffset,
                add_end_columns: addEndColumns
            };

            const response = await fetch('/api/generate-portal-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(parameters)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.clearAllObjects();
                
                // Store parameters with both naming conventions for compatibility
                this.state.rigidFrameParams = {
                    ...parameters,
                    structural_system_type: 'portal_frame',
                    // Add camelCase aliases for frontend compatibility
                    portalSpacing: parameters.portal_spacing,
                    numPortals: parameters.num_portals,
                    eaveHeight: parameters.eave_height,
                    ridgeHeight: parameters.ridge_height,
                    purlinSpacing: parameters.purlin_spacing,
                    girtSpacing: parameters.girt_spacing,
                    endColumnYOffset: parameters.end_column_y_offset,
                    addEndColumns: parameters.add_end_columns
                };
                
                console.log('[DEBUG] Portal frame generation successful, stored parameters:', this.state.rigidFrameParams);

                const figureData = JSON.parse(result.figure);
                
                // Store member metadata for later use
                this.memberMetadata = result.members || [];
                
                await this.loadRigidFrameVisualization(figureData, 0);

                // Enable slab auto-generation controls
                this.enableSlabAutoGeneration();

                this.core.autoFitCamera();
                console.log('[StructureDesigner3D] Portal frame generated successfully');
                this.core.showSuccess('Portal frame structure generated successfully');
            }

        } catch (error) {
            console.error('[StructureDesigner3D] Error generating portal frame:', error);
            this.core.showError(`Failed to generate portal frame: ${error.message}`);
        }
    }

    async generateHybridFrame() {
        try {
            console.log('[StructureDesigner3D] Starting hybrid frame generation');

            const statusElement = document.getElementById('hybridFrameStatus');
            if (statusElement) {
                statusElement.textContent = 'Generating hybrid frame structure...';
                statusElement.className = 'status-display status-warning';
            }

            const parameters = {
                building_length: parseFloat(document.getElementById('hybridBuildingLength')?.value) || 20,
                building_width: parseFloat(document.getElementById('hybridBuildingWidth')?.value) || 10,
                bay_spacing_x: parseFloat(document.getElementById('hybridBaySpacingX')?.value) || 5,
                bay_spacing_y: parseFloat(document.getElementById('hybridBaySpacingY')?.value) || 5,
                column_depth: parseFloat(document.getElementById('hybridColumnDepth')?.value) || 0.3,
                column_width: parseFloat(document.getElementById('hybridColumnWidth')?.value) || 0.2,
                column_flange_thickness: parseFloat(document.getElementById('hybridColumnFlangeThickness')?.value) || 0.015,
                column_web_thickness: parseFloat(document.getElementById('hybridColumnWebThickness')?.value) || 0.01,
                beam_depth: parseFloat(document.getElementById('hybridBeamDepth')?.value) || 0.4,
                beam_width: parseFloat(document.getElementById('hybridBeamWidth')?.value) || 0.15,
                beam_flange_thickness: parseFloat(document.getElementById('hybridBeamFlangeThickness')?.value) || 0.015,
                beam_web_thickness: parseFloat(document.getElementById('hybridBeamWebThickness')?.value) || 0.01,
                num_storeys: parseInt(document.getElementById('hybridNumStoreys')?.value) || 3,
                storey_height: parseFloat(document.getElementById('hybridStoreyHeight')?.value) || 3.5,
                core_width: parseFloat(document.getElementById('hybridCoreWidth')?.value) || 3.0,
                core_depth: parseFloat(document.getElementById('hybridCoreDepth')?.value) || 3.0,
                core_type: document.getElementById('hybridCoreType')?.value || 'hollow',
                core_wall_thickness: parseFloat(document.getElementById('hybridCoreWallThickness')?.value) || 0.4
            };

            const response = await fetch('/api/generate-hybrid-frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(parameters)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.clearAllObjects();
                this.state.rigidFrameParams = parameters;

                const figureData = JSON.parse(result.figure);
                
                // Store member metadata for later use (if provided)
                this.memberMetadata = result.members || [];
                
                await this.loadRigidFrameVisualization(figureData, 0);

                if (statusElement) {
                    statusElement.textContent = `Hybrid frame generated successfully - ${result.stats.total_columns} columns, ${result.stats.total_beams} beams`;
                    statusElement.className = 'status-display status-success';
                }

                // Enable slab auto-generation controls
                this.enableSlabAutoGeneration();

                this.core.autoFitCamera();
                console.log('[StructureDesigner3D] Hybrid frame generated successfully');
                this.core.showSuccess('Hybrid frame structure generated successfully');

            } else {
                throw new Error(result.error || 'Failed to generate hybrid frame');
            }

        } catch (error) {
            console.error('[StructureDesigner3D] Error generating hybrid frame:', error);
            this.core.showError(`Failed to generate hybrid frame: ${error.message}`);

            const statusElement = document.getElementById('hybridFrameStatus');
            if (statusElement) {
                statusElement.textContent = `Error: ${error.message}`;
                statusElement.className = 'status-display status-error';
            }
        }
    }

    async loadRigidFrameVisualization(figureData, zOffset = 0) {
        try {
            const traces = figureData.data;

            for (const trace of traces) {
                if (trace.type === 'mesh3d') {
                    const geometry = new THREE.BufferGeometry();

                    const vertices = [];
                    for (let i = 0; i < trace.x.length; i++) {
                        vertices.push(trace.x[i], trace.y[i], trace.z[i] + zOffset);
                    }
                    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

                    const indices = [];
                    for (let i = 0; i < trace.i.length; i++) {
                        indices.push(trace.i[i], trace.j[i], trace.k[i]);
                    }
                    geometry.setIndex(indices);
                    geometry.computeVertexNormals();

                    // Color code by member type
                    const colorMap = {
                        'column': 0x4682b4,     // steelblue
                        'beam': 0xf08080,       // lightcoral  
                        'rafter_beam': 0x90ee90, // lightgreen
                        'purlin': 0xdda0dd,     // plum
                        'girt': 0xf0e68c        // khaki
                    };
                    
                    const elementType = trace.name || 'beam';
                    const color = colorMap[elementType] || 0x4682b4;
                    
                    const material = new THREE.MeshLambertMaterial({ 
                        color: color,
                        opacity: trace.opacity || 0.9,
                        transparent: true
                    });

                    const mesh = new THREE.Mesh(geometry, material);
                    
                    // Get member metadata from customdata if available
                    let memberMeta = null;
                    if (trace.customdata && trace.customdata.length > 0) {
                        const memberId = trace.customdata[0];
                        if (this.memberMetadata && this.memberMetadata.length > 0) {
                            memberMeta = this.memberMetadata.find(m => m.id === memberId);
                        }
                    }
                    
                    // Fallback metadata if none found - create default metadata for rigid/hybrid frames
                    if (!memberMeta) {
                        memberMeta = this.generateDefaultMemberMetadata(elementType, trace, zOffset);
                    }
                    
                    mesh.userData = { 
                        type: 'structuralMember',  // Changed from 'rigidFrame' to enable individual selection
                        elementType: elementType,
                        selectable: true,
                        id: trace.customdata ? trace.customdata[0] : `member_${Date.now()}_${Math.random()}`,
                        metadata: memberMeta
                    };

                    this.core.scene.add(mesh);
                }
            }

        } catch (error) {
            console.error('[StructureDesigner3D] Error loading rigid frame visualization:', error);
            throw error;
        }
    }

    autoGenerateSlab() {
        if (!this.state.rigidFrameParams) {
            this.core.showError('Please generate a structural system first');
            return;
        }

        try {
            const xOffset = parseFloat(document.getElementById('slabXOffset')?.value) || 1.0;
            const yOffset = parseFloat(document.getElementById('slabYOffset')?.value) || 1.0;
            const slabThickness = parseFloat(document.getElementById('slabThickness')?.value) || 0.25;

            console.log('[DEBUG] Slab offset inputs:', { xOffset, yOffset, slabThickness });
            console.log('[DEBUG] Stored rigid frame params:', this.state.rigidFrameParams);

            let slabLength, slabWidth;
            const structuralSystemType = this.state.rigidFrameParams.structural_system_type || 'rigid_frame';

            if (structuralSystemType === 'portal_frame') {
                // For portal frames: extract parameters from the correct source
                const portalParams = this.state.rigidFrameParams;
                
                // Handle both snake_case (from backend) and camelCase (from frontend) parameter names
                const portalSpacing = portalParams.portal_spacing || portalParams.portalSpacing || 6;
                const numPortals = portalParams.num_portals || portalParams.numPortals || 4;
                const span = portalParams.span || 20;

                console.log('[DEBUG] Portal frame parameters (all keys):', Object.keys(portalParams));
                console.log('[DEBUG] Portal frame parameters extracted:', { 
                    portalSpacing, 
                    numPortals, 
                    span, 
                    xOffset, 
                    yOffset,
                    rawParams: portalParams
                });

                // Portal frame structure dimensions:
                // X direction: portal spacing * (num_portals - 1) = total length along portal line
                // Y direction: span = width of each portal frame
                const frameXDimension = portalSpacing * (numPortals - 1);
                const frameYDimension = span;

                // Calculate slab dimensions with offsets
                // Note: THREE.js BoxGeometry uses (width_X, height_Y, depth_Z)
                // So slabLength goes in X direction, slabWidth goes in Y direction
                slabLength = frameXDimension + (2 * xOffset);  // X direction
                slabWidth = frameYDimension + (2 * yOffset);   // Y direction

                console.log('[DEBUG] Portal frame slab calculation:', { 
                    portalSpacing,
                    numPortals,
                    span,
                    frameXDimension: `${portalSpacing} * (${numPortals} - 1) = ${frameXDimension}`,
                    frameYDimension: `span = ${frameYDimension}`,
                    xOffset,
                    yOffset,
                    finalSlabLength: `${frameXDimension} + 2*${xOffset} = ${slabLength}`,
                    finalSlabWidth: `${frameYDimension} + 2*${yOffset} = ${slabWidth}`,
                    expectedResult: 'Should be 20m x 22m for 4 portals, 6m spacing, 20m span'
                });
            } else {
                // For other frame types
                const frameLength = this.state.rigidFrameParams.building_length || 20;
                const frameWidth = this.state.rigidFrameParams.building_width || 10;

                slabLength = frameLength + (2 * xOffset);
                slabWidth = frameWidth + (2 * yOffset);
            }

            this.clearSlab();

            // Create slab geometry - THREE.BoxGeometry(width_X, height_Y, depth_Z)
            // slabLength is X dimension, slabWidth is Y dimension
            const slabGeometry = new THREE.BoxGeometry(slabLength, slabWidth, slabThickness);

            // Create slab material with better visibility
            const slabMaterial = new THREE.MeshLambertMaterial({ 
                color: 0xaaaaaa,
                transparent: true,
                opacity: 0.8,
                side: THREE.DoubleSide
            });

            const slabMesh = new THREE.Mesh(slabGeometry, slabMaterial);

            // Position slab correctly based on frame type
            if (structuralSystemType === 'portal_frame') {
                // For portal frames: position slab so it extends from -offset to frame_dimension + offset
                // Portal frame starts at origin, so slab center should account for the offset
                slabMesh.position.set(
                    (slabLength / 2),    // Center in X direction
                    (slabWidth / 2),     // Center in Y direction
                    slabThickness / 2    // Half thickness above ground
                );
            } else {
                // For other frame types: center and offset
                slabMesh.position.set(
                    slabLength / 2,
                    slabWidth / 2,
                    slabThickness / 2  // Positive Z to extrude upward
                );
            }

            slabMesh.castShadow = true;
            slabMesh.receiveShadow = true;

            // Add visible edges for better definition
            const edges = new THREE.EdgesGeometry(slabGeometry);
            const wireframe = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ 
                color: 0x333333, 
                linewidth: 2 
            }));
            slabMesh.add(wireframe);

            slabMesh.userData = { type: 'slab', category: 'structure', selectable: true };

            this.core.scene.add(slabMesh);

            const extrudedSlab = {
                id: `slab_extrusion_${Date.now()}`,
                type: 'extrusion',
                object: slabMesh,
                height: slabThickness
            };

            this.state.objects3D.push(extrudedSlab);

            // Store slab position - consistent for all frame types
            const slabPosition = { 
                x: slabLength / 2, 
                y: slabWidth / 2, 
                z: slabThickness / 2 
            };

            this.state.slab = {
                width: slabWidth,
                length: slabLength,
                position: slabPosition,
                thickness: slabThickness,
                extrudedObject: extrudedSlab,
                xOffset: xOffset,
                yOffset: yOffset
            };

            // Move the frame up to sit on the slab and apply offsets
            if (structuralSystemType === 'portal_frame') {
                // For portal frames: move up by slab thickness AND apply X/Y offsets
                // so the portal frame is positioned correctly relative to the slab
                this.repositionRigidFrameForSlab(slabThickness, xOffset, yOffset);
                console.log(`[DEBUG] Portal frame repositioned by offsets: x=${xOffset}, y=${yOffset}, z=${slabThickness}`);
            } else {
                // For other frame types: offset as before
                this.repositionRigidFrameForSlab(slabThickness, xOffset, yOffset);
            }

            this.core.autoFitCamera();
            this.updateUI();

            // Update the UI input fields to show the calculated dimensions for reference
            const slabLengthInput = document.getElementById('slabLength');
            const slabWidthInput = document.getElementById('slabWidth');
            if (slabLengthInput) slabLengthInput.value = slabLength.toFixed(1);
            if (slabWidthInput) slabWidthInput.value = slabWidth.toFixed(1);

            console.log(`[StructureDesigner3D] Auto-generated slab: ${slabLength}m x ${slabWidth}m x ${slabThickness}m`);
            this.core.showSuccess(`Slab auto-generated successfully (${slabLength.toFixed(1)}m x ${slabWidth.toFixed(1)}m x ${slabThickness}m)`);

        } catch (error) {
            console.error('[StructureDesigner3D] Error auto-generating slab:', error);
            this.core.showError(`Failed to auto-generate slab: ${error.message}`);
        }
    }

    repositionRigidFrameForSlab(zOffset, xOffset, yOffset) {
        const objectsToMove = [];
        this.core.scene.traverse((child) => {
            if (child.userData && (child.userData.type === 'rigidFrame' || child.userData.type === 'structuralMember')) {
                objectsToMove.push(child);
            }
        });

        objectsToMove.forEach(obj => {
            obj.position.z += zOffset;
            obj.position.x += xOffset;
            obj.position.y += yOffset;
        });

        console.log(`[StructureDesigner3D] Repositioned ${objectsToMove.length} structural objects by (${xOffset}, ${yOffset}, ${zOffset})`);
    }

    enableSlabAutoGeneration() {
        // Enable the auto-generate slab button
        const autoGenerateSlabBtn = document.getElementById('autoGenerateSlabBtn');
        if (autoGenerateSlabBtn) {
            autoGenerateSlabBtn.disabled = false;
            autoGenerateSlabBtn.style.opacity = '1';
            autoGenerateSlabBtn.style.cursor = 'pointer';
        }

        // Enable the slab parameter input fields
        const slabXOffset = document.getElementById('slabXOffset');
        const slabYOffset = document.getElementById('slabYOffset');
        const slabThickness = document.getElementById('slabThickness');

        if (slabXOffset) {
            slabXOffset.disabled = false;
            slabXOffset.style.opacity = '1';
        }
        if (slabYOffset) {
            slabYOffset.disabled = false;
            slabYOffset.style.opacity = '1';
        }
        if (slabThickness) {
            slabThickness.disabled = false;
            slabThickness.style.opacity = '1';
        }

        // Update status message
        const slabGenerationStatus = document.getElementById('slabGenerationStatus');
        if (slabGenerationStatus) {
            slabGenerationStatus.textContent = 'Ready to auto-generate slab';
            slabGenerationStatus.className = 'status-display status-success';
        }

        console.log('[StructureDesigner3D] Slab auto-generation controls enabled');
    }

    async loadBeamSpecifications() {
        try {
            const response = await fetch('/api/beam-specifications', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                this.populateBeamDropdowns(result.specifications);
                console.log(`[StructureDesigner3D] Loaded ${result.specifications.length} beam specifications`);
            }

        } catch (error) {
            console.error('[StructureDesigner3D] Error loading beam specifications:', error);
        }
    }

    populateBeamDropdowns(specifications) {
        const columnBeamSelect = document.getElementById('columnBeamSelect');
        const frameBeamSelect = document.getElementById('frameBeamSelect');

        if (!columnBeamSelect || !frameBeamSelect) return;

        columnBeamSelect.innerHTML = '<option value="">Use default dimensions</option>';
        frameBeamSelect.innerHTML = '<option value="">Use default dimensions</option>';

        specifications.forEach(spec => {
            const optionText = `${spec.designation} (${spec.material}, ${spec.grade_mpa}MPa, ${spec.section_depth_mm}mm depth)`;

            const columnOption = document.createElement('option');
            columnOption.value = spec.id;
            columnOption.textContent = optionText;
            columnBeamSelect.appendChild(columnOption);

            const frameOption = document.createElement('option');
            frameOption.value = spec.id;
            frameOption.textContent = optionText;
            frameBeamSelect.appendChild(frameOption);
        });
    }

    updateStructuralSystemParameters(systemType) {
        const rigidFrameParams = document.getElementById('rigidFrameParameters');
        const hybridFrameParams = document.getElementById('hybridFrameParameters'); 
        const portalFrameParams = document.getElementById('portalFrameParameters');

        if (rigidFrameParams) rigidFrameParams.style.display = 'none';
        if (hybridFrameParams) hybridFrameParams.style.display = 'none';
        if (portalFrameParams) portalFrameParams.style.display = 'none';

        switch (systemType) {
            case 'rigid_frame':
                if (rigidFrameParams) rigidFrameParams.style.display = 'block';
                break;
            case 'hybrid_core_frame':
                if (hybridFrameParams) hybridFrameParams.style.display = 'block';
                break;
            case 'portal_frame':
                if (portalFrameParams) portalFrameParams.style.display = 'block';
                break;
        }
    }

    updateColumnLayoutParameter(paramId, value) {
        this.state.columnLayout[paramId] = value;

        if (this.state.columns.length > 0) {
            this.generateColumnLayout();
        }
    }

    clearLayout() {
        this.clearSlab();
        this.clearColumns();
        this.updateUI();
        console.log('[StructureDesigner3D] Layout cleared');
    }

    clearSlab() {
        if (this.state.slab) {
            if (this.state.slab.extrudedObject) {
                this.core.scene.remove(this.state.slab.extrudedObject.object);
                this.state.objects3D = this.state.objects3D.filter(obj => obj.id !== this.state.slab.extrudedObject.id);
            }
            this.state.slab = null;
        }
    }

    clearColumns() {
        this.state.columns.forEach(column => {
            if (column.sketch) {
                this.core.scene.remove(column.sketch.object);
            }
            if (column.extrudedObject) {
                this.core.scene.remove(column.extrudedObject.object);
                this.state.objects3D = this.state.objects3D.filter(obj => obj.id !== column.extrudedObject.id);
            }
        });
        this.state.columns = [];
    }

    clearExtrudedColumns() {
        this.state.columns.forEach(column => {
            if (column.extrudedObject) {
                this.core.scene.remove(column.extrudedObject.object);
                this.state.objects3D = this.state.objects3D.filter(obj => obj.id !== column.extrudedObject.id);
                column.extrudedObject = null;
            }
        });
        this.updateUI();
    }

    clearRidgeBeam() {
        if (this.state.ridgeBeam) {
            this.core.scene.remove(this.state.ridgeBeam.object);
            this.state.ridgeBeam = null;
        }
    }

    clearRafterBeams() {
        if (this.state.rafterBeams && this.state.rafterBeams.length > 0) {
            this.state.rafterBeams.forEach(rafterBeam => {
                if (rafterBeam.object) {
                    this.core.scene.remove(rafterBeam.object);
                }
            });
            this.state.rafterBeams = [];
        }
    }

    clearAllObjects() {
        const objectsToRemove = [];
        this.core.scene.traverse((child) => {
            if (child.userData && (child.userData.type === 'rigidFrame' || child.userData.type === 'structuralMember')) {
                objectsToRemove.push(child);
            }
        });

        objectsToRemove.forEach(obj => {
            this.core.scene.remove(obj);
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) obj.material.dispose();
        });

        this.clearLayout();
        this.clearRidgeBeam();
        this.clearRafterBeams();

        // Reset rigid frame parameters and disable slab controls
        this.state.rigidFrameParams = null;
        this.disableSlabAutoGeneration();

        console.log('[StructureDesigner3D] All objects cleared');
    }

    disableSlabAutoGeneration() {
        // Disable the auto-generate slab button
        const autoGenerateSlabBtn = document.getElementById('autoGenerateSlabBtn');
        if (autoGenerateSlabBtn) {
            autoGenerateSlabBtn.disabled = true;
            autoGenerateSlabBtn.style.opacity = '0.5';
            autoGenerateSlabBtn.style.cursor = 'not-allowed';
        }

        // Disable the slab parameter input fields
        const slabXOffset = document.getElementById('slabXOffset');
        const slabYOffset = document.getElementById('slabYOffset');
        const slabThickness = document.getElementById('slabThickness');

        if (slabXOffset) {
            slabXOffset.disabled = true;
            slabXOffset.style.opacity = '0.5';
        }
        if (slabYOffset) {
            slabYOffset.disabled = true;
            slabYOffset.style.opacity = '0.5';
        }
        if (slabThickness) {
            slabThickness.disabled = true;
            slabThickness.style.opacity = '0.5';
        }

        // Update status message
        const slabGenerationStatus = document.getElementById('slabGenerationStatus');
        if (slabGenerationStatus) {
            slabGenerationStatus.textContent = 'Generate structure first';
            slabGenerationStatus.className = 'status-display';
        }

        console.log('[StructureDesigner3D] Slab auto-generation controls disabled');
    }

    createCompleteStructure() {
        this.drawSlab();

        setTimeout(() => {
            this.generateColumnLayout();

            setTimeout(() => {
                this.extrudeAllColumns();

                setTimeout(() => {
                    this.core.autoFitCamera();
                    this.core.showSuccess('Complete structure created and camera positioned');
                }, 200);
            }, 500);
        }, 100);
    }

    generateDefaultMemberMetadata(elementType, trace, zOffset = 0) {
        /**
         * Generate default member metadata for rigid and hybrid frames
         * when no specific metadata is available
         */
        const structuralSystemType = this.state.rigidFrameParams?.structural_system_type || 'rigid_frame';
        
        // Calculate approximate dimensions based on geometry
        let length = 6.0; // Default length
        let dimensions = { width: 0.3, depth: 0.6 }; // Default dimensions
        
        if (trace.x && trace.y && trace.z) {
            // Calculate actual length from geometry
            const xRange = Math.max(...trace.x) - Math.min(...trace.x);
            const yRange = Math.max(...trace.y) - Math.min(...trace.y);
            const zRange = Math.max(...trace.z) - Math.min(...trace.z);
            length = Math.sqrt(xRange * xRange + yRange * yRange + zRange * zRange);
            
            // Use rigid frame parameters for dimensions if available
            if (this.state.rigidFrameParams) {
                if (elementType === 'column') {
                    dimensions = {
                        width: this.state.rigidFrameParams.column_width || 0.3,
                        depth: this.state.rigidFrameParams.column_depth || 0.6
                    };
                } else if (elementType === 'beam') {
                    dimensions = {
                        width: this.state.rigidFrameParams.beam_width || 0.3,
                        depth: this.state.rigidFrameParams.beam_depth || 0.6
                    };
                }
            }
        }
        
        // Generate start and end points
        const startPoint = trace.x && trace.y && trace.z ? 
            [trace.x[0] || 0, trace.y[0] || 0, (trace.z[0] || 0) + zOffset] : 
            [0, 0, zOffset];
        
        const endPoint = trace.x && trace.y && trace.z ? 
            [trace.x[trace.x.length - 1] || length, trace.y[trace.y.length - 1] || 0, (trace.z[trace.z.length - 1] || 0) + zOffset] : 
            [length, 0, zOffset];
        
        // Calculate orientation
        const dx = endPoint[0] - startPoint[0];
        const dy = endPoint[1] - startPoint[1];
        const dz = endPoint[2] - startPoint[2];
        
        const horizontalAngle = Math.atan2(dy, dx) * 180 / Math.PI;
        const horizontalLength = Math.sqrt(dx * dx + dy * dy);
        const verticalAngle = horizontalLength > 0 ? Math.atan2(dz, horizontalLength) * 180 / Math.PI : 0;
        
        // Generate member designation
        const memberCount = this.core.scene.children.filter(child => 
            child.userData?.type === 'structuralMember' && 
            child.userData?.elementType === elementType
        ).length + 1;
        
        const designation = `${this.formatMemberType(elementType)} ${memberCount}`;
        
        return {
            id: `${elementType}_${memberCount}_${Date.now()}`,
            type: elementType,
            designation: designation,
            cross_section: 'I-beam',
            length: length,
            orientation: {
                horizontal_angle: horizontalAngle,
                vertical_angle: verticalAngle
            },
            dimensions: dimensions,
            start_point: startPoint,
            end_point: endPoint,
            structural_system: structuralSystemType
        };
    }

    formatMemberType(type) {
        const typeMap = {
            'column': 'Column',
            'beam': 'Beam',
            'rafter_beam': 'Rafter Beam'
        };
        return typeMap[type] || type;
    }

    updateUI() {
        const layoutStatus = document.getElementById('layoutStatus');
        if (!layoutStatus) return;

        if (this.state.slab && this.state.columns.length > 0) {
            const slabInfo = `${this.state.slab.width}m x ${this.state.slab.length}m`;
            const extrudedColumns = this.state.columns.filter(c => c.extrudedObject).length;
            const crossSectionType = this.state.columnLayout.crossSectionType;
            const crossSectionInfo = crossSectionType === 'i-beam' ? 'I-beam' : 'rectangular';

            const heights = this.state.columns.map(c => c.pitchedHeight || 3.0);
            const minHeight = Math.min(...heights);
            const maxHeight = Math.max(...heights);
            const heightRange = minHeight === maxHeight ? `${minHeight.toFixed(1)}m` : `${minHeight.toFixed(1)}-${maxHeight.toFixed(1)}m`;

            const columnInfo = `${this.state.columns.length} ${crossSectionInfo} columns (${extrudedColumns} extruded, heights: ${heightRange})`;
            layoutStatus.textContent = `Slab: ${slabInfo}, ${columnInfo}`;
            layoutStatus.className = 'status-display status-success';
        } else if (this.state.slab) {
            const slabInfo = `${this.state.slab.width}m x ${this.state.slab.length}m`;
            layoutStatus.textContent = `Slab: ${slabInfo} (no columns)`;
            layoutStatus.className = 'status-display status-warning';
        } else {
            layoutStatus.textContent = 'No slab defined';
            layoutStatus.className = 'status-display';
        }
    }
}

// Export for use by other modules
window.StructureDesignerStructures = StructureDesignerStructures;