# 进阶任务用法：交互式可扩展 Agent

`agent-repo-analyzer.py` 现在不是固定“输出 Markdown 报告”的脚本，而是一个更像 Claude Code 的交互式 Agent。

它启动时会加载：

- Rules：`agent/minitask/.agent/rules/*.md`
- Skills：`agent/minitask/.agent/skills/*/SKILL.md`
- MCP 工具 schema：`agent/minitask/.agent/mcp.json`

Python Agent 仓库分析能力被做成了一个 Skill：

```bash
agent/minitask/.agent/skills/python-agent-analysis/SKILL.md
```

配套 MCP 风格工具在：

```bash
agent/minitask/.agent/mcp.json
```

## 准备环境

```bash
cd /Users/dyy/Documents/nanoAgent-book
source .venv/bin/activate
export OPENAI_API_KEY="你的 DeepSeek key"
```

配置文件：

```bash
agent/minitask/repo_analyzer_config.json
```

默认使用：

```json
{
  "model": "deepseek-v4-pro",
  "base_url": "https://api.deepseek.com"
}
```

## 交互式运行

```bash
python agent/minitask/agent-repo-analyzer.py
```

进入后可以问：

```text
分析 agent/03-skills-mcp/agent-skills-mcp.py，讲清楚 tools schema 是怎么加载和执行的
```

```text
看 agent/full 的 agent loop，解释 tool result 是怎么回填到 messages 的
```

```text
解释 agent/04-subagent 的子 agent 调度流程
```

默认只在对话里回答，不写 Markdown 文件。只有你明确要求“写到某个文件”时，Agent 才会使用 `write` 工具。

## 一次性提问

```bash
python agent/minitask/agent-repo-analyzer.py "分析 agent/full 里的 agent loop 和 subagent 交互"
```

## 内置命令

```text
/help    查看示例
/status  查看已加载 Rules / Skills / MCP tools
/compact 压缩当前上下文
/clear   清空当前上下文
/exit    退出
```

## 怎么扩展成通用 Agent

新增一个 Skill：

```bash
agent/minitask/.agent/skills/your-skill/SKILL.md
```

在 `SKILL.md` 里写 frontmatter：

```markdown
---
name: your-skill
description: What this skill does
when_to_use: When the agent should use this skill
triggers: keyword1, keyword2
---

具体工作流程...
```

新增 MCP 工具：

1. 在 `agent/minitask/.agent/mcp.json` 里加工具 schema。
2. 在 `agent-repo-analyzer.py` 里实现同名 Python 函数。
3. 把函数注册到 `MCP_FUNCTIONS`。

这样主 Agent 不需要改核心 loop，只是多加载一个 Skill 和一组工具。
