
"""
Mass Calculator Service - Calculate mass and gravity forces for structural members
"""
import numpy as np
from typing import Dict, Any, List, Tuple
from .base_service import BaseService
from .beam_service import BeamService


class MassCalculatorService(BaseService):
    """Service for calculating structural member masses and gravity forces"""
    
    def __init__(self):
        super().__init__("MassCalculatorService")
        
        # Material densities (kg/m³)
        self.material_densities = {
            'steel': 7850,
            'concrete': 2400,
            'reinforced_concrete': 2500
        }
        
        # Gravity acceleration (m/s²)
        self.g = 9.81
    
    def calculate_structure_masses(self, structure_type: str, parameters: Dict[str, Any], 
                                  session_id: str = None) -> Dict[str, Any]:
        """Calculate masses for all structural members in a structure"""
        try:
            self._log_operation(f"Mass calculation started for {structure_type}")
            
            if structure_type == 'portal_frame':
                return self.calculate_portal_frame_masses(parameters, session_id)
            elif structure_type == 'rigid_frame':
                return self.calculate_rigid_frame_masses(parameters, session_id)
            elif structure_type == 'hybrid_frame':
                return self.calculate_hybrid_frame_masses(parameters, session_id)
            else:
                raise ValueError(f"Unsupported structure type: {structure_type}")
                
        except Exception as e:
            return self._handle_error("Structure mass calculation", e, {})
    
    def calculate_portal_frame_masses(self, parameters: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Calculate masses for portal frame structure"""
        try:
            # Get beam selections if available
            beam_selections = {}
            if session_id:
                beam_selections = BeamService.get_user_beam_selections(session_id)
            
            # Extract parameters
            span = parameters.get('span', 20.0)
            eave_height = parameters.get('eave_height', 6.0)
            ridge_height = parameters.get('ridge_height', 9.0)
            portal_spacing = parameters.get('portal_spacing', 6.0)
            num_portals = parameters.get('num_portals', 4)
            beam_size = parameters.get('beam_size', (0.3, 0.6))
            column_size = parameters.get('column_size', (0.3, 0.6))
            purlin_size = parameters.get('purlin_size', (0.1, 0.1))
            girt_size = parameters.get('girt_size', (0.1, 0.1))
            
            results = {
                'steel_members': {},
                'concrete_members': {},
                'total_masses': {},
                'gravity_forces': {},
                'summary': {}
            }
            
            # Calculate steel member masses
            steel_masses = self._calculate_portal_steel_masses(
                span, eave_height, ridge_height, portal_spacing, num_portals,
                beam_size, column_size, purlin_size, girt_size, beam_selections
            )
            results['steel_members'] = steel_masses
            
            # Calculate slab mass if specified
            if parameters.get('include_slab', True):
                slab_thickness = parameters.get('slab_thickness', 0.15)
                slab_area = (num_portals - 1) * portal_spacing * span
                slab_mass = self._calculate_slab_mass(slab_area, slab_thickness)
                results['concrete_members']['floor_slab'] = slab_mass
            
            # Calculate totals
            total_steel_mass = sum(member['mass_kg'] for member in steel_masses.values())
            total_concrete_mass = sum(member['mass_kg'] for member in results['concrete_members'].values())
            total_mass = total_steel_mass + total_concrete_mass
            
            results['total_masses'] = {
                'steel_total_kg': total_steel_mass,
                'concrete_total_kg': total_concrete_mass,
                'structure_total_kg': total_mass
            }
            
            results['gravity_forces'] = {
                'steel_total_kN': total_steel_mass * self.g / 1000,
                'concrete_total_kN': total_concrete_mass * self.g / 1000,
                'structure_total_kN': total_mass * self.g / 1000
            }
            
            results['summary'] = self._create_mass_summary(results)
            
            self._log_operation(f"Portal frame mass calculation completed", 
                              f"Total mass: {total_mass:.1f} kg")
            
            return {
                'success': True,
                'results': results,
                'structure_type': 'portal_frame'
            }
            
        except Exception as e:
            return self._handle_error("Portal frame mass calculation", e, {})
    
    def calculate_rigid_frame_masses(self, parameters: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Calculate masses for rigid frame structure"""
        try:
            # Get beam selections if available
            beam_selections = {}
            if session_id:
                beam_selections = BeamService.get_user_beam_selections(session_id)
            
            # Extract parameters
            building_length = parameters.get('building_length', 20.0)
            building_width = parameters.get('building_width', 10.0)
            bay_spacing_x = parameters.get('bay_spacing_x', 5.0)
            bay_spacing_y = parameters.get('bay_spacing_y', 5.0)
            column_height = parameters.get('column_height', 4.0)
            num_storeys = parameters.get('num_storeys', 1)
            storey_height = parameters.get('storey_height', column_height)
            
            # Calculate derived parameters
            num_bays_x = max(1, int(building_length / bay_spacing_x))
            num_bays_y = max(1, int(building_width / bay_spacing_y))
            actual_length = num_bays_x * bay_spacing_x
            actual_width = num_bays_y * bay_spacing_y
            
            results = {
                'steel_members': {},
                'concrete_members': {},
                'total_masses': {},
                'gravity_forces': {},
                'summary': {}
            }
            
            # Calculate steel member masses
            steel_masses = self._calculate_rigid_frame_steel_masses(
                actual_length, actual_width, num_bays_x, num_bays_y,
                storey_height, num_storeys, parameters, beam_selections
            )
            results['steel_members'] = steel_masses
            
            # Calculate concrete slab masses for each floor
            if parameters.get('include_slabs', True):
                slab_thickness = parameters.get('slab_thickness', 0.15)
                floor_area = actual_length * actual_width
                
                for storey in range(num_storeys):
                    slab_mass = self._calculate_slab_mass(floor_area, slab_thickness)
                    results['concrete_members'][f'floor_slab_level_{storey + 1}'] = slab_mass
            
            # Calculate totals
            total_steel_mass = sum(member['mass_kg'] for member in steel_masses.values())
            total_concrete_mass = sum(member['mass_kg'] for member in results['concrete_members'].values())
            total_mass = total_steel_mass + total_concrete_mass
            
            results['total_masses'] = {
                'steel_total_kg': total_steel_mass,
                'concrete_total_kg': total_concrete_mass,
                'structure_total_kg': total_mass
            }
            
            results['gravity_forces'] = {
                'steel_total_kN': total_steel_mass * self.g / 1000,
                'concrete_total_kN': total_concrete_mass * self.g / 1000,
                'structure_total_kN': total_mass * self.g / 1000
            }
            
            results['summary'] = self._create_mass_summary(results)
            
            self._log_operation(f"Rigid frame mass calculation completed", 
                              f"Total mass: {total_mass:.1f} kg")
            
            return {
                'success': True,
                'results': results,
                'structure_type': 'rigid_frame'
            }
            
        except Exception as e:
            return self._handle_error("Rigid frame mass calculation", e, {})
    
    def calculate_hybrid_frame_masses(self, parameters: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Calculate masses for hybrid frame structure with core"""
        try:
            # Get beam selections if available
            beam_selections = {}
            if session_id:
                beam_selections = BeamService.get_user_beam_selections(session_id)
            
            # Extract parameters
            building_length = parameters.get('building_length', 20.0)
            building_width = parameters.get('building_width', 10.0)
            bay_spacing_x = parameters.get('bay_spacing_x', 5.0)
            bay_spacing_y = parameters.get('bay_spacing_y', 5.0)
            num_storeys = parameters.get('num_storeys', 3)
            storey_height = parameters.get('storey_height', 3.5)
            core_width = parameters.get('core_width', 3.0)
            core_depth = parameters.get('core_depth', 3.0)
            core_type = parameters.get('core_type', 'hollow')
            core_wall_thickness = parameters.get('core_wall_thickness', 0.4)
            
            # Calculate derived parameters
            num_bays_x = max(1, int(building_length / bay_spacing_x))
            num_bays_y = max(1, int(building_width / bay_spacing_y))
            actual_length = num_bays_x * bay_spacing_x
            actual_width = num_bays_y * bay_spacing_y
            total_height = num_storeys * storey_height
            
            results = {
                'steel_members': {},
                'concrete_members': {},
                'total_masses': {},
                'gravity_forces': {},
                'summary': {}
            }
            
            # Calculate steel frame masses (same as rigid frame but with hybrid system)
            steel_masses = self._calculate_rigid_frame_steel_masses(
                actual_length, actual_width, num_bays_x, num_bays_y,
                storey_height, num_storeys, parameters, beam_selections
            )
            results['steel_members'] = steel_masses
            
            # Calculate concrete core mass
            core_mass = self._calculate_core_mass(
                core_width, core_depth, total_height, core_type, core_wall_thickness
            )
            results['concrete_members']['shear_core'] = core_mass
            
            # Calculate concrete slab masses for each floor
            if parameters.get('include_slabs', True):
                slab_thickness = parameters.get('slab_thickness', 0.15)
                # Subtract core area from floor area
                floor_area = actual_length * actual_width - (core_width * core_depth)
                
                for storey in range(num_storeys):
                    slab_mass = self._calculate_slab_mass(floor_area, slab_thickness)
                    results['concrete_members'][f'floor_slab_level_{storey + 1}'] = slab_mass
            
            # Calculate totals
            total_steel_mass = sum(member['mass_kg'] for member in steel_masses.values())
            total_concrete_mass = sum(member['mass_kg'] for member in results['concrete_members'].values())
            total_mass = total_steel_mass + total_concrete_mass
            
            results['total_masses'] = {
                'steel_total_kg': total_steel_mass,
                'concrete_total_kg': total_concrete_mass,
                'structure_total_kg': total_mass
            }
            
            results['gravity_forces'] = {
                'steel_total_kN': total_steel_mass * self.g / 1000,
                'concrete_total_kN': total_concrete_mass * self.g / 1000,
                'structure_total_kN': total_mass * self.g / 1000
            }
            
            results['summary'] = self._create_mass_summary(results)
            
            self._log_operation(f"Hybrid frame mass calculation completed", 
                              f"Total mass: {total_mass:.1f} kg")
            
            return {
                'success': True,
                'results': results,
                'structure_type': 'hybrid_frame'
            }
            
        except Exception as e:
            return self._handle_error("Hybrid frame mass calculation", e, {})
    
    def _calculate_portal_steel_masses(self, span, eave_height, ridge_height, portal_spacing, 
                                     num_portals, beam_size, column_size, purlin_size, girt_size,
                                     beam_selections):
        """Calculate masses for portal frame steel members"""
        masses = {}
        
        # Get beam specifications for accurate calculations
        column_spec = beam_selections.get('column')
        beam_spec = beam_selections.get('beam')
        
        # Columns
        column_length = eave_height
        num_columns = num_portals * 2  # Two columns per portal
        
        if column_spec:
            # Use actual beam specification
            column_area = column_spec['section_area_mm2'] / 1000000  # mm² to m²
            column_volume_per_unit = column_area * column_length
            column_mass_per_unit = column_volume_per_unit * self.material_densities['steel']
        else:
            # Use simple rectangular approximation
            column_width, column_depth = column_size
            column_area = self._calculate_i_beam_area(column_width, column_depth)
            column_volume_per_unit = column_area * column_length
            column_mass_per_unit = column_volume_per_unit * self.material_densities['steel']
        
        masses['columns'] = {
            'count': num_columns,
            'length_each_m': column_length,
            'area_each_m2': column_area,
            'volume_each_m3': column_volume_per_unit,
            'mass_each_kg': column_mass_per_unit,
            'mass_kg': column_mass_per_unit * num_columns,
            'gravity_force_kN': column_mass_per_unit * num_columns * self.g / 1000
        }
        
        # Rafters
        rafter_length = np.sqrt((span/2)**2 + (ridge_height - eave_height)**2)
        num_rafters = num_portals * 2  # Two rafters per portal
        
        if beam_spec:
            # Use actual beam specification
            rafter_area = beam_spec['section_area_mm2'] / 1000000  # mm² to m²
            rafter_volume_per_unit = rafter_area * rafter_length
            rafter_mass_per_unit = rafter_volume_per_unit * self.material_densities['steel']
        else:
            # Use simple rectangular approximation
            beam_width, beam_depth = beam_size
            rafter_area = self._calculate_i_beam_area(beam_width, beam_depth)
            rafter_volume_per_unit = rafter_area * rafter_length
            rafter_mass_per_unit = rafter_volume_per_unit * self.material_densities['steel']
        
        masses['rafters'] = {
            'count': num_rafters,
            'length_each_m': rafter_length,
            'area_each_m2': rafter_area,
            'volume_each_m3': rafter_volume_per_unit,
            'mass_each_kg': rafter_mass_per_unit,
            'mass_kg': rafter_mass_per_unit * num_rafters,
            'gravity_force_kN': rafter_mass_per_unit * num_rafters * self.g / 1000
        }
        
        # Purlins
        purlin_length = portal_spacing
        purlin_width, purlin_depth = purlin_size
        purlin_area = purlin_width * purlin_depth
        
        # Estimate number of purlins (simplified)
        purlins_per_side = max(1, int(rafter_length / 1.5))  # Spacing ~1.5m
        num_purlins = purlins_per_side * 2 * (num_portals - 1)  # Both sides, between portals
        
        purlin_volume_per_unit = purlin_area * purlin_length
        purlin_mass_per_unit = purlin_volume_per_unit * self.material_densities['steel']
        
        masses['purlins'] = {
            'count': num_purlins,
            'length_each_m': purlin_length,
            'area_each_m2': purlin_area,
            'volume_each_m3': purlin_volume_per_unit,
            'mass_each_kg': purlin_mass_per_unit,
            'mass_kg': purlin_mass_per_unit * num_purlins,
            'gravity_force_kN': purlin_mass_per_unit * num_purlins * self.g / 1000
        }
        
        # Girts
        girt_length = portal_spacing
        girt_width, girt_depth = girt_size
        girt_area = girt_width * girt_depth
        
        # Estimate number of girts
        girts_per_side = max(1, int(eave_height / 1.5))  # Spacing ~1.5m
        num_girts = girts_per_side * 2 * (num_portals - 1)  # Both sides, between portals
        
        girt_volume_per_unit = girt_area * girt_length
        girt_mass_per_unit = girt_volume_per_unit * self.material_densities['steel']
        
        masses['girts'] = {
            'count': num_girts,
            'length_each_m': girt_length,
            'area_each_m2': girt_area,
            'volume_each_m3': girt_volume_per_unit,
            'mass_each_kg': girt_mass_per_unit,
            'mass_kg': girt_mass_per_unit * num_girts,
            'gravity_force_kN': girt_mass_per_unit * num_girts * self.g / 1000
        }
        
        return masses
    
    def _calculate_rigid_frame_steel_masses(self, building_length, building_width, num_bays_x, 
                                          num_bays_y, storey_height, num_storeys, parameters, 
                                          beam_selections):
        """Calculate masses for rigid frame steel members"""
        masses = {}
        
        # Get beam specifications
        column_spec = beam_selections.get('column')
        beam_spec = beam_selections.get('beam')
        
        # Columns
        total_columns = (num_bays_x + 1) * (num_bays_y + 1)
        column_height = storey_height * num_storeys
        
        if column_spec:
            column_area = column_spec['section_area_mm2'] / 1000000  # mm² to m²
        else:
            column_width = parameters.get('column_width', 0.2)
            column_depth = parameters.get('column_depth', 0.3)
            column_area = self._calculate_i_beam_area(column_width, column_depth)
        
        column_volume_per_unit = column_area * column_height
        column_mass_per_unit = column_volume_per_unit * self.material_densities['steel']
        
        masses['columns'] = {
            'count': total_columns,
            'length_each_m': column_height,
            'area_each_m2': column_area,
            'volume_each_m3': column_volume_per_unit,
            'mass_each_kg': column_mass_per_unit,
            'mass_kg': column_mass_per_unit * total_columns,
            'gravity_force_kN': column_mass_per_unit * total_columns * self.g / 1000
        }
        
        # Beams
        beams_per_storey_x = num_bays_x * (num_bays_y + 1)  # X-direction beams
        beams_per_storey_y = num_bays_y * (num_bays_x + 1)  # Y-direction beams
        total_beams = (beams_per_storey_x + beams_per_storey_y) * num_storeys
        
        # Average beam length
        avg_beam_length_x = building_length / num_bays_x
        avg_beam_length_y = building_width / num_bays_y
        avg_beam_length = (avg_beam_length_x + avg_beam_length_y) / 2
        
        if beam_spec:
            beam_area = beam_spec['section_area_mm2'] / 1000000  # mm² to m²
        else:
            beam_width = parameters.get('beam_width', 0.15)
            beam_depth = parameters.get('beam_depth', 0.4)
            beam_area = self._calculate_i_beam_area(beam_width, beam_depth)
        
        beam_volume_per_unit = beam_area * avg_beam_length
        beam_mass_per_unit = beam_volume_per_unit * self.material_densities['steel']
        
        masses['beams'] = {
            'count': total_beams,
            'avg_length_each_m': avg_beam_length,
            'area_each_m2': beam_area,
            'volume_each_m3': beam_volume_per_unit,
            'mass_each_kg': beam_mass_per_unit,
            'mass_kg': beam_mass_per_unit * total_beams,
            'gravity_force_kN': beam_mass_per_unit * total_beams * self.g / 1000
        }
        
        return masses
    
    def _calculate_i_beam_area(self, width, depth, flange_thickness_ratio=0.15, web_thickness_ratio=0.25):
        """Calculate approximate cross-sectional area of an I-beam"""
        flange_thickness = depth * flange_thickness_ratio
        web_thickness = width * web_thickness_ratio
        
        # Two flanges + web
        flange_area = 2 * width * flange_thickness
        web_area = web_thickness * (depth - 2 * flange_thickness)
        
        return flange_area + web_area
    
    def _calculate_slab_mass(self, area, thickness):
        """Calculate mass of concrete slab"""
        volume = area * thickness
        mass = volume * self.material_densities['reinforced_concrete']
        
        return {
            'area_m2': area,
            'thickness_m': thickness,
            'volume_m3': volume,
            'mass_kg': mass,
            'gravity_force_kN': mass * self.g / 1000
        }
    
    def _calculate_core_mass(self, width, depth, height, core_type, wall_thickness):
        """Calculate mass of concrete core"""
        if core_type == 'solid':
            volume = width * depth * height
        elif core_type == 'hollow':
            outer_volume = width * depth * height
            inner_width = width - 2 * wall_thickness
            inner_depth = depth - 2 * wall_thickness
            inner_volume = inner_width * inner_depth * height
            volume = outer_volume - inner_volume
        elif core_type == 'u':
            # U-shape: three walls
            wall1_volume = wall_thickness * depth * height
            wall2_volume = wall_thickness * depth * height
            wall3_volume = (width - 2 * wall_thickness) * wall_thickness * height
            volume = wall1_volume + wall2_volume + wall3_volume
        elif core_type == 'l':
            # L-shape: two walls
            wall1_volume = wall_thickness * depth * height
            wall2_volume = width * wall_thickness * height
            overlap_volume = wall_thickness * wall_thickness * height
            volume = wall1_volume + wall2_volume - overlap_volume
        elif core_type == 'coupled':
            # Two separate walls
            wall_width = (width - 1.0) / 2  # Assuming 1m gap
            volume = 2 * wall_width * depth * height
        else:
            volume = width * depth * height  # Default to solid
        
        mass = volume * self.material_densities['reinforced_concrete']
        
        return {
            'width_m': width,
            'depth_m': depth,
            'height_m': height,
            'core_type': core_type,
            'wall_thickness_m': wall_thickness,
            'volume_m3': volume,
            'mass_kg': mass,
            'gravity_force_kN': mass * self.g / 1000
        }
    
    def _create_mass_summary(self, results):
        """Create a summary of mass calculations"""
        summary = {
            'steel_members_count': len(results['steel_members']),
            'concrete_members_count': len(results['concrete_members']),
            'total_mass_kg': results['total_masses']['structure_total_kg'],
            'total_gravity_force_kN': results['gravity_forces']['structure_total_kN'],
            'mass_distribution': {
                'steel_percentage': (results['total_masses']['steel_total_kg'] / 
                                   results['total_masses']['structure_total_kg'] * 100) if results['total_masses']['structure_total_kg'] > 0 else 0,
                'concrete_percentage': (results['total_masses']['concrete_total_kg'] / 
                                      results['total_masses']['structure_total_kg'] * 100) if results['total_masses']['structure_total_kg'] > 0 else 0
            }
        }
        
        return summary


# Create service instance
mass_calculator_service = MassCalculatorService()
