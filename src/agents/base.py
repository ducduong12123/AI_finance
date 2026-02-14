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
        self.total_tokens = 0
        self.input_tokens = 0
        self.output_tokens = 0

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

        response = self.chat_session.send_message(prompt, stream=True)
        return response

    async def generate_content_async(self, prompt: str) -> Any:
        """Helper for non-streaming calls that tracks tokens."""
        response = await self.model.generate_content_async(prompt)
        self._update_tokens(response.usage_metadata)
        return response

    def _update_tokens(self, usage):
        """Updates token counts from usage metadata."""
        if usage:
            self.input_tokens += usage.prompt_token_count
            self.output_tokens += usage.candidates_token_count
            self.total_tokens += usage.total_token_count

    def get_token_usage(self) -> Dict[str, int]:
        """Returns and resets token usage."""
        usage = {
            "input": self.input_tokens,
            "output": self.output_tokens,
            "total": self.total_tokens,
        }
        # Optionally reset if needed, but for now we keep accumulating
        return usage
