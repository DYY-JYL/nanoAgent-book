# 从零开始理解 Agent（二）：Memory 如何让 Agent 记住上一次

> **「从零开始理解 Agent」系列** —— 通过一个极简开源项目 [nanoAgent](https://github.com/GitHubxsy/nanoAgent)，逐层拆解 Agent 背后的核心机制。
>
> - [第一篇：底层原理，约 100 行](../01-essence/agent-essence.md) —— 工具 + 循环
> - **第二篇：Memory**（本文）—— 在第一篇基础上增加持久记忆
> - [第三篇：Rules、Skills 与 MCP](../03-skills-mcp/agent-skills-mcp.md) —— 能力外置

第一讲已经搭好最小闭环：用户给任务，模型决定是否调用工具，工具返回结果，循环继续，直到模型给出最终回答。

第二讲只做一件事：**让下一次运行能看到上一次的结果**。工具列表不变，循环结构不变，只在第一讲的脚本上增加三个 Memory 增量：

1. 启动时读取 `agent_memory.md`
2. 将历史记忆注入 system prompt
3. 任务结束后把本轮任务与结果追加写回 `agent_memory.md`

这就是最小 Memory 闭环。

---

## 一、从第一讲到第二讲：变化在哪里？

| 能力 | 第一讲 `agent-essence.py` | 第二讲 `agent-memory.py` |
|------|---------------------------|---------------------------|
| 工具 | `execute_bash` / `read_file` / `write_file` | 完全保留 |
| 循环 | `run_agent()` 内处理 `tool_calls` | 仍然是同一个循环 |
| 记忆读取 | 无 | 启动时 `load_memory()` |
| 记忆注入 | 无 | 拼进 system prompt |
| 记忆写入 | 无 | 结束时 `save_memory()` |

注意这个递进关系：第二讲不是换一个 Agent，而是在第一讲的 Agent 外面加了一层“记事本”。

---

## 二、第一处变化：定义记忆文件

```python
MEMORY_FILE = "agent_memory.md"
```

这里没有数据库、没有向量检索、没有复杂框架。Memory 先从最小方案开始：把历史写进一个 Markdown 文件。

为什么用文件？因为它足够直观。演示时可以直接打开 `agent_memory.md`，看到每一次任务和结果是如何追加进去的。

---

## 三、第二处变化：读取与写入 Memory

```python
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return ""
    with open(MEMORY_FILE, "r") as f:
        lines = f.read().splitlines()
    return "\n".join(lines[-50:])


def save_memory(task, result):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## {timestamp}\n**Task:** {task}\n**Result:** {result}\n"
    with open(MEMORY_FILE, "a") as f:
        f.write(entry)
    print(f"[Memory] Saved to {MEMORY_FILE}")
```

`save_memory()` 做的是“写入”：每轮任务结束后，将时间、任务、结果追加到文件末尾。

`load_memory()` 做的是“读取”：下一轮启动时，读取最近 50 行历史。这里的 50 行是一个最小窗口，避免记忆文件无限增长后一次性塞进 prompt。

---

## 四、第三处变化：把记忆放回上下文

```python
def build_messages(user_message):
    system_prompt = "You are a helpful assistant. Be concise."
    memory = load_memory()
    if memory:
        print(f"[Memory] Loaded {MEMORY_FILE}")
        system_prompt += f"\n\nPrevious context:\n{memory}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
```

这一段是 Memory 的关键。

文件本身不会让模型记住任何东西。真正起作用的是：下一次运行时，脚本把 `agent_memory.md` 里的历史搬进 system prompt，让模型在本轮推理时“看到”之前发生过什么。

也就是说，最小 Memory 的本质不是“模型内部长出了记忆”，而是“外部历史被重新注入上下文”。

---

## 五、第四处变化：在原来的循环末尾保存结果

第一讲的 `run_agent()` 在模型给出最终回答后直接返回。第二讲只在返回前多做一步：

```python
if not message.tool_calls:
    save_memory(user_message, message.content)
    return message.content
```

其余工具调用循环保持不变：

```python
for tool_call in message.tool_calls:
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    print(f"[Tool] {name}({args})")
    result = functions[name](**args)
    messages.append(
        {"role": "tool", "tool_call_id": tool_call.id, "content": result}
    )
```

这是第二讲可以现场强调的递进点：**循环没有变，只是循环开始前多读一次记忆，循环结束后多写一次记忆。**

---

## 六、实际运行效果

第一轮：

```bash
python3 agent/02-memory/agent-memory.py "创建 launch-note.txt，内容是 Agent Memory Demo"
```

观察点：

```text
[Tool] write_file(...)
[Memory] Saved to agent_memory.md
```

然后打开 `agent_memory.md`，能看到本轮任务和结果被追加写入。

第二轮：

```bash
python3 agent/02-memory/agent-memory.py "不重新读文件，只根据记忆说明你上一次完成了什么任务"
```

观察点：

```text
[Memory] Loaded agent_memory.md
[Memory] Saved to agent_memory.md
```

第二轮没有要求读取 `launch-note.txt`，但模型仍然能根据 `Previous context` 回答上一次做过什么。这里就是 Memory 生效的证据。

---

## 七、最小 Memory 的边界

这个版本故意保持简单，所以它也有明显边界：

- 只按最近 50 行截断，不能保证取到最相关的历史。
- 错误结果也会被写入，下一轮可能继续污染上下文。
- 文件越长，注入 prompt 的成本越高。

但正因为简单，它非常适合现场分享：Memory 的完整链路可以一眼看清。

```text
本轮任务
  ↓
run_agent()
  ↓
save_memory()
  ↓
agent_memory.md
  ↓
下一轮 load_memory()
  ↓
Previous context
  ↓
模型基于历史继续回答
```

---

## 八、本讲结论

第二讲只回答一个问题：Agent 如何记住上一次？

答案是三步：

1. 把本轮结果写入外部文件。
2. 下一轮启动时读取外部文件。
3. 将历史注入 system prompt。

从第一讲到第二讲，用户能看到清晰的逐步递进：先有工具循环，再给这个循环接上一个最小记事本。后面的 Rules、Skills、MCP、SubAgent、Teams，都是在这个最小闭环上继续扩展。
