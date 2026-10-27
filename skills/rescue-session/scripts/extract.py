#!/usr/bin/env python3
"""rescue-session: extract the human/assistant skeleton from a harness
session transcript that ai-memory backfill refused (size limits).

Usage:
    python3 extract.py --agent codex --target /path/to/session.jsonl
    python3 extract.py --agent pi --target 019f88e3            # locate by id
    python3 extract.py --agent auto --target <path-or-id>      # probe formats

Outputs (in --out-dir, default /tmp/rescue-<target>):
    user-all.txt    all user-role messages, in order
    asst-tail.txt   last N assistant messages (default 150)
    meta.txt        source file, session cwd, counts, suggested chunk count

Exit codes: 0 ok; 2 file not found; 3 unknown/unrecognized format.
Pure standard library; no network access.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

ASST_TAIL_DEFAULT = 150
LINES_PER_CHUNK = 500

# Where each harness keeps its transcripts, for id-prefix location.
SEARCH_ROOTS = {
    "codex": ["~/.codex/sessions"],
    "pi": ["~/.pi/agent/sessions"],
    "zcode": ["~/.zcode"],
    "auto": ["~/.codex/sessions", "~/.pi/agent/sessions", "~/.zcode"],
}


def die(code: int, msg: str) -> None:
    print(f"extract.py: {msg}", file=sys.stderr)
    raise SystemExit(code)


def locate(target: str, agent: str) -> Path:
    """Return an existing file path for a path or id-prefix target."""
    p = Path(os.path.expanduser(target))
    if p.is_file():
        return p
    roots = SEARCH_ROOTS[agent]
    hits: list[Path] = []
    for root in roots:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        for pat in (f"**/*{target}*.jsonl", f"**/*{target}*.json"):
            hits.extend(Path(m) for m in glob.glob(os.path.join(root, pat), recursive=True))
    hits = sorted({h for h in hits if h.is_file()}, key=lambda h: h.stat().st_size, reverse=True)
    if not hits:
        die(2, f"target '{target}' is neither a file nor a locatable id under {roots}")
    if len(hits) > 1:
        print(f"extract.py: {len(hits)} candidates, using largest: {hits[0]}", file=sys.stderr)
    return hits[0]


def content_text(content) -> str:
    """Normalize a message content field (str | list[{text}] | list[str])."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                t = item.get("text")
                if isinstance(t, str):
                    parts.append(t)
        return "\n".join(p for p in parts if p)
    return str(content)


# --- per-harness extractors -------------------------------------------------
# Each yields (role, text) in file order; raise ValueError on shape mismatch.


def iter_codex(lines):
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get("type") != "response_item":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "message":
            continue
        role = payload.get("role")
        if role in ("user", "assistant"):
            yield role, content_text(payload.get("content"))


def iter_pi(lines):
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or row.get("type") != "message":
            continue
        msg = row.get("message")
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role in ("user", "assistant"):
            yield role, content_text(msg.get("content"))


def _walk_messages(node, depth=0):
    """Generic probe: recursively find dicts with role in {user,assistant}."""
    if depth > 6 or node is None:
        return
    if isinstance(node, dict):
        role = node.get("role")
        if role in ("user", "assistant") and ("content" in node or "text" in node):
            yield role, content_text(node.get("content")) or str(node.get("text") or "")
        for v in node.values():
            yield from _walk_messages(v, depth + 1)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_messages(item, depth + 1)


def iter_probe(lines):
    """Unknown harness: probe per line, tolerate noise."""
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield from _walk_messages(row)


EXTRACTORS = {"codex": iter_codex, "pi": iter_pi}
# pi first: it also matches many generic shapes, so try it before probing.
FALLBACK_ORDER = ["codex", "pi"]


def extract(path: Path, agent: str):
    """Return (user_msgs, asst_msgs, session_cwd, extractor_name)."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()
    first = {}
    for line in lines[:5]:
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                first = row
                break
        except json.JSONDecodeError:
            continue
    session_cwd = first.get("cwd") if isinstance(first.get("cwd"), str) else None

    order = [agent] if agent in EXTRACTORS else FALLBACK_ORDER
    for name in order:
        users, assts = [], []
        for role, text in EXTRACTORS[name](lines):
            (users if role == "user" else assts).append(text)
        if users:
            return users, assts, session_cwd, name

    if agent in ("zcode", "auto"):
        users, assts = [], []
        for role, text in iter_probe(lines):
            (users if role == "user" else assts).append(text)
        if users:
            return users, assts, session_cwd, "probe"
        die(3, f"unrecognized transcript format: {path} (no user messages found; "
               "inspect the file and extend this script)")
    die(3, f"no {agent} messages found in {path}; the file may use another "
           "harness's format — retry with --agent auto")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", required=True, choices=["codex", "pi", "zcode", "auto"])
    ap.add_argument("--target", required=True, help="session file path or session-id prefix")
    ap.add_argument("--out-dir", default=None, help="default /tmp/rescue-<target-basename>")
    ap.add_argument("--asst-tail", type=int, default=ASST_TAIL_DEFAULT)
    args = ap.parse_args()

    path = locate(args.target, args.agent)
    out = Path(os.path.expanduser(args.out_dir or f"/tmp/rescue-{path.stem}"))
    out.mkdir(parents=True, exist_ok=True)

    users, assts, session_cwd, extractor = extract(path, args.agent)

    user_txt = "\n\n".join(u for u in users if u.strip())
    (out / "user-all.txt").write_text(user_txt, encoding="utf-8")
    (out / "asst-tail.txt").write_text(
        "\n\n".join(a for a in assts[-args.asst_tail:] if a.strip()), encoding="utf-8")

    user_lines = user_txt.count("\n") + (1 if user_txt else 0)
    chunks = max(1, -(-user_lines // LINES_PER_CHUNK))
    meta = [
        f"source_file: {path}",
        f"source_bytes: {path.stat().st_size}",
        f"extractor: {extractor}",
        f"session_cwd: {session_cwd or '(unknown)'}",
        f"user_messages: {len(users)}",
        f"assistant_messages: {len(assts)}",
        f"user_all_bytes: {len(user_txt.encode('utf-8'))}",
        f"user_all_lines: {user_lines}",
        f"suggested_chunks (~{LINES_PER_CHUNK} lines each): {chunks}",
    ]
    (out / "meta.txt").write_text("\n".join(meta) + "\n", encoding="utf-8")

    print("\n".join(meta))
    print(f"out_dir: {out}")
    if len(user_txt.encode("utf-8")) > 2 * 1024 * 1024:
        print("NOTE: user-all.txt exceeds 2 MB — confirm token budget before the "
              "summarize step.", file=sys.stderr)


if __name__ == "__main__":
    main()
