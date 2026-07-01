"""
agent-repo-analyzer.py - 可扩展交互式 Agent（Skills + MCP）

这版不再是固定的“生成 Markdown 报告”脚本，而是一个更像 Claude Code 的
通用交互式 Agent：
  1. 启动时加载 Rules
  2. 启动时加载 Skills
  3. 从 mcp.json 加载 MCP 风格工具 schema
  4. 在多轮对话里按需调用工具
  5. Python Agent 仓库分析能力作为一个 Skill + 一组 MCP 工具接入

用法:
  python agent/minitask/agent-repo-analyzer.py
  python agent/minitask/agent-repo-analyzer.py "分析 agent/full 里的 agent loop"
"""

import ast
import glob as glob_module
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(
    os.environ.get("NANO_REPO_ANALYZER_CONFIG", SCRIPT_DIR / "repo_analyzer_config.json")
).expanduser()

DEFAULT_CONFIG = {
    "model": "deepseek-v4-pro",
    "base_url": "https://api.deepseek.com",
    "agent_home": ".agent",
    "memory_file": "repo_analyzer_memory.md",
    "max_iterations": 12,
    "max_files": 80,
    "max_file_chars": 18000,
    "max_tool_output": 8000,
    "compact_threshold": 24,
    "keep_recent": 8,
}


# ==================== 配置、记忆、路径 ====================


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    config = DEFAULT_CONFIG.copy()
    config.update(user_config)
    return config


CONFIG = load_config()
MODEL = os.environ.get("OPENAI_MODEL", CONFIG["model"])


def config_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = CONFIG_FILE.parent / path
    return path


AGENT_HOME = config_path(CONFIG["agent_home"])
RULES_DIR = AGENT_HOME / "rules"
SKILLS_DIR = AGENT_HOME / "skills"
MCP_CONFIG = AGENT_HOME / "mcp.json"
MEMORY_FILE = config_path(CONFIG["memory_file"])


def resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def load_memory() -> str:
    if not MEMORY_FILE.exists():
        return ""
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-80:])


def save_memory(user_input: str, result: str):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**User:** {user_input}\n"
        f"**Agent:** {result[:800]}\n"
    )
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def truncate_output(text: str) -> str:
    limit = int(CONFIG["max_tool_output"])
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + f"\n\n... [已截断，原始 {len(text)} 字符] ...\n\n" + text[-half:]


def compact_messages(messages: List[Any]) -> List[Any]:
    threshold = int(CONFIG["compact_threshold"])
    if len(messages) <= threshold:
        return messages

    keep_recent = int(CONFIG["keep_recent"])
    system_msg = messages[0]
    old_messages = messages[1:-keep_recent]
    recent_messages = messages[-keep_recent:]
    old_text = "\n".join(
        f"[{getattr(msg, 'type', msg.__class__.__name__)}] {message_text(msg)}"
        for msg in old_messages
        if message_text(msg)
    )

    print(f"\n[Compact] {len(old_messages)} 条旧消息 -> 摘要")
    summary = build_llm().invoke(
        [
            SystemMessage(
                content="Summarize this conversation. Keep important paths, decisions, tool results, and user intent. Be concise."
            ),
            HumanMessage(content=old_text),
        ]
    ).content

    return [
        system_msg,
        HumanMessage(content=f"[Previous conversation summary]\n{summary}"),
        AIMessage(content="Understood. I will continue from this summary."),
        *recent_messages,
    ]


# ==================== Base tools：通用文件与搜索能力 ====================


def read(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    try:
        file_path = resolve_path(path)
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        start = offset or 0
        end = start + limit if limit else len(lines)
        return "\n".join(f"{i + 1:4d} {line}" for i, line in enumerate(lines[start:end], start))
    except Exception as e:
        return f"Error: {e}"


def write(path: str, content: str) -> str:
    try:
        file_path = resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error: {e}"


def edit(path: str, old_string: str, new_string: str) -> str:
    try:
        file_path = resolve_path(path)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        count = content.count(old_string)
        if count != 1:
            return f"Error: old_string must appear exactly once, found {count}"
        file_path.write_text(content.replace(old_string, new_string), encoding="utf-8")
        return f"Successfully edited {file_path}"
    except Exception as e:
        return f"Error: {e}"


def glob(pattern: str) -> str:
    try:
        files = glob_module.glob(pattern, recursive=True)
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return "\n".join(files) if files else "No files found"
    except Exception as e:
        return f"Error: {e}"


def grep(pattern: str, path: str = ".") -> str:
    try:
        result = subprocess.run(
            ["grep", "-R", "-n", pattern, path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout if result.stdout else "No matches found"
    except Exception as e:
        return f"Error: {e}"


BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read a local text file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write a local text file. Use only when the user explicitly asks to create or update a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Replace one exact string in a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files by glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search text in files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["pattern"],
            },
        },
    },
]


