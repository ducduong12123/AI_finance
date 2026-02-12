# Zod Integration Plan - FE-BE Data Validation Layer

## Tổng quan

Mục tiêu: Xây lớp validation 2 chiều **Frontend (Zod)** ↔ **Backend (Pydantic)** để đảm bảo type safety từ input user → API → LLM processing.

### Tại sao cần Zod + Pydantic?

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRƯỚC (Thiếu Zod)                           │
├─────────────────────────────────────────────────────────────────────┤
│  User Input → FE State → JSON Payload → [KHÔNG CÓ VALIDATION]      │
│                                ↓                                    │
│                        BE nhận DƠN, parse tùy tiện                  │
│                                ↓                                    │
│                        LLM nhận data KHÔNG ĐƯỢC chuẩn hóa         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        SAU (Có Zod + Pydantic)                      │
├─────────────────────────────────────────────────────────────────────┤
│  User Input → Zod.parse() → Valid Payload → API Request            │
│                                ↓                                    │
│  BE: Pydantic.parse_obj() → Strict Type → LLM                      │
│                                ↓                                    │
│  Response: Pydantic Model → Zod Schema → FE State                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Phân tích BE Schemas (High Priority)

### 1.1 Các BE Pydantic Schemas cần map sang Zod

Dựa trên system_spec.md, các schemas chính:

| Schema | Mục đích | Ưu tiên |
|--------|----------|---------|
| `ChatRequest` | Validate tin nhắn chat gửi lên | 🔴 Cao |
| `Message` | Định dạng tin nhắn (role, content, messageId) | 🔴 Cao |
| `FileUploadRequest` | Upload PDF/Doc cho RAG | 🟡 Trung |
| `UserProfile` | Thông tin user profile | 🟡 Trung |
| `Transaction` | Giao dịch tài chính | 🟡 Trung |
| `Portfolio` | Danh mục đầu tư | 🟢 Thấp |
| `AnalysisResult` | Kết quả phân tích từ LLM | 🟡 Trung |

### 1.2 Action Items

```bash
# Bước 1: Đọc BE schemas từ backend/
frontend/src/types/     # Tạo thư mục này
├── index.ts          # Export tất cả schemas
├── chat.ts           # Chat-related schemas
├── finance.ts        # Finance-related schemas
└── shared.ts         # Shared types
```

---

## Phase 2: Tạo Zod Schemas (High Priority)

### 2.1 Cấu trúc thư mục

```
frontend/
├── src/
│   ├── types/
│   │   ├── schemas/
│   │   │   ├── index.ts           # Export all schemas
│   │   │   ├── chat.ts            # Chat validation schemas
│   │   │   ├── finance.ts         # Finance validation schemas
│   │   │   └── shared.ts          # Shared validation utilities
│   │   ├── inference.ts           # Type inference từ Zod
│   │   └── api.ts                 # API response types
│   ├── lib/
│   │   ├── validator.ts           # Validation utilities
│   │   └── api-client.ts          # Type-safe API client
│   └── components/
│       ├── MyAssistantProvider.tsx
│       └── MyChat.tsx
```

### 2.2 Ví dụ Code: Chat Schema (`frontend/src/types/schemas/chat.ts`)

