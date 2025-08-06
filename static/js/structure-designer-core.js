
/**
 * Structure Designer Core - 3D Engine and Basic Functionality
 * Handles Three.js initialization, scene management, camera controls, and UI
 */

class StructureDesigner3DCore {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.raycaster = null;
        this.mouse = null;

        // State management
        this.state = {
            currentView: '3D',
            currentTool: 'select',
            gridSnap: true,
            workingPlane: 'XY',
            selectedObject: null,
            selectedMember: null
        };

        // Grid and axes
        this.gridHelper = null;
        this.axesHelper = null;
        this.workingPlaneHelper = null;

        // Materials - initialize after Three.js is loaded
        this.materials = null;

        // Initialization tracking
        this.initializationAttempts = 0;
        this.maxInitializationAttempts = 50;
    }

    initializeMaterials() {
        this.materials = {
            sketch: new THREE.LineBasicMaterial({ color: 0x00ff00, linewidth: 2 }),
            selected: new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 3 }),
            extrusion: new THREE.MeshLambertMaterial({ color: 0x8B4513, transparent: true, opacity: 0.8 }),
            grid: new THREE.LineBasicMaterial({ color: 0x444444, transparent: true, opacity: 0.5 }),
            workingPlane: new THREE.MeshBasicMaterial({ 
                color: 0x4a6cf7, 
                transparent: true, 
                opacity: 0.2,
                side: THREE.DoubleSide
            }),
            slab: new THREE.MeshLambertMaterial({ 
                color: 0x888888, 
                transparent: true, 
                opacity: 0.8,
                side: THREE.DoubleSide
            }),
            column: new THREE.MeshLambertMaterial({ color: 0xff8c00, transparent: true, opacity: 0.8 }),
            ridgeBeam: new THREE.MeshLambertMaterial({ color: 0x00ffff, transparent: true, opacity: 0.8 }),
            rafterBeam: new THREE.MeshLambertMaterial({ color: 0xff69b4, transparent: true, opacity: 0.8 })
        };
    }

    initialize() {
        try {
            console.log('[StructureDesigner3D] Starting initialization attempt', this.initializationAttempts + 1);

            const container = document.getElementById('designCanvas');
            if (!container) {
                console.error('[StructureDesigner3D] Design canvas container not found');
                if (this.initializationAttempts < this.maxInitializationAttempts) {
                    this.initializationAttempts++;
                    setTimeout(() => this.initialize(), 100);
                    return;
                }
                throw new Error('Design canvas container not found after maximum attempts');
            }

            if (typeof THREE === 'undefined') {
                console.log('[StructureDesigner3D] Three.js not yet loaded, retrying...');
                if (this.initializationAttempts < this.maxInitializationAttempts) {
                    this.initializationAttempts++;
                    setTimeout(() => this.initialize(), 200);
                    return;
                }
                throw new Error('Three.js library not loaded after maximum attempts');
            }

            if (typeof THREE.OrbitControls === 'undefined') {
                console.log('[StructureDesigner3D] OrbitControls not yet loaded, retrying...');
                if (typeof window.THREE !== 'undefined' && window.THREE.OrbitControls) {
                    THREE.OrbitControls = window.THREE.OrbitControls;
                } else if (this.initializationAttempts < this.maxInitializationAttempts) {
                    this.initializationAttempts++;
                    setTimeout(() => this.initialize(), 200);
                    return;
                } else {
                    console.warn('[StructureDesigner3D] OrbitControls not available, will use basic camera controls');
                }
            }

            this.initializeMaterials();
            this.initializeThreeJS();
            this.setupScene();
            this.setupEventListeners();
            this.updateUI();
            this.animate();

            console.log('[StructureDesigner3D] ✅ Initialization complete successfully');
            this.showSuccess('3D Designer initialized successfully');

            if (this.renderer && this.scene && this.camera) {
                this.renderer.render(this.scene, this.camera);
            }

        } catch (error) {
            console.error('[StructureDesigner3D] ❌ Initialization failed:', error);
            this.showError(`Failed to initialize 3D Designer: ${error.message}`);
            
            const container = document.getElementById('designCanvas');
            if (container) {
                container.innerHTML = `
                    <div style="color: white; padding: 20px; text-align: center;">
                        <h3>3D Designer Failed to Load</h3>
                        <p>Error: ${error.message}</p>
                        <p>Check the console for more details.</p>
                        <button onclick="window.structureDesigner = new StructureDesigner3D(); window.structureDesigner.initialize();" 
                                style="padding: 10px 20px; margin-top: 10px;">
                            Retry Initialization
                        </button>
                    </div>
                `;
            }
        }
    }

    initializeThreeJS() {
        const container = document.getElementById('designCanvas');

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a1a);

        // Camera - Orthographic for true isometric view
        const aspect = container.clientWidth / container.clientHeight;
        const frustumSize = 20;
        this.camera = new THREE.OrthographicCamera(
            -frustumSize * aspect / 2, 
            frustumSize * aspect / 2,
            frustumSize / 2, 
            -frustumSize / 2,
            0.1, 
            1000
        );

        this.camera.position.set(10, -10, 10);
        this.camera.up.set(0, 0, 1);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);

        // Controls
        if (typeof THREE.OrbitControls !== 'undefined') {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.enableRotate = true;
            this.controls.enableZoom = true;
            this.controls.enablePan = true;
            this.controls.minZoom = 0.5;
            this.controls.maxZoom = 5;
        } else {
            this.controls = {
                enabled: true,
                enableDamping: false,
                update: () => {}
            };
        }

        // Raycaster for mouse interactions
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();

        window.addEventListener('resize', () => this.onWindowResize());
    }

    setupScene() {
        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);

        this.createGrid();
        this.createAxes();
        this.createWorkingPlane();
    }

    createGrid() {
        if (this.gridHelper) {
            this.scene.remove(this.gridHelper);
        }

        this.gridHelper = new THREE.GridHelper(20, 20, 0x666666, 0x333333);
        this.gridHelper.rotation.x = Math.PI / 2;
        this.scene.add(this.gridHelper);
    }

    createAxes() {
        if (this.axesHelper) {
            this.scene.remove(this.axesHelper);
        }

        this.axesHelper = new THREE.AxesHelper(5);
        this.scene.add(this.axesHelper);
        this.createAxisLabels();
    }

    createAxisLabels() {
        const createLabel = (text, position, color) => {
            const geometry = new THREE.SphereGeometry(0.1);
            const material = new THREE.MeshBasicMaterial({ color: color });
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.copy(position);
            sphere.userData = { label: text };
            this.scene.add(sphere);
        };

        createLabel('X', new THREE.Vector3(5.5, 0, 0), 0xff0000);
        createLabel('Y', new THREE.Vector3(0, 5.5, 0), 0x00ff00);
        createLabel('Z', new THREE.Vector3(0, 0, 5.5), 0x0000ff);
    }

    createWorkingPlane() {
        if (this.workingPlaneHelper) {
            this.scene.remove(this.workingPlaneHelper);
        }

        const geometry = new THREE.PlaneGeometry(20, 20);
        this.workingPlaneHelper = new THREE.Mesh(geometry, this.materials.workingPlane);
        this.updateWorkingPlane();
        this.scene.add(this.workingPlaneHelper);
    }

    updateWorkingPlane() {
        if (!this.workingPlaneHelper) return;

        switch (this.state.workingPlane) {
            case 'XY':
                this.workingPlaneHelper.rotation.set(0, 0, 0);
                this.workingPlaneHelper.position.set(0, 0, 0);
                break;
            case 'XZ':
                this.workingPlaneHelper.rotation.set(-Math.PI / 2, 0, 0);
                this.workingPlaneHelper.position.set(0, 0, 0);
                break;
            case 'YZ':
                this.workingPlaneHelper.rotation.set(0, Math.PI / 2, 0);
                this.workingPlaneHelper.position.set(0, 0, 0);
                break;
        }
    }

    setupEventListeners() {
        // View controls
        const view3DBtn = document.getElementById('view3DBtn');
        const viewTopBtn = document.getElementById('viewTopBtn');
        const viewFrontBtn = document.getElementById('viewFrontBtn');
        const viewSideBtn = document.getElementById('viewSideBtn');

        if (view3DBtn) view3DBtn.addEventListener('click', () => this.setView('3D'));
        if (viewTopBtn) viewTopBtn.addEventListener('click', () => this.setView('XY'));
        if (viewFrontBtn) viewFrontBtn.addEventListener('click', () => this.setView('XZ'));
        if (viewSideBtn) viewSideBtn.addEventListener('click', () => this.setView('YZ'));

        // Grid snap toggle
        const gridSnapToggle = document.getElementById('gridSnapToggle');
        if (gridSnapToggle) {
            gridSnapToggle.addEventListener('change', (e) => {
                this.state.gridSnap = e.target.checked;
                this.updateUI();
            });
        }

        // Tool selection
        ['toolSelect', 'toolLine', 'toolRect', 'toolCircle', 'toolPolygon', 'toolMove'].forEach(toolId => {
            const element = document.getElementById(toolId);
            if (element) {
                element.addEventListener('click', () => {
                    const tool = toolId.replace('tool', '').toLowerCase();
                    this.setTool(tool);
                });
            }
        });

        // Mouse events for selection and interaction
        if (this.renderer && this.renderer.domElement) {
            this.renderer.domElement.addEventListener('mousedown', (e) => this.onMouseDown(e));
            this.renderer.domElement.addEventListener('mousemove', (e) => this.onMouseMove(e));
            this.renderer.domElement.addEventListener('mouseup', (e) => this.onMouseUp(e));
            this.renderer.domElement.addEventListener('click', (e) => this.onClick(e));
            
            this.renderer.domElement.style.pointerEvents = 'auto';
        }

        document.addEventListener('keydown', (e) => this.onKeyDown(e));

        // Auto-fit camera button
        const autoFitCameraBtn = document.getElementById('autoFitCameraBtn');
        if (autoFitCameraBtn) {
            autoFitCameraBtn.addEventListener('click', () => {
                this.autoFitCamera();
                this.showSuccess('Camera positioned to fit all objects');
            });
        }

        // Member details close button
        const closeMemberDetails = document.getElementById('closeMemberDetails');
        if (closeMemberDetails) {
            closeMemberDetails.addEventListener('click', () => {
                this.setSelectedMember(null);
            });
        }

        // Analyze member button
        const analyzeMemberBtn = document.getElementById('analyzeMemberBtn');
        if (analyzeMemberBtn) {
            analyzeMemberBtn.addEventListener('click', () => {
                if (this.state.selectedMember) {
                    this.openStructuralAnalyser(this.state.selectedMember);
                }
            });
        }
    }

    setView(viewMode) {
        this.state.currentView = viewMode;

        document.querySelectorAll('.view-btn').forEach(btn => btn.classList.remove('active'));

        if (viewMode === '3D') {
            const view3DBtn = document.getElementById('view3DBtn');
            if (view3DBtn) view3DBtn.classList.add('active');

            this.camera.position.set(10, 10, 10);
            this.camera.lookAt(0, 0, 0);
            this.controls.enabled = true;
            this.workingPlaneHelper.visible = false;
        } else {
            this.state.workingPlane = viewMode;
            this.updateWorkingPlane();
            this.workingPlaneHelper.visible = true;
            this.controls.enabled = false;

            switch (viewMode) {
                case 'XY':
                    const viewTopBtn = document.getElementById('viewTopBtn');
                    if (viewTopBtn) viewTopBtn.classList.add('active');
                    this.camera.position.set(0, 0, 20);
                    this.camera.lookAt(0, 0, 0);
                    break;
                case 'XZ':
                    const viewFrontBtn = document.getElementById('viewFrontBtn');
                    if (viewFrontBtn) viewFrontBtn.classList.add('active');
                    this.camera.position.set(0, -20, 0);
                    this.camera.lookAt(0, 0, 0);
                    break;
                case 'YZ':
                    const viewSideBtn = document.getElementById('viewSideBtn');
                    if (viewSideBtn) viewSideBtn.classList.add('active');
                    this.camera.position.set(20, 0, 0);
                    this.camera.lookAt(0, 0, 0);
                    break;
            }
        }

        this.updateUI();
        console.log('[StructureDesigner3D] View changed to:', viewMode);
    }

    setTool(tool) {
        this.state.currentTool = tool;

        document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
        const toolBtn = document.getElementById(`tool${tool.charAt(0).toUpperCase() + tool.slice(1)}`);
        if (toolBtn) toolBtn.classList.add('active');

        this.updateUI();
        console.log('[StructureDesigner3D] Tool changed to:', tool);
    }

    updateUI() {
        const viewStatus = document.getElementById('viewStatus');
        if (viewStatus) {
            viewStatus.textContent = `${this.state.currentView} View - Grid Snap: ${this.state.gridSnap ? 'On' : 'Off'}`;
        }

        const toolStatus = document.getElementById('toolStatus');
        if (toolStatus) {
            toolStatus.textContent = `${this.state.currentTool.charAt(0).toUpperCase() + this.state.currentTool.slice(1)} tool active`;
        }

        this.updateSelectedMemberInfo();
    }

    updateSelectedMemberInfo() {
        const selectedMemberInfo = document.getElementById('selectedMemberInfo');
        if (!selectedMemberInfo) return;

        if (this.state.selectedMember) {
            const member = this.state.selectedMember;
            let infoText = `Selected: ${member.type.replace('_', ' ')} (${member.category})`;

            selectedMemberInfo.innerHTML = `
                <div>${infoText}</div>
                <button id="structuralAnalyserBtn" class="action-button" style="margin-top: 8px; padding: 8px 16px; font-size: 12px;">
                    🔧 Structural Analyser
                </button>
            `;
            selectedMemberInfo.className = 'status-display status-success';
            
            setTimeout(() => {
                const analyserBtn = document.getElementById('structuralAnalyserBtn');
                if (analyserBtn) {
                    analyserBtn.addEventListener('click', () => {
                        this.openStructuralAnalyser(member);
                    });
                }
            }, 10);
        } else {
            selectedMemberInfo.textContent = 'No member selected - click on a 3D object to select';
            selectedMemberInfo.className = 'status-display';
        }
    }

    onMouseDown(event) {
        event.preventDefault();
        this.updateMousePosition(event);

        if (this.state.currentTool === 'select') {
            this.selectObjectAt();
            return;
        }
    }

    onMouseMove(event) {
        this.updateMousePosition(event);
        this.updateViewportInfo();
    }

    onMouseUp(event) {
        // Handle mouse up events
    }

    onClick(event) {
        if (this.state.currentTool === 'select') {
            this.updateMousePosition(event);
            this.selectObjectAt();
        }
    }

    onKeyDown(event) {
        switch (event.key) {
            case 'Escape':
                // Cancel current operation
                break;
            case 'Delete':
                this.deleteSelected();
                break;
            case 'g':
                if (event.ctrlKey) {
                    event.preventDefault();
                    document.getElementById('gridSnapToggle').click();
                }
                break;
        }
    }

    updateMousePosition(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    }

    selectObjectAt() {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        
        const selectableObjects = [];
        this.scene.traverse((child) => {
            if (child.userData && (child.userData.type === 'structuralMember' || child.userData.type === 'rigidFrame' || child.userData.selectable)) {
                selectableObjects.push(child);
            }
        });

        const intersects = this.raycaster.intersectObjects(selectableObjects, true);
        
        if (intersects.length > 0) {
            const intersectedObject = intersects[0].object;
            const userData = intersectedObject.userData;
            
            const selectedData = {
                type: userData.elementType || userData.type || 'selected_object',
                id: userData.id || `object_${intersectedObject.uuid}`,
                category: userData.category || 'structural',
                object: intersectedObject,
                meshObject: intersectedObject,
                metadata: userData.metadata || null
            };
            
            this.setSelectedMember(selectedData);
        } else {
            this.setSelectedMember(null);
        }
    }

    setSelectedMember(memberData) {
        this.clearMemberSelection();
        this.state.selectedMember = memberData;
        
        if (memberData && memberData.meshObject) {
            this.highlightMember(memberData.meshObject);
            this.showMemberDetails(memberData);
        } else {
            this.hideMemberDetails();
        }
        
        this.updateUI();
    }

    clearMemberSelection() {
        if (this.state.selectedMember && this.state.selectedMember.meshObject) {
            this.unhighlightMember(this.state.selectedMember.meshObject);
        }
    }

    highlightMember(meshObject) {
        if (!meshObject.userData.originalMaterial) {
            meshObject.userData.originalMaterial = meshObject.material;
        }
        
        const highlightMaterial = new THREE.MeshLambertMaterial({
            color: 0xffff00,
            transparent: true,
            opacity: 0.8
        });
        
        meshObject.material = highlightMaterial;
    }

    unhighlightMember(meshObject) {
        if (meshObject.userData.originalMaterial) {
            meshObject.material = meshObject.userData.originalMaterial;
        }
    }

    deleteSelected() {
        if (!this.state.selectedMember) return;

        const meshObject = this.state.selectedMember.meshObject;
        if (meshObject) {
            this.scene.remove(meshObject);
            if (meshObject.geometry) meshObject.geometry.dispose();
            if (meshObject.material) meshObject.material.dispose();
        }

        this.state.selectedMember = null;
        this.updateUI();
        console.log('[StructureDesigner3D] Selected object deleted');
    }

    updateViewportInfo() {
        const intersect = this.getIntersectionWithWorkingPlane();
        let coords = '(0, 0, 0)';

        if (intersect) {
            const point = this.snapToGrid(intersect.point);
            coords = `(${point.x.toFixed(1)}, ${point.y.toFixed(1)}, ${point.z.toFixed(1)})`;
        }

        const viewportInfo = document.getElementById('viewportInfo');
        if (viewportInfo) {
            viewportInfo.textContent = `Coordinates: ${coords} | View: ${this.state.currentView} | Tool: ${this.state.currentTool}`;
        }
    }

    getIntersectionWithWorkingPlane() {
        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObject(this.workingPlaneHelper);
        return intersects.length > 0 ? intersects[0] : null;
    }

    snapToGrid(point) {
        if (!this.state.gridSnap) return point;

        const gridSize = 1;
        return new THREE.Vector3(
            Math.round(point.x / gridSize) * gridSize,
            Math.round(point.y / gridSize) * gridSize,
            Math.round(point.z / gridSize) * gridSize
        );
    }

    onWindowResize() {
        const container = document.getElementById('designCanvas');
        if (!container || !this.camera || !this.renderer) return;

        const aspect = container.clientWidth / container.clientHeight;
        const frustumSize = 20;

        this.camera.left = -frustumSize * aspect / 2;
        this.camera.right = frustumSize * aspect / 2;
        this.camera.top = frustumSize / 2;
        this.camera.bottom = -frustumSize / 2;

        this.camera.updateProjectionMatrix();
        this.renderer.setSize(container.clientWidth, container.clientHeight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        if (this.controls) {
            this.controls.update();
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    autoFitCamera() {
        if (!this.camera || !this.controls) return;

        const bounds = this.calculateSceneBounds();
        if (!bounds || bounds.isEmpty()) {
            console.log('[StructureDesigner3D] No objects to fit camera to');
            return;
        }

        const size = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);

        if (this.camera.isOrthographicCamera) {
            const paddingFactor = 1.4;
            const targetSize = maxDim * paddingFactor;
            const aspect = this.camera.right / this.camera.top;
            const halfHeight = targetSize / 2;
            const halfWidth = halfHeight * aspect;

            this.camera.left = -halfWidth;
            this.camera.right = halfWidth;
            this.camera.top = halfHeight;
            this.camera.bottom = -halfHeight;
            this.camera.updateProjectionMatrix();
        }

        if (this.state.currentView === '3D') {
            const distance = maxDim * 1.5;
            const cameraPosition = new THREE.Vector3(
                center.x + distance * 0.7,
                center.y - distance * 0.7,
                center.z + distance * 0.7
            );

            this.camera.position.copy(cameraPosition);
            this.camera.lookAt(center);

            if (this.controls && this.controls.target) {
                this.controls.target.copy(center);
                this.controls.update();
            }
        }

        if (this.renderer) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    calculateSceneBounds() {
        const box = new THREE.Box3();
        const objects = [];

        this.scene.traverse((child) => {
            if (child.isMesh && child.userData.type !== 'grid' && child.userData.type !== 'axes') {
                objects.push(child);
            }
        });

        if (objects.length === 0) {
            return null;
        }

        objects.forEach(object => {
            const objectBox = new THREE.Box3().setFromObject(object);
            box.union(objectBox);
        });

        return box;
    }

    openStructuralAnalyser(member) {
        const memberData = this.extractMemberAnalysisData(member);
        
        const params = new URLSearchParams({
            type: memberData.type,
            id: memberData.id,
            category: memberData.category,
            length: memberData.length,
            storey: memberData.storey,
            totalStoreys: memberData.totalStoreys,
            tributaryWidth: memberData.tributaryWidth
        });
        
        if (memberData.designation) {
            params.set('designation', memberData.designation);
        }
        
        window.location.href = `/structural-analyser?${params.toString()}`;
    }

    extractMemberAnalysisData(member) {
        return {
            type: member.type,
            id: member.id,
            category: member.category,
            length: 6.0,
            storey: 1,
            totalStoreys: 3,
            tributaryWidth: 3.0,
            designation: null
        };
    }

    showMemberDetails(memberData) {
        const container = document.getElementById('memberDetailsContainer');
        const canvas = document.getElementById('designCanvas');
        
        if (!container) return;
        
        // Populate member details
        this.populateMemberDetails(memberData);
        
        // Show container
        container.style.display = 'flex';
        container.classList.add('active');
        
        // Adjust canvas
        if (canvas) {
            canvas.classList.add('member-details-open');
        }
        
        console.log('[StructureDesigner3D] Member details shown for:', memberData.type);
    }

    hideMemberDetails() {
        const container = document.getElementById('memberDetailsContainer');
        const canvas = document.getElementById('designCanvas');
        
        if (!container) return;
        
        // Hide container
        container.classList.remove('active');
        setTimeout(() => {
            container.style.display = 'none';
        }, 300);
        
        // Reset canvas
        if (canvas) {
            canvas.classList.remove('member-details-open');
        }
        
        console.log('[StructureDesigner3D] Member details hidden');
    }

    populateMemberDetails(memberData) {
        // Helper function to safely set text content
        const setText = (id, value) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value || '-';
            }
        };

        // Basic member information
        setText('memberType', this.formatMemberType(memberData.type));
        setText('memberID', memberData.id || 'Unknown');
        
        // If this is a structural member with metadata
        if (memberData.metadata) {
            const meta = memberData.metadata;
            setText('memberDesignation', meta.designation || 'Standard Section');
            setText('memberLength', meta.length ? `${meta.length.toFixed(2)} m` : '-');
            setText('memberOrientation', this.formatOrientation(meta.orientation));
            setText('memberCrossSection', meta.cross_section || 'Unknown');
            setText('memberDimensions', this.formatDimensions(meta.dimensions));
        } else {
            // Fallback for basic object data
            setText('memberDesignation', 'Standard Section');
            setText('memberLength', '-');
            setText('memberOrientation', '-');
            setText('memberCrossSection', '-');
            setText('memberDimensions', '-');
        }
    }

    formatMemberType(type) {
        const typeMap = {
            'column': 'Column',
            'beam': 'Beam', 
            'rafter_beam': 'Rafter Beam',
            'selected_object': 'Selected Object',
            'rigidFrame': 'Structural Frame'
        };
        return typeMap[type] || type;
    }

    formatOrientation(orientation) {
        if (!orientation) return '-';
        
        const h = orientation.horizontal_angle?.toFixed(1) || '0.0';
        const v = orientation.vertical_angle?.toFixed(1) || '0.0';
        return `H: ${h}°, V: ${v}°`;
    }

    formatDimensions(dimensions) {
        if (!dimensions) return '-';
        
        if (dimensions.width && dimensions.depth) {
            return `${(dimensions.width * 1000).toFixed(0)} × ${(dimensions.depth * 1000).toFixed(0)} mm`;
        }
        
        return '-';
    }

    formatPoint(point) {
        if (!point || !Array.isArray(point)) return '-';
        
        return `(${point[0]?.toFixed(2) || '0'}, ${point[1]?.toFixed(2) || '0'}, ${point[2]?.toFixed(2) || '0'})`;
    }

    showError(message) {
        console.error('[StructureDesigner3D] Error:', message);
        const layoutStatus = document.getElementById('layoutStatus');
        if (layoutStatus) {
            layoutStatus.textContent = `Error: ${message}`;
            layoutStatus.className = 'status-display status-error';
        }
    }

    showSuccess(message) {
        console.log('[StructureDesigner3D] Success:', message);
        const layoutStatus = document.getElementById('layoutStatus');
        if (layoutStatus) {
            layoutStatus.textContent = message;
            layoutStatus.className = 'status-display status-success';
            setTimeout(() => {
                if (layoutStatus.textContent === message) {
                    layoutStatus.textContent = 'Ready';
                    layoutStatus.className = 'status-display';
                }
            }, 3000);
        }
    }
}

// Export for use by other modules
window.StructureDesigner3DCore = StructureDesigner3DCore;
