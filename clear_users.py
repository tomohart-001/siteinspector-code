
#!/usr/bin/env python3
"""
Script to remove all existing users from the database and clear sessions
"""

import sqlite3
import os
import glob
from utils.logger import app_logger

def clear_all_users_and_sessions():
    """Remove all users, related data, and clear Flask sessions"""
    try:
        # Connect to the database
        conn = sqlite3.connect('engineroom.db')
        cursor = conn.cursor()
        
        # Get count of users before deletion
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_profiles')
        profile_count = cursor.fetchone()[0]
        
        if user_count == 0:
            print("No users found in database.")
        else:
            print(f"Found {user_count} users and {profile_count} profiles to delete.")
            
            # Confirm deletion
            confirm = input("Are you sure you want to delete ALL users and clear sessions? (type 'YES' to confirm): ")
            if confirm != 'YES':
                print("Operation cancelled.")
                return
            
            # Delete user profiles first (due to foreign key constraint)
            cursor.execute('DELETE FROM user_profiles')
            deleted_profiles = cursor.rowcount
            
            # Delete users
            cursor.execute('DELETE FROM users')
            deleted_users = cursor.rowcount
            
            # Delete team invitations (if any exist)
            cursor.execute('DELETE FROM team_invitations WHERE invited_by_user_id IS NOT NULL')
            deleted_invitations = cursor.rowcount
            
            # Delete teams (if table exists)
            try:
                cursor.execute('DELETE FROM teams')
                deleted_teams = cursor.rowcount
            except sqlite3.OperationalError:
                deleted_teams = 0  # Table doesn't exist
            
            # Delete conversations
            cursor.execute('DELETE FROM conversations WHERE user_id IS NOT NULL')
            deleted_conversations = cursor.rowcount
            
            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("users", "user_profiles", "teams", "conversations", "team_invitations")')
            
            # Commit changes
            conn.commit()
            
            print(f"✅ Successfully deleted:")
            print(f"   - {deleted_users} users")
            print(f"   - {deleted_profiles} user profiles")
            print(f"   - {deleted_conversations} user conversations")
            print(f"   - {deleted_invitations} team invitations")
            print(f"   - {deleted_teams} teams")
            print("   - Reset auto-increment counters")
            
            app_logger.info(f"Database cleared: {deleted_users} users, {deleted_profiles} profiles removed")
        
        # Clear Flask session files (if any exist)
        session_files_cleared = 0
        try:
            # Look for Flask session files in common locations
            session_patterns = [
                'flask_session/*',
                'instance/sessions/*',
                'sessions/*',
                'tmp/sessions/*'
            ]
            
            for pattern in session_patterns:
                session_files = glob.glob(pattern)
                for session_file in session_files:
                    try:
                        os.remove(session_file)
                        session_files_cleared += 1
                    except OSError:
                        pass
            
            if session_files_cleared > 0:
                print(f"   - {session_files_cleared} session files cleared")
            
        except Exception as e:
            print(f"Note: Could not clear session files: {e}")
        
        # Clear any uploaded profile pictures
        profile_pics_cleared = 0
        try:
            profile_pic_path = 'static/uploads/profile_pictures/*'
            profile_pics = glob.glob(profile_pic_path)
            for pic in profile_pics:
                try:
                    os.remove(pic)
                    profile_pics_cleared += 1
                except OSError:
                    pass
            
            if profile_pics_cleared > 0:
                print(f"   - {profile_pics_cleared} profile pictures cleared")
                
        except Exception as e:
            print(f"Note: Could not clear profile pictures: {e}")
        
        print("\n🔄 Restart the application to clear active sessions completely.")
        print("   Users will need to log in again after restart.")
        print("\n💡 If users still appear logged in:")
        print("   - Clear browser cookies/cache")
        print("   - Try incognito/private browsing mode")
        print("   - Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)")
        
    except Exception as e:
        print(f"❌ Error clearing users: {e}")
        app_logger.error(f"Failed to clear users: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    clear_all_users_and_sessions()
