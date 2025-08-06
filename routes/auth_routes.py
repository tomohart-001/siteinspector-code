"""Modified authentication routes to include user profile data in dashboard settings."""
from flask import request, jsonify, render_template, session, url_for, redirect
from auth import authenticate_user, create_user, create_user_extended, hash_password, verify_password, get_user_by_id, authenticate_user_by_email
from database import UserProfileRepository, DatabaseManager
from utils.logger import app_logger
from utils.validators import ValidationError


class AuthRoutes:
    """Authentication route handlers"""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def register_routes(self, app):
        """Register authentication routes with Flask app"""
        app.route('/login', methods=['GET', 'POST'], endpoint='login')(self.handle_login)
        app.route('/signup', methods=['POST'], endpoint='signup')(self.handle_signup)
        app.route('/signup-step2', methods=['GET'], endpoint='signup_step2')(self.handle_signup_step2)
        app.route('/signup-step3', methods=['GET'], endpoint='signup_step3')(self.handle_signup_step3)
        app.route('/logout', methods=['POST'], endpoint='logout')(self.handle_logout)
        app.route('/api/update-settings', methods=['POST'], endpoint='update_settings')(self.handle_update_settings)
        app.route('/api/get-user-profile', methods=['GET'], endpoint='get_user_profile')(self.handle_get_user_profile)
        app.route('/api/check-username', methods=['POST'], endpoint='check_username')(self.handle_check_username)
        app.route('/api/check-email', methods=['POST'], endpoint='check_email')(self.handle_check_email)
        app.route('/api/setup-team', methods=['POST'], endpoint='setup_team')(self.handle_setup_team)
        app.route('/api/upload-profile-picture', methods=['POST'], endpoint='upload_profile_picture')(self.handle_upload_profile_picture)
        app.route('/api/get-team-name', methods=['GET'], endpoint='get_team_name')(self.handle_get_team_name)
        app.route('/api/get-team-details', methods=['GET'], endpoint='get_team_details')(self.handle_get_team_details)
        app.route('/api/update-team-details', methods=['POST'], endpoint='update_team_details')(self.handle_update_team_details)
        app.route('/api/delete-team', methods=['POST'], endpoint='delete_team')(self.handle_delete_team)
        app.route('/dashboard-settings', methods=['GET'], endpoint='dashboard_settings')(self.handle_dashboard_settings)
        app.route('/api/leave-team', methods=['POST'], endpoint='leave_team')(self.handle_leave_team)
        app.route('/api/apply-invitation-token', methods=['POST'], endpoint='apply_invitation_token')(self.handle_apply_invitation_token)

    def handle_login(self):
        """Handle login page or login request"""
        if request.method == 'GET':
            app_logger.debug("Login page requested")
            return render_template('login.html')

        try:
            # Log incoming login attempt
            client_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', 'Unknown')
            app_logger.info(f"Login attempt from {client_ip} - {user_agent}")

            data = request.get_json()
            if not data:
                app_logger.warning("Login request missing JSON data")
                return jsonify({'error': 'Invalid request format'}), 400

            email = data.get('email', '').strip()
            password = data.get('password', '')

            # Log validation details (without password)
            app_logger.debug(f"Login validation - email: '{email}', password_length: {len(password) if password else 0}")

            if not email or not password:
                app_logger.warning(f"Login validation failed - missing credentials for email: '{email}'")
                return jsonify({'error': 'Email and password are required'}), 400

            # Email validation
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, email):
                app_logger.warning(f"Login validation failed - invalid email format: '{email}'")
                return jsonify({'error': 'Please enter a valid email address'}), 400

            if len(password) < 6:
                app_logger.warning(f"Login validation failed - password too short for user: '{email}'")
                return jsonify({'error': 'Password must be at least 6 characters'}), 400

            # Attempt authentication
            app_logger.debug(f"Attempting authentication for user: '{email}'")
            result = authenticate_user_by_email(email, password)

            if result.get('success'):
                session['user'] = {
                    'id': result['id'],
                    'username': result['username']
                }
                app_logger.info(f"✅ User '{result['username']}' (ID: {result['id']}) logged in successfully from {client_ip}")
                return jsonify({'success': True, 'redirect': '/dashboard'}), 200
            else:
                error_msg = result.get('error', 'Login failed')
                # Update generic authentication error to be more specific
                if error_msg == 'Invalid username or password':
                    error_msg = 'Invalid email address or password'
                app_logger.warning(f"❌ Login failed for user '{email}' from {client_ip}: {error_msg}")
                return jsonify({'error': error_msg}), 401

        except Exception as e:
            app_logger.error(f"🚨 Login system error for user '{email if 'email' in locals() else 'unknown'}': {str(e)}")
            return jsonify({'error': 'Login system temporarily unavailable'}), 500

    def handle_signup(self):
        """Handle user signup with multi-step process"""
        try:
            # Log incoming signup attempt
            client_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', 'Unknown')
            app_logger.info(f"Signup attempt from {client_ip} - {user_agent}")

            data = request.get_json()
            if not data:
                app_logger.warning("Signup request missing JSON data")
                return jsonify({'error': 'Invalid request format'}), 400

            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            username = data.get('username', '').strip()
            account_type = data.get('account_type', '').strip()
            subscribe_to_updates = data.get('subscribe_to_updates', False)

            # Log validation details (without passwords)
            app_logger.debug(f"Signup validation - email: '{email}', username: '{username}', account_type: '{account_type}', password_length: {len(password) if password else 0}")

            # Comprehensive validation with detailed logging
            if not email or not password or not username or not account_type:
                app_logger.warning(f"Signup validation failed - missing required fields for email: '{email}'")
                return jsonify({'error': 'All fields are required'}), 400

            # Email validation (already validated in step 1, but keeping as safety check)
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, email):
                app_logger.warning(f"Signup validation failed - invalid email format: '{email}'")
                return jsonify({'error': 'Please enter a valid email address'}), 400

            # Username validation
            if len(username) < 3:
                app_logger.warning(f"Signup validation failed - username too short: '{username}'")
                return jsonify({'error': 'Username must be at least 3 characters'}), 400

            # Username format validation (alphanumeric and underscores only)
            username_pattern = r'^[a-zA-Z0-9_]+$'
            if not re.match(username_pattern, username):
                app_logger.warning(f"Signup validation failed - invalid username format: '{username}'")
                return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

            # Password validation
            if len(password) < 6:
                app_logger.warning(f"Signup validation failed - password too short for user: '{email}' (length: {len(password)})")
                return jsonify({'error': 'Password must be at least 6 characters'}), 400

            if password != confirm_password:
                app_logger.warning(f"Signup validation failed - password mismatch for user: '{email}'")
                return jsonify({'error': 'Passwords do not match'}), 400

            # Account type validation
            if account_type not in ['individual', 'team']:
                app_logger.warning(f"Signup validation failed - invalid account type: '{account_type}'")
                return jsonify({'error': 'Please select a valid account type'}), 400

            # Attempt user creation with additional fields
            app_logger.debug(f"Attempting to create new user: '{email}' with username: '{username}'")
            result = create_user_extended(email, password, username, account_type, subscribe_to_updates)

            if result.get('success'):
                try:
                    # Set user role based on account type
                    if account_type == 'team':
                        # Set team account users as owners
                        with self.db_manager.db.get_cursor() as cursor:
                            cursor.execute('UPDATE users SET role = ? WHERE id = ?', ('owner', result['id']))
                        app_logger.info(f"Set user {result['id']} role to 'owner' for team account")

                    # Save profile data to user_profiles table
                    profile_data = {
                        'account_type': account_type,
                        'subscribe_to_updates': subscribe_to_updates
                    }
                    profile_saved = UserProfileRepository.save_user_profile(result['id'], profile_data)

                    if not profile_saved:
                        app_logger.error(f"Failed to save user profile for user ID: {result['id']}")
                        return jsonify({'error': 'User created but profile setup failed'}), 500

                    session['user'] = {
                        'id': result['id'],
                        'username': result['username'],
                        'email': result['email']
                    }
                    app_logger.info(f"✅ New user '{result['username']}' (ID: {result['id']}) created and logged in from {client_ip}")
                    return jsonify({'success': True, 'redirect': '/dashboard'}), 201

                except Exception as profile_error:
                    app_logger.error(f"Profile creation error for user {result['id']}: {str(profile_error)}")
                    return jsonify({'error': 'User created but profile setup failed'}), 500
            else:
                error_msg = result.get('error', 'Signup failed')
                app_logger.warning(f"❌ Signup failed for user '{email}' from {client_ip}: {error_msg}")
                return jsonify({'error': error_msg}), 400

        except Exception as e:
            app_logger.error(f"🚨 Signup system error for user '{email if 'email' in locals() else 'unknown'}': {str(e)}")
            return jsonify({'error': 'Signup system temporarily unavailable'}), 500

    def handle_logout(self):
        """Handle user logout"""
        client_ip = request.remote_addr
        username = session.get('user', {}).get('username', 'Unknown')
        user_id = session.get('user', {}).get('id', 'Unknown')

        app_logger.info(f"🚪 User '{username}' (ID: {user_id}) logged out from {client_ip}")
        session.clear()

        return redirect(url_for('index'))

    def handle_update_settings(self):
        """Handle settings update request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid request format'}), 400

            app_logger.info(f"Settings update request from user {user_id} at {client_ip}")

            # Prepare profile data
            profile_data = {}

            # Handle basic profile fields
            if 'firstName' in data and data['firstName'].strip():
                profile_data['first_name'] = data['firstName'].strip()
            if 'lastName' in data and data['lastName'].strip():
                profile_data['last_name'] = data['lastName'].strip()
            if 'email' in data and data['email'].strip():
                profile_data['email'] = data['email'].strip()
            if 'subscribeToUpdates' in data:
                profile_data['subscribe_to_updates'] = data['subscribeToUpdates']

            # Handle password change if provided
            password_updated = False
            if data.get('currentPassword') and data.get('newPassword'):
                current_password = data['currentPassword']
                new_password = data['newPassword']
                confirm_password = data.get('confirmPassword')

                # Validate password change
                if new_password != confirm_password:
                    return jsonify({'error': 'New passwords do not match'}), 400

                if len(new_password) < 6:
                    return jsonify({'error': 'New password must be at least 6 characters'}), 400

                # Verify current password
                from auth import get_user_by_id
                user_data = get_user_by_id(user_id)
                if not user_data or not verify_password(current_password, user_data['password_hash']):
                    return jsonify({'error': 'Current password is incorrect'}), 400

                # Update password
                new_password_hash = hash_password(new_password)
                if UserProfileRepository.update_user_password(user_id, new_password_hash):
                    password_updated = True
                else:
                    return jsonify({'error': 'Failed to update password'}), 500

            # Save profile data
            if profile_data:
                if not UserProfileRepository.save_user_profile(user_id, profile_data):
                    return jsonify({'error': 'Failed to update profile'}), 500

            # Update session if email was changed
            if 'email' in profile_data:
                session['user']['email'] = profile_data['email']

            app_logger.info(f"Settings updated successfully for user {user_id}")

            response_data = {'success': True, 'message': 'Settings updated successfully'}
            if password_updated:
                response_data['password_updated'] = True

            return jsonify(response_data), 200

        except Exception as e:
            app_logger.error(f"Settings update error: {str(e)}")
            return jsonify({'error': 'Settings update failed'}), 500

    def handle_get_user_profile(self):
        """Handle get user profile request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']

            # Get user profile
            profile = UserProfileRepository.get_user_profile(user_id)
            if not profile:
                return jsonify({'error': 'Profile not found'}), 404

            # Get team name if user has a team
            team_name = None
            if profile.get('team_id'):
                try:
                    with self.db_manager.db.get_cursor() as cursor:
                        cursor.execute('SELECT name FROM teams WHERE id = ?', (profile['team_id'],))
                        team_result = cursor.fetchone()
                        if team_result:
                            team_name = team_result[0]
                except Exception as e:
                    app_logger.error(f"Failed to get team name: {e}")

            # Get user role
            user_role = None
            try:
                with self.db_manager.db.get_cursor() as cursor:
                    cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
                    role_result = cursor.fetchone()
                    if role_result:
                        user_role = role_result[0]
            except Exception as e:
                app_logger.error(f"Failed to get user role: {e}")

            # Return profile data (excluding sensitive information)
            response_data = {
                'username': profile['username'],
                'email': profile['email'] or '',
                'first_name': profile['first_name'] or '',
                'last_name': profile['last_name'] or '',
                'profile_picture': profile['profile_picture'] or '',
                'account_type': profile['account_type'] or 'individual',
                'subscribe_to_updates': profile['subscribe_to_updates'] or False,
                'team_id': profile.get('team_id'),
                'team_name': team_name,
                'role': user_role,
                'created_at': profile['created_at'],
                'updated_at': profile['updated_at']
            }

            return jsonify(response_data), 200

        except Exception as e:
            app_logger.error(f"Get user profile error: {str(e)}")
            return jsonify({'error': 'Failed to get profile'}), 500

    def handle_check_username(self):
        """Handle username availability check"""
        try:
            data = request.get_json()
            if not data or 'username' not in data:
                return jsonify({'error': 'Username is required'}), 400

            username = data['username'].strip()

            # Basic validation
            if len(username) < 3:
                return jsonify({'available': False, 'error': 'Username too short'}), 400

            # Check format
            import re
            username_pattern = r'^[a-zA-Z0-9_]+$'
            if not re.match(username_pattern, username):
                return jsonify({'available': False, 'error': 'Invalid username format'}), 400

            # Check if username exists in database
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', (username,))
                count = cursor.fetchone()[0]

                available = count == 0
                return jsonify({'available': available}), 200

        except Exception as e:
            app_logger.error(f"Username check error: {str(e)}")
            return jsonify({'error': 'Username check failed'}), 500

    def handle_check_email(self):
        """Handle email availability check"""
        try:
            data = request.get_json()
            if not data or 'email' not in data:
                return jsonify({'error': 'Email is required'}), 400

            email = data['email'].strip()

            # Basic email validation
            import re
            email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_pattern, email):
                return jsonify({'available': False, 'error': 'Invalid email format'}), 400

            # Check if email exists in database
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM users WHERE email = ?', (email,))
                count = cursor.fetchone()[0]

                available = count == 0
                return jsonify({'available': available}), 200

        except Exception as e:
            app_logger.error(f"Email check error: {str(e)}")
            return jsonify({'error': 'Email check failed'}), 500

    def handle_signup_step2(self):
        """Handle signup step 2 page (username)"""
        try:
            app_logger.debug("Signup step 2 page requested")
            invitation_token = request.args.get('invite')
            return render_template('signup-username.html', invitation_token=invitation_token)
        except Exception as e:
            app_logger.error(f"Failed to render signup step 2 page: {e}")
            return "Signup step 2 error", 500

    def handle_signup_step3(self):
        """Handle signup step 3 page (account type)"""
        try:
            app_logger.debug("Signup step 3 page requested")
            return render_template('signup-account.html')
        except Exception as e:
            app_logger.error(f"Failed to render signup step 3 page: {e}")
            return "Signup step 3 error", 500

    def handle_setup_team(self):
        """Handle team setup request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid request format'}), 400

            team_name = data.get('teamName', '').strip()
            team_description = data.get('teamDescription', '').strip()
            team_size = data.get('teamSize', '').strip()

            if not team_name:
                return jsonify({'error': 'Team name is required'}), 400

            app_logger.info(f"Team setup request from user {user_id} at {client_ip}")

            # Create teams table if it doesn't exist
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS teams (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        size_range TEXT,
                        owner_user_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (owner_user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                ''')

                # Insert team data
                cursor.execute('''
                    INSERT INTO teams (name, description, size_range, owner_user_id)
                    VALUES (?, ?, ?, ?)
                ''', (team_name, team_description, team_size, user_id))

                team_id = cursor.lastrowid

                # Link the user to the team and set as owner
                cursor.execute('''
                    UPDATE user_profiles 
                    SET team_id = ?, account_type = 'team'
                    WHERE user_id = ?
                ''', (team_id, user_id))

                # Set user role to owner
                cursor.execute('''
                    UPDATE users 
                    SET role = 'owner' 
                    WHERE id = ?
                ''', (user_id,))

            app_logger.info(f"Team '{team_name}' created successfully for user {user_id} with ID {team_id}")

            return jsonify({
                'success': True, 
                'message': 'Team created successfully',
                'team_id': team_id
            }), 200

        except Exception as e:
            app_logger.error(f"Team setup error: {str(e)}")
            return jsonify({'error': 'Team setup failed'}), 500

    def handle_leave_team(self):
        """Handle leave team request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']

            with self.db_manager.db.get_cursor() as cursor:
                # Get user's current team
                cursor.execute('''
                    SELECT team_id FROM user_profiles WHERE user_id = ?
                ''', (user_id,))

                team_result = cursor.fetchone()
                if not team_result or not team_result[0]:
                    return jsonify({'error': 'User is not part of a team'}), 400

                team_id = team_result[0]

                # Check if user is the owner of the team
                cursor.execute('''
                    SELECT owner_user_id FROM teams WHERE id = ?
                ''', (team_id,))

                owner_result = cursor.fetchone()
                if owner_result and owner_result[0] == user_id:
                    return jsonify({'error': 'Team owners cannot leave their team. You must delete the team or transfer ownership first.'}), 400

                # Remove user from team
                cursor.execute('''
                    UPDATE user_profiles 
                    SET team_id = NULL 
                    WHERE user_id = ?
                ''', (user_id,))

                # Update user role back to member
                cursor.execute('''
                    UPDATE users 
                    SET role = 'member' 
                    WHERE id = ?
                ''', (user_id,))

                # Update session
                session['user']['role'] = 'member'
                if 'team_id' in session['user']:
                    del session['user']['team_id']

            app_logger.info(f"User {user_id} left team {team_id}")

            return jsonify({
                'success': True,
                'message': 'Successfully left team'
            }), 200

        except Exception as e:
            app_logger.error(f"Leave team error: {str(e)}")
            return jsonify({'error': 'Failed to leave team'}), 500

    def handle_dashboard_settings(self):
        """Handle dashboard settings page"""
        try:
            user_info = session.get('user')
            if not user_info:
                from flask import redirect, url_for
                return redirect(url_for('login'))

            # Get full user profile from database
            user_profile = self.get_user_profile(user_info['id'])
            if user_profile:
                user_info.update(user_profile)

            return render_template('dashboard-settings.html', user=user_info)
        except Exception as e:
            app_logger.error("Failed to render dashboard settings page", e)
            return "Dashboard settings error", 500

    def handle_upload_profile_picture(self):
        """Handle profile picture upload"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            # Check if file was uploaded
            if 'profile_picture' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400

            file = request.files['profile_picture']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400

            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
            file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

            if file_extension not in allowed_extensions:
                return jsonify({'error': 'Invalid file type. Please upload an image file.'}), 400

            # Validate file size (5MB limit)
            if len(file.read()) > 5 * 1024 * 1024:
                return jsonify({'error': 'File too large. Maximum size is 5MB.'}), 400

            # Reset file pointer
            file.seek(0)

            app_logger.info(f"Profile picture upload request from user {user_id} at {client_ip}")

            # Create uploads directory if it doesn't exist
            import os
            upload_dir = os.path.join('static', 'uploads', 'profile_pictures')
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename
            import uuid
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{user_id}_{uuid.uuid4().hex}.{file_extension}"
            file_path = os.path.join(upload_dir, filename)

            # Save file
            file.save(file_path)

            # Create URL for the uploaded file
            profile_picture_url = f"/static/uploads/profile_pictures/{filename}"

            # Update user profile in database
            profile_data = {'profile_picture': profile_picture_url}
            if not UserProfileRepository.save_user_profile(user_id, profile_data):
                # Clean up uploaded file if database update fails
                try:
                    os.remove(file_path)
                except:
                    pass
                return jsonify({'error': 'Failed to update profile picture in database'}), 500

            app_logger.info(f"Profile picture updated successfully for user {user_id}: {filename}")

            return jsonify({
                'success': True,
                'message': 'Profile picture updated successfully',
                'profile_picture_url': profile_picture_url
            }), 200

        except Exception as e:
            app_logger.error(f"Profile picture upload error: {str(e)}")
            return jsonify({'error': 'Profile picture upload failed'}), 500

    def handle_get_team_name(self):
        """Handle get team name request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']

            # Get user's team - check both via user_profiles and as team owner
            with self.db_manager.db.get_cursor() as cursor:
                # First try to get team via user_profiles
                cursor.execute('''
                    SELECT t.name 
                    FROM teams t
                    JOIN user_profiles p ON t.id = p.team_id
                    WHERE p.user_id = ?
                ''', (user_id,))

                team_result = cursor.fetchone()
                if team_result:
                    return jsonify({'success': True, 'team_name': team_result[0]}), 200

                # If no team found via user_profiles, check if user is a team owner
                cursor.execute('''
                    SELECT t.name 
                    FROM teams t
                    WHERE t.owner_user_id = ?
                ''', (user_id,))

                owner_team_result = cursor.fetchone()
                if owner_team_result:
                    # User owns a team but their profile isn't linked - fix this
                    cursor.execute('''
                        SELECT id FROM teams WHERE owner_user_id = ?
                    ''', (user_id,))
                    team_id_result = cursor.fetchone()

                    if team_id_result:
                        # Update user profile to link to their team
                        cursor.execute('''
                            UPDATE user_profiles 
                            SET team_id = ? 
                            WHERE user_id = ?
                        ''', (team_id_result[0], user_id))

                        app_logger.info(f"Fixed team association for user {user_id} - linked to team {team_id_result[0]}")

                    return jsonify({'success': True, 'team_name': owner_team_result[0]}), 200

                return jsonify({'success': False, 'team_name': None}), 200

        except Exception as e:
            app_logger.error(f"Get team name error: {str(e)}")
            return jsonify({'error': 'Failed to get team name'}), 500

    def handle_get_team_details(self):
        """Handle get team details request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']

            # Get user's team details
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT t.id, t.name, t.description, t.size_range, t.created_at, u.role
                    FROM teams t
                    JOIN user_profiles p ON t.id = p.team_id
                    JOIN users u ON u.id = ?
                    WHERE p.user_id = ?
                ''', (user_id, user_id))

                team_result = cursor.fetchone()
                if team_result:
                    # Check if user has permission to view team settings
                    user_role = team_result[5]
                    if user_role not in ['owner', 'admin']:
                        return jsonify({'error': 'Insufficient permissions'}), 403

                    return jsonify({
                        'success': True,
                        'team': {
                            'id': team_result[0],
                            'name': team_result[1],
                            'description': team_result[2],
                            'size_range': team_result[3],
                            'created_at': team_result[4]
                        }
                    }), 200
                else:
                    return jsonify({'error': 'Team not found'}), 404

        except Exception as e:
            app_logger.error(f"Get team details error: {str(e)}")
            return jsonify({'error': 'Failed to get team details'}), 500

    def handle_update_team_details(self):
        """Handle update team details request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid request format'}), 400

            team_name = data.get('name', '').strip()
            team_description = data.get('description', '').strip()
            team_size = data.get('size_range', '').strip()

            if not team_name:
                return jsonify({'error': 'Team name is required'}), 400

            if not team_size:
                return jsonify({'error': 'Team size is required'}), 400

            app_logger.info(f"Team update request from user {user_id} at {client_ip}")

            # Get user's team and check permissions
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT t.id, u.role
                    FROM teams t
                    JOIN user_profiles p ON t.id = p.team_id
                    JOIN users u ON u.id = ?
                    WHERE p.user_id = ?
                ''', (user_id, user_id))

                team_result = cursor.fetchone()
                if not team_result:
                    return jsonify({'error': 'Team not found'}), 404

                team_id, user_role = team_result
                if user_role not in ['owner', 'admin']:
                    return jsonify({'error': 'Insufficient permissions'}), 403

                # Update team details
                cursor.execute('''
                    UPDATE teams 
                    SET name = ?, description = ?, size_range = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (team_name, team_description, team_size, team_id))

            app_logger.info(f"Team '{team_name}' updated successfully by user {user_id}")

            return jsonify({
                'success': True, 
                'message': 'Team details updated successfully'
                }), 200

        except Exception as e:
            app_logger.error(f"Team update error: {str(e)}")
            return jsonify({'error': 'Team update failed'}), 500

    def handle_delete_team(self):
        """Handle delete team request"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            app_logger.info(f"Team deletion request from user {user_id} at {client_ip}")

            # Get user's team and check permissions
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT t.id, t.name, u.role
                    FROM teams t
                    JOIN user_profiles p ON t.id = p.team_id
                    JOIN users u ON u.id = ?
                    WHERE p.user_id = ?
                ''', (user_id, user_id))

                team_result = cursor.fetchone()
                if not team_result:
                    return jsonify({'error': 'Team not found'}), 404

                team_id, team_name, user_role = team_result
                if user_role != 'owner':
                    return jsonify({'error': 'Only team owners can delete teams'}), 403

                # Remove team_id from all user profiles and change account type to individual
                cursor.execute('''
                    UPDATE user_profiles 
                    SET team_id = NULL, account_type = 'individual'
                    WHERE team_id = ?
                ''', (team_id,))

                # Reset user roles to member for team members
                cursor.execute('''
                    UPDATE users 
                    SET role = 'member' 
                    WHERE id IN (
                        SELECT user_id FROM user_profiles WHERE team_id = ? OR user_id = ?
                    )
                ''', (team_id, user_id))

                # Delete the team
                cursor.execute('DELETE FROM teams WHERE id = ?', (team_id,))

            app_logger.info(f"Team '{team_name}' (ID: {team_id}) deleted successfully by user {user_id}")

            return jsonify({
                'success': True, 
                'message': 'Team deleted successfully',
                'clear_team_setup_flag': True  # Signal frontend to clear localStorage flag
            }), 200

        except Exception as e:
            app_logger.error(f"Team deletion error: {str(e)}")
            return jsonify({'error': 'Team deletion failed'}), 500

    def handle_apply_invitation_token(self):
        """Handle invitation token application"""
        try:
            # Check if user is logged in
            if 'user' not in session:
                return jsonify({'error': 'Not authenticated'}), 401

            user_id = session['user']['id']
            client_ip = request.remote_addr

            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid request format'}), 400

            invitation_token = data.get('invitation_token', '').strip()
            if not invitation_token:
                return jsonify({'error': 'Invitation token is required'}), 400

            app_logger.info(f"Invitation token application from user {user_id} at {client_ip}")

            # Check if user is already part of a team
            user_profile = UserProfileRepository.get_user_profile(user_id)
            if user_profile and user_profile.get('team_id'):
                return jsonify({'error': 'You are already part of a team. Please leave your current team first.'}), 400

            # Get invitation by token
            from database import TeamInvitationRepository
            invitation = TeamInvitationRepository.get_invitation_by_token(invitation_token)

            if not invitation:
                return jsonify({'error': 'Invalid or expired invitation token'}), 400

            # Accept the invitation
            if TeamInvitationRepository.accept_invitation(invitation['id'], user_id):
                app_logger.info(f"User {user_id} joined team {invitation['team_id']} via invitation token")
                return jsonify({
                    'success': True,
                    'message': f"Successfully joined team '{invitation['team_name']}'",
                    'team_name': invitation['team_name']
                }), 200
            else:
                return jsonify({'error': 'Failed to join team. Please try again.'}), 500

        except Exception as e:
            app_logger.error(f"Invitation token application error: {str(e)}")
            return jsonify({'error': 'Failed to apply invitation token'}), 500

    def get_user_profile(self, user_id: int) -> dict:
        """Get user profile data from database"""
        try:
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT u.id, u.username, u.email, u.created_at, u.last_login,
                           p.first_name, p.last_name, p.profile_picture
                    FROM users u
                    LEFT JOIN user_profiles p ON u.id = p.user_id
                    WHERE u.id = ?
                ''', (user_id,))

                user_data = cursor.fetchone()
                if user_data:
                    return {
                        'id': user_data[0],
                        'username': user_data[1],
                        'email': user_data[2],
                        'created_at': user_data[3],
                        'last_login': user_data[4],
                        'first_name': user_data[5],
                        'last_name': user_data[6],
                        'profile_picture': user_data[7]
                    }
                return {}

        except Exception as e:
            app_logger.error(f"Failed to get user profile: {e}")
            return {}


# Create route handler instance
auth_route_handler = AuthRoutes()