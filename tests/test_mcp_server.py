#!/usr/bin/env python3
"""Tests for the knowledge-base MCP server's query, write and git tools.

Covers the tools an agent needs when the MCP server is its only way into the
vault: orienting with graph_summary, creating notes, editing notes, capturing
raw bytes (local files and downloads), committing staged paths, and pushing.
Each test drives the server through `_call_tool` against a throwaway repository
so no test touches the real vault.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import importlib

mcp = importlib.import_module("mcp-server")


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


class ToolTestCase(unittest.TestCase):
    """Base case: a temporary git repo standing in for the vault."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve() / "vault"
        self.root.mkdir()
        self.state = mcp.AppState(
            root=self.root, graph_path=self.root / "index" / "graph.json"
        )
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "test@example.com")
        _git(self.root, "config", "user.name", "Test")
        _git(self.root, "config", "commit.gpgsign", "false")
        (self.root / "README.md").write_text("# vault\n", encoding="utf-8")
        _git(self.root, "add", "README.md")
        _git(self.root, "commit", "-qm", "init")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def call(self, name: str, **args) -> dict:
        return mcp._call_tool(self.state, name, args)

    def structured(self, name: str, **args) -> dict:
        return self.call(name, **args)["structuredContent"]


class TestToolDefinitions(unittest.TestCase):
    def test_write_and_git_tools_are_advertised(self) -> None:
        names = {tool["name"] for tool in mcp._tool_definitions()}
        self.assertLessEqual(
            {"write_note", "edit_note", "capture_raw", "git_commit", "git_push"},
            names,
        )

    def test_every_tool_has_a_schema_and_description(self) -> None:
        for tool in mcp._tool_definitions():
            self.assertTrue(tool.get("description"), tool["name"])
            self.assertEqual(tool["inputSchema"]["type"], "object", tool["name"])


class TestWriteNote(ToolTestCase):
    def test_creates_note_and_parent_directories(self) -> None:
        payload = self.structured(
            "write_note",
            path="03_resources/demo/index.md",
            content="---\nid: resource/demo\n---\n\n# Demo\n",
        )
        target = self.root / "03_resources/demo/index.md"
        self.assertTrue(target.exists())
        self.assertIn("# Demo", target.read_text(encoding="utf-8"))
        self.assertEqual(payload["path"], "03_resources/demo/index.md")
        self.assertTrue(payload["created"])

    def test_refuses_to_overwrite_existing_note_by_default(self) -> None:
        self.call("write_note", path="note.md", content="first")
        with self.assertRaises(FileExistsError):
            self.call("write_note", path="note.md", content="second")
        self.assertEqual((self.root / "note.md").read_text(encoding="utf-8"), "first")

    def test_overwrites_when_asked(self) -> None:
        self.call("write_note", path="note.md", content="first")
        payload = self.structured(
            "write_note", path="note.md", content="second", overwrite=True
        )
        self.assertFalse(payload["created"])
        self.assertEqual((self.root / "note.md").read_text(encoding="utf-8"), "second")

    def test_rejects_path_outside_the_vault(self) -> None:
        with self.assertRaises(ValueError):
            self.call("write_note", path="../escape.md", content="nope")
        self.assertFalse((self.root.parent / "escape.md").exists())

    def test_rejects_absolute_path(self) -> None:
        with self.assertRaises(ValueError):
            self.call("write_note", path="/tmp/escape.md", content="nope")

    def test_requires_path_and_content(self) -> None:
        with self.assertRaises(ValueError):
            self.call("write_note", content="orphan")
        with self.assertRaises(ValueError):
            self.call("write_note", path="note.md")

    def test_rejects_writes_into_the_generated_graph(self) -> None:
        with self.assertRaises(ValueError):
            self.call("write_note", path="index/graph.json", content="{}")


