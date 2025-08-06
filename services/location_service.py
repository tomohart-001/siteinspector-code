
"""
Location Service Module
Handles location selection, geocoding, and validation
"""
import requests
from typing import Dict, Any, Optional, Tuple, List
from utils.logger import app_logger
from utils.error_handler import ErrorHandler, ErrorCategories


class LocationService:
    """Service for handling location operations"""
    
    # New Zealand city coordinates
    NZ_CITIES = {
        'Auckland': {'lat': -36.8485, 'lng': 174.7633},
        'Wellington': {'lat': -41.2865, 'lng': 174.7762},
        'Christchurch': {'lat': -43.5321, 'lng': 172.6362},
        'Hamilton': {'lat': -37.7870, 'lng': 175.2793},
        'Tauranga': {'lat': -37.6878, 'lng': 176.1651},
        'Dunedin': {'lat': -45.8788, 'lng': 170.5028}
    }
    
    @staticmethod
    def get_city_coordinates(city_name: str) -> Optional[Dict[str, float]]:
        """
        Get coordinates for a predefined New Zealand city
        
        Args:
            city_name: Name of the city
            
        Returns:
            Dictionary with lat/lng coordinates or None if not found
        """
        try:
            coordinates = LocationService.NZ_CITIES.get(city_name)
            if coordinates:
                app_logger.info(f"Retrieved coordinates for {city_name}: {coordinates}")
                return coordinates
            else:
                app_logger.warning(f"City {city_name} not found in predefined cities")
                return None
        except Exception as e:
            app_logger.error(f"Error getting city coordinates for {city_name}", e)
            return None
    
    @staticmethod
    def geocode_location(query: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Geocode a location query using OpenStreetMap Nominatim
        
        Args:
            query: Location search query
            
        Returns:
            Tuple of (location_data, error_message)
        """
        try:
            if not query or not query.strip():
                return None, "Location query cannot be empty"
            
            # Sanitize query
            query = query.strip()[:100]  # Limit length
            
            app_logger.info(f"Geocoding location: {query}")
            
            # Use Nominatim for geocoding
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'format': 'json',
                'q': query,
                'limit': 1,
                'addressdetails': 1
            }
            
            # Add User-Agent as required by Nominatim
            headers = {
                'User-Agent': 'EngineRoom/1.0 (engineering application)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                app_logger.warning(f"No results found for location: {query}")
                return None, f"No results found for '{query}'"
            
            result = data[0]
            location_data = {
                'lat': float(result['lat']),
                'lng': float(result['lon']),
                'display_name': result['display_name'],
                'address': result.get('address', {}),
                'importance': result.get('importance', 0)
            }
            
            app_logger.info(f"Successfully geocoded {query} to {location_data['display_name']}")
            return location_data, None
            
        except requests.exceptions.Timeout:
            error_msg = "Location search timed out. Please try again."
            app_logger.error(f"Geocoding timeout for query: {query}")
            return None, error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = "Location search service unavailable. Please try again later."
            app_logger.error(f"Geocoding request error for query {query}", e)
            return None, error_msg
            
        except (ValueError, KeyError) as e:
            error_msg = "Invalid location data received. Please try a different search."
            app_logger.error(f"Geocoding data parsing error for query {query}", e)
            return None, error_msg
            
        except Exception as e:
            error_msg = "Location search failed. Please try again."
            app_logger.error(f"Unexpected geocoding error for query {query}", e)
            return None, error_msg
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> Tuple[bool, List[str]]:
        """
        Validate latitude and longitude coordinates
        
        Args:
            lat: Latitude value
            lng: Longitude value
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            # Check if values are numeric
            lat = float(lat)
            lng = float(lng)
            
            # Validate ranges
            if not (-90 <= lat <= 90):
                errors.append(f"Invalid latitude {lat}. Must be between -90 and 90")
            
            if not (-180 <= lng <= 180):
                errors.append(f"Invalid longitude {lng}. Must be between -180 and 180")
            
            # Coordinates validated globally - no geographic restrictions
            
        except (ValueError, TypeError):
            errors.append("Coordinates must be valid numbers")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def format_location_for_storage(location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format location data for consistent storage"""
        try:
            lat = float(location_data.get('lat', 0))
            lng = float(location_data.get('lng', 0))
            
            # Simple validation
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                raise ValueError("Invalid coordinates")
            
            return {
                'lat': lat,
                'lng': lng,
                'name': location_data.get('display_name', location_data.get('name', 'Unknown Location')),
                'address': location_data.get('address', {})
            }
            
        except Exception as e:
            app_logger.error("Error formatting location data", e)
            raise
    
    @staticmethod
    def get_location_summary(location_data: Dict[str, Any]) -> str:
        """Get a human-readable summary of location data"""
        try:
            name = location_data.get('name', 'Unknown Location')
            lat = location_data.get('lat', 0)
            lng = location_data.get('lng', 0)
            
            return f"{name} ({lat:.4f}, {lng:.4f})"
            
        except Exception as e:
            app_logger.error("Error creating location summary", e)
            return "Unknown Location"
    
    @staticmethod
    def find_nearby_locations(user_lat: float, user_lng: float, radius_km: int = 50) -> List[Dict[str, Any]]:
        """
        Find nearby suburbs and cities based on user's coordinates
        
        Args:
            user_lat: User's latitude
            user_lng: User's longitude
            radius_km: Search radius in kilometers
            
        Returns:
            List of nearby location dictionaries, prioritizing suburbs
        """
        try:
            app_logger.info(f"Finding nearby locations within {radius_km}km of {user_lat}, {user_lng}")
            
            # First, try to find suburbs specifically
            suburbs = LocationService._search_nearby_places(user_lat, user_lng, 'suburb', radius_km)
            
            # If we don't have enough suburbs, search for cities/towns
            if len(suburbs) < 4:
                cities = LocationService._search_nearby_places(user_lat, user_lng, 'city', radius_km)
                towns = LocationService._search_nearby_places(user_lat, user_lng, 'town', radius_km)
                
                # Combine and prioritize suburbs, then cities, then towns
                all_locations = suburbs + cities + towns
            else:
                all_locations = suburbs
            
            # If still no results and coordinates appear to be outside NZ, suggest fallback locations
            if not all_locations and not LocationService._is_in_new_zealand(user_lat, user_lng):
                return LocationService._get_regional_fallback_locations(user_lat, user_lng)
            
            # Process and clean up results
            processed_locations = []
            seen_names = set()
            
            for location in all_locations:
                try:
                    lat = float(location['lat'])
                    lng = float(location['lon'])
                    
                    # Calculate distance
                    distance = LocationService._calculate_distance(user_lat, user_lng, lat, lng)
                    
                    if distance <= radius_km:
                        # Extract the best name
                        address = location.get('address', {})
                        name = (address.get('suburb') or 
                               address.get('city') or 
                               address.get('town') or 
                               address.get('village') or
                               location.get('display_name', '').split(',')[0])
                        
                        if name and len(name.strip()) > 1:
                            clean_name = name.strip()
                            name_lower = clean_name.lower()
                            
                            # Avoid duplicates and generic names
                            if (name_lower not in seen_names and 
                                not any(generic in name_lower for generic in ['unnamed', 'untitled', 'area', 'region'])):
                                
                                seen_names.add(name_lower)
                                processed_locations.append({
                                    'name': clean_name,
                                    'lat': lat,
                                    'lng': lng,
                                    'distance_km': round(distance, 1),
                                    'display_name': location.get('display_name', clean_name),
                                    'type': LocationService._get_location_type(address)
                                })
                                
                except (ValueError, KeyError) as e:
                    app_logger.warning(f"Error processing location result: {e}")
                    continue
            
            # Sort by distance and prioritize suburbs
            processed_locations.sort(key=lambda x: (x['type'] != 'suburb', x['distance_km']))
            
            # Return exactly 4 locations
            final_locations = processed_locations[:4]
            
            app_logger.info(f"Found {len(final_locations)} nearby locations: {[loc['name'] for loc in final_locations]}")
            return final_locations
            
        except Exception as e:
            app_logger.error(f"Error finding nearby locations: {e}")
            return LocationService._get_regional_fallback_locations(user_lat, user_lng)
    
    @staticmethod
    def _search_nearby_places(user_lat: float, user_lng: float, place_type: str, radius_km: int) -> List[Dict[str, Any]]:
        """Search for specific types of places nearby"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            
            # Create a tighter search box based on radius
            lat_offset = radius_km / 111.0  # Rough conversion km to degrees
            lng_offset = radius_km / (111.0 * abs(user_lat))  # Adjust for latitude
            
            params = {
                'format': 'json',
                'q': place_type,
                'limit': 20,
                'addressdetails': 1,
                'viewbox': f"{user_lng - lng_offset},{user_lat - lat_offset},{user_lng + lng_offset},{user_lat + lat_offset}",
                'bounded': 1
            }
            
            headers = {
                'User-Agent': 'EngineRoom/1.0 (engineering application)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            app_logger.warning(f"Error searching for {place_type}: {e}")
            return []
    
    @staticmethod
    def _is_in_new_zealand(lat: float, lng: float) -> bool:
        """Check if coordinates are within New Zealand bounds"""
        return -47 <= lat <= -34 and 166 <= lng <= 179
    
    @staticmethod
    def _get_location_type(address: Dict[str, Any]) -> str:
        """Determine the type of location from address components"""
        if address.get('suburb'):
            return 'suburb'
        elif address.get('city'):
            return 'city'
        elif address.get('town'):
            return 'town'
        else:
            return 'other'
    
    @staticmethod
    def _get_regional_fallback_locations(user_lat: float, user_lng: float) -> List[Dict[str, Any]]:
        """Provide fallback location suggestions based on approximate region"""
        
        # Determine which region the user might be in based on coordinates
        if LocationService._is_in_new_zealand(user_lat, user_lng):
            # If in NZ, suggest major centers
            if user_lat > -38:  # Northern NZ
                fallback_cities = ['Auckland', 'Hamilton', 'Tauranga', 'Wellington']
            else:  # Southern NZ
                fallback_cities = ['Wellington', 'Christchurch', 'Dunedin', 'Queenstown']
        else:
            # If outside NZ, determine likely region and suggest appropriate locations
            if -34 <= user_lat <= -25 and 150 <= user_lng <= 155:  # Sydney region
                fallback_locations = [
                    {'name': 'Sydney', 'lat': -33.8688, 'lng': 151.2093},
                    {'name': 'Parramatta', 'lat': -33.8151, 'lng': 151.0000},
                    {'name': 'Bondi', 'lat': -33.8915, 'lng': 151.2767},
                    {'name': 'Manly', 'lat': -33.7969, 'lng': 151.2840}
                ]
            elif -38 <= user_lat <= -35 and 144 <= user_lng <= 146:  # Melbourne region
                fallback_locations = [
                    {'name': 'Melbourne', 'lat': -37.8136, 'lng': 144.9631},
                    {'name': 'Richmond', 'lat': -37.8197, 'lng': 144.9850},
                    {'name': 'St Kilda', 'lat': -37.8677, 'lng': 144.9811},
                    {'name': 'Brunswick', 'lat': -37.7689, 'lng': 144.9631}
                ]
            elif -28 <= user_lat <= -25 and 152 <= user_lng <= 154:  # Brisbane region
                fallback_locations = [
                    {'name': 'Brisbane', 'lat': -27.4698, 'lng': 153.0251},
                    {'name': 'South Bank', 'lat': -27.4748, 'lng': 153.0235},
                    {'name': 'Fortitude Valley', 'lat': -27.4574, 'lng': 153.0370},
                    {'name': 'New Farm', 'lat': -27.4698, 'lng': 153.0507}
                ]
            else:
                # Default to major Australian cities if region unclear
                fallback_locations = [
                    {'name': 'Sydney', 'lat': -33.8688, 'lng': 151.2093},
                    {'name': 'Melbourne', 'lat': -37.8136, 'lng': 144.9631},
                    {'name': 'Brisbane', 'lat': -27.4698, 'lng': 153.0251},
                    {'name': 'Perth', 'lat': -31.9505, 'lng': 115.8605}
                ]
            
            # Add distance calculations for fallback locations
            for location in fallback_locations:
                location['distance_km'] = round(
                    LocationService._calculate_distance(user_lat, user_lng, location['lat'], location['lng']), 1
                )
                location['display_name'] = location['name']
                location['type'] = 'city'
            
            app_logger.info(f"Using regional fallback locations for coordinates outside NZ: {user_lat}, {user_lng}")
            return fallback_locations
        
        # For NZ fallback, use predefined cities
        fallback_locations = []
        for city in fallback_cities:
            if city in LocationService.NZ_CITIES:
                coords = LocationService.NZ_CITIES[city]
                distance = LocationService._calculate_distance(user_lat, user_lng, coords['lat'], coords['lng'])
                fallback_locations.append({
                    'name': city,
                    'lat': coords['lat'],
                    'lng': coords['lng'],
                    'distance_km': round(distance, 1),
                    'display_name': city,
                    'type': 'city'
                })
        
        # Sort by distance and return 4
        fallback_locations.sort(key=lambda x: x['distance_km'])
        return fallback_locations[:4]
    
    @staticmethod
    def _calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate approximate distance between two points in kilometers"""
        import math
        
        # Simple haversine formula approximation
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng / 2) ** 2)
        
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        
        return c * r
