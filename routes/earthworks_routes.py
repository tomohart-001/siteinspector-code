
"""
Earthworks Routes Module - Handles earthworks calculation requests
"""
from flask import request, jsonify
from utils.logger import app_logger

# Try to import earthworks service with graceful fallback
try:
    from services.earthworks_service import earthworks_service
    EARTHWORKS_AVAILABLE = earthworks_service.available if earthworks_service else False
    app_logger.info(f"Earthworks service import result: available={EARTHWORKS_AVAILABLE}")
except ImportError as e:
    app_logger.warning(f"Earthworks service unavailable: {e}")
    earthworks_service = None
    EARTHWORKS_AVAILABLE = False


class EarthworksRoutes:
    """Earthworks route handlers"""

    def handle_calculate_earthworks(self):
        """Handle earthworks calculation API endpoint"""
        try:
            if not EARTHWORKS_AVAILABLE:
                app_logger.warning("Earthworks calculation requested but service unavailable")
                return jsonify({
                    'success': False,
                    'error': 'Earthworks calculation service unavailable - missing geospatial dependencies'
                }), 503

            app_logger.info("Earthworks calculation request - Service available: True")

            # Get request data
            data = request.get_json()
            app_logger.info(f"Earthworks calculation request: {list(data.keys()) if data else 'No data'}")

            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            # Validate required fields
            terrain_data = data.get('terrain_data')
            platform_coords = data.get('platform_coords')
            
            if not terrain_data:
                return jsonify({'success': False, 'error': 'Terrain data required'}), 400
            
            if not platform_coords:
                return jsonify({'success': False, 'error': 'Platform coordinates required'}), 400

            # Optional parameters
            ffl = data.get('ffl')  # Can be None
            optimize_ffl = data.get('optimize_ffl', False)

            app_logger.info(f"Earthworks calculation - Platform: {len(platform_coords)} points, FFL: {ffl}, Optimize: {optimize_ffl}")

            # Calculate earthworks
            result = earthworks_service.calculate_earthworks(
                terrain_data=terrain_data,
                platform_coords=platform_coords,
                ffl=ffl,
                optimize_ffl=optimize_ffl
            )

            if result.get('success'):
                app_logger.info(f"Earthworks calculated - Cut: {result.get('cut_volume_m3', 0):.1f}m³, Fill: {result.get('fill_volume_m3', 0):.1f}m³")
            else:
                app_logger.error(f"Earthworks calculation failed: {result.get('error')}")

            return jsonify(result)

        except Exception as e:
            app_logger.error(f"Earthworks calculation error: {e}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500

    def handle_optimize_ffl(self):
        """Handle FFL optimization endpoint"""
        try:
            if not EARTHWORKS_AVAILABLE:
                return jsonify({
                    'success': False,
                    'error': 'Earthworks service unavailable'
                }), 503

            data = request.get_json()
            if not data or 'terrain_data' not in data or 'platform_coords' not in data:
                return jsonify({'success': False, 'error': 'Terrain data and platform coordinates required'}), 400

            # Calculate optimal FFL only
            result = earthworks_service.calculate_earthworks(
                terrain_data=data['terrain_data'],
                platform_coords=data['platform_coords'],
                ffl=None,
                optimize_ffl=True
            )

            if result.get('success'):
                return jsonify({
                    'success': True,
                    'optimal_ffl': result['ffl'],
                    'ffl_relative_to_base': result['ffl_relative_to_base']
                })
            else:
                return jsonify(result)

        except Exception as e:
            app_logger.error(f"FFL optimization error: {e}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500

    def register_routes(self, app):
        """Register routes with Flask app"""
        self.app = app

        with app.app_context():
            # Main earthworks calculation API
            self.app.add_url_rule('/api/calculate-earthworks', 'calculate_earthworks',
                                 self.handle_calculate_earthworks, methods=['POST'])

            app_logger.info(f"✅ Successfully registered: /api/calculate-earthworks")

            # FFL optimization endpoint
            self.app.add_url_rule('/api/optimize-ffl', 'optimize_ffl',
                                 self.handle_optimize_ffl, methods=['POST'])

            app_logger.info(f"✅ Successfully registered: /api/optimize-ffl")
