"""
Page Rendering Routes Module
"""
from flask import render_template, session, flash, redirect, url_for
from utils.logger import app_logger
from functools import wraps  # Import wraps
# Assuming get_user_by_id is defined elsewhere
# from your_module import get_user_by_id


# Dummy implementations for demonstration only - Replace with actual implementations
def get_user_by_id(user_id):
    """Dummy function to simulate getting a user by ID."""
    # Replace this with your actual user retrieval logic from your database
    class User:
        def __init__(self, id, username, email, first_name, last_name, profile_picture, account_type):
            self.id = id
            self.username = username
            self.email = email
            self.first_name = first_name
            self.last_name = last_name
            self.profile_picture = profile_picture
            self.account_type = account_type

    if user_id == 1:
        return User(id=1, username='testuser', email='test@example.com', first_name='Test', last_name='User',
                    profile_picture='/static/uploads/profile_pictures/4_3d492b1e1b644ec2996066e1cf27c562.jpg',
                    account_type='admin')
    return None


def login_required(f):
    """Dummy login required decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Replace this with your actual login check logic
        user = session.get('user')
        if user is None:
            flash('Login required', 'error')
            return redirect(url_for('login'))  # Assuming you have a login route
        return f(*args, **kwargs)

    return decorated_function


class PageRoutes:
    """Page rendering route handlers"""

    def register_routes(self, app):
        """Register page rendering routes"""
        app.route('/', endpoint='index')(self.handle_index)
        app.route('/blueprints', methods=['GET'])(self.handle_blueprints)
        app.route('/toolshop', methods=['GET'])(self.handle_toolshop)
        app.route('/dashboard')(self.dashboard)  # Add dashboard route


    def handle_index(self):
        """Main landing page"""
        user = session.get('user')
        if user:
            # Get complete user profile including profile picture
            from routes.auth_routes import AuthRoutes
            auth_handler = AuthRoutes()
            user_profile = auth_handler.get_user_profile(user['id'])
            if user_profile:
                user.update(user_profile)
        return render_template('index.html', user=user)

    def handle_blueprints(self):
        """Blueprints page"""
        user = session.get('user')
        if user:
            # Get complete user profile including profile picture
            from routes.auth_routes import AuthRoutes
            auth_handler = AuthRoutes()
            user_profile = auth_handler.get_user_profile(user['id'])
            if user_profile:
                user.update(user_profile)
        return render_template('blueprints.html', user=user)

    def handle_toolshop(self):
        """Tool shop page"""
        user = session.get('user')
        if user:
            # Get complete user profile including profile picture
            from routes.auth_routes import AuthRoutes
            auth_handler = AuthRoutes()
            user_profile = auth_handler.get_user_profile(user['id'])
            if user_profile:
                user.update(user_profile)
        return render_template('toolshop.html', user=user)

    @login_required
    def dashboard(self):
        """Dashboard page - main application interface"""
        user_id = session.get('user')['id']
        username = session.get('user')['username']
        app_logger.info(f"Dashboard accessed by user: {username}")

        # Get complete user profile including profile picture
        from routes.auth_routes import AuthRoutes
        auth_handler = AuthRoutes()
        user_profile = auth_handler.get_user_profile(user_id)
        
        if not user_profile:
            flash('User session invalid. Please log in again.', 'error')
            return redirect(url_for('login'))

        # Start with session user data and update with profile data
        user_info = session.get('user').copy()
        user_info.update(user_profile)
        
        # Ensure all required fields are present
        if not user_info.get('username'):
            user_info['username'] = username
        if not user_info.get('first_name'):
            user_info['first_name'] = username
            
        # Debug log the user info to check profile picture
        app_logger.info(f"Dashboard user profile data: {user_info}")
        if user_info.get('profile_picture'):
            app_logger.info(f"Profile picture URL: {user_info['profile_picture']}")
        else:
            app_logger.info("No profile picture found in user data")

        # Ensure profile picture is properly formatted for template
        if user_info.get('profile_picture') and user_info['profile_picture'] != 'None':
            # Make sure the profile picture URL is properly formatted
            profile_pic = user_info['profile_picture']
            if not profile_pic.startswith('/') and not profile_pic.startswith('http'):
                user_info['profile_picture'] = f"/static/uploads/profile_pictures/{profile_pic}"
        else:
            user_info['profile_picture'] = None

        return render_template('dashboard.html', user=user_info)