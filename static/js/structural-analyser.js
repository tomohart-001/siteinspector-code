
/**
 * Structural Analyser - Member Analysis and Design Verification
 */

class StructuralAnalyser {
    constructor() {
        this.memberData = null;
        this.analysisResults = null;
        this.beamSpecifications = {};
        this.lastMetadata = null;
        this.refreshInterval = null;
        
        this.initialize();
    }

    initialize() {
        console.log('[StructuralAnalyser] Initializing...');
        
        // Load member data from URL parameters
        this.loadMemberData();
        
        // Load beam specifications
        this.loadBeamSpecifications();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Update member info display
        this.updateMemberDisplay();
        
        // Start periodic refresh of beam specifications
        this.startPeriodicRefresh();
    }

    loadMemberData() {
        const urlParams = new URLSearchParams(window.location.search);
        
        this.memberData = {
            type: urlParams.get('type') || 'Unknown',
            id: urlParams.get('id') || 'Unknown',
            category: urlParams.get('category') || 'Unknown',
            length: parseFloat(urlParams.get('length')) || 6.0,
            storey: parseInt(urlParams.get('storey')) || 1,
            totalStoreys: parseInt(urlParams.get('totalStoreys')) || 3,
            tributaryWidth: parseFloat(urlParams.get('tributaryWidth')) || 3.0,
            designation: urlParams.get('designation') || null
        };

        console.log('[StructuralAnalyser] Member data loaded:', this.memberData);
    }

    async loadBeamSpecifications() {
        try {
            const response = await fetch('/api/beam-specifications');
            const result = await response.json();
            
            if (result.success) {
                // Store previous specifications count for change detection
                const previousCount = Object.keys(this.beamSpecifications).length;
                
                // Clear existing specifications
                this.beamSpecifications = {};
                
                result.specifications.forEach(spec => {
                    this.beamSpecifications[spec.designation] = spec;
                    console.log(`[StructuralAnalyser] Loaded spec for ${spec.designation}:`, {
                        area: spec.section_area_mm2,
                        depth: spec.section_depth_mm,
                        Ix: spec.moment_inertia_x_mm4,
                        Iy: spec.moment_inertia_y_mm4,
                        Zx: spec.section_modulus_x_mm3,
                        Zy: spec.section_modulus_y_mm3,
                        grade: spec.grade_mpa,
                        density: spec.density_kg_m
                    });
                });
                
                // Update steel designation dropdown
                this.populateDesignationDropdown();
                
                // If specifications changed, update section properties
                const currentCount = Object.keys(this.beamSpecifications).length;
                if (previousCount !== currentCount && previousCount > 0) {
                    console.log('[StructuralAnalyser] Beam specifications updated, refreshing properties');
                    this.updateSectionProperties();
                }
                
                console.log(`[StructuralAnalyser] Loaded ${result.specifications.length} beam specifications from database`);
            }
        } catch (error) {
            console.error('[StructuralAnalyser] Error loading beam specifications:', error);
        }
    }

    async fetchBeamSpecificationByDesignation(designation) {
        try {
            const response = await fetch(`/api/beam-specifications?designation=${encodeURIComponent(designation)}`);
            const result = await response.json();
            
            if (result.success && result.specifications.length > 0) {
                const spec = result.specifications.find(s => s.designation === designation);
                if (spec) {
                    console.log(`[StructuralAnalyser] Fetched specification for ${designation}:`, spec);
                    return spec;
                }
            }
            return null;
        } catch (error) {
            console.error(`[StructuralAnalyser] Error fetching specification for ${designation}:`, error);
            return null;
        }
    }

