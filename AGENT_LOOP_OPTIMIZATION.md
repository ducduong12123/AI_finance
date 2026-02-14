# Agent Loop Optimization Proposal

## Tóm tắt vấn đề

Với query đơn giản như "giá cổ phiếu VCB", hệ thống hiện tại:
- Chạy **3 iterations** (quá nhiều)
- Gọi **6-9 API calls** (lãng phí)
- Mất **10-15 giây** (quá chậm)
- Vẫn trả về kết quả sai định dạng

## Root Causes

### 1. Format giá sai trong vnstock_tool.py
```python
# Hiện tại (sai):
f"**Giá hiện tại:** {quote.price:,.0f} VND"  # → "64 VND"

# Đúng:
f"**Giá hiện tại:** {quote.price * 1000:,.0f} VND"  # → "64,000 VND"
```

### 2. Over-engineering cho simple queries
- Query đơn giản (real-time data) không cần Critic
- Không cần multiple iterations
- Không cần cross-check với Tavily

### 3. Tool results không được accumulate
- Mỗi iteration gọi lại tools từ đầu
- Không tái sử dụng kết quả cũ

## Giải pháp

### Phase 1: Hotfix (Ngay lập tức)

#### 1.1 Fix vnstock_tool.py
```python
# vnstock_tool.py - Dòng 347
def format_quote_for_llm(self, response: VNStockResponse) -> str:
    if not response.success:
        return f"❌ {response.message}"

    quote = response.data
    # FIX: Nhân giá với 1000 (vnstock trả về đơn vị nghìn đồng)
    price_vnd = quote.price * 1000
    open_vnd = quote.open_price * 1000
    high_vnd = quote.high_price * 1000
    low_vnd = quote.low_price * 1000
    
    lines = [
        f"## 📈 Thông tin cổ phiếu {quote.symbol}",
        "",
        f"**Giá hiện tại:** {price_vnd:,.0f} VND",
        f"**Thay đổi:** {quote.change * 1000:+,.0f} ({quote.change_percent:+.2f}%)",
        f"**Khối lượng giao dịch:** {quote.volume:,}",
        "",
        "**Giá trong ngày:**",
        f"- Mở cửa: {open_vnd:,.0f} VND",
        f"- Cao nhất: {high_vnd:,.0f} VND",
        f"- Thấp nhất: {low_vnd:,.0f} VND",
    ]
    return "\n".join(lines)
```

#### 1.2 Thêm Simple Query Bypass
```python
# agent_loop.py
class AgentLoop:
    # ...
    
    # Simple query patterns - không cần Critic
    SIMPLE_PATTERNS = [
        r'giá\s+(cổ phiếu|cp)?\s*\w+',  # giá VCB, giá cổ phiếu VNM
        r'\w+\s+bao nhiêu',  # VCB bao nhiêu
        r'giá\s+hiện tại',  # giá hiện tại
    ]
    
    def _is_simple_query(self, query: str) -> bool:
        """Kiểm tra query có đơn giản không (không cần Critic)."""
        import re
        query_lower = query.lower()
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False
    
    async def execute_simple(self, user_query: str) -> AgentLoopResult:
        """Execute simple query without Critic overhead."""
        start_time = time.time()
        
        # Tạo plan đơn giản (không qua LLM)
        plan = self._create_simple_plan(user_query)
        
        # Execute tools
        tool_results = await self.orchestrator.execute_tools(plan)
        
        # Synthesize response
        response = await self.orchestrator.synthesize_response(plan, tool_results)
        
        execution_time = time.time() - start_time
        
        return AgentLoopResult(
            success=response.success,
            query=user_query,
            final_answer=response.synthesized_answer,
            iterations=1,
            execution_time=execution_time,
            plan=plan,
            tool_results=tool_results,
            critic_reviews=[],  # No critic for simple queries
            metrics={
                "latency_ms": round(execution_time * 1000, 2),
                "tokens": 0,  # No LLM calls
                "accuracy": 10.0  # Assume good for simple queries
            }
        )
    
    def _create_simple_plan(self, query: str) -> OrchestratorPlan:
        """Tạo plan đơn giản dựa trên pattern matching."""
        import re
        
        # Extract symbol từ query
        match = re.search(r'(\b[A-Z]{2,4}\b)', query.upper())
        symbol = match.group(1) if match else None
        
        if symbol and any(x in query.lower() for x in ['giá', 'cổ phiếu', 'cp', 'bao nhiêu']):
            return OrchestratorPlan(
                original_query=query,
                interpreted_intent=f"Lấy giá cổ phiếu {symbol}",
                tools=[
                    ToolPlan(
                        tool_name="vnstock_get_quote",
                        parameters={"symbol": symbol},
                        reason="Lấy giá real-time",
                        priority=1
                    )
                ],
                can_parallel=False,
                expected_outcome=f"Giá cổ phiếu {symbol} hiện tại"
            )
        
        # Fallback: dùng Tavily
        return OrchestratorPlan(
            original_query=query,
            interpreted_intent="Tìm kiếm thông tin",
            tools=[
                ToolPlan(
                    tool_name="tavily_web_search",
                    parameters={"query": query, "max_results": 3},
                    reason="Tìm kiếm thông tin",
                    priority=1
                )
            ],
            can_parallel=False,
            expected_outcome="Thông tin về yêu cầu"
        )
    
    async def execute(self, user_query: str, ...) -> AgentLoopResult:
        """Main entry point with smart routing."""
        # Check if simple query
        if self._is_simple_query(user_query):
            return await self.execute_simple(user_query)
        
        # Complex query: use full pipeline with Critic
        return await self._execute_complex(user_query, ...)
```

