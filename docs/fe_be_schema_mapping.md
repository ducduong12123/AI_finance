# FE-BE Schema Mapping (Source of Truth)

> **Lưu ý**: Tài liệu này là nguồn sự thật (Source of Truth) cho việc mapping schemas giữa Frontend (Zod) và Backend (Pydantic).

---

## Tổng quan

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  User Input ──► Zod Validation (FE) ──► API Request ──► Pydantic  │
│                         ↓                                           │
│                  TypeScript Types                                   │
│                                                                     │
│  LLM Response ──► Pydantic Models ──► API Response ──► Zod Parse    │
│                                                 ↓                   │
│                                            React State              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Chat Flow

### 1.1 Request: Frontend → Backend

| Frontend (Zod) | Backend (Pydantic) | Type | Required | Notes |
|----------------|-------------------|------|----------|-------|
| `messages` | `messages` | `List[Message]` | ✅ | Array of message objects |
| `messages[].role` | `messages[].role` | `Literal["user", "assistant", "system"]` | ✅ | Message author role |
| `messages[].content` | `messages[].content` | `str` | ✅ | Message text content |
| `messages[].messageId` | `messages[].id` | `UUID` | ❌ | FE optional, BE generates if missing |
| `stream` | `stream` | `bool` | ❌ | Default: `true` |
| `temperature` | `temperature` | `float` | ❌ | Range: 0-2, Default: 0.7 |
| `model` | `model` | `Literal["gemini-2.0-flash", "gemini-1.5-pro"]` | ❌ | Default: `gemini-2.0-flash` |
| `contextId` | `context_id` | `UUID` | ❌ | For RAG context |
| `fileIds` | `file_ids` | `List[UUID]` | ❌ | Attached documents |

### 1.2 Response: Backend → Frontend (AG-UI Events)

| Backend (Pydantic) | Frontend (Zod) | Event Type | Description |
|-------------------|----------------|------------|-------------|
| `TextMessageStart` | `ZodTextMessageStart` | `TextMessageStart` | Assistant starts new message |
| `TextMessageContent` | `ZodTextMessageContent` | `TextMessageContent` | Streaming content chunk |
| `TextMessageEnd` | `ZodTextMessageEnd` | `TextMessageEnd` | Message streaming complete |
| `RunFinished` | `ZodRunFinished` | `RunFinished` | Chat session complete |
| `RunError` | `ZodRunError` | `RunError` | Error occurred |

### 1.3 Message Schema Details

```typescript
// Frontend (Zod)
interface ZodMessage {
  messageId?: string;      // Optional, BE generates UUID
  role: "user" | "assistant" | "system";
  content: string;
  status?: "streaming" | "complete" | "error";
  timestamp?: Date;
}
```

```python
# Backend (Pydantic)
class Message(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)
    status: Literal["streaming", "complete", "error"] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

---

## 2. RAG / Document Flow

### 2.1 Upload Request

| Frontend (Zod) | Backend (Pydantic) | Type | Notes |
|----------------|-------------------|------|-------|
| `file` | `file` | `UploadFile` | Binary file upload |
| `metadata` | `metadata` | `dict` | Optional file metadata |

### 2.2 Upload Response

| Backend (Pydantic) | Frontend (Zod) | Type |
|-------------------|----------------|------|
| `file_id` | `fileId` | `UUID` |
| `filename` | `filename` | `str` |
| `chunks` | `chunks` | `int` |
| `status` | `status` | `"processing" | "indexed" | "failed"` |

---

## 3. Validation Rules

### 3.1 Frontend (Zod) Validation

```typescript
// frontend/types/schemas/chat.ts

// Message validation
const zodMessageSchema = z.object({
  messageId: z.string().uuid().optional(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string().min(1, "Content cannot be empty"),
  status: z.enum(["streaming", "complete", "error"]).optional(),
  timestamp: z.date().optional(),
});

// Chat request validation
const zodChatRequestSchema = z.object({
  messages: z
    .array(zodMessageSchema)
    .min(1, "At least one message required")
    .max(100, "Maximum 100 messages per request"),
  stream: z.boolean().default(true),
  temperature: z.number().min(0).max(2).default(0.7),
  model: z.enum(["gemini-2.0-flash", "gemini-1.5-pro"]).default("gemini-2.0-flash"),
});
```

### 3.2 Backend (Pydantic) Validation

```python
# backend/schemas/chat.py

from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class Message(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)
    status: Literal["streaming", "complete", "error"] | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_items=1, max_items=100)
    stream: bool = True
    temperature: float = Field(0.7, ge=0, le=2)
    model: Literal["gemini-2.0-flash", "gemini-1.5-pro"] = "gemini-2.0-flash"
    context_id: UUID | None = None
    file_ids: List[UUID] | None = None
```

---

## 4. Error Handling

### 4.1 Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request body validation failed |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server-side error |
| `LLM_ERROR` | 500 | LLM generation failed |

### 4.2 Error Response Format

```typescript
// Frontend (Zod)
const zodErrorResponseSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.unknown()).optional(),
  }),
});
```

```python
# Backend (Pydantic)
class ErrorResponse(BaseModel):
    success: Literal[False]
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None
```

---

## 5. Finance Flow (TBD)

> Phần này sẽ được cập nhật khi implement Finance Core modules.

### 5.1 Transaction Schema (Draft)

```typescript
// Frontend (Zod) - Planned
interface ZodTransaction {
  id: string;
  amount: number;
  type: "income" | "expense";
  category: string;
  description: string;
  date: string;
  currency: string;
}
```

```python
# Backend (Pydantic) - Planned
class Transaction(BaseModel):
    id: UUID
    amount: float = Field(..., gt=0)
    type: Literal["income", "expense"]
    category: str
    description: str
    date: datetime
    currency: str = "VND"
```

---

## 6. Shared Types

### 6.1 Pagination

```typescript
// Frontend (Zod)
const zodPaginationParamsSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
});

interface ZodPaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}
```

```python
# Backend (Pydantic)
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationResult

class PaginationResult(BaseModel):
    page: int
    limit: int
    total: int
    has_more: bool
```

---

## 7. File Structure

```
frontend/
├── types/
│   ├── schemas/
│   │   ├── index.ts          # Re-exports
│   │   └── chat.ts           # Chat validation schemas
│   └── inference.ts         # Type inference utilities
└── lib/
    └── api-client.ts        # Type-safe API client

backend/
└── schemas/
    ├── chat.py              # Pydantic chat schemas
    └── finance.py           # Pydantic finance schemas
```

---

## 8. Update Log

| Date | Changes | Author |
|------|---------|--------|
| 2024-02-11 | Initial chat schemas | FE Team |
| 2024-02-11 | Added AG-UI event schemas | FE Team |
| 2024-02-11 | Documented FE-BE mapping | FE Team |

---

> **Lưu ý quan trọng**: Khi thay đổi schemas, hãy cập nhật cả hai phía (FE và BE) để đảm bảo compatibility.
