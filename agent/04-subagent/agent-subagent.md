# 从零开始理解 Agent（四）：给 Agent 找个帮手——最简 SubAgent 实现

> **「从零开始理解 Agent」系列** —— 通过一个不到 300 行的开源项目 [nanoAgent](https://github.com/GitHubxsy/nanoAgent)，逐层拆解 OpenClaw / Claude Code 等 AI Agent 背后的主要机制。
>
> - [第一篇：底层原理，约 100 行](../01-essence/agent-essence.md) —— 工具 + 循环
> - [第二篇：Memory](../02-memory/agent-memory.md) —— 让 Agent 记住上一次
> - [第三篇：Rules、Skills 与 MCP](../03-skills-mcp/agent-skills-mcp.md) —— 把能力从代码里拿出来
> - **第四篇：最简 SubAgent 实现**（本文）—— 临时委派
> - [第五篇：多智能体协作与编排](../05-teams/agent-teams.md) —— 持久团队
> - [第六篇：上下文压缩](../06-compact/agent-compact.md) —— 控制上下文
> - [第七篇：安全与权限控制](../07-safety/agent-safe.md) —— 加上工程边界

前三篇，我们一路把 Agent 从"会用工具"推进到"能记住上一次、能从项目配置里扩展能力"。但到目前为止，所有版本都有一个共同特点：**永远只有一个 Agent 在干活**。

想象一下这个场景：你让 Agent "搭建一个博客系统，前端用 React，后端用 FastAPI，数据库用 SQLite"。一个 Agent 要同时精通前端、后端、数据库——它可以做到，但很容易顾此失彼，上下文越来越长，后面写前端的时候把前面后端的细节忘了。

现实中遇到这类问题，常见做法是：**找帮手，分工合作。**

这就是 SubAgent（子智能体）的核心思想：主 Agent 当项目经理，把子任务委派给拥有不同专业身份的 SubAgent，各管一块，互不干扰。

---

## 一、一个协作类比理解 SubAgent

```
之前（一个人干所有活）:

  任务发起方 → "把前端后端数据库都处理一下"
         一个协作者（同一个上下文里处理所有事）
         - 写后端 API...
         - 写前端页面...（等等，后端那个接口叫啥来着？）
         - 建数据库表...（前端那个字段是什么格式？）


现在（项目经理 + 专人）:

  任务发起方 → 协调者（主 Agent）
              │
              ├── "后端用 FastAPI" → 后端协作者（SubAgent A）
              ├── "前端用 React"   → 前端协作者（SubAgent B）
              └── "验证能跑通"     → 测试协作者（SubAgent C）

  每个 SubAgent 只看自己的任务，完成后把摘要交回主 Agent 汇总。
```

但要注意一个关键点：这个类比不完全准确。真实协作里，每个人有稳定身份和长期记忆，下次还能继续接上。**SubAgent 不是这样的。** SubAgent 的生命周期是：

```
生成 → 接收任务 → 干活（可以调用工具）→ 返回结果摘要 → 消亡
```

**一次性的。** 没有持久身份，没有跨调用的记忆。主 Agent 第一次派出的"后端工程师"和第二次派出的"后端工程师"之间没有任何关联——它们是两个完全独立的一次性执行上下文。

这个"用完即弃"的设计是刻意的：SubAgent 解决的是**单次任务内的分工问题**，不是长期协作问题。它的价值在于给子任务一个干净的上下文和专注的角色，而不是构建一个持久的团队。

---

## 二、在代码里怎么实现？

如果你读过前三篇，这个实现可能会让你惊讶——**核心新增只有大约 30 行代码**。

为什么这么少？因为前三篇已经把所有基础设施搭好了：工具系统（第一篇）、Agent 循环（第一篇）、工具路由表（第一篇）、记忆（第二篇）。SubAgent 要做的，只是**复用这些基础设施，再启动一个独立的 Agent 循环**。

这个版本继续保持最小实现：工具层和循环复用前几讲，新增重点只放在 `subagent()` 如何启动一段独立上下文。

### 2.1 新增一个工具定义

还记得第一篇中的核心洞察吗？

> LLM 本身不会执行任何代码。它只是根据工具说明书，输出一段结构化的 JSON。真正的执行发生在我们的 Python 代码里。

SubAgent 也不例外。我们要做的第一步，就是写一份"工具说明书"告诉 LLM："你有一个叫 subagent 的工具，可以指定角色和任务来委派子任务"：

```python
{
    "name": "subagent",
    "description": "Delegate a task to a specialized sub-agent with its own role and independent context.",
    "parameters": {
        "type": "object",
        "properties": {
            "role": {"type": "string", "description": "The sub-agent's specialty, e.g. 'Python backend developer'"},
            "task": {"type": "string", "description": "The specific task to delegate"}
        },
        "required": ["role", "task"]
    }
}
```

就这么一个 JSON。和 `read`、`write`、`bash` 等工具完全一样的格式——对 LLM 来说，`subagent` 就是"又一个工具"，没有任何特殊之处。

### 2.2 实现 subagent 函数

```python
def subagent(role, task):
    """启动一个独立的 Agent 循环，拥有专属角色和独立上下文"""
    print(f"\n[SubAgent:{role}] 开始: {task}")

    # 关键 1：独立的 messages，独立的 system prompt
    sub_messages = [
        {"role": "system", "content": f"You are a {role}. Be concise and focused. Only do what is asked."},
        {"role": "user", "content": task}
    ]

    # 关键 2：排除 subagent 自身，防止无限递归
    sub_tools = [t for t in tools if t["function"]["name"] != "subagent"]

    # 关键 3：一个完整的 Agent 循环（和第一篇的核心循环一模一样）
    for _ in range(10):
        response = client.chat.completions.create(
            model=MODEL, messages=sub_messages, tools=sub_tools
        )
        message = response.choices[0].message
        sub_messages.append(message)

        if not message.tool_calls:
            print(f"[SubAgent:{role}] 完成")
            return message.content

        for tc in message.tool_calls:
            fn = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  [SubAgent:{role}] {fn}({args})")
            result = available_functions[fn](**args)
            sub_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "SubAgent: max iterations reached"
```

### 2.3 注册到路由表

```python
available_functions["subagent"] = subagent
```

完了。就这些。

---

## 三、等一下——代码里没有调用 subagent 的地方？

如果你仔细看完整个代码，会发现一件"奇怪"的事：**没有任何地方主动调用 `subagent()` 函数**。没有 `if task == "复杂任务": subagent(...)`，没有任何预编排逻辑。

这正是 Agent 和传统程序的根本区别，也是贯穿这整个系列的核心设计思想。

让我用一张图还原 subagent 被调用的完整链路：

```
用户: "创建一个 TODO 应用，包含 Python 后端和 HTML 前端"
  │
  ▼
主 Agent 的 run_agent() 循环启动
  │
  ▼
(1) 代码把 messages + tools 列表发送给 LLM
    tools 列表里包含: [read, write, edit, glob, grep, bash, subagent]
                                                            ^^^^^^^^
                                                       LLM 看到了这个工具
  │
  ▼
(2) LLM 分析任务，决定委派，返回:
    {"tool_calls": [{"function": {"name": "subagent",
                                  "arguments": {"role": "Python backend developer",
                                                "task": "用 FastAPI 创建..."}}}]}
  │
  ▼
(3) 核心循环中的通用调度代码执行:
    fn = "subagent"
    args = {"role": "Python backend developer", "task": "..."}
    result = available_functions["subagent"](**args)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
             走到了我们写的 subagent() 函数！
  │
  ▼
(4) subagent() 内部启动一个全新的 Agent 循环
    - 独立的 system prompt: "You are a Python backend developer."
    - 独立的 messages 列表
    - 可以使用 read/write/edit/bash 等工具
    - 循环结束后，返回结果文本
  │
  ▼
(5) 结果返回给主 Agent，主 Agent 可能继续派出前端 SubAgent...
```

关键在第 (3) 步——`available_functions["subagent"](**args)` 这行代码。它和 `available_functions["bash"](**args)` 走的是**完全相同的调度路径**。在核心循环眼里，subagent 和 bash 没有任何区别，都是"LLM 说要调用，那我就执行"。

**控制流在 LLM 手里，不在代码里。** 代码只提供能力（注册工具），LLM 决定何时使用。

---

## 四、三个关键设计决策

### 4.1 为什么 SubAgent 要有独立的 messages？

```python
# 主 Agent 的 messages（可能已经很长了）
messages = [system, user, assistant, tool, assistant, tool, ...]

# SubAgent 创建全新的 messages（从零开始）
sub_messages = [
    {"role": "system", "content": f"You are a {role}. ..."},
    {"role": "user", "content": task}
]
```

还记得第二篇中的"短期记忆"概念吗？`messages` 列表就是 Agent 的短期记忆。如果 SubAgent 共享主 Agent 的 messages，它会看到所有历史——前端 SubAgent 会被后端的代码细节干扰，上下文越来越长，token 开销越来越大。

独立的 messages 意味着：**SubAgent 只知道自己的角色和任务，保持专注**。而且这个 `sub_messages` 在函数返回后就被垃圾回收了——SubAgent 没有任何持久记忆，干完活就消亡，下次调用是一个全新的 SubAgent。

### 4.2 为什么 SubAgent 有不同的 system prompt？

```python
# 主 Agent: 协调者
"You are an orchestrator agent. You can delegate to sub-agents..."

# SubAgent: 专家
f"You are a {role}. Be concise and focused. Only do what is asked."
```

第三篇中我们讲了 Rules——用声明式文件定制 Agent 的行为。SubAgent 的 system prompt 是同一个思路的极简版：**通过不同的角色描述，让同一个 LLM 展现出不同的专业行为。**

当 `role` 是 "Python backend developer" 时，LLM 会倾向于用 FastAPI/Flask，写 RESTful 接口；当 `role` 是 "frontend developer" 时，LLM 会倾向于写 HTML/CSS/JavaScript。同一个模型，不同的人格。

### 4.3 为什么要排除 subagent 工具？

```python
sub_tools = [t for t in tools if t["function"]["name"] != "subagent"]
```

这里的重点是**防止无限递归**。如果 SubAgent 也能派出自己的 SubAgent，而那个 SubAgent 又派出自己的……就会无限嵌套下去。

一行代码，一个过滤，问题解决。

---

## 五、实际运行效果

假设用户输入：

```bash
python agent/04-subagent/agent-subagent.py "不要直接完成任务。请调用 subagent 工具两次，两个子代理都不要读写文件：1）role=Python API 设计师，task=为 TODO 应用设计 3 个后端接口，只返回接口清单；2）role=前端交互设计师，task=为 TODO 应用设计 3 个界面交互，只返回交互清单。最后主 Agent 用纯文本 4 行汇总，不要表格：后端交付、前端交付、为什么适合委派、主 Agent 没做什么。"
```

终端输出大致如下：

```
[Tool] subagent({"role": "Python API 设计师", "task": "为 TODO 应用设计 3 个后端接口..."})

==================================================
[SubAgent:Python API 设计师] 开始: 为 TODO 应用设计 3 个后端接口...
==================================================
[SubAgent:Python API 设计师] 完成

[Tool] subagent({"role": "前端交互设计师", "task": "为 TODO 应用设计 3 个界面交互..."})

==================================================
[SubAgent:前端交互设计师] 开始: 为 TODO 应用设计 3 个界面交互...
==================================================
[SubAgent:前端交互设计师] 完成

后端交付：3 个 API 接口清单。
前端交付：3 个交互流程清单。
为什么适合委派：后端接口与前端交互是不同专业视角。
主 Agent 没做什么：没有直接设计细节，只负责分派和汇总。
```

注意两个关键现象：

**主 Agent 不直接完成专业细节。** 它只做了两件事：调用 subagent 委派 API 设计任务，再调用 subagent 委派前端交互任务，最后汇总结果。

**两个 SubAgent 各管各的。** API 子代理只看到自己的接口设计任务，前端子代理只看到自己的交互设计任务。它们不会共享同一个 `messages`，所以不会把两个专业视角搅在一起。

---

## 六、SubAgent vs 之前的方案：什么时候用哪个？

| 场景 | 推荐方案 | 为什么 |
|------|---------|--------|
| "统计目录下的文件数" | 第一篇的基础 Agent | 简单任务，不需要额外机制 |
| "找到所有 TODO 并整理到文件" | 第一篇的基础 Agent 循环 | 步骤之间有依赖，适合让同一个上下文连续推进 |
| "前端用 React，后端用 FastAPI" | **SubAgent** | 子任务之间相对独立，需要不同专业身份 |
| "按照项目规范重构代码" | 第三篇的 Rules | 需要行为约束，不需要分工 |

SubAgent 和普通单 Agent 循环最大的区别：

| 维度 | 单 Agent 循环 | SubAgent（本文） |
|------|--------------|-----------------|
| 上下文 | 所有步骤**共享** messages | 每个 SubAgent **独立** messages |
| 身份 | 同一个 Agent，同一个角色 | 每个 SubAgent **不同的专业角色** |
| 生命周期 | 步骤间 Agent 持续存在 | **生成 → 干活 → 返回摘要 → 消亡**（一次性） |
| 跨次记忆 | 步骤 2 能看到步骤 1 的全部细节 | SubAgent B 看不到 SubAgent A 做了什么 |
| 适合 | 步骤之间强依赖 | 子任务之间相对独立 |
| 类比 | 一个人按步骤做事 | 找一个一次性协作者，完成后返回摘要 |

---

## 七、系列总结：从 100 行到完整 Agent 架构

四篇文章，我们从零搭建了一个完整的 Agent 认知体系：

```
┌───────────────────────────────────────────────────────┐
│                    Agent 架构全景                       │
│                                                        │
│  ┌──────────────┐  第四篇 (本文)                       │
│  │  SubAgent    │  多智能体协作 ── subagent() 工具      │
│  ├──────────────┤  第三篇                              │
│  │  Rules       │  行为约束层 ──── .agent/rules/       │
│  │  Skills      │  技能知识层 ──── .agent/skills/      │
│  │  MCP         │  工具扩展层 ──── .agent/mcp.json     │
│  ├──────────────┤  第二篇                              │
│  │  Memory      │  持久记忆层 ──── agent_memory.md     │
│  ├──────────────┤  第一篇                              │
│  │  LLM         │  推理决策层 ──── OpenAI API          │
│  │  Tools       │  工具执行层 ──── bash/read/write     │
│  │  Loop        │  核心循环层 ──── for + tool_calls    │
│  └──────────────┘                                      │
└───────────────────────────────────────────────────────┘
```

| 篇 | 文件 | 核心主题 | 一句话总结 |
|----|------|---------|-----------|
| 一 | agent-essence.py | 工具 + 循环 | Agent 的最小本质——LLM 是大脑，代码是手脚 |
| 二 | agent-memory.py | Memory | 时间维度——把上一次结果带回上下文 |
| 三 | agent-skills-mcp.py | Rules + Skills + MCP | 空间维度——扩展知识与工具 |
| 四 | agent-subagent.py ⭐新 | SubAgent | 协作维度——给 Agent 找帮手 |

> 注：前三个文件来自 [nanoAgent 原始仓库](https://github.com/GitHubxsy/nanoAgent)。第四个文件是本文新开发的（[GitHub 源码](https://github.com/GitHubxsy/nanoAgent/blob/main/agent/04-subagent/agent-subagent.py)）。为了聚焦 SubAgent，本文只保留与委派直接相关的代码。

四个维度叠加起来，就能接近 OpenClaw、Claude Code、Cursor Agent、Devin 等产品中的一部分核心结构。

而贯穿整个系列的核心设计思想只有一个：**一切能力都可以做成"工具"。** 读文件是工具，写文件是工具，搜索是工具，甚至**派出一个子智能体也是工具**（本文）。LLM 通过统一的 Function Calling 协议按需调用它们，代码通过统一的路由表（`available_functions`）执行它们。

但 SubAgent 的"一次性"本质也带来了局限：它们之间无法通信，不记得上次做了什么，无法被多次调用。当任务需要持续协作——你写完我来接、测出 bug 再回到开发、改完继续验证——就需要从一次性委派升级为有身份和历史的团队成员。

这就是 [第五篇：多智能体协作与编排](../05-teams/agent-teams.md) 的主题：用两个类（`Agent` + `Team`）实现持久记忆、身份管理和通信通道。

---

*本文基于 [GitHubxsy/nanoAgent](https://github.com/GitHubxsy/nanoAgent) 的架构扩展。完整系列：[第一篇：底层原理](../01-essence/agent-essence.md) → [第二篇：Memory](../02-memory/agent-memory.md) → [第三篇：Rules、Skills 与 MCP](../03-skills-mcp/agent-skills-mcp.md) → 第四篇：SubAgent（本文） → [第五篇：多智能体协作](../05-teams/agent-teams.md)*
