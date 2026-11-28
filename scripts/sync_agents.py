#!/usr/bin/env python3
"""Synchronize Claude Code, OpenCode, and Antigravity agent definitions via model_tiers.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_DIR = ROOT / ".claude" / "agents"
OPENCODE_DIR = ROOT / ".opencode" / "agents"
ANTIGRAVITY_DIR = ROOT / ".agents" / "agents"
SIDE_DIRS = {
    "claude": CLAUDE_DIR,
    "opencode": OPENCODE_DIR,
    "antigravity": ANTIGRAVITY_DIR,
}
SIDES = ("claude", "opencode", "antigravity")
STATE_PATH = ROOT / ".agent-sync-state.json"
TIERS_PATH = ROOT / "scripts" / "model_tiers.json"
CLAUDE_SETTINGS_PATH = ROOT / ".claude" / "settings.json"
OPENCODE_CONFIG_PATH = ROOT / "opencode.json"

ANTIGRAVITY_COMPAT_HEADING = "## Antigravity Tool Compatibility"
ANTIGRAVITY_SHARED_KEYS = {
    "name",
    "description",
    "model",
    "mainAgent",
    "subagent",
    "tools",
    "commandExecutionPolicy",
}
CLI_MANAGED_KEYS = ANTIGRAVITY_SHARED_KEYS | {"disallowedTools", "mode", "permission"}
CANONICAL_IGNORED_KEYS = (CLI_MANAGED_KEYS - {"name", "description"}) | {
    "skills",
    "mcpServers",
    "rules",
    "workflows",
    "hooks",
}

ROLE_POLICIES = {
    "planner": ("deny", "ask", ["Read", "Grep", "Glob"]),
    "reviewer": ("deny", "ask", ["Read", "Grep", "Glob"]),
    "evaluator": ("deny", "ask", ["Read", "Grep", "Glob"]),
    "developer": ("allow", "ask", None),
    "deployment": ("allow", "ask", None),
    "documentation": ("allow", "deny", None),
    "onboarding": ("deny", "ask", ["Read", "Grep", "Glob"]),
    "verifier": ("deny", "ask", ["Read", "Grep", "Glob"]),
    "recorder": ("allow", "ask", None),
}

ANTIGRAVITY_ROLE_POLICIES: dict[str, tuple[list[str], str]] = {
    "onboarding": (["view_file", "grep_search"], "off"),
    "planner": (["view_file", "replace_file_content", "grep_search"], "off"),
    "reviewer": (["view_file", "replace_file_content", "grep_search"], "off"),
    "documentation": (["view_file", "replace_file_content", "grep_search"], "off"),
    "developer": (["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"),
    "verifier": (["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"),
    "evaluator": (["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"),
    "deployment": (["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"),
    "recorder": (["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"),
}


def load_tiers() -> dict[str, Any]:
    data = json.loads(TIERS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data.get("opencode_provider"), str) or not isinstance(data.get("tiers"), dict):
        raise ValueError(f"Invalid model tier configuration: {TIERS_PATH}")
    return data


def model_tables(config: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    aliases: dict[str, str] = {}
    full_ids: dict[str, str] = {}
    for tier in config["tiers"].values():
        alias = tier["claude_alias"]
        model_id = tier["opencode_model_id"]
        full_id = f"{config['opencode_provider']}/{model_id}"
        aliases[alias] = full_id
        full_ids[full_id] = alias
    return aliases, full_ids


def split_document(text: str) -> tuple[list[str], str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", text, re.S)
    if not match:
        return [], text
    return match.group(1).splitlines(), match.group(2)


def split_frontmatter_blocks(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Group top-level YAML frontmatter lines into (key, block_lines) pairs."""
    blocks: list[tuple[str, list[str]]] = []
    current_key: str | None = None
    current_lines: list[str] = []
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            if current_key is not None:
                blocks.append((current_key, current_lines))
            current_key = match.group(1)
            current_lines = [line]
        elif current_key is not None:
            current_lines.append(line)
    if current_key is not None:
        blocks.append((current_key, current_lines))
    return blocks


def parse_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    return fields


def emit_document(lines: list[str], body: str) -> str:
    if not lines:
        return body
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def set_frontmatter_value(lines: list[str], key: str, value: str) -> list[str]:
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f"{key}: {value}"
            return lines
    lines.append(f"{key}: {value}")
    return lines


def role_of(name: str) -> str:
    return name.removeprefix("harness-").lower()