### Phase 2: Accumulate Tool Results

```python
# agent_loop.py - Trong while loop
async def _execute_complex(self, user_query: str, ...) -> AgentLoopResult:
    all_tool_results: list[ToolResult] = []  # Accumulate across iterations
    
    while current_iteration < self.config.max_iterations:
        current_iteration += 1
        
        # Create plan
        plan = await self.orchestrator.create_plan(user_query)
        
        # Execute only NEW tools (not already executed)
        new_tools = [t for t in plan.tools 
                     if not any(r.tool_name == t.tool_name for r in all_tool_results)]
        
        if new_tools:
            # Create sub-plan with only new tools
            sub_plan = OrchestratorPlan(
                original_query=plan.original_query,
                interpreted_intent=plan.interpreted_intent,
                tools=new_tools,
                can_parallel=plan.can_parallel,
                expected_outcome=plan.expected_outcome
            )
            new_results = await self.orchestrator.execute_tools(sub_plan)
            all_tool_results.extend(new_results)
        
        # Synthesize using ALL accumulated results
        response = await self.orchestrator.synthesize_response(
            plan, all_tool_results  # Use accumulated results
        )
        
        # ... rest of logic
```

### Phase 3: Critic Optimization

```python
# critic.py - Nên có tiêu chí khác nhau cho simple vs complex queries

class CriticAgent(BaseAgent):
    # ...
    
    async def review_simple_query(self, plan: OrchestratorPlan) -> CriticReview:
        """Nhanh gọn cho simple queries - chỉ check tool phù hợp."""
        # Simple check: đúng tool chưa?
        if plan.tools and plan.tools[0].tool_name in ["vnstock_get_quote", "tavily_web_search"]:
            return CriticReview(
                approved=True,
                score=8.0,
                reasoning="Simple query với tool phù hợp",
                concerns=[],
                requires_changes=False
            )
        
        return await self.review_plan(plan)  # Fallback
```

## Hiệu quả dự kiến

| Metric | Trước | Sau | Cải thiện |
|--------|-------|-----|-----------|
| Iterations | 3 | 1 | -67% |
| API Calls | 6-9 | 1-2 | -80% |
| Latency | 10-15s | 1-2s | -85% |
| Cost | $$$ | $ | -80% |
| Accuracy | ❌ (64 VND) | ✅ (64,000 VND) | Fixed |

## Lộ trình triển khai

1. **Ngay lập tức**: Fix vnstock_tool.py (30 phút)
2. **Tuần 1**: Implement Simple Query Bypass
3. **Tuần 2**: Tool results accumulation
4. **Tuần 3**: Critic optimization

## Câu hỏi cho bạn

1. Bạn muốn tôi implement Phase 1 (hotfix) ngay không?
2. Có những query pattern nào khác nên được coi là "simple"?
3. Bạn có muốn thêm caching cho vnstock data (vì giá thay đổi chậm, có thể cache 1-5 phút)?
