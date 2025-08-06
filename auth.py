from flask import session, jsonify, request
import uuid
import bcrypt
import psycopg2
from typing import Dict, Any, Optional
from database import db_manager

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def get_session_id():
    """Get or create session ID - use user ID if logged in"""
    # If user is logged in, use their user ID as session ID for persistence
    if 'user' in session and session['user'].get('id'):
        return f"user_{session['user']['id']}"

    # Otherwise use anonymous session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def clear_all_sessions():
    """Clear all active sessions"""
    from flask import session
    session.clear()



def create_user_extended(email: str, password: str, username: str, account_type: str, subscribe_to_updates: bool = False) -> dict:
    """
    Create a new user with extended signup information
    Returns: dict with 'success', 'error', 'id', 'username', 'email' keys
    """
    try:
        if not email or not password or not username:
            return {
                'success': False,
                'error': 'Email, password, and username are required'
            }

        # Validate email format
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return {
                'success': False,
                'error': 'Please enter a valid email address'
            }

        # Validate password length
        if len(password) < 6:
            return {
                'success': False,
                'error': 'Password must be at least 6 characters'
            }

        # Validate username length
        if len(username) < 3:
            return {
                'success': False,
                'error': 'Username must be at least 3 characters'
            }

        email = email.strip().lower()
        username = username.strip()

        # Use a transaction to ensure data consistency
        with db_manager.db.get_cursor() as cursor:
            try:
                # Check if email already exists
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                existing_user = cursor.fetchone()

                if existing_user:
                    return {
                        'success': False,
                        'error': 'Email already exists'
                    }

                # Check if username already exists
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                existing_username = cursor.fetchone()

                if existing_username:
                    return {
                        'success': False,
                        'error': 'Username already exists'
                    }

                # Hash password and create user
                password_hash = hash_password(password)
                cursor.execute('''
                    INSERT INTO users (username, email, password_hash, created_at) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (username, email, password_hash))

                user_id = cursor.lastrowid

                if not user_id:
                    raise DatabaseError("Failed to create user - no user ID returned")

                # Create user profile with additional information
                cursor.execute('''
                    INSERT INTO user_profiles 
                    (user_id, account_type, subscribe_to_updates)
                    VALUES (?, ?, ?)
                ''', (user_id, account_type, subscribe_to_updates))

                # Verify both user and profile were created
                cursor.execute('SELECT COUNT(*) FROM users WHERE id = ?', (user_id,))
                user_count = cursor.fetchone()[0]

                cursor.execute('SELECT COUNT(*) FROM user_profiles WHERE user_id = ?', (user_id,))
                profile_count = cursor.fetchone()[0]

                if user_count != 1 or profile_count != 1:
                    raise DatabaseError(f"Data integrity check failed - user: {user_count}, profile: {profile_count}")

                from utils.logger import app_logger
                app_logger.info(f"✅ User created successfully: {email} -> {username} (ID: {user_id}) with account type: {account_type}")

                return {
                    'success': True,
                    'id': user_id,
                    'username': username,
                    'email': email
                }

            except Exception as e:
                from utils.logger import app_logger
                app_logger.error(f"Transaction failed during user creation: {str(e)}")
                # The cursor context manager will automatically rollback on exception
                raise

    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"❌ Extended user creation failed for '{email}': {str(e)}")
        return {
            'success': False,
            'error': 'User creation failed'
        }


def create_user(email: str, password: str) -> dict:
    """
    Create a new user with email and password
    Returns: dict with 'success', 'error', 'id', 'username', 'email' keys
    """
    try:
        if not email or not password:
            return {
                'success': False,
                'error': 'Email and password are required'
            }

        # Validate email format
        import re
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, email):
            return {
                'success': False,
                'error': 'Please enter a valid email address'
            }

        # Validate password length
        if len(password) < 6:
            return {
                'success': False,
                'error': 'Password must be at least 6 characters'
            }

        email = email.strip().lower()

        # Generate username from email (part before @)
        username = email.split('@')[0]

        # Check if email already exists
        with db_manager.db.get_cursor() as cursor:
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                return {
                    'success': False,
                    'error': 'Email already exists'
                }

            # Check if generated username exists, if so append numbers
            base_username = username
            counter = 1
            while True:
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                if not cursor.fetchone():
                    break
                username = f"{base_username}{counter}"
                counter += 1

            # Hash password and create user
            password_hash = hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, created_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (username, email, password_hash))

            user_id = cursor.lastrowid
            from utils.logger import app_logger
            app_logger.info(f"✅ User created successfully: {email} -> {username} (ID: {user_id})")

            return {
                'success': True,
                'id': user_id,
                'username': username,
                'email': email
            }

    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"❌ User creation failed for '{email}': {str(e)}")
        return {
            'success': False,
            'error': 'User creation failed'
        }

def authenticate_user_by_email(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user with email and password"""
    try:
        from utils.logger import app_logger
        app_logger.debug(f"Authenticating user by email: {email}")

        with db_manager.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT id, username, password_hash, email, last_login
                FROM users WHERE email = ?
            ''', (email.lower(),))

            user = cursor.fetchone()

            if not user:
                app_logger.warning(f"User not found with email: {email}")
                return {'success': False, 'error': 'Invalid email address or password'}

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                app_logger.warning(f"Invalid password for user: {email}")
                return {'success': False, 'error': 'Invalid email address or password'}

            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user[0],))

            app_logger.info(f"User {email} authenticated successfully")

            return {
                'success': True,
                'id': user[0],
                'username': user[1],
            }

    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"Authentication error: {e}")
        return {'success': False, 'error': f'Authentication system error'}


def authenticate_user_by_email(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user by email and password"""
    try:
        with db_manager.db.get_cursor() as cursor:
            cursor.execute('SELECT id, username, password_hash FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                # Update last login
                cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user[0],))
                return {
                    'success': True,
                    'id': user[0],
                    'username': user[1]
                }
            else:
                return {
                    'success': False,
                    'error': 'Invalid email address or password'
                }
    except Exception as e:
        app_logger.error(f"Authentication error: {e}")
        return {
            'success': False,
            'error': 'Authentication failed'
        }

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """Authenticate user with username and password"""
    try:
        from utils.logger import app_logger
        app_logger.debug(f"Authenticating user: {username}")

        with db_manager.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT id, username, password_hash, email, last_login
                FROM users WHERE username = ?
            ''', (username,))

            user = cursor.fetchone()

            if not user:
                app_logger.warning(f"User not found: {username}")
                return {'success': False, 'error': 'Invalid email address or password'}

            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                app_logger.warning(f"Invalid password for user: {username}")
                return {'success': False, 'error': 'Invalid email address or password'}

            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user[0],))

            app_logger.info(f"User {username} authenticated successfully")

            return {
                'success': True,
                'id': user[0],
                'username': user[1],
            }

    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"Authentication error: {e}")
        return {'success': False, 'error': f'Authentication system error'}


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    try:
        from utils.logger import app_logger
        with db_manager.db.get_cursor() as cursor:
            cursor.execute('''
                SELECT id, username, password_hash, email, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))

            user = cursor.fetchone()
            return dict(zip(('id', 'username', 'password_hash', 'email', 'created_at', 'last_login'), user)) if user else None

    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"Get user by ID error: {e}")
        return None


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"Password verification error: {e}")
        return False


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    try:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    except Exception as e:
        from utils.logger import app_logger
        app_logger.error(f"Password hashing error: {e}")
        raise