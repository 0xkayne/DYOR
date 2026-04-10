# Memory Enhancement Implementation Plan

> Multi-user, multi-instance distributed checkpointer with intelligent context compression.
>
> **Last updated**: 2026-04-08

---

## Table of Contents

1. [Background & Goals](#1-background--goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Phase 1: Dual-Layer Checkpointer](#3-phase-1--dual-layer-checkpointer)
   - [1.1 RedisSaver Implementation](#31-redissaver-implementation)
   - [1.2 PostgresSaver Implementation](#32-postgressaver-implementation)
   - [1.3 Checkpointer Factory](#33-checkpointer-factory)
   - [1.4 Configuration](#34-configuration)
   - [1.5 Testing](#35-testing)
4. [Phase 2: Memory Selector](#4-phase-2--memory-selector)
   - [2.1 Architecture](#21-architecture)
   - [2.2 Summarization Strategy](#22-summarization-strategy)
   - [2.3 Similarity Recall](#23-similarity-recall)
   - [2.4 Context Assembly](#24-context-assembly)
   - [2.5 Integration with Workflow](#25-integration-with-workflow)
   - [2.6 Testing](#26-testing)
5. [File Inventory](#5-file-inventory)
6. [Risk & Rollback](#6-risk--rollback)

---

## 1. Background & Goals

### Current State

- `src/memory/checkpointer.py` uses `langgraph.checkpoint.memory.MemorySaver`
- Process-local; lost on restart
- No multi-instance support
- No long-term history persistence

### Target State

| Goal | Description |
|------|-------------|
| **Durability** | Session state survives service restarts |
| **Multi-instance** | All instances share the same checkpoint store |
| **Smart context** | LLM only receives carefully selected context, not full history |
| **No data loss** | Long conversations are archived, not truncated |

### Non-Goals

- Not implementing authentication / authorization (handled separately)
- Not migrating existing data from `MemorySaver` (backwards compatibility not required for initial release)

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                         User Request                          │
│              (query + thread_id + optional session_id)        │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                      Memory Selector                          │
│                                                              │
│  1. Load checkpoint chain from RedisSaver (hot)             │
│  2. If cold/missing → load from PostgresSaver               │
│  3. Build session context via summarization                  │
│  4. Recall similar historical sessions via embedding search  │
│  5. Assemble final context → LLM                            │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                         │
│                                                              │
│  checkpoint written on every node transition                 │
│  → RedisSaver (primary, fast read/write)                     │
│  → Archived to PostgresSaver (async, durable)                │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Storage Layer                              │
│                                                              │
│  ┌─────────────────┐         ┌─────────────────────────┐   │
│  │   RedisSaver    │──async──│    PostgresSaver        │   │
│  │  (hot storage)  │ archival│   (cold / durable)      │   │
│  │  TTL: 7 days    │         │   unlimited retention   │   │
│  └─────────────────┘         └─────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

```
[Write Path]
  workflow checkpoint
    → RedisSaver (sync, fast)
    → background task: copy to PostgresSaver (async)

[Read Path (hot)]
  RedisSaver.get(thread_id) → checkpoint

[Read Path (cold)]
  RedisSaver miss
    → PostgresSaver.get(thread_id) → checkpoint
    → RedisSaver.set (re-warm cache)

[Context Assembly Path]
  RedisSaver.get(thread_id)
    → session history
    → Summarizer.compress(long_history)
    → EmbeddingStore.similarity_recall(query, top_k)
    → AssembledContext → LLM
```

---

## 3. Phase 1 — Dual-Layer Checkpointer

### 3.1 RedisSaver Implementation

**File**: `src/memory/checkpointer_redis.py` (new)

**Responsibilities**:
- Wrap `langgraph.checkpoint.redis.RedisSaver`
- Provide singleton factory
- Handle Redis connection lifecycle
- Configure TTL for automatic session expiry

**Key decisions**:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Redis client | `redis.asyncio.Redis` | Async-first; matches FastAPI/uvicorn async model |
| Serialization | JSON (default LangGraph) | No extra dependency; sufficient for state |
| TTL | 7 days | Balance memory usage vs session recovery |
| Connection pool | Singleton connection pool | Avoid connection exhaustion |

**Interface**:

```python
def get_redis_checkpointer(
    redis_url: str = "redis://localhost:6379/0",
    ttl_seconds: int = 604800,  # 7 days
) -> RedisSaver:
    """Return a singleton RedisSaver instance."""
```

**Environment variables**:

```bash
REDIS_URL=redis://localhost:6379/0
REDIS_CHECKPOINTER_TTL=604800  # 7 days in seconds
```

---

### 3.2 PostgresSaver Implementation

**File**: `src/memory/checkpointer_postgres.py` (new)

**Responsibilities**:
- Wrap `langgraph.checkpoint.postgres.PostgresSaver`
- Provide async factory with connection string
- Auto-create schema on first connection
- Handle connection pooling

**Key decisions**:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Driver | `psycopg3` (via LangGraph) | Official LangGraph recommendation |
| Connection | Async connection string | `postgresql+asyncpg://...` or `postgresql://...` |
| Schema migration | LangGraph auto-creates | Migrations managed separately if needed |
| Connection pool | LangGraph-managed | Don't overcomplicate |

**Interface**:

```python
async def get_postgres_checkpointer(
    conn_string: str,  # e.g. "postgresql://user:pass@localhost:5432/dyor"
) -> PostgresSaver:
    """Return a PostgresSaver instance (must be used with async context)."""
```

**Environment variables**:

```bash
POSTGRES_CONN_STRING=postgresql://user:pass@localhost:5432/dyor
```

---

### 3.3 Checkpointer Factory

**File**: `src/memory/checkpointer.py` (modify)

**Changes**: Replace current `MemorySaver` singleton with a factory that returns the appropriate checkpointer based on configuration.

```python
# src/memory/checkpointer.py

from enum import Enum

class CheckpointerBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    POSTGRES = "postgres"
    REDIS_THEN_POSTGRES = "redis_then_postgres"  # dual-layer

def get_checkpointer(
    backend: CheckpointerBackend | None = None,
) -> BaseCheckpointSaver:
    """Return a singleton checkpointer based on configuration.

    If backend is None, reads from settings.checkpointer_backend.
    """
```

**Dual-layer logic** (`RedisThenPostgresSaver`):

LangGraph provides `MultiStore` or the user can configure two separate checkpointer instances. The write path always writes to both; the read path reads from Redis first, falls back to Postgres.

```python
# Write: both savers simultaneously
await asyncio.gather(
    redis_saver.aput(thread_id, checkpoint),
    postgres_saver.aput(thread_id, checkpoint),
)

# Read: Redis first, Postgres fallback
try:
    return await redis_saver.aget(thread_id)
except Exception:
    return await postgres_saver.aget(thread_id)
```

> **Note**: LangGraph 0.2+ has experimental `MultiSaver` / `CompositeSaver` — if stable, use that. Otherwise implement the dual-saver pattern manually.

---

### 3.4 Configuration

**File**: `src/config.py` (modify)

Add new settings:

```python
# Checkpointer
checkpointer_backend: CheckpointerBackend = CheckpointerBackend.MEMORY
redis_url: str = "redis://localhost:6379/0"
redis_ttl_seconds: int = 604800
postgres_conn_string: str = ""

# Memory Selector
memory_selector_backend: str = "local"  # "local" | "embedding"
summarization_threshold: int = 10  # trigger summarization after N messages
similarity_top_k: int = 3  # number of similar sessions to recall
max_context_messages: int = 20  # hard limit on messages fed to LLM
```

---

### 3.5 Testing

**Files** (new):

- `tests/test_memory/test_checkpointer_redis.py`
- `tests/test_memory/test_checkpointer_postgres.py`
- `tests/test_memory/test_dual_checkpointer.py`

**Test matrix**:

| Test | Description | Mock |
|------|-------------|------|
| `test_redis_checkpointer_singleton` | Same instance returned on repeated calls | Mock Redis client |
| `test_redis_checkpointer_write_read` | Write checkpoint → read back identical | Mock Redis |
| `test_postgres_checkpointer_write_read` | Write checkpoint → read back identical | Mock connection |
| `test_dual_write_both_savers` | Write → both Redis and PG receive call | Mock both |
| `test_dual_read_redis_fallback` | Redis miss → PG fallback | Mock Redis (miss) + PG (hit) |
| `test_backend_enum_parsing` | `memory`/`redis`/`postgres` env string → enum | None |
| `test_ttl_config_passed` | TTL from config reaches RedisSaver | Mock Redis |

---

## 4. Phase 2 — Memory Selector

### 4.1 Architecture

```
src/memory/
├── __init__.py
├── checkpointer.py           # Phase 1: dual-layer factory
├── checkpointer_redis.py     # Phase 1: RedisSaver wrapper
├── checkpointer_postgres.py  # Phase 1: PostgresSaver wrapper
├── selector/
│   ├── __init__.py
│   ├── base.py               # AbstractMemorySelector
│   ├── summarizer.py         # Summarization logic
│   ├── recall.py             # Similarity recall via embeddings
│   └── context_assembler.py  # Assembles final context for LLM
```

**`AbstractMemorySelector` interface**:

```python
class AbstractMemorySelector(ABC):
    @abstractmethod
    async def load_context(
        self,
        thread_id: str,
        user_query: str,
        max_tokens: int,
    ) -> list[BaseMessage]:
        """Return compressed message history ready for LLM context."""

    @abstractmethod
    async def archive_session(self, thread_id: str) -> None:
        """Move session from hot (Redis) to cold (Postgres) storage."""
```

---

### 4.2 Summarization Strategy

**File**: `src/memory/selector/summarizer.py`

**Trigger condition**: When `len(messages) > settings.summarization_threshold` (default: 10).

**Algorithm**:

```
Input: full message list from checkpoint
Output: compressed message list

if len(messages) <= threshold:
    return messages  # no compression needed

# Step 1: Separate system/user/assistant messages
system_msgs = [m for m in messages if is_system(m)]
recent_msgs = messages[-threshold:]  # keep last N messages

# Step 2: Generate summary of older messages
older_msgs = messages[:-threshold]
summary_prompt = f"""Summarize this conversation history concisely,
preserving all key facts, user preferences, and conclusions:

{format_messages(older_msgs)}"""

summary_text = await llm.ainvoke(summary_prompt)  # lightweight model

# Step 3: Return [older_summary] + recent_messages
return [
    SystemMessage(content=f"Prior conversation summary: {summary_text}"),
    *recent_msgs,
]
```

**LLM for summarization**: Use `claude-haiku` or the same model with low tokens. Not critical path so can be synchronous in background.

**State schema changes**:

Add to `AgentState` (or a separate `SessionMetadata`):

```python
class SessionMetadata(TypedDict):
    session_id: str
    thread_id: str
    is_summarized: bool
    original_message_count: int
    summary_text: str | None
    created_at: str
    last_updated: str
```

---

### 4.3 Similarity Recall

**File**: `src/memory/selector/recall.py`

**Purpose**: When a new query arrives, find relevant passages from *past sessions* (not just current thread) to inject as context.

**Algorithm**:

```
Input: user_query_embedding (from current query)
       top_k (default 3)
Output: list of relevant historical session snippets

1. Embed user_query using BGE-M3 (same model as RAG)
2. Query vector store (ChromaDB) for top_k similar session chunks
   - Collection: "session_summaries"
   - Metadata filter: exclude current thread_id
3. Return snippets with similarity score
4. Inject into LLM context as "Prior relevant sessions:"
```

**When to trigger similarity recall**: Every new user query (non-replay).

**Session summary embedding**: After each session ends (or every N checkpoints), compute embedding of the session summary and store in ChromaDB:

```python
async def archive_and_index(thread_id: str, summary: str):
    # 1. Archive to Postgres (Phase 1 done)
    await postgres_saver.archive(thread_id)

    # 2. Embed and index for recall
    embedding = await embedding_model.embed([summary])
    vector_store.add_texts(
        texts=[summary],
        embeddings=embedding,
        metadatas=[{"thread_id": thread_id}],
        collection="session_summaries",
    )
```

---

### 4.4 Context Assembly

**File**: `src/memory/selector/context_assembler.py`

Final pipeline that combines all memory signals:

```python
class ContextAssembler:
    def __init__(
        self,
        checkpointer: BaseCheckpointSaver,
        summarizer: Summarizer,
        recall: SimilarityRecall,
        max_context_messages: int = 20,
    ):
        ...

    async def assemble(self, thread_id: str, user_query: str) -> dict:
        """Assemble complete context for a new LLM call.

        Returns:
            dict with keys:
                - messages: list of BaseMessage to inject
                - has_recall: bool (whether recall was added)
                - is_summarized: bool (whether history was compressed)
                - token_count: int (approximate)
        """
        # 1. Load raw checkpoint history
        raw_messages = await self.checkpointer.get_messages(thread_id)

        # 2. Summarize if over threshold
        if len(raw_messages) > self.summarizer.threshold:
            messages = await self.summarizer.compress(raw_messages)
            is_summarized = True
        else:
            messages = raw_messages
            is_summarized = False

        # 3. Recall similar past sessions
        similar_snippets = await self.recall.retrieve(
            query=user_query,
            top_k=self.recall.top_k,
            exclude_thread_id=thread_id,
        )
        has_recall = len(similar_snippets) > 0

        # 4. Inject similar sessions as system context
        if has_recall:
            recall_msg = SystemMessage(
                content=f"Prior relevant sessions:\n" + "\n---\n".join(similar_snippets)
            )
            messages = [recall_msg] + messages

        # 5. Truncate to max_context_messages
        if len(messages) > self.max_context_messages:
            messages = messages[-self.max_context_messages:]

        # 6. Estimate token count (rough: len(chars) / 4)
        token_count = sum(len(m.content) for m in messages) // 4

        return {
            "messages": messages,
            "has_recall": has_recall,
            "is_summarized": is_summarized,
            "token_count": token_count,
        }
```

---

### 4.5 Integration with Workflow

**Changes to `src/graph/workflow.py`**:

Option A — **Inject context at node level** (simpler):
- Modify `run_router` or `run_planner` to call `ContextAssembler.assemble()` before LLM call
- The assembled messages are prepended to the LLM prompt

Option B — **Inject via system prompt** (recommended, less invasive):
- Add assembled context as a `SystemMessage` at the start of `state.messages`
- No changes to individual agent node functions
- Context lives in the message history like any other turn

**Where to integrate**:

```
workflow.py:
  build_workflow(checkpointer)
    → add a new node: "memory_loader"
    → entry point: router
    → memory_loader runs BEFORE router (or as part of router)
    → reads checkpoint → assembles context → injects into state.messages
```

**Minimal change to `src/graph/nodes/router.py`**:

```python
# In run_router, before calling the LLM:
context = await context_assembler.assemble(
    thread_id=config["configurable"]["thread_id"],
    user_query=user_query,
)
# Prepend to messages
state["messages"] = context["messages"] + state["messages"]
```

**Config changes** (`src/config.py`):

```python
memory_selector_enabled: bool = True
summarization_threshold: int = 10
similarity_top_k: int = 3
max_context_messages: int = 20
```

---

### 4.6 Testing

**Files** (new):

- `tests/test_memory/test_summarizer.py`
- `tests/test_memory/test_recall.py`
- `tests/test_memory/test_context_assembler.py`
- `tests/test_memory/test_memory_selector_integration.py`

**Test matrix**:

| Test | Description |
|------|-------------|
| `test_summarize_below_threshold` | 5 messages → returns unchanged |
| `test_summarize_above_threshold` | 15 messages → returns 1 summary + last 10 |
| `test_summarize_preserves_key_facts` | Summary contains entity names from older messages |
| `test_recall_returns_top_k` | Returns exactly top_k similar sessions |
| `test_recall_excludes_current_thread` | Current thread_id never in results |
| `test_assembler_injects_recall` | Recall snippets added as SystemMessage |
| `test_assembler_truncates_to_max` | Messages truncated when over max_context_messages |
| `test_assembler_token_estimate` | Token count roughly accurate (±20%) |
| `test_workflow_injects_context_on_rerun` | Second invoke with same thread_id gets assembled context |

---

## 5. File Inventory

### Phase 1 — New Files

| File | Purpose |
|------|---------|
| `src/memory/checkpointer_redis.py` | RedisSaver factory and wrapper |
| `src/memory/checkpointer_postgres.py` | PostgresSaver factory and wrapper |
| `tests/test_memory/test_checkpointer_redis.py` | Redis checkpointer tests |
| `tests/test_memory/test_checkpointer_postgres.py` | Postgres checkpointer tests |
| `tests/test_memory/test_dual_checkpointer.py` | Dual-layer tests |

### Phase 1 — Modified Files

| File | Change |
|------|--------|
| `src/memory/checkpointer.py` | Replace `MemorySaver` singleton with factory |
| `src/config.py` | Add `checkpointer_backend`, `redis_url`, `redis_ttl_seconds`, `postgres_conn_string` |
| `.env.example` | Add new env vars |

### Phase 2 — New Files

| File | Purpose |
|------|---------|
| `src/memory/selector/__init__.py` | Package init, exports |
| `src/memory/selector/base.py` | `AbstractMemorySelector` |
| `src/memory/selector/summarizer.py` | Summarization logic |
| `src/memory/selector/recall.py` | ChromaDB-backed similarity recall |
| `src/memory/selector/context_assembler.py` | Full context assembly pipeline |
| `src/memory/session_store.py` | Session metadata + session_summaries ChromaDB collection |
| `tests/test_memory/test_summarizer.py` | Summarizer tests |
| `tests/test_memory/test_recall.py` | Recall tests |
| `tests/test_memory/test_context_assembler.py` | Assembler tests |

### Phase 2 — Modified Files

| File | Change |
|------|--------|
| `src/graph/state.py` | Add `SessionMetadata` to state (optional) |
| `src/graph/nodes/router.py` | Call `ContextAssembler.assemble()` before LLM call |
| `src/config.py` | Add `memory_selector_enabled`, `summarization_threshold`, `similarity_top_k`, `max_context_messages` |
| `src/rag/ingest.py` | Add `session_summaries` ChromaDB collection initialization |

---

## 6. Risk & Rollback

### Phase 1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Postgres connection failure on startup | Medium | Service won't start | Fallback to MemorySaver if `postgres_conn_string` empty |
| Redis unavailable | Medium | Checkpoint writes fail; read path falls back to PG | Graceful degradation: if Redis down, reads from PG directly |
| Dual-write performance regression | Low | 2x write latency per checkpoint | Use `asyncio.gather` for parallel writes; Redis is async |
| Breaking existing session continuity | Low | Old session_ids incompatible | Existing `MemorySaver` data is lost; acceptable per non-goals |

### Phase 2 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Summarization LLM call adds latency | Medium | First message after long session is slow | Run summarization async / after session ends |
| Recall returns irrelevant context | Low | Pollutes LLM context | Score threshold filter: skip if similarity < 0.7 |
| Context size miscalculation | Medium | Token overflow in LLM | Hard truncate at `max_context_messages` + estimate check |
| ChromaDB session collection grows unbounded | Medium | Recall quality degrades | Periodic cleanup: delete sessions older than 90 days |

### Rollback Plan

If Phase 2 causes issues in production:

1. Set `memory_selector_enabled = False` in `.env`
2. Restart service
3. Context assembly is bypassed; workflow uses raw checkpoint history
4. Phase 1 (dual checkpointer) remains active independently

If Phase 1 causes issues in production:

1. Set `checkpointer_backend = memory` in `.env`
2. Restart service
3. Falls back to `MemorySaver`; no persistence but service works
4. Investigate Redis/Postgres connectivity separately

---

## Appendix: LangGraph Checkpointer Reference

### RedisSaver

```python
from langgraph.checkpoint.redis import RedisSaver
from redis.asyncio import Redis

redis_client = Redis.from_url("redis://localhost:6379/0")
checkpointer = RedisSaver(redis_client)
app = graph.compile(checkpointer=checkpointer)
```

### PostgresSaver

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost:5432/dyor"
)
app = graph.compile(checkpointer=checkpointer)
```

### MultiSaver (if available in installed LangGraph version)

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import RedisSaver
from langgraph.checkpoint.saver import MultiSaver

# Write to both; read from first that has the data
saver = MultiSaver([RedisSaver(redis_client), PostgresSaver(conn_string)])
```

---

*End of document*
