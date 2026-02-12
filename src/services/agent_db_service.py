"""
Database service layer for agent-related operations.
Provides CRUD operations for agent sessions, query history, and tool executions.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from data.adapters.supabase_client import get_supabase_client, SupabaseClient
from data.models.agent_models import (
    AgentSession,
    AgentQueryHistory,
    ToolExecution,
    AgentStage,
    SessionStatus,
    QueryType,
)


class AgentDatabaseService:
    """
    Service layer for agent database operations.
    Handles all CRUD operations for agent-related tables.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ==================== Agent Session Operations ====================

    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentSession]:
        """Create a new agent session."""
        client = self._get_client()
        if not client:
            return None

        try:
            session = AgentSession(
                session_id=session_id,
                user_id=user_id,
                stage=AgentStage.IDLE,
                status=SessionStatus.ACTIVE,
                metadata=metadata or {},
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )

            result = (
                client.table("agent_sessions")
                .insert(session.model_dump(exclude={"id"}))
                .execute()
            )

            if result.data:
                return AgentSession(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating session: {e}")
            return None

    async def get_session(self, session_id: str) -> Optional[AgentSession]:
        """Get session by session_id."""
        client = self._get_client()
        if not client:
            return None

        try:
            result = (
                client.table("agent_sessions")
                .select("*")
                .eq("session_id", session_id)
                .single()
                .execute()
            )
            if result.data:
                return AgentSession(**result.data)
            return None
        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    async def update_session(
        self,
        session_id: str,
        stage: Optional[AgentStage] = None,
        status: Optional[SessionStatus] = None,
        context: Optional[Dict[str, Any]] = None,
        memory: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentSession]:
        """Update session fields."""
        client = self._get_client()
        if not client:
            return None

        try:
            update_data = {"updated_at": datetime.utcnow().isoformat()}
            if stage:
                update_data["stage"] = stage.value
            if status:
                update_data["status"] = status.value
            if context is not None:
                update_data["context"] = context
            if memory is not None:
                update_data["memory"] = memory

            result = (
                client.table("agent_sessions")
                .update(update_data)
                .eq("session_id", session_id)
                .execute()
            )

            if result.data:
                return AgentSession(**result.data[0])
            return None
        except Exception as e:
            print(f"Error updating session: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data."""
        client = self._get_client()
        if not client:
            return False

        try:
            client.table("agent_sessions").delete().eq(
                "session_id", session_id
            ).execute()
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

    async def get_user_sessions(
        self, user_id: str, limit: int = 50
    ) -> List[AgentSession]:
        """Get all sessions for a user."""
        client = self._get_client()
        if not client:
            return []

        try:
            result = (
                client.table("agent_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [AgentSession(**data) for data in result.data]
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

    # ==================== Query History Operations ====================

    async def create_query_record(
        self, session_id: str, query: str, user_id: Optional[str] = None
    ) -> Optional[AgentQueryHistory]:
        """Create a new query history record."""
        client = self._get_client()
        if not client:
            return None

        try:
            record = AgentQueryHistory(
                session_id=session_id, user_id=user_id, query=query
            )

            result = (
                client.table("agent_query_history")
                .insert(record.model_dump(exclude={"id"}))
                .execute()
            )

            if result.data:
                return AgentQueryHistory(**result.data[0])
            return None
        except Exception as e:
            print(f"Error creating query record: {e}")
            return None

    async def update_query_result(
        self,
        record_id: str,
        final_answer: str,
        success: bool,
        plan: Optional[Dict[str, Any]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        critic_reviews: Optional[List[Dict[str, Any]]] = None,
        iterations: int = 0,
        execution_time: float = 0,
        tokens_used: Optional[int] = None,
        model_used: Optional[str] = None,
        query_type: Optional[QueryType] = None,
    ) -> Optional[AgentQueryHistory]:
        """Update query record with results."""
        client = self._get_client()
        if not client:
            return None

        try:
            update_data = {
                "final_answer": final_answer,
                "success": success,
                "iterations": iterations,
                "execution_time": execution_time,
                "completed_at": datetime.utcnow().isoformat(),
            }

            if plan:
                update_data["plan"] = plan
            if tool_results:
                update_data["tool_results"] = tool_results
            if critic_reviews:
                update_data["critic_reviews"] = critic_reviews
            if tokens_used is not None:
                update_data["tokens_used"] = tokens_used
            if model_used:
                update_data["model_used"] = model_used
            if query_type:
                update_data["query_type"] = query_type.value

            result = (
                client.table("agent_query_history")
                .update(update_data)
                .eq("id", record_id)
                .execute()
            )

            if result.data:
                return AgentQueryHistory(**result.data[0])
            return None
        except Exception as e:
            print(f"Error updating query result: {e}")
            return None

    async def get_query_history(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AgentQueryHistory]:
        """Get query history with optional filters."""
        client = self._get_client()
        if not client:
            return []

        try:
            query = client.table("agent_query_history").select("*")

            if session_id:
                query = query.eq("session_id", session_id)
            if user_id:
                query = query.eq("user_id", user_id)

            result = (
                query.order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return [AgentQueryHistory(**data) for data in result.data]
        except Exception as e:
            print(f"Error getting query history: {e}")
            return []

    # ==================== Tool Execution Operations ====================

    async def record_tool_execution(
        self,
        session_id: str,
        tool_name: str,
        tool_params: Dict[str, Any],
        tool_result: Optional[Dict[str, Any]] = None,
        execution_time: float = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        query_history_id: Optional[str] = None,
    ) -> Optional[ToolExecution]:
        """Record a tool execution."""
        client = self._get_client()
        if not client:
            return None

        try:
            execution = ToolExecution(
                session_id=session_id,
                query_history_id=query_history_id,
                tool_name=tool_name,
                tool_params=tool_params,
                tool_result=tool_result,
                execution_time=execution_time,
                success=success,
                error_message=error_message,
            )

            result = (
                client.table("tool_executions")
                .insert(execution.model_dump(exclude={"id"}))
                .execute()
            )

            if result.data:
                return ToolExecution(**result.data[0])
            return None
        except Exception as e:
            print(f"Error recording tool execution: {e}")
            return None

    async def get_tool_executions(
        self,
        session_id: Optional[str] = None,
        query_history_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[ToolExecution]:
        """Get tool execution history."""
        client = self._get_client()
        if not client:
            return []

        try:
            query = client.table("tool_executions").select("*")

            if session_id:
                query = query.eq("session_id", session_id)
            if query_history_id:
                query = query.eq("query_history_id", query_history_id)
            if tool_name:
                query = query.eq("tool_name", tool_name)

            result = query.order("created_at", desc=True).limit(limit).execute()
            return [ToolExecution(**data) for data in result.data]
        except Exception as e:
            print(f"Error getting tool executions: {e}")
            return []

    # ==================== Analytics Operations ====================

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        client = self._get_client()
        if not client:
            return {}

        try:
            # Get query count
            queries_result = (
                client.table("agent_query_history")
                .select("id", count="exact")
                .eq("session_id", session_id)
                .execute()
            )
            query_count = queries_result.count

            # Get tool execution count
            tools_result = (
                client.table("tool_executions")
                .select("id", count="exact")
                .eq("session_id", session_id)
                .execute()
            )
            tool_count = tools_result.count

            # Get average execution time
            avg_time_result = (
                client.table("agent_query_history")
                .select("execution_time")
                .eq("session_id", session_id)
                .execute()
            )
            avg_time = 0
            if avg_time_result.data:
                times = [
                    r.get("execution_time", 0)
                    for r in avg_time_result.data
                    if r.get("execution_time")
                ]
                if times:
                    avg_time = sum(times) / len(times)

            # Get success rate
            success_result = (
                client.table("agent_query_history")
                .select("success")
                .eq("session_id", session_id)
                .execute()
            )
            success_count = sum(1 for r in success_result.data if r.get("success"))
            total = len(success_result.data)
            success_rate = (success_count / total * 100) if total > 0 else 0

            return {
                "session_id": session_id,
                "total_queries": query_count,
                "total_tool_executions": tool_count,
                "average_execution_time": round(avg_time, 2),
                "success_rate": round(success_rate, 1),
                "queries": query_count,
                "success": success_count,
                "failed": total - success_count,
            }
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return {}

    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up data older than specified days."""
        client = self._get_client()
        if not client:
            return {}

        try:
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Delete old query history
            queries_deleted = (
                client.table("agent_query_history")
                .delete()
                .lt("created_at", cutoff)
                .execute()
            )

            # Delete old tool executions
            tools_deleted = (
                client.table("tool_executions")
                .delete()
                .lt("created_at", cutoff)
                .execute()
            )

            # Delete old sessions
            sessions_deleted = (
                client.table("agent_sessions")
                .delete()
                .lt("updated_at", cutoff)
                .execute()
            )

            return {
                "queries_deleted": len(queries_deleted.data)
                if queries_deleted.data
                else 0,
                "tools_deleted": len(tools_deleted.data) if tools_deleted.data else 0,
                "sessions_deleted": len(sessions_deleted.data)
                if sessions_deleted.data
                else 0,
            }
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            return {}


# Global service instance
agent_db_service = AgentDatabaseService()
