#!/usr/bin/env python3
"""MCP server for the knowledge-base repository.

This server is the single interface an agent needs to work the vault over stdio
with JSON-RPC 2.0.  The vault holds domains (domains/<domain>/ with features/
and rules/), repositories (repositories/<repo>/) and resources
(resources/<slug>/, originals under raw/); the graph tags every node with its
kind (`type`) and, for domain notes, its `domain`.  It exposes graph and note *querying* (graph_summary,
graph_search_nodes, graph_neighbors, read_note, refresh_graph), *writing*
(write_note for text, capture_raw for verbatim bytes from a local file or an
http(s) download) and *publishing* (edit_note, git_commit, git_push), so an
agent without shell or filesystem tools can ingest a resource end to end.

Every write is confined to the repository root, and staging is always explicit:
paths are named one by one, never `.` or `-A`.

It auto-detects the transport layer:
  - Content-Length framing (MCP spec, used by most clients)
  - Newline-delimited JSON (used by Claude Code ≥ 2.1)
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


SERVER_NAME = "knowledge-base-mcp"
SERVER_VERSION = "0.1.0"


@dataclass
class AppState:
    root: Path
    graph_path: Path


class _StdinReader:
    """Buffered stdin reader that supports transport auto-detection."""

    def __init__(self, raw: Any) -> None:
        self._raw = raw
        self._prefix: bytes = b""

    def read(self, n: int) -> bytes:
        if self._prefix:
            chunk, self._prefix = self._prefix[:n], self._prefix[n:]
            remaining = n - len(chunk)
            return chunk + (self._raw.read(remaining) if remaining else b"")
        return self._raw.read(n)

    def readline(self) -> bytes:
        if self._prefix:
            nl = self._prefix.find(b"\n")
            if nl != -1:
                line, self._prefix = self._prefix[: nl + 1], self._prefix[nl + 1 :]
                return line
            prefix, self._prefix = self._prefix, b""
            return prefix + self._raw.readline()
        return self._raw.readline()

    def peek_byte(self) -> bytes:
        b = self._raw.read(1)
        if b:
            self._prefix = b + self._prefix
        return b


_WHITESPACE_BYTES = {b"\r", b"\n", b"\t", b" "}


def _detect_transport(reader: _StdinReader) -> str:
    """Peek at the first non-whitespace byte to decide 'ndjson' vs 'framed'.

    Leading ASCII whitespace bytes are discarded — they corrupt neither JSON
    nor Content-Length headers, and some client wrappers emit stray newlines
    before the first message.  EOF before any non-whitespace defaults to
    'ndjson' so the read loop exits cleanly on an empty stream.
    """
    while True:
        b = reader._raw.read(1)
        if not b:
            return "ndjson"
        if b not in _WHITESPACE_BYTES:
            reader._prefix = b + reader._prefix
            return "ndjson" if b == b"{" else "framed"


def _read_message_framed(reader: _StdinReader) -> Dict[str, Any] | None:
    headers: Dict[str, str] = {}
    while True:
        line = reader.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.strip().lower()] = value.strip()

    length_raw = headers.get("content-length")
    if not length_raw:
        raise ValueError("missing Content-Length header")
    length = int(length_raw)
    payload = reader.read(length)
    if len(payload) != length:
        raise ValueError("incomplete payload")
    return json.loads(payload.decode("utf-8"))


def _read_message_ndjson(reader: _StdinReader) -> Dict[str, Any] | None:
    while True:
        line = reader.readline()
        if not line:
            return None
        stripped = line.strip()
        if not stripped:
            continue
        return json.loads(stripped.decode("utf-8"))


def _write_message_framed(stdout: Any, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    stdout.buffer.write(f"Content-Length: {len(data)}\r\n\r\n".encode("utf-8"))
    stdout.buffer.write(data)
    stdout.buffer.flush()


def _write_message_ndjson(stdout: Any, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8") + b"\n"
    stdout.buffer.write(data)
    stdout.buffer.flush()



def _response(message_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {"code": code, "message": message},
    }


def _load_graph(state: AppState) -> Dict[str, Any]:
    if not state.graph_path.exists():
        raise FileNotFoundError(
            f"graph not found at {state.graph_path}. Run scripts/generate-graph.py first."
        )
    return json.loads(state.graph_path.read_text(encoding="utf-8"))


def _nodes_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    nodes = graph.get("nodes", [])
    return {str(node.get("id")): node for node in nodes if isinstance(node, dict)}


def _match_filters(node: Dict[str, Any], args: Dict[str, Any]) -> bool:
    domain = args.get("domain")
    note_type = args.get("type")
    status = args.get("status")
    tag = args.get("tag")
    query = str(args.get("query", "")).strip().lower()

    if domain and node.get("domain") != domain:
        return False
    if note_type and node.get("type") != note_type:
        return False
    if status and node.get("status") != status:
        return False
    if tag and tag not in (node.get("tags") or []):
        return False
    if query:
        haystacks = [
            str(node.get("id", "")).lower(),
            str(node.get("title", "")).lower(),
            str(node.get("path", "")).lower(),
            " ".join(str(t).lower() for t in (node.get("tags") or [])),
        ]
        if not any(query in h for h in haystacks):
            return False
    return True


_WILDCARD_PATHS = {".", "./", "-A", "--all", "*", "-a", ":/"}

# Ceiling for a single capture_raw call; papers and slide decks fit, a video
# download that would bloat the vault does not.
_DEFAULT_MAX_CAPTURE_BYTES = 100 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 60

# graph_summary defaults: enough most-linked notes to spot the hubs, and enough
# tags to cover the vocabulary an agent actually filters on.
_DEFAULT_TOP_LINKED = 10
_DEFAULT_TOP_TAGS = 50


def _resolve_in_root(state: AppState, raw_path: Any, *, label: str = "path") -> Path:
    """Turn a vault-relative path into an absolute path inside the repo root.

    Rejects empty values, absolute paths and anything escaping the root, so a
    tool call can never touch a file outside the vault.
    """
    value = str(raw_path or "").strip()
    if not value:
        raise ValueError(f"'{label}' is required")
    candidate = Path(value)
    if candidate.is_absolute():
        raise ValueError(f"'{label}' must be vault-relative, got absolute '{value}'")
    root = state.root.resolve()
    target = (root / candidate).resolve()
    if target != root and not target.is_relative_to(root):
        raise ValueError(f"'{label}' resolves outside repository root: '{value}'")
    return target


def _relative_to_root(state: AppState, target: Path) -> str:
    return target.relative_to(state.root.resolve()).as_posix()


def _run_git(state: AppState, args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=state.root,
        check=False,
        capture_output=True,
        text=True,
    )


def _git_result(payload: Dict[str, Any], exit_code: int) -> Dict[str, Any]:
    text = json.dumps(payload, indent=2)
    if exit_code != 0:
        return {
            "isError": True,
            "content": [{"type": "text", "text": text}],
            "structuredContent": payload,
        }
    return _text_result(text, structured=payload)


def _tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "name": "graph_summary",
            "description": (
                "Orientation for a cold start: node and edge counts, notes "
                "per domain as `by_domain`, the most-linked notes, and the tag vocabulary as "
                "`by_tag` (most frequent first) plus `tag_count`, the number of "
                "distinct tags. Read `by_tag` before filtering "
                "`graph_search_nodes` by `tag` \u2014 that filter matches a tag "
                "verbatim, so a guessed spelling returns nothing."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topLinked": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "description": "Most-linked notes to return (default 10).",
                    },
                    "topTags": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 500,
                        "description": "Tags to return, most frequent first (default 50).",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "graph_search_nodes",
            "description": (
                "Search graph nodes by metadata and free text. `type` is the "
                "kind of note (hub, meta, domain, feature, rule, repository, "
                "resource); `domain` is the folder name under domains/."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "type": {"type": "string"},
                    "status": {"type": "string"},
                    "tag": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                },
            },
        },
        {
            "name": "graph_neighbors",
            "description": (
                "Show inbound and outbound links for a node ID. Each neighbor "
                "includes the edge `type` (relationship, e.g. implemented-in, "
                "context, part-of), `anchor_text` (the link's display text), and "
                "`annotation` (what to expect in that note)."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                },
            },
        },
        {
            "name": "read_note",
            "description": (
                "Read note content by graph node ID or vault-relative path. "
                "Provide exactly one of `id` or `path`. "
                "If both or neither are provided, the call returns an error."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Graph node ID (e.g. 'AGENTS')."},
                    "path": {"type": "string", "description": "Vault-relative file path (e.g. 'README.md')."},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "refresh_graph",
            "description": "Regenerate graph.json using scripts/generate-graph.py.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "validate": {"type": "boolean"},
                },
            },
        },
        {
            "name": "write_note",
            "description": (
                "Create a note (or any text file) at a vault-relative path, "
                "creating parent directories as needed. Fails if the file "
                "exists unless `overwrite` is true. The generated "
                "`index/graph.json` is off limits — use `refresh_graph`."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Vault-relative path, e.g. 'resources/demo/index.md'.",
                    },
                    "content": {"type": "string", "description": "Full file content."},
                    "overwrite": {
                        "type": "boolean",
                        "description": "Replace an existing file (default false).",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "edit_note",
            "description": (
                "Replace an exact string inside an existing note. `old_string` "
                "must occur exactly once unless `replace_all` is true."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["path", "old_string", "new_string"],
                "properties": {
                    "path": {"type": "string", "description": "Vault-relative path of the note."},
                    "old_string": {"type": "string", "description": "Text to replace, matched verbatim."},
                    "new_string": {"type": "string", "description": "Replacement text."},
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence (default false).",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "capture_raw",
            "description": (
                "Copy a local file or download an http(s) URL into the vault "
                "byte-for-byte — the way an original PDF, image, or archive is "
                "preserved under `resources/<slug>/raw/`. Provide exactly one "
                "of `source_path` (absolute or CWD-relative path on this machine) "
                "or `url`. Binary-safe; returns size and sha256. Read the "
                "captured file back with `read_note`, which reports binary files "
                "with an absolute path to open with a file-reading tool."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Vault-relative destination, e.g. 'resources/demo/raw/paper.pdf'.",
                    },
                    "source_path": {
                        "type": "string",
                        "description": "Path of the local file to copy.",
                    },
                    "url": {
                        "type": "string",
                        "description": "http(s) URL to download verbatim.",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Replace an existing capture (default false).",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Reject captures larger than this (default 100 MiB).",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "git_commit",
            "description": (
                "Stage the named vault-relative paths individually and commit "
                "them. `paths` must list every path explicitly — wildcard "
                "staging ('.', '-A', '*') is rejected. Returns an error result "
                "if git refuses the commit (e.g. nothing staged)."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["message", "paths"],
                "properties": {
                    "message": {"type": "string", "description": "Commit message (Conventional Commits)."},
                    "paths": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string"},
                        "description": "Vault-relative paths to stage, one entry per file or directory.",
                    },
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "git_push",
            "description": (
                "Push commits to a remote. Defaults to 'origin' and the current "
                "branch. Returns an error result if git refuses the push."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "remote": {"type": "string", "description": "Remote name (default 'origin')."},
                    "branch": {"type": "string", "description": "Branch to push (default: current branch)."},
                    "set_upstream": {
                        "type": "boolean",
                        "description": "Pass --set-upstream (default false).",
                    },
                },
                "additionalProperties": False,
            },
        },
    ]


def _text_result(text: str, structured: Dict[str, Any] | None = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if structured is not None:
        result["structuredContent"] = structured
    return result


def _tool_graph_summary(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    graph = _load_graph(state)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    top_n = int(args.get("topLinked", _DEFAULT_TOP_LINKED))
    top_tags = int(args.get("topTags", _DEFAULT_TOP_TAGS))

    by_domain: Counter[str] = Counter(
        str(node["domain"]) for node in nodes if node.get("domain")
    )
    tag_counts: Counter[str] = Counter(
        str(tag) for node in nodes for tag in (node.get("tags") or [])
    )
    # Frequent tags first, alphabetical within a tie, so a truncated list is
    # both the most useful slice and stable across calls.
    ranked_tags = sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))

    sorted_nodes = sorted(
        nodes,
        key=lambda n: int(n.get("inbound_count", 0)),
        reverse=True,
    )[:top_n]
    payload = {
        "version": graph.get("version"),
        "generated_at": graph.get("generated_at"),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "by_domain": dict(by_domain),
        "tag_count": len(tag_counts),
        "by_tag": [
            {"tag": tag, "count": count} for tag, count in ranked_tags[:top_tags]
        ],
        "top_linked": [
            {
                "id": node.get("id"),
                "title": node.get("title"),
                "path": node.get("path"),
                "inbound_count": node.get("inbound_count", 0),
            }
            for node in sorted_nodes
        ],
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_graph_search_nodes(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    graph = _load_graph(state)
    nodes = graph.get("nodes", [])
    limit = int(args.get("limit", 30))
    filtered = [node for node in nodes if _match_filters(node, args)]
    filtered.sort(key=lambda n: str(n.get("id", "")))
    sliced = filtered[:limit]
    payload = {
        "total_matches": len(filtered),
        "returned": len(sliced),
        "items": sliced,
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_graph_neighbors(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    graph = _load_graph(state)
    node_id = str(args["id"])
    limit = int(args.get("limit", 50))
    nodes = _nodes_by_id(graph)
    if node_id not in nodes:
        raise ValueError(f"node '{node_id}' not found")

    edges = graph.get("edges", [])
    outbound_edges = [e for e in edges if e.get("from") == node_id]
    inbound_edges = [e for e in edges if e.get("to") == node_id]

    def describe(edge_list: List[Dict[str, Any]], direction: str) -> List[Dict[str, Any]]:
        # neighbor id is the "other end" relative to node_id
        other_key = "to" if direction == "outbound" else "from"
        result: List[Dict[str, Any]] = []
        for edge in edge_list:
            item_id = str(edge.get(other_key))
            node = nodes.get(item_id)
            entry = {
                "id": node.get("id") if node else item_id,
                "title": node.get("title") if node else "<missing>",
                "path": node.get("path") if node else "",
                "direction": direction,
                "type": edge.get("type", "related"),
                "anchor_text": edge.get("anchor_text", ""),
                "annotation": edge.get("annotation", ""),
            }
            result.append(entry)
        return result[:limit]

    payload = {
        "node": nodes[node_id],
        "inbound_count": len(inbound_edges),
        "outbound_count": len(outbound_edges),
        "inbound": describe(inbound_edges, "inbound"),
        "outbound": describe(outbound_edges, "outbound"),
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_read_note(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    has_id = bool(args.get("id"))
    has_path = bool(args.get("path"))

    if has_id and has_path:
        raise ValueError("provide exactly one of 'id' or 'path', not both")
    if not has_id and not has_path:
        raise ValueError("exactly one of 'id' or 'path' is required")

    path_value = args.get("path")

    if has_id:
        nodes = _nodes_by_id(_load_graph(state))
        node = nodes.get(str(args["id"]))
        if not node:
            raise ValueError(f"node '{args['id']}' not found")
        path_value = node.get("path")

    target = (state.root / str(path_value)).resolve()
    if not target.is_relative_to(state.root.resolve()):
        raise ValueError("note path resolves outside repository root")
    if not target.exists():
        raise FileNotFoundError(f"note not found at {target}")

    relative = str(target.relative_to(state.root).as_posix())
    data = target.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        payload = {
            "path": relative,
            "binary": True,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "hint": (
                f"{target} is not UTF-8 text (e.g. a PDF or image captured under "
                "raw/). Open it with a file-reading tool that handles binaries; "
                "this server returns text only."
            ),
        }
        return _text_result(json.dumps(payload, indent=2), structured=payload)

    payload = {
        "path": relative,
        "binary": False,
        "content": text,
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_refresh_graph(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    command = [sys.executable, "scripts/generate-graph.py"]
    if bool(args.get("validate", False)):
        command.append("--validate")

    proc = subprocess.run(
        command,
        cwd=state.root,
        check=False,
        capture_output=True,
        text=True,
    )

    payload = {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.returncode != 0:
        return {
            "isError": True,
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "structuredContent": payload,
        }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_write_note(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    if "content" not in args:
        raise ValueError("'content' is required")
    content = str(args["content"])
    target = _resolve_in_root(state, args.get("path"))
    relative = _relative_to_root(state, target)
    if relative == state.graph_path.relative_to(state.root.resolve()).as_posix():
        raise ValueError(
            "index/graph.json is generated \u2014 use refresh_graph instead of writing it"
        )

    existed = target.exists()
    if existed and not bool(args.get("overwrite", False)):
        raise FileExistsError(
            f"note already exists at {relative}; pass overwrite=true to replace it"
        )
    if existed and target.is_dir():
        raise ValueError(f"'{relative}' is a directory")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    payload = {
        "path": relative,
        "created": not existed,
        "bytes": len(content.encode("utf-8")),
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_edit_note(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    if "old_string" not in args or "new_string" not in args:
        raise ValueError("'old_string' and 'new_string' are required")
    old_string = str(args["old_string"])
    new_string = str(args["new_string"])
    if not old_string:
        raise ValueError("'old_string' must not be empty")
    if old_string == new_string:
        raise ValueError("'old_string' and 'new_string' are identical")

    target = _resolve_in_root(state, args.get("path"))
    relative = _relative_to_root(state, target)
    if not target.is_file():
        raise FileNotFoundError(f"note not found at {relative}")

    text = target.read_text(encoding="utf-8")
    occurrences = text.count(old_string)
    if occurrences == 0:
        raise ValueError(f"'old_string' not found in {relative}")
    replace_all = bool(args.get("replace_all", False))
    if occurrences > 1 and not replace_all:
        raise ValueError(
            f"'old_string' occurs {occurrences} times in {relative}; "
            "make it unique or pass replace_all=true"
        )

    updated = text.replace(old_string, new_string)
    target.write_text(updated, encoding="utf-8")
    payload = {
        "path": relative,
        "replacements": occurrences if replace_all else 1,
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _download_bytes(url: str, max_bytes: int) -> bytes:
    """Fetch an http(s) URL into memory, refusing anything over `max_bytes`."""
    request = urllib.request.Request(
        url, headers={"User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"}
    )
    with urllib.request.urlopen(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
        declared = response.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            raise ValueError(
                f"remote file is {declared} bytes, over the {max_bytes} byte limit"
            )
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"download exceeds the {max_bytes} byte limit")
    return data


def _tool_capture_raw(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    source_path = str(args.get("source_path") or "").strip()
    url = str(args.get("url") or "").strip()
    if bool(source_path) == bool(url):
        raise ValueError("provide exactly one of 'source_path' or 'url'")

    max_bytes = int(args.get("max_bytes", _DEFAULT_MAX_CAPTURE_BYTES))
    if max_bytes < 1:
        raise ValueError("'max_bytes' must be positive")

    target = _resolve_in_root(state, args.get("path"))
    relative = _relative_to_root(state, target)
    existed = target.exists()
    if existed and not bool(args.get("overwrite", False)):
        raise FileExistsError(
            f"capture already exists at {relative}; pass overwrite=true to replace it"
        )
    if existed and target.is_dir():
        raise ValueError(f"'{relative}' is a directory")

    if source_path:
        origin = Path(source_path).expanduser()
        if not origin.exists():
            raise FileNotFoundError(f"source file not found at {origin}")
        if not origin.is_file():
            raise ValueError(f"source is not a file: {origin}")
        size = origin.stat().st_size
        if size > max_bytes:
            raise ValueError(
                f"source file is {size} bytes, over the {max_bytes} byte limit"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, target)
        data = target.read_bytes()
        source_label = str(origin)
    else:
        scheme = url.split(":", 1)[0].lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"only http(s) URLs can be captured, got '{url}'")
        try:
            data = _download_bytes(url, max_bytes)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            payload = {
                "url": url,
                "path": relative,
                "exit_code": 1,
                "stderr": f"download failed: {exc}",
            }
            return _git_result(payload, 1)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        source_label = url

    payload = {
        "path": relative,
        "absolute_path": str(target),
        "source": source_label,
        "created": not existed,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return _text_result(json.dumps(payload, indent=2), structured=payload)


def _tool_git_commit(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    message = str(args.get("message", "")).strip()
    if not message:
        raise ValueError("'message' is required")

    raw_paths = args.get("paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        raise ValueError("'paths' must list at least one vault-relative path")

    relatives: List[str] = []
    for raw in raw_paths:
        value = str(raw or "").strip()
        if value in _WILDCARD_PATHS or value.startswith("-"):
            raise ValueError(
                f"wildcard staging is not allowed: '{value}'. Name each path explicitly."
            )
        target = _resolve_in_root(state, value, label="paths[]")
        relative = _relative_to_root(state, target)
        if not target.exists():
            raise FileNotFoundError(f"path not found at {relative}")
        relatives.append(relative)

    relatives = sorted(set(relatives))
    for relative in relatives:
        add = _run_git(state, ["add", "--", relative])
        if add.returncode != 0:
            payload = {
                "command": ["git", "add", "--", relative],
                "exit_code": add.returncode,
                "stdout": add.stdout,
                "stderr": add.stderr,
                "committed_paths": [],
            }
            return _git_result(payload, add.returncode)

    commit = _run_git(state, ["commit", "-m", message])
    payload = {
        "command": ["git", "commit", "-m", message],
        "exit_code": commit.returncode,
        "stdout": commit.stdout,
        "stderr": commit.stderr,
        "committed_paths": relatives if commit.returncode == 0 else [],
    }
    if commit.returncode == 0:
        head = _run_git(state, ["rev-parse", "--short", "HEAD"])
        payload["commit"] = head.stdout.strip()
    return _git_result(payload, commit.returncode)


def _tool_git_push(state: AppState, args: Dict[str, Any]) -> Dict[str, Any]:
    remote = str(args.get("remote") or "origin").strip()
    branch = str(args.get("branch") or "").strip()
    for label, value in (("remote", remote), ("branch", branch)):
        if value.startswith("-"):
            raise ValueError(f"'{label}' must not look like an option: '{value}'")
    if not remote:
        raise ValueError("'remote' must not be empty")

    if not branch:
        head = _run_git(state, ["rev-parse", "--abbrev-ref", "HEAD"])
        if head.returncode != 0:
            payload = {
                "command": ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                "exit_code": head.returncode,
                "stdout": head.stdout,
                "stderr": head.stderr,
            }
            return _git_result(payload, head.returncode)
        branch = head.stdout.strip()

    command = ["push"]
    if bool(args.get("set_upstream", False)):
        command.append("--set-upstream")
    command += [remote, branch]

    push = _run_git(state, command)
    payload = {
        "command": ["git", *command],
        "remote": remote,
        "branch": branch,
        "exit_code": push.returncode,
        "stdout": push.stdout,
        "stderr": push.stderr,
    }
    return _git_result(payload, push.returncode)


def _call_tool(state: AppState, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "graph_summary":
        return _tool_graph_summary(state, arguments)
    if name == "graph_search_nodes":
        return _tool_graph_search_nodes(state, arguments)
    if name == "graph_neighbors":
        return _tool_graph_neighbors(state, arguments)
    if name == "read_note":
        return _tool_read_note(state, arguments)
    if name == "refresh_graph":
        return _tool_refresh_graph(state, arguments)
    if name == "write_note":
        return _tool_write_note(state, arguments)
    if name == "edit_note":
        return _tool_edit_note(state, arguments)
    if name == "capture_raw":
        return _tool_capture_raw(state, arguments)
    if name == "git_commit":
        return _tool_git_commit(state, arguments)
    if name == "git_push":
        return _tool_git_push(state, arguments)
    raise ValueError(f"unknown tool '{name}'")


def _list_resources(state: AppState) -> Dict[str, Any]:
    return {
        "resources": [
            {
                "uri": "repo://graph",
                "name": "Repository Graph",
                "description": "Raw index/graph.json",
                "mimeType": "application/json",
            },
            {
                "uri": "repo://readme",
                "name": "Repository README",
                "description": "Root README.md",
                "mimeType": "text/markdown",
            },
        ]
    }


def _read_resource(state: AppState, uri: str) -> Dict[str, Any]:
    if uri == "repo://graph":
        text = state.graph_path.read_text(encoding="utf-8")
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": text,
                }
            ]
        }
    if uri == "repo://readme":
        readme = (state.root / "README.md").read_text(encoding="utf-8")
        return {"contents": [{"uri": uri, "mimeType": "text/markdown", "text": readme}]}
    raise ValueError(f"unknown resource '{uri}'")


def _handle_request(state: AppState, message: Dict[str, Any]) -> Dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    params = message.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "capabilities": {"tools": {}, "resources": {}},
        }
        return _response(message_id, result)

    if method == "tools/list":
        return _response(message_id, {"tools": _tool_definitions()})

    if method == "tools/call":
        try:
            tool_name = str(params.get("name", ""))
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            result = _call_tool(state, tool_name, arguments)
            return _response(message_id, result)
        except Exception as exc:
            error_result = {
                "isError": True,
                "content": [{"type": "text", "text": str(exc)}],
            }
            return _response(message_id, error_result)

    if method == "resources/list":
        return _response(message_id, _list_resources(state))

    if method == "resources/read":
        try:
            uri = str(params.get("uri", ""))
            return _response(message_id, _read_resource(state, uri))
        except Exception as exc:
            return _error(message_id, -32602, str(exc))

    if message_id is None:
        return None
    return _error(message_id, -32601, f"method not found: {method}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    state = AppState(root=root, graph_path=root / "index" / "graph.json")

    reader = _StdinReader(sys.stdin.buffer)
    try:
        transport = _detect_transport(reader)
    except OSError as exc:
        print(
            json.dumps({"error": "transport detection failed", "detail": str(exc)}),
            file=sys.stderr,
        )
        sys.exit(1)
    if transport == "ndjson":
        read_msg = _read_message_ndjson
        write_msg = _write_message_ndjson
    else:
        read_msg = _read_message_framed
        write_msg = _write_message_framed

    while True:
        try:
            message = read_msg(reader)
        except Exception as exc:
            write_msg(sys.stdout, _error(None, -32700, f"parse error: {exc}"))
            continue

        if message is None:
            break

        response = _handle_request(state, message)
        if response is not None:
            write_msg(sys.stdout, response)


if __name__ == "__main__":
    main()
