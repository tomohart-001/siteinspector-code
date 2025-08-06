"""
Database Layer - Centralized database operations
"""
import sqlite3
import threading
import time
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from utils.logger import app_logger
from config import Config
from datetime import datetime


class DatabaseError(Exception):
    """Custom database exception"""
    pass


class DatabaseConnection:
    """Thread-safe database connection manager"""

    def __init__(self, db_path: str = 'engineroom.db'):
        self.db_path = db_path
        self._local = threading.local()

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Set pragmas for better performance and data integrity
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")  # Back to NORMAL for better performance
            self._local.connection.execute("PRAGMA cache_size=10000")
            self._local.connection.execute("PRAGMA temp_store=memory")
            self._local.connection.execute("PRAGMA foreign_keys=ON")
            self._local.connection.execute("PRAGMA busy_timeout=30000")
            self._local.connection.execute("PRAGMA wal_autocheckpoint=1000")  # Less frequent checkpoints
            self._local.connection.execute("PRAGMA read_uncommitted=true")  # Allow dirty reads for better concurrency
        return self._local.connection

    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            app_logger.error(f"Database operation failed: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            cursor.close()


class DatabaseManager:
    """Database operations manager"""

    def __init__(self):
        self.db = DatabaseConnection()
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Ensure all required tables exist"""
        try:
            with self.db.get_cursor() as cursor:
                # Core tables
                self._create_users_table(cursor)
                self._create_user_profiles_table(cursor)
                self._create_conversations_table(cursor)
                self._create_messages_table(cursor)
                self._create_projects_table(cursor)
                self._create_project_history_table(cursor)
                self._create_project_snapshots_table(cursor)
                self._create_team_invitations_table(cursor)
                self._create_project_comments_table(cursor)
                self._create_project_notes_table(cursor)

                # Create indexes
                self._create_indexes(cursor)

            app_logger.info("Database tables initialized successfully")
        except Exception as e:
            app_logger.error(f"Database initialization failed: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}")

    def _create_users_table(self, cursor):
        """Create users table with migrations"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')

        # Add role column if it doesn't exist (migration)
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'role' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "member"')
            cursor.execute('UPDATE users SET role = "admin" WHERE id = 1')

    def _create_user_profiles_table(self, cursor):
        """Create user profiles table with migrations"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                profile_picture TEXT,
                account_type TEXT DEFAULT 'individual',
                subscribe_to_updates BOOLEAN DEFAULT FALSE,
                team_id INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE SET NULL
            )
        ''')

        # Migrations for new columns
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'account_type' not in columns:
            cursor.execute('ALTER TABLE user_profiles ADD COLUMN account_type TEXT DEFAULT "individual"')
        if 'subscribe_to_updates' not in columns:
            cursor.execute('ALTER TABLE user_profiles ADD COLUMN subscribe_to_updates BOOLEAN DEFAULT FALSE')
        if 'team_id' not in columns:
            cursor.execute('ALTER TABLE user_profiles ADD COLUMN team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL')

    def _create_conversations_table(self, cursor):
        """Create conversations table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                session_id TEXT,
                title TEXT NOT NULL,
                location TEXT,
                preview TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    def _create_messages_table(self, cursor):
        """Create messages table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                conversation_id TEXT
            )
        ''')

    def _create_projects_table(self, cursor):
        """Create projects table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                project_number TEXT,
                client_name TEXT,
                address TEXT NOT NULL,
                site_information TEXT,
                project_type TEXT DEFAULT 'building',
                project_units TEXT DEFAULT 'metric',
                project_visibility TEXT DEFAULT 'private',
                team_members TEXT,
                location_lat REAL,
                location_lng REAL,
                created_at TEXT,
                updated_at TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Add location columns if they don't exist (migration)
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'location_lat' not in columns:
            cursor.execute('ALTER TABLE projects ADD COLUMN location_lat REAL')
        if 'location_lng' not in columns:
            cursor.execute('ALTER TABLE projects ADD COLUMN location_lng REAL')

    def _create_project_history_table(self, cursor):
        """Create project history table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Create project_snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                snapshot_type TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Add missing columns to existing projects table
        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN project_number TEXT")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN client_name TEXT")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN project_type TEXT DEFAULT 'building'")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN project_units TEXT DEFAULT 'metric'")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN project_visibility TEXT DEFAULT 'private'")
        except:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE projects ADD COLUMN team_members TEXT")
        except:
            pass  # Column already exists

    def _create_project_snapshots_table(self, cursor):
        """Create project snapshots table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER,
                snapshot_type TEXT NOT NULL,
                snapshot_data TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
                UNIQUE(project_id, snapshot_type)
            )
        ''')

    def _create_team_invitations_table(self, cursor):
        """Create team invitations table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                invited_by_user_id INTEGER NOT NULL,
                invitation_token TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (invited_by_user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        # Migration for invitation_token
        cursor.execute("SELECT COUNT(*) FROM pragma_table_info('team_invitations') WHERE name='invitation_token'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('ALTER TABLE team_invitations ADD COLUMN invitation_token TEXT')

    def _create_project_comments_table(self, cursor):
        """Create project comments table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

    def _create_project_notes_table(self, cursor):
        """Create project notes table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                note_type TEXT DEFAULT 'general',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

    def _create_indexes(self, cursor):
        """Create database indexes for performance"""
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)',
            'CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)',
            'CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_team_invitations_token ON team_invitations(invitation_token)',
            'CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_project_history_project_id ON project_history(project_id)',
            'CREATE INDEX IF NOT EXISTS idx_project_snapshots_project_id ON project_snapshots(project_id)',
            'CREATE INDEX IF NOT EXISTS idx_project_comments_project_id ON project_comments(project_id)',
            'CREATE INDEX IF NOT EXISTS idx_project_notes_project_id ON project_notes(project_id)'
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

    # User management methods
    def update_user_role(self, user_id: int, new_role: str) -> bool:
        """Update user role"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            app_logger.error(f"Failed to update user role: {e}")
            return False

    def make_user_admin(self, user_id: int) -> bool:
        """Make a user an admin"""
        return self.update_user_role(user_id, 'admin')

    def get_username_by_id(self, user_id: int) -> Optional[str]:
        """Get username by user ID"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            app_logger.error(f"Error getting username by ID: {e}")
            return None

    # Project management methods
    def save_project(self, project_data: Dict[str, Any]) -> Optional[int]:
        """Save a new project to the database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO projects (
                        user_id, name, project_number, client_name, address, site_information, 
                        project_type, project_units, project_visibility, team_members, 
                        location_lat, location_lng,
                        created_at, updated_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_data['user_id'],
                    project_data['name'],
                    project_data.get('project_number', ''),
                    project_data.get('client_name', ''),
                    project_data['address'],
                    project_data.get('site_information', ''),
                    project_data.get('project_type', 'building'),
                    project_data.get('project_units', 'metric'),
                    project_data.get('project_visibility', 'private'),
                    project_data.get('team_members', ''),
                    project_data.get('location_lat'),
                    project_data.get('location_lng'),
                    datetime.utcnow(),
                    datetime.utcnow(),
                    project_data.get('status', 'active')
                ))

                project_id = cursor.lastrowid
                if project_id:
                    self.add_project_history_event(
                        project_id=project_id,
                        user_id=project_data['user_id'],
                        event_type='created',
                        description="Project created"
                    )

                app_logger.info(f"Project saved successfully with ID: {project_id}")
                return project_id

        except Exception as e:
            app_logger.error(f"Error saving project: {e}")
            return None

    def delete_project(self, project_id, user_id):
        """Delete a project and all related data"""
        try:
            # Use a separate connection for deletion to avoid conflicts
            conn = sqlite3.connect(self.db.db_path, timeout=30.0)
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")

            try:
                cursor = conn.cursor()

                # Verify project exists and belongs to user before deletion
                cursor.execute('SELECT id FROM projects WHERE id = ? AND user_id = ?', (project_id, user_id))
                if not cursor.fetchone():
                    app_logger.warning(f"Project {project_id} not found or doesn't belong to user {user_id}")
                    return False

                # Since foreign keys are enabled with CASCADE, deleting the project will automatically delete related records
                cursor.execute('DELETE FROM projects WHERE id = ? AND user_id = ?', (project_id, user_id))
                project_deleted = cursor.rowcount

                if project_deleted > 0:
                    conn.commit()
                    app_logger.info(f"Project {project_id} and all related data deleted successfully")

                    # Force WAL checkpoint after commit
                    cursor.execute('PRAGMA wal_checkpoint(FULL)')

                    # Verify deletion
                    cursor.execute('SELECT COUNT(*) FROM projects WHERE id = ?', (project_id,))
                    remaining_count = cursor.fetchone()[0]

                    if remaining_count > 0:
                        app_logger.error(f"Project {project_id} still exists after deletion")
                        return False

                    return True
                else:
                    app_logger.warning(f"No project deleted for ID {project_id}")
                    return False

            finally:
                conn.close()

        except Exception as e:
            app_logger.error(f"Error deleting project {project_id}: {e}")
            return False

    def get_user_projects(self, user_id):
        """Get all projects for a user"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                with self.db.get_cursor() as cursor:
                    cursor.execute('''
                        SELECT id, name, project_number, client_name, address, site_information, 
                               project_type, project_units, project_visibility, team_members,
                               location_lat, location_lng, status, 
                               created_at, updated_at
                        FROM projects 
                        WHERE user_id = ? AND status = 'active'
                        ORDER BY updated_at DESC
                    ''', (user_id,))

                    rows = cursor.fetchall()
                    projects = []

                    for row in rows:
                        projects.append({
                            'id': row[0],
                            'name': row[1],
                            'project_number': row[2],
                            'client_name': row[3],
                            'address': row[4],
                            'site_information': row[5],
                            'project_type': row[6],
                            'project_units': row[7],
                            'project_visibility': row[8],
                            'team_members': row[9],
                            'location_lat': row[10],
                            'location_lng': row[11],
                            'status': row[12],
                            'created': row[13],
                            'modified': row[14],
                            'owner': self.get_username_by_id(user_id) or 'Unknown',
                            'type': 'my'
                        })

                    app_logger.info(f"Retrieved {len(projects)} active projects for user {user_id}")
                    return projects

            except DatabaseError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    app_logger.error(f"Error getting user projects after {max_retries} retries: {e}")
                    return []
                else:
                    app_logger.warning(f"Database locked, retrying ({retry_count}/{max_retries})")
                    import time
                    time.sleep(0.1 * retry_count)  # Exponential backoff
            except Exception as e:
                app_logger.error(f"Error getting user projects: {e}")
                return []

        return []

    def get_project_by_id(self, project_id: int, user_id: int):
        """Get a specific project by ID for a user"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT p.*, u.username as owner
                    FROM projects p
                    LEFT JOIN users u ON p.user_id = u.id
                    WHERE p.id = ? AND (p.user_id = ? OR p.project_visibility != 'private')
                ''', (project_id, user_id))

                row = cursor.fetchone()
                if row:
                    # Convert row to dict for easier access
                    columns = [description[0] for description in cursor.description]
                    project = dict(zip(columns, row))

                    # Convert datetime strings to datetime objects
                    from datetime import datetime
                    if project.get('created_at'):
                        try:
                            if isinstance(project['created_at'], str):
                                # Handle various datetime string formats
                                date_str = project['created_at']
                                if 'T' in date_str:
                                    # ISO format
                                    project['created_at'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    # SQLite datetime format - try multiple patterns
                                    try:
                                        project['created_at'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        try:
                                            project['created_at'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                                        except ValueError:
                                            project['created_at'] = datetime.fromisoformat(date_str)
                            elif not isinstance(project['created_at'], datetime):
                                # If it's not a string or datetime, try to convert it
                                project['created_at'] = datetime.fromisoformat(str(project['created_at']))
                        except Exception as e:
                            app_logger.warning(f"Failed to parse created_at: {project['created_at']}, error: {e}")
                            project['created_at'] = datetime.now()  # Use current time as fallback

                    if project.get('updated_at'):
                        try:
                            if isinstance(project['updated_at'], str):
                                # Handle various datetime string formats
                                date_str = project['updated_at']
                                if 'T' in date_str:
                                    # ISO format
                                    project['updated_at'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    # SQLite datetime format - try multiple patterns
                                    try:
                                        project['updated_at'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        try:
                                            project['updated_at'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                                        except ValueError:
                                            project['updated_at'] = datetime.fromisoformat(date_str)
                            elif not isinstance(project['updated_at'], datetime):
                                # If it's not a string or datetime, try to convert it
                                project['updated_at'] = datetime.fromisoformat(str(project['updated_at']))
                        except Exception as e:
                            app_logger.warning(f"Failed to parse updated_at: {project['updated_at']}, error: {e}")
                            project['updated_at'] = datetime.now()  # Use current time as fallback

                    return project
                return None
        except Exception as e:
            app_logger.error(f"Error getting project by ID: {e}")
            return None

    def get_project_team_members(self, project_id: int) -> list:
        """Get team members for a specific project"""
        try:
            with self.db.get_cursor() as cursor:
                # Get project owner's team members
                cursor.execute('''
                    SELECT p.user_id FROM projects p WHERE p.id = ?
                ''', (project_id,))

                project_result = cursor.fetchone()
                if not project_result:
                    return []

                project_owner_id = project_result[0]

                # Get team members from owner's team
                cursor.execute('''
                    SELECT u.id, u.username, u.email, up.first_name, up.last_name, 
                           up.profile_picture, u.role
                    FROM users u
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE up.team_id = (
                        SELECT team_id FROM user_profiles WHERE user_id = ?
                    ) AND u.id != ?
                    ORDER BY u.username ASC
                ''', (project_owner_id, project_owner_id))

                members = cursor.fetchall()
                team_members = []

                for member in members:
                    profile_picture = member[5]
                    if profile_picture and not profile_picture.startswith('uploads/'):
                        profile_picture = f"uploads/profile_pictures/{profile_picture}"

                    display_name = f"{member[3]} {member[4] or ''}".strip() if member[3] else member[1]

                    team_members.append({
                        'id': member[0],
                        'username': member[1],
                        'email': member[2] or f"{member[1]}@engineroom.com",
                        'display_name': display_name,
                        'profile_picture': profile_picture,
                        'role': member[6] or 'member'
                    })

                return team_members

        except Exception as e:
            app_logger.error(f"Failed to get project team members: {e}")
            return []

    def get_project_comments(self, project_id: int) -> list:
        """Get project comments from the database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT pc.id, pc.user_id, pc.comment, pc.created_at, 
                           COALESCE(up.first_name || ' ' || up.last_name, u.username) as display_name
                    FROM project_comments pc
                    JOIN users u ON pc.user_id = u.id
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE pc.project_id = ?
                    ORDER BY pc.created_at DESC
                ''', (project_id,))

                comments = cursor.fetchall()
                comments_list = []
                for comment in comments:
                    created_at = self._parse_datetime(comment[3])

                    comments_list.append({
                        'id': comment[0],
                        'user_id': comment[1],
                        'comment': comment[2],
                        'created_at': created_at,
                        'display_name': comment[4] or 'Unknown User'
                    })
                return comments_list
        except Exception as e:
            app_logger.error(f"Failed to get project comments: {e}")
            return []

    def get_project_notes(self, project_id: int) -> list:
        """Get project notes from the database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT pn.id, pn.user_id, pn.note, pn.created_at, 
                           COALESCE(up.first_name || ' ' || up.last_name, u.username) as display_name
                    FROM project_notes pn
                    JOIN users u ON pn.user_id = u.id
                    LEFT JOIN user_profiles up ON u.id = up.user_id
                    WHERE pn.project_id = ?
                    ORDER BY pn.created_at DESC
                ''', (project_id,))

                notes = cursor.fetchall()
                notes_list = []
                for note in notes:
                    created_at = self._parse_datetime(note[3])

                    notes_list.append({
                        'id': note[0],
                        'user_id': note[1],
                        'note': note[2],
                        'created_at': created_at,
                        'display_name': note[4] or 'Unknown User'
                    })
                return notes_list
        except Exception as e:
            app_logger.error(f"Failed to get project notes: {e}")
            return []

    def add_project_comment(self, project_id: int, user_id: int, comment: str) -> bool:
        """Add a comment to a project"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO project_comments (project_id, user_id, comment)
                    VALUES (?, ?, ?)
                ''', (project_id, user_id, comment))

                # Log this activity in project history
                self.add_project_history_event(
                    project_id=project_id,
                    user_id=user_id,
                    event_type='comment_added',
                    description=f"Added a comment"
                )

                return True
        except Exception as e:
            app_logger.error(f"Error adding project comment: {e}")
            return False

    def add_project_note(self, project_id: int, user_id: int, note: str, note_type: str = 'general') -> bool:
        """Add a note to a project"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO project_notes (project_id, user_id, note, note_type)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, user_id, note, note_type))
                return True
        except Exception as e:
            app_logger.error(f"Error adding project note: {e}")
            return False

    # Project history methods
    def add_project_history_event(self, project_id: int, user_id: int, event_type: str, description: str) -> Optional[int]:
        """Add an event to project history"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO project_history (project_id, user_id, event_type, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (project_id, user_id, event_type, description, datetime.utcnow()))
                return cursor.lastrowid
        except Exception as e:
            app_logger.error(f"Failed to add project history event: {e}")
            return None

    def get_project_history(self, project_id: int) -> List[Dict[str, Any]]:
        """Get project history events"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT ph.id, ph.event_type, ph.description, ph.created_at,
                           users.username, up.first_name, up.last_name
                    FROM project_history ph
                    LEFT JOIN users ON ph.user_id = users.id
                    LEFT JOIN user_profiles up ON users.id = up.user_id
                    WHERE ph.project_id = ?
                    ORDER BY ph.created_at DESC
                    LIMIT 20
                ''', (project_id,))

                events = cursor.fetchall()
                history_list = []

                for event in events:
                    user_name = self._format_user_name(event[5], event[6], event[4])
                    created_at = self._parse_datetime(event[3])

                    history_list.append({
                        'id': event[0],
                        'event_type': event[1],
                        'description': event[2],
                        'created_at': created_at,
                        'user_name': user_name
                    })

                return history_list

        except Exception as e:
            app_logger.error(f"Failed to get project history: {e}")
            return []

    def update_project_settings(self, project_id: int, user_id: int, units: str, visibility: str) -> bool:
        """Update project settings"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('SELECT user_id FROM projects WHERE id = ?', (project_id,))
                result = cursor.fetchone()

                if not result or result[0] != user_id:
                    app_logger.warning(f"User {user_id} attempted to update settings for project {project_id} without permission")
                    return False

                cursor.execute('''
                    UPDATE projects 
                    SET project_units = ?, project_visibility = ?, updated_at = ?
                    WHERE id = ? AND user_id = ?
                ''', (units, visibility, datetime.utcnow(), project_id, user_id))

                return cursor.rowcount > 0
        except Exception as e:
            app_logger.error(f"Failed to update project settings: {e}")
            return False

    # Project snapshot methods
    def save_project_snapshot(self, project_id: int, user_id: int, snapshot_type: str, snapshot_data: str, description: str = None) -> bool:
        """Save or update a project snapshot"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT OR REPLACE INTO project_snapshots 
                    (project_id, user_id, snapshot_type, snapshot_data, description, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (project_id, user_id, snapshot_type, snapshot_data, description, datetime.utcnow()))

                self.add_project_history_event(
                    project_id=project_id,
                    user_id=user_id,
                    event_type='snapshot_saved',
                    description=f"Saved {snapshot_type} snapshot"
                )

                return True
        except Exception as e:
            app_logger.error(f"Failed to save project snapshot: {e}")
            return False

    def get_project_snapshot(self, project_id: int, snapshot_type: str = None) -> Optional[Dict[str, Any]]:
        """Get project snapshot(s)"""
        try:
            with self.db.get_cursor() as cursor:
                # First check if any snapshots exist for this project
                cursor.execute('SELECT COUNT(*) FROM project_snapshots WHERE project_id = ?', (project_id,))
                count = cursor.fetchone()[0]
                app_logger.info(f"Found {count} snapshots for project {project_id}")

                if snapshot_type:
                    query = '''
                        SELECT ps.id, ps.project_id, ps.user_id, ps.snapshot_type, 
                               ps.snapshot_data, ps.description, ps.created_at, ps.updated_at, u.username
                        FROM project_snapshots ps
                        LEFT JOIN users u ON ps.user_id = u.id
                        WHERE ps.project_id = ? AND ps.snapshot_type = ?
                        ORDER BY ps.updated_at DESC
                        LIMIT 1
                    '''
                    cursor.execute(query, (project_id, snapshot_type))
                else:
                    query = '''
                        SELECT ps.id, ps.project_id, ps.user_id, ps.snapshot_type, 
                               ps.snapshot_data, ps.description, ps.created_at, ps.updated_at, u.username
                        FROM project_snapshots ps
                        LEFT JOIN users u ON ps.user_id = u.id
                        WHERE ps.project_id = ?
                        ORDER BY ps.updated_at DESC
                        LIMIT 1
                    '''
                    cursor.execute(query, (project_id,))

                result = cursor.fetchone()
                if result:
                    return {
                        'id': result[0],
                        'project_id': result[1],
                        'user_id': result[2],                        'snapshot_type': result[3],
                        'snapshot_data': result[4],
                        'description': result[5],
                        'created_at': result[6],
                        'updated_at': result[7],
                        'username': result[8] if result[8] else 'Unknown User'
                    }
                return None
        except Exception as e:
            app_logger.error(f"Failed to get project snapshot: {e}")
            return None

    # Utility methods
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string safely"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, datetime):
                return date_str

            # Convert to string if it's not already
            date_str = str(date_str)

            # Try ISO format first
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))

            # Try SQLite format
            try:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    return datetime.fromisoformat(date_str)
        except Exception as e:
            app_logger.warning(f"Failed to parse datetime: {date_str}, error: {e}")
            return None

    def _format_user_name(self, first_name: str, last_name: str, username: str) -> str:
        """Format user display name"""
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif username:
            return username
        return "Unknown User"

    def verify_project_deletion(self, project_id: int) -> Dict[str, int]:
        """Verify that a project and all related data has been completely deleted"""
        try:
            with self.db.get_cursor() as cursor:
                # Force checkpoint to ensure we see all changes
                cursor.execute('PRAGMA wal_checkpoint(FULL)')

                results = {}

                # Check projects table
                cursor.execute('SELECT COUNT(*) FROM projects WHERE id = ?', (project_id,))
                results['projects'] = cursor.fetchone()[0]

                # Check project_history table
                cursor.execute('SELECT COUNT(*) FROM project_history WHERE project_id = ?', (project_id,))
                results['project_history'] = cursor.fetchone()[0]

                # Check project_snapshots table
                cursor.execute('SELECT COUNT(*) FROM project_snapshots WHERE project_id = ?', (project_id,))
                results['project_snapshots'] = cursor.fetchone()[0]

                # Check project_comments table
                cursor.execute('SELECT COUNT(*) FROM project_comments WHERE project_id = ?', (project_id,))
                results['project_comments'] = cursor.fetchone()[0]

                # Check project_notes table
                cursor.execute('SELECT COUNT(*) FROM project_notes WHERE project_id = ?', (project_id,))
                results['project_notes'] = cursor.fetchone()[0]

                total_remaining = sum(results.values())

                app_logger.info(f"Project {project_id} deletion verification: {results} (total remaining: {total_remaining})")
                return results

        except Exception as e:
            app_logger.error(f"Error verifying project deletion: {e}")
            return {}


# Global database manager instance
db_manager = DatabaseManager()


# Module-level convenience functions for backward compatibility
def get_user_conversations(user_id: int) -> List[Dict[str, Any]]:
    """Get all conversations for a user - convenience function"""
    return ConversationRepository.get_user_conversations(user_id)


def create_conversation(user_id: int, title: str, location: Optional[str] = None) -> str:
    """Create a new conversation - convenience function"""
    return ConversationRepository.create_conversation(user_id, title, location)


def get_conversation_with_messages(conversation_id: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get conversation with messages - convenience function"""
    conversation = ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation or conversation.get('user_id') != user_id:
        return None

    # Get messages for this conversation
    messages = MessageRepository.get_conversation_history(conversation_id)
    conversation['messages'] = messages
    return conversation


def delete_conversation(conversation_id: str, user_id: int) -> bool:
    """Delete a conversation - convenience function"""
    # Verify ownership before deletion
    conversation = ConversationRepository.get_conversation_by_id(conversation_id)
    if not conversation or conversation.get('user_id') != user_id:
        return False

    return ConversationRepository.delete_conversation(conversation_id)


def save_message(session_id: str, role: str, content: str, conversation_id: Optional[str] = None) -> str:
    """Save a message - convenience function"""
    return MessageRepository.save_message(session_id, role, content, conversation_id)


def get_conversation_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get conversation history - convenience function"""
    return MessageRepository.get_conversation_history(session_id, limit)


class MessageRepository:
    """Repository for message operations"""

    @staticmethod
    def save_message(session_id: str, role: str, content: str, conversation_id: Optional[str] = None) -> str:
        """Save a message to the database"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO messages (session_id, role, content, conversation_id)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, role, content, conversation_id))

                message_id = str(cursor.lastrowid)
                app_logger.debug(f"Message saved: {message_id}")
                return message_id

        except Exception as e:
            app_logger.error(f"Failed to save message: {e}")
            raise DatabaseError(f"Failed to save message: {e}")

    @staticmethod
    def get_conversation_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT role, content, timestamp, conversation_id
                    FROM messages 
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (session_id, limit))

                messages = [dict(row) for row in cursor.fetchall()]
                messages.reverse()  # Return in chronological order
                return messages

        except Exception as e:
            app_logger.error(f"Failed to get conversation history: {e}")
            return []

    @staticmethod
    def clear_session_history(session_id: str) -> int:
        """Clear all messages for a session"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
                deleted_count = cursor.rowcount
                app_logger.info(f"Cleared {deleted_count} messages for session {session_id[:8]}")
                return deleted_count

        except Exception as e:
            app_logger.error(f"Failed to clear session history: {e}")
            return 0


class UserProfileRepository:
    """Repository for user profile operations"""

    @staticmethod
    def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT u.username, u.email, u.created_at, u.last_login,
                           p.first_name, p.last_name, p.profile_picture, p.account_type, p.subscribe_to_updates, p.team_id, p.updated_at
                    FROM users u
                    LEFT JOIN user_profiles p ON u.id = p.user_id
                    WHERE u.id = ?
                ''', (user_id,))

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            app_logger.error(f"Failed to get user profile: {e}")
            return None

    @staticmethod
    def save_user_profile(user_id: int, profile_data: Dict[str, Any]) -> bool:
        """Save or update user profile information"""
        try:
            with db_manager.db.get_cursor() as cursor:
                # Verify user exists
                cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
                if not cursor.fetchone():
                    app_logger.error(f"User ID {user_id} does not exist")
                    return False

                # Update user table if email is provided
                if 'email' in profile_data:
                    cursor.execute('UPDATE users SET email = ? WHERE id = ?', (profile_data['email'], user_id))

                # Check if profile exists
                cursor.execute('SELECT id FROM user_profiles WHERE user_id = ?', (user_id,))
                profile_exists = cursor.fetchone()

                if profile_exists:
                    cursor.execute('''
                        UPDATE user_profiles 
                        SET first_name = ?, last_name = ?, profile_picture = ?, 
                        account_type = ?, subscribe_to_updates = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    ''', (
                        profile_data.get('first_name'),
                        profile_data.get('last_name'),
                        profile_data.get('profile_picture'),
                        profile_data.get('account_type'),
                        profile_data.get('subscribe_to_updates'),
                        user_id
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO user_profiles (user_id, first_name, last_name, profile_picture, account_type, subscribe_to_updates)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        profile_data.get('first_name'),
                        profile_data.get('last_name'),
                        profile_data.get('profile_picture'),
                        profile_data.get('account_type'),
                        profile_data.get('subscribe_to_updates')
                    ))

                app_logger.info(f"User profile successfully saved for user ID: {user_id}")
                return True

        except Exception as e:
            app_logger.error(f"Failed to save user profile for user ID {user_id}: {e}")
            return False

    @staticmethod
    def update_user_password(user_id: int, new_password_hash: str) -> bool:
        """Update user password"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, user_id))
                app_logger.info(f"Password updated for user ID: {user_id}")
                return True

        except Exception as e:
            app_logger.error(f"Failed to update password: {e}")
            return False


class ConversationRepository:
    """Repository for conversation operations"""

    @staticmethod
    def create_conversation(user_id: int, title: str, location: Optional[str] = None) -> str:
        """Create a new conversation"""
        try:
            conversation_id = f"conv_{int(time.time() * 1000)}"

            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO conversations (id, user_id, title, location)
                    VALUES (?, ?, ?, ?)
                ''', (conversation_id, user_id, title, location))

            app_logger.info(f"Created conversation: {conversation_id}")
            return conversation_id

        except Exception as e:
            app_logger.error(f"Failed to create conversation: {e}")
            raise DatabaseError(f"Failed to create conversation: {e}")

    @staticmethod
    def get_user_conversations(user_id: int) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, title, location, preview, created_at, updated_at
                    FROM conversations 
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                ''', (user_id,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            app_logger.error(f"Failed to get user conversations: {e}")
            return []

    @staticmethod
    def get_conversation_by_id(conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, user_id, title, location, preview, created_at, updated_at
                    FROM conversations
                    WHERE id = ?
                ''', (conversation_id,))

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            app_logger.error(f"Failed to get conversation by ID: {e}")
            return None

    @staticmethod
    def update_conversation(conversation_id: str, title: str, location: Optional[str] = None, preview: Optional[str] = None) -> bool:
        """Update conversation details"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE conversations
                    SET title = ?, location = ?, preview = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (title, location, preview, conversation_id))

                return cursor.rowcount > 0

        except Exception as e:
            app_logger.error(f"Failed to update conversation: {e}")
            return False

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    DELETE FROM conversations
                    WHERE id = ?
                ''', (conversation_id,))

                return cursor.rowcount > 0

        except Exception as e:
            app_logger.error(f"Failed to delete conversation: {e}")
            return False

class TeamRepository:
    """Repository for team operations"""

    @staticmethod
    def create_team(name: str, created_by_user_id: int) -> Optional[int]:
        """Create a new team"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO teams (name, created_by_user_id)
                    VALUES (?, ?)
                ''', (name, created_by_user_id))

                team_id = cursor.lastrowid
                return team_id

        except Exception as e:
            app_logger.error(f"Failed to create team: {e}")
            return None

    @staticmethod
    def get_team_by_id(team_id: int) -> Optional[Dict[str, Any]]:
        """Get a team by ID"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, name, created_by_user_id, created_at
                    FROM teams
                    WHERE id = ?
                ''', (team_id,))

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            app_logger.error(f"Failed to get team by ID: {e}")
            return None

    @staticmethod
    def update_team(team_id: int, name: str) -> bool:
        """Update team details"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE teams
                    SET name = ?
                    WHERE id = ?
                ''', (name, team_id))

                return cursor.rowcount > 0

        except Exception as e:
            app_logger.error(f"Failed to update team: {e}")
            return False

    @staticmethod
    def delete_team(team_id: int) -> bool:
        """Delete a team"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    DELETE FROM teams
                    WHERE id = ?
                ''', (team_id,))

                return cursor.rowcount > 0

        except Exception as e:
            app_logger.error(f"Failed to delete team: {e}")
            return False
class TeamInvitationRepository:
    """Repository for team invitation operations"""

    @staticmethod
    def create_team_invitation(email: str, invited_by_user_id: int, invitation_token: str) -> bool:
        """Create a new team invitation"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO team_invitations (email, invited_by_user_id, invitation_token)
                    VALUES (?, ?, ?)
                ''', (email, invited_by_user_id, invitation_token))

                return True

        except Exception as e:
            app_logger.error(f"Failed to create team invitation: {e}")
            return False

    @staticmethod
    def get_team_invitation_by_token(invitation_token: str) -> Optional[Dict[str, Any]]:
        """Get a team invitation by token"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, email, invited_by_user_id, status, created_at
                    FROM team_invitations
                    WHERE invitation_token = ?
                ''', (invitation_token,))

                row = cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            app_logger.error(f"Failed to get team invitation by token: {e}")
            return None

    @staticmethod
    def update_team_invitation_status(invitation_token: str, status: str) -> bool:
        """Update team invitation status"""
        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    UPDATE team_invitations
                    SET status = ?
                    WHERE invitation_token = ?
                ''', (status, invitation_token))

                return cursor.rowcount > 0

        except Exception as e:
            app_logger.error(f"Failed to update team invitation status: {e}")
            return False