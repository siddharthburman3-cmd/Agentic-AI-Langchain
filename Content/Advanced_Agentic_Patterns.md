# Advanced Agentic AI Patterns

## Overview

This document covers four advanced patterns for building robust, production-grade agentic systems using LangChain. These patterns move beyond single-agent, static-tool setups toward systems that adapt their behaviour at runtime based on context, conversation state, and user identity.

---

## 1. Multi-Agent Systems (`13_multi_agent.ipynb`)

### Concept

A **multi-agent system** decomposes a complex task by delegating subtasks to specialised sub-agents, each with its own tools and instructions. A **main (orchestrator) agent** receives the user's request, decides which sub-agent to call, and assembles the final answer.

### Architecture

```
User Request
     │
     ▼
Main Agent (orchestrator)
     │            │
     ▼            ▼
Sub-Agent 1   Sub-Agent 2
(square root) (square)
```

### Key Mechanics

- **Sub-agents as tools**: Each sub-agent is wrapped in a `@tool`-decorated function. From the orchestrator's perspective, calling a sub-agent is identical to calling any other tool — it sends a `HumanMessage` and reads the last message of the response.
- **Isolation of capability**: Each sub-agent only has the tools it needs. Sub-agent 1 only knows how to compute square roots; Sub-agent 2 only knows how to compute squares. This prevents capability leakage and keeps each agent's decision space small.
- **Delegation via natural language**: The orchestrator does not hard-code which sub-agent handles which query. It reasons from tool descriptions and delegates accordingly.

### Why This Matters

| Concern | Single-agent approach | Multi-agent approach |
|---|---|---|
| Tool overload | Agent must reason across all tools | Each agent reasons over a focused set |
| Specialisation | General purpose, may drift | Each sub-agent is an expert |
| Scalability | Adding tools increases context noise | Add new sub-agents without affecting others |
| Testability | Hard to isolate failures | Each agent can be tested independently |

### Pattern Summary

```python
# 1. Define specialist tools
@tool
def square_root(x: float) -> float: ...

# 2. Create sub-agents with specialist tools
subagent_1 = create_agent(model=..., tools=[square_root])

# 3. Wrap sub-agents as tools for the orchestrator
@tool
def call_subagent_1(x: float) -> float:
    response = subagent_1.invoke({"messages": [HumanMessage(...)]})
    return response["messages"][-1].content

# 4. Create the orchestrator with sub-agent tools
main_agent = create_agent(model=..., tools=[call_subagent_1, call_subagent_2])
```

---

## 2. Dynamic Model Selection (`14.1_dynamic_models.ipynb`)

### Concept

Rather than binding an agent to a single model for its lifetime, **dynamic model selection** uses middleware to swap the underlying model on a per-request basis. The choice of model is made at inference time using any observable signal from the request or conversation state.

### Why Different Models?

Different models offer different trade-offs:

| Factor | Lightweight model (e.g. gpt-5-nano) | Powerful model (e.g. gpt-5.5) |
|---|---|---|
| Cost | Lower | Higher |
| Latency | Faster | Slower |
| Context window | Smaller | Larger |
| Reasoning depth | Adequate for simple tasks | Better for complex, long conversations |

Dynamically routing between them lets you **optimise cost and quality simultaneously** rather than picking one for all cases.

### Middleware: `@wrap_model_call`

The `@wrap_model_call` decorator intercepts every call the agent makes to its model. The middleware function receives:
- `request` — the full model request, including all messages and current state
- `handler` — the function that actually calls the model; the middleware must invoke it to produce a response

The middleware can inspect the request, override properties (like which model to use), and then pass the (modified) request to the handler.

### Decision Signal: Conversation Length

In this example, the middleware reads `len(request.messages)`:
- **≤ 10 messages** → use the lightweight `standard_model`
- **> 10 messages** → switch to `large_model` with a larger context window

```python
@wrap_model_call
def state_based_model(request: ModelRequest,
                      handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
    message_count = len(request.messages)
    model = large_model if message_count > 10 else standard_model
    request = request.override(model=model)
    return handler(request)
```

### Key Design Principle

The agent definition (`create_agent`) still names a default model — this acts as a fallback and makes the agent self-describing. The middleware is additive; it can choose to leave the model unchanged or override it. The agent code itself never changes.

---

## 3. Dynamic Prompts (`14.2_dynamic_prompts.ipynb`)

### Concept

A **dynamic system prompt** is generated at runtime rather than written once at agent creation. The prompt adapts based on contextual signals — in this case, the user's preferred language — making the agent's persona and constraints contextually appropriate.

### Runtime Context

