# LangGraph Design: Supervisor-Worker Architecture

This document describes the **Supervisor Pattern** implementation for the Multi-Agent Interview Assistant. This is a more advanced LangGraph pattern where a central "Manager" agent controls the lifecycle of the interview.

## 1. Design Overview

Unlike a simple linear flow, the **Supervisor Pattern** allows for dynamic, intent-based orchestration. The Supervisor acts as the "Top-Level Agent" that instructs specialized modules when to perform their specific tasks.

### Graph Architecture
1.  **Orchestrator Node (Supervisor)**: A high-level LLM node that decides the "Next Action".
2.  **Specialized Workers**:
    *   **Research Worker**: Profile verification.
    *   **KPI Worker**: Role-based benchmarking.
    *   **Interview Worker**: Technical evaluation.
    *   **Feedback Worker**: Performance reporting.

---

## 2. Visual Workflow (Supervisor Pattern)

```mermaid
graph TD
    %% User input initiates the cycle
    USER([User Input]) --> SUPERVISOR{<b>Supervisor Agent</b><br/>(The Decision Maker)}

    %% Routing logic
    SUPERVISOR -- "Instructs" --> RESEARCH[<b>Research Agent</b>]
    SUPERVISOR -- "Instructs" --> KPI[<b>KPI Agent</b>]
    SUPERVISOR -- "Instructs" --> INTERVIEW[<b>Interviewer Agent</b>]
    SUPERVISOR -- "Instructs" --> EVAL[<b>Feedback Agent</b>]

    %% Feedback loop: Workers always report back to the Manager
    RESEARCH --> SUPERVISOR
    KPI --> SUPERVISOR
    INTERVIEW --> SUPERVISOR
    EVAL --> SUPERVISOR

    %% Termination logic
    SUPERVISOR -- "Task Finished" --> FINISH((● End Session))

    %% Colors for clarity
    style SUPERVISOR fill:#ffcc80,stroke:#ef6c00,stroke-width:2px
    style RESEARCH fill:#e1f5fe,stroke:#01579b
    style INTERVIEW fill:#e8f5e9,stroke:#1b5e20
    style EVAL fill:#ffebee,stroke:#b71c1c
```

---

## 3. The State Schema

We use a unified `HistoryState` that allows the Supervisor to see everything that has happened so far.

```python
class InterviewTeamState(TypedDict):
    # A list of messages that represents the chat history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Metadata for worker coordination
    last_worker: str
    phase_logs: Dict[str, str]
    ready_for_kpi: bool
```

---

## 4. Key Improvements over Linear Design

1.  **Intent-Driven Routing**: If a user asks to skip research and go straight to the interview, the **Supervisor** can decide to fulfill that request, whereas a linear flow would be stuck.
2.  **Centralized Control**: The Supervisor has a comprehensive view of the entire conversation, reducing the risk of redundant questions.
3.  **Modular Workers**: Each agent can be developed and tested independently, as they only need to "talk" to the Supervisor.
