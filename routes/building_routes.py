from flask import Blueprint, request, jsonify, session
from utils.logger import app_logger
from services.building_service import building_service
import json

from services.rigid_frame_designer import RigidFrameDesigner
from services.hybrid_frame_designer import HybridFrameDesigner
from services.portal_frame_designer import PortalFrameDesigner  # Import the PortalFrameDesigner
from services.beam_service import BeamService


building_routes = Blueprint('building_routes', __name__)


class BuildingRoutes:
    """Building route handlers"""

    def register_routes(self, app):
        """Register building routes with Flask app"""
        app.route('/api/generate-3d-building', methods=['POST'], endpoint='generate_3d_building')(self.handle_generate_3d_building)
        app.route('/api/save-building-design', methods=['POST'], endpoint='save_building_design')(self.handle_save_building_design)

        app.route('/api/generate-rigid-frame', methods=['POST'])(self.handle_generate_rigid_frame)
        app.route('/api/generate-hybrid-frame', methods=['POST'])(self.handle_generate_hybrid_frame)
        app.route('/api/beam-specifications', methods=['GET'])(self.handle_get_beam_specifications)
        app.route('/api/beam-specifications/metadata', methods=['GET'])(self.handle_get_beam_specifications_metadata)
        app.route('/api/beam-specifications', methods=['POST'])(self.handle_add_beam_specification)
        app.route('/api/save-beam-selection', methods=['POST'])(self.handle_save_beam_selection)
        app.route('/api/get-beam-selections', methods=['GET'])(self.handle_get_beam_selections)
        app.route('/api/get-beam-designation', methods=['GET'])(self.handle_get_beam_designation)

        # Building design routes
        app.add_url_rule('/api/generate-rigid-frame', 'generate_rigid_frame', self.handle_generate_rigid_frame, methods=['POST'])
        app.add_url_rule('/api/generate-hybrid-frame', 'generate_hybrid_frame', self.handle_generate_hybrid_frame, methods=['POST'])
        app.add_url_rule('/api/generate-portal-frame', 'generate_portal_frame', self.handle_generate_portal_frame, methods=['POST'])

    def handle_generate_3d_building(self):
        """Generate 3D building model based on site and parameters"""
        try:
            data = request.get_json()
            app_logger.info(f"3D building generation request: {data.keys()}")

            site_coords = data.get('site_coords', [])
            buildable_area = data.get('buildable_area', {})
            building_params = data.get('building_params', {})

            # Use building service for generation
            result = building_service.generate_3d_building(site_coords, buildable_area, building_params)

            if result.get('success'):
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            app_logger.error(f"3D building generation error: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_save_building_design(self):
        """Save 3D building design to session"""
        try:
            data = request.get_json()
            building_data = data.get('building_data', {})
            site_id = data.get('site_id', 'unknown')

            # Use building service for saving
            result = building_service.save_building_design(building_data, site_id)

            # Also save to session for now
            if result.get('success'):
                session['building_design'] = {
                    'building_data': building_data,
                    'site_id': site_id,
                    'created_at': json.dumps(None, default=str)
                }

            status_code = 200 if result.get('success') else 400
            return jsonify(result), status_code

        except Exception as e:
            app_logger.error(f"Building design save error: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)

            }), 500

    def handle_generate_rigid_frame(self):
        """Generate a rigid frame structure"""
        try:
            data = request.get_json()

            # Initialize rigid frame designer
            designer = RigidFrameDesigner()

            # Generate the rigid frame
            result = designer.generate_rigid_frame(data)

            if result['success']:
                # Convert plotly figure to JSON for frontend
                figure_json = result['figure'].to_json()

                return jsonify({
                    'success': True,
                    'figure': figure_json,
                    'stats': result['stats'],
                    'parameters': result['parameters']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error occurred')
                }), 500

        except Exception as e:
            app_logger.error(f"Error generating rigid frame: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_generate_hybrid_frame(self):
        """Generate a hybrid core + frame structure"""
        try:
            data = request.get_json()

            # Initialize hybrid frame designer
            designer = HybridFrameDesigner()

            # Generate the hybrid frame
            result = designer.generate_hybrid_frame(data)

            if result['success']:
                # Convert plotly figure to JSON for frontend
                figure_json = result['figure'].to_json()

                return jsonify({
                    'success': True,
                    'figure': figure_json,
                    'stats': result['stats'],
                    'parameters': result['parameters']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error occurred')
                }), 500

        except Exception as e:
            app_logger.error(f"Error generating hybrid frame: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_generate_portal_frame(self):
        """Generate a portal frame structure"""
        try:
            data = request.get_json()

            # Initialize portal frame designer
            designer = PortalFrameDesigner()

            # Generate the portal frame
            result = designer.generate_portal_frame(data)

            if result['success']:
                # Convert plotly figure to JSON for frontend
                figure_json = result['figure'].to_json()

                return jsonify({
                    'success': True,
                    'figure': figure_json,
                    'stats': result['stats'],
                    'parameters': result['parameters']
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error occurred')
                }), 500

        except Exception as e:
            app_logger.error(f"Error generating portal frame: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_get_beam_specifications(self):
        """Get all beam specifications or filter by designation"""
        try:
            designation = request.args.get('designation')

            if designation:
                # Get specific specification by designation
                spec = BeamService.get_beam_specification_by_designation(designation)
                if spec:
                    return {
                        'success': True,
                        'specifications': [spec]
                    }
                else:
                    return {
                        'success': False,
                        'error': f'No specification found for designation: {designation}'
                    }
            else:
                # Get all specifications
                specs = BeamService.get_all_beam_specifications()

                # Initialize default specs if none exist
                if not specs:
                    BeamService.initialize_default_beam_specifications()
                    specs = BeamService.get_all_beam_specifications()

                return {
                    'success': True,
                    'specifications': specs
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def handle_get_beam_specifications_metadata(self):
        """Get beam specifications metadata for change detection"""
        try:
            metadata = BeamService.get_beam_specifications_metadata()
            return jsonify({
                'success': True,
                'metadata': metadata
            }), 200
        except Exception as e:
            app_logger.error(f"Error getting beam specifications metadata: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_add_beam_specification(self):
        """Add new beam specification"""
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = [
                'material', 'designation', 'section_depth_mm', 'grade_mpa',
                'density_kg_m', 'width_mm', 'flange_thickness_mm', 'web_thickness_mm',
                'section_area_mm2', 'moment_inertia_x_mm4', 'section_modulus_x_mm3',
                'moment_inertia_y_mm4', 'section_modulus_y_mm3'
            ]

            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }

            spec_id = BeamService.add_beam_specification(data)

            return {
                'success': True,
                'specification_id': spec_id
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def handle_save_beam_selection(self):
        """Save user's beam selection"""
        try:
            data = request.get_json()
            session_id = session.get('session_id')

            if not session_id:
                return {
                    'success': False,
                    'error': 'No session found'
                }

            element_type = data.get('element_type')
            beam_spec_id = data.get('beam_specification_id')

            if not element_type or not beam_spec_id:
                return {
                    'success': False,
                    'error': 'Missing element_type or beam_specification_id'
                }

            success = BeamService.save_user_beam_selection(session_id, element_type, beam_spec_id)

            return {
                'success': success
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def handle_get_beam_selections(self):
        """Get user's beam selections"""
        try:
            session_id = session.get('session_id')

            if not session_id:
                return {
                    'success': False,
                    'error': 'No session found'
                }

            selections = BeamService.get_user_beam_selections(session_id)

            return {
                'success': True,
                'selections': selections
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def handle_get_beam_designation(self):
        """Get beam designation for a specific element type"""
        try:
            element_type = request.args.get('element_type')
            if not element_type:
                return jsonify({'success': False, 'error': 'Element type is required'}), 400

            session_id = session.get('session_id')
            if not session_id:
                return jsonify({
                    'success': False,
                    'error': 'No session found'
                }), 400

            designation = BeamService.get_beam_designation_by_type(session_id, element_type)

            if designation:
                return jsonify({
                    'success': True,
                    'designation': designation
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'No designation found for this element type'
                }), 404

        except Exception as e:
            app_logger.error(f"Error getting beam designation: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    def handle_generate_rigid_frame(self):
        """Handle rigid frame generation"""
        try:
            from services.rigid_frame_designer import RigidFrameDesigner

            data = request.get_json()
            designer = RigidFrameDesigner()
            result = designer.generate_rigid_frame(data)

            if result['success']:
                return jsonify({
                    'success': True,
                    'figure': result['figure'].to_json(),
                    'stats': result['stats']
                })
            else:
                return jsonify({'success': False, 'error': result['error']}), 500

        except Exception as e:
            app_logger.error(f"Error generating rigid frame: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_generate_hybrid_frame(self):
        """Handle hybrid frame generation"""
        try:
            from services.hybrid_frame_designer import HybridFrameDesigner

            data = request.get_json()
            designer = HybridFrameDesigner()
            result = designer.generate_hybrid_frame(data)

            if result['success']:
                return jsonify({
                    'success': True,
                    'figure': result['figure'].to_json(),
                    'stats': result['stats']
                })
            else:
                return jsonify({'success': False, 'error': result['error']}), 500

        except Exception as e:
            app_logger.error(f"Error generating hybrid frame: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    def handle_generate_portal_frame(self):
        """Handle portal frame generation"""
        try:
            from services.portal_frame_designer import PortalFrameDesigner

            data = request.get_json()
            designer = PortalFrameDesigner()
            result = designer.generate_portal_frame(data)

            if result['success']:
                return jsonify({
                    'success': True,
                    'figure': result['figure'].to_json(),
                    'stats': result['stats']
                })
            else:
                return jsonify({'success': False, 'error': result['error']}), 500

        except Exception as e:
            app_logger.error(f"Error generating portal frame: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


# Create route handler instance
building_route_handler = BuildingRoutes()