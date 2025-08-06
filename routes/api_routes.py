
"""
General API Routes Module
"""
from flask import request, jsonify
from typing import Tuple, Dict, Any
from services import api_calculation_service
from services.location_service import LocationService
from utils.logger import app_logger
from utils.error_handler import ErrorHandler, ErrorCategories
from services import response_service
from utils.timezone_helper import TimezoneHelper


class ApiRoutes:
    """General API route handlers"""

    def register_routes(self, app):
        """Register general API routes"""
        app.route('/api/locations', methods=['GET'])(self.handle_get_locations)
        app.route('/api/calculate-buildable-area', methods=['POST'])(self.handle_calculate_buildable_area)
        app.route('/api/geocode-location', methods=['POST'])(self.handle_geocode_location)
        app.route('/api/set-timezone', methods=['POST'])(self.handle_set_timezone)

    def handle_get_locations(self) -> Tuple[Dict[str, Any], int]:
        """Get available locations for user selection"""
        try:
            # Standard New Zealand locations
            locations = [
                "Auckland", "Wellington", "Christchurch", "Hamilton", 
                "Tauranga", "Dunedin", "Palmerston North", "Hastings",
                "Napier", "Rotorua", "New Plymouth", "Whangarei"
            ]
            return jsonify(locations), 200

        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.UNKNOWN,
                context={'operation': 'get_locations'}
            ), 500

    def handle_calculate_buildable_area(self) -> Tuple[Dict[str, Any], int]:
        """Calculate buildable area based on site parameters"""
        try:
            data = request.get_json()
            if not data:
                return response_service.validation_error("Request body must be JSON")

            site_coords = data.get('site_coords', [])
            requirements = data.get('requirements', {})
            frontage = data.get('frontage', [])
            edge_classifications = data.get('edge_classifications', [])

            if not site_coords or not requirements:
                return response_service.validation_error(
                    "Site coordinates and requirements are required"
                )

            app_logger.info(f"Calculating buildable area - coords: {len(site_coords)}")

            result = api_calculation_service.calculate_buildable_area(
                site_coords=site_coords,
                requirements=requirements,
                frontage=frontage,
                edge_classifications=edge_classifications
            )

            app_logger.info(f"Buildable area calculated: {result.get('buildable_area_m2', 0):.1f} m²")
            return response_service.success(result, "Buildable area calculated successfully")

        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.CALCULATION,
                context={'operation': 'buildable_area_calculation'}
            ), 500

    def handle_geocode_location(self) -> Tuple[Dict[str, Any], int]:
        """Geocode a location query"""
        try:
            data = request.get_json()
            if not data or not data.get('query'):
                return response_service.validation_error('Location query is required'), 400

            query = data['query'].strip()
            if not query:
                return response_service.validation_error('Location query cannot be empty'), 400

            app_logger.info(f"Geocoding location query: {query}")

            # Use the location service to geocode
            location_data, error = LocationService.geocode_location(query)

            if error:
                app_logger.warning(f"Geocoding failed for '{query}': {error}")
                return response_service.validation_error(error), 400

            if not location_data:
                return response_service.validation_error(f"No results found for '{query}'"), 404

            app_logger.info(f"Successfully geocoded '{query}' to {location_data['display_name']}")

            return response_service.success({
                'location': location_data
            }, "Location geocoded successfully")

        except Exception as e:
            app_logger.error(f"Geocoding error: {e}")
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.UNKNOWN,
                context={'operation': 'geocode_location', 'query': data.get('query') if 'data' in locals() else None}
            ), 500

    def handle_set_timezone(self):
        """Set user's timezone preference"""
        try:
            data = request.get_json()
            if not data or 'timezone' not in data:
                return jsonify({'error': 'Timezone is required'}), 400

            timezone_name = data['timezone']

            if TimezoneHelper.set_user_timezone(timezone_name):
                app_logger.info(f"User timezone set to: {timezone_name}")
                return jsonify({'success': True, 'timezone': timezone_name})
            else:
                return jsonify({'error': 'Invalid timezone'}), 400

        except Exception as e:
            app_logger.error(f"Error setting user timezone: {e}")
            return jsonify({'error': 'Failed to set timezone'}), 500
