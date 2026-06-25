# LangChain 文件修改 Agent

这个 minitask 用 LangChain 复刻 nanoAgent 的核心形态：**LLM + 工具 + 循环**。不同点是这里用 `ChatOpenAI.bind_tools()` 来绑定工具，用 `ToolMessage` 把工具结果送回模型。

目标流程：

1. 用户输入：`帮我修改 xxx 目录下的文件`
2. 主 Agent 调用 `scan_directory` 扫描目录
3. 主 Agent 调用 `ask_user_choice` 让用户选择目标文件
4. 主 Agent 追问行号和替换内容
5. 主 Agent 调用 `delegate_to_file_subagent`
6. 子 Agent 调用 `read_file_line` 和 `replace_file_line` 完成修改
7. 主 Agent 校验并总结

运行：

```bash
pip install -r agent/requirements.txt
export OPENAI_API_KEY="your-key"

python agent/minitask/agent-langchain-file.py "帮我修改 ./demo 目录下的文件"
```

配置文件：

默认读取：

```bash
agent/minitask/agent_config.json
```

可以在配置里改模型、base_url、记忆文件、最大循环轮次和 prompt：

```json
{
  "model": "deepseek-v4-pro",
  "base_url": "https://api.deepseek.com",
  "memory_file": "langchain_file_agent_memory.md",
  "max_iterations": 10
}
```

也可以指定另一份配置：

```bash
NANO_FILE_AGENT_CONFIG=./my_config.json python agent/minitask/agent-langchain-file.py
```

`OPENAI_API_KEY` 继续放环境变量里，不写进配置文件。

核心点：

- **工具调用**：目录扫描、选择题、读文件、改文件、拉起子 Agent 都是工具。
- **状态管理**：`AgentSession.messages` 保存多轮上下文，`STATE` 保存目录扫描和选择结果，`langchain_file_agent_memory.md` 保存简短历史。
- **子 Agent 调度**：主 Agent 不直接写文件，而是把明确的文件、行号、内容交给 `file-editor` 子 Agent。
- **保持简洁**：没有引入 LangGraph 或复杂状态机，代码形状仍然接近 nanoAgent 的教学版本。
