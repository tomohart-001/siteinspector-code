
"""
API Calculation Service
Handles complex calculations extracted from routes
"""
from typing import Dict, Any, List, Optional
from .base_service import BaseService
from . import council_service
import time


class ApiCalculationService(BaseService):
    """Service for API calculation operations"""
    
    def __init__(self):
        super().__init__("ApiCalculationService")
    
    def calculate_buildable_area(self, site_coords: List[Dict], requirements: Dict, 
                               frontage: Optional[str] = None, 
                               edge_classifications: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Calculate buildable area with comprehensive validation and logging"""
        try:
            self._log_operation("Buildable area calculation started")
            
            if not site_coords or not requirements:
                raise ValueError("Site coordinates and requirements are required")
            
            # Use council service for actual calculation
            result = council_service.calculate_buildable_area(
                site_coords=site_coords,
                requirements=requirements,
                frontage=frontage,
                edge_classifications=edge_classifications
            )
            
            # Log calculation details
            calculation_method = result.get('calculation_method', 'unknown')
            site_area = result.get('site_area_m2', 0)
            buildable_area = result.get('buildable_area_m2', 0)
            
            self._log_operation(
                "Buildable area calculation completed",
                f"Site: {site_area:.0f}m², Buildable: {buildable_area:.0f}m², Method: {calculation_method}"
            )
            
            return result
            
        except Exception as e:
            return self._handle_error("Buildable area calculation", e, {
                'error': str(e),
                'site_area_m2': 0,
                'buildable_area_m2': 0,
                'calculation_method': 'error'
            })
    
    def enhance_site_data(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance site data with calculations and external data"""
        try:
            self._log_operation("Site data enhancement started")
            
            enhanced_data = site_data.copy()
            
            # Calculate gradient data
            from . import gradient_service
            gradient_data = gradient_service.calculate_gradient_data(site_data)
            enhanced_data.update(gradient_data)
            
            # Get council requirements and calculate buildable area
            council_name = enhanced_data.get('council', '')
            zoning = enhanced_data.get('zoning', 'residential')
            
            if council_name:
                self._log_operation("Council requirements lookup", f"{council_name}, zoning: {zoning}")
                council_requirements = council_service.get_council_requirements(council_name, zoning)
                enhanced_data['council_requirements'] = council_requirements
                
                # Calculate buildable area if coordinates available
                coordinates = enhanced_data.get('coordinates', [])
                if coordinates and len(coordinates) > 0:
                    coords_to_use = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                    buildable_data = self.calculate_buildable_area(coords_to_use, council_requirements)
                    enhanced_data['buildable_area'] = buildable_data
                    
                    buildable_area_m2 = buildable_data.get('buildable_area_m2', 0)
                    self._log_operation("Buildable area calculated", f"{buildable_area_m2:.1f} m²")
            
            self._log_operation("Site data enhancement completed")
            return enhanced_data
            
        except Exception as e:
            return self._handle_error("Site data enhancement", e, site_data)
    
    def process_edge_selection(self, selected_edges: List[Dict], site_id: str) -> Dict[str, Any]:
        """Process and validate edge selection data"""
        try:
            self._log_operation("Edge selection processing", f"Site {site_id}: {len(selected_edges)} edges")
            
            return {
                'selectedEdges': selected_edges,
                'siteId': site_id,
                'timestamp': time.time(),
                'edge_count': len(selected_edges),
                'processed': True
            }
            
        except Exception as e:
            return self._handle_error("Edge selection processing", e, {
                'selectedEdges': [],
                'siteId': site_id,
                'error': str(e)
            })
    
    def process_edge_classifications(self, edge_classifications: List[Dict], site_id: str) -> Dict[str, Any]:
        """Process and validate edge classifications"""
        try:
            self._log_operation("Edge classifications processing", f"Site {site_id}")
            
            if not edge_classifications:
                raise ValueError("Edge classifications are required")
            
            total_edges = len(edge_classifications)
            classified_edges = [edge for edge in edge_classifications 
                              if edge.get('type') in ['street_frontage', 'side', 'rear']]
            
            if len(classified_edges) != total_edges:
                raise ValueError("All edges must be classified as street frontage, side, or rear")
            
            frontage_edges = [edge for edge in edge_classifications 
                            if edge.get('type') == 'street_frontage']
            if not frontage_edges:
                raise ValueError("At least one edge must be classified as street frontage")
            
            classifications_summary = [(i, edge.get('type')) for i, edge in enumerate(edge_classifications)]
            self._log_operation("Edge classifications validated", f"Classifications: {classifications_summary}")
            
            return {
                'edgeClassifications': edge_classifications,
                'siteId': site_id,
                'confirmed': True,
                'timestamp': time.time(),
                'total_edges': total_edges,
                'frontage_edges': len(frontage_edges)
            }
            
        except Exception as e:
            return self._handle_error("Edge classifications processing", e, {
                'edgeClassifications': [],
                'siteId': site_id,
                'error': str(e)
            })


# Global instance
api_calculation_service = ApiCalculationService()