```typescript
import { z } from "zod";

// ============================================
// Chat Request/Response Schemas
// ============================================

/**
 * Schema cho tin nhắn chat
 * Map với BE: Message Schema (Pydantic)
 */
export const zodMessageSchema = z.object({
  messageId: z.string().uuid().optional(), // BE tạo nếu không có
  role: z.enum(["user", "assistant", "system"]),
  content: z.string().min(1, "Content cannot be empty"),
  status: z.enum(["streaming", "complete", "error"]).optional(),
  timestamp: z.date().optional(),
});

export type ZodMessage = z.infer<typeof zodMessageSchema>;

/**
 * Schema cho chat request gửi lên BE
 * Map với BE: ChatRequest Schema (Pydantic)
 */
export const zodChatRequestSchema = z.object({
  messages: z
    .array(zodMessageSchema)
    .min(1, "At least one message required")
    .max(100, "Maximum 100 messages per request"),
  
  // Optional metadata cho RAG
  contextId: z.string().uuid().optional(),
  fileIds: z.array(z.string().uuid()).optional(),
  
  // Streaming options
  stream: z.boolean().default(true),
  
  // Model options
  model: z.enum(["gemini-2.0-flash", "gemini-1.5-pro"]).default("gemini-2.0-flash"),
  
  // Temperature for creativity (0-2)
  temperature: z.number().min(0).max(2).default(0.7),
});

export type ZodChatRequest = z.infer<typeof zodChatRequestSchema>;

/**
 * Schema cho streaming events từ BE
 * Map với BE: AG-UI Events (Pydantic)
 */
export const zodTextMessageStartSchema = z.object({
  eventType: z.literal("TextMessageStart"),
  messageId: z.string().uuid(),
});

export const zodTextMessageContentSchema = z.object({
  eventType: z.literal("TextMessageContent"),
  messageId: z.string().uuid(),
  content: z.string(),
});

export const zodTextMessageEndSchema = z.object({
  eventType: z.literal("TextMessageEnd"),
  messageId: z.string().uuid(),
});

export const zodRunFinishedSchema = z.object({
  eventType: z.literal("RunFinished"),
});

export const zodRunErrorSchema = z.object({
  eventType: z.literal("RunError"),
  message: z.string(),
  code: z.string().optional(),
});

/**
 * Union type cho tất cả AG-UI events
 */
export const zodAGUIEventSchema = z.union([
  zodTextMessageStartSchema,
  zodTextMessageContentSchema,
  zodTextMessageEndSchema,
  zodRunFinishedSchema,
  zodRunErrorSchema,
]);

export type ZodAGUIEvent = z.infer<typeof zodAGUIEventSchema>;
```

### 2.3 Ví dụ Code: Shared Validation (`frontend/src/types/schemas/shared.ts`)

```typescript
import { z } from "zod";

// ============================================
// Shared Validation Utilities
// ============================================

/**
 * UUID validation
 */
export const zodUUID = z.string().uuid("Invalid UUID format");

/**
 * Email validation (RFC 5322 subset)
 */
export const zodEmail = z.string().email("Invalid email format");

/**
 * Date string validation (ISO 8601)
 */
export const zodISODate = z.string().datetime("Invalid date format");

/**
 * Pagination params
 */
export const zodPaginationParams = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
});

export type ZodPaginationParams = z.infer<typeof zodPaginationParams>;

/**
 * Sort params
 */
export const zodSortParams = z.object({
  sortBy: z.string().optional(),
  sortOrder: z.enum(["asc", "desc"]).default("asc"),
});

/**
 * API Response wrapper
 */
export const zodApiResponse = <T extends z.ZodType>(dataSchema: T) =>
  z.object({
    success: z.boolean(),
    data: dataSchema.optional(),
    error: z
      .object({
        code: z.string(),
        message: z.string(),
        details: z.record(z.unknown()).optional(),
      })
      .optional(),
    meta: z
      .object({
        requestId: z.string().uuid().optional(),
        timestamp: z.date(),
        latency: z.number().optional(),
      })
      .optional(),
  });

export type ZodApiResponse<T> = z.infer<ReturnType<typeof zodApiResponse<T>>>;

/**
 * Validation helper function
 */
export function validateWithZod<T>(
  schema: z.ZodType<T>,
  data: unknown
): { success: true; data: T } | { success: false; errors: z.ZodError } {
  const result = schema.safeParse(data);
  
  if (result.success) {
    return { success: true, data: result.data };
  }
  
  return { success: false, errors: result.error };
}

/**
 * Parse with throw on error (for non-critical cases)
 */
export function parseWithZod<T>(schema: z.ZodType<T>, data: unknown): T {
  return schema.parse(data);
}
```

