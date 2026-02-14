# Agent Architecture Overview - AI Finance Assistant

## 1. Kién trúc Tong quan

He thong Agent duoc thiet ke theo mo hinh **Multi-Agent Orchestration** voi 3 thanh phan chinh:

```mermaid
graph TB
    subgraph Core Agents
        O[OrchestratorAgent<br/>Dieu phoi & Lap ke hoach]
        C[CriticAgent<br/>Danh gia & Phan bien]
        F[FinanceAgent<br/>Chuyen gia Tai chinh]
    end
    
    subgraph Loop Controller
        AL[AgentLoop<br/>Quan ly vong lap]
    end
    
    subgraph State Management
        SM[StateManager<br/>Quan ly trang thai]
    end
    
    subgraph Tools
        TS[tavily_web_search<br/>Tim kiem Web]
        VS[vnstock_get_quote<br/>Gia co phieu VN]
        VI[vnstock_get_company_info<br/>Thong tin cong ty]
    end
    
    AL --> O
    AL --> C
    AL --> SM
    O --> TS
    O --> VS
    O --> VI
    F -.-> O
```

---

## 2. Luong Hoat dong Chinh - Agent Loop

Luong hoat dong duoc dieu phoi boi [`AgentLoop`](src/agents/agent_loop.py:51):

```mermaid
sequenceDiagram
    participant U as User
    participant AL as AgentLoop
    participant O as Orchestrator
    participant C as Critic
    participant T as Tools
    participant SM as StateManager

    U->>AL: User Query
    AL->>SM: Update State: PLANNING
    
    loop Max Iterations: 3
        AL->>O: create_plan query
        O-->>AL: OrchestratorPlan
        
        AL->>C: review_plan
        C-->>AL: CriticReview
        
        alt Plan Rejected
            AL->>AL: Prepare feedback
            Note over AL: Continue to next iteration
        else Plan Approved
            AL->>SM: Update State: EXECUTING
            AL->>O: execute_tools plan
            O->>T: Call tools parallel/sequential
            T-->>O: ToolResult list
            O-->>AL: ToolResult list
            
            AL->>SM: Update State: ANALYZING
            AL->>O: synthesize_response
            O-->>AL: OrchestratorResponse
            
            AL->>C: review_results
            C-->>AL: CriticReview
            
            alt Results Approved
                AL->>SM: Update State: FINALIZING
                AL-->>U: AgentLoopResult
            else Needs Iteration
                AL->>AL: Prepare improved query
            end
        end
    end
```

---

## 3. Chi tiet tung thanh phan

### 3.1 BaseAgent - Lop co so

[`BaseAgent`](src/agents/base.py:7) la lop cha cho tat ca cac Agent:

```python
class BaseAgent:
    def __init__(self, system_prompt, model_name, tools):
        self.system_prompt = system_prompt      # Huong dan cho AI
        self.model_name = model_name            # Gemini model
        self.tools = tools                      # Danh sach tools
        self.model = genai.GenerativeModel(...) # Gemini client
        self.chat_session = None                # Session chat
        self.total_tokens = 0                   # Token tracking
```

**Chuc nang chinh:**
- Quan ly ket noi LLM (Google Gemini)
- Tracking token usage
- Quan ly chat history

---

### 3.2 OrchestratorAgent - Dieu phoi chinh

[`OrchestratorAgent`](src/agents/orchestrator.py:73) la "bo nao" cua he thong:

```mermaid
graph LR
    subgraph OrchestratorAgent
        CP[create_plan<br/>Phan tich & Lap ke hoach]
        ET[execute_tools<br/>Thuc thi tools]
        SR[synthesize_response<br/>Tong hop cau tra loi]
    end
    
    subgraph Tools Registry
        T1[tavily_web_search]
        T2[vnstock_get_quote]
        T3[vnstock_get_company_info]
    end
    
    CP -->|OrchestratorPlan| ET
    ET -->|ToolResult list| SR
    ET --> T1
    ET --> T2
    ET --> T3
```

**Data Models:**

| Model | Mo ta |
|-------|-------|
| [`ToolPlan`](src/agents/orchestrator.py:24) | Ke hoach thuc thi 1 tool: tool_name, parameters, reason, priority |
| [`OrchestratorPlan`](src/agents/orchestrator.py:35) | Ke hoach day du: original_query, interpreted_intent, tools[], can_parallel |
| [`ToolResult`](src/agents/orchestrator.py:49) | Ket qua thuc thi: tool_name, success, result, execution_time, error |
| [`OrchestratorResponse`](src/agents/orchestrator.py:59) | Phan hoi cuoi: synthesized_answer, needs_iteration |

