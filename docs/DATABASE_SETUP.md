# Database Migration and Setup Guide

This guide explains how to set up the Supabase database for the AI Finance Assistant multi-agent system.

## Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Supabase Project**: Create a new project or use an existing one
3. **API Credentials**: Get your `SUPABASE_URL` and `SUPABASE_KEY` from Project Settings > API

## Database Schema

The database consists of 5 main tables:

### 1. `agent_sessions`
Stores active agent sessions with state information.

```sql
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL UNIQUE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    stage TEXT NOT NULL DEFAULT 'idle',
    status TEXT NOT NULL DEFAULT 'active',
    context JSONB DEFAULT '{}',
    memory JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_agent_sessions_user_id ON agent_sessions(user_id);
CREATE INDEX idx_agent_sessions_session_id ON agent_sessions(session_id);
CREATE INDEX idx_agent_sessions_status ON agent_sessions(status);
```

### 2. `agent_query_history`
Stores history of all queries and their results.

```sql
CREATE TABLE IF NOT EXISTS agent_query_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    query_type TEXT DEFAULT 'mixed',
    final_answer TEXT,
    plan JSONB,
    tool_results JSONB DEFAULT '[]',
    critic_reviews JSONB DEFAULT '[]',
    iterations INTEGER DEFAULT 0,
    execution_time FLOAT DEFAULT 0,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    tokens_used INTEGER,
    model_used TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_query_history_session_id ON agent_query_history(session_id);
CREATE INDEX idx_query_history_user_id ON agent_query_history(user_id);
CREATE INDEX idx_query_history_created_at ON agent_query_history(created_at);
```

### 3. `tool_executions`
Records individual tool executions for debugging and analytics.

```sql
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT NOT NULL REFERENCES agent_sessions(session_id) ON DELETE CASCADE,
    query_history_id UUID REFERENCES agent_query_history(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_params JSONB NOT NULL DEFAULT '{}',
    tool_result JSONB,
    execution_time FLOAT DEFAULT 0,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX idx_tool_executions_query_history ON tool_executions(query_history_id);
```

### 4. `user_profiles`
Extended user profile information (extends Supabase auth.users).

```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT,
    preferences JSONB DEFAULT '{}',
    default_stocks JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);
```

### 5. `rate_limits`
Tracks API usage for rate limiting.

```sql
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT,
    ip_address INET,
    endpoint TEXT NOT NULL,
    requests_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_rate_limits_user_id ON rate_limits(user_id);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);
```

## Setup Instructions

### Method 1: Using Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **Table Editor**
3. Click **New Table** and create each table manually
4. Add indexes as specified above

### Method 2: Using SQL Editor

1. Go to **SQL Editor** in Supabase dashboard
2. Run the SQL scripts from `src/data/models/agent_models.py`
3. The `SQL_SCHEMA` constant contains all necessary DDL statements

### Method 3: Using Supabase CLI

```bash
# Install Supabase CLI if not already installed
npm install -g supabase

# Link your project
supabase link --project-ref <your-project-ref>

# Create migration
supabase migration new create_agent_tables

# Edit the generated migration file with the SQL schema

# Apply migration
supabase db push
```

## Environment Configuration

Add these environment variables to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-anon-key-or-service-role-key>
```

**Note**: 
- Use `anon` key for client-side operations
- Use `service_role` key for server-side operations (bypasses RLS)

## Row Level Security (RLS)

Enable RLS on all tables:

```sql
-- Enable RLS
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_query_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;

-- RLS Policies for agent_sessions
CREATE POLICY "Users can view own sessions" 
    ON agent_sessions FOR SELECT 
    USING (user_id = auth.uid() OR user_id IS NULL);

CREATE POLICY "Users can update own sessions" 
    ON agent_sessions FOR UPDATE 
    USING (user_id = auth.uid());

-- RLS Policies for agent_query_history
CREATE POLICY "Users can view own queries" 
    ON agent_query_history FOR SELECT 
    USING (user_id = auth.uid() OR user_id IS NULL);

-- RLS Policies for user_profiles
CREATE POLICY "Users can view own profile" 
    ON user_profiles FOR SELECT 
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile" 
    ON user_profiles FOR UPDATE 
    USING (id = auth.uid());
```

## Testing the Connection

Create a test script:

```python
# test_db_connection.py
import asyncio
from data.adapters.supabase_client import SupabaseClient, get_supabase_client

async def test_connection():
    # Check if configured
    print(f"Supabase configured: {SupabaseClient.is_configured()}")
    
    # Get client
    client = get_supabase_client()
    if client:
        # Test query
        result = client.table("agent_sessions").select("count").execute()
        print(f"Connection successful! Result: {result}")
    else:
        print("Failed to connect to Supabase")

if __name__ == "__main__":
    asyncio.run(test_connection())
```

Run the test:
```bash
python test_db_connection.py
```

## Troubleshooting

### Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
- Check if the URL includes `https://`
- Ensure you're using the correct key (anon vs service_role)

### Permission Denied
- Check RLS policies are configured correctly
- For server-side operations, use the service_role key
- For client-side operations, ensure user is authenticated

### Table Not Found
- Run the migration SQL to create tables
- Check if you're connected to the correct project
- Verify table names match exactly (case-sensitive)

## Backup and Restore

### Export Data
```bash
supabase db dump --data-only > backup.sql
```

### Import Data
```bash
psql <your-database-url> < backup.sql
```

## Maintenance

### Cleanup Old Sessions
The system automatically cleans up sessions older than 24 hours. You can also run manual cleanup:

```sql
-- Delete sessions older than 30 days
DELETE FROM agent_sessions 
WHERE updated_at < NOW() - INTERVAL '30 days';
```

### Monitor Disk Usage
Check table sizes in Supabase dashboard under **Database > Usage**.

## Next Steps

After database setup:
1. ✅ Database layer complete
2. ⏳ Integrate with AgentLoop for query persistence
3. ⏳ Add authentication middleware
4. ⏳ Implement rate limiting

## Support

For issues:
- Supabase Docs: https://supabase.com/docs
- Database Service: `src/services/agent_db_service.py`
- Models: `src/data/models/agent_models.py`