def tier_for_role(config: dict[str, Any], role: str) -> dict[str, str]:
    tier_name = config.get("role_tiers", {}).get(role)
    if tier_name not in config["tiers"]:
        raise ValueError(f"Missing tier for role {role!r} in {TIERS_PATH}")
    return config["tiers"][tier_name]


def antigravity_policy_for(role: str) -> tuple[list[str], str]:
    """Return Antigravity tools list and commandExecutionPolicy for a role."""
    if role in ANTIGRAVITY_ROLE_POLICIES:
        tools, policy = ANTIGRAVITY_ROLE_POLICIES[role]
        return list(tools), policy
    edit, bash, _tools = ROLE_POLICIES.get(role, ("allow", "ask", None))
    if edit == "deny":
        return ["view_file", "grep_search"], "off"
    if bash == "deny":
        return ["view_file", "replace_file_content", "grep_search"], "off"
    return ["view_file", "replace_file_content", "grep_search", "run_command"], "sandbox"


def strip_antigravity_compat(body: str) -> str:
    """Strip the generated Antigravity compatibility section for cross-CLI parity."""
    pattern = re.compile(rf"\r?\n*{re.escape(ANTIGRAVITY_COMPAT_HEADING)}\b.*\Z", re.S)
    cleaned = pattern.sub("", body).replace("\r\n", "\n").rstrip()
    if not cleaned:
        return ""
    leading = "\n" if body.startswith(("\n", "\r\n")) else ""
    return leading + cleaned.lstrip("\n") + "\n"


def render_antigravity_compat(role: str, core_body: str) -> str:
    """Build a concise Antigravity tool compatibility addendum matching the role policy."""
    agy_tools, policy = antigravity_policy_for(role)
    can_write = "replace_file_content" in agy_tools
    lines = [
        ANTIGRAVITY_COMPAT_HEADING,
        "",
        f"In Google Antigravity (`tools: [{', '.join(agy_tools)}]`, `commandExecutionPolicy: {policy}`), map Claude Code references above as follows:",
        "- `Read` -> `view_file` (or `read_file` with explicit line ranges, always `<= 200` lines on large files)",
        "- `Grep` / `Glob` -> `grep_search`",
    ]
    if role in {"planner", "reviewer", "verifier", "evaluator", "documentation", "recorder"} and can_write:
        lines.append(
            "- `Edit` / `Write` -> `replace_file_content` (or `edit_file` / `write_file`) STRICTLY within this role's allowed artifact/doc paths; keep application source code untouched"
        )
    elif can_write:
        lines.append("- `Edit` / `Write` -> `replace_file_content` (or `edit_file` / `write_file`; keep edits compact and targeted)")
    else:
        lines.append("- `Write` / `Edit` / `NotebookEdit` -> disabled in this read-only Antigravity profile; never modify repository files")

    if policy == "sandbox":
        lines.append("- `Bash` / `PowerShell` -> `run_command` (use `PYTHONUTF8=1 backend/.venv/Scripts/python.exe` and keep stdout `<= 50` lines via `scripts/harness_run.py`)")
    elif any(token in core_body for token in ("Bash", "PowerShell", "pytest", "ruff", "mypy", "alembic", "git ", "python.exe")):
        lines.append("- `Bash` / `PowerShell` -> disabled (`commandExecutionPolicy: off`) in this Antigravity profile; use pre-generated artifacts or return commands to `HarnessOrchestrator`")

    if any(token in core_body for token in ("Agent", "ListAgents", "SendMessage")):
        lines.append("- `Agent` / `ListAgents` / `SendMessage` -> `invoke_subagent` / `manage_subagents` / `send_message` (dispatched by main `HarnessOrchestrator`)")
    if "CLAUDE.md" in core_body:
        lines.append("- `CLAUDE.md` -> follow `AGENTS.md` (Antigravity `always_on` rule root) alongside `CLAUDE.md`")

    return "\n".join(lines) + "\n"


def preserve_antigravity_extras(existing_text: str | None) -> list[str]:
    """Preserve Antigravity-only frontmatter fields (e.g., skills, mcpServers) on incremental updates."""
    if not existing_text:
        return []
    existing_lines, _ = split_document(existing_text)
    extra_lines: list[str] = []
    for key, block_lines in split_frontmatter_blocks(existing_lines):
        if key not in CLI_MANAGED_KEYS:
            extra_lines.extend(block_lines)
    return extra_lines


