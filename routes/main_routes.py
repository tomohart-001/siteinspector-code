"""
Core Application Routes Module - Streamlined
"""
from flask import Flask, request, jsonify, render_template, session
from typing import Tuple, Dict, Any
import asyncio
from datetime import datetime

from auth import get_session_id
from database import DatabaseManager
from services import ChatService, response_service
from database import MessageRepository
from utils.validators import validate_message, validate_session_id, ValidationError
from utils.logger import app_logger
from utils.error_handler import ErrorHandler, ErrorCategories


class MainRoutes:
    """Core application routes handler - streamlined for essential functionality"""

    def __init__(self):
        self.chat_service = ChatService(enable_streaming=True)
        self.db_manager = DatabaseManager()

    def register_routes(self, app: Flask) -> None:
        """Register core application routes"""

        # Core functionality routes only
        app.route('/dashboard', methods=['GET'])(self.handle_dashboard)
        app.route('/chat', methods=['POST'])(self.handle_chat)
        app.route('/api/chat', methods=['POST'])(self.handle_chat)
        app.route('/reset', methods=['POST'])(self.handle_reset_session)
        app.route('/history', methods=['GET'])(self.handle_get_history)
        app.route('/conversations', methods=['GET'])(self.handle_get_conversations)




    def handle_dashboard(self):
        """Handle dashboard page"""
        user_info = session.get('user')
        if not user_info:
            from flask import redirect, url_for
            return redirect(url_for('login'))

        # Get user profile to include account type
        try:
            with self.db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT u.username, u.email, p.account_type
                    FROM users u
                    LEFT JOIN user_profiles p ON u.id = p.user_id
                    WHERE u.id = ?
                ''', (user_info['id'],))

                user_data = cursor.fetchone()
                if user_data:
                    user_info.update({
                        'username': user_data[0],
                        'email': user_data[1],
                        'account_type': user_data[2] or 'individual'
                    })
        except Exception as e:
            app_logger.error(f"Failed to get user profile for dashboard: {e}")

        app_logger.info(f"Dashboard accessed by user: {user_info.get('username', 'Unknown')}")
        return render_template('dashboard.html', user=user_info)

    def handle_chat(self) -> Tuple[Any, int]:
        """Process chat messages with comprehensive error handling"""
        try:
            # Validate request
            if not request.is_json:
                return response_service.validation_error("Content-Type must be application/json")

            data = request.json
            user_message = data.get('message')
            conversation_id = data.get('conversation_id')

            if not user_message:
                return response_service.validation_error("No message provided", "message")

            # Validate and process
            user_message = validate_message(user_message)
            session_id = get_session_id()
            validate_session_id(session_id)

            app_logger.info(f"Processing chat message for session {session_id[:8]}")

            # Get agent type from request
            agent_type = data.get('agent')
            
            # Generate AI response
            response_text, message_id = asyncio.run(
                self.chat_service.process_message(user_message, session_id, conversation_id, agent_type)
            )

            # Save user message
            MessageRepository.save_message(session_id, 'user', user_message, conversation_id)

            # Return appropriate response
            if self.chat_service.enable_streaming:
                def generate_streaming_response():
                    if conversation_id:
                        yield f'data: {{"conversation_id": "{conversation_id}"}}\n\n'

                    for chunk in self.chat_service.generate_streaming_response(response_text, message_id):
                        yield chunk

                return app.response_class(
                    generate_streaming_response(),
                    mimetype='text/plain'
                )
            else:
                return response_service.success({
                    'response': response_text,
                    'message_id': message_id,
                    'conversation_id': conversation_id
                })

        except ValidationError as e:
            app_logger.warning(f"Validation error: {e}")
            return response_service.validation_error(str(e))
        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.UNKNOWN,
                context={'operation': 'chat_processing'}
            ), 500

    def handle_reset_session(self) -> Tuple[Dict[str, Any], int]:
        """Reset user session with proper cleanup"""
        try:
            session_id = get_session_id()
            app_logger.info(f"Resetting session {session_id[:8]}")

            cleared_count = MessageRepository.clear_session_history(session_id)
            session.clear()

            app_logger.info(f"Session reset completed - cleared {cleared_count} messages")
            return response_service.success({
                'messages_cleared': cleared_count
            }, "Session reset successfully")

        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.DATABASE,
                context={'operation': 'session_reset'}
            ), 500

    def handle_get_history(self) -> Tuple[Dict[str, Any], int]:
        """Retrieve conversation history for current session"""
        try:
            session_id = get_session_id()
            history = MessageRepository.get_conversation_history(session_id)
            return response_service.success({'history': history})

        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.DATABASE,
                context={'operation': 'history_retrieval'}
            ), 500

    def handle_get_conversations(self) -> Tuple[Dict[str, Any], int]:
        """Get conversations for current user"""
        try:
            # For now, return empty conversations list
            return response_service.success({'conversations': []})
        except Exception as e:
            return ErrorHandler.handle_error(
                e,
                category=ErrorCategories.DATABASE,
                context={'operation': 'get_conversations'}
            ), 500


def main_route_handler():
    """Legacy route handler function for compatibility"""
    return MainRoutes()