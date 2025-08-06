
"""
Earthworks Service - Handles cut/fill calculations for building platforms
"""
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from .base_service import BaseService

# Try to import geospatial dependencies with graceful fallback
try:
    from shapely.geometry import Polygon, Point
    from shapely.ops import transform as shapely_transform
    from pyproj import Transformer
    import rasterio
    from scipy import interpolate
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False


class EarthworksService(BaseService):
    """Service for calculating earthworks (cut/fill) for building platforms"""

    def __init__(self):
        super().__init__("EarthworksService")
        self.available = GEOSPATIAL_AVAILABLE

        if self.available:
            self.logger.info("Earthworks service initialized successfully")
        else:
            self.logger.warning("Earthworks service unavailable - missing geospatial dependencies")

    def calculate_earthworks(self, terrain_data: Dict[str, Any], platform_coords: List[List[float]], 
                           ffl: Optional[float] = None, optimize_ffl: bool = False) -> Dict[str, Any]:
        """Calculate cut/fill volumes for a building platform"""
        try:
            if not self.available:
                return {
                    'success': False,
                    'error': 'Earthworks calculation requires geospatial libraries'
                }

            self.logger.info(f"Starting earthworks calculation - platform coords: {len(platform_coords)} points")
            
            # Validate inputs
            if not terrain_data or 'elevation_data' not in terrain_data:
                return {'success': False, 'error': 'Valid terrain data required'}
            
            if not platform_coords or len(platform_coords) < 3:
                return {'success': False, 'error': 'Platform requires at least 3 coordinate points'}

            # Extract terrain data
            elevation_data = np.array(terrain_data['elevation_data'])
            x_coords = np.array(terrain_data['x_coords'])
            y_coords = np.array(terrain_data['y_coords'])
            base_level = terrain_data.get('base_level', 0)
            
            self.logger.info(f"Terrain data: {elevation_data.shape}, base level: {base_level}")

            # Convert platform coordinates to local coordinate system
            platform_local = self._convert_platform_to_local(platform_coords, terrain_data)
            if not platform_local:
                return {'success': False, 'error': 'Failed to convert platform coordinates'}

            # Create platform polygon
            platform_polygon = Polygon(platform_local)
            platform_bounds = platform_polygon.bounds
            
            self.logger.info(f"Platform bounds: {platform_bounds}")
            self.logger.info(f"Platform area: {platform_polygon.area:.2f}")
            
            # Validate polygon is not degenerate
            if platform_polygon.area < 1.0:  # Less than 1 square meter
                return {
                    'success': False, 
                    'error': f'Platform polygon is degenerate (area: {platform_polygon.area:.2f}m²). Check coordinate conversion.'
                }

            # Create interpolation function for terrain elevation
            terrain_interpolator = self._create_terrain_interpolator(x_coords, y_coords, elevation_data)
            
            # Calculate or optimize FFL
            if optimize_ffl:
                ffl = self._calculate_optimal_ffl(platform_polygon, terrain_interpolator)
                self.logger.info(f"Optimized FFL: {ffl:.2f}m")
            elif ffl is None:
                # Use average elevation within platform as default
                ffl = self._calculate_average_elevation(platform_polygon, terrain_interpolator)
                self.logger.info(f"Default FFL (average): {ffl:.2f}m")
            else:
                self.logger.info(f"User-specified FFL: {ffl:.2f}m")

            # Calculate cut/fill volumes
            cut_fill_result = self._calculate_cut_fill_volumes(
                platform_polygon, terrain_interpolator, ffl, resolution=1.0
            )

            # Create visualisation data
            visualisation_data = self._create_visualisation_data(
                platform_polygon, ffl, cut_fill_result, terrain_data
            )

            result = {
                'success': True,
                'platform_coords': platform_coords,
                'platform_local_coords': platform_local,
                'ffl': ffl,
                'ffl_relative_to_base': ffl + base_level,
                'cut_volume_m3': cut_fill_result['cut_volume'],
                'fill_volume_m3': cut_fill_result['fill_volume'],
                'net_earthwork_m3': cut_fill_result['net_volume'],
                'platform_area_m2': platform_polygon.area,
                'earthwork_type': 'net_cut' if cut_fill_result['net_volume'] > 0 else 'net_fill',
                'cut_fill_grid': cut_fill_result['grid_data'],
                'visualization_data': visualisation_data,
                'calculation_details': {
                    'grid_resolution_m': 1.0,
                    'calculation_method': 'interpolated_grid',
                    'optimized_ffl': optimize_ffl
                }
            }

            self._log_operation("Earthworks calculated", 
                              f"Cut: {cut_fill_result['cut_volume']:.1f}m³, Fill: {cut_fill_result['fill_volume']:.1f}m³")

            return result

        except Exception as e:
            self.logger.error(f"Earthworks calculation failed: {e}")
            return {'success': False, 'error': str(e)}

    def _convert_platform_to_local(self, platform_coords: List[List[float]], terrain_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Convert platform coordinates to local terrain coordinate system"""
        try:
            # Get terrain coordinate ranges
            x_coords = np.array(terrain_data['x_coords'])
            y_coords = np.array(terrain_data['y_coords'])
            
            x_min, x_max = x_coords.min(), x_coords.max()
            y_min, y_max = y_coords.min(), y_coords.max()
            
            platform_local = []
            self.logger.info(f"Converting {len(platform_coords)} platform coordinates from: {platform_coords}")
            self.logger.info(f"Terrain coordinate ranges: x({x_min:.1f} to {x_max:.1f}), y({y_min:.1f} to {y_max:.1f})")
            
            for i, coord in enumerate(platform_coords):
                if isinstance(coord, dict):
                    # Dictionary format with x, y keys (from buildable area or relative coordinates)
                    x_val = coord.get('x', 0)
                    y_val = coord.get('y', 0)
                    self.logger.info(f"Coord {i}: dict format x={x_val}, y={y_val}")
                    
                    # Check if these are lat/lng coordinates (buildable area format)
                    if abs(x_val) > 2 and abs(y_val) > 2:  # Likely lat/lng coordinates
                        self.logger.info(f"Processing lat/lng coordinate: lng={x_val}, lat={y_val}")
                        
                        # Get site coordinates for reference - use the first site coordinate as reference point
                        site_coords = terrain_data.get('coordinates', {})
                        if site_coords and hasattr(site_coords, 'get'):
                            ref_lat = site_coords.get('lat', -41.28)
                            ref_lng = site_coords.get('lng', 174.73)
                        else:
                            # Fallback to approximate center of Wellington
                            ref_lat = -41.28
                            ref_lng = 174.73
                        
                        self.logger.info(f"Using reference point: lat={ref_lat}, lng={ref_lng}")
                        
                        # Convert lat/lng difference to meters (approximate)
                        # 1 degree longitude ≈ 111320 * cos(lat) meters
                        # 1 degree latitude ≈ 111320 meters
                        lat_diff = y_val - ref_lat
                        lng_diff = x_val - ref_lng
                        
                        # Convert to approximate meters
                        import math
                        y_meters = lat_diff * 111320
                        x_meters = lng_diff * 111320 * math.cos(math.radians(ref_lat))
                        
                        self.logger.info(f"Coordinate offset in meters: x={x_meters:.1f}m, y={y_meters:.1f}m")
                        
                        # Convert meters to relative coordinates within terrain bounds
                        terrain_width = x_max - x_min
                        terrain_height = y_max - y_min
                        
                        # Place relative to terrain center with offset
                        x_rel = 0.5 + (x_meters / terrain_width)
                        y_rel = 0.5 + (y_meters / terrain_height)
                        
                        self.logger.info(f"Calculated relative coordinates: x_rel={x_rel:.3f}, y_rel={y_rel:.3f}")
                        self.logger.info(f"Terrain dimensions: width={terrain_width:.1f}m, height={terrain_height:.1f}m")
                    else:
                        # Assume relative coordinates (0-1 range)
                        x_rel = x_val
                        y_rel = y_val
                        
                else:
                    # List format [x, y] or [lng, lat]
                    x_val = coord[0] if len(coord) > 0 else 0
                    y_val = coord[1] if len(coord) > 1 else 0
                    self.logger.info(f"Coord {i}: list format x={x_val}, y={y_val}")
                    
                    # Check if these are lat/lng coordinates
                    if abs(x_val) > 2 and abs(y_val) > 2:  # Likely lat/lng coordinates
                        self.logger.info(f"Processing lat/lng coordinate (list): lng={x_val}, lat={y_val}")
                        
                        # Get site coordinates for reference
                        site_coords = terrain_data.get('coordinates', {})
                        if site_coords and hasattr(site_coords, 'get'):
                            ref_lat = site_coords.get('lat', -41.28)
                            ref_lng = site_coords.get('lng', 174.73)
                        else:
                            ref_lat = -41.28
                            ref_lng = 174.73
                        
                        # Convert lat/lng difference to meters
                        lat_diff = y_val - ref_lat
                        lng_diff = x_val - ref_lng
                        
                        import math
                        y_meters = lat_diff * 111320
                        x_meters = lng_diff * 111320 * math.cos(math.radians(ref_lat))
                        
                        # Convert meters to relative coordinates within terrain bounds
                        terrain_width = x_max - x_min
                        terrain_height = y_max - y_min
                        
                        x_rel = 0.5 + (x_meters / terrain_width)
                        y_rel = 0.5 + (y_meters / terrain_height)
                        
                        self.logger.info(f"List format - relative coordinates: x_rel={x_rel:.3f}, y_rel={y_rel:.3f}")
                    else:
                        # Assume relative coordinates
                        x_rel = x_val
                        y_rel = y_val
                
                # Convert to local terrain coordinates
                # Ensure we have valid relative coordinates (0-1 range)
                x_rel = max(0.0, min(1.0, x_rel))
                y_rel = max(0.0, min(1.0, y_rel))
                
                x_local = x_min + (x_rel * (x_max - x_min))
                y_local = y_min + (y_rel * (y_max - y_min))
                
                self.logger.info(f"Coordinate conversion: rel({x_rel:.3f}, {y_rel:.3f}) -> local({x_local:.1f}, {y_local:.1f})")
                platform_local.append((x_local, y_local))
            
            self.logger.info(f"Converted {len(platform_coords)} platform coordinates to local system")
            return platform_local
            
        except Exception as e:
            self.logger.error(f"Failed to convert platform coordinates: {e}")
            return []

    def _create_terrain_interpolator(self, x_coords: np.ndarray, y_coords: np.ndarray, elevation_data: np.ndarray):
        """Create interpolation function for terrain elevation"""
        try:
            # Flatten coordinate arrays
            x_flat = x_coords.flatten()
            y_flat = y_coords.flatten()
            z_flat = elevation_data.flatten()
            
            # Remove NaN values
            valid_mask = ~np.isnan(z_flat)
            x_valid = x_flat[valid_mask]
            y_valid = y_flat[valid_mask]
            z_valid = z_flat[valid_mask]
            
            # Create interpolator
            interpolator = interpolate.LinearNDInterpolator(
                np.column_stack([x_valid, y_valid]), z_valid, fill_value=np.nan
            )
            
            return interpolator
            
        except Exception as e:
            self.logger.error(f"Failed to create terrain interpolator: {e}")
            return None

    def _calculate_optimal_ffl(self, platform_polygon: Polygon, terrain_interpolator) -> float:
        """Calculate optimal FFL that minimizes total cut+fill volume"""
        try:
            # Sample elevations within platform
            bounds = platform_polygon.bounds
            x_samples = np.linspace(bounds[0], bounds[2], 20)
            y_samples = np.linspace(bounds[1], bounds[3], 20)
            
            elevations = []
            for x in x_samples:
                for y in y_samples:
                    point = Point(x, y)
                    if platform_polygon.contains(point):
                        elevation = terrain_interpolator(x, y)
                        if not np.isnan(elevation):
                            elevations.append(elevation)
            
            if elevations:
                # Use median as optimal FFL (minimizes total earthwork)
                return float(np.median(elevations))
            else:
                return 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to calculate optimal FFL: {e}")
            return 0.0

    def _calculate_average_elevation(self, platform_polygon: Polygon, terrain_interpolator) -> float:
        """Calculate average elevation within platform"""
        try:
            bounds = platform_polygon.bounds
            x_samples = np.linspace(bounds[0], bounds[2], 10)
            y_samples = np.linspace(bounds[1], bounds[3], 10)
            
            elevations = []
            for x in x_samples:
                for y in y_samples:
                    point = Point(x, y)
                    if platform_polygon.contains(point):
                        elevation = terrain_interpolator(x, y)
                        if not np.isnan(elevation):
                            elevations.append(elevation)
            
            return float(np.mean(elevations)) if elevations else 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to calculate average elevation: {e}")
            return 0.0

    def _calculate_cut_fill_volumes(self, platform_polygon: Polygon, terrain_interpolator, 
                                  ffl: float, resolution: float = 1.0) -> Dict[str, Any]:
        """Calculate cut/fill volumes using grid method"""
        try:
            bounds = platform_polygon.bounds
            
            # Create grid
            x_range = np.arange(bounds[0], bounds[2] + resolution, resolution)
            y_range = np.arange(bounds[1], bounds[3] + resolution, resolution)
            
            cut_volume = 0.0
            fill_volume = 0.0
            grid_data = []
            
            for i, x in enumerate(x_range[:-1]):
                grid_row = []
                for j, y in enumerate(y_range[:-1]):
                    # Create cell polygon
                    cell_coords = [
                        (x, y),
                        (x + resolution, y),
                        (x + resolution, y + resolution),
                        (x, y + resolution)
                    ]
                    cell_polygon = Polygon(cell_coords)
                    
                    # Check if cell intersects with platform
                    intersection = cell_polygon.intersection(platform_polygon)
                    if intersection.area > 0:
                        # Calculate center point elevation
                        center_x = x + resolution / 2
                        center_y = y + resolution / 2
                        terrain_elevation = terrain_interpolator(center_x, center_y)
                        
                        if not np.isnan(terrain_elevation):
                            # Calculate cut/fill depth
                            depth_diff = terrain_elevation - ffl
                            cell_area = intersection.area
                            
                            if depth_diff > 0:  # Cut required
                                cut_volume += depth_diff * cell_area
                            else:  # Fill required
                                fill_volume += abs(depth_diff) * cell_area
                            
                            grid_row.append({
                                'x': center_x,
                                'y': center_y,
                                'terrain_elevation': float(terrain_elevation),
                                'target_elevation': float(ffl),
                                'cut_fill_depth': float(depth_diff),
                                'area': float(cell_area),
                                'volume': float(depth_diff * cell_area)
                            })
                        else:
                            grid_row.append(None)
                    else:
                        grid_row.append(None)
                
                if grid_row:
                    grid_data.append(grid_row)
            
            return {
                'cut_volume': cut_volume,
                'fill_volume': fill_volume,
                'net_volume': cut_volume - fill_volume,
                'grid_data': grid_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cut/fill volumes: {e}")
            return {
                'cut_volume': 0.0,
                'fill_volume': 0.0,
                'net_volume': 0.0,
                'grid_data': []
            }

    def _create_visualisation_data(self, platform_polygon: Polygon, ffl: float, 
                                 cut_fill_result: Dict[str, Any], terrain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create data structure for 3D visualisation with realistic engineering practices"""
        try:
            # Platform boundary for visualization
            platform_coords = list(platform_polygon.exterior.coords[:-1])
            
            # Platform surface coordinates (at FFL level)
            platform_surface = {
                'x': [coord[0] for coord in platform_coords],
                'y': [coord[1] for coord in platform_coords],
                'z': [ffl] * len(platform_coords)
            }
            
            # Cut/fill visualisation data with detailed grid information
            cut_fill_viz = []
            grid_data = cut_fill_result.get('grid_data', [])
            
            for row_idx, row in enumerate(grid_data):
                for col_idx, cell in enumerate(row):
                    if cell and cell['area'] > 0:  # Only include cells with actual area
                        # Apply slope grading for realistic earthworks
                        engineered_depth = self._apply_slope_grading(
                            cell['cut_fill_depth'], cell['x'], cell['y'], platform_polygon
                        )
                        
                        # Determine earthwork type and intensity
                        cut_fill_type = 'cut' if cell['cut_fill_depth'] > 0 else 'fill'
                        depth_magnitude = abs(cell['cut_fill_depth'])
                        
                        # Classify intensity
                        if depth_magnitude > 2.0:
                            intensity = 'heavy'
                        elif depth_magnitude > 1.0:
                            intensity = 'medium'
                        elif depth_magnitude > 0.2:
                            intensity = 'light'
                        else:
                            intensity = 'minimal'
                        
                        cut_fill_viz.append({
                            'x': cell['x'],
                            'y': cell['y'],
                            'z_terrain': cell['terrain_elevation'],
                            'z_target': cell['target_elevation'],
                            'z_engineered': cell['terrain_elevation'] - engineered_depth,
                            'depth': cell['cut_fill_depth'],
                            'engineered_depth': engineered_depth,
                            'type': cut_fill_type,
                            'intensity': intensity,
                            'volume': abs(cell['volume']),
                            'area': cell['area'],
                            'slope_type': self._determine_slope_type(engineered_depth),
                            'grid_position': {'row': row_idx, 'col': col_idx}
                        })
            
            # Create platform boundary at FFL for 3D visualization
            platform_boundary_3d = {
                'x': [coord[0] for coord in platform_coords] + [platform_coords[0][0]],
                'y': [coord[1] for coord in platform_coords] + [platform_coords[0][1]],
                'z': [ffl] * (len(platform_coords) + 1)
            }
            
            return {
                'platform_surface': platform_surface,
                'platform_boundary': platform_boundary_3d,
                'cut_fill_points': cut_fill_viz,
                'grid_resolution': 1.0,
                'total_platform_area': platform_polygon.area,
                'engineering_notes': self._generate_engineering_notes(cut_fill_result),
                'earthwork_summary': {
                    'cut_volume': cut_fill_result.get('cut_volume', 0),
                    'fill_volume': cut_fill_result.get('fill_volume', 0),
                    'net_volume': cut_fill_result.get('net_volume', 0),
                    'platform_elevation': ffl
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create visualization data: {e}")
            return {}

    def _create_engineered_surface(self, platform_polygon: Polygon, ffl: float, 
                                 cut_fill_result: Dict[str, Any], terrain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create engineered surface with proper slopes and transitions"""
        try:
            # Get platform bounds and create transition zones
            bounds = platform_polygon.bounds
            transition_width = 3.0  # 3 meter transition zone
            
            # Expand bounds for transition zone
            expanded_bounds = (
                bounds[0] - transition_width,
                bounds[1] - transition_width, 
                bounds[2] + transition_width,
                bounds[3] + transition_width
            )
            
            engineered_points = []
            
            # Create grid for engineered surface
            resolution = 1.0
            x_range = np.arange(expanded_bounds[0], expanded_bounds[2] + resolution, resolution)
            y_range = np.arange(expanded_bounds[1], expanded_bounds[3] + resolution, resolution)
            
            for x in x_range:
                for y in y_range:
                    point = Point(x, y)
                    distance_to_platform = platform_polygon.exterior.distance(point)
                    
                    if distance_to_platform <= transition_width:
                        # Apply 3:1 slope ratio (33% grade) for transitions
                        slope_ratio = 3.0
                        if distance_to_platform > 0:
                            # Gradual transition from platform to natural terrain
                            transition_factor = distance_to_platform / transition_width
                            # This would need terrain interpolation for actual elevation
                            engineered_z = ffl  # Simplified for now
                        else:
                            engineered_z = ffl
                            
                        engineered_points.append({
                            'x': x, 'y': y, 'z': engineered_z,
                            'type': 'transition', 'distance': distance_to_platform
                        })
            
            return {'transition_points': engineered_points}
            
        except Exception as e:
            self.logger.error(f"Failed to create engineered surface: {e}")
            return {}

    def _apply_slope_grading(self, original_depth: float, x: float, y: float, platform_polygon: Polygon) -> float:
        """Apply realistic slope grading based on distance from platform edge"""
        try:
            point = Point(x, y)
            distance_to_edge = platform_polygon.exterior.distance(point)
            
            # If we're at the platform edge, apply slope grading
            if distance_to_edge <= 5.0:  # 5 meter influence zone
                # Standard 3:1 slope (run:rise)
                slope_ratio = 3.0
                max_transition = min(abs(original_depth) / slope_ratio, distance_to_edge)
                
                if original_depth > 0:  # Cut
                    # Gradual cut with slope
                    return original_depth * (1 - (distance_to_edge / 5.0) * 0.7)
                else:  # Fill
                    # Gradual fill with slope
                    return original_depth * (1 - (distance_to_edge / 5.0) * 0.5)
            
            return original_depth
            
        except Exception as e:
            return original_depth

    def _determine_slope_type(self, depth: float) -> str:
        """Determine the type of slope treatment needed"""
        if abs(depth) < 0.5:
            return "minimal_grading"
        elif abs(depth) < 1.5:
            return "standard_slope"
        elif abs(depth) < 3.0:
            return "engineered_slope"
        else:
            return "retaining_wall_required"

    def _generate_engineering_notes(self, cut_fill_result: Dict[str, Any]) -> List[str]:
        """Generate engineering recommendations based on cut/fill analysis"""
        notes = []
        
        cut_vol = cut_fill_result['cut_volume']
        fill_vol = cut_fill_result['fill_volume']
        net_vol = cut_fill_result['net_volume']
        
        # Material balance recommendations
        if abs(net_vol) < (cut_vol + fill_vol) * 0.1:
            notes.append("✓ Good cut/fill balance - minimal material import/export needed")
        elif net_vol > 0:
            notes.append(f"⚠ Excess cut material: {net_vol:.1f}m³ - consider export or landscape use")
        else:
            notes.append(f"⚠ Fill material needed: {abs(net_vol):.1f}m³ - source quality fill material")
        
        # Slope stability recommendations
        max_depth = max([max([cell['cut_fill_depth'] if cell else 0 for cell in row]) 
                        for row in cut_fill_result.get('grid_data', [])])
        
        if max_depth > 3.0:
            notes.append("⚠ Deep cuts detected - consider retaining walls or terracing")
        elif max_depth > 1.5:
            notes.append("• Standard 3:1 slopes recommended for stability")
        
        # Drainage recommendations
        notes.append("• Install proper drainage systems in cut areas")
        notes.append("• Compact fill material in 300mm lifts to 95% standard Proctor density")
        
        return notes


# Global service instance
earthworks_service = EarthworksService()