class TestEditNote(ToolTestCase):
    def setUp(self) -> None:
        super().setUp()
        (self.root / "note.md").write_text("alpha beta alpha\n", encoding="utf-8")

    def test_replaces_a_unique_occurrence(self) -> None:
        payload = self.structured(
            "edit_note", path="note.md", old_string="beta", new_string="gamma"
        )
        self.assertEqual(payload["replacements"], 1)
        self.assertEqual(
            (self.root / "note.md").read_text(encoding="utf-8"), "alpha gamma alpha\n"
        )

    def test_rejects_ambiguous_occurrence(self) -> None:
        with self.assertRaises(ValueError):
            self.call("edit_note", path="note.md", old_string="alpha", new_string="x")
        self.assertEqual(
            (self.root / "note.md").read_text(encoding="utf-8"), "alpha beta alpha\n"
        )

    def test_replaces_all_when_asked(self) -> None:
        payload = self.structured(
            "edit_note",
            path="note.md",
            old_string="alpha",
            new_string="x",
            replace_all=True,
        )
        self.assertEqual(payload["replacements"], 2)
        self.assertEqual(
            (self.root / "note.md").read_text(encoding="utf-8"), "x beta x\n"
        )

    def test_errors_when_old_string_absent(self) -> None:
        with self.assertRaises(ValueError):
            self.call("edit_note", path="note.md", old_string="zeta", new_string="x")

    def test_errors_when_note_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.call("edit_note", path="ghost.md", old_string="a", new_string="b")

    def test_rejects_identical_strings(self) -> None:
        with self.assertRaises(ValueError):
            self.call("edit_note", path="note.md", old_string="beta", new_string="beta")

    def test_rejects_path_outside_the_vault(self) -> None:
        with self.assertRaises(ValueError):
            self.call("edit_note", path="../../x.md", old_string="a", new_string="b")


