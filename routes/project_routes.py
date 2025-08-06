"""
Project Management Routes Module
"""
from flask import request, jsonify, render_template, session
from typing import Tuple, Dict, Any
from datetime import datetime
from database import DatabaseManager
from utils.logger import app_logger
from services import response_service
from utils.error_handler import ErrorHandler, ErrorCategories


class ProjectRoutes:
    """Project management route handlers"""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def register_routes(self, app):
        """Register project management routes"""
        app.route('/api/create-project', methods=['POST'])(self.handle_create_project)
        app.route('/api/get-user-projects', methods=['GET'])(self.handle_get_user_projects)
        app.route('/project/', methods=['GET'])(self.handle_project_redirect)
        app.route('/project/<int:project_id>', methods=['GET'])(self.handle_project_overview)
        app.route('/api/project/<int:project_id>', methods=['GET'])(self.handle_get_project_data)
        app.route('/api/project/<int:project_id>/snapshot', methods=['GET'])(self.handle_project_snapshot)
        app.route('/api/project/<int:project_id>/snapshot', methods=['POST'])(self.handle_project_snapshot)
        app.route('/api/project/<int:project_id>', methods=['DELETE'])(self.handle_delete_project)
        app.route('/api/project-address', methods=['GET'])(self.handle_get_project_address)
        

    def handle_project_redirect(self):
        """Handle base project route - redirect to dashboard"""
        try:
            from flask import redirect, url_for
            app_logger.info("Base project route accessed, redirecting to dashboard")
            return redirect(url_for('dashboard'))
        except Exception as e:
            app_logger.error(f"Project redirect error: {e}")
            return "Project not found", 404

    def handle_project_overview(self, project_id: int):
        """Handle project overview page"""
        try:
            user_info = session.get('user')
            if not user_info:
                from flask import redirect, url_for
                return redirect(url_for('login'))

            # Get project details from database
            project = self.db_manager.get_project_by_id(project_id, user_info['id'])
            if not project:
                return "Project not found", 404

            # Get team members for the project
            team_members = self.db_manager.get_project_team_members(project_id)

            # Get project notes
            notes = self.db_manager.get_project_notes(project_id)

            # Get project history
            project_history = self.db_manager.get_project_history(project_id)

            # Get project snapshot (get the latest one)
            project_snapshot = self.db_manager.get_project_snapshot(project_id)
            
            # Debug: Log what snapshot we found
            if project_snapshot:
                app_logger.info(f"Project {project_id} snapshot found: type={project_snapshot.get('snapshot_type')}, data_length={len(str(project_snapshot.get('snapshot_data', '')))}")
            else:
                app_logger.info(f"No snapshot found for project {project_id}")

            # Determine current engineering flow step
            flow_step = self._determine_flow_step(project_id)

            app_logger.info(f"Project overview page requested for project ID: {project_id}")
            return render_template('project_overview.html', user=user_info, project=project, team_members=team_members, notes=notes, project_history=project_history, project_snapshot=project_snapshot, flow_step=flow_step)
        except Exception as e:
            app_logger.error(f"Failed to render project overview page: {e}")
            return "Project overview error", 500

    def _determine_flow_step(self, project_id: int):
        """Determine the current engineering flow step based on project progress"""
        try:
            with self.db_manager.db.get_cursor() as cursor:
                # Check for different types of snapshots to determine progress
                cursor.execute('''
                    SELECT snapshot_type, created_at 
                    FROM project_snapshots 
                    WHERE project_id = ? 
                    ORDER BY created_at DESC
                ''', (project_id,))
                
                snapshots = cursor.fetchall()
                
                # Default to step 1 if no progress
                if not snapshots:
                    return {
                        'current_step': 1,
                        'step_name': 'Site Inspector',
                        'next_step': 1,
                        'next_step_name': 'Site Inspector',
                        'button_text': 'Start Site Inspector',
                        'route_url': f'/site-inspector?project_id={project_id}'
                    }
                
                # Analyze snapshots to determine progress
                snapshot_types = [snap[0] for snap in snapshots]
                
                # Step 4: Structure Analyser (final step)
                if 'structural_analysis' in snapshot_types:
                    return {
                        'current_step': 4,
                        'step_name': 'Structure Analyser',
                        'next_step': 4,
                        'next_step_name': 'Structure Analyser',
                        'button_text': 'Open Structure Analyser',
                        'route_url': f'/structural-analyser?project_id={project_id}'
                    }
                
                # Step 3: Structural Designer
                elif 'structure_design' in snapshot_types:
                    return {
                        'current_step': 3,
                        'step_name': 'Structural Designer',
                        'next_step': 4,
                        'next_step_name': 'Structure Analyser',
                        'button_text': 'Continue to Structure Analyser',
                        'route_url': f'/structural-analyser?project_id={project_id}'
                    }
                
                # Step 2: Terrain Analysis
                elif 'terrain_analysis' in snapshot_types or 'buildable_area' in snapshot_types:
                    return {
                        'current_step': 2,
                        'step_name': 'Terrain Analysis',
                        'next_step': 3,
                        'next_step_name': 'Structural Designer',
                        'button_text': 'Continue to Structural Designer',
                        'route_url': f'/structure-designer?project_id={project_id}'
                    }
                
                # Step 1: Site Inspector (completed)
                elif 'site_boundary' in snapshot_types:
                    return {
                        'current_step': 1,
                        'step_name': 'Site Inspector',
                        'next_step': 2,
                        'next_step_name': 'Terrain Analysis',
                        'button_text': 'Continue to Terrain Analysis',
                        'route_url': f'/terrain-viewer?project_id={project_id}'
                    }
                
                # Default case
                else:
                    return {
                        'current_step': 1,
                        'step_name': 'Site Inspector',
                        'next_step': 1,
                        'next_step_name': 'Site Inspector',
                        'button_text': 'Continue Site Inspector',
                        'route_url': f'/site-inspector?project_id={project_id}'
                    }
                    
        except Exception as e:
            app_logger.error(f"Error determining flow step: {e}")
            # Return default step on error
            return {
                'current_step': 1,
                'step_name': 'Site Inspector',
                'next_step': 1,
                'next_step_name': 'Site Inspector',
                'button_text': 'Open Site Inspector',
                'route_url': f'/site-inspector?project_id={project_id}'
            }

    def handle_create_project(self) -> Tuple[Dict[str, Any], int]:
        """Create a new project"""
        try:
            if 'user' not in session:
                return response_service.validation_error('Not logged in'), 401

            data = request.get_json()
            if not data:
                return response_service.validation_error('Request body must be JSON'), 400

            user_id = session['user']['id']

            project_name = data['name'].strip()
            site_address = data['address'].strip()

            if not project_name or not site_address:
                return response_service.validation_error('Project name and site address cannot be empty'), 400

            # Create project data object with all fields
            project_data = {
                'name': project_name,
                'project_number': data.get('projectNumber', '').strip(),
                'client_name': data.get('clientName', '').strip(),
                'address': site_address,
                'site_information': data.get('siteInformation', '').strip(),
                'project_type': data.get('projectType'),
                'project_units': data.get('projectUnits', 'metric'),
                'project_visibility': data.get('projectVisibility', 'private'),
                'team_members': data.get('teamMembers', '').strip(),
                'status': 'active',
                'user_id': user_id
            }

            # Save project to database
            project_id = self.db_manager.save_project(project_data)

            if project_id:
                # Add project creation event to history
                self.db_manager.add_project_history_event(
                    project_id, 
                    user_id, 
                    'created', 
                    f"Project '{project_name}' was created"
                )

                project_data['id'] = project_id
                app_logger.info(f"Project created: {project_name} at {site_address} for user {user_id} with ID {project_id}")

                return jsonify({
                    'success': True, 
                    'project': project_data,
                    'redirect_url': f'/project/{project_id}',
                    'message': 'Project created successfully'
                })
            else:
                return jsonify({'error': 'Failed to save project to database'}), 500

        except Exception as e:
            app_logger.error(f"Project creation error: {e}")
            return jsonify({'error': 'Project creation failed'}), 500

    def handle_get_user_projects(self):
        """Get user projects"""
        try:
            if 'user' not in session:
                return response_service.validation_error('Not logged in'), 401

            user_id = session.get('user', {}).get('id')

            # Get projects from database
            projects = self.db_manager.get_user_projects(user_id)

            return jsonify({
                'success': True,
                'projects': projects
            }), 200

        except Exception as e:
            app_logger.error(f"Error getting user projects: {e}")
            return jsonify({'error': 'Failed to get projects'}), 500

    def handle_add_project_comment(self, project_id: int):
        """Add a comment to a project"""
        try:
            if 'user' not in session:
                return response_service.validation_error('Not logged in'), 401

            data = request.get_json()
            if not data:
                return response_service.validation_error('Request body must be JSON'), 400

            user_id = session['user']['id']
            comment_text = data.get('comment')

            if not comment_text:
                return response_service.validation_error('Comment text is required'), 400

            # Save the comment to the database
            comment_id = self.db_manager.add_project_comment(project_id, user_id, comment_text)

            if comment_id:
                # Add comment event to project history
                self.db_manager.add_project_history_event(
                    project_id, 
                    user_id, 
                    'comment_added', 
                    'Added a new comment'
                )

                app_logger.info(f"Comment added to project {project_id} by user {user_id}")
                return jsonify({'success': True, 'comment_id': comment_id, 'message': 'Comment added successfully'})
            else:
                return jsonify({'error': 'Failed to save comment to database'}), 500

        except Exception as e:
            app_logger.error(f"Error adding project comment: {e}")
            return jsonify({'error': 'Failed to add project comment'}), 500

    def handle_add_project_note(self, project_id: int):
        """Add a note to a project"""
        try:
            if 'user' not in session:
                return response_service.validation_error('Not logged in'), 401

            data = request.get_json()
            if not data:
                return response_service.validation_error('Request body must be JSON'), 400

            user_id = session['user']['id']
            note_text = data.get('note')

            if not note_text:
                return response_service.validation_error('Note text is required'), 400

            # Save the note to the database
            note_id = self.db_manager.add_project_note(project_id, user_id, note_text)

            if note_id:
                # Add note event to project history
                self.db_manager.add_project_history_event(
                    project_id, 
                    user_id, 
                    'note_added', 
                    'Added a new note'
                )

                app_logger.info(f"Note added to project {project_id} by user {user_id}")
                return jsonify({'success': True, 'note_id': note_id, 'message': 'Note added successfully'})
            else:
                return jsonify({'error': 'Failed to save note to database'}), 500

        except Exception as e:
            app_logger.error(f"Error adding project note: {e}")
            return jsonify({'error': 'Failed to add project note'}), 500

    def handle_update_project_settings(self, project_id: int):
        """Update project settings"""
        try:
            if 'user' not in session:
                return response_service.validation_error('Not logged in'), 401

            data = request.get_json()
            if not data:
                return response_service.validation_error('Request body must be JSON'), 400

            user_id = session['user']['id']
            units = data.get('units')
            visibility = data.get('visibility')

            if not units or not visibility:
                return response_service.validation_error('Units and visibility are required'), 400

            # Validate values
            if units not in ['metric', 'imperial']:
                return response_service.validation_error('Invalid units value'), 400

            if visibility not in ['private', 'team', 'public']:
                return response_service.validation_error('Invalid visibility value'), 400

            # Update project settings in database
            updated = self.db_manager.update_project_settings(project_id, user_id, units, visibility)

            if updated:
                # Add settings update event to project history
                self.db_manager.add_project_history_event(
                    project_id, 
                    user_id, 
                    'settings_updated', 
                    f"Project settings updated (Units: {units}, Visibility: {visibility})"
                )

                app_logger.info(f"Project {project_id} settings updated by user {user_id}")
                return jsonify({'success': True, 'message': 'Settings updated successfully'})
            else:
                return jsonify({'error': 'Failed to update project settings'}), 500

        except Exception as e:
            app_logger.error(f"Error updating project settings: {e}")
            return jsonify({'error': 'Failed to update project settings'}), 500

    def handle_project_snapshot(self, project_id: int):
        """Handle project snapshot operations"""
        try:
            if request.method == 'GET':
                # Get project snapshot
                snapshot_type = request.args.get('type')
                app_logger.info(f"Getting project snapshot for project {project_id}, type: {snapshot_type}")

                snapshot = self.db_manager.get_project_snapshot(project_id, snapshot_type)
                app_logger.info(f"Snapshot result: {snapshot}")

                if snapshot:
                    return jsonify({
                        'success': True,
                        'snapshot': {
                            'id': snapshot['id'],
                            'project_id': snapshot['project_id'],
                            'snapshot_type': snapshot['snapshot_type'],
                            'snapshot_data': snapshot['snapshot_data'],
                            'description': snapshot['description'],
                            'created_at': snapshot['created_at'],
                            'updated_at': snapshot['updated_at'],
                            'user_id': snapshot['user_id'],
                            'username': snapshot['username']
                        }
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No snapshot found'
                    }), 404

            elif request.method == 'POST':
                # Save/update project snapshot
                if 'user' not in session:
                    return jsonify({'error': 'Not logged in'}), 401

                data = request.get_json()
                if not data:
                    return jsonify({'error': 'Request body must be JSON'}), 400

                user_id = session['user']['id']
                snapshot_type = data.get('snapshot_type')
                snapshot_data = data.get('snapshot_data')
                description = data.get('description', '')

                if not snapshot_type or not snapshot_data:
                    return jsonify({'error': 'Snapshot type and data are required'}), 400

                # Save snapshot to database
                snapshot_id = self.db_manager.save_project_snapshot(
                    project_id, user_id, snapshot_type, snapshot_data, description
                )

                if snapshot_id:
                    # Add snapshot event to project history
                    self.db_manager.add_project_history_event(
                        project_id, 
                        user_id, 
                        'snapshot_created', 
                        f"Project snapshot created: {description or snapshot_type}"
                    )

                    app_logger.info(f"Project snapshot saved: {snapshot_type} for project {project_id}")
                    return jsonify({
                        'success': True, 
                        'snapshot_id': snapshot_id,
                        'message': 'Snapshot saved successfully'
                    }), 200
                else:
                    return jsonify({'error': 'Failed to save snapshot'}), 500

        except Exception as e:
            app_logger.error(f"Error handling project snapshot: {e}")
            return jsonify({'error': 'Failed to handle project snapshot'}), 500

    def handle_get_project_data(self, project_id):
        """Get project data as JSON"""
        try:
            user_info = session.get('user')
            if not user_info:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401

            # Get project data from database
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, user_id, name, address, site_information, created_at, updated_at
                    FROM projects
                    WHERE id = ? AND user_id = ?
                ''', (project_id, user_info['id']))

                project_data = cursor.fetchone()

            if not project_data:
                return jsonify({'success': False, 'error': 'Project not found'}), 404

            # Convert to dictionary
            project = {
                'id': project_data[0],
                'user_id': project_data[1],
                'name': project_data[2],
                'address': project_data[3],
                'site_information': project_data[4],
                'created_at': project_data[5],
                'updated_at': project_data[6]
            }

            app_logger.info(f"Project data requested for project ID: {project_id}")

            return jsonify({'success': True, 'project': project}), 200

        except Exception as e:
            app_logger.error(f"Error getting project data: {e}")
            return jsonify({'success': False, 'error': 'Failed to get project data'}), 500

    

    def handle_get_project_address(self):
        """Get project address for site inspector"""
        try:
            if 'user' not in session:
                return jsonify({'success': False, 'error': 'Not authenticated'}), 401

            project_id = request.args.get('project_id')
            if not project_id:
                return jsonify({'success': False, 'error': 'Project ID required'}), 400

            # Clean up malformed project IDs (remove any extra parameters)
            if '?' in project_id:
                project_id = project_id.split('?')[0]

            # Validate project ID is numeric
            try:
                project_id = int(project_id)
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid project ID format'}), 400

            user_id = session['user']['id']

            # Get project data from database including coordinates
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT name, address, site_information, location_lat, location_lng
                    FROM projects
                    WHERE id = ? AND user_id = ?
                ''', (project_id, user_id))

                project_data = cursor.fetchone()

            if not project_data:
                return jsonify({'success': False, 'error': 'Project not found'}), 404

            project_name, site_address, site_information, location_lat, location_lng = project_data

            app_logger.info(f"Project address requested for project ID: {project_id} - {project_name} at {site_address}")

            # Build response with coordinates if available
            response_data = {
                'success': True,
                'site_address': site_address,
                'project_name': project_name,
                'site_information': site_information
            }

            # Include coordinates if they exist
            if location_lat is not None and location_lng is not None:
                try:
                    lat = float(location_lat)
                    lng = float(location_lng)
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        response_data['location'] = {'lat': lat, 'lng': lng}
                        app_logger.info(f"Including stored coordinates: lat={lat}, lng={lng}")
                except (ValueError, TypeError):
                    app_logger.warning(f"Invalid coordinates in database: lat={location_lat}, lng={location_lng}")

            return jsonify(response_data), 200

        except Exception as e:
            app_logger.error(f"Error getting project address: {e}")
            return jsonify({'success': False, 'error': 'Failed to get project address'}), 500

    def handle_delete_project(self, project_id: int):
        """Delete a project"""
        try:
            if 'user' not in session:
                return jsonify({'error': 'Not logged in'}), 401

            user_id = session['user']['id']

            # Check if project exists and belongs to user
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT name FROM projects 
                    WHERE id = ? AND user_id = ?
                ''', (project_id, user_id))

                project = cursor.fetchone()

            if not project:
                return jsonify({'error': 'Project not found or access denied'}), 404

            project_name = project[0]

            # Delete project and related data
            success = self.db_manager.delete_project(project_id, user_id)

            if success:
                # Verify deletion was complete
                verification_results = self.db_manager.verify_project_deletion(project_id)
                total_remaining = sum(verification_results.values())
                
                if total_remaining > 0:
                    app_logger.error(f"Project {project_id} deletion incomplete. Remaining records: {verification_results}")
                    return jsonify({
                        'error': 'Project deletion incomplete',
                        'details': verification_results
                    }), 500
                
                app_logger.info(f"Project {project_id} '{project_name}' deleted completely by user {user_id}")
                return jsonify({
                    'success': True,
                    'message': f"Project '{project_name}' deleted successfully"
                }), 200
            else:
                app_logger.error(f"Failed to delete project {project_id} from database")
                return jsonify({'error': 'Failed to delete project from database'}), 500

        except Exception as e:
            app_logger.error(f"Error deleting project {project_id}: {e}")
            return jsonify({'error': 'Failed to delete project'}), 500

    