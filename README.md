# nanoAgent

这个仓库按三套系列文章组织，像一本从底层原理到工程实践的小书，拆解大模型、Agent 与 Skill 的核心概念。

- **[从零开始理解大模型](./llm/README.md)**：理解 LLM 的底层机制
- **[从零开始理解 Agent](./agent/README.md)**：理解模型如何调用工具、记忆、规划和协作
- **[从零开始写好 Skill](./skill/README.md)**：理解如何给 Agent 编写可复用的工作手册

建议阅读顺序：先读 **大模型** 建立底层直觉，再读 **Agent** 理解模型如何长出手脚，最后读 **Skill** 学会把经验沉淀为可复用能力。

---

## 第一部：从零开始理解大模型

从“预测下一个 token”开始，逐步理解 Token、Embedding、Attention、Transformer、训练、推理、上下文窗口、Scaling Law，再扩展到 Agent、多模态、GPU、计费、思考模式、MoE 与算子。

系列导读：[llm/README.md](./llm/README.md)

| 章 | 标题 | 目录 |
|---|------|------|
| 01 | 一切从“猜下一个词”开始 | [llm/01-next-token/](./llm/01-next-token/) |
| 02 | Token：大模型眼中的“字”长什么样 | [llm/02-token/](./llm/02-token/) |
| 03 | 向量与 Embedding：把文字变成数学 | [llm/03-embedding/](./llm/03-embedding/) |
| 04 | Attention：大模型的“阅读理解”机制 | [llm/04-attention/](./llm/04-attention/) |
| 05 | Transformer 全景：积木怎么搭成大厦 | [llm/05-transformer/](./llm/05-transformer/) |
| 06 | 训练：70 亿个参数是怎么“学”出来的 | [llm/06-training/](./llm/06-training/) |
| 07 | 推理：你按下回车后的这一秒发生了什么 | [llm/07-inference/](./llm/07-inference/) |
| 08 | 上下文窗口：大模型的“工作记忆”到底有多大 | [llm/08-context-window/](./llm/08-context-window/) |
| 09 | Scaling Law：为什么“大力出奇迹”有效 | [llm/09-scaling-law/](./llm/09-scaling-law/) |
| 10 | 从大模型到 Agent：下一个词预测如何长出手脚 | [llm/10-agent/](./llm/10-agent/) |
| 11 | 多模态：大模型是怎么“看懂”图片的 | [llm/11-multimodal/](./llm/11-multimodal/) |
| 12 | 为什么大模型离不开 GPU | [llm/12-gpu/](./llm/12-gpu/) |
| 13 | 为什么用 Token 计费？为什么输出比输入贵？ | [llm/13-token-pricing/](./llm/13-token-pricing/) |
| 14 | 思考模式和非思考模式到底有什么区别？ | [llm/14-thinking-mode/](./llm/14-thinking-mode/) |
| 15 | MoE：总参数 1.6T，激活参数 49B 是什么意思 | [llm/15-moe/](./llm/15-moe/) |
| 16 | 算子：大模型里的“最小施工单位” | [llm/16-operators/](./llm/16-operators/) |

---

## 第二部：从零开始理解 Agent

从一个极简 Agent 出发，逐步加入记忆、规划、Rules、Skills、MCP、SubAgent、多 Agent 团队、上下文压缩与安全防线，再补充文件系统、Token、工具选择、流式输出、Command、可观测性、评估、Agent 创建模式和真实 MCP 接入。

系列导读：[agent/README.md](./agent/README.md)

| 章 | 标题 | 目录 |
|---|------|------|
| 01 | 底层原理：只有 100 行 | [agent/01-essence/](./agent/01-essence/) |
| 02 | 记忆与规划 | [agent/02-memory/](./agent/02-memory/) |
| 03 | Rules、Skills 与 MCP 机制 | [agent/03-skills-mcp/](./agent/03-skills-mcp/) |
| 04 | SubAgent：给 Agent 找个帮手 | [agent/04-subagent/](./agent/04-subagent/) |
| 05 | 多智能体协作与编排 | [agent/05-teams/](./agent/05-teams/) |
| 06 | 上下文压缩 | [agent/06-compact/](./agent/06-compact/) |
| 07 | 安全与权限控制 | [agent/07-safety/](./agent/07-safety/) |
| 08 | 为什么 Agent 需要一个文件系统？ | [agent/08-filesystem/](./agent/08-filesystem/) |
| 09 | Token 都花在哪了？ | [agent/09-token/](./agent/09-token/) |
| 10 | LLM 是怎么从一堆工具里挑出正确工具的？ | [agent/10-tool-selection/](./agent/10-tool-selection/) |
| 11 | 流式输出：别让用户干等 | [agent/11-streaming/](./agent/11-streaming/) |
| 12 | Command：不是所有操作都要过大脑 | [agent/12-command/](./agent/12-command/) |
| 13 | 可观测性：Agent 出了问题怎么排查？ | [agent/13-observable/](./agent/13-observable/) |
| 14 | Eval：Agent 怎么知道自己做完了？ | [agent/14-eval/](./agent/14-eval/) |
| 15 | 谁来创建 Agent？主 Agent 创建 vs 用户创建 | [agent/15-agent-creation-modes/](./agent/15-agent-creation-modes/) |
| 16 | 真正的 MCP 长什么样？ | [agent/16-mcp-real/](./agent/16-mcp-real/) |
| 附录 | 七篇合一：完整 Agent | [agent/full/](./agent/full/) |

---

## 第三部：从零开始写好 Skill

理解 Skill 是什么、一个好 Skill 如何组织、如何从零写第一个 Skill、如何用 skill-creator 辅助创作、多个 Skill 如何组合完成复杂任务，以及 Skill 在 Agent 工作流中的位置。

系列导读：[skill/README.md](./skill/README.md)

| 章 | 标题 | 目录 |
|---|------|------|
| 01 | Skill 是什么？为什么你应该关心它 | [skill/01-what-is-skill/](./skill/01-what-is-skill/) |
| 02 | 一个好 Skill 长什么样：SKILL.md 的解剖 | [skill/02-anatomy-of-skill/](./skill/02-anatomy-of-skill/) |
| 03 | 手把手写你的第一个 Skill | [skill/03-first-skill/](./skill/03-first-skill/) |
| 04 | 写 Skill 太费劲？让 skill-creator 来帮你 | [skill/04-skill-creator/](./skill/04-skill-creator/) |
| 05 | 拆开写，串起用：Skill 的组合之道 | [skill/05-composition/](./skill/05-composition/) |
| 06 | 从 Skill 到 Agent 工作流：全局视角 | [skill/06-agent-workflow/](./skill/06-agent-workflow/) |

## License

[MIT](./LICENSE)
