# 从零开始理解 Agent —— 系列导读

[English](./README_CN.md) | 中文

> 通过一个极简开源项目 [nanoAgent](https://github.com/GitHubxsy/nanoAgent)，逐层拆解 OpenClaw / Claude Code 等 AI Agent 背后的全部核心概念。

## 这个系列讲什么

很多人会用 ChatGPT，但不理解 Agent。这个系列从一个仅 **103 行**的极简实现出发，每篇增加一个核心能力，最终搭建出涵盖记忆、规划、工具扩展、多智能体、安全等所有关键特性的完整 Agent。

**一句话总结：** Agent = LLM + 工具 + 循环。理解了这个，你就理解了 Claude Code、Cursor、Devin 的底层。

---

## 正篇：七篇文章 × 七个代码文件

| # | 目录 | 文章 | 配套代码 | 行数 | 核心主题 |
|---|------|------|----------|------|----------|
| 01 | [01-essence/](./01-essence/) | [OpenClaw / Claude Code 的底层原理，只有 100 行](./01-essence/agent-essence.md) | [`agent-essence.py`](./01-essence/agent-essence.py) | 103 行 | 工具 + 循环，Agent 最小实现 |
| 02 | [02-memory/](./02-memory/) | [OpenClaw / Claude Code 如何实现记忆与规划](./02-memory/agent-memory.md) | [`agent-memory.py`](./02-memory/agent-memory.py) | 206 行 | 持久记忆、任务分解规划 |
| 03 | [03-skills-mcp/](./03-skills-mcp/) | [OpenClaw / Claude Code 的 Rules、Skills 与 MCP 机制](./03-skills-mcp/agent-skills-mcp.md) | [`agent-skills-mcp.py`](./03-skills-mcp/agent-skills-mcp.py) | 282 行 | 行为规则、技能复用、MCP 协议 |
| 04 | [04-subagent/](./04-subagent/) | [给 Agent 找个帮手——最简 SubAgent 实现](./04-subagent/agent-subagent.md) | [`agent-subagent.py`](./04-subagent/agent-subagent.py) | 192 行 | 一次性子智能体，任务委派 |
| 05 | [05-teams/](./05-teams/) | [从临时工到正式团队——多智能体协作与编排](./05-teams/agent-teams.md) | [`agent-teams.py`](./05-teams/agent-teams.py) | 270 行 | 持久 Agent、身份管理、团队通信 |
| 06 | [06-compact/](./06-compact/) | [Agent 的一次断舍离——上下文压缩](./06-compact/agent-compact.md) | [`agent-compact.py`](./06-compact/agent-compact.py) | 169 行 | 自动摘要压缩，防止 Context 爆炸 |
| 07 | [07-safety/](./07-safety/) | [Agent 执行 rm -rf / 怎么办？三道安全防线](./07-safety/agent-safe.md) | [`agent-safe.py`](./07-safety/agent-safe.py) | 219 行 | 命令黑名单、人工确认、输出截断 |
| — | [full/](./full/) | [七篇合一](./full/agent-full.md) | [`agent-full.py`](./full/agent-full.py) | 507 行 | 完整集成版，包含所有能力 |

### 番外篇

| # | 目录 | 文章 | 配套代码 |
|---|------|------|----------|
| 08 | [08-filesystem/](./08-filesystem/) | [为什么 Agent 需要一个文件系统？](./08-filesystem/nanoAgent-bonus-filesystem.md) | — |
| 09 | [09-token/](./09-token/) | [Token 都花在哪了？](./09-token/nanoAgent-bonus-token.md) | — |
| 10 | [10-tool-selection/](./10-tool-selection/) | [LLM 是怎么从一堆工具里挑出正确的那个的？](./10-tool-selection/nanoAgent-bonus-tool-selection.md) | — |
| 11 | [11-streaming/](./11-streaming/) | [Agent 思考时，用户在干等](./11-streaming/nanoAgent-bonus-streaming.md) | [`agent-stream.py`](./11-streaming/agent-stream.py) |
| 12 | [12-command/](./12-command/) | [Command——不是所有操作都要过大脑](./12-command/nanoAgent-bonus-command.md) | [`agent-command.py`](./12-command/agent-command.py) |
| 13 | [13-observable/](./13-observable/) | [Agent 出了问题怎么排查？](./13-observable/nanoAgent-bonus-observable.md) | [`agent-observable.py`](./13-observable/agent-observable.py) |
| 14 | [14-eval/](./14-eval/) | [Agent 怎么知道自己做完了？](./14-eval/nanoAgent-bonus-eval.md) | — |
| 15 | [15-agent-creation-modes/](./15-agent-creation-modes/) | [谁来创建 Agent？](./15-agent-creation-modes/nanoagent-bonus-agent-creation-modes.md) | [`agent-preset.py`](./15-agent-creation-modes/agent-preset.py) |
| 16 | [16-mcp-real/](./16-mcp-real/) | [真正的 MCP 长什么样？](./16-mcp-real/nanoagent-bonus-mcp-real.md) | [`nano_mcp_http_server.py`](./16-mcp-real/nano_mcp_http_server.py)、[`nano_mcp_http_agent.py`](./16-mcp-real/nano_mcp_http_agent.py) |

---

## 推荐阅读路径

### 路径 A：从头到尾（推荐新手）

```
01-essence → 02-memory → 03-skills-mcp → 04-subagent → 05-teams → 06-compact → 07-safety
  essence.py  memory.py   skills-mcp.py    subagent.py   teams.py   compact.py   safe.py
```

每篇都建立在前一篇基础上，逐层添加新特性。

### 路径 B：按需跳入（推荐有基础的读者）

- 只想理解 **Agent 原理** → [01-essence/](./01-essence/)
- 想让 Agent **记住历史** → [02-memory/](./02-memory/)
- 想接入 **MCP / 自定义工具** → [03-skills-mcp/](./03-skills-mcp/)
- 想做 **并行任务分解** → [04-subagent/](./04-subagent/)
- 想做 **多 Agent 协作** → [05-teams/](./05-teams/)
- 担心 **Context 爆满** → [06-compact/](./06-compact/)
- 担心 **Agent 搞破坏** → [07-safety/](./07-safety/)
- 想要**一个文件搞定所有** → [full/](./full/)

### 路径 C：只看代码

每个目录下都有对应的 `.py` 文件，文件顶部 docstring 是该篇章的摘要。

---

## 各篇章核心概念速查

| 概念 | 出现篇章 | 关键代码位置 |
|------|----------|--------------|
| Tool Schema / Function Calling | 第一篇 | `01-essence/agent-essence.py:16-60` |
| Agent Loop（核心循环） | 第一篇 | `01-essence/agent-essence.py:62-100` |
| 持久记忆（Persistent Memory） | 第二篇 | `02-memory/agent-memory.py:99-117` |
| 任务规划（Planning） | 第二篇 | `02-memory/agent-memory.py:119-142` |
| Rules（行为规则） | 第三篇 | `03-skills-mcp/agent-skills-mcp.py:143-153` |
| Skills（可复用技能） | 第三篇 | `03-skills-mcp/agent-skills-mcp.py:155-165` |
| MCP 工具加载 | 第三篇 | `03-skills-mcp/agent-skills-mcp.py:167-181` |
| SubAgent（子智能体） | 第四篇 | `04-subagent/agent-subagent.py:81-110` |
| 多智能体通信 | 第五篇 | `05-teams/agent-teams.py` |
| Context 压缩 | 第六篇 | `06-compact/agent-compact.py:80-123` |
| 安全黑名单 | 第七篇 | `07-safety/agent-safe.py` |

---

## 安装与快速上手

```bash
git clone https://github.com/GitHubxsy/nanoAgent.git
cd nanoAgent
pip install -r agent/requirements.txt

export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 或 DeepSeek/Qwen 等

# 从第一篇开始
python agent/01-essence/agent-essence.py "列出当前目录下所有 Python 文件"

# 带记忆的版本
python agent/02-memory/agent-memory.py "统计代码行数并记住结果"

# 完整版（集成所有特性）
python agent/full/agent-full.py "重构 hello.py，添加类型注解和单元测试"
```

---

## 许可证

MIT

────────────────────────────────────────

⏺ *如同一粒种子长成森林，一个文件化作无限可能。*
