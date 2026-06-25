# 从零开始理解 Agent（五）：从一次性委派到持久团队——多智能体协作与编排

> **「从零开始理解 Agent」系列** —— 从一个极简开源项目 [nanoAgent](https://github.com/GitHubxsy/nanoAgent) 出发，逐层拆解 OpenClaw / Claude Code 等 AI Agent 背后的主要机制。
>
> - [第一篇：底层原理，约 100 行](../01-essence/agent-essence.md) —— 工具 + 循环
> - [第二篇：Memory](../02-memory/agent-memory.md) —— 让 Agent 记住上一次
> - [第三篇：Rules、Skills 与 MCP](../03-skills-mcp/agent-skills-mcp.md) —— 把能力从代码里拿出来
> - [第四篇：SubAgent 子智能体](../04-subagent/agent-subagent.md) —— 临时委派
> - **第五篇：多智能体协作与编排**（本文）—— 持久团队
> - [第六篇：上下文压缩](../06-compact/agent-compact.md) —— 控制上下文
> - [第七篇：安全与权限控制](../07-safety/agent-safe.md) —— 加上工程边界

上一篇我们实现了 SubAgent——主 Agent 可以临时派出一个"专家"来处理局部任务。但我们也明确定义了 SubAgent 的本质：**一次性协作者，生成 → 干活 → 返回摘要 → 消亡，没有持久身份，没有跨次记忆。**

这在很多场景下够用了。但换到软件开发团队的协作场景里，后端工程师写完 API 后，前端工程师需要知道接口长什么样；测试工程师发现 bug 后，需要告诉开发去修；开发修完后，测试还要再验一遍——**同一个角色会被多次找到，而且需要保留上下文。**

SubAgent 做不到这些。每次调用都是一个全新的执行上下文，不会自动接上上一次的历史。

这就引出下一步：**从一次性 SubAgent，升级到有身份和历史的团队。**

---

## 一、一次性协作者 vs 持久团队成员：差什么？

| | SubAgent（一次性协作者） | Teams Agent（持久团队成员） |
|--|--|--|
| 有名字吗？ | ❌ 只有一个临时角色描述 | ✅ 有名字（alice）、有固定角色 |
| 记得上次做了什么吗？ | ❌ 每次调用都是新上下文 | ✅ 多次交互之间记忆持续累积 |
| 能收到其他成员的消息吗？ | ❌ 互相看不到 | ✅ 有收件箱，能收消息 |
| 什么时候消失？ | 函数返回就没了 | 团队解散才消失 |

要从一次性委派升级为持久团队，需要补齐三样东西：

**1. 能跨多轮对话存活的持久智能体** —— Agent 有记忆，被多次 `chat()` 调用时记得之前做过什么，不会像 SubAgent 那样每次都是新上下文

**2. 身份与生命周期管理** —— Agent 有名字、有角色，被创建、持续存活、最终解散，而不是用完即弃

**3. 智能体之间的通信通道** —— Agent 之间可以互相发消息（点对点或广播），而不是彼此隔离、互相看不到

接下来看代码怎么实现。

---

## 二、核心实现：两个类搞定一切

这个版本的核心新增是两个类：`Agent` 和 `Team`。工具层（read/write/edit/bash）和 Agent 循环完全复用前几篇的代码。

### 2.1 Agent 类：有状态的持久智能体

先回忆 SubAgent 的实现——一个函数：

```python
# SubAgent（第四篇）—— 一个函数，用完就没
def subagent(role, task):
    sub_messages = [...]  # 局部变量，函数返回即消亡
    for _ in range(10):
        ...
    return result  # 返回后 sub_messages 被垃圾回收，一切归零
```

现在看 Teams 中的 Agent——一个类：

```python
class Agent:
    def __init__(self, name, role):
        self.name = name                # 身份：有名字
        self.role = role                # 身份：有角色
        self.inbox = []                 # 通信：收件箱
        self.messages = [               # 记忆：持久保持
            {"role": "system", "content": f"You are {name}, a {role}. Be concise and focused."}
        ]
```

区别只有一个，但意义巨大：**`messages` 从函数的局部变量变成了对象的实例属性**。

局部变量在函数返回后就被垃圾回收。实例属性只要对象还活着，就一直在。这意味着你可以对同一个 Agent 多次调用 `chat()`，每次的对话历史都会累积在 `self.messages` 中——**Agent 记得之前做过什么**。

### 2.2 chat() 方法：带收件箱的 Agent 循环

```python
def chat(self, task):
    # 第 1 步：如果 inbox 有新消息，先读取并消化
    if self.inbox:
        mail = "\n".join(f"[来自 {m['from']}]: {m['content']}" for m in self.inbox)
        self.messages.append({"role": "user", "content": f"你收到了团队成员的消息:\n{mail}"})
        resp = client.chat.completions.create(model=MODEL, messages=self.messages)
        self.messages.append(resp.choices[0].message)
        self.inbox.clear()

    # 第 2 步：执行本次任务（和之前的 Agent 循环一样）
    self.messages.append({"role": "user", "content": task})
    for _ in range(10):
        response = client.chat.completions.create(model=MODEL, messages=self.messages, tools=tools)
        message = response.choices[0].message
        self.messages.append(message)
        if not message.tool_calls:
            return message.content
        for tc in message.tool_calls:
            # ... 执行工具，追加结果（和第一篇完全一样）
```

关键在第 1 步：每次 `chat()` 开始前，Agent 会先检查收件箱。如果有其他 Agent 发来的消息，就先读取、消化（让 LLM 处理一下），然后清空收件箱。这样 Agent 在执行任务时，已经知道了队友们的最新进展。

### 2.3 receive() 方法：通信通道

```python
def receive(self, sender, message):
    self.inbox.append({"from": sender, "content": message})
```

就这一行。往收件箱里追加一条消息。简单到不需要解释。

---

## 三、Team 类：生命周期管理与通信编排

```python
class Team:
    def __init__(self):
        self.agents = {}  # name → Agent

    def hire(self, name, role):
        """招募：创建一个持久 Agent"""
        agent = Agent(name, role)
        self.agents[name] = agent
        return agent

    def send(self, from_name, to_name, message):
        """点对点通信"""
        self.agents[to_name].receive(from_name, message)

    def broadcast(self, from_name, message):
        """广播：给团队所有其他人发消息"""
        for name, agent in self.agents.items():
            if name != from_name:
                agent.receive(from_name, message)

    def disband(self):
        """解散：所有 Agent 生命周期结束"""
        self.agents.clear()
```

四个方法，对应团队协作的四个动作：

| 方法 | 作用 | 类比 |
|------|------|------|
| `hire()` | 创建 Agent，加入团队 | 创建成员 |
| `send()` | A 给 B 发消息 | 工作群里 @ 某人 |
| `broadcast()` | A 给所有人发消息 | 群发公告 |
| `disband()` | 解散团队，所有 Agent 消亡 | 项目结束，团队解散 |

---

## 四、完整协作流程

```python
def run_team(task):
    team = Team()

    # 第 1 阶段：组建团队
    members = plan_team(task)  # LLM 自动拆分角色
    for m in members:
        team.hire(m["name"], m["role"])

    # 第 2 阶段：逐个执行，每人干完广播成果
    for m in members:
        agent = team.agents[m["name"]]
        result = agent.chat(m["task"])
        team.broadcast(m["name"], f"我完成了任务。摘要: {result[:200]}")

    # 第 3 阶段：最后一个成员做二次审查
    reviewer = team.agents[members[-1]["name"]]
    review = reviewer.chat("请根据团队成果做最终审查")

    # 第 4 阶段：解散
    team.disband()
```

用一个具体例子来说明。假设输入一个固定的发布评审演示命令：

```bash
python3 -u agent/05-teams/agent-teams.py "固定 3 人发布评审团队演示：登录接口发布前评审。要求所有成员不要读写文件，只输出短清单；重点观察 [创建]、[记忆]、[收件箱]、[广播]、最终审查、[解散]。"
```

```
[团队] 3 人:
  1. alice — api developer → 登录接口交付摘要
  2. bob — security reviewer → 安全风险与建议
  3. chris — release reviewer → 发布验收标准

============================================================
  第 1 阶段: 招募团队
============================================================
  [创建] alice (api developer)
  [创建] bob (security reviewer)
  [创建] chris (release reviewer)

============================================================
  第 2 阶段: 协作开发
============================================================

── [1/3] alice 开始工作 ──
  [记忆] alice 第 1 次 chat，已有 1 条 messages，inbox 0 条
  [alice] → 1. 登录接口已交付
             2. 支持账号密码验证
             3. 返回 Token 令牌
  [记忆] alice 本轮结束，messages 3 条
  [广播] alice → 全体: 我完成了任务。摘要: 登录接口已交付...

── [2/3] bob 开始工作 ──
  [记忆] bob 第 1 次 chat，已有 1 条 messages，inbox 1 条
  [收件箱] bob 读取 1 条团队消息
  [bob] → 1. 密码必须加盐哈希存储
           2. Token 需设置有效期
  [记忆] bob 本轮结束，messages 5 条
  [广播] bob → 全体: 我完成了任务。摘要: 安全风险与建议...

── [3/3] chris 开始工作 ──
  [记忆] chris 第 1 次 chat，已有 1 条 messages，inbox 2 条
  [收件箱] chris 读取 2 条团队消息
  [chris] → G1. 登录接口可用
             G2. 密码加盐哈希
             G3. Token 安全有效期
  [记忆] chris 本轮结束，messages 5 条
  [广播] chris → 全体: 我完成了任务。摘要: 发布验收标准...

============================================================
  第 3 阶段: chris 做最终审查
============================================================
  [记忆] chris 第 2 次 chat，已有 5 条 messages，inbox 0 条
  （这里最关键：chris 没有重新收到消息，但 messages 里还保留第一次的验收标准）
  [chris] → 结论：不通过，需补充安全证据
            记忆证据：引用 G2/G3
            风险：密码或 Token 安全缺口
            下一步：补充实现证据后重新审查
```

注意 **carol 被调用了两次 `chat()`** ：第一次做测试，第二次做审查。第二次时她还记得第一次做了什么——这就是"持久记忆"的价值。SubAgent 做不到这一点，因为每次调用都会创建一个全新的上下文。

---

## 五、三大核心能力的代码对照

回到开头提出的三个要求，逐一对照：

### 能力 1：能跨多轮对话存活的持久智能体

```python
# SubAgent：局部变量，函数返回即消亡
def subagent(role, task):
    sub_messages = [...]  # 🔴 生命周期 = 这个函数调用
    ...
    return result         # sub_messages 被回收

# Teams Agent：实例属性，对象存活就一直在
class Agent:
    def __init__(self, ...):
        self.messages = [...]  # 🟢 生命周期 = Agent 对象的生命周期

    def chat(self, task):
        self.messages.append(...)  # 每次调用都往同一个列表里追加
        ...
        # 第 1 次 chat()：messages = [system, user1, assistant1]
        # 第 2 次 chat()：messages = [system, user1, assistant1, user2, assistant2]
        # Agent 在第 2 次时能看到第 1 次的全部历史
```

### 能力 2：身份与生命周期管理

```python
team = Team()

# 创建：Agent 被创建，开始存活
alice = team.hire("alice", "backend developer")
bob   = team.hire("bob",   "frontend developer")

# 存活期间：可以多次交互
alice.chat("创建后端 API")
alice.chat("添加认证中间件")   # alice 记得第一次创建的 API

# 解散：所有 Agent 生命周期结束
team.disband()                 # alice、bob 都消亡了
```

### 能力 3：智能体之间的通信通道

```python
# 点对点：alice 告诉 bob 接口格式
team.send("alice", "bob", "API 接口: GET /todos, POST /todos")

# 广播：alice 告诉所有人
team.broadcast("alice", "后端已完成，接口文档见 API.md")

# bob 下次 chat() 时，会先读 inbox 中的消息
bob.chat("创建前端页面")  # bob 已经知道了 API 接口格式
```

---

## 六、SubAgent vs Teams：什么时候用哪个？

| 场景 | 选 SubAgent | 选 Teams |
|------|------------|----------|
| 子任务之间完全独立 | ✅ 互不干扰，简单直接 | 机制偏重 |
| 后续任务依赖前面的结果 | ❌ 看不到别人做了什么 | ✅ 通过通信通道传递信息 |
| 需要同一个人多次返工 | ❌ 每次都是新人，不记得 | ✅ 持久记忆，记得上次做了什么 |
| 需要测试 → 修 bug → 再测试 | ❌ 做不到 | ✅ 测试人员和开发都能被多次调用 |

一句话总结：**任务简单、互不相关用 SubAgent；需要协作、需要记忆用 Teams。**

---

## 七、系列总结

五篇文章，从一个 100 行的极简 Agent 出发，逐层叠加能力：

| 篇 | 核心新增 | 一句话 |
|----|---------|--------|
| 一 | 工具 + 循环 | Agent 的最小本质 |
| 二 | Memory | 把上一次结果带回上下文 |
| 三 | Rules + Skills + MCP | 扩展知识与工具 |
| 四 | SubAgent | 一次性委派 |
| **五** | **Agent 类 + Team 类** | **有记忆、有身份、能通信的正式团队** |

从第四篇的 `subagent()` 函数到第五篇的 `Agent` 类，变化只有一个：**`messages` 从局部变量变成了实例属性**。但这一个变化，让 Agent 从"一次性执行上下文"进化为了"有记忆、有身份、能协作的团队成员"。

这就是软件工程中最朴素的道理：**数据放在哪里，决定了它的生命周期；生命周期决定了能力边界。**

但能力越强，副作用也越大——Agent 干的活越多、协作越复杂，`messages` 就越长。长到撑爆 LLM 的 context window 怎么办？在 [第六篇：上下文压缩](../06-compact/agent-compact.md) 中，我们用一个 30 行的函数来解决这个"自我窒息"问题。

---

*本文基于 agent-teams.py（[GitHub 源码](https://github.com/GitHubxsy/nanoAgent/blob/main/agent/05-teams/agent-teams.py)）分析。完整系列：[第一篇](../01-essence/agent-essence.md) → [第二篇](../02-memory/agent-memory.md) → [第三篇](../03-skills-mcp/agent-skills-mcp.md) → [第四篇](../04-subagent/agent-subagent.md) → 第五篇（本文） → [第六篇](../06-compact/agent-compact.md)*
