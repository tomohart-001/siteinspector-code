
"""
Timezone Helper Utilities
Handles timezone conversion and formatting for user display
"""
import pytz
from datetime import datetime, timezone
from typing import Optional, Union
from flask import request, session


class TimezoneHelper:
    """Helper class for timezone operations"""
    
    DEFAULT_TIMEZONE = 'Pacific/Auckland'  # New Zealand timezone
    
    @staticmethod
    def get_user_timezone() -> str:
        """Get user's timezone from session, request headers, or default"""
        # Try to get from session first
        if 'user_timezone' in session:
            return session['user_timezone']
        
        # Try to get from browser/request headers
        # This would typically come from JavaScript detection
        user_tz = request.headers.get('X-User-Timezone')
        if user_tz:
            try:
                # Validate timezone
                pytz.timezone(user_tz)
                session['user_timezone'] = user_tz
                return user_tz
            except pytz.UnknownTimeZoneError:
                pass
        
        # Default to New Zealand timezone
        return TimezoneHelper.DEFAULT_TIMEZONE
    
    @staticmethod
    def set_user_timezone(timezone_name: str) -> bool:
        """Set user's timezone in session"""
        try:
            # Validate timezone
            pytz.timezone(timezone_name)
            session['user_timezone'] = timezone_name
            return True
        except pytz.UnknownTimeZoneError:
            return False
    
    @staticmethod
    def convert_to_user_timezone(dt: Union[datetime, str], user_tz: Optional[str] = None) -> datetime:
        """Convert datetime to user's timezone"""
        if isinstance(dt, str):
            # Parse string datetime
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return None
        
        if dt is None:
            return None
        
        if user_tz is None:
            user_tz = TimezoneHelper.get_user_timezone()
        
        # Ensure datetime is timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        # Convert to user timezone
        user_timezone = pytz.timezone(user_tz)
        return dt.astimezone(user_timezone)
    
    @staticmethod
    def format_for_display(dt: Union[datetime, str], format_str: str = '%b %d at %I:%M %p', user_tz: Optional[str] = None) -> str:
        """Format datetime for display in user's timezone"""
        if dt is None:
            return "Unknown"
        
        # Convert to user timezone
        user_dt = TimezoneHelper.convert_to_user_timezone(dt, user_tz)
        
        if user_dt is None:
            return "Invalid date"
        
        return user_dt.strftime(format_str)
    
    @staticmethod
    def get_relative_time(dt: Union[datetime, str], user_tz: Optional[str] = None) -> str:
        """Get relative time string (e.g., '2 hours ago')"""
        if dt is None:
            return "Unknown"
        
        user_dt = TimezoneHelper.convert_to_user_timezone(dt, user_tz)
        if user_dt is None:
            return "Invalid date"
        
        now = datetime.now(pytz.timezone(user_tz or TimezoneHelper.get_user_timezone()))
        diff = now - user_dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @staticmethod
    def get_available_timezones() -> list:
        """Get list of common timezones"""
        return [
            'Pacific/Auckland',
            'Pacific/Chatham',
            'Australia/Sydney',
            'Australia/Melbourne',
            'Australia/Brisbane',
            'Asia/Tokyo',
            'Asia/Singapore',
            'Europe/London',
            'Europe/Paris',
            'America/New_York',
            'America/Los_Angeles',
            'America/Chicago',
            'UTC'
        ]
