# 从零开始写好 Skill —— 系列导读

这个系列讲一件事：如何把一次性的经验，写成 Agent 可以反复调用的工作手册。

如果说 Agent 是“会调用工具的执行者”，Skill 就是给 Agent 的“操作说明书”：什么时候触发、按什么步骤做、遇到异常如何兜底、输出应该长什么样。

---

## 这个系列讲什么

很多人会让 Agent 做任务，但每次都要重复说明背景、格式和注意事项。Skill 要解决的正是这个问题：把稳定的流程沉淀下来，让 Agent 在合适的场景自动复用。

读完这个系列，你会理解：

- Skill 为什么能影响 Agent 行为
- 一个好的 `SKILL.md` 应该怎么组织
- 如何从零写出第一个可用 Skill
- 如何用 `skill-creator` 提高编写和迭代效率
- 多个 Skill 如何组合完成更复杂的任务
- Skill 在 Agent 完整工作流中的位置与边界

---

## 文章目录

| # | 目录 | 文章 | 核心主题 |
|---|------|------|----------|
| 01 | [01-what-is-skill/](./01-what-is-skill/) | [Skill 是什么？为什么你应该关心它](./01-what-is-skill/nano-skill-01-what-is-skill.md) | Skill 的本质与使用场景 |
| 02 | [02-anatomy-of-skill/](./02-anatomy-of-skill/) | [一个好 Skill 长什么样——SKILL.md 的解剖](./02-anatomy-of-skill/nano-skill-02-anatomy-of-skill.md) | `SKILL.md` 结构拆解 |
| 03 | [03-first-skill/](./03-first-skill/) | [手把手写你的第一个 Skill](./03-first-skill/nano-skill-03-first-skill.md) | 从零编写与迭代 |
| 04 | [04-skill-creator/](./04-skill-creator/) | [写 Skill 太费劲？让 skill-creator 来帮你](./04-skill-creator/nano-skill-04-skill-creator.md) | 用元技能辅助创作 |
| 05 | [05-composition/](./05-composition/) | [拆开写，串起用——Skill 的组合之道](./05-composition/nano-skill-05-composition.md) | 多 Skill 协作与组合 |
| 06 | [06-agent-workflow/](./06-agent-workflow/) | [从 Skill 到 Agent 工作流——全局视角](./06-agent-workflow/nano-skill-06-agent-workflow.md) | Skill 与 Rules、Memory、MCP 的边界 |

---

## 推荐阅读路径

第一次阅读建议按编号顺序：

```text
01-what-is-skill → 02-anatomy-of-skill → 03-first-skill → 04-skill-creator → 05-composition → 06-agent-workflow
```

如果已经知道 Skill 是什么，可以直接从第二篇开始，把 `SKILL.md` 的结构和写法先建立起来。

---

## 和 Agent 系列的关系

Skill 系列是 [从零开始理解 Agent](../agent/README.md) 的延伸。

Agent 系列回答“Agent 如何工作”，Skill 系列回答“如何把人类经验写成 Agent 能复用的能力”。建议先读完 Agent 系列前三篇，再阅读本系列。
