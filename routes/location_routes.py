"""
The LocationRoutes class is modified to focus on API endpoints only, removing the deprecated location selection page.
"""
from flask import request, jsonify, session
from typing import Dict, Any
from auth import get_session_id
from services.location_service import LocationService
from utils.logger import app_logger
from utils.error_handler import ErrorHandler, ValidationError, safe_execute


class LocationRoutes:
    """Location management route handlers - API only"""

    def register_routes(self, app):
        """Register location-related API routes only"""
        routes_to_register = [
            ('/api/save-location', ['POST'], 'save_location', self.handle_save_location, 'Save selected location API', False),
            ('/api/geocode-location', ['POST'], 'geocode_location', self.handle_geocode_location, 'Geocode location API', False),
            ('/api/nearby-locations', ['POST'], 'nearby_locations', self.handle_nearby_locations, 'Get nearby locations API', False),
        ]

        registered_count = 0
        failed_routes = []

        for path, methods, endpoint, handler, description, is_critical in routes_to_register:
            try:
                app_logger.info(f"🔧 Registering location route: {path} ({description})")
                app.route(path, methods=methods, endpoint=endpoint)(handler)
                registered_count += 1
                app_logger.info(f"✅ Successfully registered: {path}")
            except Exception as e:
                error_msg = f"Failed to register {path}: {e}"
                app_logger.error(error_msg)
                failed_routes.append((path, error_msg))
                if is_critical:
                    raise Exception(f"Critical route {path} failed to register: {e}")

        app_logger.info(f"📊 Location routes registration summary: {registered_count} successful, {len(failed_routes)} failed")
        return registered_count, failed_routes

    def handle_save_location(self):
        """Handle saving selected location to session"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(ErrorHandler.handle_validation_error("Location data is required")[0]), 400

            # Extract location information
            lat = data.get('lat')
            lng = data.get('lng')
            name = data.get('name', '')

            if lat is None or lng is None:
                return jsonify(ErrorHandler.handle_validation_error("Latitude and longitude are required")[0]), 400

            # Validate coordinates
            is_valid, errors = LocationService.validate_coordinates(lat, lng)
            if not is_valid:
                return jsonify(ErrorHandler.handle_validation_error(f"Invalid coordinates: {'; '.join(errors)}")[0]), 400

            # Store in session
            session_id = get_session_id()
            session['user_location'] = name
            session['location_data'] = {
                'lat': float(lat),
                'lng': float(lng),
                'name': name
            }

            # Store selected location flag
            session['location_selected'] = True

            app_logger.info(f"Location saved successfully: {name} ({lat}, {lng})", {
                'session_id': session_id[:8],
                'location': name,
                'coordinates': {'lat': lat, 'lng': lng}
            })

            return jsonify({
                'success': True,
                'message': 'Location saved successfully',
                'location': {
                    'name': name,
                    'lat': float(lat),
                    'lng': float(lng)
                }
            }), 200

        except Exception as e:
            app_logger.error("Failed to save location", e)
            error_response = ErrorHandler.handle_error(e, context={'endpoint': 'save_location'})
            return jsonify(error_response), 500

    def handle_geocode_location(self):
        """Handle location geocoding requests"""
        try:
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify(ErrorHandler.handle_validation_error("Location query is required")[0]), 400

            query = data.get('query', '').strip()
            if not query:
                return jsonify(ErrorHandler.handle_validation_error("Location query cannot be empty")[0]), 400

            app_logger.info(f"Geocoding request for: {query}")

            # Attempt geocoding
            location_data, error = LocationService.geocode_location(query)

            if error:
                app_logger.warning(f"Geocoding failed for {query}: {error}")
                return jsonify({
                    'success': False,
                    'error': error,
                    'query': query
                }), 404

            # Format location data
            formatted_location = LocationService.format_location_for_storage(location_data)

            # Store in session
            session_id = get_session_id()
            session[f'geocoded_location_{session_id}'] = formatted_location

            app_logger.info(f"Successfully geocoded {query} to {LocationService.get_location_summary(formatted_location)}")

            return jsonify({
                'success': True,
                'location': formatted_location,
                'summary': LocationService.get_location_summary(formatted_location)
            })

        except Exception as e:
            app_logger.error("Geocoding request failed", e)
            error_response = ErrorHandler.handle_error(e, context={'endpoint': 'geocode_location'})
            return jsonify(error_response), 500

    def handle_nearby_locations(self):
        """Handle requests for nearby locations based on user coordinates"""
        try:
            data = request.get_json()
            if not data:
                return jsonify(ErrorHandler.handle_validation_error("Location data is required")[0]), 400

            lat = data.get('lat')
            lng = data.get('lng')

            if lat is None or lng is None:
                return jsonify(ErrorHandler.handle_validation_error("Latitude and longitude are required")[0]), 400

            # Validate coordinates
            is_valid, errors = LocationService.validate_coordinates(lat, lng)
            if not is_valid:
                return jsonify(ErrorHandler.handle_validation_error(f"Invalid coordinates: {'; '.join(errors)}")[0]), 400

            app_logger.info(f"Finding nearby locations for coordinates: {lat}, {lng}")

            # Find nearby locations
            nearby_locations = LocationService.find_nearby_locations(float(lat), float(lng))

            if not nearby_locations:
                app_logger.warning(f"No nearby locations found for {lat}, {lng}")
                return jsonify({
                    'success': True,
                    'locations': [],
                    'message': 'No nearby locations found'
                })

            app_logger.info(f"Found {len(nearby_locations)} nearby locations")

            return jsonify({
                'success': True,
                'locations': nearby_locations,
                'user_location': {'lat': float(lat), 'lng': float(lng)}
            })

        except Exception as e:
            app_logger.error("Nearby locations request failed", e)
            error_response = ErrorHandler.handle_error(e, context={'endpoint': 'nearby_locations'})
            return jsonify(error_response), 500


# Create route handler instance  
location_route_handler = LocationRoutes()