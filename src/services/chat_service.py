import google.generativeai as genai
from typing import List, AsyncGenerator
import json
import uuid
import asyncio
from core.config import settings
from api.schemas import Message


class ChatService:
    def __init__(self):
        print("[ChatService] Initialized")
        # Configure Gemini with API key
        if settings.GOOGLE_API_KEY:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self.model = genai.GenerativeModel(settings.PRIMARY_MODEL)
            print(f"[ChatService] Using model: {settings.PRIMARY_MODEL}")
        else:
            self.model = None
            print("[ChatService] WARNING: No API key - using mock mode")

    async def stream_chat(self, history: List[Message]) -> AsyncGenerator[str, None]:
        """
        Stream response theo AG-UI Protocol với Gemini API.
        """
        try:
            # Nếu không có API key, dùng mock
            if not self.model:
                async for chunk in self._stream_mock_generator():
                    yield chunk
                return

            print("[ChatService] Calling Gemini API")

            # Convert history cho Gemini
            gemini_history = []
            for msg in history[:-1]:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg.content]})

            last_message = history[-1].content if history else "Hello"

            # Gọi Gemini với streaming
            chat_session = self.model.start_chat(history=gemini_history)
            response = chat_session.send_message(last_message, stream=True)

            message_id = str(uuid.uuid4())

            # AG-UI Protocol Events

            # 1. TextMessageStart
            start_event = {
                "type": "TextMessageStart",
                "messageId": message_id,
                "role": "assistant",
            }
            yield f"EVENT: TextMessageStart\ndata: {json.dumps(start_event)}\n"

            # 2. TextMessageContent - stream từng chunk
            for chunk in response:
                if chunk.text:
                    content_event = {
                        "type": "TextMessageContent",
                        "messageId": message_id,
                        "content": chunk.text,
                    }
                    yield f"EVENT: TextMessageContent\ndata: {json.dumps(content_event)}\n"

            # 3. TextMessageEnd
            end_event = {"type": "TextMessageEnd", "messageId": message_id}
            yield f"EVENT: TextMessageEnd\ndata: {json.dumps(end_event)}\n"

            # 4. RunFinished
            run_finished = {
                "type": "RunFinished",
                "finalState": {"status": "completed"},
            }
            yield f"EVENT: RunFinished\ndata: {json.dumps(run_finished)}\n"

        except Exception as e:
            print(f"ERROR in stream_chat: {str(e)}")
            error_event = {"type": "RunError", "message": str(e)}
            yield f"EVENT: RunError\ndata: {json.dumps(error_event)}\n"

    async def _stream_mock_generator(self) -> AsyncGenerator[str, None]:
        """Mock response khi không có API key"""
        mock_responses = [
            "Xin ",
            "chào! ",
            "Tôi ",
            "là ",
            "AI ",
            "Finance ",
            "Advisor. ",
            "(Đây là mock mode - cần API key để dùng Gemini thật)",
        ]

        message_id = str(uuid.uuid4())

        # 1. TextMessageStart
        start_event = {
            "type": "TextMessageStart",
            "messageId": message_id,
            "role": "assistant",
        }
        yield f"EVENT: TextMessageStart\ndata: {json.dumps(start_event)}\n"
        await asyncio.sleep(0.02)

        # 2. TextMessageContent
        for text in mock_responses:
            content_event = {
                "type": "TextMessageContent",
                "messageId": message_id,
                "content": text,
            }
            yield f"EVENT: TextMessageContent\ndata: {json.dumps(content_event)}\n"
            await asyncio.sleep(0.05)

        # 3. TextMessageEnd
        end_event = {"type": "TextMessageEnd", "messageId": message_id}
        yield f"EVENT: TextMessageEnd\ndata: {json.dumps(end_event)}\n"

        # 4. RunFinished
        run_finished = {
            "type": "RunFinished",
            "finalState": {"status": "completed"},
        }
        yield f"EVENT: RunFinished\ndata: {json.dumps(run_finished)}\n"


chat_service = ChatService()
