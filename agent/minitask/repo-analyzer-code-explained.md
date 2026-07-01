# 代码说明：为什么这版更像通用 Agent

这版 `agent-repo-analyzer.py` 参考了 `agent/03-skills-mcp/agent-skills-mcp.py` 的结构，把“能力”从主流程里拆出来。

当前 LLM 配置支持 OneAPI 这类非标准鉴权头：

- `base_url` 写到 `/v1`，不要包含 `/chat/completions`。
- `authorization_scheme` 为 `"Bearer"` 时发送 `Authorization: Bearer <key>`。
- `authorization_scheme` 为空字符串时发送 `Authorization: <key>`。

核心不再是：

```text
固定流程 -> 分析仓库 -> 写 Markdown 报告
```

而是：

```text
通用 Agent Loop
  + Rules
  + Skills
  + MCP tools
  + 多轮交互上下文
```

## 1. Rules

Rules 放在：

```bash
agent/minitask/.agent/rules/interactive-agent.md
```

启动时 `load_rules()` 会读取这些规则并注入 system prompt。

当前规则要求：

- 默认在聊天里回答
- 不主动写 Markdown 报告
- 分析代码时引用文件和行号
- 用户只要求解释时不要改文件

## 2. Skills

仓库分析能力被抽象成 Skill：

```bash
agent/minitask/.agent/skills/python-agent-analysis/SKILL.md
```

它告诉 Agent：

1. 什么时候使用这个技能
2. 应该先调用哪个工具
3. 如何识别 tools schema、tool invocation、agent loop、subagent
4. 默认在对话里回答

也就是说，Agent 的核心代码不再写死“必须分析仓库”。它只是读到一个 Skill，于是在相关任务里学会调用对应工具。

## 3. MCP 工具

MCP 风格工具 schema 放在：

```bash
agent/minitask/.agent/mcp.json
```

里面声明了：

- `scan_python_repo`
- `summarize_python_file`
- `read_code_excerpt`
- `extract_agent_features`
- `explain_agent_feature`

这些工具的 Python 实现在 `agent-repo-analyzer.py` 里，并注册到：

```python
MCP_FUNCTIONS = {
    "scan_python_repo": scan_python_repo,
    ...
}
```

这和 `03-skills-mcp` 的教学思路一致：MCP 配置提供工具 schema，Python 侧提供实际实现。

## 4. Tool Schema 转换

`BASE_TOOLS` 和从 `mcp.json` 读出来的工具都是 OpenAI function schema 风格：

```python
{
    "type": "function",
    "function": {
        "name": "...",
        "description": "...",
        "parameters": {...}
    }
}
```

LangChain 的 `ChatOpenAI.bind_tools()` 可以直接绑定这些 schema。

当模型返回 `tool_calls` 后，代码通过工具名从 `AVAILABLE_FUNCTIONS` 找到真实 Python 函数并执行。

## 5. Agent Loop

核心循环仍然很小：

```python
message = llm_with_tools.invoke(messages)
messages.append(message)

if not message.tool_calls:
    return message.content

for tool_call in message.tool_calls:
    result = call_tool(tool_call)
    messages.append(ToolMessage(result, tool_call_id=tool_call["id"]))
```

这就是 Agent 的本体：

1. 模型看上下文
2. 模型决定是否调用工具
3. Python 执行工具
4. 工具结果放回 messages
5. 重复直到模型直接回答

## 6. 子 Agent

`explain_agent_feature` 是一个 MCP 工具，但它内部会拉起一个小的代码阅读子 Agent：

```python
messages = [
    SystemMessage(content="You are a code reading sub-agent..."),
    HumanMessage(content="关注点 + 代码片段")
]
```

它有独立上下文，只负责解释某个聚焦问题，比如：

- tool 调用链
- subagent 交互
- agent loop

这保留了“主 Agent 调度子 Agent”的机制，但不会让主循环变复杂。

## 7. 如何继续扩展

`agent/full` 里的两个耐用性能力也被吸收进来了：

- 工具输出截断：避免一次工具结果把上下文塞爆。
- 上下文压缩：超过阈值后把旧消息总结成摘要，保留最近几轮细节；也可以手动输入 `/compact`。

扩展一个新能力时，优先新增：

1. 一个 Skill：描述什么时候用、怎么用
2. 一组 MCP tool schema：暴露给模型
3. 对应 Python 函数：真正执行工具

主 Agent 的 loop 不需要改。这样它就从“专用脚本”变成了“可持续挂载能力的通用 Agent”。