---

## Phase 3: Tích hợp vào MyAssistantProvider.tsx (High Priority)

### 3.1 Import và sử dụng Zod

```typescript
// frontend/components/MyAssistantProvider.tsx
"use client";

import { createAGUI, AGUIRuntimeProvider, useAGUI } from "@ag-ui/client";
import { useState, useCallback, useEffect, useRef } from "react";
import type { Message } from "@ag-ui/core";
import { MyChat } from "./MyChat";

// ✅ MỚI: Import Zod schemas
import { 
  zodChatRequestSchema, 
  zodAGUIEventSchema,
  validateWithZod,
} from "@/types/schemas/chat";

export function MyAssistantProvider() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [input, setInput] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // ✅ MỚI: Validate chat request trước khi gửi
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Client-side validation với Zod
    const rawPayload = {
      messages: [...messages, { role: "user", content: input }],
      stream: true,
      temperature: 0.7,
    };

    const validation = validateWithZod(zodChatRequestSchema, rawPayload);
    
    if (!validation.success) {
      console.error("❌ Validation errors:", validation.errors.format());
      // ✅ Hiển thị lỗi cho user
      alert(`Validation failed: ${validation.errors.errors[0]?.message}`);
      return;
    }

    // ✅ Payload đã được validate - an toàn để gửi
    const validPayload = validation.data;
    
    if (!validPayload.messages[validPayload.messages.length - 1].content.trim() || isRunning) {
      return;
    }

    const userMessageId = Date.now().toString();
    const userContent = input;

    // ... existing code tiếp tục
  };

  // ✅ MỚI: Validate AG-UI events từ BE
  const parseAGUIEvent = useCallback((rawEvent: unknown) => {
    const validation = validateWithZod(zodAGUIEventSchema, rawEvent);
    
    if (!validation.success) {
      console.warn("⚠️ Invalid AG-UI event received:", validation.errors.format());
      return null;
    }
    
    return validation.data;
  }, []);

  // ... rest of component
}
```

### 3.2 Streaming Parser với Zod

```typescript
// frontend/lib/streaming-parser.ts
import { z } from "zod";

interface StreamParserOptions<T> {
  schema: z.ZodType<T>;
  onEvent: (event: T) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

/**
 * Parse SSE stream với Zod validation
 */
export function parseSSEWithZod<T>(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  options: StreamParserOptions<T>
): void {
  const decoder = new TextDecoder();
  let buffer = "";

  (async () => {
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          options.onComplete?.();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("EVENT: ")) {
            const eventType = line.replace("EVENT: ", "").trim();
            const dataLine = lines.find((l) => l.startsWith("data: "));
            
            if (dataLine) {
              try {
                const rawData = JSON.parse(dataLine.replace("data: ", ""));
                const eventWithType = { ...rawData, eventType };
                
                const parsed = options.schema.safeParse(eventWithType);
                if (parsed.success) {
                  options.onEvent(parsed.data);
                } else {
                  console.warn("Event validation failed:", parsed.error.format());
                }
              } catch (e) {
                console.error("Failed to parse event data:", e);
              }
            }
          }
        }
      }
    } catch (error) {
      options.onError?.(error as Error);
    }
  })();
}
```

---

## Phase 4: Tích hợp vào MyChat.tsx (Medium Priority)

### 4.1 Form Validation với Zod

