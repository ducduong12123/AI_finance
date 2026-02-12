# API Development Guidelines (Backend → Frontend)

> **Version:** 1.0  
> **Last Updated:** 2026-02-12  
> **Status:** MANDATORY for all backend development

---

## 📋 Mục lục

1. [Nguyên tắc Vàng](#1-nguyên-tắc-vàng)
2. [API Contract-First Development](#2-api-contract-first-development)
3. [Response Format Standards](#3-response-format-standards)
4. [Versioning Strategy](#4-versioning-strategy)
5. [Real-time Communication (SSE)](#5-real-time-communication-sse)
6. [Error Handling](#6-error-handling)
7. [Mock Data & Testing](#7-mock-data--testing)
8. [Documentation Standards](#8-documentation-standards)
9. [Communication Protocol](#9-communication-protocol)
10. [Checklist](#10-checklist)

---

## 1. Nguyên tắc Vàng

### 1.1 Backend là "Source of Truth"

```
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (Bạn)                    FRONTEND (AI khác)        │
│  ├─ Define API Contract    ─────► ├─ Consume API            │
│  ├─ Version Control               ├─ Map to UI              │
│  ├─ Stable Format                 └─ Display to User        │
│  └─ Documentation                                           │
└─────────────────────────────────────────────────────────────┘
```

**Rule:** Backend developer PHẢI định nghĩa contract trước, cung cấp mock data, rồi mới implement. Không để FE đoán mò.

### 1.2 Never Break Contract

- Không đổi field name sau khi FE đã integrate
- Không đổi data type (string → number)
- Không xóa field đang được sử dụng
- Mọi thay đổi phải qua versioning

---

## 2. API Contract-First Development

### 2.1 Trình tự phát triển

**ĐÚNG:**
1. Viết OpenAPI spec (YAML/JSON)
2. Review với FE team
3. Generate mock server
4. FE dev dựa trên mock
5. BE implement theo spec
6. Integration test

**SAI:**
1. BE code ngay
2. FE đoán structure
3. Mismatch → Sửa BE → Sửa FE → Lặp lại

### 2.2 OpenAPI Spec Template

```yaml
# File: docs/api/agent-api.v1.yaml
openapi: 3.0.0
info:
  title: AI Finance Agent API
  version: 1.0.0
  description: |
    Multi-Agent Orchestration API for stock market queries.
    
    **Changelog:**
    - v1.0.0 (2026-02-12): Initial release

paths:
  /api/v1/agent/query:
    post:
      summary: Execute agent query (non-streaming)
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AgentQueryRequest'
            example:
              query: "Giá cổ phiếu VCB hôm nay"
              maxIterations: 3
      responses:
        '200':
          description: Successful execution
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AgentQueryResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/InternalError'

  /api/v1/agent/query/stream:
    post:
      summary: Execute agent query with SSE streaming
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AgentQueryRequest'
      responses:
        '200':
          description: SSE Stream of agent events
          content:
            text/event-stream:
              schema:
                $ref: '#/components/schemas/AgentEventStream'

components:
  schemas:
    # ============================================
    # REQUEST SCHEMAS
    # ============================================
    AgentQueryRequest:
      type: object
      required: [query]
      properties:
        query:
          type: string
          minLength: 1
          description: User's natural language query
          example: "Giá cổ phiếu VCB hôm nay"
        sessionId:
          type: string
          format: uuid
          description: Optional session ID for persistence
        maxIterations:
          type: integer
          minimum: 1
          maximum: 5
          default: 3
          description: Maximum agent iterations allowed

    # ============================================
    # RESPONSE SCHEMAS
    # ============================================
    AgentQueryResponse:
      type: object
      required: [success, query, answer, iterations, executionTime, meta]
      properties:
        success:
          type: boolean
          description: Whether execution succeeded
        query:
          type: string
          description: Original query
        answer:
          type: string
          description: Final synthesized answer from agent
        iterations:
          type: integer
          description: Number of iterations executed
        executionTime:
          type: number
          format: float
          description: Total execution time in seconds
        planSummary:
          $ref: '#/components/schemas/PlanSummary'
        toolExecutions:
          type: array
          items:
            $ref: '#/components/schemas/ToolExecution'
        criticReviews:
          type: array
          items:
            $ref: '#/components/schemas/CriticReview'
        meta:
          $ref: '#/components/schemas/ResponseMeta'

    PlanSummary:
      type: object
      properties:
        intent:
          type: string
          description: AI's interpretation of user intent
        toolsPlanned:
          type: array
          items:
            type: string
          example: ["tavily_web_search", "vnstock_get_quote"]
        canParallel:
          type: boolean
          description: Whether tools can run in parallel

    ToolExecution:
      type: object
      properties:
        tool:
          type: string
          description: Tool name
        success:
          type: boolean
        executionTime:
          type: number
          format: float
          description: Time in seconds

    CriticReview:
      type: object
      properties:
        approved:
          type: boolean
        score:
          type: number
          minimum: 0
          maximum: 10
        reasoning:
          type: string
        concerns:
          type: array
          items:
            type: string
        suggestions:
          type: array
          items:
            type: string
        requiresChanges:
          type: boolean
        iterationFeedback:
          type: string
          nullable: true

    ResponseMeta:
      type: object
      required: [requestId, timestamp, duration, version]
      properties:
        requestId:
          type: string
          format: uuid
          description: Unique request ID for tracing
        timestamp:
          type: string
          format: date-time
          description: Response timestamp (ISO 8601)
        duration:
          type: integer
          description: Processing time in milliseconds
        version:
          type: string
          description: API version
          example: "v1"

    # ============================================
    # SSE STREAM SCHEMAS
    # ============================================
    AgentEventStream:
      oneOf:
        - $ref: '#/components/schemas/AgentStartEvent'
        - $ref: '#/components/schemas/AgentPlanCreatedEvent'
        - $ref: '#/components/schemas/AgentToolExecutingEvent'
        - $ref: '#/components/schemas/AgentToolCompletedEvent'
        - $ref: '#/components/schemas/AgentCriticReviewedEvent'
        - $ref: '#/components/schemas/AgentSynthesizingEvent'
        - $ref: '#/components/schemas/AgentFinalResultEvent'
        - $ref: '#/components/schemas/AgentErrorEvent'
      discriminator:
        propertyName: eventType
        mapping:
          START: '#/components/schemas/AgentStartEvent'
          PLAN_CREATED: '#/components/schemas/AgentPlanCreatedEvent'
          TOOL_EXECUTING: '#/components/schemas/AgentToolExecutingEvent'
          TOOL_COMPLETED: '#/components/schemas/AgentToolCompletedEvent'
          CRITIC_REVIEWED: '#/components/schemas/AgentCriticReviewedEvent'
          SYNTHESIZING: '#/components/schemas/AgentSynthesizingEvent'
          FINAL_RESULT: '#/components/schemas/AgentFinalResultEvent'
          ERROR: '#/components/schemas/AgentErrorEvent'

    # Base Event (all events extend this)
    AgentEventBase:
      type: object
      required: [eventType, metadata, progress]
      properties:
        eventType:
          type: string
          enum: [START, PLAN_CREATED, TOOL_EXECUTING, TOOL_COMPLETED, 
                 CRITIC_REVIEWED, SYNTHESIZING, FINAL_RESULT, ERROR]
        metadata:
          type: object
          required: [iteration, timestamp, executionTime]
          properties:
            iteration:
              type: integer
              description: Current iteration number
            timestamp:
              type: string
              format: date-time
            executionTime:
              type: number
              description: Total execution time so far (ms)
        progress:
          type: object
          required: [currentStep, totalSteps, percentComplete]
          properties:
            currentStep:
              type: integer
              description: Current step number
            totalSteps:
              type: integer
              description: Total steps in workflow
            percentComplete:
              type: integer
              minimum: 0
              maximum: 100
              description: Progress percentage

    AgentStartEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [START]
            payload:
              type: object
              required: [query]
              properties:
                query:
                  type: string

    AgentPlanCreatedEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [PLAN_CREATED]
            payload:
              type: object
              required: [plan]
              properties:
                plan:
                  $ref: '#/components/schemas/OrchestratorPlan'

    OrchestratorPlan:
      type: object
      required: [originalQuery, interpretedIntent, tools, canParallel, expectedOutcome]
      properties:
        originalQuery:
          type: string
        interpretedIntent:
          type: string
        tools:
          type: array
          items:
            $ref: '#/components/schemas/ToolPlan'
        canParallel:
          type: boolean
        expectedOutcome:
          type: string

    ToolPlan:
      type: object
      required: [toolName, parameters, reason, priority]
      properties:
        toolName:
          type: string
        parameters:
          type: object
          additionalProperties: true
        reason:
          type: string
        priority:
          type: integer
          minimum: 1
          maximum: 10

    AgentToolExecutingEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [TOOL_EXECUTING]
            payload:
              type: object
              required: [toolName, parameters]
              properties:
                toolName:
                  type: string
                parameters:
                  type: object

    AgentToolCompletedEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [TOOL_COMPLETED]
            payload:
              type: object
              required: [toolName, success, executionTime]
              properties:
                toolName:
                  type: string
                success:
                  type: boolean
                executionTime:
                  type: number
                result:
                  type: string

    AgentCriticReviewedEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [CRITIC_REVIEWED]
            payload:
              $ref: '#/components/schemas/CriticReview'

    AgentSynthesizingEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [SYNTHESIZING]
            payload:
              type: object
              properties:
                message:
                  type: string

    AgentFinalResultEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [FINAL_RESULT]
            payload:
              $ref: '#/components/schemas/AgentQueryResponse'

    AgentErrorEvent:
      allOf:
        - $ref: '#/components/schemas/AgentEventBase'
        - type: object
          properties:
            eventType:
              type: string
              enum: [ERROR]
            payload:
              type: object
              required: [code, message]
              properties:
                code:
                  type: string
                message:
                  type: string
                details:
                  type: object

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
          example:
            success: false
            error:
              code: INVALID_QUERY
              message: "Query cannot be empty"
            meta:
              requestId: "550e8400-e29b-41d4-a716-446655440000"
              timestamp: "2026-02-12T07:20:36.104Z"
              duration: 12
              version: "v1"

    InternalError:
      description: Server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'

  schemas:
    ErrorResponse:
      type: object
      required: [success, error, meta]
      properties:
        success:
          type: boolean
          enum: [false]
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: object
        meta:
          $ref: '#/components/schemas/ResponseMeta'
```

### 2.3 Validation trong FastAPI

```python
# File: src/api/schemas/agent.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class ResponseMeta(BaseModel):
    """Metadata cho mọi API response."""
    request_id: str = Field(..., description="UUID for tracing")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration: int = Field(..., description="Processing time in ms")
    version: str = Field(default="v1")


class AgentQueryRequest(BaseModel):
    """Request schema được validate tự động bởi FastAPI."""
    query: str = Field(..., min_length=1, description="User query")
    session_id: Optional[str] = Field(None, description="Optional session UUID")
    max_iterations: int = Field(default=3, ge=1, le=5)


class CriticReview(BaseModel):
    """Critic review data."""
    approved: bool
    score: float = Field(..., ge=0, le=10)
    reasoning: str
    concerns: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    requires_changes: bool = False
    iteration_feedback: Optional[str] = None


class AgentEvent(BaseModel):
    """Base class cho tất cả SSE events."""
    event_type: Literal[
        "START", "PLAN_CREATED", "TOOL_EXECUTING", "TOOL_COMPLETED",
        "CRITIC_REVIEWED", "SYNTHESIZING", "FINAL_RESULT", "ERROR"
    ]
    metadata: Dict[str, Any]
    progress: Dict[str, int]  # currentStep, totalSteps, percentComplete
```

---

## 3. Response Format Standards

### 3.1 Mọi Response PHẢI có cùng structure

```typescript
// Không bao giờ thay đổi format này!
interface ApiResponse<T> {
  success: boolean;              // Luôn có
  data?: T;                      // Payload (chỉ khi success=true)
  error?: {                      // Chỉ khi success=false
    code: string;                // Machine-readable error code
    message: string;             // Human-readable message
    details?: any;               // Debug info (dev mode only)
  };
  meta: {                        // Luôn có
    requestId: string;           // UUID
    timestamp: string;           // ISO 8601
    duration: number;            // ms
    version: string;             // API version
  };
}
```

### 3.2 Naming Convention

**Dùng camelCase cho JSON (để FE JavaScript dễ dùng):**

```python
# Python (snake_case)
class ToolResult(BaseModel):
    tool_name: str
    execution_time: float

# → JSON Response (camelCase)
{
  "toolName": "tavily_web_search",    # ✅ Đúng
  "executionTime": 1.234
}

# Không dùng:
{
  "tool_name": "...",                  # ❌ FE khó xài
  "tool": "...",                       # ❌ Không rõ nghĩa
}
```

**Cấu hình Pydantic để auto-convert:**

```python
class ToolResult(BaseModel):
    model_config = {
        "populate_by_name": True,
        "alias_generator": lambda x: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(x.split("_"))
        )
    }
    
    tool_name: str
    execution_time: float
```

---

## 4. Versioning Strategy

### 4.1 URL Versioning (Khuyên dùng)

```
/api/v1/agent/query        # Current stable
/api/v2/agent/query        # Breaking changes
```

### 4.2 Breaking Changes = New Version

**Breaking changes (phải tăng version):**
- Đổi field name
- Đổi data type
- Xóa field required
- Thay đổi behavior
- Đổi URL path

**Non-breaking (giữ nguyên version):**
- Thêm field mới
- Thêm endpoint mới
- Sửa bug
- Thêm optional parameters

### 4.3 Deprecation Policy

```python
# Mark deprecated endpoints
@router.post(
    "/query",
    deprecated=True,
    summary="[DEPRECATED] Use /v2/agent/query instead"
)
async def old_query():
    ...
```

---

## 5. Real-time Communication (SSE)

### 5.1 Event Envelope Pattern (BẮT BUỘC)

**Mọi event đều phải có cùng envelope:**

```typescript
interface AgentEvent<T> {
  eventType: 'START' | 'PLAN_CREATED' | 'TOOL_EXECUTING' | 
             'TOOL_COMPLETED' | 'CRITIC_REVIEWED' | 
             'SYNTHESIZING' | 'FINAL_RESULT' | 'ERROR';
  payload: T;                    // Data riêng của event
  metadata: {
    iteration: number;           // Vòng lặp thứ mấy
    timestamp: string;           // ISO 8601
    executionTime: number;       // Tổng thời gian (ms)
  };
  progress: {
    currentStep: number;         // Bước hiện tại
    totalSteps: number;          // Tổng số bước
    percentComplete: number;     // % hoàn thành
  };
}
```

**Tại sao cần envelope:**
- FE có thể parse bằng 1 hàm duy nhất
- Progress bar dễ implement
- Type safety

### 5.2 SSE Format

```python
# Backend (FastAPI)
async def event_stream():
    yield f"data: {json.dumps({
        'eventType': 'TOOL_EXECUTING',
        'payload': {'toolName': 'tavily', 'parameters': {...}},
        'metadata': {'iteration': 1, 'timestamp': '...', 'executionTime': 1234},
        'progress': {'currentStep': 3, 'totalSteps': 6, 'percentComplete': 50}
    })}\n\n"
```

```typescript
// Frontend (Zod validation)
const AgentEventSchema = z.object({
  eventType: z.enum(['START', 'PLAN_CREATED', ...]),
  payload: z.any(),
  metadata: z.object({
    iteration: z.number(),
    timestamp: z.string().datetime(),
    executionTime: z.number()
  }),
  progress: z.object({
    currentStep: z.number(),
    totalSteps: z.number(),
    percentComplete: z.number().min(0).max(100)
  })
});
```

---

## 6. Error Handling

### 6.1 Error Codes chuẩn

```typescript
// Error codes phải có tài liệu đầy đủ
enum AgentErrorCode {
  // Client errors (4xx)
  INVALID_QUERY = 'INVALID_QUERY',
  QUERY_TOO_LONG = 'QUERY_TOO_LONG',
  INVALID_ITERATIONS = 'INVALID_ITERATIONS',
  
  // Server errors (5xx)
  AGENT_TIMEOUT = 'AGENT_TIMEOUT',
  ORCHESTRATOR_ERROR = 'ORCHESTRATOR_ERROR',
  TOOL_EXECUTION_FAILED = 'TOOL_EXECUTION_FAILED',
  CRITIC_REJECTED = 'CRITIC_REJECTED',
  LLM_RATE_LIMIT = 'LLM_RATE_LIMIT',
  TAVILY_API_ERROR = 'TAVILY_API_ERROR',
  VNSTOCK_API_ERROR = 'VNSTOCK_API_ERROR',
  
  // Unknown
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}
```

### 6.2 Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "AGENT_TIMEOUT",
    "message": "Agent execution exceeded 60 seconds",
    "details": {
      "timeout": 60,
      "elapsed": 60.5,
      "stage": "TOOL_EXECUTING"
    }
  },
  "meta": {
    "requestId": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-02-12T07:20:36.104Z",
    "duration": 60500,
    "version": "v1"
  }
}
```

---

## 7. Mock Data & Testing

### 7.1 Cung cấp Mock Server

```python
# File: src/api/mock/agent_mock.py
@router.post("/mock/agent/query")
async def mock_agent_query():
    """Return predefined mock data for FE development."""
    return {
        "success": True,
        "query": "Giá VCB",
        "answer": "VCB đang ở 95,500 VND (+1.2%)",
        "iterations": 1,
        "executionTime": 2.5,
        # ... full response
    }

@router.post("/mock/agent/query/stream")
async def mock_agent_stream():
    """Stream mock events."""
    events = [
        {"eventType": "START", "payload": {...}, ...},
        {"eventType": "PLAN_CREATED", "payload": {...}, ...},
        # ... all events
    ]
    # Stream với delay giả lập
```

### 7.2 Mock Data File

```typescript
// File: frontend/src/mocks/agent-events.ts
export const mockAgentEvents = [
  {
    eventType: 'START',
    payload: { query: 'Giá cổ phiếu VCB' },
    metadata: { iteration: 1, timestamp: '...', executionTime: 0 },
    progress: { currentStep: 1, totalSteps: 6, percentComplete: 0 }
  },
  {
    eventType: 'PLAN_CREATED',
    payload: {
      plan: {
        originalQuery: 'Giá cổ phiếu VCB',
        interpretedIntent: 'User wants current price of VCB',
        tools: [
          { toolName: 'vnstock_get_quote', parameters: { symbol: 'VCB' }, ... }
        ],
        canParallel: false,
        expectedOutcome: 'Current VCB stock price'
      }
    },
    metadata: { iteration: 1, timestamp: '...', executionTime: 500 },
    progress: { currentStep: 2, totalSteps: 6, percentComplete: 16 }
  },
  // ... complete all events
];
```

---

## 8. Documentation Standards

### 8.1 Tự động generate từ code

```python
# FastAPI tự generate docs
app = FastAPI(
    title="AI Finance Agent API",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc
)

# Mỗi endpoint phải có docstring đầy đủ
@router.post("/query")
async def agent_query(request: AgentQueryRequest):
    """
    Execute multi-agent query.
    
    ## Workflow
    1. Orchestrator phân tích query
    2. Critic đánh giá plan
    3. Thực thi tools
    4. Tổng hợp kết quả
    
    ## Example
    ```json
    {
      "query": "Giá VCB hôm nay",
      "maxIterations": 3
    }
    ```
    
    ## Response
    Trả về `AgentQueryResponse` với đầy đủ thông tin execution.
    """
    ...
```

### 8.2 Changelog

```markdown
# API Changelog

## v1.0.0 (2026-02-12)
- Initial release
- Agent query endpoint
- SSE streaming support
- Tavily + VNStock tools

## v1.1.0 (Planned)
- [ ] Add WebSocket support
- [ ] Add more VNStock tools
- [ ] Caching layer
```

---

## 9. Communication Protocol

### 9.1 Workflow giữa BE và FE teams

```
Day 1: BE Dev
├── Write OpenAPI spec
├── Create PR
└── Request FE review

Day 1-2: FE Review  
├── Review spec
├── Request changes (if any)
└── Approve

Day 2-3: Parallel Development
├── BE: Implement API
└── FE: Dev with mock data

Day 4: Integration
├── Integration test
├── Bug fixes
└── Deploy
```

### 9.2 Communication Channels

**Mọi API change PHẢI qua:**
1. **GitHub PR** - Code review
2. **API Review Meeting** - Discuss breaking changes
3. **#api-changes Slack channel** - Notifications

**Template cho API change request:**

```markdown
## API Change Request

**Endpoint:** POST /api/v1/agent/query
**Type:** [ ] New / [ ] Update / [ ] Deprecate
**Breaking Change:** [ ] Yes / [ ] No

**Description:**
...

**Schema Changes:**
```yaml
# Before
field: string

# After  
field: number
```

**Migration Guide:**
- FE cần đổi gì...
- Timeline: ...
```

---

## 10. Checklist

**Trước khi merge PR:**

- [ ] OpenAPI spec updated
- [ ] Pydantic schemas match spec
- [ ] Field names use camelCase in JSON
- [ ] Error handling implemented
- [ ] Mock endpoints created
- [ ] Tests pass
- [ ] Documentation updated
- [ ] FE team notified

**Trước khi deploy:**

- [ ] Version bumped (if breaking)
- [ ] Changelog updated
- [ ] Migration guide written (if breaking)
- [ ] FE has test in staging
- [ ] Rollback plan ready

---

## Appendix: Tools & Resources

### Backend
- **FastAPI:** Web framework
- **Pydantic:** Schema validation
- **OpenAPI Generator:** Generate client SDK

### Frontend
- **Zod:** Runtime validation
- **OpenAPI TypeScript:** Generate types from spec
- **React Query:** Data fetching

### Testing
- **Postman:** API testing
- **Swagger UI:** Interactive docs
- **Mockoon:** Mock server

---

**End of Document**  
**Author:** Backend Team  
**Reviewers:** Frontend Team Lead, Tech Lead