    populateDesignationDropdown() {
        const dropdown = document.getElementById('steelDesignation');
        if (!dropdown) {
            console.error('[StructuralAnalyser] Steel designation dropdown not found');
            return;
        }
        
        dropdown.innerHTML = '';
        
        // Sort designations for better user experience
        const sortedDesignations = Object.keys(this.beamSpecifications).sort();
        
        if (sortedDesignations.length === 0) {
            console.warn('[StructuralAnalyser] No beam specifications available');
            return;
        }
        
        sortedDesignations.forEach(designation => {
            const spec = this.beamSpecifications[designation];
            const option = document.createElement('option');
            option.value = designation;
            option.textContent = `${designation} (${spec.grade_mpa}MPa)`;
            dropdown.appendChild(option);
        });
        
        // Set designation based on member data if available, otherwise use default
        let selectedDesignation = null;
        
        if (this.memberData && this.memberData.designation && this.beamSpecifications[this.memberData.designation]) {
            selectedDesignation = this.memberData.designation;
            console.log('[StructuralAnalyser] Set designation from member data:', this.memberData.designation);
        } else {
            // Use the first available designation as default
            selectedDesignation = sortedDesignations[0] || '760UB173';
            console.log('[StructuralAnalyser] Using default designation:', selectedDesignation);
        }
        
        dropdown.value = selectedDesignation;
        
        // Force update properties after dropdown is populated
        setTimeout(() => {
            this.updateSectionProperties();
        }, 100);
    }

    updateMemberDisplay() {
        const memberInfo = document.getElementById('memberInfo');
        if (memberInfo && this.memberData) {
            memberInfo.value = `${this.memberData.type} (${this.memberData.category}) - Storey ${this.memberData.storey}`;
        }
        
        // Update length and storey inputs
        document.getElementById('memberLength').value = this.memberData.length;
        document.getElementById('memberStorey').value = this.memberData.storey;
        document.getElementById('totalStoreys').value = this.memberData.totalStoreys;
        document.getElementById('tributaryWidth').value = this.memberData.tributaryWidth;
    }

    setupEventListeners() {
        // Steel designation change
        document.getElementById('steelDesignation').addEventListener('change', () => {
            this.updateSectionProperties();
        });

        // Run analysis button
        document.getElementById('runAnalysisBtn').addEventListener('click', () => {
            this.runAnalysis();
        });

        // Reset inputs button
        document.getElementById('resetInputsBtn').addEventListener('click', () => {
            this.resetToDefaults();
        });

        // Export results button
        document.getElementById('exportResultsBtn').addEventListener('click', () => {
            this.exportResults();
        });

        // New analysis button
        document.getElementById('newAnalysisBtn').addEventListener('click', () => {
            this.newAnalysis();
        });
    }

