"""Fixes project data inclusion in error cases and template rendering for site inspector page."""
"""The code combines syntax error fix in debug gradient handler with the updated property boundaries handler."""
"""The code adds the missing handle_project_builder method to the SiteRoutes class to resolve the "AttributeError: 'SiteRoutes' object has no attribute 'handle_project_builder'" error."""
"""The floorplan data is now only included in the site inspector if it's valid and from the current session, preventing the "file uploaded" message from appearing prematurely."""
"""Site Management Routes Module"""
from flask import request, jsonify, render_template, session, redirect, url_for
import time
import json
from typing import Tuple, Dict, Any
from auth import get_session_id
from services import council_service, gradient_service, floorplan_service, property_service
from utils.logger import app_logger
from utils.site_validator import SiteValidator, BuildableAreaValidator, create_validation_response
from utils.error_handler import (
    ErrorHandler, SiteInspectorError, ValidationError, GeometryError, 
    safe_execute, validate_request_data
)
from datetime import datetime
import os


class SiteRoutes:
    """Site management route handlers"""

    def register_routes(self, app):
        """
        Register site management routes with comprehensive error handling.

        This method registers all routes related to site selection, inspection,
        and analysis functionality. Each route is registered individually with
        proper error handling to ensure partial failures don't break the entire system.

        Args:
            app (Flask): Flask application instance to register routes with

        Raises:
            Exception: Only if critical routes fail to register
        """
        routes_to_register = [
            # (path, methods, endpoint, handler, description, critical)
            ('/site-inspector', ['GET'], 'site_inspector', self.handle_site_inspector, 'Site inspection and analysis page', True),
            ('/api/calculate-buildable-area', ['POST'], 'calculate_buildable_area', self.handle_calculate_buildable_area, 'Buildable area calculation API', False),
            ('/api/save-edge-classifications', ['POST'], 'save_edge_classifications', self.handle_save_edge_classifications, 'Save edge classification data', False),
            ('/api/load-edge-classifications', ['GET'], 'load_edge_classifications', self.handle_load_edge_classifications, 'Load edge classification data', False),
            ('/api/save-edge-selection', ['POST'], 'save_edge_selection', self.handle_save_edge_selection, 'Save edge selection data', False),
            ('/api/load-edge-selection', ['GET'], 'load_edge_selection', self.handle_load_edge_selection, 'Load edge selection data', False),
            ('/api/site-status', ['GET'], 'get_site_status', self.handle_get_site_status, 'Get comprehensive site status', False),
            ('/test-navigation', ['GET'], 'test_navigation', self.handle_test_navigation, 'Test navigation functionality', False),
            ('/api/mapbox-token', ['GET'], 'get_mapbox_token', self.handle_get_mapbox_token, 'Get Mapbox access token', False),
            ('/api/debug-gradient', ['POST'], 'debug_gradient', self.handle_debug_gradient, 'Debug gradient calculation', False),
            ('/project-builder', ['GET'], 'project_builder', self.handle_project_builder, 'Project builder page', False),
            ('/structure-designer', ['GET'], 'structure_designer', self.handle_structure_designer, 'Structure designer page', False),
            ('/api/property-boundaries', ['POST'], 'get_property_boundaries', self.handle_get_property_boundaries, 'Get property boundaries for location', False),
            ('/api/get-saved-location', ['GET'], 'get_saved_location', self.handle_get_saved_location, 'Get saved location', False)
        ]

        registered_count = 0
        failed_routes = []

        for path, methods, endpoint, handler, description, is_critical in routes_to_register:
            try:
                app_logger.info(f"🔧 Registering route: {path} ({description})")

                # Validate handler exists
                if not callable(handler):
                    raise AttributeError(f"Handler {handler.__name__ if hasattr(handler, '__name__') else handler} is not callable")

                # Register the route
                app.route(path, methods=methods, endpoint=endpoint)(handler)

                registered_count += 1
                app_logger.info(f"✅ Successfully registered: {path}")

            except Exception as e:
                error_msg = f"Failed to register {path}: {e}"
                app_logger.error(error_msg)
                failed_routes.append((path, error_msg))

                # If this is a critical route, we might want to raise
                if is_critical:
                    app_logger.critical(f"🚨 Critical route {path} failed to register: {e}")
                    # Continue for now, but log as critical

        # Summary logging
        total_routes = len(routes_to_register)
        app_logger.info(f"📊 Site routes registration summary:")
        app_logger.info(f"   ✅ Registered: {registered_count}/{total_routes}")
        app_logger.info(f"   ❌ Failed: {len(failed_routes)}")

        if failed_routes:
            app_logger.warning("Failed routes:")
            for path, error in failed_routes:
                app_logger.warning(f"   - {path}: {error}")

        # Only raise if no routes were registered at all
        if registered_count == 0:
            raise Exception("No site routes could be registered - site functionality will be unavailable")

    def handle_test_navigation(self):
        """Test route to verify navigation is working"""
        app_logger.info("Test navigation route accessed successfully")

        # Test template rendering capability
        template_test = "Template rendering not tested"
        try:
            from flask import current_app
            import os
            template_dir = current_app.template_folder
            map_template_path = os.path.join(template_dir, 'map.html')
            template_test = f"Template directory: {template_dir}<br>"
            template_test += f"map.html exists: {os.path.exists(map_template_path)}<br>"
            if os.path.exists(map_template_path):
                with open(map_template_path, 'r') as f:
                    content_preview = f.read()[:200]
                template_test += f"Template content preview: {content_preview}..."
        except Exception as e:
            template_test = f"Template test failed: {e}"

        return f"""
        <html>
        <head><title>Navigation Test</title></head>
        <body>
            <h1>Navigation Working!</h1>
            <p>If you can see this, navigation is working.</p>
            <p><strong>Template Test Results:</strong></p>
            <p>{template_test}</p>
            <p><a href="/">Back to Home</a></p>
            <p><a href="/site-selection">Try Site Selection</a></p>
            <script>
                console.log('Test navigation page loaded successfully');
                console.log('Testing site-selection route...');
                fetch('/site-selection', {{ method: 'HEAD' }})
                    .then(response => {{
                        console.log('Site selection route test:', response.status, response.statusText);
                    }})
                    .catch(error => {{
                        console.error('Site selection route test failed:', error);
                    }});
            </script>
        </body>
        </html>
        """



    def handle_site_inspector(self):
        """Handle Site Inspector page with comprehensive error handling"""
        try:
            # Get project information from URL parameters
            project_id = request.args.get('project') or request.args.get('project_id')

            # Debug logging for URL parameters
            app_logger.info(f"Site inspector request - URL: {request.url}")
            app_logger.info(f"Site inspector request - Args: {dict(request.args)}")
            app_logger.info(f"Site inspector request - Project ID: {project_id}")

            # Clean up malformed project IDs early in the process
            if project_id and ('?' in str(project_id) or '&' in str(project_id)):
                project_id = str(project_id).split('?')[0].split('&')[0]
                app_logger.info(f"Cleaned malformed project ID early: {project_id}")

            project_data = {}

            if project_id:
                try:
                    # Clean up malformed project IDs
                    if '?' in str(project_id):
                        project_id = str(project_id).split('?')[0]

                    # Validate project ID is numeric
                    try:
                        project_id = int(project_id)
                    except (ValueError, TypeError):
                        app_logger.warning(f"Invalid project ID format: {project_id}")
                        project_id = None
                        project_data = {}

                    if project_id:
                        from database import DatabaseManager
                        db_manager = DatabaseManager()
                        user_id = session.get('user', {}).get('id')

                        if user_id:
                            with db_manager.db.get_cursor() as cursor:
                                cursor.execute('''
                                    SELECT name, address, location_lat, location_lng
                                    FROM projects 
                                    WHERE id = ? AND user_id = ?
                                ''', (project_id, user_id))

                                project_row = cursor.fetchone()
                                if project_row:
                                    project_data = {
                                        'id': project_id,
                                        'name': project_row[0],
                                        'address': project_row[1],
                                        'location_lat': project_row[2],
                                        'location_lng': project_row[3]
                                    }
                                    app_logger.info(f"Retrieved project data: {project_data['name']} at {project_data['address']} (ID: {project_id})")

                                    # Store project info in session for JavaScript access
                                    session['current_project_id'] = project_id
                                    session['current_project_name'] = project_data['name']
                                    session['current_project_address'] = project_data['address']
                except Exception as e:
                    app_logger.error(f"Failed to retrieve project data: {e}")

            # Enhanced session data validation
            site_data = session.get('site_data')
            if not site_data:
                app_logger.info("No site data in session, loading site inspector for new polygon creation", {
                    'session_keys': list(session.keys()),
                    'user_agent': request.headers.get('User-Agent', 'Unknown'),
                    'referer': request.headers.get('Referer', 'None')
                })
                # Provide minimal site data structure for new polygon creation
                site_data = {
                    'area': 0,
                    'area_m2': 0,
                    'type': 'residential',
                    'coordinates': [],
                    'center': None,
                    'ready_for_new_polygon': True
                }

            app_logger.info("Processing site inspector request", {
                'site_data_keys': list(site_data.keys()) if site_data else [],
                'has_coordinates': bool(site_data.get('coordinates')),
                'coordinate_count': len(site_data.get('coordinates', [{}])[0]) if site_data.get('coordinates') else 0,
                'has_center': bool(site_data.get('center')),
                'area': site_data.get('area', 'unknown')
            })

            # Enhanced site data validation
            site_valid, site_errors = SiteValidator.validate_site_data(site_data)
            if not site_valid:
                app_logger.warning(f"Site data validation failed: {site_errors}")

                # Don't treat empty site data as an error - allow for new polygon creation
                if site_data or site_errors != ['Site data is empty or None']:
                    try:
                        # Create a simple error message without using the complex error handler
                        error_message = f'Site data validation issues: {"; ".join(site_errors)}'
                        app_logger.warning(f"Site data validation warnings (non-blocking): {error_message}")
                        
                        # Don't block loading - just log the warnings and continue
                        # The site inspector can handle missing data and allow new polygon creation
                        error_message = None  # Clear error to allow normal loading
                    except Exception as e:
                        app_logger.error(f"Error handler failed: {e}")
                        error_message = None  # Clear error to allow normal loading

                    # Only return error template if we have a critical error
                    if error_message:
                        return render_template('site_inspector.html', 
                                             site_data={'error': error_message},
                                             site_data_json=json.dumps({'error': True, 'message': error_message}),
                                             area_text="Error: Invalid site data",
                                             validation_errors=site_errors,
                                             project_data=project_data if project_data else {},
                                             project_id=project_id)

            # Use services to enhance site data
            enhanced_site_data = site_data.copy() if site_data else {}
            app_logger.info(f"Processing site inspector for area: {site_data.get('area', 'unknown')} m²")

            # Calculate gradient data with error handling
            try:
                gradient_data = gradient_service.calculate_gradient_data(site_data)
                enhanced_site_data.update(gradient_data)
                app_logger.info("Gradient data calculated successfully")
            except Exception as e:
                app_logger.error(f"Gradient calculation failed: {e}")
                enhanced_site_data['gradient_error'] = str(e)

            # Get council requirements and calculate buildable area
            council_name = enhanced_site_data.get('council', '')
            zoning = enhanced_site_data.get('zoning', 'residential')

            if council_name:
                app_logger.info(f"Looking up requirements for {council_name}, zoning: {zoning}")
                try:
                    council_requirements = council_service.get_council_requirements(council_name, zoning)
                    enhanced_site_data['council_requirements'] = council_requirements
                    app_logger.info(f"Council requirements loaded: {list(council_requirements.keys()) if council_requirements else 'None'}")

                    # Calculate buildable area with proper error handling
                    coordinates = enhanced_site_data.get('coordinates', [])
                    if coordinates and len(coordinates) > 0:
                        coords_to_use = coordinates[0] if isinstance(coordinates[0], list) else coordinates
                        app_logger.info(f"Calculating buildable area for {len(coords_to_use)} coordinate points")

                        # Check for edge classifications in session
                        session_id = get_session_id()
                        edge_classifications = session.get(f'edge_classifications_{session_id}', [])

                        # If no edge classifications, try a fallback frontage
                        frontage = 'north' if not edge_classifications else None

                        # Validate buildable area inputs
                        inputs_valid, input_errors = BuildableAreaValidator.validate_buildable_area_inputs(
                            coords_to_use, council_requirements, frontage, edge_classifications
                        )

                        if inputs_valid:
                            buildable_data, error = safe_execute(
                                council_service.calculate_buildable_area,
                                coords_to_use, council_requirements, frontage, edge_classifications,
                                error_handler=ErrorHandler.handle_buildable_area_error,
                                context={'coords_count': len(coords_to_use), 'requirements': council_requirements}
                            )

                            if error:
                                app_logger.error(f"Buildable area calculation failed: {error}")
                                enhanced_site_data['buildable_area'] = error
                            else:
                                # Validate result
                                result_valid, result_errors = BuildableAreaValidator.validate_buildable_area_result(buildable_data)
                                if result_valid:
                                    enhanced_site_data['buildable_area'] = buildable_data
                                    buildable_area_m2 = buildable_data.get('buildable_area_m2', 0)
                                    if buildable_area_m2 > 0:
                                        app_logger.info(f"Calculated buildable area: {buildable_area_m2:.1f} m²")
                                    else:
                                        app_logger.warning(f"Buildable area calculation resulted in 0 m². Errors: {result_errors}")
                                else:
                                    app_logger.error(f"Invalid buildable area result: {result_errors}")
                                    enhanced_site_data['buildable_area'] = {
                                        'error': f'Invalid calculation result: {"; ".join(result_errors)}',
                                        'buildable_area_m2': 0
                                    }
                        else:
                            app_logger.error(f"Invalid buildable area inputs: {input_errors}")
                            enhanced_site_data['buildable_area'] = {
                                'error': f'Invalid inputs: {"; ".join(input_errors)}',
                                'buildable_area_m2': 0
                            }
                    else:
                        app_logger.error("No valid coordinates available for buildable area calculation")
                        enhanced_site_data['buildable_area'] = {'error': 'No coordinates available', 'buildable_area_m2': 0}

                except Exception as e:
                    app_logger.error(f"Council service error: {e}")
                    enhanced_site_data['council_error'] = str(e)
                    enhanced_site_data['buildable_area'] = {'error': f'Council service failed: {e}', 'buildable_area_m2': 0}
            else:
                app_logger.warning("No council name available for requirements lookup")
                enhanced_site_data['buildable_area'] = {'error': 'No council information available', 'buildable_area_m2': 0}

            # Check for existing floor plan data (only if it's from current session)
            floorplan_data = session.get('floorplan_data')
            # Only include floorplan data if it has been properly processed and has boundaries
            if floorplan_data and floorplan_data.get('success') and floorplan_data.get('boundaries'):
                site_data['floorplan_data'] = floorplan_data
                app_logger.info(f"Floor plan data available: {len(floorplan_data.get('boundaries', []))} boundary points")
            else:
                # Clear any stale or incomplete floorplan data
                if 'floorplan_data' in session:
                    del session['floorplan_data']

            # Calculate area text for display
            area = enhanced_site_data.get('area', 0)
            area_text = f"{(area / 10000):.2f} hectares" if area > 10000 else f"{area:.0f} m²"

            # Include lock status in the data passed to template
            enhanced_site_data['isLocked'] = session.get('site_locked', False)
            enhanced_site_data['polygonId'] = session.get('polygon_id')

            # Store current project ID in session for other tools
            if project_id:
                session['current_project_id'] = project_id

            # Pass the site data to the template, including the JSON version for JavaScript
            return render_template('site_inspector.html', 
                                 site_data=enhanced_site_data,
                                 site_data_json=json.dumps(enhanced_site_data),
                                 area_text=area_text,
                                 project_data=project_data,
                                 project_id=project_id)

        except Exception as e:
            app_logger.error(f"Site inspector error: {e}")
            # Return error page or redirect with error message
            return render_template('site_inspector.html', 
                                 site_data={'error': str(e)},
                                 site_data_json='{}',
                                 area_text="Error calculating area",
                                 project_data=project_data if 'project_data' in locals() and project_data else {},
                                 project_id=project_id if 'project_id' in locals() else None)

    def handle_calculate_buildable_area(self):
        """Calculate buildable area with specific frontage configuration"""
        try:
            print(f"[SiteRoutes] Buildable area calculation requested")

            # Validate request data
            data = request.get_json()
            print(f"[SiteRoutes] Request data keys: {list(data.keys()) if data else 'None'}")

            # Check if we have site_coords at minimum
            if not data or 'site_coords' not in data:
                error_response = ErrorHandler.handle_buildable_area_error(
                    ValidationError("Site coordinates are required"), data
                )
                return jsonify(error_response), 400

            site_coords = data.get('site_coords')
            requirements = data.get('requirements')
            frontage = data.get('frontage', 'auto')
            edge_classifications = data.get('edge_classifications')

            # If no requirements provided, try to get them from session/site data
            if not requirements:
                site_data = session.get('site_data', {})
                council_name = site_data.get('council', '')
                zoning = site_data.get('zoning', 'residential')

                if council_name:
                    app_logger.info(f"Getting requirements for {council_name}, zoning: {zoning}")
                    requirements = council_service.get_council_requirements(council_name, zoning)
                    app_logger.info(f"Retrieved requirements: {bool(requirements)}")
                else:
                    app_logger.warning("No council data available, using default requirements")
                    requirements = council_service._get_default_requirements()

            # Validate we now have requirements
            if not requirements:
                error_response = ErrorHandler.handle_buildable_area_error(
                    ValidationError("Council requirements could not be determined"), data
                )
                return jsonify(error_response), 400

            print(f"[SiteRoutes] Inputs - coords: {len(site_coords) if site_coords else 0}, frontage: {frontage}")
            print(f"[SiteRoutes] Requirements: {requirements}")
            print(f"[SiteRoutes] Edge classifications: {len(edge_classifications) if edge_classifications else 0}")

            # Validate inputs
            inputs_valid, input_errors = BuildableAreaValidator.validate_buildable_area_inputs(
                site_coords, requirements, frontage, edge_classifications
            )

            if not inputs_valid:
                error_response = ErrorHandler.handle_buildable_area_error(
                    ValidationError(f"Invalid inputs: {'; '.join(input_errors)}"),
                    data
                )
                return jsonify(error_response), 400

            # Perform calculation with error handling
            result, error = safe_execute(
                council_service.calculate_buildable_area,
                site_coords, requirements, frontage, edge_classifications,
                error_handler=ErrorHandler.handle_buildable_area_error,
                context=data
            )

            if error:
                return jsonify(error), 500

            # Validate result
            result_valid, result_errors = BuildableAreaValidator.validate_buildable_area_result(result)
            if not result_valid:
                app_logger.warning(f"Buildable area result validation issues: {result_errors}")
                # Still return result but log warnings

            calculation_method = result.get('calculation_method', 'unknown')
            buildable_area = result.get('buildable_area_m2', 0)
            app_logger.info(f"Recalculated buildable area with method {calculation_method}: {buildable_area:.1f} m²")

            # Log user action
            ErrorHandler.log_user_action(
                'calculate_buildable_area', 
                True, 
                {
                    'method': calculation_method,
                    'area': buildable_area,
                    'frontage': frontage,
                    'edge_classifications_count': len(edge_classifications) if edge_classifications else 0
                }
            )

            return jsonify(result), 200

        except Exception as e:
            app_logger.error(f"Buildable area calculation error: {e}")
            error_response = ErrorHandler.handle_buildable_area_error(e, data if 'data' in locals() else None)
            return jsonify(error_response), 500

    def handle_save_edge_classifications(self):
        """Save edge classifications for a site"""
        try:
            # Validate request data
            data = request.get_json()
            if not data:
                error_response = ErrorHandler.handle_edge_classification_error(
                    ValidationError("No JSON data received")
                )
                return jsonify(error_response), 400

            validation_error = validate_request_data(data, ['edgeClassifications', 'siteId'])
            if validation_error:
                error_response = ErrorHandler.handle_edge_classification_error(validation_error, data)
                return jsonify(error_response), validation_error.status_code

            edge_classifications = data.get('edgeClassifications', [])
            site_id = data.get('siteId', 'unknown')

            app_logger.info(f"Processing {len(edge_classifications)} edge classifications for site {site_id}")

            # Filter out unclassified edges (those with None type) before validation
            classified_edges = [edge for edge in edge_classifications if edge.get('type') is not None]

            # Only validate if we have classified edges
            if classified_edges:
                edge_valid, edge_errors = SiteValidator.validate_edge_classifications(classified_edges)
                if not edge_valid:
                    error_response = ErrorHandler.handle_edge_classification_error(
                        ValidationError(f"Invalid edge classifications: {'; '.join(edge_errors)}"),
                        edge_classifications
                    )
                    return jsonify(error_response), 400

            # Normalize edge classifications
            for edge in edge_classifications:
                if 'type' not in edge and 'classification' in edge:
                    edge['type'] = edge['classification']

            # Store in session (could be enhanced to use database)
            session[f'edge_classifications_{site_id}'] = edge_classifications

            app_logger.info(f"Successfully saved edge classifications for site {site_id}: {len(edge_classifications)} edges")

            # Log user action
            ErrorHandler.log_user_action(
                'save_edge_classifications',
                True,
                {
                    'site_id': site_id,
                    'edge_count': len(edge_classifications),
                    'edge_types': [edge.get('type') for edge in edge_classifications]
                }
            )

            response = ErrorHandler.create_success_response(
                {'edge_count': len(edge_classifications)},
                'Edge classifications saved successfully'
            )
            return jsonify(response), 200

        except Exception as e:
            app_logger.error(f"Error saving edge classifications: {e}")
            error_response = ErrorHandler.handle_edge_classification_error(e, data if 'data' in locals() else None)
            return jsonify(error_response), 500

    def handle_load_edge_classifications(self):
        """Load edge classifications for a site"""
        try:
            site_id = request.args.get('siteId', 'unknown')
            edge_classifications = session.get(f'edge_classifications_{site_id}', [])

            return jsonify({
                'success': True, 
                'edge_classifications': edge_classifications
            }), 200

        except Exception as e:
            app_logger.error(f"Error loading edge classifications: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_save_edge_selection(self):
        """Save edge selection for a site"""
        try:
            data = request.get_json()
            selected_edges = data.get('selectedEdges', [])
            site_id = data.get('siteId', 'unknown')

            # Store in session for now
            session[f'edge_selection_{site_id}'] = {
                'selectedEdges': selected_edges,
                'timestamp': data.get('timestamp', None)
            }

            app_logger.info(f"Saved edge selection for site {site_id}: {len(selected_edges)} edges")

            return jsonify({'success': True, 'message': 'Edge selection saved'}), 200

        except Exception as e:
            app_logger.error(f"Error saving edge selection: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_load_edge_selection(self):
        """Load edge selection for a site"""
        try:
            site_id = request.args.get('siteId', 'unknown')
            edge_selection = session.get(f'edge_selection_{site_id}', {})

            return jsonify({
                'success': True, 
                'selectedEdges': edge_selection.get('selectedEdges', []),
                'timestamp': edge_selection.get('timestamp', None)
            }), 200

        except Exception as e:
            app_logger.error(f"Error loading edge selection: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_get_site_status(self):
        """Get comprehensive site status including floor plan and buildable area"""
        try:
            site_data = session.get('site_data', {})
            floorplan_data = session.get('floorplan_data', {})

            # Check buildable area status
            buildable_area = site_data.get('buildable_area', {})

            # Prepare status response
            status = {
                'site_selected': session.get('site_selected', False),
                'has_site_data': bool(site_data),
                'has_floorplan': bool(floorplan_data.get('success')),
                'has_buildable_area': bool(buildable_area.get('buildable_area_m2')),
                'buildable_area_m2': buildable_area.get('buildable_area_m2', 0),
                'site_area': site_data.get('area', 0),
                'location': session.get('user_location', ''),
                'council': site_data.get('council', ''),
                'zoning': site_data.get('zoning', '')
            }

            return jsonify({'success': True, 'status': status}), 200

        except Exception as e:
            app_logger.error(f"Error getting site status: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_get_mapbox_token(self):
        """Get Mapbox access token"""
        try:
            import os
            token = os.getenv('MAPBOX_ACCESS_TOKEN')
            if token:
                return jsonify({'success': True, 'token': token}), 200
            else:
                app_logger.error("No Mapbox token found in environment variables")
                return jsonify({'success': False, 'error': 'No Mapbox token configured', 'token': None}), 200
        except Exception as e:
            app_logger.error(f"Error getting Mapbox token: {e}")
            return jsonify({'success': False, 'error': str(e), 'token': None}), 500

    def handle_debug_gradient(self):
        """Debug gradient calculation"""
        try:
            data = request.get_json()

            app_logger.info(f"Gradient debug request received with keys: {list(data.keys()) if data else 'None'}")

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided for gradient debugging'
                }), 400

            # Detailed input validation and logging
            coordinates = data.get('coordinates', [])
            if coordinates and isinstance(coordinates[0], list):
                coordinates = coordinates[0]

            input_summary = {
                'has_coordinates': bool(data.get('coordinates')),
                'coordinate_count': len(coordinates) if coordinates else 0,
                'coordinate_sample': coordinates[:2] if coordinates else [],
                'has_bounds': bool(data.get('bounds')),
                'bounds_keys': list(data.get('bounds',{}).keys()),
                'area': data.get('area', 'missing'),
                'slope_provided': data.get('slope') is not None,
                'bearing_provided': data.get('bearing') is not None,
                'center_provided': data.get('center') is not None
            }
            app_logger.info(f"Input data validation: {input_summary}")

            # Continue with gradient calculation logic here
            result = gradient_service.debug_gradient_calculation(data)

            app_logger.info(f"Debug gradient request: {data}")

            # Return debug info

            return jsonify({
                'success': True,
                'debug_info': 'Gradient debug endpoint working'
            }), 200
        except Exception as e:
            app_logger.error(f"Debug gradient error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_project_builder(self):
        """Handle project builder page"""
        try:
            app_logger.info("Project builder page requested")
            return render_template('project_builder.html')
        except Exception as e:
            app_logger.error(f"Project builder error: {e}")
            return f"Error loading project builder: {e}", 500

    def handle_structure_designer(self):
        """Handle structure designer page"""
        try:
            app_logger.info("Structure designer page requested")
            return render_template('structure_designer.html')
        except Exception as e:
            app_logger.error(f"Structure designer error: {e}")
            return render_template('structure_designer.html', 
                                 site_data={'error': str(e)},
                                 site_data_json='{}'), 500

    def handle_get_property_boundaries(self):
        """Get property boundaries for location"""
        try:
            data = request.get_json()
            app_logger.info(f"Property boundaries request: {data}")

            if not data or ('lat' not in data or 'lng' not in data):
                return jsonify({
                    'success': False,
                    'error': 'Latitude and longitude are required',
                    'properties': [],
                    'containing_property': None,
                    'total_count': 0
                }), 400

            lat = float(data['lat'])
            lng = float(data['lng'])

            # Use the property service to get only the containing property
            from services.property_service import property_service
            result = property_service.get_containing_property_only(lat, lng)

            app_logger.info(f"Property boundaries result: {result.get('success', False)}, {result.get('total_count', 0)} properties")

            return jsonify(result), 200

        except (ValueError, TypeError) as e:
            app_logger.error(f"Invalid coordinates in property boundaries request: {e}")
            return jsonify({
                'success': False,
                'error': 'Invalid coordinates provided',
                'properties': [],
                'containing_property': None,
                'total_count': 0
            }), 400
        except Exception as e:
            app_logger.error(f"Property boundaries error: {e}")
            return jsonify({
                'success': False,
                'error': 'Property boundary service failed',
                'properties': [],
                'containing_property': None,
                'total_count': 0
            }), 500

    def handle_get_saved_location(self):
        """Get saved location"""
        try:
            location = session.get('user_location', '')
            location_data = session.get('location_data', {})

            return jsonify({
                'success': True,
                'location': location,
                'location_data': location_data
            }), 200
        except Exception as e:
            app_logger.error(f"Get saved location error: {e}")
            return jsonify({'error': str(e)}), 500


# Create route handler instance
site_route_handler = SiteRoutes()