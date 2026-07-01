"""
agent-langchain-file.py - LangChain 版文件修改 Agent

目标:
  1. 主 Agent 扫描目录、让用户选择文件、追问修改细节
  2. 主 Agent 将明确的文件修改任务委派给子 Agent
  3. 子 Agent 读取第 k 行并替换为 xxx
  4. 多轮 CLI 对话保持 messages 状态

用法:
  python agent/minitask/agent-langchain-file.py
  python agent/minitask/agent-langchain-file.py "帮我修改 ./tmp 目录下的文件"
  NANO_FILE_AGENT_CONFIG=./my_config.json python agent/minitask/agent-langchain-file.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(
    os.environ.get("NANO_FILE_AGENT_CONFIG", SCRIPT_DIR / "agent_config.json")
).expanduser()

DEFAULT_CONFIG = {
    "model": "gpt-4o-mini",
    "base_url": "",
    "temperature": 0,
    "max_tokens": 4096,
    "verify_ssl": True,
    "memory_file": "langchain_file_agent_memory.md",
    "max_iterations": 10,
    "main_system_prompt": (
        "You are a LangChain file operation agent.\n"
        "Follow this workflow:\n"
        "1. If the user gives a directory, call scan_directory.\n"
        "2. Ask the user to select target file(s) with ask_user_choice. Use selected_paths from its result.\n"
        "3. If edit details are missing, ask: 请指定要修改的行号(k)及替换内容(xxx)，或选择其他修改方式。\n"
        "4. When path, line_no, and new_content are clear, call delegate_to_file_subagent.\n"
        "5. After modification, summarize what changed and include verification.\n"
        "Be concise. Prefer Chinese when the user uses Chinese."
    ),
    "subagent_system_prompt": (
        "You are a file editing sub-agent. "
        "Use read_file_line first, then replace_file_line. "
        "Only edit the requested line. Return a concise summary."
    ),
}


def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    config = DEFAULT_CONFIG.copy()
    config.update(user_config)
    return config


def config_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = CONFIG_FILE.parent / path
    return path


CONFIG = load_config()
MODEL = os.environ.get("OPENAI_MODEL", CONFIG["model"])
MEMORY_FILE = config_path(CONFIG["memory_file"])
STATE: Dict[str, Any] = {"files": [], "selected_files": []}


# ==================== 工具实现 ====================


def resolve_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p.resolve()


@tool
def scan_directory(path: str) -> str:
    """Scan a local directory and return a numbered file list for user selection."""
    root = resolve_path(path)
    if not root.exists():
        return f"Error: path not found: {root}"
    if not root.is_dir():
        return f"Error: not a directory: {root}"

    files = [p for p in sorted(root.iterdir()) if p.is_file()]
    STATE["files"] = [str(p) for p in files]
    if not files:
        return f"No files found in {root}"

    lines = [f"Directory: {root}", "Files:"]
    for i, p in enumerate(files, 1):
        lines.append(f"{i}. {p.name}  ->  {p}")
    return "\n".join(lines)


@tool
def ask_user_choice(question: str, options: List[str], multiple: bool = False) -> str:
    """Ask the user to choose one or more options from a numbered list."""
    print(f"\n{question}")
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")

    hint = "可多选，用逗号分隔 > " if multiple else "请选择编号 > "
    while True:
        raw = input(hint).strip()
        try:
            indexes = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            print("请输入数字编号。")
            continue

        if not indexes:
            print("至少选择一个编号。")
            continue
        if not multiple and len(indexes) != 1:
            print("这里只能选择一个编号。")
            continue
        if any(i < 1 or i > len(options) for i in indexes):
            print("编号超出范围。")
            continue

        selected = [options[i - 1] for i in indexes]
        selected_paths = []
        scanned = [Path(p) for p in STATE.get("files", [])]
        for item in selected:
            match = next(
                (str(p) for p in scanned if item in {str(p), p.name, f"{p.name}  ->  {p}"}),
                item,
            )
            selected_paths.append(match)

        STATE["selected_files"] = selected_paths
        return json.dumps(
            {"selected": selected, "selected_paths": selected_paths},
            ensure_ascii=False,
        )


@tool
def read_file_line(path: str, line_no: int) -> str:
    """Read one line from a file, using 1-based line number."""
    file_path = resolve_path(path)
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        return f"Error: {e}"

    if line_no < 1 or line_no > len(lines):
        return f"Error: line_no must be 1..{len(lines)}"
    return json.dumps(
        {
            "path": str(file_path),
            "line_no": line_no,
            "content": lines[line_no - 1],
        },
        ensure_ascii=False,
    )


@tool
def replace_file_line(path: str, line_no: int, new_content: str) -> str:
    """Replace one line in a file, using 1-based line number."""
    file_path = resolve_path(path)
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except Exception as e:
        return f"Error: {e}"

    if line_no < 1 or line_no > len(lines):
        return f"Error: line_no must be 1..{len(lines)}"

    old = lines[line_no - 1].rstrip("\n")
    newline = "\n" if lines[line_no - 1].endswith("\n") else ""
    lines[line_no - 1] = new_content + newline
    file_path.write_text("".join(lines), encoding="utf-8")

    return json.dumps(
        {
            "path": str(file_path),
            "line_no": line_no,
            "old": old,
            "new": new_content,
        },
        ensure_ascii=False,
    )


# ==================== LangChain Agent 循环 ====================


def build_llm():
    kwargs = {
        "model": MODEL,
        "temperature": CONFIG.get("temperature", 0),
        "max_tokens": CONFIG.get("max_tokens", 4096),
    }
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        kwargs["api_key"] = api_key
    base_url = os.environ.get("OPENAI_BASE_URL") or CONFIG.get("base_url")
    if base_url:
        kwargs["base_url"] = base_url
    if CONFIG.get("verify_ssl") is False:
        transport = httpx.HTTPTransport(verify=False)
        kwargs["http_client"] = httpx.Client(transport=transport)
    return ChatOpenAI(**kwargs)


def call_tool(tool_map, tool_call):
    name = tool_call["name"]
    args = tool_call.get("args") or {}
    print(f"[Tool] {name}({json.dumps(args, ensure_ascii=False)[:120]})")
    if name not in tool_map:
        return f"Error: unknown tool {name}"
    try:
        return tool_map[name].invoke(args)
    except Exception as e:
        return f"Error: {e}"


def run_agent(messages, tools, max_iterations=None):
    max_iterations = max_iterations or int(CONFIG["max_iterations"])
    llm_with_tools = build_llm().bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    for _ in range(max_iterations):
        message = llm_with_tools.invoke(messages)
        messages.append(message)

        if not message.tool_calls:
            return message.content

        for tc in message.tool_calls:
            result = call_tool(tool_map, tc)
            messages.append(ToolMessage(str(result), tool_call_id=tc["id"]))

    return "达到最大轮次，任务未完成。"


# ==================== SubAgent ====================


def run_file_subagent(path: str, line_no: int, new_content: str) -> str:
    """一次性子 Agent: 读取目标行，替换目标行，返回修改摘要。"""
    print(f"\n{'=' * 50}")
    print(f"[SubAgent:file-editor] 修改 {path}:{line_no}")
    print(f"{'=' * 50}")

    messages = [
        SystemMessage(
            content=CONFIG["subagent_system_prompt"]
        ),
        HumanMessage(
            content=(
                f"File: {path}\n"
                f"Line: {line_no}\n"
                f"New content: {new_content}\n"
                "Read the line, replace it, and report old/new content."
            )
        ),
    ]
    result = run_agent(messages, [read_file_line, replace_file_line])
    print("[SubAgent:file-editor] 完成\n")
    return result


@tool
def delegate_to_file_subagent(path: str, line_no: int, new_content: str) -> str:
    """Delegate an exact file line replacement task to the file editing sub-agent."""
    result = run_file_subagent(path, line_no, new_content)
    verify = read_file_line.invoke({"path": path, "line_no": line_no})
    return f"SubAgent result:\n{result}\n\nVerification:\n{verify}"


# ==================== 记忆与主 Agent ====================


def load_memory() -> str:
    if not MEMORY_FILE.exists():
        return ""
    lines = MEMORY_FILE.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-50:])


def save_memory(user_input: str, result: str):
    entry = (
        f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"**User:** {user_input}\n"
        f"**Agent:** {result[:500]}\n"
    )
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


class AgentSession:
    def __init__(self):
        system = CONFIG["main_system_prompt"]
        memory = load_memory()
        if memory:
            system += f"\n\nPrevious context:\n{memory}"
        self.messages = [SystemMessage(content=system)]
        self.tools = [
            scan_directory,
            ask_user_choice,
            read_file_line,
            delegate_to_file_subagent,
        ]

    def chat(self, user_input: str) -> str:
        self.messages.append(HumanMessage(content=user_input))
        result = run_agent(self.messages, self.tools)
        save_memory(user_input, result)
        return result


# ==================== CLI ====================


def main():
    session = AgentSession()
    first_input = " ".join(sys.argv[1:]).strip()

    if first_input:
        print("\nAgent:", session.chat(first_input))

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"/exit", "/quit", "exit", "quit"}:
            print("Bye!")
            break

        print("\nAgent:", session.chat(user_input))


if __name__ == "__main__":
    main()