    updateSectionProperties() {
        const designation = document.getElementById('steelDesignation').value;
        const spec = this.beamSpecifications[designation];
        
        if (spec) {
            console.log(`[StructuralAnalyser] Updating properties for ${designation} with spec:`, spec);
            
            // Update all section properties from database metadata
            const sectionAreaField = document.getElementById('sectionArea');
            const sectionDepthField = document.getElementById('sectionDepth');
            const momentInertiaXField = document.getElementById('momentInertiaX');
            const momentInertiaYField = document.getElementById('momentInertiaY');
            const sectionModulusXField = document.getElementById('sectionModulusX');
            const sectionModulusYField = document.getElementById('sectionModulusY');
            
            // Update Section Properties with proper values
            if (sectionAreaField && spec.section_area_mm2) {
                sectionAreaField.value = spec.section_area_mm2;
                console.log(`[StructuralAnalyser] Updated Section Area: ${spec.section_area_mm2} mm²`);
            }
            if (sectionDepthField && spec.section_depth_mm) {
                sectionDepthField.value = spec.section_depth_mm;
                console.log(`[StructuralAnalyser] Updated Section Depth: ${spec.section_depth_mm} mm`);
            }
            if (momentInertiaXField && spec.moment_inertia_x_mm4) {
                momentInertiaXField.value = spec.moment_inertia_x_mm4;
                console.log(`[StructuralAnalyser] Updated I_x: ${spec.moment_inertia_x_mm4} mm⁴`);
            }
            if (momentInertiaYField && spec.moment_inertia_y_mm4) {
                momentInertiaYField.value = spec.moment_inertia_y_mm4;
                console.log(`[StructuralAnalyser] Updated I_y: ${spec.moment_inertia_y_mm4} mm⁴`);
            }
            if (sectionModulusXField && spec.section_modulus_x_mm3) {
                sectionModulusXField.value = spec.section_modulus_x_mm3;
                console.log(`[StructuralAnalyser] Updated Z_x: ${spec.section_modulus_x_mm3} mm³`);
            }
            if (sectionModulusYField && spec.section_modulus_y_mm3) {
                sectionModulusYField.value = spec.section_modulus_y_mm3;
                console.log(`[StructuralAnalyser] Updated Z_y: ${spec.section_modulus_y_mm3} mm³`);
            }
            
            // Update steel properties from database metadata
            const steelDensityField = document.getElementById('steelDensity');
            const yieldStrengthField = document.getElementById('yieldStrength');
            
            if (steelDensityField && spec.density_kg_m) {
                steelDensityField.value = spec.density_kg_m;
                console.log(`[StructuralAnalyser] Updated Steel Density: ${spec.density_kg_m} kg/m³`);
            }
            if (yieldStrengthField && spec.grade_mpa) {
                yieldStrengthField.value = spec.grade_mpa;
                console.log(`[StructuralAnalyser] Updated Yield Strength: ${spec.grade_mpa} MPa`);
            }
            
            // Update additional properties if available
            if (spec.width_mm) {
                // Store width for calculations but don't display as it's not in UI
                this.currentBeamWidth = spec.width_mm;
            }
            
            console.log(`[StructuralAnalyser] Successfully updated all properties from database for ${designation}`);
        } else {
            console.warn(`[StructuralAnalyser] No specification found for designation: ${designation}`);
            console.log(`[StructuralAnalyser] Available specifications:`, Object.keys(this.beamSpecifications));
        }
    }

    collectInputData() {
        return {
            member: {
                type: this.memberData.type,
                length: parseFloat(document.getElementById('memberLength').value),
                storey: parseInt(document.getElementById('memberStorey').value),
                totalStoreys: parseInt(document.getElementById('totalStoreys').value),
                tributaryWidth: parseFloat(document.getElementById('tributaryWidth').value)
            },
            analysis: {
                supportConditions: document.getElementById('supportConditions').value,
                loadingType: document.getElementById('loadingType').value
            },
            steel: {
                designation: document.getElementById('steelDesignation').value,
                density: parseFloat(document.getElementById('steelDensity').value),
                yieldStrength: parseFloat(document.getElementById('yieldStrength').value),
                modulusElasticity: parseFloat(document.getElementById('modulusElasticity').value)
            },
            section: {
                area: parseFloat(document.getElementById('sectionArea').value),
                depth: parseFloat(document.getElementById('sectionDepth').value),
                momentInertiaX: parseFloat(document.getElementById('momentInertiaX').value),
                momentInertiaY: parseFloat(document.getElementById('momentInertiaY').value),
                sectionModulusX: parseFloat(document.getElementById('sectionModulusX').value),
                sectionModulusY: parseFloat(document.getElementById('sectionModulusY').value)
            },
            liveLoads: {
                roof: {
                    occupancy: parseFloat(document.getElementById('roofOccupancy').value),
                    snow: parseFloat(document.getElementById('snowLoad').value),
                    wind: parseFloat(document.getElementById('windLoad').value),
                    maintenance: parseFloat(document.getElementById('maintenanceLoad').value)
                },
                floor: {
                    occupancy: parseFloat(document.getElementById('floorOccupancy').value),
                    seismic: parseFloat(document.getElementById('seismicLoad').value)
                }
            },
            deadLoads: {
                floor: parseFloat(document.getElementById('floorDeadLoad').value),
                slabSelfWeight: parseFloat(document.getElementById('slabSelfWeight').value)
            }
        };
    }

