# 从零开始理解 Agent（三）：Rules、Skills 与 MCP 如何外置能力

> **「从零开始理解 Agent」系列** —— 通过一个极简开源项目 [nanoAgent](https://github.com/GitHubxsy/nanoAgent)，逐层拆解 Agent 背后的核心机制。
>
> - [第一篇：底层原理，约 100 行](../01-essence/agent-essence.md) —— 工具 + 循环
> - [第二篇：Memory](../02-memory/agent-memory.md) —— 让 Agent 记住上一次
> - **第三篇：Rules、Skills 与 MCP**（本文）—— 把能力从代码里拿出来

第一讲让模型能动手，第二讲让模型能记住上一次。第三讲继续往前走：**不要把所有行为、知识和工具都硬编码进 Python 文件里**。

本讲只讲三件事：

1. **Rules**：把项目规则写成文件，启动时注入 prompt。
2. **Skills**：把可复用的任务方法写成 Markdown，启动时注入 prompt。
3. **MCP**：把外部工具定义写成配置，启动时追加到 tools 列表。

这就是能力外置。

---

## 一、为什么要外置能力？

如果所有东西都写死在脚本里，会遇到三个问题：

| 问题 | 外置方式 |
|------|----------|
| 不同项目有不同规范 | 用 `.agent/rules/*.md` |
| 不同任务有不同做法 | 用 `.agent/skills/*/SKILL.md` |
| 不同环境要接不同工具 | 用 `.agent/mcp.json` |

第三讲的重点不是让 Agent 更“聪明”，而是让能力变得可替换、可观察、可配置。

---

## 二、Rule：项目规则进入 prompt

```python
RULES_DIR = ".agent/rules"

def load_rules():
    rules = []
    if not os.path.exists(RULES_DIR):
        return ""
    try:
        for rule_file in sorted(Path(RULES_DIR).glob("*.md")):
            with open(rule_file, "r") as f:
                rules.append(f"# {rule_file.stem}\n{f.read()}")
        return "\n\n".join(rules) if rules else ""
    except:
        return ""
```

Rule 是项目级约束。演示里的最小 Rule 很短，只管输出形态：

```markdown
# Demo Style

- 最终回答固定输出 3 行，行首分别是：`Rule证据：`、`Skill证据：`、`MCP证据：`。
- 不输出表格，不展开长解释，每行控制在 60 个字以内。
- `Skill证据：` 这一行必须使用 `排序：X > Y > Z` 的形式。
- 如果调用了 MCP 工具，`MCP证据：` 这一行要引用工具返回的“只做演示，不修改文件”。
```

它不是工具，模型不会“调用” Rule。它的作用方式更直接：启动时拼进 system prompt，让模型从一开始就看到这些约束。

---

## 三、Skill：任务方法进入 prompt

```python
SKILLS_DIR = ".agent/skills"

def load_skills():
    skills = []
    if not os.path.exists(SKILLS_DIR):
        return []
    try:
        skill_files = sorted(Path(SKILLS_DIR).glob("*/SKILL.md")) + sorted(
            Path(SKILLS_DIR).glob("*.md")
        )
        for skill_file in skill_files:
            skills.append(parse_markdown_skill(skill_file))
        return skills
    except:
        return []
```

Skill 更像“做事手册”。演示里的 `release_triage` 不是让模型多一个函数，而是告诉模型：发布前有多个问题时，应该先修哪个、后修哪个。

现在 Skill 使用 Markdown 格式：

```markdown
---
name: release_triage
description: 给发布前问题排序：数据安全第一，无法启动第二，界面文案最后。
when_to_use: 当任务要求整理发布前问题、判断修复顺序或输出发布检查优先级时使用。
triggers: release_triage, 发布前检查, 发布排序, 修复顺序, 优先级
---

# Release Triage

## Priority Order

1. 数据安全：删除、权限、泄露、不可恢复。
2. 无法启动：启动报错、构建失败、接口 500。
3. 界面文案：颜色、按钮、说明文字、README。
```

Markdown 文件会被解析成三部分：frontmatter 里的名称和说明、正文里的操作步骤、以及文件路径。

```python
def parse_markdown_skill(path):
    content = path.read_text(encoding="utf-8")
    metadata = {}
    body = content
    if content.startswith("---\n"):
        end = content.find("\n---", 4)
        if end != -1:
            frontmatter = content[4:end].strip()
            body = content[end + 4 :].strip()
            for line in frontmatter.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
    name = metadata.get(
        "name", path.parent.name if path.name == "SKILL.md" else path.stem
    )
    return {
        "name": name,
        "description": metadata.get("description", ""),
        "when_to_use": metadata.get("when_to_use", ""),
        "path": str(path),
        "content": body,
    }
```

最后把 Skill 整理成 prompt 片段：

```python
def format_skill_for_prompt(skill):
    lines = [
        f"## {skill['name']}",
        f"Source: {skill['path']}",
        f"Description: {skill.get('description', '')}",
    ]
    when_to_use = skill.get("when_to_use")
    if when_to_use:
        lines.append(f"When to use: {when_to_use}")
    lines.append(skill["content"])
    return "\n".join(lines)
```

这版演示只讲一个更直接的结论：**Skill 是外置的任务方法，启动时进入 prompt，影响模型做事方式。**

---

## 四、MCP：外部工具进入 tools 列表

```python
MCP_CONFIG = ".agent/mcp.json"

def load_mcp_tools():
    if not os.path.exists(MCP_CONFIG):
        return []
    try:
        with open(MCP_CONFIG, "r") as f:
            config = json.load(f)
            mcp_tools = []
            for server_name, server_config in config.get("mcpServers", {}).items():
                if server_config.get("disabled", False):
                    continue
                for tool in server_config.get("tools", []):
                    mcp_tools.append({"type": "function", "function": tool})
            return mcp_tools
    except:
        return []
```

Rule 和 Skill 进入 prompt，MCP 工具进入 tools 列表。这个差异很重要：

```python
all_tools = base_tools + mcp_tools
```

对模型来说，MCP 加载出来的 `demo_release_policy` 和内置的 `read`、`write`、`bash` 一样，都是可以选择调用的工具。

---

## 五、三类配置如何组装

```python
def run_agent_with_external_capabilities(task):
    rule_count = count_rule_files()
    rules = load_rules()
    skills = load_skills()
    mcp_tools = load_mcp_tools()
    all_tools = base_tools + mcp_tools

    context_parts = [
        "You are a helpful assistant that can interact with the system. Be concise."
    ]
    if rules:
        context_parts.append(f"\n# Rules\n{rules}")
        print(f"[Rules] Loaded {rule_count} rule files")
    if skills:
        context_parts.append(
            f"\n# Skills\n"
            + "\n\n".join(format_skill_for_prompt(skill) for skill in skills)
        )
        skill_names = [skill["name"] for skill in skills]
        print(f"[Skills] Loaded {len(skills)} skill files: {', '.join(skill_names)}")
    if mcp_tools:
        tool_names = [tool["function"]["name"] for tool in mcp_tools]
        print(f"[MCP] Loaded {len(mcp_tools)} MCP tools: {', '.join(tool_names)}")
```

最终结构可以记成一句话：

```text
Rules + Skills → system prompt
MCP            → tools
```

---

## 六、实际运行效果

### 推荐演示：一条命令同时看 Rule、Skill、MCP

```bash
python3 agent/03-skills-mcp/agent-skills-mcp.py "请先调用 demo_release_policy 获取发布策略。然后按 release_triage 对这三个发布前问题排序：A 应用启动报错；B 删除数据没有二次确认；C 按钮颜色不统一。最后严格按 Rule 要求输出三行。"
```

观察点：

```text
[Rules] Loaded 1 rule files
[Skills] Loaded 1 skill files: release_triage
[MCP] Loaded 1 MCP tools: demo_release_policy
[Tool] demo_release_policy(...)
```

前三行证明外置配置已经被加载；看到 `[Tool] demo_release_policy(...)`，就能证明 MCP 工具已经进入 tools 列表，并被模型实际调用。

再看最终回答，效果会非常直观：

```text
Rule证据：最终回答按三行固定格式输出。
Skill证据：排序：B > A > C，先保数据安全。
MCP证据：策略要求只演示、不修改文件。
```

这里三件事同时发生：Rule 改变输出格式，Skill 改变排序逻辑，MCP 提供一条可调用的外部发布策略。

---

## 七、本讲结论

第三讲只回答一个问题：如何不改 Python 代码，也能改变 Agent 的行为、知识和工具？

答案是三类外置能力：

1. Rule 改变约束。
2. Skill 改变做法。
3. MCP 改变可调用工具。

从第二讲到第三讲，递进关系也很清楚：Memory 解决“记得住”，Rules、Skills、MCP 解决“能力可以从项目配置里长出来”。
