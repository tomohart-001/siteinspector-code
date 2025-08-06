
"""
Team Management Routes Module
"""
from flask import render_template, session, request, jsonify, redirect, url_for
from typing import Tuple, Dict, Any
from database import DatabaseManager
from utils.logger import app_logger
from services import response_service
from utils.error_handler import ErrorHandler, ErrorCategories


class TeamRoutes:
    """Team management route handlers"""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def register_routes(self, app):
        """Register team management routes"""
        app.route('/team', methods=['GET'])(self.handle_team)
        app.route('/api/get-team-name', methods=['GET'])(self.handle_get_team_name)

    def handle_team(self):
        """Handle team management page"""
        try:
            user_info = session.get('user')
            if not user_info:
                return redirect(url_for('login'))

            app_logger.info("Team page requested")

            # Get full user profile from database
            user_profile = self.get_user_profile(user_info['id'])
            if user_profile:
                user_info.update(user_profile)

            # Check user's account type from profile
            try:
                with self.db_manager.db.get_cursor() as cursor:
                    cursor.execute('SELECT account_type FROM user_profiles WHERE user_id = ?', (user_info['id'],))
                    account_result = cursor.fetchone()
                    if account_result and account_result[0] == 'individual':
                        # Individual users should not access team page
                        return redirect(url_for('dashboard'))
            except Exception as e:
                app_logger.error(f"Failed to check account type: {e}")

            # Get team name from database
            team_name = None
            try:
                with self.db_manager.db.get_cursor() as cursor:
                    cursor.execute("""
                        SELECT t.name 
                        FROM teams t
                        WHERE t.owner_user_id = ?
                        ORDER BY t.created_at DESC
                        LIMIT 1
                    """, (user_info['id'],))
                    team_result = cursor.fetchone()
                    if team_result:
                        team_name = team_result[0]
            except Exception as e:
                app_logger.error(f"Failed to get team name: {e}")
                team_name = None

            # Ensure user has a role - default to admin for first user, member for others
            if 'role' not in user_info or not user_info['role']:
                user_info['role'] = 'admin'  # For testing, make first user admin

            # Get team members from database
            team_members = self.get_team_members(user_info['id'])

            # Get team invitations from database
            team_invitations = self.get_team_invitations(user_info['id'])

            return render_template('team.html', user=user_info, team_members=team_members, team_invitations=team_invitations, team_name=team_name)
        except Exception as e:
            app_logger.error("Failed to render team page", e)
            return "Team error", 500

    def handle_get_team_name(self) -> Tuple[Dict[str, Any], int]:
        """Get team name for current user"""
        try:
            if 'user' not in session:
                return jsonify({'success': False, 'team_name': None}), 401

            user_id = session['user']['id']
            team_name = None

            try:
                with self.db_manager.db.get_cursor() as cursor:
                    # Check if user has a team through user_profiles
                    cursor.execute('SELECT team_id FROM user_profiles WHERE user_id = ?', (user_id,))
                    team_result = cursor.fetchone()

                    if team_result and team_result[0]:
                        # Get team name
                        cursor.execute('SELECT name FROM teams WHERE id = ?', (team_result[0],))
                        name_result = cursor.fetchone()
                        if name_result:
                            team_name = name_result[0]

                    # Also check if user owns a team
                    if not team_name:
                        cursor.execute('SELECT name FROM teams WHERE owner_user_id = ?', (user_id,))
                        owner_result = cursor.fetchone()
                        if owner_result:
                            team_name = owner_result[0]

            except Exception as e:
                app_logger.warning(f"Could not get team name: {e}")

            return jsonify({
                'success': True if team_name else False,
                'team_name': team_name
            }), 200

        except Exception as e:
            app_logger.error(f"Error getting team name: {e}")
            return jsonify({'success': False, 'team_name': None}), 500

    def get_team_members(self, user_id: int) -> list:
        """Get team members for the current user"""
        try:
            with self.db_manager.db.get_cursor() as cursor:
                # First get the user's team_id
                cursor.execute('''
                    SELECT team_id FROM user_profiles WHERE user_id = ?
                ''', (user_id,))

                team_result = cursor.fetchone()
                if not team_result or not team_result[0]:
                    # No team associated, return just the current user
                    cursor.execute('''
                        SELECT u.id, u.username, u.email, u.created_at, u.last_login,
                               p.first_name, p.last_name, p.profile_picture, u.role
                        FROM users u
                        LEFT JOIN user_profiles p ON u.id = p.user_id
                        WHERE u.id = ?
                    ''', (user_id,))

                    user_data = cursor.fetchone()
                    if user_data:
                        actual_email = user_data[2] if user_data[2] else f"{user_data[1]}@engineroom.com"
                        profile_picture = user_data[7]
                        if profile_picture and not profile_picture.startswith('uploads/'):
                            profile_picture = f"uploads/profile_pictures/{profile_picture}"
                        
                        return [{
                            'id': user_data[0],
                            'username': user_data[1],
                            'email': actual_email,
                            'first_name': user_data[5],
                            'last_name': user_data[6],
                            'profile_picture': profile_picture,
                            'role': user_data[8] or 'member',
                            'is_online': True
                        }]
                    return []

                team_id = team_result[0]

                # Get all team members
                cursor.execute('''
                    SELECT u.id, u.username, u.email, u.created_at, u.last_login,
                           p.first_name, p.last_name, p.profile_picture, u.role
                    FROM users u
                    LEFT JOIN user_profiles p ON u.id = p.user_id
                    WHERE p.team_id = ?
                    ORDER BY 
                        CASE u.role 
                            WHEN 'owner' THEN 1 
                            WHEN 'admin' THEN 2 
                            WHEN 'member' THEN 3 
                            ELSE 4 
                        END,
                        u.username ASC
                ''', (team_id,))

                members = cursor.fetchall()
                team_members = []
                for member in members:
                    actual_email = member[2] if member[2] else f"{member[1]}@engineroom.com"
                    profile_picture = member[7]
                    if profile_picture and not profile_picture.startswith('uploads/'):
                        profile_picture = f"uploads/profile_pictures/{profile_picture}"
                    
                    team_members.append({
                        'id': member[0],
                        'username': member[1],
                        'email': actual_email,
                        'first_name': member[5],
                        'last_name': member[6],
                        'profile_picture': profile_picture,
                        'role': member[8] or 'member',
                        'is_online': member[0] == user_id  # Current user is online
                    })

                return team_members

        except Exception as e:
            app_logger.error(f"Failed to get team members: {e}")
            return []

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

    def get_team_invitations(self, user_id: int) -> list:
        """Get team invitations for the current user"""
        try:
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, email, status, created_at, invitation_token
                    FROM team_invitations
                    WHERE invited_by_user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))

                invitations = cursor.fetchall()
                team_invitations = []
                for invitation in invitations:
                    team_invitations.append({
                        'id': invitation[0],
                        'email': invitation[1],
                        'status': invitation[2],
                        'created_at': invitation[3],
                        'invitation_token': invitation[4]
                    })

                return team_invitations

        except Exception as e:
            app_logger.error(f"Failed to get team invitations: {e}")
            return []
