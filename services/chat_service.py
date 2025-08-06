
"""
ChatService - Core chat processing logic
Refactored with better error handling and performance
"""
import asyncio
import time
from typing import Tuple, Generator, List, Dict, Any
from .base_service import BaseService


class ChatService(BaseService):
    """Service for processing chat messages and managing AI interactions"""

    def __init__(self, enable_streaming: bool = True):
        super().__init__("ChatService")
        self.enable_streaming = enable_streaming
        self.word_delay = 0.01  # From constants

    async def process_message(self, user_message: str, session_id: str, conversation_id: str = None, agent_type: str = None) -> Tuple[str, str]:
        """Process user message and generate AI response"""
        try:
            agent_info = f"Agent: {agent_type}" if agent_type else "Default agent"
            self._log_operation("Processing message", f"Session {session_id[:8]}, {agent_info}")

            # Save user message
            from database import save_message, get_conversation_history
            save_message(session_id, 'user', user_message, conversation_id)

            # Get conversation context
            conversation_history = self._get_conversation_context(session_id)

            # Generate AI response
            response_text = await self._generate_ai_response(conversation_history, agent_type)

            # Save AI response
            assistant_message_id = save_message(session_id, 'assistant', response_text, conversation_id)

            self._log_operation("Response generated", f"{len(response_text)} characters")
            return response_text, assistant_message_id

        except Exception as e:
            return self._handle_error("process_message", e)

    def _get_conversation_context(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve and format conversation history for AI processing"""
        from database import get_conversation_history
        
        history = get_conversation_history(session_id)
        self._log_operation("History retrieved", f"{len(history)} messages")

        return [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in history
        ]

    async def _generate_ai_response(self, conversation_context: List[Dict[str, str]], agent_type: str = None) -> str:
        """Generate AI response using orchestrator agent"""
        if agent_type == 'ADAM':
            self._log_operation("AI generation", "Invoking ADAM agent")
        else:
            self._log_operation("AI generation", "Invoking orchestrator agent")

        from agents import Runner
        from agent_definitions import orchestrator_agent

        # Add ADAM context if specified
        if agent_type == 'ADAM':
            system_message = {
                "role": "system", 
                "content": "You are ADAM (Automated Design, Analysis and Modelling), an AI assistant specializing in engineering, structural design, and construction analysis. Provide expert guidance on structural engineering, building codes, design calculations, and project analysis."
            }
            conversation_context = [system_message] + conversation_context

        result = await Runner.run(
            starting_agent=orchestrator_agent,
            input=conversation_context
        )

        return result.final_output

    def generate_streaming_response(self, response_text: str, message_id: str) -> Generator[str, None, None]:
        """Generate streaming response for real-time display"""
        try:
            words = response_text.split()

            for i, word in enumerate(words):
                escaped_word = self._escape_json_content(word)

                if i < len(words) - 1:
                    escaped_word += " "

                yield f'data: {{"delta": "{escaped_word}"}}\n\n'
                time.sleep(self.word_delay)

            yield 'data: {"done": true}\n\n'

        except Exception as e:
            escaped_error = self._escape_json_content(str(e))
            yield f'data: {{"error": "{escaped_error}"}}\n\n'

    def _escape_json_content(self, content: str) -> str:
        """Escape content for safe JSON transmission"""
        return (content
                .replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace('\n', '\\n')
                .replace('\r', '\\r'))