**Logic lap ke hoach:**
1. Nhan user query
2. Goi Gemini de phan tich intent
3. Chon tools phu hop tu registry
4. Tra ve JSON plan

**Logic thuc thi tools:**
- Neu `can_parallel = true`: Thuc thi song song voi `asyncio.gather()`
- Neu `can_parallel = false`: Thuc thi tuan tu

---

### 3.3 CriticAgent - Phan bien & Danh gia

[`CriticAgent`](src/agents/critic.py:39) dam bao chat luong:

```mermaid
graph TB
    subgraph CriticAgent
        RP[review_plan<br/>Danh gia ke hoach]
        RR[review_results<br/>Danh gia ket qua]
    end
    
    subgraph Criteria
        F[Freshness Audit<br/>Kiem tra du lieu moi]
        R[Relevance<br/>Phu hop yeu cau]
        C[Completeness<br/>Day du thong tin]
        E[Efficiency<br/>Hieu qua tools]
    end
    
    RP --> F
    RP --> R
    RP --> C
    RP --> E
    RR --> F
    RR --> R
    RR --> C
    RR --> E
```

**CriticReview Model:**

| Field | Type | Mo ta |
|-------|------|-------|
| approved | bool | Phe duyet hay khong |
| score | float 0-10 | Diem chat luong |
| reasoning | str | Ly do chi tiet |
| concerns | list | Danh sach van de |
| suggestions | list | Goi y cai thien |
| requires_changes | bool | Can thay doi |
| iteration_feedback | str | Huong dan iteration tiep |

**Nguyen tac quan trong - Freshness Audit:**
> "No Old Knowledge" - Doi voi du lieu tai chinh, kien thuc cu training data la vo gia tri. Chi chap nhan thong tin tu Tools.

---

### 3.4 AgentLoop - Vong lap chinh

[`AgentLoop`](src/agents/agent_loop.py:51) dieu phoi toan bo workflow:

```mermaid
stateDiagram-v2
    [*] --> PLANNING: Nhan query
    PLANNING --> CRITIC_REVIEW: Tao plan
    CRITIC_REVIEW --> PLANNING: Plan rejected
    CRITIC_REVIEW --> EXECUTING: Plan approved
    EXECUTING --> ANALYZING: Tools completed
    ANALYZING --> RESULT_REVIEW: Synthesize response
    RESULT_REVIEW --> PLANNING: Needs iteration
    RESULT_REVIEW --> FINALIZING: Approved
    FINALIZING --> [*]: Return result
```

**AgentLoopConfig:**

| Parameter | Default | Mo ta |
|-----------|---------|-------|
| max_iterations | 3 | So lan lap toi da |
| require_critic_approval | true | Can Critic phe duyet |
| parallel_tool_execution | true | Thuc thi tools song song |
| timeout_seconds | 60.0 | Thoi gian timeout |

**Progress Callback Stages:**
1. `start` - Bat dau xu ly
2. `iteration_start` - Bat dau 1 vong lap
3. `planning` - Orchestrator dang lap ke hoach
4. `plan_created` - Ke hoach da tao
5. `critic_review` - Critic dang danh gia
6. `plan_reviewed` - Danh gia xong
7. `plan_rejected` - Ke hoach bi tu choi
8. `executing` - Dang thuc thi tools
9. `tools_completed` - Tools hoan thanh
10. `synthesizing` - Dang tong hop
11. `response_ready` - Phan hoi san sang
12. `result_review` - Critic danh gia ket qua
13. `completed` - Hoan thanh

---

### 3.5 StateManager - Quan ly trang thai

[`StateManager`](src/agents/state/manager.py:18) luu tru trang thai session:

```mermaid
graph LR
    subgraph StateManager
        Cache[In-Memory Cache]
        DB[Supabase Database]
    end
    
    subgraph AgentState
        session_id
        stage
        context
        memory
        last_updated
    end
    
    Cache --> DB
```

**AgentStage Enum:**
- `IDLE` - Cho doi
- `PLANNING` - Dang lap ke hoach
- `EXECUTING` - Dang thuc thi
- `ANALYZING` - Dang phan tich
- `FINALIZING` - Dang hoan thanh

---

## 4. Tools - Cong cu

### 4.1 Tavily Web Search

[`tavily_web_search`](src/agents/tools/tavily_search.py) - Tim kiem web toi uu cho AI:

```python
# Parameters
query: str              # Tu khoa tim kiem
search_depth: str       # basic, advanced, fast, ultra-fast
max_results: int        # So luong ket qua
recency_days: int       # Loc theo thoi gian
```

### 4.2 VNStock Tools

