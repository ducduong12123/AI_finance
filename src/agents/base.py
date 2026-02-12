import google.generativeai as genai
from typing import List, Any, Dict, Optional
from core.config import settings
from api.schemas import Message


class BaseAgent:
    """
    Base class for all Agents in the system.
    Handles LLM interaction, system prompts, and history.
    """

    def __init__(
        self,
        system_prompt: str,
        model_name: str = settings.PRIMARY_MODEL,
        tools: List[Any] = None,
    ):
        self.system_prompt = system_prompt
        self.model_name = model_name
        self.tools = tools
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
            tools=self.tools,
        )
        self.chat_session = None

    def start_session(self, history: List[Message] = None):
        """Initializes or resumes a chat session."""
        gemini_history = []
        if history:
            for msg in history:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})

        self.chat_session = self.model.start_chat(history=gemini_history)

    async def generate_response(self, prompt: str, tools: List[Any] = None):
        """Generates a response from the LLM."""
        if not self.chat_session:
            self.start_session()

        # Note: In a real implementation, we would pass tools to the GenerativeModel constructor
        # or use the tool_config for function calling.
        response = self.chat_session.send_message(prompt, stream=True)
        return response
