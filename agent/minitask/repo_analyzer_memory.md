
## 2026-07-01 09:38:52
**User:** 分析 agent/03-skills-mcp/agent-skills-mcp.py，讲清楚 tools schema 是怎么加载和执行的
**Agent:** 现在我有了完整的信息，可以给你一个全面的分析。

---

## `agent-skills-mcp.py` Tools Schema 加载与执行全链路

整个文件 379 行，tools schema 的生命周期分 **三个来源、四个阶段**：

---

### 一、三种 Tools Schema 来源

#### 1. Base Tools（硬编码，第 22–109 行）

```python
base_tools = [
    {"type": "function", "function": {"name": "read", ...}},
    {"type": "function", "function": {"name": "write", ...}},
    {"type": "function", "function": {"name": "edit", ...}},
    {"type": "function", "function": {"name": "glob", ...}},
    {"type": "function", "function": {"name": "grep", ...}},
    {"type": "function", "function": {"name": "bash", ...}},
]
```

这是 6 个内置工具，每个都符合 OpenAI Function Calling 的 schema 格式：`{"type": "function", "function": {name, description, parameters}}`。它们是直接写在代码里的 Python 列表。

#### 2. MCP Tools（从 `.agent/mcp.json` 加载，第 291–305 行）

```python