# ==================== MCP 工具实现：Python Agent 仓库分析 ====================


STATE: Dict[str, Any] = {"python_files": [], "last_features": {}}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"}


def iter_python_files(root: Path) -> List[Path]:
    if root.is_file() and root.suffix == ".py":
        return [root]
    files = []
    for p in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        files.append(p)
    return sorted(files)[: int(CONFIG["max_files"])]


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[: int(CONFIG["max_file_chars"])]


def line_no(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return ""


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def summarize_ast(path: Path, text: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {"path": relative(path), "syntax_error": str(e)}

    functions = []
    classes = []
    tool_decorators = []
    interesting_calls = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [decorator_name(d) for d in node.decorator_list]
            functions.append({"name": node.name, "line": node.lineno, "decorators": [d for d in decorators if d]})
            if "tool" in decorators:
                tool_decorators.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.Call):
            name = call_name(node.func)
            if any(key in name for key in ("bind_tools", "invoke", "create", "ToolMessage", "run_agent", "subagent")):
                interesting_calls.append({"name": name, "line": getattr(node, "lineno", None)})

    return {
        "path": relative(path),
        "functions": functions[:60],
        "classes": classes[:30],
        "tool_decorators": tool_decorators,
        "interesting_calls": interesting_calls[:50],
    }


FEATURE_PATTERNS = {
    "tool_schema_openai": r'"type"\s*:\s*"function"|["\']parameters["\']\s*:',
    "tool_schema_langchain": r"@tool\b|bind_tools\s*\(|convert_to_openai_tool",
    "tool_registry": r"available_functions|tool_map|raw_functions|BASE_TOOLS|TOOLS|tools\s*=",
    "tool_call_read": r"tool_calls|function\.name|function\.arguments",
    "tool_call_execute": r"\.invoke\s*\(|ToolMessage\s*\(|tool_call_id|available_functions\[|tool_map\[",
    "agent_loop": r"for\s+.*range\(.*\):|while\s+True:",
    "llm_call": r"chat\.completions\.create|llm_with_tools\.invoke|client\.chat|ChatOpenAI|build_llm",
    "message_state": r"messages\.append|self\.messages|SystemMessage|HumanMessage",
    "subagent": r"subagent|SubAgent|delegate_to_|run_.*subagent|子\s*Agent",
    "skill": r"load_skills|SKILL\.md|format_skill_for_prompt|Skills",
    "mcp": r"load_mcp_tools|mcp\.json|MCP_CONFIG|mcpServers",
}


def find_patterns(text: str) -> List[Dict[str, Any]]:
    findings = []
    for kind, pattern in FEATURE_PATTERNS.items():
        for match in re.finditer(pattern, text, flags=re.MULTILINE):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            findings.append({"kind": kind, "line": line_no(text, match.start()), "evidence": text[start:end].strip()})
    return findings


def scan_python_repo(path: str) -> str:
    root = resolve_path(path)
    if not root.exists():
        return f"Error: path not found: {root}"
    files = iter_python_files(root)
    STATE["python_files"] = [str(p) for p in files]
    rows = []
    for p in files:
        rows.append({"path": relative(p), "lines": read_text(p).count("\n") + 1, "bytes": p.stat().st_size})
    return json.dumps({"root": str(root), "files": rows}, ensure_ascii=False, indent=2)


def summarize_python_file(path: str) -> str:
    file_path = resolve_path(path)
    if not file_path.exists():
        return f"Error: path not found: {file_path}"
    return json.dumps(summarize_ast(file_path, read_text(file_path)), ensure_ascii=False, indent=2)


def read_code_excerpt(path: str, start_line: int = 1, limit: int = 120) -> str:
    return read(path, offset=max(start_line - 1, 0), limit=limit)


def extract_agent_features(path: str) -> str:
    root = resolve_path(path)
    files = iter_python_files(root)
    result: Dict[str, Any] = {
        "root": str(root),
        "files_scanned": len(files),
        "features": {
            "tools_schema": [],
            "tool_invocation": [],
            "agent_loop": [],
            "subagent_interaction": [],
            "skills_mcp_extension": [],
        },
    }

    for file_path in files:
        text = read_text(file_path)
        summary = summarize_ast(file_path, text)
        rel = relative(file_path)
        for item in find_patterns(text):
            payload = {"file": rel, "line": item["line"], "kind": item["kind"], "evidence": item["evidence"]}
            if item["kind"].startswith("tool_schema") or item["kind"] == "tool_registry":
                result["features"]["tools_schema"].append(payload)
            elif item["kind"].startswith("tool_call"):
                result["features"]["tool_invocation"].append(payload)
            elif item["kind"] in {"agent_loop", "llm_call", "message_state"}:
                result["features"]["agent_loop"].append(payload)
            elif item["kind"] == "subagent":
                result["features"]["subagent_interaction"].append(payload)
            elif item["kind"] in {"skill", "mcp"}:
                result["features"]["skills_mcp_extension"].append(payload)
        for tool_fn in summary.get("tool_decorators", []):
            result["features"]["tools_schema"].append(
                {"file": rel, "line": tool_fn["line"], "kind": "langchain_tool_decorator", "evidence": f"@tool function: {tool_fn['name']}"}
            )

    for key in result["features"]:
        result["features"][key] = result["features"][key][:40]
    STATE["last_features"] = result
    return json.dumps(result, ensure_ascii=False, indent=2)


def explain_agent_feature(feature: str, files: List[str]) -> str:
    snippets = []
    for file in files[:4]:
        path = resolve_path(file)
        if path.exists() and path.suffix == ".py":
            snippets.append(f"\n# {relative(path)}\n{read_code_excerpt(str(path), 1, 180)}")
    if not snippets:
        return "Error: no readable Python files provided"

    messages = [
        SystemMessage(
            content=(
                "You are a code reading sub-agent. Explain only the provided code. "
                "Use concrete file names and line numbers. Answer in Chinese."
            )
        ),
        HumanMessage(content=f"关注点: {feature}\n\n代码:\n{''.join(snippets)}"),
    ]
    return build_llm().invoke(messages).content


BASE_FUNCTIONS = {"read": read, "write": write, "edit": edit, "glob": glob, "grep": grep}
MCP_FUNCTIONS = {
    "scan_python_repo": scan_python_repo,
    "summarize_python_file": summarize_python_file,
    "read_code_excerpt": read_code_excerpt,
    "extract_agent_features": extract_agent_features,
    "explain_agent_feature": explain_agent_feature,
}


# ==================== Rules / Skills / MCP 加载 ====================


def parse_tool_arguments(raw_arguments: Any) -> Dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not raw_arguments:
        return {}
    try:
        parsed = json.loads(raw_arguments)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as error:
        return {"_argument_error": f"Invalid JSON arguments: {error}"}


def load_rules() -> str:
    if not RULES_DIR.exists():
        return ""
    rules = []
    for rule_file in sorted(RULES_DIR.glob("*.md")):
        rules.append(f"# {rule_file.stem}\n{rule_file.read_text(encoding='utf-8')}")
    return "\n\n".join(rules)


def parse_markdown_skill(path: Path) -> Dict[str, Any]:
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
    name = metadata.get("name", path.parent.name if path.name == "SKILL.md" else path.stem)
    triggers = [t.strip().lower() for t in metadata.get("triggers", "").split(",") if t.strip()]
    return {
        "name": name,
        "description": metadata.get("description", ""),
        "when_to_use": metadata.get("when_to_use", ""),
        "triggers": triggers,
        "path": str(path),
        "content": body,
    }


def load_skills() -> List[Dict[str, Any]]:
    if not SKILLS_DIR.exists():
        return []
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md")) + sorted(SKILLS_DIR.glob("*.md"))
    return [parse_markdown_skill(path) for path in skill_files]


def format_skill_for_prompt(skill: Dict[str, Any]) -> str:
    lines = [
        f"## {skill['name']}",
        f"Source: {skill['path']}",
        f"Description: {skill.get('description', '')}",
    ]
    if skill.get("when_to_use"):
        lines.append(f"When to use: {skill['when_to_use']}")
    if skill.get("triggers"):
        lines.append(f"Triggers: {', '.join(skill['triggers'])}")
    lines.append(skill["content"])
    return "\n".join(lines)


def load_mcp_tools() -> List[Dict[str, Any]]:
    if not MCP_CONFIG.exists():
        return []
    with open(MCP_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    tools = []
    for _server_name, server_config in config.get("mcpServers", {}).items():
        if server_config.get("disabled"):
            continue
        for tool_schema in server_config.get("tools", []):
            tools.append({"type": "function", "function": tool_schema})
    return tools


# ==================== LangChain Agent Loop ====================


def build_llm():
    kwargs = {"model": MODEL}
    if os.environ.get("OPENAI_API_KEY"):
        kwargs["api_key"] = os.environ["OPENAI_API_KEY"]
    base_url = os.environ.get("OPENAI_BASE_URL") or CONFIG.get("base_url")
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def call_tool(tool_call: Dict[str, Any]) -> str:
    name = tool_call["name"]
    args = parse_tool_arguments(tool_call.get("args"))
    print(f"[Tool] {name}({json.dumps(args, ensure_ascii=False)[:140]})")
    if "_argument_error" in args:
        return f"Error: {args['_argument_error']}"
    function_impl = AVAILABLE_FUNCTIONS.get(name)
    if not function_impl:
        return f"Error: Unknown tool '{name}'"
    try:
        return truncate_output(str(function_impl(**args)))
    except Exception as e:
        return f"Error: {e}"


def run_agent_step(messages: List[Any], tools: List[Any], max_iterations: Optional[int] = None) -> str:
    max_iterations = max_iterations or int(CONFIG["max_iterations"])
    llm_with_tools = build_llm().bind_tools(tools)

    for _ in range(max_iterations):
        messages[:] = compact_messages(messages)
        message = llm_with_tools.invoke(messages)
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for tool_call in message.tool_calls:
            result = call_tool(tool_call)
            messages.append(ToolMessage(result, tool_call_id=tool_call["id"]))

    return "Max iterations reached"


AVAILABLE_FUNCTIONS = {**BASE_FUNCTIONS, **MCP_FUNCTIONS}


class InteractiveAgent:
    def __init__(self):
        rules = load_rules()
        skills = load_skills()
        mcp_tools = load_mcp_tools()

        self.tool_schemas = BASE_TOOLS + mcp_tools
        self.tools = self.tool_schemas

        parts = [
            "You are a Claude Code style interactive coding agent.",
            "You can inspect and edit local files, and you can use Skills and MCP tools.",
            "Do not write reports to files unless the user explicitly asks. Prefer answering in chat.",
            "When analyzing a Python Agent repo, use the python-agent-analysis skill and MCP tools.",
        ]
        if rules:
            parts.append(f"\n# Rules\n{rules}")
            print(f"[Rules] Loaded {len(list(RULES_DIR.glob('*.md')))} rule files")
        if skills:
            parts.append("\n# Skills\n" + "\n\n".join(format_skill_for_prompt(skill) for skill in skills))
            print(f"[Skills] Loaded {len(skills)} skill files: {', '.join(s['name'] for s in skills)}")
        if mcp_tools:
            print(f"[MCP] Loaded {len(mcp_tools)} MCP tools: {', '.join(t['function']['name'] for t in mcp_tools)}")

        memory = load_memory()
        if memory:
            parts.append(f"\n# Previous Context\n{memory}")
        self.messages = [SystemMessage(content="\n".join(parts))]

    def chat(self, user_input: str) -> str:
        self.messages.append(HumanMessage(content=user_input))
        result = run_agent_step(self.messages, self.tools)
        save_memory(user_input, result)
        return result

    def compact(self):
        self.messages = compact_messages(self.messages)
        return f"Context messages: {len(self.messages)}"


# ==================== CLI ====================


def print_help():
    print(
        """Commands:
  /help      显示帮助
  /status    显示已加载 Rules / Skills / MCP tools
  /compact   压缩当前上下文
  /clear     清空本轮上下文
  /exit      退出

Examples:
  分析 agent/03-skills-mcp 里的 tools schema 转换
  看 agent/full 的 agent loop 是怎么把 tool result 放回 messages 的
  解释 agent/04-subagent 的子 agent 调度流程
"""
    )


def main():
    agent = InteractiveAgent()
    first_input = " ".join(sys.argv[1:]).strip()
    if first_input:
        print("\nAgent:", agent.chat(first_input))
        return

    print("Interactive Agent ready. 输入 /help 查看命令，/exit 退出。")
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not user_input:
            continue
        if user_input in {"/exit", "/quit", "exit", "quit"}:
            print("Bye!")
            break
        if user_input == "/help":
            print_help()
            continue
        if user_input == "/status":
            print(f"Rules: {RULES_DIR}")
            print(f"Skills: {SKILLS_DIR}")
            print(f"MCP: {MCP_CONFIG}")
            print(f"Tools: {', '.join(tool['function']['name'] for tool in agent.tools)}")
            continue
        if user_input == "/clear":
            agent = InteractiveAgent()
            print("Context cleared.")
            continue
        if user_input == "/compact":
            print(agent.compact())
            continue

        print("\nAgent:", agent.chat(user_input))


if __name__ == "__main__":
    main()
