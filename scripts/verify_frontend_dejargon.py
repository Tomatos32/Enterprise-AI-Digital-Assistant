#!/usr/bin/env python3
"""
Enterprise AI Assistant - Frontend Anti-Jargon & Anti-Emoji Static Verification Scanner.
Sprint F-08 DoD Enforcement: 100% Zero Developer Pollution in User-Facing Frontend.
"""

import sys
import os
import re
from pathlib import Path

FORBIDDEN_JARGON_PATTERNS = [
    (r"TTFT\s*:", "TTFT developer latency metric leak"),
    (r"Tokens\s*:\s*\d+", "Raw Token usage count leak"),
    (r"\[WS已连接\]", "Raw WebSocket connection status badge leak"),
    (r"\[断开\]", "Raw disconnect status badge leak"),
    (r"●\s*ROUTER", "Low-level LangGraph router node token"),
    (r"●\s*TOOL", "Low-level tool execution log badge"),
    (r"LangGraph\s+interrupt", "Raw LangGraph state-machine interrupt jargon"),
    (r"熔断器\s*:\s*(?:CLOSED|HALF_OPEN|OPEN)", "Circuit breaker internal state leak"),
    (r"thread_ws_[a-zA-Z0-9_-]+", "Raw internal WebSocket session thread ID leak"),
]

# Prohibited system emojis in user-facing UI (must use Lucide SVG components instead)
PROHIBITED_EMOJIS = [
    ("💡", "System emoji 💡 prohibited; use Lucide Sparkles/Lightbulb instead"),
    ("⚠️", "System emoji ⚠️ prohibited; use Lucide AlertCircle/AlertTriangle instead"),
    ("⚙️", "System emoji ⚙️ prohibited; use Lucide Settings instead"),
]

def scan_frontend(src_dir: Path):
    violations = []
    scanned_files = 0

    valid_extensions = {".vue", ".js", ".jsx", ".ts", ".tsx", ".html"}
    ignored_dirs = {"node_modules", "dist", ".git", ".venv"}

    for root, dirs, files in os.walk(src_dir):
        # Prune ignored directories in place
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for f in files:
            path = Path(root) / f
            if path.suffix not in valid_extensions:
                continue

            scanned_files += 1
            rel_path = path.relative_to(src_dir)
            content = path.read_text(encoding="utf-8", errors="ignore")

            for line_no, line in enumerate(content.splitlines(), start=1):
                # Check jargon patterns
                for pattern, desc in FORBIDDEN_JARGON_PATTERNS:
                    if re.search(pattern, line):
                        violations.append({
                            "file": str(rel_path),
                            "line": line_no,
                            "type": "JARGON_VIOLATION",
                            "desc": desc,
                            "text": line.strip()
                        })

                # Check prohibited emojis
                for emoji_char, desc in PROHIBITED_EMOJIS:
                    if emoji_char in line:
                        violations.append({
                            "file": str(rel_path),
                            "line": line_no,
                            "type": "EMOJI_VIOLATION",
                            "desc": desc,
                            "text": line.strip()
                        })

    return scanned_files, violations

def main():
    root_dir = Path(__file__).resolve().parent.parent
    frontend_dir = root_dir / "frontend"

    if not frontend_dir.exists():
        print(f"Error: Directory {frontend_dir} does not exist.")
        sys.exit(1)

    print(f"[*] Commencing Frontend Anti-Jargon & Anti-Emoji Scanner...")
    print(f"[*] Target Directory: {frontend_dir}")

    scanned_files, violations = scan_frontend(frontend_dir)

    print(f"[*] Scanned {scanned_files} frontend source files.")

    if violations:
        print(f"[!] FAILED: Found {len(violations)} violations:")
        for v in violations:
            print(f"  - {v['file']}:{v['line']} [{v['type']}]: {v['desc']} -> \"{v['text']}\"")
        sys.exit(1)
    else:
        print("[+] SUCCESS: 0 Developer Jargon violations, 0 Prohibited Emojis found!")
        print("[+] Frontend meets 100% Zero Developer Pollution standard.")
        sys.exit(0)

if __name__ == "__main__":
    main()