class TestGitCommit(ToolTestCase):
    def _log(self) -> str:
        return _git(self.root, "log", "--format=%s", "-n", "1").stdout.strip()

    def test_stages_named_paths_and_commits(self) -> None:
        self.call("write_note", path="03_resources/demo/index.md", content="# Demo\n")
        self.call("write_note", path="03_resources/demo/topic.md", content="# Topic\n")
        payload = self.structured(
            "git_commit",
            message="feat: ingest demo resource",
            paths=["03_resources/demo/index.md", "03_resources/demo/topic.md"],
        )
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(self._log(), "feat: ingest demo resource")
        self.assertEqual(payload["committed_paths"], sorted(payload["committed_paths"]))
        self.assertEqual(
            _git(self.root, "status", "--porcelain").stdout.strip(), ""
        )

    def test_commits_only_the_named_paths(self) -> None:
        self.call("write_note", path="wanted.md", content="a\n")
        self.call("write_note", path="unwanted.md", content="b\n")
        self.call("git_commit", message="feat: only wanted", paths=["wanted.md"])
        status = _git(self.root, "status", "--porcelain").stdout.split()
        self.assertIn("unwanted.md", status)
        self.assertNotIn("wanted.md", status)

    def test_requires_at_least_one_path(self) -> None:
        with self.assertRaises(ValueError):
            self.call("git_commit", message="feat: nothing", paths=[])

    def test_rejects_wildcard_staging(self) -> None:
        for bad in [".", "-A", "*", "./"]:
            with self.assertRaises(ValueError):
                self.call("git_commit", message="feat: broad", paths=[bad])

    def test_requires_a_message(self) -> None:
        self.call("write_note", path="note.md", content="a\n")
        with self.assertRaises(ValueError):
            self.call("git_commit", message="", paths=["note.md"])

    def test_rejects_path_outside_the_vault(self) -> None:
        with self.assertRaises(ValueError):
            self.call("git_commit", message="feat: escape", paths=["../outside.md"])

    def test_errors_when_path_does_not_exist(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.call("git_commit", message="feat: ghost", paths=["ghost.md"])

    def test_reports_error_when_nothing_to_commit(self) -> None:
        result = self.call("git_commit", message="feat: noop", paths=["README.md"])
        self.assertTrue(result.get("isError"))
        self.assertNotEqual(result["structuredContent"]["exit_code"], 0)


class TestGitPush(ToolTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.remote = self.root.parent / "remote.git"
        _git(self.root.parent, "init", "-q", "--bare", str(self.remote))
        _git(self.root, "remote", "add", "origin", str(self.remote))

    def _remote_log(self) -> str:
        return subprocess.run(
            ["git", "log", "--format=%s", "-n", "1", "main"],
            cwd=self.remote,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_pushes_current_branch(self) -> None:
        self.call("write_note", path="note.md", content="a\n")
        self.call("git_commit", message="feat: add note", paths=["note.md"])
        payload = self.structured("git_push", set_upstream=True)
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(self._remote_log(), "feat: add note")

    def test_reports_error_for_unknown_remote(self) -> None:
        result = self.call("git_push", remote="nope")
        self.assertTrue(result.get("isError"))
        self.assertNotEqual(result["structuredContent"]["exit_code"], 0)

    def test_rejects_option_like_remote_or_branch(self) -> None:
        with self.assertRaises(ValueError):
            self.call("git_push", remote="--force")
        with self.assertRaises(ValueError):
            self.call("git_push", branch="--delete")


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves a fixture directory without logging to stderr."""

    def log_message(self, *args) -> None:  # noqa: D102 - silence the test server
        pass


class TestCaptureRaw(ToolTestCase):
    """capture_raw preserves source bytes verbatim, local or downloaded."""

    PDF_BYTES = b"%PDF-1.7\n\x00\x01\x02binary\xff\xfe payload\n%%EOF\n"

    def setUp(self) -> None:
        super().setUp()
        self.fixtures = Path(self._tmp.name) / "fixtures"
        self.fixtures.mkdir()
        self.pdf = self.fixtures / "paper.pdf"
        self.pdf.write_bytes(self.PDF_BYTES)

        self.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            lambda *a, **kw: _QuietHandler(*a, directory=str(self.fixtures), **kw),
        )
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        super().tearDown()

    def test_copies_a_local_binary_verbatim(self) -> None:
        payload = self.structured(
            "capture_raw",
            path="03_resources/demo/raw/paper.pdf",
            source_path=str(self.pdf),
        )
        target = self.root / "03_resources/demo/raw/paper.pdf"
        self.assertEqual(target.read_bytes(), self.PDF_BYTES)
        self.assertEqual(payload["bytes"], len(self.PDF_BYTES))
        self.assertEqual(
            payload["sha256"], hashlib.sha256(self.PDF_BYTES).hexdigest()
        )
        self.assertEqual(payload["source"], str(self.pdf))
        self.assertTrue(payload["created"])

    def test_downloads_a_binary_verbatim(self) -> None:
        payload = self.structured(
            "capture_raw",
            path="03_resources/demo/raw/paper.pdf",
            url=f"{self.base_url}/paper.pdf",
        )
        target = self.root / "03_resources/demo/raw/paper.pdf"
        self.assertEqual(target.read_bytes(), self.PDF_BYTES)
        self.assertEqual(
            payload["sha256"], hashlib.sha256(self.PDF_BYTES).hexdigest()
        )

    def test_refuses_to_overwrite_by_default(self) -> None:
        self.call("capture_raw", path="raw/paper.pdf", source_path=str(self.pdf))
        other = self.fixtures / "other.pdf"
        other.write_bytes(b"different")
        with self.assertRaises(FileExistsError):
            self.call("capture_raw", path="raw/paper.pdf", source_path=str(other))
        self.assertEqual(
            (self.root / "raw/paper.pdf").read_bytes(), self.PDF_BYTES
        )

    def test_overwrites_when_asked(self) -> None:
        self.call("capture_raw", path="raw/paper.pdf", source_path=str(self.pdf))
        other = self.fixtures / "other.pdf"
        other.write_bytes(b"different")
        payload = self.structured(
            "capture_raw",
            path="raw/paper.pdf",
            source_path=str(other),
            overwrite=True,
        )
        self.assertFalse(payload["created"])
        self.assertEqual((self.root / "raw/paper.pdf").read_bytes(), b"different")

    def test_requires_exactly_one_source(self) -> None:
        with self.assertRaises(ValueError):
            self.call("capture_raw", path="raw/x.pdf")
        with self.assertRaises(ValueError):
            self.call(
                "capture_raw",
                path="raw/x.pdf",
                url=f"{self.base_url}/paper.pdf",
                source_path=str(self.pdf),
            )
        self.assertFalse((self.root / "raw/x.pdf").exists())

    def test_rejects_destination_outside_the_vault(self) -> None:
        with self.assertRaises(ValueError):
            self.call(
                "capture_raw", path="../escape.pdf", source_path=str(self.pdf)
            )
        self.assertFalse((self.root.parent / "escape.pdf").exists())

    def test_rejects_non_http_url_scheme(self) -> None:
        for bad in [f"file://{self.pdf}", "ftp://example.com/x.pdf", "data:,x"]:
            with self.assertRaises(ValueError):
                self.call("capture_raw", path="raw/x.pdf", url=bad)

    def test_errors_when_local_source_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.call(
                "capture_raw",
                path="raw/x.pdf",
                source_path=str(self.fixtures / "ghost.pdf"),
            )

    def test_errors_when_local_source_is_a_directory(self) -> None:
        with self.assertRaises(ValueError):
            self.call("capture_raw", path="raw/x.pdf", source_path=str(self.fixtures))

    def test_download_failure_leaves_no_partial_file(self) -> None:
        result = self.call(
            "capture_raw", path="raw/x.pdf", url=f"{self.base_url}/missing.pdf"
        )
        self.assertTrue(result.get("isError"))
        self.assertFalse((self.root / "raw/x.pdf").exists())

    def test_enforces_the_size_limit(self) -> None:
        with self.assertRaises(ValueError):
            self.call(
                "capture_raw",
                path="raw/x.pdf",
                source_path=str(self.pdf),
                max_bytes=4,
            )
        self.assertFalse((self.root / "raw/x.pdf").exists())

    def test_captured_binary_is_committable(self) -> None:
        self.call(
            "capture_raw",
            path="03_resources/demo/raw/paper.pdf",
            source_path=str(self.pdf),
        )
        payload = self.structured(
            "git_commit",
            message="feat: ingest demo pdf",
            paths=["03_resources/demo/raw/paper.pdf"],
        )
        self.assertEqual(payload["exit_code"], 0)


class TestReadNoteBinary(ToolTestCase):
    """read_note must say what to do instead of choking on binary bytes."""

    def test_reports_binary_notes_instead_of_failing_to_decode(self) -> None:
        target = self.root / "03_resources/demo/raw/paper.pdf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"%PDF-1.7\n\x00\x01\xff binary")
        result = self.call("read_note", path="03_resources/demo/raw/paper.pdf")
        payload = result["structuredContent"]
        self.assertTrue(payload["binary"])
        self.assertNotIn("content", payload)
        self.assertIn("sha256", payload)
        self.assertIn(str(self.root / "03_resources/demo/raw/paper.pdf"), payload["hint"])


if __name__ == "__main__":
    unittest.main()


class TestGraphSummary(ToolTestCase):
    """graph_summary is the agent's vocabulary lookup, not a stats dump.

    Tags are the vault's only high-cardinality facet and the `tag` filter of
    graph_search_nodes matches them verbatim, so the summary has to name them.
    """

    def write_graph(self, nodes: list) -> None:
        self.state.graph_path.parent.mkdir(parents=True, exist_ok=True)
        self.state.graph_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "2026-09-14T00:00:00Z",
                    "nodes": nodes,
                    "edges": [],
                }
            ),
            encoding="utf-8",
        )

    def node(self, node_id: str, **fields) -> dict:
        base = {
            "id": node_id,
            "title": node_id,
            "path": f"03_resources/{node_id}.md",
            "domain": "",
            "type": "resource",
            "status": "active",
            "tags": [],
            "inbound_count": 0,
        }
        base.update(fields)
        return base

    def test_counts_tags_and_orders_them_by_frequency(self) -> None:
        self.write_graph(
            [
                self.node("a", tags=["kcp", "flux"]),
                self.node("b", tags=["kcp"]),
                self.node("c", tags=["kcp", "helm"]),
            ]
        )
        payload = self.structured("graph_summary")
        self.assertEqual(
            payload["by_tag"],
            [
                {"tag": "kcp", "count": 3},
                {"tag": "flux", "count": 1},
                {"tag": "helm", "count": 1},
            ],
        )

    def test_reports_the_distinct_tag_total_even_when_truncated(self) -> None:
        self.write_graph(
            [self.node(f"n{i}", tags=[f"tag-{i}"]) for i in range(10)]
        )
        payload = self.structured("graph_summary", topTags=3)
        self.assertEqual(len(payload["by_tag"]), 3)
        self.assertEqual(payload["tag_count"], 10)

    def test_drops_the_type_and_status_facets(self) -> None:
        self.write_graph([self.node("a"), self.node("b", status="deprecated")])
        payload = self.structured("graph_summary")
        self.assertNotIn("by_type", payload)
        self.assertNotIn("by_status", payload)

    def test_counts_notes_per_domain_and_keeps_most_linked_notes(self) -> None:
        self.write_graph(
            [
                self.node("hub", inbound_count=9),
                self.node("a", domain="billing", inbound_count=1),
                self.node("b", domain="billing"),
                self.node("c", domain="identity"),
            ]
        )
        payload = self.structured("graph_summary", topLinked=1)
        self.assertEqual(payload["by_domain"], {"billing": 2, "identity": 1})
        self.assertNotIn("by_repo", payload)
        self.assertEqual([n["id"] for n in payload["top_linked"]], ["hub"])
        self.assertEqual(payload["node_count"], 4)

    def test_search_filters_by_domain(self) -> None:
        self.write_graph(
            [
                self.node("a", domain="billing", type="rule"),
                self.node("b", domain="identity", type="rule"),
                self.node("c"),
            ]
        )
        payload = self.structured("graph_search_nodes", domain="billing")
        self.assertEqual([n["id"] for n in payload["items"]], ["a"])

    def test_search_advertises_domain_not_repo(self) -> None:
        tool = next(
            t for t in mcp._tool_definitions() if t["name"] == "graph_search_nodes"
        )
        self.assertIn("domain", tool["inputSchema"]["properties"])
        self.assertNotIn("repo", tool["inputSchema"]["properties"])

    def test_advertises_the_top_tags_argument(self) -> None:
        tool = next(
            t for t in mcp._tool_definitions() if t["name"] == "graph_summary"
        )
        self.assertIn("topTags", tool["inputSchema"]["properties"])