[`vnstock_get_quote`](src/agents/tools/vnstock_tool.py) - Lay gia co phieu VN:
```python
# Parameters
symbol: str  # Ma co phieu: VCB, VNM, VIC...
```

[`vnstock_get_company_info`](src/agents/tools/vnstock_tool.py) - Thong tin cong ty:
```python
# Parameters
symbol: str  # Ma co phieu
```

---

## 5. Vi du Luong Hoat dong

**User Query:** "Phan tich co phieu VCB"

```mermaid
sequenceDiagram
    participant U as User
    participant AL as AgentLoop
    participant O as Orchestrator
    participant C as Critic
    participant T as Tools

    U->>AL: Phan tich co phieu VCB
    AL->>O: create_plan
    
    Note over O: Gemini phan tich:<br/>- Can gia hien tai<br/>- Can thong tin cong ty<br/>- Can tin tuc moi nhat
    
    O-->>AL: Plan with 3 tools:<br/>1. vnstock_get_quote VCB<br/>2. vnstock_get_company_info VCB<br/>3. tavily_web_search VCB
    
    AL->>C: review_plan
    C-->>AL: Approved, Score: 8
    
    AL->>O: execute_tools parallel
    par Parallel Execution
        O->>T: vnstock_get_quote VCB
        O->>T: vnstock_get_company_info VCB
        O->>T: tavily_web_search
    end
    T-->>O: 3 ToolResults
    
    AL->>O: synthesize_response
    O-->>AL: Synthesized answer
    
    AL->>C: review_results
    C-->>AL: Approved, Score: 9
    
    AL-->>U: Final Answer with:<br/>- Gia hien tai<br/>- Chi so P/E, P/B<br/>- Tin tich/Phan tich
```

---

## 6. Co che Iteration

Khi Critic tu choi, he thong se lap lai voi feedback:

```mermaid
graph TB
    A[Plan Created] --> B{Critic Review}
    B -->|Approved| C[Execute Tools]
    B -->|Rejected| D[Prepare Feedback]
    D --> E[Enhanced Query]
    E --> A
    
    C --> F[Synthesize Response]
    F --> G{Result Review}
    G -->|Approved| H[Return Result]
    G -->|Needs Iteration| I[Iteration Feedback]
    I --> J[Improved Query]
    J --> A
```

**Feedback Enhancement:**
```python
# Plan rejected
enhanced_query = f"Yeu cau goc: {original_query}\n\n
                   Ke hoach truoc chua dat. Phan hoi: {feedback}\n\n
                   Hay tao ke hoach moi tot hon."

# Results need iteration
improved_query = f"Yeu cau goc: {original_query}\n\n
                   Ket qua chua dat yeu cau. Phan hoi: {feedback}\n\n
                   Hay thu cach tiep can khac."
```

---

## 7. Metrics & Monitoring

**AgentLoopResult Metrics:**

| Metric | Mo ta |
|--------|-------|
| latency_ms | Thoi gian thuc thi tong |
| tokens | Tong so token su dung |
| accuracy | Diem trung binh tu Critic (scale 0-100) |

**Token Tracking:**
- Orchestrator tokens: input + output
- Critic tokens: input + output
- Total = Orchestrator + Critic

---

## 8. Luu tru Du lieu & Tai su dung

### 8.1 Dau duoc luu?

**Tool Results duoc luu trong:**

```mermaid
graph TB
    subgraph In-Memory - Trong 1 lan execute
        TR[ToolResult objects]
        OR[OrchestratorResponse.tool_results]
        ALR[AgentLoopResult.tool_results]
    end
    
    subgraph Persistent - Session State
        SM[StateManager.memory]
        DB[Supabase Database]
    end
    
    TR --> OR
    OR --> ALR
    ALR -.->|Optional| SM
    SM --> DB
```

**Cac vi tri luu tru:**

| Vi tri | Pham vi | Noi dung |
|--------|---------|----------|
| [`ToolResult`](src/agents/orchestrator.py:49) | Trong 1 iteration | Ket qua tu 1 tool |
| [`OrchestratorResponse.tool_results`](src/agents/orchestrator.py:65) | Trong 1 iteration | List ket qua tu tat ca tools |
| [`AgentLoopResult.tool_results`](src/agents/agent_loop.py:45) | Tra ve cho user | Tat ca tool results cuoi cung |
| [`StateManager.memory`](src/agents/state/manager.py:147) | Cross-session | Co the luu, nhung **Hien chua duoc su dung** |

### 8.2 Du lieu cu co duoc tai su dung?

**TRANG THAI HIEN TAI: KHONG TAI SU DUNG**

