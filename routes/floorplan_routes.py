"""
Floor Plan Routes Module
"""
from flask import request, jsonify, session
from typing import Tuple, Dict, Any
from auth import get_session_id
from services import floorplan_service
from utils.logger import app_logger


class FloorplanRoutes:
    """Floor plan processing route handlers"""

    def register_routes(self, app):
        """Register floor plan routes with Flask app"""
        app.route('/api/upload-floorplan', methods=['POST'], endpoint='upload_floorplan')(self.handle_upload_floorplan)
        app.route('/api/scale-floorplan', methods=['POST'], endpoint='scale_floorplan')(self.handle_scale_floorplan)
        app.route('/api/get-floorplan-data', methods=['GET'], endpoint='get_floorplan_data')(self.handle_get_floorplan_data)
        app.route('/api/save-transformed-floorplan', methods=['POST'], endpoint='save_transformed_floorplan')(self.handle_save_transformed_floorplan)
        app.route('/api/clear-floorplan', methods=['POST'], endpoint='clear_floorplan')(self.handle_clear_floorplan)
        app.route('/api/convert-floorplan-to-geojson', methods=['POST'], endpoint='convert_to_geojson')(self.handle_convert_to_geojson)
        app.route('/api/update-floorplan-transform', methods=['POST'], endpoint='update_transform')(self.handle_update_transform)

    def handle_upload_floorplan(self):
        """Handle floor plan image upload and processing"""
        try:
            data = request.get_json()
            app_logger.info(f"[FloorPlan] Upload request received: {bool(data)}")

            if not data or 'image' not in data:
                app_logger.error("[FloorPlan] No image data provided in request")
                return jsonify({'error': 'Image data is required'}), 400

            image_data = data.get('image')
            scale_reference = data.get('scale_reference')

            app_logger.info(f"[FloorPlan] Processing image: data_length={len(image_data) if image_data else 0}, scale_ref={scale_reference}")

            # Process the floor plan image
            result = floorplan_service.process_floorplan_image(image_data, scale_reference)

            if result.get('success'):
                # Store in session for later use
                session['floorplan_data'] = {
                    'boundaries': result['boundaries'],
                    'coordinates': result['coordinates'],
                    'metrics': result['metrics']
                }

                app_logger.info(f"[FloorPlan] Processing successful: {len(result['boundaries'])} boundary points, {len(result['coordinates'])} coordinates")
                app_logger.info(f"[FloorPlan] Metrics: {result.get('metrics', {})}")
                return jsonify(result), 200
            else:
                app_logger.error(f"[FloorPlan] Processing failed: {result.get('error')}")
                return jsonify(result), 400

        except Exception as e:
            app_logger.error(f"[FloorPlan] Upload error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_scale_floorplan(self):
        """Scale floor plan to fit within buildable area"""
        try:
            data = request.get_json()
            app_logger.info(f"[FloorPlan] Scale request received: {bool(data)}")

            buildable_coords = data.get('buildable_coords')
            scale_factor = data.get('scale_factor', 0.8)

            app_logger.info(f"[FloorPlan] Scale parameters: buildable_coords={len(buildable_coords) if buildable_coords else 0}, scale_factor={scale_factor}")
            app_logger.info(f"[FloorPlan] Buildable coords format: {type(buildable_coords[0]) if buildable_coords else 'None'}")
            if buildable_coords:
                app_logger.info(f"[FloorPlan] Buildable coords sample: {buildable_coords[0]}")

            if not buildable_coords:
                app_logger.error("[FloorPlan] No buildable area coordinates provided")
                return jsonify({'error': 'Buildable area coordinates are required'}), 400

            # Get floor plan data from session
            floorplan_data = session.get('floorplan_data')
            if not floorplan_data:
                app_logger.error("[FloorPlan] No floor plan data in session")
                return jsonify({'error': 'No floor plan data found. Please upload a floor plan first.'}), 400

            floorplan_coords = floorplan_data['coordinates']
            app_logger.info(f"[FloorPlan] Using floor plan coordinates: {len(floorplan_coords)} points")

            # Scale floor plan to buildable area
            scaled_coords = floorplan_service.scale_floorplan_to_buildable_area(
                floorplan_coords, buildable_coords, scale_factor
            )

            if scaled_coords:
                # Update session with scaled coordinates
                session['floorplan_data']['scaled_coordinates'] = scaled_coords

                result = {
                    'success': True,
                    'scaled_coordinates': scaled_coords,
                    'metrics': floorplan_data['metrics']
                }

                app_logger.info(f"[FloorPlan] Scaling successful: {len(scaled_coords)} scaled points generated")
                return jsonify(result), 200
            else:
                app_logger.error("[FloorPlan] Scaling failed - no coordinates returned")
                return jsonify({'error': 'Failed to scale floor plan'}), 400

        except Exception as e:
            app_logger.error(f"[FloorPlan] Scaling error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_get_floorplan_data(self):
        """Get current floor plan data from session"""
        try:
            floorplan_data = session.get('floorplan_data', {})
            app_logger.info(f"[FloorPlan] Data retrieved: {bool(floorplan_data)}")

            return jsonify({
                'success': True,
                'data': floorplan_data
            }), 200

        except Exception as e:
            app_logger.error(f"[FloorPlan] Error retrieving data: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_save_transformed_floorplan(self):
        """Save transformed (rotated/moved) floor plan coordinates"""
        try:
            data = request.get_json()
            app_logger.info(f"[FloorPlan] Save transformed request received: {bool(data)}")

            transformed_coords = data.get('transformed_coordinates')
            rotation = data.get('rotation', 0)
            center = data.get('center')

            if not transformed_coords:
                app_logger.error("[FloorPlan] No transformed coordinates provided")
                return jsonify({'error': 'Transformed coordinates are required'}), 400

            # Get existing floor plan data from session
            floorplan_data = session.get('floorplan_data', {})

            # Update with transformed coordinates
            floorplan_data.update({
                'transformed_coordinates': transformed_coords,
                'rotation': rotation,
                'center': center,
                'last_modified': 'transformed'
            })

            session['floorplan_data'] = floorplan_data

            app_logger.info(f"[FloorPlan] Transformed coordinates saved: {len(transformed_coords)} points, rotation: {rotation}°")

            return jsonify({
                'success': True,
                'message': 'Transformed floor plan saved',
                'coordinates_count': len(transformed_coords),
                'rotation': rotation
            }), 200

        except Exception as e:
            app_logger.error(f"[FloorPlan] Error saving transformed data: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_clear_floorplan(self):
        """Clear floor plan data from session"""
        try:
            had_data = 'floorplan_data' in session
            if had_data:
                del session['floorplan_data']

            app_logger.info(f"[FloorPlan] Data cleared from session (had_data={had_data})")
            return jsonify({'success': True, 'message': 'Floor plan data cleared'}), 200

        except Exception as e:
            app_logger.error(f"[FloorPlan] Error clearing data: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_convert_to_geojson(self):
        """Convert stored floor plan data to GeoJSON polygon"""
        try:
            data = request.get_json()
            app_logger.info(f"[FloorPlan] GeoJSON conversion request received: {bool(data)}")

            center_lat = data.get('center_lat')
            center_lng = data.get('center_lng')
            scale_meters = data.get('scale_meters')  # Let service auto-calculate if not provided

            if not center_lat or not center_lng:
                app_logger.error("[FloorPlan] Missing center coordinates for GeoJSON conversion")
                return jsonify({'error': 'Center coordinates are required'}), 400

            # Get floor plan data from session
            floorplan_data = session.get('floorplan_data')
            if not floorplan_data or 'coordinates' not in floorplan_data:
                app_logger.error("[FloorPlan] No floor plan coordinates found in session")
                return jsonify({'error': 'No floor plan data found. Please upload a floor plan first.'}), 400

            coordinates = floorplan_data['coordinates']
            boundaries = floorplan_data.get('boundaries', [])
            app_logger.info(f"[FloorPlan] Converting {len(coordinates)} coordinates to GeoJSON (boundaries: {len(boundaries)})")

            # Convert to GeoJSON
            geojson_polygon = floorplan_service.convert_to_geojson_polygon(
                coordinates, center_lat, center_lng, scale_meters
            )

            if geojson_polygon:
                # Store GeoJSON in session
                session['floorplan_data']['geojson_polygon'] = geojson_polygon

                result = {
                    'success': True,
                    'geojson_polygon': geojson_polygon,
                    'coordinates_count': len(coordinates)
                }

                app_logger.info(f"[FloorPlan] GeoJSON conversion successful")
                return jsonify(result), 200
            else:
                app_logger.error("[FloorPlan] GeoJSON conversion failed")
                return jsonify({'error': 'Failed to convert to GeoJSON'}), 400

        except Exception as e:
            app_logger.error(f"[FloorPlan] GeoJSON conversion error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_update_transform(self):
        """Update floor plan transform (position, rotation, scale)"""
        try:
            data = request.get_json()
            app_logger.info(f"[FloorPlan] Transform update request received: {bool(data)}")

            transform = data.get('transform', {})
            geojson_polygon = data.get('geojson_polygon')

            if not transform and not geojson_polygon:
                app_logger.error("[FloorPlan] No transform data or GeoJSON provided")
                return jsonify({'error': 'Transform data or GeoJSON polygon is required'}), 400

            # Get existing floor plan data from session
            floorplan_data = session.get('floorplan_data', {})

            # Update transform data
            if transform:
                floorplan_data['transform'] = {
                    'position': transform.get('position', {'lat': 0, 'lng': 0}),
                    'rotation': transform.get('rotation', 0),
                    'scale': transform.get('scale', 1.0),
                    'locked': transform.get('locked', False)
                }

            # Update GeoJSON polygon
            if geojson_polygon:
                floorplan_data['geojson_polygon'] = geojson_polygon

            floorplan_data['last_modified'] = 'transform_updated'
            session['floorplan_data'] = floorplan_data

            app_logger.info(f"[FloorPlan] Transform updated: {transform}")

            return jsonify({
                'success': True,
                'message': 'Floor plan transform updated',
                'transform': floorplan_data.get('transform', {}),
                'has_geojson': 'geojson_polygon' in floorplan_data
            }), 200

        except Exception as e:
            app_logger.error(f"[FloorPlan] Transform update error: {e}")
            return jsonify({'error': str(e)}), 500

    def _save_structure_placement_snapshot(self, project_id: str, floorplan_data: Dict[str, Any]):
        """Save structure placement data as a project snapshot."""
        from services import project_service  # Import here to avoid circular dependency

        structure_placement_data = {
            'boundaries': floorplan_data.get('boundaries'),
            'dimensions': floorplan_data.get('dimensions'),
            'area_m2': floorplan_data.get('area_m2'),
            'placement': floorplan_data.get('placement'),
            'structure_type': floorplan_data.get('structure_type'),
            'rooms': floorplan_data.get('rooms'),
            'walls': floorplan_data.get('walls')
        }

        project_service.save_project_snapshot(
            project_id=project_id,
            snapshot_type='structure_placement',
            snapshot_data=structure_placement_data
        )

# Create route handler instance
floorplan_route_handler = FloorplanRoutes()