    runAnalysis() {
        console.log('[StructuralAnalyser] Running analysis...');
        
        const inputs = this.collectInputData();
        
        try {
            // Compute load cases
            const storeyLoads = this.computeLoadCases(inputs);
            
            // Compute bending and shear
            const bendingShearResults = this.computeBendingShear(storeyLoads, inputs.member.length);
            
            // Perform design checks
            const designChecks = this.performDesignChecks(inputs, bendingShearResults);
            
            // Store results
            this.analysisResults = {
                inputs: inputs,
                storeyLoads: storeyLoads,
                bendingShear: bendingShearResults,
                designChecks: designChecks
            };
            
            // Display results
            this.displayResults();
            
        } catch (error) {
            console.error('[StructuralAnalyser] Analysis error:', error);
            alert('Error running analysis: ' + error.message);
        }
    }

    computeLoadCases(inputs) {
        const { member, liveLoads, deadLoads } = inputs;
        const results = [];

        for (let i = 0; i < member.totalStoreys; i++) {
            const isRoof = (i === 0);
            const storeyNumber = member.totalStoreys - i;

            // Live and dead loads in kPa -> N/m²
            let qArea = 0;
            if (isRoof) {
                qArea = (liveLoads.roof.occupancy + liveLoads.roof.snow + 
                        liveLoads.roof.wind + liveLoads.roof.maintenance) * 1000;
            } else {
                qArea = (liveLoads.floor.occupancy + liveLoads.floor.seismic) * 1000;
            }

            const gArea = (deadLoads.floor + deadLoads.slabSelfWeight) * 1000;

            // Convert area loads to line loads (N/m)
            const G = gArea * member.tributaryWidth;
            const Q = qArea * member.tributaryWidth;
            const Qs = 0.7 * Q;
            
            // Cumulative dead load from upper floors
            const cumulativeDeadAbove = results.reduce((sum, r) => sum + r.G, 0);
            const GTotal = G + cumulativeDeadAbove;

            results.push({
                storey: storeyNumber,
                G: GTotal,
                Q: Q,
                Qs: Qs,
                ULS1: 1.35 * GTotal,
                ULS2: 1.2 * GTotal + 1.5 * Q,
                SLS1: GTotal,
                SLS2: Qs,
                SLS3: GTotal + Qs
            });
        }

        return results.reverse(); // Bottom-up
    }

    computeBendingShear(storeyLoads, span) {
        const results = [];
        
        for (const load of storeyLoads) {
            const result = { storey: load.storey };

            ['ULS1', 'ULS2', 'SLS1', 'SLS2', 'SLS3'].forEach(caseType => {
                const w = load[caseType]; // N/m
                const MMax = w * span * span / 8; // Nm
                const VMax = w * span / 2; // N

                result[`${caseType}_Mmax_kNm`] = Math.round(MMax / 1000 * 100) / 100;
                result[`${caseType}_Vmax_kN`] = Math.round(VMax / 1000 * 100) / 100;
            });

            results.push(result);
        }

        return results;
    }

