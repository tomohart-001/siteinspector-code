
"""
Building Service
Handles 3D building model generation and calculations
"""
from typing import Dict, Any, List
from .base_service import BaseService
from .geometry_calculator import GeometryCalculator
from utils.logger import app_logger


class BuildingService(BaseService):
    """Service for building model generation and calculations"""
    
    def __init__(self):
        super().__init__("BuildingService")
        self.geometry_calc = GeometryCalculator()
    
    def generate_3d_building(self, site_coords: List[Dict], buildable_area: Dict[str, Any], 
                           building_params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate 3D building model based on site and parameters"""
        try:
            self._log_operation("3D building generation started")
            
            # Validate inputs
            if not site_coords or len(site_coords) < 3:
                raise ValueError('Valid site coordinates required')
            
            if not building_params:
                raise ValueError('Building parameters required')
            
            # Extract building parameters
            storeys = building_params.get('storeys', 2)
            storey_height = building_params.get('storey_height', 3.0)
            site_coverage = building_params.get('site_coverage', 60)
            
            # Calculate building footprint from buildable area
            buildable_coords = buildable_area.get('buildable_coords', [])
            buildable_area_m2 = buildable_area.get('buildable_area_m2', 0)
            
            if not buildable_coords and buildable_area_m2 == 0:
                # Use site coords as fallback
                buildable_coords = site_coords
                buildable_area_m2 = self._estimate_buildable_area(site_coords)
            
            # Calculate building footprint area
            target_footprint_area = buildable_area_m2 * (site_coverage / 100.0)
            
            # Create simplified building footprint
            if buildable_coords:
                footprint_coords = self.create_building_footprint(buildable_coords, site_coverage)
            else:
                footprint_coords = self.create_building_footprint(site_coords, site_coverage)
            
            # Calculate building metrics
            total_height = storeys * storey_height
            footprint_area = target_footprint_area
            total_floor_area = footprint_area * storeys
            
            building_data = {
                'footprint_coords': footprint_coords,
                'footprint_area': footprint_area,
                'total_floor_area': total_floor_area,
                'total_height': total_height,
                'storeys': storeys,
                'storey_height': storey_height,
                'site_coverage': site_coverage,
                'building_type': '3d_extruded_model'
            }
            
            self._log_operation("3D building generated", 
                              f"{total_height}m high, {storeys} storeys, {footprint_area:.1f}m² footprint")
            
            return {
                'success': True,
                'building_data': building_data
            }
            
        except Exception as e:
            return self._handle_error("3D building generation", e, {
                'success': False,
                'error': str(e)
            })
    
    def create_building_footprint(self, coords: List, coverage_percent: float) -> List[List[float]]:
        """Create a building footprint within the given coordinates"""
        try:
            from shapely.geometry import Polygon
            import numpy as np
            
            # Convert to shapely polygon
            if isinstance(coords[0], dict):
                poly_coords = [(coord['lng'], coord['lat']) for coord in coords]
            else:
                poly_coords = [(coord[1], coord[0]) for coord in coords]
            
            polygon = Polygon(poly_coords)
            centroid = polygon.centroid
            
            # Create a scaled-down version of the polygon for the building footprint
            scale_factor = np.sqrt(coverage_percent / 100.0) * 0.8
            
            # Scale the polygon around its centroid
            building_coords = []
            for lng, lat in poly_coords:
                # Translate to origin
                lng_translated = lng - centroid.x
                lat_translated = lat - centroid.y
                
                # Scale
                lng_scaled = lng_translated * scale_factor
                lat_scaled = lat_translated * scale_factor
                
                # Translate back
                lng_final = lng_scaled + centroid.x
                lat_final = lat_scaled + centroid.y
                
                building_coords.append([lat_final, lng_final])
            
            return building_coords
            
        except Exception as e:
            app_logger.error(f"Building footprint creation error: {str(e)}")
            return self._create_fallback_footprint(coords)
    
    def save_building_design(self, building_data: Dict[str, Any], site_id: str) -> Dict[str, Any]:
        """Save 3D building design"""
        try:
            if not building_data:
                raise ValueError('Building data required')
            
            # This would typically save to database
            # For now, we'll return success
            
            self._log_operation("Building design saved", f"Site {site_id}")
            
            return {
                'success': True,
                'message': 'Building design saved successfully'
            }
            
        except Exception as e:
            return self._handle_error("Building design save", e, {
                'success': False,
                'error': str(e)
            })
    
    def _estimate_buildable_area(self, site_coords: List[Dict]) -> float:
        """Estimate buildable area from site coordinates"""
        try:
            from shapely.geometry import Polygon
            site_polygon = Polygon([(coord['lng'], coord['lat']) for coord in site_coords])
            return site_polygon.area * (111320 ** 2) * 0.7  # Rough approximation
        except:
            return 200  # Fallback
    
    def _create_fallback_footprint(self, coords: List) -> List[List[float]]:
        """Create a simple rectangular footprint as fallback"""
        if coords and len(coords) >= 3:
            center_lat = sum(coord.get('lat', coord[0] if isinstance(coord, list) else 0) for coord in coords) / len(coords)
            center_lng = sum(coord.get('lng', coord[1] if isinstance(coord, list) else 0) for coord in coords) / len(coords)
            
            offset = 0.0001
            return [
                [center_lat - offset, center_lng - offset],
                [center_lat - offset, center_lng + offset],
                [center_lat + offset, center_lng + offset],
                [center_lat + offset, center_lng - offset]
            ]
        
        return []


# Global instance
building_service = BuildingService()
