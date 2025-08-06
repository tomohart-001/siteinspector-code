"""
Terrain Service - Handles 3D terrain visualization using NZ elevation data
"""
import os
import requests
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from .base_service import CacheableService

# Try to import geospatial dependencies with graceful fallback
try:
    import rasterio
    import rasterio.mask
    from shapely.geometry import Point, shape, mapping, Polygon, MultiPolygon
    from shapely.ops import transform as shapely_transform
    from pyproj import Transformer
    from rasterio.transform import xy
    from scipy.ndimage import gaussian_filter, gaussian_filter1d
    GEOSPATIAL_AVAILABLE = True
    print(f"[TerrainService] All geospatial dependencies loaded successfully")
except ImportError as e:
    print(f"[TerrainService] Geospatial dependency error: {e}")
    GEOSPATIAL_AVAILABLE = False
    rasterio = None
    Point = None
    shape = None
    mapping = None
    shapely_transform = None
    Transformer = None
    xy = None
    gaussian_filter = None


class TerrainService(CacheableService):
    """Service for processing terrain elevation data and creating 3D visualizations"""

    def __init__(self):
        super().__init__("TerrainService", cache_ttl=3600)  # 1 hour cache
        self.api_key = os.getenv('TERRAIN_API_KEY')
        self.available = GEOSPATIAL_AVAILABLE
        
        # Log API key status for debugging
        if self.api_key:
            self.logger.info(f"LINZ API key configured (length: {len(self.api_key)})")
        else:
            self.logger.warning("LINZ API key not configured - property boundary retrieval will fail")

        # Set Mapbox token
        self.mapbox_token = os.getenv('MAPBOX_TOKEN', 'pk.eyJ1IjoidG9tby1oYXJ0IiwiYSI6ImNsemhjbzU2aTFvcmcya3Bhcm1vNGJqOTQifQ.f-vqCMUDiIpQZqHxJdE7Sw')

        # Tile cache with bounding box coverage for fast coordinate lookups
        self.tile_bbox_cache = {}  # Cache tiles by their bounding boxes
        self.coordinate_tile_cache = {}  # Legacy cache for specific coordinates
        self.cache_precision = 3  # Round coordinates to 3 decimal places for caching

        if self.available:
            self.logger.info("Terrain service initialized successfully with all dependencies")
        else:
            self.logger.warning("Terrain service unavailable - missing geospatial dependencies")

        # DEM Collections for different NZ cities
        self.dem_collections = {
            "wellington": [
                {
                    "name": "Wellington City (2019-2020)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/wellington-city_2019-2020/dem_1m/2193/collection.json"
                }
            ],
            "auckland": [
                {
                    "name": "Auckland Part 2 (2024)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/auckland/auckland-part-2_2024/dem_1m/2193/collection.json"
                },
                {
                    "name": "Auckland Part 1 (2024)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/auckland/auckland-part-1_2024/dem_1m/2193/collection.json"
                }
            ],
            "christchurch": [
                {
                    "name": "Christchurch (2020-2021)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/canterbury/christchurch_2020-2021/dem_1m/2193/collection.json"
                }
            ],
            "hamilton": [
                {
                    "name": "Hamilton (2023)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/waikato/hamilton_2023/dem_1m/2193/collection.json"
                }
            ],
            "dunedin": [
                {
                    "name": "Dunedin and Mosgiel (2021)",
                    "url": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/otago/dunedin-and-mosgiel_2021/dem_1m/2193/collection.json"
                }
            ]
        }

    def generate_terrain_data(self, site_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """Generate 3D terrain data for a site with optional progress tracking"""
        try:
            def update_progress(step: int, message: str, percentage: int = None):
                """Update progress if callback provided"""
                if progress_callback:
                    progress_callback(step, message, percentage)
                self.logger.info(f"[TerrainService] Progress Step {step}: {message}")

            self.logger.info(f"[TerrainService] DEBUG: Starting terrain generation with site_data keys: {list(site_data.keys())}")

            # Check for terrain bounds from site boundary
            terrain_bounds = site_data.get('terrainBounds')
            if terrain_bounds:
                self.logger.info(f"[TerrainService] Using provided terrain bounds: {terrain_bounds}")
                update_progress(1, "Using terrain bounds", 10)
            else:
                update_progress(1, "Geocoding coordinates", 10)

            # Check if geospatial dependencies are available
            if not self.available:
                self.logger.error("[TerrainService] DEBUG: Geospatial dependencies not available")
                return {
                    'success': False,
                    'error': 'Terrain visualization requires additional geospatial libraries. Please install: rasterio, shapely, pyproj, scipy'
                }

            # Extract coordinates and address from site data
            coordinates = site_data.get('coordinates', [])
            self.logger.info(f"[TerrainService] DEBUG: Extracted coordinates: {coordinates}")

            if not coordinates:
                self.logger.error("[TerrainService] DEBUG: No coordinates found in site data")
                return {'success': False, 'error': 'No site coordinates available'}

            # Handle coordinate format - coordinates should be a list of [lng, lat] pairs
            coords = coordinates
            self.logger.info(f"[TerrainService] DEBUG: Processing coordinates with {len(coords)} points")

            # Calculate center point from site boundary polygon coordinates
            lat = None
            lng = None

            try:
                # Calculate the centroid of the polygon
                if coords and len(coords) > 0:
                    total_lng = 0
                    total_lat = 0
                    valid_points = 0

                    for coord in coords:
                        coord_lng = None
                        coord_lat = None

                        if isinstance(coord, dict):
                            coord_lat = coord.get('lat') or coord.get('latitude') or coord.get('y')
                            coord_lng = coord.get('lng') or coord.get('longitude') or coord.get('x')
                        elif isinstance(coord, (list, tuple)) and len(coord) >= 2:
                            # Assume [lng, lat] format for coordinate arrays
                            coord_lng, coord_lat = float(coord[0]), float(coord[1])

                        if coord_lng is not None and coord_lat is not None:
                            total_lng += float(coord_lng)
                            total_lat += float(coord_lat)
                            valid_points += 1

                    if valid_points > 0:
                        lng = total_lng / valid_points
                        lat = total_lat / valid_points
                        self.logger.info(f"[TerrainService] DEBUG: Calculated center from polygon: lat={lat}, lng={lng} from {valid_points} points")
                    else:
                        self.logger.error("[TerrainService] DEBUG: No valid coordinate points found in polygon")
                        return {'success': False, 'error': 'No valid coordinates in site boundary polygon'}
                else:
                    self.logger.error("[TerrainService] DEBUG: Empty coordinates array")
                    return {'success': False, 'error': 'Empty coordinates array'}

            except (IndexError, TypeError, ValueError) as e:
                self.logger.error(f"[TerrainService] DEBUG: Error calculating polygon center: {e}")
                return {'success': False, 'error': f'Error calculating polygon center: {str(e)}'}

            # Validate that we have valid numeric coordinates
            if lat is None or lng is None:
                self.logger.error(f"[TerrainService] DEBUG: Missing lat/lng values: lat={lat}, lng={lng}")
                return {'success': False, 'error': 'Missing latitude or longitude values'}

            try:
                lat = float(lat)
                lng = float(lng)
            except (ValueError, TypeError) as e:
                self.logger.error(f"[TerrainService] DEBUG: Invalid numeric coordinates: lat={lat}, lng={lng}, error={e}")
                return {'success': False, 'error': f'Invalid numeric coordinates: {str(e)}'}

            # Validate coordinate ranges for New Zealand with user-friendly messaging
            if not (-47.0 <= lat <= -34.0) or not (166.0 <= lng <= 179.0):
                self.logger.warning(f"[TerrainService] DEBUG: Location {lat}, {lng} is outside New Zealand")

                # Determine the likely region for a more helpful error message
                region_info = self._identify_region(lat, lng)

                return {
                    'success': False, 
                    'error': f'Terrain visualization is currently only available for New Zealand locations. This location appears to be in {region_info}.',
                    'error_type': 'location_not_supported',
                    'supported_region': 'New Zealand',
                    'detected_location': {'lat': lat, 'lng': lng, 'region': region_info}
                }

            # Get address from multiple possible sources
            address = (site_data.get('address') or 
                      site_data.get('formatted_address') or
                      site_data.get('display_name') or
                      f'{lat:.6f}, {lng:.6f}')

            self.logger.info(f"[TerrainService] DEBUG: Using address: '{address}'")

            self._log_operation("Starting terrain generation", f"Address: {address}, Coords: {lat}, {lng}")

            # Find appropriate DEM tile using coordinates
            update_progress(2, "Identifying city region", 15)
            city = self._get_city_from_coordinates(lng, lat)
            self.logger.info(f"[TerrainService] DEBUG: Identified city as: '{city}' from coordinates: {lng}, {lat}")

            # Get property boundary from LINZ
            update_progress(3, "Retrieving property boundary", 20)
            self.logger.info(f"[TerrainService] DEBUG: Getting property boundary for {lng}, {lat}")
            property_shape = self._get_property_boundary(lng, lat)
            if not property_shape:
                self.logger.error("[TerrainService] DEBUG: Failed to get property boundary")
                if not self.api_key:
                    return {'success': False, 'error': 'LINZ API key not configured. Please contact administrator to configure terrain data access.'}
                else:
                    return {'success': False, 'error': 'Could not retrieve property boundary from LINZ. This may be due to API connectivity issues or the location not being found in the property database.'}
            self.logger.info(f"[TerrainService] DEBUG: Property boundary retrieved successfully")

            # Find DEM tile
            update_progress(4, "Finding DEM tiles", 25)
            dem_tile = self._find_dem_tile(city, lng, lat)
            if not dem_tile:
                self.logger.error(f"[TerrainService] DEBUG: No DEM tile found for city '{city}' at coordinates {lng}, {lat}")
                return {'success': False, 'error': f'No elevation data available for {city}'}
            self.logger.info(f"[TerrainService] DEBUG: Found DEM tile: {dem_tile.get('id', 'unknown')}")

            # Download elevation data
            update_progress(5, "Downloading elevation data", 40)

            # Process elevation data
            update_progress(6, "Processing terrain data", 50)
            self.logger.info(f"[TerrainService] DEBUG: Processing elevation data")
            terrain_data = self._process_elevation_data(dem_tile, property_shape, progress_callback)
            if not terrain_data:
                self.logger.error("[TerrainService] DEBUG: Failed to process elevation data")
                return {'success': False, 'error': 'Failed to process elevation data'}

            # Create visualisation data
            update_progress(7, "Creating visualisation", 70)

            # Add metadata and polygon overlays
            terrain_data.update({
                'success': True,
                'address': address,
                'city': city,
                'coordinates': {'lat': lat, 'lng': lng}
            })

            # Add Mapbox tile if terrain bounds provided
            if terrain_bounds:
                mapbox_tile_url = self._extract_mapbox_tile(terrain_bounds)
                if mapbox_tile_url:
                    terrain_data['mapbox_tile_url'] = mapbox_tile_url
                    terrain_data['terrain_bounds'] = terrain_bounds
                    self.logger.info(f"[TerrainService] Added Mapbox tile integration")

            # Add polygon overlays for visualisation
            polygons = {}
            if site_data.get('coordinates'):
                polygons['site_boundary'] = {
                    'coordinates': site_data['coordinates'],
                    'area_m2': site_data.get('area_m2', 0),
                    'color': '#007cbf',
                    'name': 'Site Boundary'
                }

            if site_data.get('buildable_area', {}).get('coordinates'):
                buildable = site_data['buildable_area']
                polygons['buildable_area'] = {
                    'coordinates': buildable['coordinates'],
                    'area_m2': buildable.get('area_m2', 0),
                    'color': '#28a745',
                    'name': 'Buildable Area',
                    'setbacks': buildable.get('setbacks', {})
                }

            if site_data.get('structure_placement', {}).get('coordinates'):
                structure = site_data['structure_placement']
                polygons['structure_placement'] = {
                    'coordinates': structure['coordinates'],
                    'area_m2': structure.get('area_m2', 0),
                    'color': '#dc3545',
                    'name': 'Structure Placement',
                    'structure_type': structure.get('structure_type', 'unknown')
                }

            if polygons:
                terrain_data['polygon_overlays'] = polygons
                self.logger.info(f"[TerrainService] Added {len(polygons)} polygon overlays: {list(polygons.keys())}")

            update_progress(7, "Complete! 🎉", 100)
            self._log_operation("Terrain generation completed", f"Data points: {len(terrain_data.get('elevation_data', []))}")
            self.logger.info(f"[TerrainService] DEBUG: Terrain generation completed successfully with {len(polygons)} polygon overlays")
            return terrain_data

        except Exception as e:
            self.logger.error(f"[TerrainService] DEBUG: Terrain generation failed with exception: {e}")
            return {'success': False, 'error': str(e)}

    def _get_property_boundary(self, lng: float, lat: float) -> Optional[Any]:
        """Get property boundary from LINZ API"""
        try:
            if not self.api_key:
                self.logger.error("LINZ API key not configured - cannot retrieve property boundary")
                return None

            layer = 50772
            url = (
                f"https://data.linz.govt.nz/services/query/v1/vector.json"
                f"?key={self.api_key}&layer={layer}&x={lng}&y={lat}"
                "&max_results=10&radius=10000&geometry=true&with_field_names=true"
            )

            self.logger.info(f"[TerrainService] Requesting property boundary from LINZ API for {lng}, {lat}")
            resp = requests.get(url, timeout=30)
            
            if resp.status_code != 200:
                self.logger.error(f"LINZ API returned status {resp.status_code}: {resp.text}")
                return None

            if not resp.text.strip():
                self.logger.error("LINZ API returned empty response")
                return None

            try:
                data = resp.json()
            except ValueError as json_error:
                self.logger.error(f"Failed to parse LINZ API response as JSON: {json_error}")
                self.logger.error(f"Response content: {resp.text[:500]}...")
                return None

            if "vectorQuery" not in data:
                self.logger.error(f"Invalid LINZ API response structure: {data}")
                return None

            layers = data["vectorQuery"].get("layers", {})
            if str(layer) not in layers:
                self.logger.warning(f"No data found in layer {layer} for coordinates {lng}, {lat}")
                return None

            features = layers[str(layer)].get("features", [])
            self.logger.info(f"[TerrainService] Found {len(features)} property features at location")

            if not features:
                self.logger.warning(f"No property features found at {lng}, {lat}")
                return None

            pt = Point(lng, lat)
            for i, f in enumerate(features):
                try:
                    geom = f.get("geometry")
                    if not geom:
                        continue
                    
                    this_shape = shape(geom)
                    if this_shape.contains(pt):
                        self.logger.info(f"[TerrainService] Found containing property boundary (feature {i+1})")
                        return this_shape
                except Exception as feature_error:
                    self.logger.warning(f"Error processing feature {i+1}: {feature_error}")
                    continue

            self.logger.warning(f"No containing property boundary found for point {lng}, {lat}")
            return None

        except requests.exceptions.RequestException as req_error:
            self.logger.error(f"Network error retrieving property boundary: {req_error}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get property boundary: {e}")
            return None

    def _get_coordinate_cache_key(self, lng: float, lat: float, city: str) -> str:
        """Generate a cache key for coordinate-to-tile mapping"""
        # Round coordinates to reduce cache key variations for nearby points
        rounded_lng = round(lng, self.cache_precision)
        rounded_lat = round(lat, self.cache_precision)
        return f"{city}_{rounded_lng}_{rounded_lat}"

    def _get_cached_tile(self, lng: float, lat: float, city: str) -> Optional[Dict[str, Any]]:
        """Check if we have a cached tile for these coordinates"""
        cache_key = self._get_coordinate_cache_key(lng, lat, city)
        cached_tile = self.coordinate_tile_cache.get(cache_key)

        if cached_tile:
            # Verify the cached tile still covers the exact coordinates
            bbox = cached_tile.get("bbox")
            if bbox and (bbox[0] <= lng <= bbox[2]) and (bbox[1] <= lat <= bbox[3]):
                self.logger.info(f"[TerrainService] Using cached tile for {lng}, {lat}: {cached_tile.get('id')}")
                return cached_tile
            else:
                # Remove invalid cache entry
                del self.coordinate_tile_cache[cache_key]
                self.logger.info(f"[TerrainService] Removed invalid cached tile for {cache_key}")

        return None

    def _cache_tile_for_coordinates(self, lng: float, lat: float, city: str, tile: Dict[str, Any]):
        """Cache a tile for the given coordinates"""
        cache_key = self._get_coordinate_cache_key(lng, lat, city)
        self.coordinate_tile_cache[cache_key] = tile
        self.logger.info(f"[TerrainService] Cached tile {tile.get('id')} for coordinates {cache_key}")

        # Also cache by bounding box for faster future lookups
        self._cache_tile_by_bbox(city, tile)

    def _cache_tile_by_bbox(self, city: str, tile: Dict[str, Any]):
        """Cache a tile by its bounding box for fast coordinate lookup"""
        if not tile or 'bbox' not in tile:
            return

        bbox = tile['bbox']
        tile_id = tile.get('id')

        # Store in city-specific bbox cache
        if city not in self.tile_bbox_cache:
            self.tile_bbox_cache[city] = []

        # Check if this tile is already cached
        for cached_tile in self.tile_bbox_cache[city]:
            if cached_tile.get('id') == tile_id:
                return  # Already cached

        self.tile_bbox_cache[city].append(tile)
        self.logger.info(f"[TerrainService] Cached tile {tile_id} bbox for city {city}: {bbox}")

    def _find_cached_tile_by_bbox(self, lng: float, lat: float, city: str) -> Optional[Dict[str, Any]]:
        """Find a cached tile that covers the given coordinates using bbox lookup"""
        if city not in self.tile_bbox_cache:
            return None

        for tile in self.tile_bbox_cache[city]:
            bbox = tile.get('bbox')
            if bbox and (bbox[0] <= lng <= bbox[2]) and (bbox[1] <= lat <= bbox[3]):
                self.logger.info(f"[TerrainService] Found cached tile by bbox: {tile.get('id')} covers {lng}, {lat}")
                return tile

        return None

    def _identify_region(self, lat: float, lng: float) -> str:
        """Identify the likely region for coordinates outside New Zealand"""
        try:
            # Australia regions
            if -44.0 <= lat <= -10.0 and 113.0 <= lng <= 154.0:
                if -35.0 <= lat <= -33.0 and 150.0 <= lng <= 152.0:
                    return "Sydney, Australia"
                elif -38.0 <= lat <= -37.0 and 144.0 <= lng <= 146.0:
                    return "Melbourne, Australia"
                elif -28.0 <= lat <= -26.0 and 152.0 <= lng <= 154.0:
                    return "Brisbane, Australia"
                elif -32.0 <= lat <= -31.0 and 115.0 <= lng <= 116.0:
                    return "Perth, Australia"
                else:
                    return "Australia"

            # Other regions
            elif 37.0 <= lat <= 49.0 and -125.0 <= lng <= -66.0:
                return "United States"
            elif 49.0 <= lat <= 60.0 and -141.0 <= lng <= -52.0:
                return "Canada"
            elif 50.0 <= lat <= 60.0 and -8.0 <= lng <= 2.0:
                return "United Kingdom"
            elif -57.0 <= lat <= -21.0 and -74.0 <= lng <= -34.0:
                return "South America"
            elif 35.0 <= lat <= 71.0 and -9.0 <= lng <= 40.0:
                return "Europe"
            elif -35.0 <= lat <= 37.0 and 25.0 <= lng <= 180.0:
                return "Asia-Pacific region"
            else:
                return "an international location"

        except Exception:
            return "an international location"

    def _get_city_from_coordinates(self, lng: float, lat: float) -> str:
        """Determine city from coordinates using approximate bounding boxes"""
        self.logger.info(f"[TerrainService] DEBUG: _get_city_from_coordinates called with: {lng}, {lat}")

        # Define approximate bounding boxes for NZ cities based on DEM coverage areas
        city_bounds = {
            "auckland": {
                "min_lat": -37.5, "max_lat": -36.3,
                "min_lng": 174.0, "max_lng": 175.5
            },
            "wellington": {
                "min_lat": -41.5, "max_lat": -41.0,
                "min_lng": 174.6, "max_lng": 175.0
            },
            "christchurch": {
                "min_lat": -43.8, "max_lat": -43.3,
                "min_lng": 172.0, "max_lng": 173.0
            },
            "hamilton": {
                "min_lat": -38.0, "max_lat": -37.6,
                "min_lng": 175.0, "max_lng": 175.5
            },
            "dunedin": {
                "min_lat": -46.0, "max_lat": -45.5,
                "min_lng": 170.0, "max_lng": 171.0
            }
        }

        self.logger.info(f"[TerrainService] DEBUG: Checking coordinate {lng}, {lat} against city bounds")

        for city, bounds in city_bounds.items():
            if (bounds["min_lat"] <= lat <= bounds["max_lat"] and 
                bounds["min_lng"] <= lng <= bounds["max_lng"]):
                self.logger.info(f"[TerrainService] DEBUG: Coordinate falls within {city} bounds")
                return city
            else:
                self.logger.info(f"[TerrainService] DEBUG: Coordinate not in {city} bounds: lat {bounds['min_lat']}-{bounds['max_lat']}, lng {bounds['min_lng']}-{bounds['max_lng']}")

        # Default to auckland if no match (most common case)
        self.logger.warning(f"[TerrainService] DEBUG: No city bounds match found, defaulting to auckland")
        return "auckland"

    def _find_dem_tile(self, city: str, lng: float, lat: float) -> Optional[Dict[str, Any]]:
        """Find DEM tile that covers the coordinates"""
        try:
            self.logger.info(f"[TerrainService] DEBUG: _find_dem_tile called for city '{city}' at {lng}, {lat}")

            # First check bbox cache - this is much faster
            bbox_cached_tile = self._find_cached_tile_by_bbox(lng, lat, city)
            if bbox_cached_tile:
                return bbox_cached_tile

            # Fallback to coordinate-specific cache
            cached_tile = self._get_cached_tile(lng, lat, city)
            if cached_tile:
                return cached_tile

            collections = self.dem_collections.get(city, [])
            self.logger.info(f"[TerrainService] DEBUG: Found {len(collections)} collections for city '{city}'")

            if not collections:
                self.logger.error(f"[TerrainService] DEBUG: No collections available for city '{city}'")
                return None

            for i, collection in enumerate(collections):
                collection_name = collection["name"]
                collection_url = collection["url"]
                self.logger.info(f"[TerrainService] DEBUG: Checking collection {i+1}/{len(collections)}: '{collection_name}'")
                self.logger.info(f"[TerrainService] DEBUG: Collection URL: {collection_url}")

                try:
                    resp = requests.get(collection_url, timeout=30)
                    if resp.status_code != 200:
                        self.logger.warning(f"[TerrainService] DEBUG: Collection request failed with status {resp.status_code}")
                        continue

                    data = resp.json()
                    tile_urls = [link["href"].lstrip("./") for link in data["links"] if link["rel"] == "item"]
                    base_url = collection_url[:collection_url.rfind('/')+1]

                    self.logger.info(f"[TerrainService] DEBUG: Found {len(tile_urls)} tiles in collection, checking all tiles")

                    # Check all tiles for coverage
                    for j, tile_url in enumerate(tile_urls):
                        full_url = base_url + tile_url
                        self.logger.info(f"[TerrainService] DEBUG: Checking tile {j+1}/{len(tile_urls)}: {tile_url}")

                        try:
                            t_resp = requests.get(full_url, timeout=10)
                            if t_resp.status_code != 200:
                                self.logger.warning(f"[TerrainService] DEBUG: Tile request failed with status {t_resp.status_code}")
                                continue

                            tile = t_resp.json()
                            bbox = tile.get("bbox")
                            assets = tile.get("assets", {})

                            self.logger.info(f"[TerrainService] DEBUG: Tile bbox: {bbox}")

                            tiff_asset = None
                            for v in assets.values():
                                if v and "href" in v and v["href"].endswith(".tiff"):
                                    tiff_asset = v["href"]
                                    break

                            if bbox and (bbox[0] <= lng <= bbox[2]) and (bbox[1] <= lat <= bbox[3]) and tiff_asset:
                                self.logger.info(f"[TerrainService] DEBUG: Found matching tile! ID: {tile.get('id')}")
                                found_tile = {
                                    "id": tile.get("id"),
                                    "bbox": bbox,
                                    "tiff": tiff_asset,
                                    "base_url": base_url,
                                }
                                # Cache this tile for future use (both coordinate and bbox caching)
                                self._cache_tile_for_coordinates(lng, lat, city, found_tile)
                                return found_tile
                            else:
                                # Even non-matching tiles should be cached by bbox to avoid re-scanning
                                if bbox and tiff_asset:
                                    non_matching_tile = {
                                        "id": tile.get("id"),
                                        "bbox": bbox,
                                        "tiff": tiff_asset,
                                        "base_url": base_url,
                                    }
                                    self._cache_tile_by_bbox(city, non_matching_tile)

                                if not bbox:
                                    self.logger.info(f"[TerrainService] DEBUG: Tile has no bbox")
                                elif not tiff_asset:
                                    self.logger.info(f"[TerrainService] DEBUG: Tile has no tiff asset")
                                else:
                                    self.logger.info(f"[TerrainService] DEBUG: Coordinate {lng}, {lat} not in bbox {bbox}")

                        except Exception as tile_e:
                            self.logger.warning(f"[TerrainService] DEBUG: Error processing tile {j+1}: {tile_e}")
                            continue

                except Exception as collection_e:
                    self.logger.warning(f"[TerrainService] DEBUG: Error processing collection '{collection_name}': {collection_e}")
                    continue

            self.logger.error(f"[TerrainService] DEBUG: No matching tile found for {lng}, {lat} in city '{city}'")
            return None

        except Exception as e:
            self.logger.error(f"[TerrainService] DEBUG: Failed to find DEM tile: {e}")
            return None

    def clear_coordinate_cache(self):
        """Clear both coordinate and bbox tile caches"""
        coord_cache_size = len(self.coordinate_tile_cache)
        bbox_cache_size = sum(len(tiles) for tiles in self.tile_bbox_cache.values())

        self.coordinate_tile_cache.clear()
        self.tile_bbox_cache.clear()

        self.logger.info(f"[TerrainService] Cleared coordinate cache ({coord_cache_size} entries) and bbox cache ({bbox_cache_size} tiles)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about both coordinate and bbox caches"""
        bbox_cache_cities = list(self.tile_bbox_cache.keys())
        bbox_cache_total = sum(len(tiles) for tiles in self.tile_bbox_cache.values())

        return {
            'coordinate_cache_size': len(self.coordinate_tile_cache),
            'bbox_cache_size': bbox_cache_total,
            'bbox_cache_cities': bbox_cache_cities,
            'bbox_cache_by_city': {city: len(tiles) for city, tiles in self.tile_bbox_cache.items()},
            'cache_precision': self.cache_precision,
            'coordinate_cached_cities': list(set(key.split('_')[0] for key in self.coordinate_tile_cache.keys())),
            'coordinate_cache_keys': list(self.coordinate_tile_cache.keys())
        }

    def _extract_mapbox_tile(self, terrain_bounds: Dict[str, Any], zoom_level: int = 16) -> Optional[str]:
        """Extract Mapbox tile URL for the terrain bounds area"""
        try:
            center_lng, center_lat = terrain_bounds['center']
            width = int(terrain_bounds['width'] * 111320 * 2)  # Convert to approximate pixels
            height = int(terrain_bounds['height'] * 111320 * 2)

            # Clamp dimensions to reasonable limits
            width = min(max(width, 400), 1280)
            height = min(max(height, 400), 1280)

            # Construct Mapbox Static API URL
            mapbox_url = (
                f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
                f"{center_lng},{center_lat},{zoom_level}/{width}x{height}@2x"
                f"?access_token={self._get_mapbox_token()}"
            )

            self.logger.info(f"[TerrainService] Generated Mapbox tile URL: {mapbox_url}")
            return mapbox_url

        except Exception as e:
            self.logger.error(f"[TerrainService] Failed to extract Mapbox tile: {e}")
            return None

    def _get_mapbox_token(self) -> str:
        """Get Mapbox access token from config"""
        if hasattr(self, 'mapbox_token') and self.mapbox_token:
            return self.mapbox_token

        # Fallback to environment variable
        token = os.getenv('MAPBOX_TOKEN')
        if not token:
            self.logger.warning("[TerrainService] No Mapbox token configured")
        return token

    def _process_elevation_data(self, dem_tile: Dict[str, Any], property_shape: Any, progress_callback=None) -> Optional[Dict[str, Any]]:
        """Process elevation data from DEM tile with progress tracking"""
        try:
            def update_progress_internal(percentage: int, message: str = None):
                """Internal progress updater"""
                if progress_callback:
                    # Map internal processing to step 6 with sub-percentages
                    overall_percentage = 50 + (percentage * 0.2)  # 50-70% range
                    progress_callback(6, message or "Processing terrain data", overall_percentage)

            # Download DEM file if needed
            tiff_url = dem_tile["base_url"] + dem_tile["tiff"]
            tiff_path = f"temp_{dem_tile['id']}.tiff"

            if not os.path.exists(tiff_path):
                self._log_operation("Downloading DEM", tiff_url)
                update_progress_internal(0, "Downloading elevation data...")

                with requests.get(tiff_url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0

                    with open(tiff_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                download_percent = (downloaded / total_size) * 30  # 0-30% of internal progress
                                update_progress_internal(download_percent, f"Downloading: {download_percent:.0f}%")

            update_progress_internal(35, "Transforming coordinates...")

            # Transform to NZTM and buffer
            project_to_nztm = Transformer.from_crs("EPSG:4326", "EPSG:2193", always_xy=True).transform
            geom_nztm_shapely = shapely_transform(project_to_nztm, property_shape)

            update_progress_internal(45, "Calculating buffer zones...")
            minx, miny, maxx, maxy = geom_nztm_shapely.bounds
            buffer_dist = 0.1 * max(maxx - minx, maxy - miny)
            geom_nztm_buffered = geom_nztm_shapely.buffer(buffer_dist)
            geom_nztm_buffered_geojson = mapping(geom_nztm_buffered)

            # Process elevation data
            update_progress_internal(55, "Reading elevation data...")
            with rasterio.open(tiff_path) as src:
                out_image, out_transform = rasterio.mask.mask(
                    src, [geom_nztm_buffered_geojson], crop=True, filled=True, nodata=0
                )

                update_progress_internal(65, "Processing elevation values...")
                arr = out_image[0].astype(float)
                arr[arr == 0] = np.nan

                update_progress_internal(75, "Smoothing terrain data...")
                valid_mask = ~np.isnan(arr)
                arr_filled = np.where(valid_mask, arr, np.nanmean(arr))
                arr_light_smooth = gaussian_filter(arr_filled, sigma=0.7)
                arr_light_smooth[~valid_mask] = np.nan
                base_level = np.nanmin(arr_light_smooth)

                update_progress_internal(85, "Generating coordinate grids...")
                height, width = arr.shape
                rows = np.arange(height)
                cols = np.arange(width)
                meshgrid_cols, meshgrid_rows = np.meshgrid(cols, rows)
                xs, ys = xy(out_transform, meshgrid_rows, meshgrid_cols, offset='center')
                xs = np.array(xs).reshape(arr.shape)
                ys = np.array(ys).reshape(arr.shape)

                # Convert to relative coordinates
                xs_rel = xs - xs.min()
                ys_rel = ys - ys.min()
                width_m = xs_rel.max()
                length_m = ys_rel.max()

                update_progress_internal(90, "Finalizing terrain model...")

                # Clean up temp file
                try:
                    os.remove(tiff_path)
                except:
                    pass

                # Handle MultiPolygon geometry
                if isinstance(geom_nztm_shapely, MultiPolygon):
                    # Select the largest polygon in the MultiPolygon
                    largest_polygon = max(geom_nztm_shapely.geoms, key=lambda polygon: polygon.area)
                    boundary_coords = {
                        'x': (np.array(largest_polygon.exterior.xy[0]) - xs.min()).tolist(),
                        'y': (np.array(largest_polygon.exterior.xy[1]) - ys.min()).tolist()
                    }
                else:
                    boundary_coords = {
                        'x': (np.array(geom_nztm_shapely.exterior.xy[0]) - xs.min()).tolist(),
                        'y': (np.array(geom_nztm_shapely.exterior.xy[1]) - ys.min()).tolist()
                    }

                # Make elevation data relative to base level (so base becomes 0)
                arr_relative = arr_light_smooth - base_level

                update_progress_internal(95, "Converting data format...")
                # Convert numpy arrays to lists and handle NaN values
                elevation_data = np.nan_to_num(arr_relative, nan=0.0).tolist()
                x_coords = np.nan_to_num(xs_rel, nan=0.0).tolist()
                y_coords = np.nan_to_num(ys_rel, nan=0.0).tolist()

                # Base level is now 0 since we made elevation relative
                adjusted_base_level = 0.0

                update_progress_internal(100, "Terrain processing complete!")

                return {
                    'elevation_data': elevation_data,
                    'x_coords': x_coords,
                    'y_coords': y_coords,
                    'base_level': float(adjusted_base_level),
                    'width_m': float(width_m),
                    'length_m': float(length_m),
                    'boundary_coords': boundary_coords,
                    'original_base_level': float(base_level)  # Keep original for reference
                }

        except Exception as e:
            self.logger.error(f"Failed to process elevation data: {e}")
            return None


# Global service instance
terrain_service = TerrainService()