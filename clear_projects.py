
#!/usr/bin/env python3
"""
Script to remove all projects from the database
"""

import sqlite3
from utils.logger import app_logger

def clear_all_projects():
    """Remove all projects and related data from the database"""
    try:
        # Connect to the database
        conn = sqlite3.connect('engineroom.db')
        cursor = conn.cursor()
        
        # Get count of projects before deletion
        cursor.execute('SELECT COUNT(*) FROM projects')
        project_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM project_history')
        history_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM project_snapshots')
        snapshot_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM project_comments')
        comment_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM project_notes')
        note_count = cursor.fetchone()[0]
        
        if project_count == 0:
            print("No projects found in database.")
        else:
            print(f"Found data to delete:")
            print(f"  - {project_count} projects")
            print(f"  - {history_count} project history entries")
            print(f"  - {snapshot_count} project snapshots")
            print(f"  - {comment_count} project comments")
            print(f"  - {note_count} project notes")
            
            # Confirm deletion
            confirm = input("\nAre you sure you want to delete ALL projects and related data? (type 'YES' to confirm): ")
            if confirm != 'YES':
                print("Operation cancelled.")
                return
            
            # Delete related data first (foreign key constraints)
            cursor.execute('DELETE FROM project_notes')
            deleted_notes = cursor.rowcount
            
            cursor.execute('DELETE FROM project_comments')
            deleted_comments = cursor.rowcount
            
            cursor.execute('DELETE FROM project_snapshots')
            deleted_snapshots = cursor.rowcount
            
            cursor.execute('DELETE FROM project_history')
            deleted_history = cursor.rowcount
            
            # Delete projects last
            cursor.execute('DELETE FROM projects')
            deleted_projects = cursor.rowcount
            
            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("projects", "project_history", "project_snapshots", "project_comments", "project_notes")')
            
            # Commit changes
            conn.commit()
            
            print(f"\n✅ Successfully deleted:")
            print(f"   - {deleted_projects} projects")
            print(f"   - {deleted_history} project history entries")
            print(f"   - {deleted_snapshots} project snapshots")
            print(f"   - {deleted_comments} project comments")
            print(f"   - {deleted_notes} project notes")
            print("   - Reset auto-increment counters")
            
            app_logger.info(f"Database cleared: {deleted_projects} projects and all related data removed")
        
    except Exception as e:
        print(f"❌ Error clearing projects: {e}")
        app_logger.error(f"Failed to clear projects: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clear_all_projects()
