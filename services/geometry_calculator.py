"""
Geometry Calculator Service
Handles complex spatial calculations for buildable areas
"""
from typing import Dict, Any, List, Optional
from .base_service import BaseService


class GeometryCalculator(BaseService):
    """Service for geometric calculations related to building setbacks and areas"""

    def __init__(self):
        super().__init__("GeometryCalculator")

    def calculate_buildable_area(self, site_coords: List[List[float]], requirements: Dict[str, Any], 
                               frontage: str = "auto", edge_classifications: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculate the buildable area within a site polygon after applying setbacks"""
        try:
            print(f"[GeometryCalculator] Starting buildable area calculation")
            print(f"[GeometryCalculator] Input coords count: {len(site_coords) if site_coords else 0}")
            print(f"[GeometryCalculator] Requirements: {requirements}")
            print(f"[GeometryCalculator] Frontage: {frontage}")
            print(f"[GeometryCalculator] Edge classifications: {len(edge_classifications) if edge_classifications else 0}")

            from shapely.geometry import Polygon, Point
            from shapely.ops import unary_union
            import numpy as np

            # Try to import pyproj, fallback if not available
            try:
                import pyproj
                from pyproj import Transformer
                PYPROJ_AVAILABLE = True
                print(f"[GeometryCalculator] pyproj available, using accurate calculations")
            except ImportError:
                print(f"[GeometryCalculator] pyproj not available, using fallback calculations")
                PYPROJ_AVAILABLE = False

            # Validate inputs
            if not site_coords or len(site_coords) < 3:
                print(f"[GeometryCalculator] ERROR: Insufficient coordinates - got {len(site_coords) if site_coords else 0}")
                raise ValueError("At least 3 coordinate points are required")

            if not requirements:
                print(f"[GeometryCalculator] ERROR: No requirements provided")
                raise ValueError("Council requirements are required")

            # Convert coordinates to Shapely polygon with error handling
            try:
                print(f"[GeometryCalculator] Raw site_coords: {site_coords[:2]}...")  # Show first 2 coords
                coords = self._normalize_coordinates(site_coords)
                print(f"[GeometryCalculator] Normalized coords: {coords[:2]}...")  # Show first 2 normalized

                site_polygon = Polygon(coords)
                print(f"[GeometryCalculator] Initial polygon valid: {site_polygon.is_valid}")
                print(f"[GeometryCalculator] Initial polygon area: {site_polygon.area}")

                if not site_polygon.is_valid:
                    print(f"[GeometryCalculator] WARNING: Invalid polygon geometry, attempting to fix")
                    self.logger.warning("Invalid polygon geometry, attempting to fix")
                    site_polygon = site_polygon.buffer(0)  # Attempt to fix geometry
                    print(f"[GeometryCalculator] Fixed polygon valid: {site_polygon.is_valid}")
                    print(f"[GeometryCalculator] Fixed polygon area: {site_polygon.area}")

                if site_polygon.is_empty or site_polygon.area <= 0:
                    print(f"[GeometryCalculator] ERROR: Site polygon has no area - empty: {site_polygon.is_empty}, area: {site_polygon.area}")
                    raise ValueError("Site polygon has no area")

            except Exception as e:
                print(f"[GeometryCalculator] ERROR: Failed to create polygon: {str(e)}")
                raise ValueError(f"Failed to create site polygon: {str(e)}")

            # Get centroid for local projection
            try:
                centroid = site_polygon.centroid
                center_lat, center_lng = centroid.y, centroid.x
                print(f"[GeometryCalculator] Polygon centroid: lat={center_lat:.6f}, lng={center_lng:.6f}")

                if not (-90 <= center_lat <= 90) or not (-180 <= center_lng <= 180):
                    print(f"[GeometryCalculator] ERROR: Invalid centroid coordinates: {center_lat}, {center_lng}")
                    raise ValueError(f"Invalid centroid coordinates: {center_lat}, {center_lng}")

            except Exception as e:
                print(f"[GeometryCalculator] ERROR: Failed to calculate centroid: {str(e)}")
                raise ValueError(f"Failed to calculate polygon centroid: {str(e)}")

            # Use accurate projection if pyproj is available, otherwise use approximate conversion
            if PYPROJ_AVAILABLE:
                # Create local projection for accurate measurements
                proj_string = f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lng} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
                print(f"[GeometryCalculator] Using projection: {proj_string}")

                transformer_to_local = Transformer.from_crs("EPSG:4326", proj_string, always_xy=True)
                transformer_to_wgs84 = Transformer.from_crs(proj_string, "EPSG:4326", always_xy=True)
                print(f"[GeometryCalculator] Transformers created successfully")

                # Transform polygon to local coordinates
                local_coords = [transformer_to_local.transform(lng, lat) for lng, lat in coords]
                local_polygon = Polygon(local_coords)
                print(f"[GeometryCalculator] Local polygon area: {local_polygon.area:.2f} m²")
            else:
                # Use approximate conversion for fallback
                print(f"[GeometryCalculator] Using approximate coordinate conversion")
                # Convert to approximate meters using simple lat/lng to meter conversion
                avg_lat = sum(coord[1] for coord in coords) / len(coords)
                lat_factor = 111320.0  # meters per degree latitude
                lng_factor = 111320.0 * np.cos(np.radians(avg_lat))  # meters per degree longitude

                local_coords = [((lng - center_lng) * lng_factor, (lat - center_lat) * lat_factor) 
                               for lng, lat in coords]
                local_polygon = Polygon(local_coords)
                print(f"[GeometryCalculator] Approximate local polygon area: {local_polygon.area:.2f} m²")

            print(f"[GeometryCalculator] Local coords sample: {local_coords[:2]}...")

            # Apply setbacks
            front_setback_m = requirements.get('front_setback', 4.5)
            side_setback_m = requirements.get('side_setback', 1.5)
            rear_setback_m = requirements.get('rear_setback', 3.0)

            print(f"[GeometryCalculator] Setbacks - Front: {front_setback_m}m, Side: {side_setback_m}m, Rear: {rear_setback_m}m")

            # Prioritize manual edge classifications over automatic frontage detection
            if edge_classifications and len(edge_classifications) > 0:
                print(f"[GeometryCalculator] Using manual edge classifications: {[e.get('type', 'unknown') for e in edge_classifications]}")
                buildable_polygon_local = self._apply_manual_edge_setbacks(
                    local_polygon, local_coords, edge_classifications,
                    front_setback_m, side_setback_m, rear_setback_m
                )
                calculation_method = 'manual_edge_classification'
            elif frontage and frontage != "auto" and frontage != "":
                print(f"[GeometryCalculator] Using directional setbacks with frontage: {frontage}")
                buildable_polygon_local = self._apply_directional_setbacks(
                    local_polygon, local_coords, frontage, 
                    front_setback_m, side_setback_m, rear_setback_m
                )
                calculation_method = f'accurate_{frontage}_frontage'
            else:
                print(f"[GeometryCalculator] WARNING: No frontage selected, frontage='{frontage}', using fallback calculation")
                self.logger.warning("No frontage selected, using fallback buffer calculation")
                # Use fallback buffer calculation instead of error
                max_setback = max(front_setback_m, side_setback_m, rear_setback_m)
                buildable_polygon_local = local_polygon.buffer(-max_setback)
                calculation_method = 'fallback_uniform_setback'

            print(f"[GeometryCalculator] Buildable polygon valid: {buildable_polygon_local.is_valid}")
            print(f"[GeometryCalculator] Buildable polygon area: {buildable_polygon_local.area:.2f} m²")
            print(f"[GeometryCalculator] Buildable polygon empty: {buildable_polygon_local.is_empty}")

            if buildable_polygon_local.is_empty or buildable_polygon_local.area <= 0:
                return self._create_no_buildable_area_result(local_polygon.area, calculation_method)

            # Transform back to WGS84
            if PYPROJ_AVAILABLE:
                buildable_coords = self._transform_polygon_to_wgs84(buildable_polygon_local, transformer_to_wgs84)
            else:
                # Use approximate conversion back to lat/lng
                buildable_coords = self._transform_polygon_to_wgs84_fallback(buildable_polygon_local, center_lat, center_lng)

            # Calculate areas
            site_area_m2 = local_polygon.area
            buildable_area_m2 = buildable_polygon_local.area

            self._log_operation("Buildable area calculated", 
                              f"Site {site_area_m2:.1f}m², Buildable {buildable_area_m2:.1f}m², Method: {calculation_method}")

            return {
                'buildable_coords': buildable_coords,
                'buildable_area_m2': buildable_area_m2,
                'site_area_m2': site_area_m2,
                'coverage_ratio': buildable_area_m2 / site_area_m2 if site_area_m2 > 0 else 0,
                'requirements_applied': requirements,
                'setback_details': {
                    'front_setback_m': front_setback_m,
                    'side_setback_m': side_setback_m,
                    'rear_setback_m': rear_setback_m,
                    'frontage': frontage
                },
                'calculation_method': calculation_method
            }

        except Exception as e:
            return self._handle_error("calculate_buildable_area", e, self._calculate_buildable_area_fallback(site_coords, requirements))

    def _normalize_coordinates(self, site_coords: List[List[float]]) -> List[tuple]:
        """Convert various coordinate formats to standard (lng, lat) tuples"""
        coords = []
        for coord in site_coords:
            if isinstance(coord, dict):
                coords.append((coord['lng'], coord['lat']))
            else:
                # Site coords are already in [lng, lat] format from frontend
                coords.append((coord[0], coord[1]))
        return coords

    def _apply_directional_setbacks(self, polygon, coords, frontage, front_setback, side_setback, rear_setback):
        """Apply different setbacks to different sides based on frontage direction"""
        from shapely.geometry import Polygon
        import numpy as np

        try:
            print(f"[GeometryCalculator] Applying directional setbacks - frontage: {frontage}")
            print(f"[GeometryCalculator] Setbacks: front={front_setback}, side={side_setback}, rear={rear_setback}")

            # Get polygon edges
            edges = [(coords[i], coords[(i + 1) % len(coords)]) for i in range(len(coords))]
            print(f"[GeometryCalculator] Created {len(edges)} edges")

            # Classify edges by frontage
            edge_types = self._classify_edges_by_frontage(edges, frontage)
            print(f"[GeometryCalculator] Edge classifications: {edge_types}")

            # Create offset lines for each edge
            offset_lines = []
            for i, ((p1, p2), edge_type) in enumerate(zip(edges, edge_types)):
                setback = {
                    'front': front_setback,
                    'rear': rear_setback,
                    'side': side_setback
                }.get(edge_type, side_setback)

                print(f"[GeometryCalculator] Edge {i}: type={edge_type}, setback={setback}m")

                # Calculate inward normal vector
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                length = np.sqrt(dx**2 + dy**2)
                print(f"[GeometryCalculator] Edge {i}: length={length:.2f}m, dx={dx:.2f}, dy={dy:.2f}")

                if length > 0:
                    nx, ny = -dy / length, dx / length

                    # Ensure normal points inward
                    centroid = polygon.centroid
                    edge_center = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2)
                    to_centroid_x = centroid.x - edge_center[0]
                    to_centroid_y = centroid.y - edge_center[1]

                    print(f"[GeometryCalculator] Edge {i}: normal=({nx:.3f}, {ny:.3f}), to_centroid=({to_centroid_x:.2f}, {to_centroid_y:.2f})")

                    if nx * to_centroid_x + ny * to_centroid_y < 0:
                        nx, ny = -nx, -ny
                        print(f"[GeometryCalculator] Edge {i}: flipped normal to ({nx:.3f}, {ny:.3f})")

                    offset_p1 = (p1[0] + nx * setback, p1[1] + ny * setback)
                    offset_p2 = (p2[0] + nx * setback, p2[1] + ny * setback)
                    offset_lines.append((offset_p1, offset_p2))
                    print(f"[GeometryCalculator] Edge {i}: offset line created")

            # Find intersections to create buildable polygon
            intersection_points = []
            for i in range(len(offset_lines)):
                line1 = offset_lines[i]
                line2 = offset_lines[(i + 1) % len(offset_lines)]
                intersection = self._line_intersection(line1, line2)
                if intersection:
                    intersection_points.append(intersection)
                    print(f"[GeometryCalculator] Intersection {i}: {intersection}")
                else:
                    print(f"[GeometryCalculator] No intersection found between lines {i} and {(i+1) % len(offset_lines)}")

            print(f"[GeometryCalculator] Found {len(intersection_points)} intersection points")

            if len(intersection_points) >= 3:
                buildable_polygon = Polygon(intersection_points)
                print(f"[GeometryCalculator] Created buildable polygon: valid={buildable_polygon.is_valid}, area={buildable_polygon.area:.2f}")

                if buildable_polygon.is_valid and polygon.contains(buildable_polygon):
                    print(f"[GeometryCalculator] Returning valid buildable polygon")
                    return buildable_polygon
                else:
                    print(f"[GeometryCalculator] Polygon invalid or not contained, using fallback")
            else:
                print(f"[GeometryCalculator] Insufficient intersection points, using fallback")

            # Fallback to simple buffer
            max_setback = max(front_setback, side_setback, rear_setback)
            print(f"[GeometryCalculator] Using buffer fallback with max setback: {max_setback}m")
            buffered = polygon.buffer(-max_setback)
            print(f"[GeometryCalculator] Buffer result: valid={buffered.is_valid}, area={buffered.area:.2f}")
            return buffered

        except Exception as e:
            self.logger.error(f"Error in directional setback calculation: {e}")
            max_setback = max(front_setback, side_setback, rear_setback)
            return polygon.buffer(-max_setback)

    def _classify_edges_by_frontage(self, edges, frontage):
        """Classify polygon edges as front, rear, or side based on frontage selection"""
        import numpy as np

        edge_types = []
        frontage_directions = frontage if isinstance(frontage, list) else [frontage]

        # Calculate bearing for each edge and find the best matching front edge
        edge_bearings = []
        for i, (p1, p2) in enumerate(edges):
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            bearing = np.degrees(np.arctan2(dx, dy))
            if bearing < 0:
                bearing += 360
            edge_bearings.append(bearing)

        # Find the edge that best matches the frontage direction
        frontage_bearing = self._direction_to_bearing(frontage)
        front_edge_index = self._find_best_matching_edge(edge_bearings, frontage_bearing)

        # Classify edges based on their relationship to the front edge
        for i in range(len(edges)):
            if i == front_edge_index:
                edge_types.append('front')
            elif len(edges) == 4:  # Rectangle/square - opposite edge is rear
                rear_index = (front_edge_index + 2) % 4
                if i == rear_index:
                    edge_types.append('rear')
                else:
                    edge_types.append('side')
            else:  # More complex polygon - classify based on angle difference
                angle_diff = abs(edge_bearings[i] - edge_bearings[front_edge_index])
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if 135 <= angle_diff <= 225:  # Opposite direction (rear)
                    edge_types.append('rear')
                else:
                    edge_types.append('side')

        return edge_types

    def _bearing_to_direction(self, bearing):
        """Convert bearing angle to compass direction"""
        directions = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']
        direction_ranges = [
            (337.5, 360), (0, 22.5), (22.5, 67.5), (67.5, 112.5),
            (112.5, 157.5), (157.5, 202.5), (202.5, 247.5), (292.5, 337.5)
        ]

        for i, (start, end) in enumerate(direction_ranges):
            if i == 0:  # North wraps around 0
                if bearing >= start or bearing <= end:
                    return 'north'
            else:
                if start <= bearing < end:
                    return directions[min(i, len(directions)-1)]

        return 'north'

    def _directions_match(self, edge_direction, selected_direction):
        """Check if two compass directions match"""
        return edge_direction.lower() == selected_direction.lower()

    def _direction_to_bearing(self, direction):
        """Convert compass direction to bearing angle"""
        direction_bearings = {
            'north': 90, 'northeast': 45, 'east': 0, 'southeast': 315,
            'south': 270, 'southwest': 225, 'west': 180, 'northwest': 135
        }
        return direction_bearings.get(direction.lower(), 90)

    def _find_best_matching_edge(self, edge_bearings, target_bearing):
        """Find the edge that best matches the target bearing"""
        best_index = 0
        min_diff = float('inf')

        for i, bearing in enumerate(edge_bearings):
            # Calculate angular difference
            diff = abs(bearing - target_bearing)
            if diff > 180:
                diff = 360 - diff

            if diff < min_diff:
                min_diff = diff
                best_index = i

        return best_index

    def _assign_rear_edges(self, edge_types, edges, frontage_directions):
        """Assign rear edges as opposite to front edges"""
        front_indices = [i for i, t in enumerate(edge_types) if t == 'front']

        opposite_directions = {
            'north': 'south', 'northeast': 'southwest', 'east': 'west', 'southeast': 'northwest',
            'south': 'north', 'southwest': 'northeast', 'west': 'east', 'northwest': 'southeast'
        }

        for front_idx in front_indices:
            if len(edges) == 4:  # Rectangle/square
                rear_idx = (front_idx + 2) % len(edges)
                if edge_types[rear_idx] == 'side':
                    edge_types[rear_idx] = 'rear'

    def _apply_manual_edge_setbacks(self, polygon, coords, edge_classifications, front_setback, side_setback, rear_setback):
        """Apply setbacks based on manual edge classifications with precise edge-to-edge mapping"""
        from shapely.geometry import Polygon, LineString
        import numpy as np

        try:
            print(f"[GeometryCalculator] Applying manual edge setbacks with edge-to-edge mapping")
            print(f"[GeometryCalculator] Edge classifications: {edge_classifications}")
            print(f"[GeometryCalculator] Setbacks: front={front_setback}, side={side_setback}, rear={rear_setback}")

            # Create edge classification map ensuring each edge has a setback
            edge_setback_map = {}
            num_edges = len(coords) - (1 if coords[0] == coords[-1] else 0)
            
            # Initialize all edges with side setback as default
            for i in range(num_edges):
                edge_setback_map[i] = {
                    'type': 'side',
                    'setback': side_setback
                }

            # Apply specific classifications, using exact setback values from UI
            for classification in edge_classifications:
                edge_index = classification.get('index')
                edge_type = classification.get('type', 'side')
                setback_value = classification.get('setback')

                if edge_index is not None and 0 <= edge_index < num_edges:
                    # Always use the exact setback value from the classification (UI input)
                    # Convert to float and allow 0 values explicitly
                    final_setback = float(setback_value) if setback_value is not None else 0.0
                    if final_setback < 0:
                        final_setback = 0  # Only prevent negative values
                        
                    edge_setback_map[edge_index] = {
                        'type': edge_type,
                        'setback': final_setback
                    }
                    print(f"[GeometryCalculator] Edge {edge_index}: {edge_type} setback={final_setback}m (UI value)")

            # Create parallel offset edges maintaining one-to-one relationship
            buildable_edges = []
            for i in range(num_edges):
                p1 = coords[i]
                p2 = coords[(i + 1) % num_edges]
                setback_info = edge_setback_map[i]
                setback = setback_info['setback']

                # Calculate perpendicular inward vector
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                length = np.sqrt(dx**2 + dy**2)

                if length > 0:
                    if setback == 0:
                        # Zero setback means no offset - use original edge
                        offset_p1 = p1
                        offset_p2 = p2
                    else:
                        # Perpendicular vector (rotated 90 degrees)
                        nx, ny = -dy / length, dx / length

                        # Ensure normal points inward toward polygon centroid
                        centroid = polygon.centroid
                        edge_center = ((p1[0] + p2[0])/2, (p1[1] + p2[1])/2)
                        to_centroid_x = centroid.x - edge_center[0]
                        to_centroid_y = centroid.y - edge_center[1]

                        # Check if normal points toward centroid, flip if not
                        if nx * to_centroid_x + ny * to_centroid_y < 0:
                            nx, ny = -nx, -ny

                        # Create parallel edge offset by setback distance
                        offset_p1 = (p1[0] + nx * setback, p1[1] + ny * setback)
                        offset_p2 = (p2[0] + nx * setback, p2[1] + ny * setback)
                    
                    buildable_edges.append({
                        'start': offset_p1,
                        'end': offset_p2,
                        'original_index': i,
                        'setback': setback,
                        'type': setback_info['type']
                    })
                    
                    print(f"[GeometryCalculator] Edge {i}: {setback_info['type']} offset by {setback}m")

            # Find intersections between consecutive offset edges to form buildable polygon
            intersection_points = []
            for i in range(len(buildable_edges)):
                edge1 = buildable_edges[i]
                edge2 = buildable_edges[(i + 1) % len(buildable_edges)]
                
                line1 = (edge1['start'], edge1['end'])
                line2 = (edge2['start'], edge2['end'])
                
                intersection = self._line_intersection(line1, line2)
                if intersection:
                    intersection_points.append(intersection)
                    print(f"[GeometryCalculator] Intersection {i}-{(i+1) % len(buildable_edges)}: {intersection}")
                else:
                    # If no intersection, use end of first edge as fallback
                    intersection_points.append(edge1['end'])
                    print(f"[GeometryCalculator] No intersection found, using edge endpoint")

            print(f"[GeometryCalculator] Created {len(intersection_points)} buildable polygon vertices")

            if len(intersection_points) >= 3:
                buildable_polygon = Polygon(intersection_points)
                
                if buildable_polygon.is_valid and not buildable_polygon.is_empty:
                    # Ensure buildable polygon is contained within original
                    if polygon.contains(buildable_polygon) or polygon.intersects(buildable_polygon):
                        print(f"[GeometryCalculator] Buildable polygon created: area={buildable_polygon.area:.2f}m²")
                        return buildable_polygon
                    else:
                        print(f"[GeometryCalculator] Buildable polygon outside original, using intersection")
                        intersection_poly = polygon.intersection(buildable_polygon)
                        if not intersection_poly.is_empty:
                            return intersection_poly

            # Fallback: use buffer with average setback if polygon creation fails
            avg_setback = sum(edge_setback_map[i]['setback'] for i in range(num_edges)) / num_edges
            print(f"[GeometryCalculator] Using buffer fallback with average setback: {avg_setback}m")
            buffered = polygon.buffer(-avg_setback)
            return buffered

        except Exception as e:
            self.logger.error(f"Error in manual edge setback calculation: {e}")
            # Final fallback
            max_setback = max(front_setback, side_setback, rear_setback)
            return polygon.buffer(-max_setback)

    def _line_intersection(self, line1, line2):
        """Find intersection point of two lines"""
        import numpy as np

        (x1, y1), (x2, y2) = line1
        (x3, y3), (x4, y4) = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (x, y)

    def _transform_polygon_to_wgs84(self, polygon, transformer):
        """Transform polygon coordinates back to WGS84"""
        if hasattr(polygon, 'exterior'):
            coords_local = list(polygon.exterior.coords[:-1])
            return [[transformer.transform(x, y)[1], transformer.transform(x, y)[0]] 
                   for x, y in coords_local]
        return []

    def _transform_polygon_to_wgs84_fallback(self, polygon, center_lat, center_lng):
        """Transform polygon coordinates back to WGS84 using approximate conversion"""
        import numpy as np

        if hasattr(polygon, 'exterior'):
            coords_local = list(polygon.exterior.coords[:-1])
            # Convert back from approximate meters to lat/lng
            lat_factor = 111320.0  # meters per degree latitude
            lng_factor = 111320.0 * np.cos(np.radians(center_lat))  # meters per degree longitude

            coords_wgs84 = []
            for x, y in coords_local:
                lng = center_lng + (x / lng_factor)
                lat = center_lat + (y / lat_factor)
                coords_wgs84.append([lat, lng])

            return coords_wgs84
        return []

    def _create_error_result(self, error_message):
        """Create error result structure"""
        return {
            'buildable_coords': [],
            'buildable_area_m2': 0,
            'site_area_m2': 0,
            'error': error_message,
            'note': 'Please select an edge of your property that faces the street',
            'calculation_method': 'error_no_frontage'
        }

    def _create_no_buildable_area_result(self, site_area, calculation_method):
        """Create result for when no buildable area exists"""
        return {
            'buildable_coords': [],
            'buildable_area_m2': 0,
            'site_area_m2': site_area,
            'coverage_ratio': 0,
            'note': 'No buildable area after applying setbacks',
            'calculation_method': calculation_method
        }

    def _calculate_buildable_area_fallback(self, site_coords, requirements):
        """Fallback calculation method"""
        try:
            from shapely.geometry import Polygon
            import numpy as np

            coords = self._normalize_coordinates(site_coords)
            site_polygon = Polygon(coords)

            max_setback_m = max(
                requirements.get('front_setback', 4.5),
                requirements.get('side_setback', 1.5), 
                requirements.get('rear_setback', 3.0)
            )

            # Rough degree conversion for New Zealand
            avg_lat = sum(coord[1] for coord in coords) / len(coords)
            lat_factor = 1.0 / 111320.0
            lng_factor = 1.0 / (111320.0 * np.cos(np.radians(avg_lat)))

            setback_deg = max_setback_m * max(lat_factor, lng_factor)
            buildable_polygon = site_polygon.buffer(-setback_deg)

            if buildable_polygon.is_empty or buildable_polygon.area <= 0:
                return self._create_no_buildable_area_result(
                    self._polygon_area_m2(site_polygon), 'fallback_approximation'
                )

            buildable_coords = [[coord[1], coord[0]] for coord in buildable_polygon.exterior.coords[:-1]]

            return {
                'buildable_coords': buildable_coords,
                'buildable_area_m2': self._polygon_area_m2(buildable_polygon),
                'site_area_m2': self._polygon_area_m2(site_polygon),
                'setback_applied_m': max_setback_m,
                'calculation_method': 'fallback_approximation'
            }

        except Exception as e:
            return self._handle_error("fallback_calculation", e, {
                'buildable_coords': [],
                'buildable_area_m2': 0,
                'site_area_m2': 0,
                'error': str(e),
                'calculation_method': 'error'
            })

    def _polygon_area_m2(self, polygon) -> float:
        """Calculate polygon area in square meters"""
        try:
            area_deg2 = polygon.area
            return area_deg2 * (111320 ** 2)
        except:
            return 0