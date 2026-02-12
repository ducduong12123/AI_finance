import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from data.adapters.supabase_client import get_supabase_client, SupabaseClient
from data.models.agent_models import AgentStage


class AgentState(BaseModel):
    """In-memory state representation (for backward compatibility)."""

    session_id: str
    stage: AgentStage = AgentStage.IDLE
    context: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    memory: Dict[str, Any] = Field(default_factory=dict)


class StateManager:
    """
    Manages the persistence and retrieval of AgentState.
    Uses Supabase for persistence with in-memory caching.
    """

    def __init__(self):
        self._cache: Dict[str, AgentState] = {}
        self._client = None
        self._table_name = "agent_sessions"

    def _get_client(self):
        """Lazy load Supabase client."""
        if self._client is None and SupabaseClient.is_configured():
            self._client = get_supabase_client()
        return self._client

    async def get_state(self, session_id: str) -> AgentState:
        """
        Retrieves state for a session.
        Checks cache first, then database.
        """
        # Check cache first
        if session_id in self._cache:
            return self._cache[session_id]

        # Try to load from database
        client = self._get_client()
        if client:
            try:
                result = (
                    client.table(self._table_name)
                    .select("*")
                    .eq("session_id", session_id)
                    .single()
                    .execute()
                )

                if result.data:
                    # Convert DB record to AgentState
                    data = result.data
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0]
                    if isinstance(data, dict):
                        state = AgentState(
                            session_id=str(data.get("session_id", session_id)),
                            stage=AgentStage(str(data.get("stage", "idle"))),
                            context=dict(data.get("context", {})),
                            memory=dict(data.get("memory", {})),
                            last_updated=datetime.datetime.fromisoformat(
                                str(
                                    data.get(
                                        "updated_at",
                                        datetime.datetime.utcnow().isoformat(),
                                    )
                                )
                            ),
                        )
                        self._cache[session_id] = state
                        return state
            except Exception as e:
                # Log error but don't fail - return new state
                print(f"Error loading state from DB: {e}")

        # Return new state if not found
        state = AgentState(session_id=session_id)
        self._cache[session_id] = state
        return state

    async def update_state(self, session_id: str, **kwargs) -> AgentState:
        """
        Updates specific fields of the state.
        Updates both cache and database.
        """
        state = await self.get_state(session_id)

        # Update state fields
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.last_updated = datetime.datetime.utcnow()

        # Update cache
        self._cache[session_id] = state

        # Persist to database if configured
        client = self._get_client()
        if client:
            try:
                db_data = {
                    "session_id": state.session_id,
                    "stage": state.stage.value,
                    "context": state.context,
                    "memory": state.memory,
                    "updated_at": state.last_updated.isoformat(),
                }

                # Upsert: insert if not exists, update if exists
                result = (
                    client.table(self._table_name)
                    .upsert(db_data, on_conflict="session_id")
                    .execute()
                )
            except Exception as e:
                # Log error but don't fail - cache is still updated
                print(f"Error saving state to DB: {e}")

        return state

    async def clear_state(self, session_id: str):
        """Resets the state for a session."""
        if session_id in self._cache:
            del self._cache[session_id]

        # Also clear from database
        client = self._get_client()
        if client:
            try:
                client.table(self._table_name).delete().eq(
                    "session_id", session_id
                ).execute()
            except Exception as e:
                print(f"Error clearing state from DB: {e}")

    async def update_stage(self, session_id: str, stage: AgentStage):
        """Convenience method to update just the stage."""
        return await self.update_state(session_id, stage=stage)

    async def add_to_memory(self, session_id: str, key: str, value: Any):
        """Add a key-value pair to session memory."""
        state = await self.get_state(session_id)
        state.memory[key] = value
        return await self.update_state(session_id, memory=state.memory)

    async def get_from_memory(self, session_id: str, key: str, default=None):
        """Get a value from session memory."""
        state = await self.get_state(session_id)
        return state.memory.get(key, default)

    async def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """
        Remove expired sessions from cache and database.
        Can be run periodically as a background task.
        """
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=max_age_hours)

        # Clear from cache
        expired_sessions = [
            sid for sid, state in self._cache.items() if state.last_updated < cutoff
        ]
        for sid in expired_sessions:
            del self._cache[sid]

        # Clear from database
        client = self._get_client()
        if client:
            try:
                client.table(self._table_name).delete().lt(
                    "updated_at", cutoff.isoformat()
                ).execute()
            except Exception as e:
                print(f"Error cleaning up expired sessions: {e}")

        return len(expired_sessions)


# Global state manager instance
state_manager = StateManager()
