# 从零开始理解 Agent（番外）：Skill 的渐进式披露——别把整本手册一次性塞给 Agent

> 上次技术分享时，有小伙伴问："Skill 的渐进式加载是怎么实现的？" 这个问题问得好——[第三篇](../03-skills-mcp/agent-skills-mcp.md)我们实现了 Skill 的基础加载，把名称和描述注入 system prompt，但没有回答一个问题：**如果 Agent 有 50 个 Skill，每个 SKILL.md 有 300 行，怎么办？**
>
> 50 × 300 = 15000 行。全部塞进 system prompt，context window 还没开始干活就用掉了大半。更糟糕的是，大部分 Skill 跟当前任务根本没关系——用户只是想查个文档，你把 Docker 部署、数据库迁移、前端构建的操作手册全塞进去了。
>
> 这篇番外就来回答这个问题。

---

## 一、问题：Skill 越多，Agent 越吃力

先量化一下。回忆第三篇的 Skill 加载方式：

```python
def format_skills(skills):
    lines = []
    for s in skills:
        lines.append(f"- {s['name']}: {s['description']}")
    return "\n".join(lines)
```

这段代码只注入了名称和一句话描述，每个 Skill 大概 50-100 Token。10 个 Skill 最多 1000 Token，可以接受。

但第三篇也说了，Skill 不只是一句话描述——它是一个文件夹，里面有 SKILL.md（操作指南）、脚本、参考资料。一个稍微复杂的 Skill（比如"文档知识库检索"），光 SKILL.md 就可能有几十行操作步骤，再加上目录索引文件和辅助脚本，整个 Skill 文件夹的内容轻松过百行。如果你把完整的 SKILL.md 全部塞进 system prompt，两个问题：

**1. Token 浪费。** 用户说"帮我写个 Python 脚本"，Docker 部署 Skill 的 50 行操作手册白白占了 context。每轮都要付这个固定税。

**2. LLM 注意力被稀释。** 长上下文里常见的 "Lost in the Middle" 问题是：内容越多，中间信息越容易被忽略。塞了 10 个无关 Skill 的操作手册，LLM 可能反而找不到那个真正有用的 Skill。

一句话概括：**把所有 Skill 完整塞进 system prompt，就像员工入职第一天就把整个公司的 SOP 手册全部打印出来堆在桌上——信息过载，找不到重点。**

---

## 二、解法：渐进式披露

正常公司不会这么干。新员工入职时拿到的是一份目录：

```
公司手册目录
├── HR 制度（请假、考勤、报销）
├── 开发规范（代码审查、分支策略、部署流程）
├── 运维手册（监控、告警、故障处理）
└── 安全合规（数据分类、访问控制）
```

需要请假了，去翻 HR 那一章；要部署了，去翻运维那一章。不会在写代码的时候翻安全合规手册。

这就是**渐进式披露（Progressive Disclosure）**的核心思想：

```
Level 0：Agent 启动时只看到 Skill 目录（名称 + 一句话描述）
Level 1：LLM 根据任务选中某个 Skill，外层代码加载它的 SKILL.md 正文
Level 2：LLM 需要具体操作细节时，外层代码继续读取 Skill 里的子文件
```

每一层只给 LLM 它当前阶段需要的信息量。从"整本手册"变成"先看目录 → 再看章节 → 再看具体步骤"。

---

## 三、第三篇的代码：Level 0 已经有了

回头看第三篇的脚本，其实它已经做了 Level 0：

```python
# 第三篇的实现（简化）
SKILLS = [
    {
        "name": "docker-deploy",
        "description": "Docker 容器化部署，支持 build / up / down",
        "steps": "1) Check Dockerfile exists ..."
    },
    {
        "name": "doc-search",
        "description": "本地文档知识库检索，支持分层导航和渐进式检索",
        "steps": "1) Read data_structure.md ..."
    }
]

system_prompt = BASE_PROMPT + "\n# Available Skills\n" + format_skills(SKILLS)
```

`format_skills` 只提取了 `name` 和 `description`，没有把 `steps` 塞进去。这就是 Level 0——LLM 知道"有哪些 Skill 可用"，但不知道每个 Skill 的具体操作步骤。

问题是：**LLM 选中一个 Skill 之后怎么办？** 如果我们继续把 `steps` 这类操作细节提前放进 prompt，Skill 少的时候还能接受，Skill 一多就会回到全量注入的问题。

---

## 四、实现 Level 1：按需加载 SKILL.md

核心想法很简单——给 Agent 加一个新工具 `load_skill`，让 LLM 自己决定什么时候加载哪个 Skill 的详细内容：

