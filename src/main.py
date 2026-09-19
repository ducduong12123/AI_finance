import sys
import io

# Fix Windows encoding issue (charmap codec error)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from core.config import settings
from api.schemas import ChatRequest
from services.chat_service import chat_service
from api.routes import conversations
from api.routes import agent
from api.routes import agent_mock

app = FastAPI(title=settings.APP_NAME)

# Cấu hình CORS cho Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - v1 API
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(agent_mock.router, prefix="/api/v1")  # Mock endpoints cho Agent 3

# Legacy routes (non-v1) for backward compatibility
app.include_router(conversations.router, prefix="/api", tags=["conversations-legacy"])
app.include_router(agent.router, prefix="/api", tags=["agent-legacy"])
app.include_router(agent_mock.router, prefix="/api", tags=["agent-mock-legacy"])


@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.APP_NAME}", "status": "online"}


@app.get("/health")
async def health():
    """Health check used by the Railway deploy config (railway.json)."""
    return {"status": "ok"}


@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """
    Endpoint xử lý chat từ Frontend.
    """
    # Log raw body để debug
    print(f"\n=== DEBUG RAW REQUEST ===")

    try:
        # Parse JSON từ request
        body_json = await request.json()
        print(f"Keys: {body_json.keys()}")
        print(f"Messages type: {type(body_json.get('messages'))}")

        if "messages" in body_json:
            for i, msg in enumerate(body_json["messages"]):
                print(
                    f"Message {i}: role={msg.get('role')}, content={msg.get('content')[:50] if msg.get('content') else 'None'}..."
                )

        # Validate với Pydantic
        chat_request = ChatRequest(**body_json)
        print(f"Validated messages count: {len(chat_request.messages)}")

    except Exception as e:
        print(f"Error parsing/validating request: {str(e)}")
        import traceback

        traceback.print_exc()
        return StreamingResponse(
            iter([f"Error: {str(e)}"]), media_type="text/event-stream"
        )

    return StreamingResponse(
        chat_service.stream_chat(chat_request.messages),
        media_type="text/plain",  # Vercel AI SDK protocol
        headers={"x-vercel-ai-data-stream": "v1"},
    )