```typescript
// frontend/components/MyChat.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import type { Message } from "@ag-ui/core";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ✅ MỚI: Import Zod
import { z } from "zod";

// ✅ MỚI: Input validation schema
const zodInputSchema = z.object({
  content: z
    .string()
    .min(1, "Message cannot be empty")
    .max(10000, "Message too long (max 10,000 characters)")
    .refine((val) => !val.trim().startsWith("/"), {
      message: "Commands not supported yet",
    }),
});

interface MyChatProps {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isRunning: boolean;
}

export function MyChat({ messages, input, setInput, handleSubmit, isRunning }: MyChatProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [inputError, setInputError] = useState<string | null>(null); // ✅ MỚI

  // ✅ MỚI: Validate input real-time
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setInput(value);
    
    const validation = zodInputSchema.safeParse({ content: value });
    if (!validation.success) {
      setInputError(validation.error.errors[0]?.message || "Invalid input");
    } else {
      setInputError(null);
    }
  };

  // ✅ MỚI: Validate trước khi submit
  const handleFormSubmit = (e: React.FormEvent) => {
    const validation = zodInputSchema.safeParse({ content: input });
    
    if (!validation.success) {
      e.preventDefault();
      setInputError(validation.error.errors[0]?.message || "Invalid input");
      return;
    }
    
    setInputError(null);
    handleSubmit(e);
  };

  return (
    <div className="...">
      {/* ... existing UI ... */}
      
      <form onSubmit={handleFormSubmit} className="p-4 border-t border-zinc-200 dark:border-zinc-800">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              value={input}
              onChange={handleInputChange}
              className={`w-full rounded-xl border px-4 py-3 outline-none focus:ring-2 ${
                inputError 
                  ? "border-red-500 focus:ring-red-500" 
                  : "border-input bg-background focus:ring-ring"
              }`}
              placeholder="Send a message..."
              disabled={isRunning}
            />
            {/* ✅ MỚI: Hiển thị lỗi */}
            {inputError && (
              <span className="absolute -bottom-5 left-0 text-xs text-red-500">
                {inputError}
              </span>
            )}
          </div>
          <button
            type="submit"
            disabled={isRunning || !input.trim() || !!inputError}
            className="..."
          >
            {/* ... */}
          </button>
        </div>
      </form>
    </div>
  );
}
```

---

## Phase 5: Type-Safe API Client (Medium Priority)

### 5.1 API Client với Zod Response Validation

```typescript
// frontend/lib/api-client.ts
import { z } from "zod";

const API_BASE = "/api";

interface RequestOptions {
  schema: z.ZodType; // Response schema
  retries?: number;
  timeout?: number;
}

/**
 * Type-safe fetch wrapper với Zod validation
 */
export async function fetchWithZod<T>(
  endpoint: string,
  options: RequestOptions & { schema: z.ZodType<T> }
): Promise<{ data: T; meta?: unknown } | { error: { code: string; message: string } }> {
  const { schema, retries = 1, timeout = 30000 } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return {
        error: {
          code: `HTTP_${response.status}`,
          message: `Request failed with status ${response.status}`,
        },
      };
    }

    const rawData = await response.json();
    const parsed = schema.safeParse(rawData);

    if (!parsed.success) {
      console.error("❌ Response validation failed:", parsed.error.format());
      return {
        error: {
          code: "VALIDATION_ERROR",
          message: "Response schema validation failed",
        },
      };
    }

    return { data: parsed.data };
  } catch (error) {
    clearTimeout(timeoutId);
    return {
      error: {
        code: "NETWORK_ERROR",
        message: error instanceof Error ? error.message : "Unknown error",
      },
    };
  }
}

// ============================================
// API Methods với Type Safety
// ============================================

/**
 * Chat API
 */
export async function sendChatMessage(
  messages: Array<{ role: string; content: string }>,
  options?: { stream?: boolean; temperature?: number }
) {
  const response = await fetchWithZod("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      stream: options?.stream ?? true,
      temperature: options?.temperature ?? 0.7,
    }),
    schema: z.object({
      success: z.boolean(),
      messageId: z.string().uuid(),
    }),
  });

  return response;
}

/**
 * File Upload API (cho RAG)
 */
export async function uploadDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetchWithZod("/upload", {
    method: "POST",
    body: formData,
    schema: z.object({
      success: z.boolean(),
      fileId: z.string().uuid(),
      chunks: z.number(),
    }),
  });

  return response;
}
```

