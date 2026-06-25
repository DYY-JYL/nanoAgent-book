"""
agent-progressive-skill.py - 渐进式 Skill 加载版 Agent
基于系列里的最小 Agent，核心新增:

  1. Skill 注册表自动扫描生成，并写出 registry.json 方便观察
  2. load_skill 工具 —— LLM 按需加载 Skill 详情
  3. Level 0/1/2 三层渐进式披露

目录结构：
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
  └── registry.json

用法：
  python3 agent/17-skill-progressive/agent-progressive-skill.py "咨询病假怎么处理"
"""

import json
import os
import re
import subprocess
import sys
import httpx
from pathlib import Path
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_DIR = SCRIPT_DIR / "skills"
REGISTRY_FILE = SKILLS_DIR / "registry.json"
MAX_ITERATIONS = 10


def create_client():
    return OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL"),
        http_client=httpx.Client(verify=False),
    )

# ── Skill 注册表 ─────────────────────────────────────

def parse_frontmatter(content: str) -> dict:
    """解析 SKILL.md 开头的 YAML frontmatter"""
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    meta = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            meta[key.strip()] = val.strip()
    return meta


def build_registry() -> list:
    """扫描 skills/ 目录，生成 Skill 注册表（Level 0）"""
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
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return registry


def format_skill_catalog(registry: list) -> str:
    """格式化 Skill 目录，注入 system prompt（Level 0）"""
    if not registry:
        return ""
    lines = ["\n# Available Skills"]
    lines.append("以下是可用的 Skill 列表。需要某个 Skill 的详细操作指南时，调用 load_skill 工具。")
    for s in registry:
        lines.append(f"- **{s['name']}**: {s['description']}")
    return "\n".join(lines)


# ── 工具实现 ──────────────────────────────────────────

def load_skill(name: str) -> str:
    """加载指定 Skill 的完整 SKILL.md（Level 1）"""
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.exists():
        return f"Error: Skill '{name}' not found. Available skills: {[d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]}"
    content = skill_file.read_text(encoding="utf-8")
    # 去掉 frontmatter，只返回正文
    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
    return content.strip()


def read_file(filepath: str) -> str:
    """读取 Skill 内部的子文件（Level 2）"""
    p = Path(filepath)
    if not p.exists() and not p.is_absolute():
        p = SCRIPT_DIR / filepath
    if not p.exists():
        return f"Error: File '{filepath}' not found"
    return p.read_text(encoding="utf-8")[:10000]  # 截断防止过长


def write_file(filepath: str, content: str) -> str:
    """写入文件"""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Written to {filepath} ({len(content)} chars)"


def execute_bash(command: str) -> str:
    """执行 bash 命令"""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        return output[:5000] or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s)"


# ── 工具注册 ──────────────────────────────────────────

# 基础工具（始终可用）
BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents. Use for reading skill sub-files, configs, docs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Run a shell command. Use for system operations, installing packages, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command"}
                },
                "required": ["command"]
            }
        }
    },
]

# load_skill 工具（渐进式披露的核心）
LOAD_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "加载一个 Skill 的完整操作指南。当你确定当前任务需要某个 Skill 时调用。调用后会返回该 Skill 的 SKILL.md 内容，包含具体的操作步骤、命令和注意事项。",
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

TOOL_FUNCTIONS = {
    "load_skill": lambda args: load_skill(args["name"]),
    "read_file": lambda args: read_file(args["filepath"]),
    "write_file": lambda args: write_file(args["filepath"], args["content"]),
    "execute_bash": lambda args: execute_bash(args["command"]),
}


# ── Agent 主循环 ──────────────────────────────────────

def run_agent(task: str):
    """带渐进式 Skill 加载的 Agent 主循环"""
    client = create_client()

    # Level 0：扫描 Skill 目录，生成目录摘要
    registry = build_registry()
    skill_catalog = format_skill_catalog(registry)

    system_prompt = f"""You are a helpful assistant that can use tools to accomplish tasks.
{skill_catalog}
"""

    # 组装工具列表：基础工具 + load_skill（如果有 Skill 的话）
    tools = BASE_TOOLS.copy()
    if registry:
        tools.append(LOAD_SKILL_TOOL)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]

    print(f"\n🚀 Task: {task}")
    if registry:
        print(f"📚 Available Skills: {[s['name'] for s in registry]}")
    print("-" * 50)

    for i in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools
        )
        msg = response.choices[0].message
        messages.append(msg)

        # 没有工具调用 → 任务完成
        if not msg.tool_calls:
            print(f"\n💬 Agent: {msg.content}")
            return

        # 处理工具调用
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            print(f"\n🔧 [{i+1}] Calling {name}({json.dumps(args, ensure_ascii=False)[:80]})")

            # 执行工具
            func = TOOL_FUNCTIONS.get(name)
            if func:
                result = func(args)
            else:
                result = f"Error: Unknown tool '{name}'"

            # 打印结果预览
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"   → {preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    print("\n⚠️ Reached max iterations")

# ── 入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python3 agent/17-skill-progressive/agent-progressive-skill.py "你的任务"')
        sys.exit(1)

    run_agent(" ".join(sys.argv[1:]))
