from typing import Optional
from constants import MAX_MESSAGE_LENGTH

class ValidationError(Exception):
    """Custom validation error"""
    pass

def validate_message(message: str) -> str:
    """Validate user message input"""
    if not message:
        raise ValidationError("Message cannot be empty")

    if not isinstance(message, str):
        raise ValidationError("Message must be a string")

    message = message.strip()
    if len(message) == 0:
        raise ValidationError("Message cannot be empty")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters")

    return message

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format"""
    if not session_id or not isinstance(session_id, str) or len(session_id.strip()) == 0:
        raise ValidationError("Invalid session ID format")
    return True

def validate_feedback_type(feedback_type: str) -> str:
    """Validate feedback type"""
    valid_types = ['like', 'dislike']
    if feedback_type not in valid_types:
        raise ValidationError(f"Invalid feedback type. Must be one of: {valid_types}")

    return feedback_type