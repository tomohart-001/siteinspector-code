"""
Property Service Module
Handles property boundary data from LINZ and other sources
"""
import os
import requests
from typing import Dict, Any, Optional, List, Tuple
from shapely.geometry import Point, shape
from utils.logger import app_logger
from .base_service import BaseService


class PropertyService(BaseService):
    """Service for handling property boundary operations"""

    def __init__(self):
        super().__init__("PropertyService")
        # LINZ API configuration
        self.linz_api_key = os.getenv('PROPERTY_API_KEY')  # Your API key
        self.property_titles_layer = 50772  # NZ Property Titles layer
        self.linz_base_url = "https://data.linz.govt.nz/services/query/v1/vector.json"

    def get_property_boundaries_at_point(self, lat: float, lng: float, radius_m: int = 10000) -> Dict[str, Any]:
        """
        Get property boundaries containing or near a specific point

        Args:
            lat: Latitude of the point
            lng: Longitude of the point  
            radius_m: Search radius in meters

        Returns:
            Dictionary with property boundary data
        """
        max_retries = 2
        timeout_seconds = 10  # Reduced from 15 to 10 seconds

        for attempt in range(max_retries + 1):
            try:
                app_logger.info(f"Fetching property boundaries for point: {lat}, {lng} (attempt {attempt + 1})")

                # Build LINZ API request
                url = (
                    f"{self.linz_base_url}"
                    f"?key={self.linz_api_key}&layer={self.property_titles_layer}"
                    f"&x={lng}&y={lat}"
                    f"&max_results=5&radius={radius_m}&geometry=true&with_field_names=true"
                )

                headers = {"User-Agent": "EngineRoom/1.0 (engineering application)"}

                # Use shorter timeout and connection timeout
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=(5, timeout_seconds),  # (connection_timeout, read_timeout)
                    stream=False
                )
                response.raise_for_status()

                data = response.json()
                features = data.get("vectorQuery", {}).get("layers", {}).get(str(self.property_titles_layer), {}).get("features", [])

                app_logger.info(f"Retrieved {len(features)} property features from LINZ on attempt {attempt + 1}")

                return self._process_property_features(features, lat, lng)

            except requests.exceptions.Timeout as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 2  # Progressive backoff: 2s, 4s
                    app_logger.warning(f"LINZ API timeout on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    app_logger.error(f"LINZ API timeout after {max_retries + 1} attempts: {e}")
                    return self._create_timeout_response()

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 3  # Progressive backoff for connection issues
                    app_logger.warning(f"LINZ API connection error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    import time
                    time.sleep(wait_time)
                    continue
                else:
                    app_logger.error(f"LINZ API connection failed after {max_retries + 1} attempts: {e}")
                    return self._create_connection_error_response()

            except requests.exceptions.RequestException as e:
                app_logger.error(f"LINZ API request failed: {e}")
                return self._create_error_response(f"Property data service temporarily unavailable")

            except Exception as e:
                app_logger.error(f"Error processing property boundaries: {e}")
                return self._create_error_response(f"Property boundary processing failed: {e}")

        # Should not reach here, but just in case
        return self._create_timeout_response()

    def _process_property_features(self, features: List[Dict], query_lat: float, query_lng: float) -> Dict[str, Any]:
        """Process property features from LINZ API response"""
        try:
            query_point = Point(query_lng, query_lat)
            processed_properties = []
            containing_property = None

            for feature in features:
                try:
                    geometry = feature.get("geometry", {})
                    properties = feature.get("properties", {})

                    # Convert geometry to Shapely object
                    parcel_shape = shape(geometry)

                    # Check if this property contains the query point
                    contains_point = parcel_shape.contains(query_point)

                    # Process polygon coordinates for Mapbox
                    property_coords = self._extract_polygon_coordinates(parcel_shape)

                    if property_coords:
                        property_data = {
                            'id': f"property_{len(processed_properties)}",
                            'coordinates': property_coords,
                            'contains_query_point': contains_point,
                            'title': properties.get('titles', 'Unknown Title'),
                            'area_ha': properties.get('area_ha'),
                            'survey_area': properties.get('survey_area'),
                            'land_district': properties.get('land_district'),
                            'territorial_authority': properties.get('territorial_authority'),
                            'properties': properties
                        }

                        processed_properties.append(property_data)

                        # Mark the property that contains the query point
                        if contains_point:
                            containing_property = property_data
                            app_logger.info(f"Found containing property: {property_data['title']}")

                except Exception as e:
                    app_logger.warning(f"Error processing individual property feature: {e}")
                    continue

            return {
                'success': True,
                'properties': processed_properties,
                'containing_property': containing_property,
                'total_count': len(processed_properties),
                'query_point': {'lat': query_lat, 'lng': query_lng}
            }

        except Exception as e:
            app_logger.error(f"Error in property feature processing: {e}")
            return self._create_error_response(f"Feature processing failed: {e}")

    def _extract_polygon_coordinates(self, parcel_shape) -> List[List[List[float]]]:
        """Extract coordinates from Shapely geometry for Mapbox"""
        try:
            coordinates = []

            # Handle both Polygon and MultiPolygon
            if parcel_shape.geom_type == "MultiPolygon":
                for polygon in parcel_shape.geoms:
                    coords = list(polygon.exterior.coords)
                    # Convert to [lng, lat] format for Mapbox
                    mapbox_coords = [[coord[0], coord[1]] for coord in coords]
                    coordinates.append(mapbox_coords)
            elif parcel_shape.geom_type == "Polygon":
                coords = list(parcel_shape.exterior.coords)
                # Convert to [lng, lat] format for Mapbox
                mapbox_coords = [[coord[0], coord[1]] for coord in coords]
                coordinates.append(mapbox_coords)

            return coordinates

        except Exception as e:
            app_logger.error(f"Error extracting polygon coordinates: {e}")
            return []

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'success': False,
            'error': error_message,
            'properties': [],
            'containing_property': None,
            'total_count': 0
        }

    def _create_timeout_response(self) -> Dict[str, Any]:
        """Create timeout-specific response"""
        return {
            'success': False,
            'error': 'Property boundary service timed out. Please try again.',
            'error_type': 'timeout',
            'properties': [],
            'containing_property': None,
            'total_count': 0,
            'user_message': 'Property boundaries are temporarily unavailable due to slow network response.'
        }

    def _create_connection_error_response(self) -> Dict[str, Any]:
        """Create connection error response"""
        return {
            'success': False,
            'error': 'Unable to connect to property boundary service.',
            'error_type': 'connection',
            'properties': [],
            'containing_property': None,
            'total_count': 0,
            'user_message': 'Property boundary service is temporarily unavailable. Please try again later.'
        }

    def get_containing_property_only(self, lat: float, lng: float) -> Dict[str, Any]:
        """
        Get only the property boundary that contains the specified point

        Args:
            lat: Latitude of the point
            lng: Longitude of the point

        Returns:
            Dictionary with only the containing property boundary data
        """
        try:
            app_logger.info(f"Fetching containing property for point: {lat}, {lng}")

            # Get all properties first
            result = self.get_property_boundaries_at_point(lat, lng, radius_m=1000)  # Smaller radius for efficiency

            if not result.get('success'):
                return result

            containing_property = result.get('containing_property')

            if containing_property:
                app_logger.info(f"Found containing property: {containing_property['title']}")
                return {
                    'success': True,
                    'properties': [containing_property],
                    'containing_property': containing_property,
                    'total_count': 1,
                    'query_point': {'lat': lat, 'lng': lng}
                }
            else:
                app_logger.warning(f"No containing property found for point: {lat}, {lng}")
                return {
                    'success': True,
                    'properties': [],
                    'containing_property': None,
                    'total_count': 0,
                    'query_point': {'lat': lat, 'lng': lng},
                    'message': 'No property boundary found containing this point'
                }

        except Exception as e:
            app_logger.error(f"Error getting containing property: {e}")
            return self._create_error_response(f"Containing property lookup failed: {e}")

    def get_property_boundaries_for_address(self, address: str) -> Dict[str, Any]:
        """
        Get property boundaries for a given address

        Args:
            address: Street address to search for

        Returns:
            Dictionary with property boundary data
        """
        try:
            # First geocode the address
            from .location_service import LocationService
            location_data, error = LocationService.geocode_location(address)

            if error or not location_data:
                return self._create_error_response(f"Address geocoding failed: {error}")

            lat = location_data['lat']
            lng = location_data['lng']

            # Then get property boundaries at that location
            return self.get_property_boundaries_at_point(lat, lng)

        except Exception as e:
            app_logger.error(f"Error getting property boundaries for address: {e}")
            return self._create_error_response(f"Address lookup failed: {e}")


# Create service instance
property_service = PropertyService()