LangChain's `context_schema` mechanism allows you to pass structured, typed data to the agent at invocation time (via `agent.invoke(..., context=...)`). This context is available inside middleware through `request.runtime.context`.

```python
@dataclass
class LanguageContext:
    user_language: str = "English"
```

The context object is defined as a dataclass with clear types and defaults. It travels with the request through the middleware stack without polluting the message history.

### `@dynamic_prompt` Decorator

The `@dynamic_prompt` decorator marks a function as a system-prompt generator. It receives the full `ModelRequest` (and thus the runtime context) and returns a string that becomes the system prompt for that specific invocation.

```python
@dynamic_prompt
def user_language_prompt(request: ModelRequest) -> str:
    user_language = request.runtime.context.user_language
    base_prompt = "You are a helpful assistant."
    if user_language != "English":
        return f"{base_prompt} only respond in {user_language}."
    return base_prompt
```

### Invocation

```python
# Agent responds in Irish
agent.invoke({"messages": [...]}, context=LanguageContext(user_language="Irish"))

# Agent responds in Spanish
agent.invoke({"messages": [...]}, context=LanguageContext(user_language="Spanish"))
```

### Why Not Just Prepend to the User Message?

Injecting instructions into the user message breaks the conversational structure and can confuse the model. A proper system prompt is applied by the model with higher authority — it frames the model's entire behaviour, not just a single turn.

### Use Cases Beyond Language

The same pattern applies to any persona- or constraint-shaping signal:
- User role (admin vs. read-only)
- Tenant/brand (customise tone per client)
- Regulatory regime (add compliance disclaimers)
- Expertise level (simplify explanations for beginners)

---

## 4. Dynamic Tool Access (`14.3_dynamic_tools.ipynb`)

### Concept

**Dynamic tool access** gates which tools an agent can use based on runtime context — typically the identity or role of the calling user. Instead of giving all users the same capabilities, the middleware restricts the available tool set to what that user is authorised to use.

### Motivation

In a production system, different users have different trust levels. Exposing internal database queries (`sql_query`) to external users would be a security risk. But replicating the agent definition for each role leads to duplication and maintenance burden. Dynamic tool access solves both problems in one place.

### Implementation

The agent is created with the **full set of tools** it might ever need:

```python
agent = create_agent(
    model="gpt-5-nano",
    tools=[web_search, sql_query],   # Full capability set
    middleware=[dynamic_tool_call],
    context_schema=UserRole
)
```

The middleware intercepts each model call and overrides the tool list based on the user's role:

```python
@wrap_model_call
def dynamic_tool_call(request: ModelRequest,
                      handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse:
    user_role = request.runtime.context.user_role
    if user_role != "internal":
        request = request.override(tools=[web_search])  # Restrict to safe tools
    return handler(request)
```

### Access Matrix

| User Role | `web_search` | `sql_query` |
|---|---|---|
| `internal` | Yes | Yes |
| `external` | Yes | No |

### Key Properties

- **Single agent definition**: One `create_agent` call serves all roles. No forking of agent logic.
- **Fail-safe default**: If the role is anything other than `"internal"`, access is restricted. Unknown roles are treated as external.
- **Enforcement at the model boundary**: The restriction happens before the model is called, so the model cannot reason about or attempt to call tools it does not know about. This is stronger than post-hoc filtering.

---

## Cross-Cutting Themes

### The Middleware Stack

All three dynamic patterns (models, prompts, tools) use the same middleware mechanism. This is a deliberate design: middleware is composable. You can chain multiple middleware functions together, each handling one concern:

```python
agent = create_agent(
    model="gpt-5-nano",
    tools=[...],
    middleware=[
        state_based_model,      # Dynamic model selection
        user_language_prompt,   # Dynamic prompt
        dynamic_tool_call,      # Dynamic tool access
    ]
)
```

Each middleware function is called in order, can read and modify the request, and must pass it to the next handler.

### Runtime Context as the Signal Bus

The `context` object (passed at `.invoke()` time) is the primary vehicle for communicating runtime facts to middleware. It is:
- **Typed**: defined as a dataclass, preventing accidental misuse
- **Immutable from the model's perspective**: the model never sees it directly; only middleware reads it
- **Decoupled**: the agent definition does not need to know what context will be passed at runtime

### When to Use Each Pattern

| Pattern | Use When |
|---|---|
| **Multi-agent** | A task decomposes into distinct subtasks with different tools or expertise requirements |
| **Dynamic model** | You want to balance cost and capability based on observable signals (length, complexity, user tier) |
| **Dynamic prompt** | The agent's persona, language, or constraints should vary per invocation context |
| **Dynamic tools** | Different users or roles should have access to different capabilities from a shared agent |

These patterns are not mutually exclusive — a production agentic system will typically combine all four.