```python
SKILLS_DIR = Path(__file__).resolve().parent / "skills"

def load_skill(name: str) -> str:
    """加载指定 Skill 的完整操作指南"""
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.exists():
        return f"Error: Skill '{name}' not found"
    content = skill_file.read_text(encoding="utf-8")
    return re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL).strip()
```

对应的 tool schema：

```python
LOAD_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "加载一个 Skill 的完整操作指南。当你确定当前任务需要某个 Skill 时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill 名称，从 Available Skills 列表中选择"
                }
            },
            "required": ["name"]
        }
    }
}
```

加上这个工具后，Agent 的行为变了：

```
用户：咨询病假怎么处理

→ LLM 看到 Available Skills 列表，发现 "doc-search" 匹配
→ LLM 调用 load_skill("doc-search")
→ 外层代码读取 skills/doc-search/SKILL.md，返回检索指南
→ LLM 继续按指南读取目录索引和请假制度
```

**是 LLM 在做加载决策。** 外层代码只提供 `load_skill` 工具，不写 if-else 路由规则，也不做关键词匹配。LLM 看到任务描述和 Skill 列表后，自己决定要不要加载、加载哪一个。这就是第三篇说的"Skill 的 description 是触发器"的实际应用。

---

## 五、Level 2：Skill 内部的分层

Level 1 解决了"Skill 之间的按需加载"。但如果一个 Skill 本身就很大呢？

想象一个"文档知识库检索"Skill——它有 SKILL.md（总入口）、data_structure.md（目录索引）、knowledge/HR/leave_policy.md（具体制度）、还有辅助脚本。全部加起来上千行。

一次性加载全部内容不合理。更好的做法是在 SKILL.md 里写清楚**引用关系**，让 LLM 按需继续加载：

```markdown
# 文档知识库检索 Skill

## 快速开始
1. 先调用 read_file("skills/doc-search/data_structure.md") 查看目录索引
2. 根据目录定位到目标子目录
3. 定位到具体制度后，调用 read_file("skills/doc-search/knowledge/HR/leave_policy.md")

## 注意
- 不要直接读取大文件，先看目录索引再局部读取
- 最多迭代 5 轮
```

看到了吗？SKILL.md 不包含 data_structure.md 和 leave_policy.md 的内容，只告诉 LLM 这些文件在哪、什么时候去读。LLM 按需加载，逐步深入。

这就是"Skill 是文件夹不是文件"这句话的真正含义——**文件夹的目录结构本身就是 Agent 的认知地图。** LLM 先看 SKILL.md（入口），再根据需要读子文件（细节），整个过程是 LLM 自驱的。

---

## 六、注册表升级：从 JSON 到文件系统

第三篇用一个 Python 字典存 Skill 注册信息。现在我们升级为真正的文件系统结构：

```
skills/
├── code-review/
│   └── SKILL.md
├── doc-search/
│   ├── SKILL.md
│   ├── data_structure.md
│   └── knowledge/
│       ├── HR/
│       │   ├── data_structure.md
│       │   ├── expense_policy.md
│       │   └── leave_policy.md
│       ├── ops/
│       │   └── deploy_runbook.md
│       └── security/
│           └── access_control.md
├── docker-deploy/
│   └── SKILL.md
└── registry.json          ← Skill 注册表
```

配套脚本已经把这组示例 Skill 放在 `agent/17-skill-progressive/skills/`，运行时不需要再执行初始化命令。

`registry.json` 只存名称和描述，是 Level 0 的目录：

```json
[
    {
        "name": "code-review",
        "description": "代码审查，支持多维度检查和结构化报告。Use when user asks to review, 代码审查, CR, 检查代码。"
    },
    {
        "name": "doc-search",
        "description": "本地文档知识库检索，支持分层导航和渐进式检索。Use when user asks to 查文档, 搜索知识库, 找资料, 查制度。"
    },
    {
        "name": "docker-deploy",
        "description": "Docker 容器化部署，支持 build / up / down / 健康检查。Use when user asks to deploy, docker, 容器部署, 上线。"
    }
]
```

脚本启动时会扫描这组文件并刷新注册表：遍历 `skills/` 目录，读每个 SKILL.md 的 YAML frontmatter：

```python
def build_registry() -> list:
    """扫描 skills 目录，生成注册表"""
    if not SKILLS_DIR.exists():
        return []
    registry = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        content = skill_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(content)
        registry.append({
            "name": meta.get("name", skill_dir.name),
            "description": meta.get("description", f"Skill: {skill_dir.name}")
        })
    REGISTRY_FILE.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return registry
```

