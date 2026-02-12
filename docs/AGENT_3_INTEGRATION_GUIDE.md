# Agent 3 (Integration) - Hướng dẫn sử dụng Mock API

> **Tài liệu này dành cho Agent 3** - Ngườ làm nhiệm vụ ghép nối Backend & Frontend

---

## 🎯 Nhiệm vụ Agent 3

1. **Test Backend** - Verify API hoạt động đúng
2. **Test Frontend** - Verify FE nhận và hiển thị đúng data
3. **Integration Test** - Ghép nối BE & FE
4. **Bug Reporting** - Báo cáo lỗi cho Agent 1 (BE) hoặc Agent 2 (FE)

---

## 📡 Mock Endpoints (Không tốn API quota)

### 1. Mock Query (Sync)
```bash
POST http://localhost:8001/api/mock/agent/query
Content-Type: application/json

{
  "query": "Giá VCB",
  "maxIterations": 3
}
```

**Response:** Full AgentQueryResponse với data mẫu

### 2. Mock Query Stream (SSE)
```bash
POST http://localhost:8001/api/mock/agent/query/stream
Content-Type: application/json

{
  "query": "Giá VCB"
}
```

**Response:** SSE stream với đầy đủ events:
- START → PLANNING → PLAN_CREATED → CRITIC_REVIEWED
- TOOL_EXECUTING → TOOL_COMPLETED → SYNTHESIZING → FINAL_RESULT

### 3. Mock Error Response
```bash
POST http://localhost:8001/api/mock/agent/query/error
```

**Response:** Error response để test error handling

### 4. Mock Stream Error
```bash
POST http://localhost:8001/api/mock/agent/query/stream/error
```

**Response:** Stream fail giữa chừng (test recovery)

---

## 🔧 Cách sử dụng cho Integration Testing

### Step 1: Test Backend API
```bash
# Test mock endpoint
curl -X POST http://localhost:8001/api/mock/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' | jq

# Verify response format
echo "✅ Check: success, query, answer, iterations, executionTime"
echo "✅ Check: planSummary, toolExecutions, criticReviews"
echo "✅ Check: meta (requestId, timestamp, duration, version)"
```

### Step 2: Test Frontend Integration
```javascript
// Test từ FE console
const response = await fetch('/api/mock/agent/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'test' })
});
const data = await response.json();
console.log('Response:', data);

// Verify
console.assert(data.success === true, 'success should be true');
console.assert(typeof data.answer === 'string', 'answer should be string');
console.assert(Array.isArray(data.toolExecutions), 'toolExecutions should be array');
```

### Step 3: Test SSE Stream
```javascript
const eventSource = new EventSource('/api/mock/agent/query/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.eventType, data.progress);
  
  if (data.eventType === 'FINAL_RESULT') {
    console.log('Final answer:', data.payload.answer);
    eventSource.close();
  }
};
```

---

## 📋 Checklist Integration Test

**Backend API:**
- [ ] `/api/mock/agent/query` trả về đúng format
- [ ] `/api/mock/agent/query/stream` stream events đúng thứ tự
- [ ] Response có đầy đủ fields (success, answer, meta...)
- [ ] Error handling hoạt động

**Frontend:**
- [ ] FE gọi API đúng endpoint
- [ ] FE parse response đúng format
- [ ] FE hiển thị answer cho user
- [ ] FE hiển thị progress (nếu dùng stream)
- [ ] FE handle error gracefully

**Integration:**
- [ ] End-to-end flow hoạt động
- [ ] Data consistency giữa BE & FE
- [ ] Error propagation đúng

---

## 🐛 Bug Reporting Template

Khi phát hiện lỗi, report cho Agent 1 (BE) hoặc Agent 2 (FE):

```markdown
## Bug Report

**Component:** [BE/FE/Integration]
**Severity:** [Critical/High/Medium/Low]

### Steps to Reproduce
1. 
2. 
3. 

### Expected Behavior

### Actual Behavior

### Evidence
```json
// Request
{}

// Response
{}
```

### Screenshots/Logs

### Environment
- Backend: localhost:8001
- Frontend: localhost:3000
```

---

## 🔗 Liên hệ

- **Agent 1 (Backend):** Nhờ fix API, schema
- **Agent 2 (Frontend):** Nhờ fix UI/UX, component
- **User:** Báo cáo tổng thể, yêu cầu feature

---

**End of Document**