    performDesignChecks(inputs, bendingShearResults) {
        const { steel, section, member } = inputs;
        const span = member.length;
        
        // Convert units
        const fY = steel.yieldStrength * 1e6; // MPa to Pa
        const E = steel.modulusElasticity * 1e9; // GPa to Pa
        const Z = section.sectionModulusX / 1e9; // mm³ to m³
        const I = section.momentInertiaX / 1e12; // mm⁴ to m⁴
        const Av = section.area / 1e6; // mm² to m² (approximation for shear area)
        const depth = section.depth / 1000; // mm to m

        // Find maximum loads from the member's storey
        const memberStoreyResult = bendingShearResults.find(r => r.storey === member.storey);
        if (!memberStoreyResult) {
            throw new Error(`No results found for storey ${member.storey}`);
        }

        // Get critical values
        const MMaxULS = Math.max(memberStoreyResult.ULS1_Mmax_kNm, memberStoreyResult.ULS2_Mmax_kNm) * 1000; // kNm to Nm
        const VMaxULS = Math.max(memberStoreyResult.ULS1_Vmax_kN, memberStoreyResult.ULS2_Vmax_kN) * 1000; // kN to N
        const MMaxSLS = memberStoreyResult.SLS3_Mmax_kNm * 1000; // kNm to Nm

        // Radius of gyration
        const radiusGyr = Math.sqrt(I / Av);
        const slendernessRatio = span / radiusGyr;

        // Design checks
        const MCapacity = 0.9 * Z * fY;
        const VCapacity = 0.9 * Av * fY / Math.sqrt(3);
        
        // Deflection check
        const wSLS = memberStoreyResult.SLS3_Mmax_kNm * 8000 / (span * span); // Back-calculate load from moment
        const deltaMax = 5 * wSLS * Math.pow(span, 4) / (384 * E * I);
        const deltaLimit = span / 250;

        return {
            bending: {
                demand: MMaxULS,
                capacity: MCapacity,
                utilization: MMaxULS / MCapacity,
                status: MMaxULS <= MCapacity ? 'PASS' : 'FAIL'
            },
            shear: {
                demand: VMaxULS,
                capacity: VCapacity,
                utilization: VMaxULS / VCapacity,
                status: VMaxULS <= VCapacity ? 'PASS' : 'FAIL'
            },
            deflection: {
                demand: deltaMax,
                limit: deltaLimit,
                utilization: deltaMax / deltaLimit,
                status: deltaMax <= deltaLimit ? 'PASS' : 'FAIL'
            },
            slenderness: {
                ratio: slendernessRatio,
                radiusGyr: radiusGyr
            }
        };
    }

    displayResults() {
        // Show results panel
        document.getElementById('resultsPanel').classList.add('show');
        
        // Display summary cards
        this.displaySummaryCards();
        
        // Display load cases table
        this.displayLoadCasesTable();
        
        // Display design checks table
        this.displayDesignChecksTable();
        
        // Display calculation working
        this.displayCalculationWorking();

        // Scroll to results
        document.getElementById('resultsPanel').scrollIntoView({ behavior: 'smooth' });
    }

    displaySummaryCards() {
        const container = document.getElementById('summaryCards');
        const { designChecks } = this.analysisResults;

        const cards = [
            {
                title: 'Bending Check',
                value: `${(designChecks.bending.utilization * 100).toFixed(1)}%`,
                caption: `${(designChecks.bending.demand / 1000).toFixed(1)} / ${(designChecks.bending.capacity / 1000).toFixed(1)} kNm`,
                status: designChecks.bending.status
            },
            {
                title: 'Shear Check',
                value: `${(designChecks.shear.utilization * 100).toFixed(1)}%`,
                caption: `${(designChecks.shear.demand / 1000).toFixed(1)} / ${(designChecks.shear.capacity / 1000).toFixed(1)} kN`,
                status: designChecks.shear.status
            },
            {
                title: 'Deflection Check',
                value: `${(designChecks.deflection.utilization * 100).toFixed(1)}%`,
                caption: `${(designChecks.deflection.demand * 1000).toFixed(1)} / ${(designChecks.deflection.limit * 1000).toFixed(1)} mm`,
                status: designChecks.deflection.status
            },
            {
                title: 'Slenderness Ratio',
                value: `${designChecks.slenderness.ratio.toFixed(1)}`,
                caption: `L / r_y = ${this.analysisResults.inputs.member.length} / ${(designChecks.slenderness.radiusGyr * 1000).toFixed(1)}mm`,
                status: 'INFO'
            }
        ];

        container.innerHTML = cards.map(card => `
            <div class="result-card">
                <div class="result-title">${card.title}</div>
                <div class="result-value status-${card.status.toLowerCase()}">${card.value}</div>
                <div class="result-caption">${card.caption}</div>
            </div>
        `).join('');
    }