---

## Phase 6: Export & Re-export (Medium Priority)

### 6.1 Main Index

```typescript
// frontend/src/types/schemas/index.ts
export * from "./chat";
export * from "./finance";
export * from "./shared";

// Re-export type inference
export type { ZodMessage } from "./chat";
export type { ZodChatRequest } from "./chat";
export type { ZodAGUIEvent } from "./chat";
export type { ZodPaginationParams } from "./shared";
export type { ZodApiResponse } from "./shared";

// Re-export validators
export { 
  validateWithZod, 
  parseWithZod,
  zodChatRequestSchema,
  zodAGUIEventSchema,
} from "./chat";
```

---

## Phase 7: Documentation (Low Priority)

### 7.1 Schema Mapping Document

```markdown
# FE-BE Schema Mapping (Source of Truth)

## Chat Flow

### Request: FE → BE

| FE (Zod) | BE (Pydantic) | Notes |
|----------|---------------|-------|
| `ZodMessage.role` | `Message.role` | "user" \| "assistant" \| "system" |
| `ZodMessage.content` | `Message.content` | String content |
| `ZodMessage.messageId` | `Message.id` | UUID (FE tạo hoặc BE sinh) |
| `ZodChatRequest.stream` | `ChatRequest.stream` | Streaming flag |
| `ZodChatRequest.temperature` | `ChatRequest.temperature` | 0-2 float |

### Response: BE → FE

| BE (Pydantic) | FE (Zod) | Notes |
|--------------|----------|-------|
| `TextMessageStart` | `ZodTextMessageStart` | eventType + messageId |
| `TextMessageContent` | `ZodTextMessageContent` | eventType + messageId + content |
| `TextMessageEnd` | `ZodTextMessageEnd` | eventType + messageId |
| `RunFinished` | `ZodRunFinished` | eventType only |
| `RunError` | `ZodRunError` | eventType + message + code |

## RAG Flow (File Upload)

| FE (Zod) | BE (Pydantic) | Notes |
|----------|---------------|-------|
| `fileId` | `Document.id` | UUID reference |
| `chunks` | `Document.chunk_count` | Number of text chunks |

## Finance Flow (TBD)

Sẽ cập nhật khi implement Finance Core modules.
```

---

## Dependencies

```json
// frontend/package.json
{
  "dependencies": {
    "zod": "^3.22.4"  // ⬅️ Thêm dòng này
  },
  "devDependencies": {
    "@types/node": "^20.10.0",
    "typescript": "^5.3.0"
  }
}
```

### Cài đặt:

```bash
cd frontend
npm install zod
# hoặc
pnpm add zod
```

---

## Checklist

- [ ] **Phase 1**: Phân tích BE Pydantic schemas
- [ ] **Phase 2**: Tạo Zod schemas (`frontend/src/types/schemas/`)
- [ ] **Phase 3**: Tích hợp vào `MyAssistantProvider.tsx`
- [ ] **Phase 4**: Tích hợp vào `MyChat.tsx`
- [ ] **Phase 5**: Tạo type-safe API client (`frontend/lib/api-client.ts`)
- [ ] **Phase 6**: Export utilities (`frontend/src/types/schemas/index.ts`)
- [ ] **Phase 7**: Cập nhật documentation (`docs/schema_mapping.md`)

---

## Lợi ích của Zod + Pydantic Combo

| Benefit | Description |
|---------|-------------|
| **Type Safety** | Compile-time type checking on FE |
| **Runtime Validation** | Catch bad data before it reaches BE |
| **Schema Consistency** | FE & BE use compatible schemas |
| **Better DX** | Auto-generated from Zod → TypeScript types |
| **Error Messages** | Human-readable validation errors |
| **Documentation** | Schemas serve as self-documenting API contracts |

---

**Status**: Plan ready. Chờ approve để proceed với implementation.