def normalize_model(value: str, aliases: dict[str, str], full_ids: dict[str, str]) -> str:
    if value in aliases:
        return value
    if value in full_ids:
        return full_ids[value]
    return value


def canonical(text: str, side: str, name: str, config: dict[str, Any], aliases: dict[str, str], full_ids: dict[str, str]) -> dict[str, Any]:
    lines, body = split_document(text)
    fields = parse_fields(lines)
    role_tier = tier_for_role(config, role_of(name))
    role_alias = role_tier["claude_alias"]
    expected_opencode_model = f"{config['opencode_provider']}/{role_tier['opencode_model_id']}"
    expected_agy_model = role_tier.get("antigravity_tier", "")
    raw_model = fields.get("model", "")
    if (
        (side == "claude" and raw_model == role_alias)
        or (side == "opencode" and raw_model == expected_opencode_model)
        or (side == "antigravity" and expected_agy_model and raw_model == expected_agy_model)
    ):
        normalized_model = role_alias
    elif side == "antigravity":
        normalized_model = f"antigravity:{raw_model}" if raw_model else ""
    else:
        normalized_model = normalize_model(raw_model, aliases, full_ids)
    core_body = strip_antigravity_compat(body) if side == "antigravity" else body
    return {
        "description": fields.get("description", ""),
        "model": normalized_model,
        "body": core_body.replace("\r\n", "\n").rstrip() + "\n",
        "extras": {key: value for key, value in fields.items() if key not in CANONICAL_IGNORED_KEYS},
    }


def digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _base_lines_for_claude_or_opencode(source_fields: dict[str, str], name: str, existing_text: str | None) -> list[str]:
    """Preserve target native tool grants while updating shared metadata when syncing from Antigravity."""
    role = role_of(name)
    agent_name = source_fields.get("name", name)
    description = source_fields.get("description", "")
    if existing_text:
        existing_lines, _ = split_document(existing_text)
        filtered = [
            line
            for line in existing_lines
            if not re.match(r"^(name|description|permission|mode|mainAgent|subagent|commandExecutionPolicy|skills|mcpServers):\s*", line)
            and not re.match(r"^\s+(edit|bash):\s*", line)
        ]
        result = [f"name: {agent_name}", f"description: {description}"]
        result.extend(filtered)
        return result

    lines = [f"name: {agent_name}", f"description: {description}"]
    edit, _bash, tools = ROLE_POLICIES.get(role, ("allow", "ask", None))
    if tools is not None:
        lines.append(f"tools: {', '.join(tools)}")
    elif edit == "allow":
        lines.append("disallowedTools: Agent, NotebookEdit")
    return lines


def convert(text: str, target: str, name: str, config: dict[str, Any], existing_text: str | None = None) -> str:
    lines, body = split_document(text)
    fields = parse_fields(lines)
    role = role_of(name)
    tier = tier_for_role(config, role)
    core_body = strip_antigravity_compat(body)

    if target == "antigravity":
        agy_model = tier.get("antigravity_tier")
        if not agy_model:
            raise ValueError(f"Missing antigravity_tier for role {role!r} in {TIERS_PATH}")
        agy_tools, policy = antigravity_policy_for(role)
        policy_yaml = '"off"' if policy == "off" else policy
        out_lines = [
            f"name: {fields.get('name', name)}",
            f"description: {fields.get('description', '')}",
            f"model: {agy_model}",
            "mainAgent: true",
            "subagent: true",
            f"tools: [{', '.join(agy_tools)}]",
            f"commandExecutionPolicy: {policy_yaml}",
        ]
        out_lines.extend(preserve_antigravity_extras(existing_text))
        compat = render_antigravity_compat(role, core_body)
        stripped = core_body.rstrip()
        full_body = ("\n" + stripped.lstrip("\n") + "\n\n" + compat) if stripped else ("\n" + compat)
        return emit_document(out_lines, full_body)

    # Preserve target-native tools/disallowedTools whenever the target file already exists
    # or when converting from Antigravity.
    if existing_text is not None or "commandExecutionPolicy" in fields or "mainAgent" in fields:
        base_lines = _base_lines_for_claude_or_opencode(fields, name, existing_text)
    else:
        base_lines = [
            line
            for line in lines
            if not re.match(r"^(model|permission|mode|mainAgent|subagent|commandExecutionPolicy):\s*", line)
            and not re.match(r"^\s+(edit|bash):\s*", line)
        ]

    if target == "opencode":
        model = f"{config['opencode_provider']}/{tier['opencode_model_id']}"
        base_lines = [line for line in base_lines if not re.match(r"^(model|mode|permission):\s*", line)]
        base_lines.extend([f"model: {model}", "mode: subagent", "permission:"])
        edit, bash, _tools = ROLE_POLICIES.get(role, ("allow", "ask", None))
        base_lines.extend([f"  edit: {edit}", f"  bash: {bash}"])
        return emit_document(base_lines, core_body)

    base_lines = [line for line in base_lines if not re.match(r"^(permission|mode):\s*", line)]
    base_lines = set_frontmatter_value(base_lines, "model", tier["claude_alias"])
    return emit_document(base_lines, core_body)