    displayLoadCasesTable() {
        const container = document.getElementById('loadCasesTable');
        const { storeyLoads, bendingShear } = this.analysisResults;

        // Find maximum Mmax and Vmax for each storey
        const storeyMaxValues = {};
        bendingShear.forEach(result => {
            let maxMmax = 0;
            let maxVmax = 0;
            let maxMmaxCase = '';
            let maxVmaxCase = '';
            
            ['ULS1', 'ULS2', 'SLS1', 'SLS2', 'SLS3'].forEach(caseType => {
                const mmax = result[`${caseType}_Mmax_kNm`];
                const vmax = result[`${caseType}_Vmax_kN`];
                
                if (mmax > maxMmax) {
                    maxMmax = mmax;
                    maxMmaxCase = caseType;
                }
                if (vmax > maxVmax) {
                    maxVmax = vmax;
                    maxVmaxCase = caseType;
                }
            });
            
            storeyMaxValues[result.storey] = {
                maxMmaxCase: maxMmaxCase,
                maxVmaxCase: maxVmaxCase
            };
        });

        let tableHTML = `
            <table class="calculations-table">
                <thead>
                    <tr>
                        <th>Storey</th>
                        <th>Load Case</th>
                        <th>Load (kN/m)</th>
                        <th>M_max (kNm)</th>
                        <th>V_max (kN)</th>
                    </tr>
                </thead>
                <tbody>
        `;

        bendingShear.forEach(result => {
            ['ULS1', 'ULS2', 'SLS1', 'SLS2', 'SLS3'].forEach(caseType => {
                const load = storeyLoads.find(l => l.storey === result.storey);
                const storeyMax = storeyMaxValues[result.storey];
                
                // Check if this row has maximum Mmax or Vmax for this storey
                const isMaxMmax = caseType === storeyMax.maxMmaxCase;
                const isMaxVmax = caseType === storeyMax.maxVmaxCase;
                const shouldHighlight = isMaxMmax || isMaxVmax;
                
                const rowClass = shouldHighlight ? ' class="max-value-row"' : '';
                
                tableHTML += `
                    <tr${rowClass}>
                        <td>${result.storey}</td>
                        <td>${caseType}</td>
                        <td>${(load[caseType] / 1000).toFixed(2)}</td>
                        <td${isMaxMmax ? ' class="max-moment"' : ''}>${result[`${caseType}_Mmax_kNm`]}</td>
                        <td${isMaxVmax ? ' class="max-shear"' : ''}>${result[`${caseType}_Vmax_kN`]}</td>
                    </tr>
                `;
            });
        });

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    }

