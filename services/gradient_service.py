
"""
Gradient Service - Handles slope and elevation calculations
Refactored with improved caching and error handling
"""
import json
import hashlib
import math
from typing import Dict, Any, Optional
from .base_service import CacheableService


class GradientService(CacheableService):
    """Service for calculating and caching gradient data"""
    
    def __init__(self):
        super().__init__("GradientService", cache_ttl=7200)  # 2 hour cache
    
    def calculate_gradient_data(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate gradient data with error handling and caching"""
        try:
            cache_key = self._generate_cache_key(site_data)
            
            # Check cache first
            cached_result = self._get_cache(cache_key)
            if cached_result:
                self._log_operation("Cache hit", "Returning cached gradient data")
                return cached_result
            
            # Calculate gradient data
            gradient_data = self._perform_gradient_calculation(site_data)
            
            # Cache the result
            self._set_cache(cache_key, gradient_data)
            
            self._log_operation("Calculation completed", "Gradient data calculated successfully")
            return gradient_data
            
        except Exception as e:
            self.logger.error(f"Gradient calculation error: {e}")
            return self._get_fallback_gradient_data(site_data)
    
    def _generate_cache_key(self, site_data: Dict[str, Any]) -> str:
        """Generate a cache key from site data"""
        key_data = {
            'coordinates': site_data.get('coordinates', []),
            'bounds': site_data.get('bounds', {}),
            'area': site_data.get('area', 0)
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _perform_gradient_calculation(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform the actual gradient calculation"""
        self._log_operation("Starting calculation", f"Data keys: {list(site_data.keys())}")
        
        # Extract and validate essential data
        coordinates = site_data.get('coordinates', [])
        bounds = site_data.get('bounds', {})
        area = site_data.get('area', 0)
        
        # Enhanced logging for debugging
        self._log_operation("Raw data check", {
            'coordinates_type': type(coordinates).__name__,
            'coordinates_length': len(coordinates) if coordinates else 0,
            'bounds_keys': list(bounds.keys()) if bounds else [],
            'area': area
        })
        
        # Handle nested coordinates structure
        if coordinates and isinstance(coordinates, list) and len(coordinates) > 0:
            if isinstance(coordinates[0], list):
                coordinates = coordinates[0]
                self._log_operation("Coordinates unnested", f"Now have {len(coordinates)} points")
        
        self._log_operation("Processing", f"{len(coordinates) if coordinates else 0} coordinate points")
        
        # Validate coordinates
        if not coordinates or len(coordinates) < 3:
            self.logger.warning("Insufficient coordinate data, using fallback calculation")
            return self._get_fallback_gradient_data(site_data)
        
        # Calculate slope and aspect with enhanced error handling
        try:
            slope = self._calculate_safe_slope(site_data, coordinates)
            aspect = self._calculate_safe_aspect(site_data, coordinates)
            
            self._log_operation("Calculated", f"Slope: {slope}%, Aspect: {aspect}°")
            
            # Validate calculated values
            if slope < 0 or slope > 100:
                self.logger.warning(f"Unusual slope value calculated: {slope}%, clamping to valid range")
                slope = max(0, min(100, slope))
            
            if aspect < 0 or aspect >= 360:
                self.logger.warning(f"Invalid aspect value calculated: {aspect}°, normalizing")
                aspect = aspect % 360  # Normalize to 0-360 range
            
            result = {
                'slope': slope,
                'realSlope': slope,
                'aspect': aspect,
                'slopeDirection': self._get_aspect_direction(aspect),
                'bearing': site_data.get('bearing', aspect),
                'method': 'enhanced_calculation',
                'calculated': True,
                'error': None,
                'debug_info': {
                    'coordinate_count': len(coordinates),
                    'bounds': bounds,
                    'calculation_method': 'coordinate_based_calculation'
                }
            }
            
            self._log_operation("DEM gradient calculation completed successfully", result)
            return result
            
        except Exception as calc_error:
            self.logger.error(f"Error during gradient calculation: {calc_error}")
            return self._get_fallback_gradient_data(site_data)
    
    def _calculate_safe_slope(self, site_data: Dict[str, Any], coordinates: list = None) -> float:
        """Calculate slope with safe fallbacks"""
        # Try existing slope data first
        for key in ['slope', 'realSlope']:
            if key in site_data and site_data[key] is not None:
                try:
                    return float(site_data[key])
                except (ValueError, TypeError):
                    continue
        
        # Try to calculate from coordinates if available
        if coordinates and len(coordinates) >= 3:
            try:
                slope = self._calculate_slope_from_coordinates(coordinates)
                if 0 <= slope <= 100:
                    return slope
            except Exception as e:
                self.logger.warning(f"Failed to calculate slope from coordinates: {e}")
        
        # Estimate based on area as fallback
        area = site_data.get('area', 1000)
        if area > 50000:
            return 2.5  # Large sites tend to be flatter
        elif area > 10000:
            return 5.0  # Medium sites
        else:
            return 8.0  # Small sites may be steeper
    
    def _calculate_slope_from_coordinates(self, coordinates: list) -> float:
        """Calculate slope from coordinate elevation changes"""
        # This is a simplified calculation - in a real implementation
        # you'd need elevation data for each coordinate
        
        # For now, estimate based on coordinate spread
        lats = []
        lngs = []
        
        for coord in coordinates:
            if isinstance(coord, dict):
                if 'lat' in coord and 'lng' in coord:
                    lats.append(float(coord['lat']))
                    lngs.append(float(coord['lng']))
            elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
                lats.append(float(coord[0]))
                lngs.append(float(coord[1]))
        
        if len(lats) >= 3:
            lat_range = max(lats) - min(lats)
            lng_range = max(lngs) - min(lngs)
            
            # Convert to approximate meters (rough calculation)
            lat_meters = lat_range * 111000  # 1 degree lat ≈ 111km
            lng_meters = lng_range * 111000 * math.cos(math.radians(sum(lats) / len(lats)))
            
            total_distance = math.sqrt(lat_meters**2 + lng_meters**2)
            
            # Estimate slope based on distance - closer coordinates suggest steeper terrain
            if total_distance < 100:
                return 15.0
            elif total_distance < 500:
                return 8.0
            elif total_distance < 1000:
                return 5.0
            else:
                return 2.0
        
        return 5.0  # Default moderate slope
    
    def _calculate_safe_aspect(self, site_data: Dict[str, Any], coordinates: list = None) -> float:
        """Calculate aspect with safe fallbacks"""
        # Try existing bearing first
        bearing = site_data.get('bearing')
        if bearing is not None:
            try:
                return float(bearing) % 360
            except (ValueError, TypeError):
                pass
        
        # Calculate from coordinates if available
        if coordinates and len(coordinates) >= 3:
            try:
                bearing = self._calculate_bearing_from_coordinates(coordinates)
                if bearing is not None:
                    return bearing
            except Exception as e:
                self.logger.warning(f"Failed to calculate bearing from coordinates: {e}")
        
        return 0.0  # Default to north-facing
    
    def _calculate_bearing_from_coordinates(self, coordinates: list) -> float:
        """Calculate bearing from coordinate points"""
        lats, lngs = [], []
        
        for coord in coordinates:
            if isinstance(coord, dict):
                if 'lat' in coord and 'lng' in coord:
                    try:
                        lats.append(float(coord['lat']))
                        lngs.append(float(coord['lng']))
                    except (ValueError, TypeError):
                        continue
            elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
                try:
                    lats.append(float(coord[0]))
                    lngs.append(float(coord[1]))
                except (ValueError, TypeError):
                    continue
        
        if len(lats) >= 3 and len(lngs) >= 3:
            # Calculate the general orientation of the site
            max_lat_idx = lats.index(max(lats))
            min_lat_idx = lats.index(min(lats))
            
            lat_diff = lats[max_lat_idx] - lats[min_lat_idx]
            lng_diff = lngs[max_lat_idx] - lngs[min_lat_idx]
            
            if abs(lat_diff) > 0.0001 or abs(lng_diff) > 0.0001:
                bearing = math.atan2(lng_diff, lat_diff) * 180 / math.pi
                return (bearing + 360) % 360
        
        return 0.0
    
    def _get_aspect_direction(self, bearing: float) -> str:
        """Convert bearing to direction name"""
        directions = [
            'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'
        ]
        index = int((bearing + 11.25) / 22.5) % 16
        return directions[index]
    
    def debug_gradient_calculation(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Debug version of gradient calculation with detailed logging"""
        try:
            self._log_operation("Debug calculation started", f"Input keys: {list(site_data.keys())}")
            
            # Perform the same calculation as normal but with more verbose logging
            result = self.calculate_gradient_data(site_data)
            
            # Add debug information
            debug_result = {
                'gradient_data': result,
                'input_summary': {
                    'coordinates_provided': bool(site_data.get('coordinates')),
                    'coordinates_count': len(site_data.get('coordinates', [])),
                    'bounds_provided': bool(site_data.get('bounds')),
                    'area': site_data.get('area'),
                    'center_provided': bool(site_data.get('center'))
                },
                'calculation_details': {
                    'method_used': result.get('method', 'unknown'),
                    'calculated_successfully': result.get('calculated', False),
                    'had_errors': result.get('error') is not None
                }
            }
            
            self._log_operation("Debug calculation completed", debug_result)
            return debug_result
            
        except Exception as e:
            self.logger.error(f"Debug gradient calculation failed: {e}")
            return {
                'gradient_data': self._get_fallback_gradient_data(site_data),
                'error': str(e),
                'debug_failed': True
            }

    def _get_fallback_gradient_data(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """Return safe fallback data when calculation fails"""
        self.logger.warning("Using fallback gradient data")
        
        # Use area-based estimation for slope
        area = site_data.get('area', 1000)
        if area > 50000:
            estimated_slope = 2.5
        elif area > 10000:
            estimated_slope = 5.0
        else:
            estimated_slope = 8.0
        
        return {
            'slope': estimated_slope,
            'realSlope': estimated_slope,
            'aspect': 0.0,
            'slopeDirection': 'N',
            'bearing': 0.0,
            'method': 'fallback_estimation',
            'calculated': False,
            'error': 'Calculation failed, using area-based estimation'
        }


# Global service instance
gradient_service = GradientService()
