"""
Conversation Routes Module
"""
from flask import request, jsonify, session
from typing import Tuple, Dict, Any
from utils.logger import app_logger


class ConversationRoutes:
    """Conversation management route handlers"""

    def register_routes(self, app):
        """Register conversation routes with Flask app"""
        app.route('/api/conversations', methods=['GET'], endpoint='get_conversations')(self.handle_get_conversations)
        app.route('/api/conversations', methods=['POST'], endpoint='create_conversation')(self.handle_create_conversation)
        app.route('/api/conversations/<conversation_id>', methods=['GET'], endpoint='get_conversation')(self.handle_get_conversation)
        app.route('/api/conversations/<conversation_id>', methods=['DELETE'], endpoint='delete_conversation')(self.handle_delete_conversation)

    def handle_get_conversations(self) -> Tuple[Dict[str, Any], int]:
        """Get all conversations for current user"""
        try:
            user_id = session.get('user', {}).get('id')
            if not user_id:
                app_logger.info("No user ID in session, returning empty conversations")
                return jsonify([]), 200

            app_logger.info(f"Getting conversations for user ID: {user_id}")
            from database import get_user_conversations
            conversations = get_user_conversations(user_id)

            if not isinstance(conversations, list):
                app_logger.error(f"get_user_conversations returned invalid type: {type(conversations)}")
                return jsonify([]), 200

            app_logger.info(f"Retrieved {len(conversations)} conversations")
            return jsonify(conversations), 200
        except Exception as e:
            app_logger.error(f"Error getting conversations: {e}")
            return jsonify([]), 200

    def handle_create_conversation(self) -> Tuple[Dict[str, Any], int]:
        """Create a new conversation"""
        try:
            user_id = session.get('user', {}).get('id')
            if not user_id:
                return jsonify({'error': 'User not logged in'}), 401

            from database import get_user_conversations
            existing_conversations = get_user_conversations(user_id)
            if len(existing_conversations) >= 2:
                return jsonify({'error': 'Conversation limit reached. Delete an existing conversation to create a new one.'}), 400

            data = request.get_json()
            title = data.get('title', 'New Conversation')

            from database import create_conversation
            conversation_id = create_conversation(user_id, title)

            return jsonify({
                'id': conversation_id,
                'title': title,
                'created_at': 'now'
            }), 201

        except Exception as e:
            app_logger.error(f"Conversation creation error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_get_conversation(self, conversation_id: str) -> Tuple[Dict[str, Any], int]:
        """Get specific conversation with messages"""
        try:
            user_id = session.get('user', {}).get('id')
            if not user_id:
                return jsonify({'error': 'User not logged in'}), 401

            from database import get_conversation_with_messages
            conversation = get_conversation_with_messages(conversation_id, user_id)

            if not conversation:
                return jsonify({'error': 'Conversation not found'}), 404

            return jsonify(conversation), 200

        except Exception as e:
            app_logger.error(f"Conversation retrieval error: {e}")
            return jsonify({'error': str(e)}), 500

    def handle_delete_conversation(self, conversation_id: str) -> Tuple[Dict[str, Any], int]:
        """Delete a specific conversation"""
        try:
            user_id = session.get('user', {}).get('id')
            if not user_id:
                return jsonify({'error': 'User not logged in'}), 401

            from database import delete_conversation
            success = delete_conversation(conversation_id, user_id)

            if success:
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'error': 'Conversation not found or access denied'}), 404

        except Exception as e:
            app_logger.error(f"Conversation deletion error: {e}")
            return jsonify({'error': str(e)}), 500

# Create route handler instance
conversation_route_handler = ConversationRoutes()