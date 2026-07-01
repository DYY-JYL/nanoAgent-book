---
name: python-agent-analysis
description: Analyze Python Agent repositories and explain tools schema conversion, tool calls, agent loops, Skills/MCP extension, and subagent interaction.
when_to_use: Use when the user asks to analyze an Agent codebase, nanoAgent implementation, LangChain tool calling, MCP integration, subagents, or Claude Code style architecture.
triggers: agent, nanoagent, langchain, tool, tools schema, agent loop, subagent, mcp, skill, claude code
---

Use this skill to analyze a Python repository that implements an Agent.

Recommended workflow:

1. Call `scan_python_repo(path)` to understand the repository shape.
2. Call `extract_agent_features(path)` to collect evidence for:
   - tools schema / tool declaration
   - tool invocation
   - agent loop
   - subagent interaction
   - Skills / MCP extension points
3. If a file is important, call `summarize_python_file(path)` or `read_code_excerpt(path, start_line, limit)`.
4. If the user asks for deeper explanation, call `explain_agent_feature(feature, files)` as a focused code-reading subagent.
5. Answer directly in chat with concrete file paths and line numbers.

Do not write a Markdown report unless the user explicitly asks for a file.
