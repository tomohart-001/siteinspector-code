from flask import Blueprint, request, jsonify, render_template
from utils.logger import app_logger

structural_routes = Blueprint('structural_routes', __name__)

class StructuralRoutes:
    """Structural analysis route handlers"""

    def register_routes(self, app):
        """Register structural analysis routes with Flask app"""
        # Register routes directly with the app
        app.add_url_rule('/structural-analyser', 'structural_analyser', self.handle_structural_analyser, methods=['GET'])
        app.add_url_rule('/api/calculate-structure-masses',
                            'calculate_structure_masses',
                            self.calculate_structure_masses,
                            methods=['POST'])
        app.add_url_rule('/api/get-member-metadata',
                            'get_member_metadata',
                            self.get_member_metadata,
                            methods=['POST'])

    def handle_structural_analyser(self):
        """Handle structural analyser page"""
        try:
            app_logger.info("Structural analyser page requested")

            # Get member data from URL parameters
            member_type = request.args.get('type', 'Unknown Member')
            member_id = request.args.get('id', '')
            category = request.args.get('category', '')
            length = request.args.get('length', '6.0')
            storey = request.args.get('storey', '1')
            total_storeys = request.args.get('totalStoreys', '3')
            tributary_width = request.args.get('tributaryWidth', '3.0')
            designation = request.args.get('designation', '')

            # Create member info string
            member_info = f"{member_type} ({category})"
            if member_id:
                member_info += f" - ID: {member_id}"

            member_data = {
                'type': member_type,
                'id': member_id,
                'category': category,
                'length': float(length) if length else 6.0,
                'storey': int(storey) if storey else 1,
                'total_storeys': int(total_storeys) if total_storeys else 3,
                'tributary_width': float(tributary_width) if tributary_width else 3.0,
                'designation': designation if designation else None
            }

            return render_template('structural_analyser.html', 
                                 member_info=member_info,
                                 member_data=member_data)

        except Exception as e:
            app_logger.error(f"Structural analyser error: {e}")
            return render_template('structural_analyser.html', 
                                 member_info='Error loading member data',
                                 member_data={})

    def calculate_structure_masses(self):
        """Endpoint to calculate mass of structural members"""
        try:
            data = request.get_json()

            # Extract member data from request
            member_type = data.get('type', 'Unknown Member')
            length = data.get('length', 0.0)
            width = data.get('width', 0.0)
            thickness = data.get('thickness', 0.0)
            material = data.get('material', 'Steel')

            # Define densities (kg/m^3)
            densities = {
                'Steel': 7850,
                'Concrete': 2400,
            }

            # Get density
            density = densities.get(material, 7850)

            # Calculate volume
            volume = length * width * thickness

            # Calculate mass
            mass = volume * density

            # Calculate gravity force (N)
            gravity_force = mass * 9.81

            result = {
                'member_type': member_type,
                'volume': volume,
                'mass': mass,
                'gravity_force': gravity_force,
            }

            return jsonify(result), 200

        except Exception as e:
            app_logger.error(f"Mass calculation error: {e}")
            return jsonify({"error": str(e)}), 500

    def get_member_metadata(self):
        """Endpoint to get metadata for structural members"""
        try:
            from services.portal_frame_designer import PortalFrameDesigner

            data = request.get_json()
            structure_type = data.get('structure_type', 'portal_frame')
            parameters = data.get('parameters', {})

            if structure_type == 'portal_frame':
                designer = PortalFrameDesigner()
                result = designer.generate_portal_frame(parameters)

                if result['success']:
                    members = result.get('members', [])

                    # Organize members by type
                    members_by_type = {}
                    for member in members:
                        member_type = member['type']
                        if member_type not in members_by_type:
                            members_by_type[member_type] = []
                        members_by_type[member_type].append(member)

                    return jsonify({
                        'success': True,
                        'members': members,
                        'members_by_type': members_by_type,
                        'statistics': result['stats']
                    }), 200
                else:
                    return jsonify({'success': False, 'error': result['error']}), 400
            else:
                return jsonify({'success': False, 'error': 'Unsupported structure type'}), 400

        except Exception as e:
            app_logger.error(f"Member metadata error: {e}")
            return jsonify({"error": str(e)}), 500

# Create route handler instance
structural_route_handler = StructuralRoutes()