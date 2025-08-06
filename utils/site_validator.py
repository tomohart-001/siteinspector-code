"""
Site Validation Utilities
Comprehensive validation for site inspector functionality
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import app_logger


class SiteValidationError(Exception):
    """Custom exception for site validation errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class SiteValidator:
    """Site data validation utilities"""
    
    @staticmethod
    def validate_site_data(site_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate site data structure and required fields"""
        errors = []
        
        if not site_data:
            errors.append("Site data is required")
            return False, errors
            
        # Check required fields
        required_fields = ['coordinates', 'area', 'center']
        for field in required_fields:
            if field not in site_data:
                errors.append(f"Missing required field: {field}")
                
        # Validate coordinates
        coordinates = site_data.get('coordinates')
        if coordinates:
            if not isinstance(coordinates, list) or len(coordinates) == 0:
                errors.append("Coordinates must be a non-empty list")
            elif len(coordinates[0]) < 3:
                errors.append("Site must have at least 3 coordinate points")
                
        # Validate area
        area = site_data.get('area')
        if area is not None and (not isinstance(area, (int, float)) or area <= 0):
            errors.append("Area must be a positive number")
            
        return len(errors) == 0, errors
        
    @staticmethod
    def validate_edge_classifications(edge_classifications: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate edge classifications"""
        errors = []
        
        if not edge_classifications:
            errors.append("Edge classifications are required")
            return False, errors
            
        valid_types = ['front', 'side', 'rear', 'other', None]
        
        for i, edge in enumerate(edge_classifications):
            if not isinstance(edge, dict):
                errors.append(f"Edge {i} must be a dictionary")
                continue
                
            edge_type = edge.get('type')
            if edge_type not in valid_types:
                errors.append(f"Edge {i} has invalid type: {edge_type}")
                
        return len(errors) == 0, errors


class BuildableAreaValidator:
    """Buildable area calculation validation"""
    
    @staticmethod
    def validate_buildable_area_inputs(coords: List, requirements: Dict, frontage: str, edge_classifications: List) -> Tuple[bool, List[str]]:
        """Validate buildable area calculation inputs"""
        errors = []
        
        if not coords or len(coords) < 3:
            errors.append("At least 3 coordinate points are required")
            
        if not requirements:
            errors.append("Council requirements are required")
            
        if frontage and frontage not in ['north', 'south', 'east', 'west', 'auto']:
            errors.append(f"Invalid frontage direction: {frontage}")
            
        return len(errors) == 0, errors
        
    @staticmethod
    def validate_buildable_area_result(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate buildable area calculation result"""
        errors = []
        
        if not result:
            errors.append("Result is required")
            return False, errors
            
        if 'buildable_area_m2' not in result:
            errors.append("Result must include buildable_area_m2")
            
        buildable_area = result.get('buildable_area_m2')
        if buildable_area is not None and (not isinstance(buildable_area, (int, float)) or buildable_area < 0):
            errors.append("Buildable area must be a non-negative number")
            
        return len(errors) == 0, errors


def create_validation_response(is_valid: bool, errors: List[str], data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a standardized validation response"""
    response = {
        'valid': is_valid,
        'errors': errors
    }
    
    if data:
        response['data'] = data
        
    return response


class SiteValidator:
    """Comprehensive site data validation"""

    @staticmethod
    def validate_site_data(site_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete site data structure"""
        errors = []

        if not site_data:
            errors.append("Site data is empty or None")
            return False, errors

        # Validate required fields
        required_fields = ['coordinates', 'center', 'area', 'type']
        for field in required_fields:
            if field not in site_data:
                errors.append(f"Missing required field: {field}")

        # Validate coordinates
        coords_valid, coords_errors = SiteValidator.validate_coordinates(
            site_data.get('coordinates', [])
        )
        if not coords_valid:
            errors.extend(coords_errors)

        # Validate center point
        center_valid, center_errors = SiteValidator.validate_center_point(
            site_data.get('center', {})
        )
        if not center_valid:
            errors.extend(center_errors)

        # Validate area
        area_valid, area_errors = SiteValidator.validate_area(
            site_data.get('area', 0)
        )
        if not area_valid:
            errors.extend(area_errors)

        return len(errors) == 0, errors

    @staticmethod
    def validate_coordinates(coordinates) -> Tuple[bool, List[str]]:
        """Validate coordinate data structure and values"""
        errors = []

        if not coordinates:
            errors.append("No coordinates provided")
            return False, errors

        # Handle nested coordinate arrays
        coords_to_check = coordinates
        if isinstance(coordinates[0], list) and len(coordinates) == 1:
            coords_to_check = coordinates[0]
        elif isinstance(coordinates[0], list) and len(coordinates) > 1:
            # This is already a flat list of coordinate pairs
            coords_to_check = coordinates

        if len(coords_to_check) < 3:
            errors.append("At least 3 coordinate points required for a polygon")
            return False, errors

        if len(coords_to_check) > 100:
            errors.append("Too many coordinate points (max 100)")
            return False, errors

        # Validate each coordinate point
        for i, coord in enumerate(coords_to_check):
            coord_valid, coord_errors = SiteValidator.validate_coordinate_point(coord, i)
            if not coord_valid:
                errors.extend(coord_errors)

        # Check if polygon is closed (first and last points should be close)
        if len(coords_to_check) > 2:
            first = coords_to_check[0]
            last = coords_to_check[-1]
            if isinstance(first, dict) and isinstance(last, dict):
                lat_diff = abs(first.get('lat', 0) - last.get('lat', 0))
                lng_diff = abs(first.get('lng', 0) - last.get('lng', 0))
                if lat_diff > 0.001 or lng_diff > 0.001:
                    app_logger.warning("Polygon may not be properly closed")

        return len(errors) == 0, errors

    @staticmethod
    def validate_coordinate_point(coord: Any, index: int) -> Tuple[bool, List[str]]:
        """Validate individual coordinate point"""
        errors = []

        if not coord:
            errors.append(f"Coordinate {index} is null or empty")
            return False, errors

        if isinstance(coord, dict):
            # Dictionary format: {'lat': x, 'lng': y}
            if 'lat' not in coord or 'lng' not in coord:
                errors.append(f"Coordinate {index} missing lat or lng")
                return False, errors

            lat, lng = coord['lat'], coord['lng']
        elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
            # Array format: [lng, lat] for GeoJSON style or [lat, lng] for traditional
            # Check if first value looks like longitude (larger absolute value often indicates lng)
            if abs(coord[0]) > abs(coord[1]) and abs(coord[0]) > 90:
                # Likely [lng, lat] format
                lng, lat = coord[0], coord[1]
            else:
                # Likely [lat, lng] format
                lat, lng = coord[0], coord[1]
        else:
            errors.append(f"Coordinate {index} has invalid format")
            return False, errors

        # Validate latitude
        if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
            errors.append(f"Coordinate {index} has invalid latitude: {lat}")

        # Validate longitude
        if not isinstance(lng, (int, float)) or lng < -180 or lng > 180:
            errors.append(f"Coordinate {index} has invalid longitude: {lng}")

        # Global coordinate validation - no geographic restrictions needed

        return len(errors) == 0, errors

    @staticmethod
    def validate_center_point(center: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate center point"""
        errors = []

        if not center:
            errors.append("Center point is required")
            return False, errors

        if 'lat' not in center or 'lng' not in center:
            errors.append("Center point missing lat or lng")
            return False, errors

        lat, lng = center['lat'], center['lng']

        if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
            errors.append(f"Center latitude invalid: {lat}")

        if not isinstance(lng, (int, float)) or lng < -180 or lng > 180:
            errors.append(f"Center longitude invalid: {lng}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_area(area: Any) -> Tuple[bool, List[str]]:
        """Validate site area"""
        errors = []

        if not isinstance(area, (int, float)):
            errors.append(f"Area must be a number, got: {type(area)}")
            return False, errors

        if area <= 0:
            errors.append(f"Area must be positive, got: {area}")

        if area > 1000000000:  # 1 billion m²
            errors.append(f"Area too large (max 1 billion m²): {area}")

        if area < 1:  # 1 m²
            errors.append(f"Area too small (min 1 m²): {area}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_edge_classifications(edge_classifications: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate edge classifications"""
        errors = []

        if not edge_classifications:
            errors.append("Edge classifications are required")
            return False, errors

        if not isinstance(edge_classifications, list):
            errors.append("Edge classifications must be a list")
            return False, errors

        valid_types = ['street_frontage', 'side', 'rear']

        for i, edge in enumerate(edge_classifications):
            if not isinstance(edge, dict):
                errors.append(f"Edge {i} must be a dictionary")
                continue

            if 'type' not in edge and 'classification' not in edge:
                errors.append(f"Edge {i} missing type or classification")
                continue

            edge_type = edge.get('type') or edge.get('classification')
            
            # Skip validation for edges that haven't been classified yet (None type)
            if edge_type is None:
                continue
                
            if edge_type not in valid_types:
                errors.append(f"Edge {i} has invalid type: {edge_type}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_council_requirements(requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate council requirements"""
        errors = []

        if not requirements:
            errors.append("Council requirements are required")
            return False, errors

        required_setbacks = ['front_setback', 'side_setback', 'rear_setback']
        for setback in required_setbacks:
            if setback not in requirements:
                errors.append(f"Missing required setback: {setback}")
                continue

            value = requirements[setback]
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"Invalid {setback} value: {value}")

        return len(errors) == 0, errors


class MapValidator:
    """Map-specific validation utilities"""

    @staticmethod
    def validate_map_initialization(map_container_id: str = 'inspectorMap') -> Dict[str, Any]:
        """Validate map can be initialized"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # This would typically check DOM elements, but since we're server-side,
        # we'll focus on data validation
        app_logger.info(f"Validating map initialization for container: {map_container_id}")

        return validation_result

    @staticmethod
    def validate_leaflet_dependencies() -> Dict[str, Any]:
        """Validate Leaflet map dependencies"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check if required JavaScript libraries are available
        # This is more of a client-side check, but we can log expectations
        app_logger.info("Validating Leaflet dependencies")

        return validation_result


class BuildableAreaValidator:
    """Buildable area calculation validation"""

    @staticmethod
    def validate_buildable_area_inputs(site_coords: List, requirements: Dict, 
                                     frontage: str = None, 
                                     edge_classifications: List = None) -> Tuple[bool, List[str]]:
        """Validate inputs for buildable area calculation"""
        errors = []

        # Validate site coordinates
        coords_valid, coords_errors = SiteValidator.validate_coordinates(site_coords)
        if not coords_valid:
            errors.extend([f"Site coords: {err}" for err in coords_errors])

        # Validate requirements
        req_valid, req_errors = SiteValidator.validate_council_requirements(requirements)
        if not req_valid:
            errors.extend([f"Requirements: {err}" for err in req_errors])

        # Validate edge classifications if provided
        if edge_classifications:
            edge_valid, edge_errors = SiteValidator.validate_edge_classifications(edge_classifications)
            if not edge_valid:
                errors.extend([f"Edge classifications: {err}" for err in edge_errors])

        # Validate frontage if provided
        if frontage and frontage not in ['auto', 'north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest']:
            errors.append(f"Invalid frontage direction: {frontage}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_buildable_area_result(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate buildable area calculation result"""
        errors = []
        warnings = []

        if not result:
            errors.append("Buildable area result is empty")
            return False, errors

        # Check for error in result
        if 'error' in result:
            errors.append(f"Calculation error: {result['error']}")

        # Validate buildable area value
        buildable_area = result.get('buildable_area_m2', 0)
        if not isinstance(buildable_area, (int, float)):
            errors.append(f"Invalid buildable area type: {type(buildable_area)}")
        elif buildable_area < 0:
            errors.append(f"Negative buildable area: {buildable_area}")
        elif buildable_area == 0:
            warnings.append("Buildable area is zero - check setback values")

        # Validate coordinates if present
        buildable_coords = result.get('buildable_coords', [])
        if buildable_coords:
            coords_valid, coords_errors = SiteValidator.validate_coordinates(buildable_coords)
            if not coords_valid:
                errors.extend([f"Buildable coords: {err}" for err in coords_errors])

        # Log warnings
        for warning in warnings:
            app_logger.warning(warning)

        return len(errors) == 0, errors + warnings


def create_validation_response(valid: bool, errors: List[str], data: Dict = None) -> Dict[str, Any]:
    """Create standardized validation response"""
    return {
        'valid': valid,
        'errors': errors,
        'data': data or {},
        'error_count': len(errors)
    }


def log_validation_result(operation: str, valid: bool, errors: List[str]):
    """Log validation results consistently"""
    if valid:
        app_logger.info(f"Validation passed: {operation}")
    else:
        app_logger.error(f"Validation failed: {operation} - Errors: {errors}")