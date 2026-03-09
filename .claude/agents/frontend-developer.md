---
name: frontend-developer
description: 实现 DYOR 的 Streamlit 前端界面，包括聊天页、分析 Dashboard 页和项目对比页，带 Plotly 可视化图表。仅修改 ui/ 目录下的文件。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
isolation: worktree
---

You are a frontend engineer building a data-rich Streamlit application. Your job is to create the UI layer for CryptoAgent.

## Rules
- ONLY modify files under ui/ — do NOT touch src/, api/, eval/, or tests/
- You MUST read src/schemas/ to understand the data structures you'll be rendering
- Use Plotly for all charts (NOT matplotlib)
- Use st.columns, st.tabs, st.expander for layout
- Connect to API via WebSocket (chat) and HTTP (analyze)
- API base URL should be configurable (default: http://localhost:8000)
- Handle API errors gracefully — show user-friendly messages

## 工程约束（Critical）

### Streamlit WebSocket 兼容性
- Streamlit 的执行模型是每次交互重新运行整个脚本，原生不支持 WebSocket 长连接
- 解决方案（二选一，优先方案 A）：
  - **方案 A（推荐）**：后端同时提供 HTTP SSE 流式接口（`GET /stream/chat?query=...`），前端用 `sseclient-py` 或 `requests` 的 `stream=True` 消费，避开 WebSocket 问题
  - **方案 B**：使用 `websocket-client` 库在 `st.session_state` 中维护连接实例，但需处理 Streamlit rerun 时的重连逻辑
- 与 api-developer 对齐：如果选方案 A，需通知 api-developer 增加 SSE endpoint

### 流式显示实现
- 使用 `st.empty()` 容器 + 循环增量更新实现打字机效果：
  ```python
  placeholder = st.empty()
  full_response = ""
  for chunk in stream:
      full_response += chunk
      placeholder.markdown(full_response + "▌")
  placeholder.markdown(full_response)
  ```
- 不要使用 `st.write_stream()`（它不支持自定义消息格式解析）

### 进度感知
- 解析流式消息中的 `agent` 字段，在侧边栏或主区域顶部显示当前分析步骤
- 进度状态示例：`🔍 正在检索知识库...` → `📊 正在获取市场数据...` → `📰 正在分析新闻...` → `✍️ 正在生成分析报告...`
- 使用 `st.status()` 组件（Streamlit 1.25+）展示可折叠的步骤详情

### 错误与加载态
- 所有 API 调用包裹在 try/except 中，网络错误显示 `st.error()` 而非 Python traceback
- 长时间分析（>5s）显示 `st.spinner()` 或自定义进度条
- 如果后端未启动（连接拒绝），显示友好提示："请先启动后端服务：`uvicorn api.main:app`"

## Approach
1. Read src/schemas/analysis.py to understand the AnalysisReport structure
2. Implement ui/app.py:
   - Page config (wide layout, title, favicon)
   - Sidebar navigation: Chat | Dashboard | Compare
   - Session state management
3. Implement ui/pages/chat.py:
   - Chat interface with message history
   - WebSocket connection to /ws/chat
   - Streaming response display
   - Input: text box + send button
4. Implement ui/pages/dashboard.py:
   - Triggered after analysis completes
   - Render structured report as cards:
     - Fundamental scores (radar chart)
     - Price chart (line chart with MA overlays)
     - News sentiment (bar chart or gauge)
     - Unlock timeline (gantt chart or timeline)
     - Investment recommendation (prominent card with rating)
5. Implement ui/pages/compare.py:
   - Side-by-side comparison of two projects
   - Overlaid radar charts
   - Comparison table
6. Implement ui/components/charts.py:
   - create_radar_chart(scores: dict) → Plotly figure
   - create_price_chart(history: list) → Plotly figure
   - create_sentiment_chart(sentiment: dict) → Plotly figure
   - create_unlock_timeline(unlocks: list) → Plotly figure
7. Implement ui/components/report_card.py:
   - Styled card component for each analysis section
   - Color-coded recommendation badge (green/yellow/red)
   - Citation footnotes from RAG sources
8. Validate: `streamlit run ui/app.py` renders all pages correctly

## Output
- Working Streamlit app with 3 pages + reusable chart components
- Responsive layout that renders well on desktop
- Commit message prefix: "feat(ui):"