新增一个 Skill 只需要创建一个文件夹、写一个 SKILL.md，注册表自动更新。零配置。

---

## 七、完整流程：从用户提问到 Skill 执行

把三个 Level 串起来：

```
用户："咨询病假怎么处理"

Level 0 —— Skill 目录（system prompt 中）
  LLM 扫描 Available Skills：
  - code-review: 代码审查...                   ← 无关
  - doc-search: 本地文档知识库检索...           ← 匹配！
  - docker-deploy: Docker 容器化部署...        ← 无关

Level 1 —— 加载 SKILL.md
  LLM 调用 load_skill("doc-search")
  → 外层代码返回 doc-search/SKILL.md 的内容
  → LLM 读到：先调用 read_file("skills/doc-search/data_structure.md") 查目录

Level 2 —— Skill 内部分层导航
  LLM 调用 read_file("skills/doc-search/data_structure.md")
  → 看到 HR、ops、security 三类资料
  → 选择 HR 目录
  → 调用 read_file("skills/doc-search/knowledge/HR/data_structure.md")
  → 看到 leave_policy.md
  → 调用 read_file("skills/doc-search/knowledge/HR/leave_policy.md")
  → 回复用户
```

整个过程中，docker-deploy 和 code-review 的 SKILL.md 从未被加载过——它们的 Token 开销为零。doc-search 的内容也是逐步加载的，每一步只读取当前需要的文件。

---

## 八、对比：三种 Skill 加载策略

| 策略 | system prompt 占用 | 适用场景 |
|------|-------------------|---------|
| 全量加载（简单版） | 所有 Skill 的完整内容 | Skill ≤ 3 个，每个很短 |
| 摘要 + 按需加载（本文） | 只有名称和描述 | Skill 5~50 个，通用场景 |
| 语义搜索（元工具） | 零（连目录都不放） | Skill > 50 个，需要额外基础设施 |

第三种是上一层楼——当 Skill 多到连目录摘要都塞不下时，你需要一个 `search_skills(query)` 元工具，让 LLM 用自然语言检索 Skill 库。原理和文档检索 Skill 的分层索引类似，只不过检索对象从"文档"变成了"Skill"。这篇不展开，但思路完全对称。

对大多数场景来说，中间那一栏（摘要 + 按需加载）就够了。它不需要向量数据库，不需要额外基础设施，核心只是一个 `load_skill` 工具和一份 registry.json。

---

## 九、一个容易忽略的细节：加载后怎么注入

`load_skill` 返回了 SKILL.md 的内容，然后呢？它在 messages 列表里是一条 tool result：

```python
{
    "role": "tool",
    "tool_call_id": "call_xxx",
    "content": "# 文档知识库检索 Skill\n\n## 快速开始\n..."
}
```

这意味着 Skill 内容作为 tool result 进入了对话历史。它的好处是：LLM 在后续轮次可以继续引用这个 Skill 的内容，不需要重复加载。但如果对话很长（比如跑了 20 轮），这条 tool result 会停留在 messages 里，持续占用 Token。

两种处理方式：

**方式一：让压缩机制自然处理。** 第六篇讲的上下文压缩会把旧的 messages 压缩成摘要。Skill 内容作为早期的 tool result，会被压缩掉，不会永久占用空间。

**方式二：注入 system prompt 而不是 tool result。** `load_skill` 不作为工具返回，而是让外层代码把 Skill 内容追加到 system prompt 的末尾。这样每轮都带，但 Token 成本恒定（不随历史增长），且不会被压缩丢失。

两种各有取舍。方式一更简单（不改 system prompt 的生成逻辑），方式二更稳定（Skill 不会被压缩掉）。配套脚本用的是方式一，因为它和前面几讲的工具回填逻辑最一致。

---

## 小结

这篇番外做了一件事：**把 Skill 的加载从"一次性全量注入"变成"按需逐层披露"。**

```
简单版：Skill 提前注入 → 能用，但不 scale
本  文：渐进式披露   → 目录 → 指南 → 具体文件，按需加载
```

核心是一个 `load_skill` 工具和一份 `registry.json`，再复用 `read_file` 做细节读取。改动不大，但解决了 Skill 数量增长后的两个问题：Token 浪费和注意力稀释。

> 第三篇说过：Skill 告诉 Agent「可以怎么做」。这篇番外加了一个约束：**不是一次性全部告诉，而是需要的时候再告诉。**

---

*本文是「从零开始理解 Agent」系列番外篇。完整系列见 [GitHub 仓库](https://github.com/GitHubxsy/nanoAgent)。*