    displayDesignChecksTable() {
        const container = document.getElementById('designChecksTable');
        const { designChecks } = this.analysisResults;

        const tableHTML = `
            <table class="calculations-table">
                <thead>
                    <tr>
                        <th>Check Type</th>
                        <th>Demand</th>
                        <th>Capacity</th>
                        <th>Utilization</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Bending</td>
                        <td>${(designChecks.bending.demand / 1000).toFixed(1)} kNm</td>
                        <td>${(designChecks.bending.capacity / 1000).toFixed(1)} kNm</td>
                        <td>${(designChecks.bending.utilization * 100).toFixed(1)}%</td>
                        <td class="status-${designChecks.bending.status.toLowerCase()}">${designChecks.bending.status}</td>
                    </tr>
                    <tr>
                        <td>Shear</td>
                        <td>${(designChecks.shear.demand / 1000).toFixed(1)} kN</td>
                        <td>${(designChecks.shear.capacity / 1000).toFixed(1)} kN</td>
                        <td>${(designChecks.shear.utilization * 100).toFixed(1)}%</td>
                        <td class="status-${designChecks.shear.status.toLowerCase()}">${designChecks.shear.status}</td>
                    </tr>
                    <tr>
                        <td>Deflection</td>
                        <td>${(designChecks.deflection.demand * 1000).toFixed(1)} mm</td>
                        <td>${(designChecks.deflection.limit * 1000).toFixed(1)} mm</td>
                        <td>${(designChecks.deflection.utilization * 100).toFixed(1)}%</td>
                        <td class="status-${designChecks.deflection.status.toLowerCase()}">${designChecks.deflection.status}</td>
                    </tr>
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
    }

    displayCalculationWorking() {
        const container = document.getElementById('calculationWorking');
        const { inputs, designChecks } = this.analysisResults;

        const working = `
CALCULATION WORKING
==================

Member: ${inputs.steel.designation} - ${inputs.member.type}
Length: ${inputs.member.length}m, Tributary Width: ${inputs.member.tributaryWidth}m

MATERIAL PROPERTIES:
f_y = ${inputs.steel.yieldStrength} MPa = ${inputs.steel.yieldStrength * 1e6} Pa
E = ${inputs.steel.modulusElasticity} GPa = ${inputs.steel.modulusElasticity * 1e9} Pa

SECTION PROPERTIES:
Z_x = ${inputs.section.sectionModulusX} mm³ = ${inputs.section.sectionModulusX / 1e9} m³
I_x = ${inputs.section.momentInertiaX} mm⁴ = ${inputs.section.momentInertiaX / 1e12} m⁴
A = ${inputs.section.area} mm² = ${inputs.section.area / 1e6} m²

DESIGN CHECKS:

1. BENDING CHECK:
   M_max = ${(designChecks.bending.demand / 1000).toFixed(1)} kNm
   M_capacity = 0.9 × Z × f_y = 0.9 × ${inputs.section.sectionModulusX / 1e9} × ${inputs.steel.yieldStrength * 1e6}
             = ${(designChecks.bending.capacity / 1000).toFixed(1)} kNm
   Utilization = ${(designChecks.bending.utilization * 100).toFixed(1)}% - ${designChecks.bending.status}

2. SHEAR CHECK:
   V_max = ${(designChecks.shear.demand / 1000).toFixed(1)} kN
   V_capacity = 0.9 × A × f_y / √3 = ${(designChecks.shear.capacity / 1000).toFixed(1)} kN
   Utilization = ${(designChecks.shear.utilization * 100).toFixed(1)}% - ${designChecks.shear.status}

3. DEFLECTION CHECK:
   δ_max = ${(designChecks.deflection.demand * 1000).toFixed(1)} mm
   δ_limit = L/250 = ${inputs.member.length}/250 = ${(designChecks.deflection.limit * 1000).toFixed(1)} mm
   Utilization = ${(designChecks.deflection.utilization * 100).toFixed(1)}% - ${designChecks.deflection.status}

4. SLENDERNESS:
   r_y = √(I/A) = ${(designChecks.slenderness.radiusGyr * 1000).toFixed(1)} mm
   λ = L/r_y = ${inputs.member.length}m / ${(designChecks.slenderness.radiusGyr * 1000).toFixed(1)}mm = ${designChecks.slenderness.ratio.toFixed(1)}
        `;

        container.textContent = working;
    }

    resetToDefaults() {
        // Reset all input fields to their default values
        const defaults = {
            steelDesignation: '760UB173',
            steelDensity: 7850,
            yieldStrength: 300,
            modulusElasticity: 200,
            supportConditions: 'simply_supported',
            loadingType: 'udl',
            roofOccupancy: 0.25,
            snowLoad: 0.9,
            windLoad: 0.6,
            maintenanceLoad: 0.25,
            floorOccupancy: 2.5,
            seismicLoad: 0.5,
            floorDeadLoad: 1.5,
            slabSelfWeight: 2.5
        };

        Object.entries(defaults).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.value = value;
        });

        this.updateSectionProperties();
    }

    exportResults() {
        if (!this.analysisResults) {
            alert('No analysis results to export');
            return;
        }

        const exportData = {
            member: this.memberData,
            inputs: this.analysisResults.inputs,
            results: this.analysisResults.designChecks,
            timestamp: new Date().toISOString()
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `structural-analysis-${this.memberData.type}-${Date.now()}.json`;
        link.click();

        URL.revokeObjectURL(url);
    }

    newAnalysis() {
        // Hide results panel
        document.getElementById('resultsPanel').classList.remove('show');
        
        // Reset to defaults
        this.resetToDefaults();
        
        // Clear results
        this.analysisResults = null;
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    startPeriodicRefresh() {
        // Check for beam specification updates every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.checkForSpecificationUpdates();
        }, 30000);
        
        console.log('[StructuralAnalyser] Started periodic refresh for beam specifications');
    }

    async checkForSpecificationUpdates() {
        try {
            // First check metadata for efficient change detection
            const metadataResponse = await fetch('/api/beam-specifications/metadata');
            const metadataResult = await metadataResponse.json();
            
            if (metadataResult.success) {
                const currentMetadata = metadataResult.metadata;
                
                // Compare with stored metadata
                if (!this.lastMetadata || 
                    this.lastMetadata.count !== currentMetadata.count ||
                    this.lastMetadata.designations_hash !== currentMetadata.designations_hash ||
                    this.lastMetadata.last_modified !== currentMetadata.last_modified) {
                    
                    console.log('[StructuralAnalyser] Database changes detected, refreshing specifications');
                    
                    // Load full specifications if changes detected
                    await this.loadBeamSpecifications();
                    
                    // Show notification to user
                    this.showUpdateNotification();
                    
                    // Update stored metadata
                    this.lastMetadata = currentMetadata;
                }
            }
        } catch (error) {
            console.error('[StructuralAnalyser] Error checking for specification updates:', error);
        }
    }

    hasSpecificationsChanged(newSpecifications) {
        const currentKeys = Object.keys(this.beamSpecifications).sort();
        const newKeys = Object.keys(newSpecifications).sort();
        
        // Check if number of specifications changed
        if (currentKeys.length !== newKeys.length) {
            return true;
        }
        
        // Check if designation names changed
        if (JSON.stringify(currentKeys) !== JSON.stringify(newKeys)) {
            return true;
        }
        
        // Check if specification data changed
        for (const designation of currentKeys) {
            const current = this.beamSpecifications[designation];
            const updated = newSpecifications[designation];
            
            if (!updated || 
                current.section_area_mm2 !== updated.section_area_mm2 ||
                current.section_depth_mm !== updated.section_depth_mm ||
                current.moment_inertia_x_mm4 !== updated.moment_inertia_x_mm4 ||
                current.section_modulus_x_mm3 !== updated.section_modulus_x_mm3) {
                return true;
            }
        }
        
        return false;
    }

    showUpdateNotification() {
        // Create temporary notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            background: linear-gradient(135deg, #4a6cf7 0%, #3a5ae0 100%);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 16px rgba(74, 108, 247, 0.3);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = 'Beam specifications updated from database';
        
        // Add slide-in animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                if (style.parentNode) {
                    style.parentNode.removeChild(style);
                }
            }, 300);
        }, 3000);
    }

    destroy() {
        // Clean up periodic refresh when component is destroyed
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            console.log('[StructuralAnalyser] Stopped periodic refresh');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.structuralAnalyser = new StructuralAnalyser();
});

// Clean up when page unloads
window.addEventListener('beforeunload', () => {
    if (window.structuralAnalyser) {
        window.structuralAnalyser.destroy();
    }
});