```mermaid
sequenceDiagram
    participant AL as AgentLoop
    participant O as Orchestrator
    participant T as Tools
    participant C as Critic

    Note over AL: Iteration 1
    AL->>O: create_plan query
    O-->>AL: Plan 1
    AL->>T: execute_tools Plan 1
    T-->>AL: ToolResults 1
    AL->>C: review_results
    C-->>AL: Rejected - Can iteration
    
    Note over AL: Iteration 2
    AL->>AL: enhanced_query = query + feedback
    AL->>O: create_plan enhanced_query
    Note over O: Tao plan HOAN TOAN MOI<br/>Khong biet ket qua cu
    O-->>AL: Plan 2
    AL->>T: execute_tools Plan 2
    Note over T: Goi tools LAI TU DAU<br/>Khong tai su dung data cu
    T-->>AL: ToolResults 2
```

**Van de hien tai:**

```python
# agent_loop.py - Dong 126
user_query = f"Yêu càu góc: {user_query}\n\nKê hoach truóc chua dat. Phan hoi: {feedback}\n\nHãy tao kê hoach mói tót hon."
# Chi truyen feedback text, KHONG truyen tool_results cu
```

### 8.3 Hieu ung cua viec khong tai su dung

| Tinh huong | Hanh vi hien tai | Van de |
|------------|------------------|---------|
| Tool 1 thanh cong, Tool 2 that bai | Goi LAI ca Tool 1 va Tool 2 | Lang phi API calls |
| Tool 1 tra ve data tot, nhung Critic muon phan tich sau | Goi lai Tool 1 | Duplicate work |
| Can them thong tin moi | Goi lai tat ca tools | Khong optimize |

### 8.4 De xuat cai thien

**Cach 1: Tool Result Caching**

```python
class AgentLoop:
    def __init__(self):
        self.tool_cache: Dict[str, ToolResult] = {}  # Cache by tool_name + params hash
    
    async def execute_with_cache(self, plan):
        results = []
        for tool in plan.tools:
            cache_key = f"{tool.tool_name}:{hash(frozenset(tool.parameters.items()))}"
            if cache_key in self.tool_cache:
                results.append(self.tool_cache[cache_key])  # Reuse
            else:
                result = await self._execute_single_tool(tool)
                self.tool_cache[cache_key] = result
                results.append(result)
        return results
```

**Cach 2: Pass Previous Results to Orchestrator**

```python
# Trong agent_loop.py
if result_review.requires_changes:
    # Truyen kem ket qua cu cho Orchestrator
    context = {
        "previous_results": tool_results,
        "feedback": result_review.iteration_feedback
    }
    plan = await self.orchestrator.create_plan(user_query, context)
```

**Cach 3: StateManager Memory Usage**

```python
# Luu tool results vao session memory
await self.state_manager.add_to_memory(
    session_id, 
    f"tool_results_iter_{current_iteration}", 
    tool_results
)

# Lay ra khi can
previous_results = await self.state_manager.get_from_memory(
    session_id,
    f"tool_results_iter_{current_iteration - 1}"
)
```

### 8.5 Tong ket ve Data Flow

```mermaid
graph LR
    subgraph Iteration 1
        T1[Tool Calls] --> TR1[ToolResults 1]
        TR1 --> C1[Critic Review 1]
        C1 -->|Rejected| F1[Feedback]
    end
    
    subgraph Iteration 2
        Q2[Enhanced Query] --> P2[New Plan]
        P2 --> T2[Tool Calls AGAIN]
        T2 --> TR2[ToolResults 2]
        TR2 --> C2[Critic Review 2]
    end
    
    F1 --> Q2
    TR1 -.->|NOT USED| T2
    
    style TR1 fill:#ffcccc
    style T2 fill:#ffcccc
```

**Ket luan:** Hien tai, du lieu tu tools KHONG duoc tai su dung giua cac iterations. Moi iteration la "clean slate" - goi lai tools tu dau.

---

## 9. Tong ket

He thong Multi-Agent nay hoat dong theo mo hinh **Plan-Execute-Review-Iterate**:

1. **Orchestrator** phan tich yeu cau va lap ke hoach su dung tools
2. **Critic** danh gia ke hoach truoc khi thuc thi
3. **Tools** duoc thuc thi song song/tuan tu
4. **Critic** danh gia ket qua sau thuc thi
5. **AgentLoop** dieu phoi vong lap cho den khi dat ket qua tot hoac het iterations

Diem noi bat cua he thong:
- **Freshness Audit**: Dam bao khong dung kien thuc cu cho du lieu tai chinh
- **Parallel Execution**: Tang toc do thuc thi
- **Self-Correction**: Tu cai thien qua iteration
- **State Persistence**: Luu trang thai vao Supabase