def paths(directory: Path) -> dict[str, Path]:
    if not directory.exists():
        return {}
    return {path.stem: path for path in directory.glob("harness-*.md") if path.is_file()}


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"version": 1, "agents": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"version": 1, "agents": {}}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid sync state file: {STATE_PATH}") from exc


def write_state(state: dict[str, Any], dry_run: bool) -> None:
    if not dry_run:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save(target: Path, text: str, dry_run: bool) -> None:
    print(f"WRITE {target.relative_to(ROOT)}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, data: dict[str, Any], dry_run: bool) -> None:
    save(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", dry_run)


def rebind_models(config: dict[str, Any], dry_run: bool) -> int:
    aliases, full_ids = model_tables(config)
    settings = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
    env = settings.setdefault("env", {})
    for tier in config["tiers"].values():
        env[tier["claude_env"]] = tier["claude_model_id"]
    write_json(CLAUDE_SETTINGS_PATH, settings, dry_run)

    claude = paths(CLAUDE_DIR)
    antigravity = paths(ANTIGRAVITY_DIR)
    for name, source in claude.items():
        original_text = source.read_text(encoding="utf-8")
        rebound_claude = convert(original_text, "claude", name, config)
        save(source, rebound_claude, dry_run)
        rebound_opencode = convert(rebound_claude, "opencode", name, config)
        save(OPENCODE_DIR / f"{name}.md", rebound_opencode, dry_run)
        existing_agy = antigravity[name].read_text(encoding="utf-8") if name in antigravity else None
        rebound_agy = convert(rebound_claude, "antigravity", name, config, existing_text=existing_agy)
        save(ANTIGRAVITY_DIR / f"{name}.md", rebound_agy, dry_run)

    opencode_config = json.loads(OPENCODE_CONFIG_PATH.read_text(encoding="utf-8"))
    fast_tier = config["tiers"]["fast"]
    fast_model = f"{config['opencode_provider']}/{fast_tier['opencode_model_id']}"
    opencode_config["small_model"] = fast_model
    agents = opencode_config.setdefault("agent", {})
    for builtin in ("explore", "compaction", "title", "summary"):
        agents.setdefault(builtin, {})["model"] = fast_model
    write_json(OPENCODE_CONFIG_PATH, opencode_config, dry_run)

    agents_state: dict[str, dict[str, str]] = {}
    state: dict[str, Any] = {"version": 1, "agents": agents_state}
    for name in sorted(claude):
        ctext = claude[name].read_text(encoding="utf-8")
        if dry_run:
            ctext = convert(ctext, "claude", name, config)
        opath = OPENCODE_DIR / f"{name}.md"
        apath = ANTIGRAVITY_DIR / f"{name}.md"
        otext = convert(ctext, "opencode", name, config) if dry_run or not opath.exists() else opath.read_text(encoding="utf-8")
        existing_agy = apath.read_text(encoding="utf-8") if apath.exists() else None
        atext = convert(ctext, "antigravity", name, config, existing_text=existing_agy) if dry_run or not apath.exists() else existing_agy
        agents_state[name] = {
            "claude": digest(canonical(ctext, "claude", name, config, aliases, full_ids)),
            "opencode": digest(canonical(otext, "opencode", name, config, aliases, full_ids)),
            "antigravity": digest(canonical(atext or "", "antigravity", name, config, aliases, full_ids)),
        }
    write_state(state, dry_run)
    return len(claude)


def status_for(hashes: dict[str, str | None], prior: dict[str, str]) -> str:
    present = {side: h for side, h in hashes.items() if h is not None}
    if len(present) == len(SIDES) and len(set(present.values())) == 1:
        return "synced"
    if not present:
        return "missing-all"
    if len(present) == 1:
        return f"only-in-{next(iter(present))}"
    if len(present) < len(SIDES):
        missing = [side for side in SIDES if side not in present]
        if len(set(present.values())) == 1:
            return f"missing-{'+'.join(missing)}"
        if all(prior.get(side) is not None for side in present):
            changed = [side for side in present if present[side] != prior.get(side)]
            if len(changed) == 1:
                return f"{changed[0]}-ahead"
        return "conflict"

    if any(prior.get(side) is None for side in SIDES):
        return "conflict"
    changed = [side for side in SIDES if present[side] != prior[side]]
    if len(changed) == 1:
        return f"{changed[0]}-ahead"
    return "conflict"


def resolve_direction(status: str, prefer: str | None, texts: dict[str, str | None]) -> str | None:
    if prefer:
        return prefer if texts.get(prefer) is not None else None
    if status.endswith("-ahead"):
        return status.removesuffix("-ahead")
    if status.startswith("only-in-"):
        return status.removeprefix("only-in-")
    if status.startswith("missing-"):
        for side in SIDES:
            if texts.get(side) is not None:
                return side
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="show synchronization state")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
    parser.add_argument("--prefer", choices=SIDES, help="resolve diverged agents from one side")
    parser.add_argument("--bootstrap", action="store_true", help="initialize missing targets from existing agents")
    parser.add_argument("--rebind-models", action="store_true", help="apply model tiers to all CLI configurations")
    parser.add_argument("agent_name", nargs="?", help="limit sync or preference to one agent name")
    args = parser.parse_args()

    try:
        config = load_tiers()
        aliases, full_ids = model_tables(config)
        if args.rebind_models:
            count = rebind_models(config, args.dry_run)
            print(f"{('DRY RUN: ' if args.dry_run else '')}rebound model tiers for {count} agent(s)")
            return 0

        side_maps = {side: paths(directory) for side, directory in SIDE_DIRS.items()}
        state = read_state()
        baseline = state.setdefault("agents", {})
        names = sorted(set().union(*(m.keys() for m in side_maps.values())))
        if args.agent_name:
            target_name = args.agent_name.removesuffix(".md")
            names = [name for name in names if name == target_name]
            if not names:
                print(f"Unknown agent: {args.agent_name}", file=sys.stderr)
                return 2

        conflicts = changes = 0
        for name in names:
            texts = {
                side: side_maps[side][name].read_text(encoding="utf-8") if name in side_maps[side] else None
                for side in SIDES
            }
            hashes: dict[str, str | None] = {}
            for side in SIDES:
                side_text = texts[side]
                hashes[side] = (
                    digest(canonical(side_text, side, name, config, aliases, full_ids))
                    if side_text is not None
                    else None
                )
            status = status_for(hashes, baseline.get(name, {}))
            print(f"{name}: {status}")
            if args.status:
                continue
            if status == "synced":
                baseline[name] = {side: hashes[side] for side in SIDES}
                continue
            if status == "conflict" and args.prefer is None:
                print(f"  conflict: use --prefer claude|opencode|antigravity {name}", file=sys.stderr)
                conflicts += 1
                continue

            direction = resolve_direction(status, args.prefer, texts)
            if direction is None or texts.get(direction) is None:
                print(f"  cannot synchronize missing side for {name}", file=sys.stderr)
                conflicts += 1
                continue

            source_text = texts[direction]
            assert source_text is not None
            updated_texts: dict[str, str] = {direction: source_text}
            missing_only = status.startswith("missing-") and args.prefer is None
            for target_side in SIDES:
                if target_side == direction:
                    continue
                if missing_only and texts.get(target_side) is not None:
                    updated_texts[target_side] = texts[target_side] or ""
                    continue
                output = convert(
                    source_text,
                    target_side,
                    name,
                    config,
                    existing_text=texts.get(target_side),
                )
                if texts.get(target_side) != output:
                    save(SIDE_DIRS[target_side] / f"{name}.md", output, args.dry_run)
                updated_texts[target_side] = output

            baseline[name] = {
                side: digest(canonical(updated_texts[side], side, name, config, aliases, full_ids))
                for side in SIDES
            }
            changes += 1

        if not args.status:
            write_state(state, args.dry_run)
            print(f"{('DRY RUN: ' if args.dry_run else '')}{changes} agent(s) synchronized")
        return 1 if conflicts else 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
