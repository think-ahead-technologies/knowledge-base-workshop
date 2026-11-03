#!/usr/bin/env python3
"""Tests for the graph generator and its validation gate.

The vault models three kinds of knowledge: domains (with their features and
rules), repositories, and resources. `--validate` keeps that model honest, so
these tests pin what it enforces: the note `type` vocabulary, the note type a
folder implies, the edge relationship vocabulary, and the typed edges that tie
the kinds together (`implemented-in` to a repository, `context` to a resource,
each with a reason). Each filesystem test builds a throwaway vault, never the
real one.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

gen = importlib.import_module("generate-graph")


def _node(node_id: str, note_type: str, path: str = "") -> dict:
    return {"id": node_id, "path": path or f"{node_id}.md", "type": note_type}


class TestNoteTypeVocabulary(unittest.TestCase):
    """The node `type` enum names the kinds of knowledge the vault holds."""

    def test_is_exactly_the_domain_repository_resource_model(self) -> None:
        self.assertEqual(
            {
                "hub",
                "meta",
                "domain",
                "feature",
                "rule",
                "repository",
                "resource",
            },
            gen.NOTE_TYPES,
        )

    def test_accepts_a_graph_whose_nodes_are_all_in_the_vocabulary(self) -> None:
        graph = {"nodes": [_node("a", "domain"), _node("b", "rule")], "edges": []}
        self.assertEqual(gen.find_invalid_node_types(graph), [])

    def test_reports_a_node_whose_type_is_outside_the_vocabulary(self) -> None:
        graph = {"nodes": [_node("a", "domain"), _node("b", "area")], "edges": []}
        invalid = gen.find_invalid_node_types(graph)
        self.assertEqual([n["id"] for n in invalid], ["b"])


class TestRelationVocabulary(unittest.TestCase):
    def test_includes_the_model_edges(self) -> None:
        self.assertIn("implemented-in", gen.RELATION_TYPES)
        self.assertIn("context", gen.RELATION_TYPES)


class TestExpectedType(unittest.TestCase):
    """A note's folder decides its kind; the frontmatter may only agree."""

    def test_maps_each_location_to_its_kind(self) -> None:
        cases = {
            "01_domains/index.md": "hub",
            "02_repositories/index.md": "hub",
            "03_resources/index.md": "hub",
            "01_domains/billing/index.md": "domain",
            "01_domains/billing/glossary.md": "domain",
            "01_domains/billing/features/invoicing.md": "feature",
            "01_domains/billing/rules/no-negative-totals.md": "rule",
            "02_repositories/billing-api/index.md": "repository",
            "02_repositories/billing-api/layout.md": "repository",
            "03_resources/oauth2-rfc6749/index.md": "resource",
            "03_resources/oauth2-rfc6749/grant-types.md": "resource",
            "04_archive/index.md": "hub",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(gen.expected_type(path), expected)

    def test_root_notes_have_no_implied_kind(self) -> None:
        self.assertIsNone(gen.expected_type("README.md"))

    def test_archived_notes_keep_their_own_kind(self) -> None:
        self.assertIsNone(gen.expected_type("04_archive/old-billing/index.md"))
        self.assertIsNone(gen.expected_type("04_archive/old-billing/rules/r.md"))
        self.assertEqual(gen.domain_of("04_archive/old-billing/index.md"), "")

    def test_derives_the_domain_from_the_path(self) -> None:
        self.assertEqual(gen.domain_of("01_domains/billing/rules/x.md"), "billing")
        self.assertEqual(gen.domain_of("01_domains/billing/index.md"), "billing")
        self.assertEqual(gen.domain_of("01_domains/index.md"), "")
        self.assertEqual(gen.domain_of("02_repositories/billing-api/index.md"), "")


class TestEdgeConstraints(unittest.TestCase):
    """`implemented-in` and `context` are the edges that join the three kinds."""

    def graph(self, edge: dict) -> dict:
        return {
            "nodes": [
                _node("domain/billing", "domain"),
                _node("repository/billing-api", "repository"),
                _node("resource/oauth2", "resource"),
            ],
            "edges": [edge],
        }

    def edge(self, to: str, rel: str, annotation: str = "why") -> dict:
        return {"from": "domain/billing", "to": to, "type": rel, "annotation": annotation}

    def test_accepts_well_formed_model_edges(self) -> None:
        for edge in (
            self.edge("repository/billing-api", "implemented-in"),
            self.edge("resource/oauth2", "context"),
        ):
            with self.subTest(edge=edge):
                self.assertEqual(gen.find_invalid_edges(self.graph(edge)), [])

    def test_rejects_implemented_in_that_does_not_reach_a_repository(self) -> None:
        bad = self.edge("resource/oauth2", "implemented-in")
        problems = gen.find_invalid_edges(self.graph(bad))
        self.assertEqual(len(problems), 1)
        self.assertIn("repository", problems[0])

    def test_rejects_context_that_does_not_reach_a_resource(self) -> None:
        bad = self.edge("repository/billing-api", "context")
        problems = gen.find_invalid_edges(self.graph(bad))
        self.assertEqual(len(problems), 1)
        self.assertIn("resource", problems[0])

    def test_requires_a_reason_on_model_edges(self) -> None:
        for rel, to in (
            ("implemented-in", "repository/billing-api"),
            ("context", "resource/oauth2"),
        ):
            with self.subTest(rel=rel):
                problems = gen.find_invalid_edges(self.graph(self.edge(to, rel, "")))
                self.assertEqual(len(problems), 1)
                self.assertIn("link-info", problems[0])


class VaultTestCase(unittest.TestCase):
    """Base case: a throwaway vault with a copy of the generator."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve() / "vault"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "scripts" / "generate-graph.py").write_text(
            (SCRIPTS / "generate-graph.py").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, frontmatter: str, body: str = "") -> None:
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"---\n{frontmatter}\n---\n\n# t\n{body}\n", encoding="utf-8")

    def run_generator(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "scripts/generate-graph.py", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def graph(self) -> dict:
        proc = self.run_generator()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads((self.root / "index" / "graph.json").read_text(encoding="utf-8"))


class TestGraphNodes(VaultTestCase):
    def test_nodes_carry_the_kind_implied_by_their_folder(self) -> None:
        self.write("01_domains/billing/features/invoicing.md", "id: feature/invoicing")
        node = self.graph()["nodes"][0]
        self.assertEqual(node["type"], "feature")
        self.assertEqual(node["domain"], "billing")
        self.assertNotIn("repo", node)

    def test_scans_the_content_folders_and_root_notes_with_frontmatter(self) -> None:
        self.write("README.md", "id: home\ntype: hub")
        self.write("01_domains/billing/index.md", "id: domain/billing")
        self.write("agents/helper.md", "id: agent")
        self.write("skills/x/SKILL.md", "id: skill")
        self.write("tests/fixture.md", "id: fixture")
        (self.root / "AGENTS.md").write_text("always read the guide\n", encoding="utf-8")
        ids = sorted(n["id"] for n in self.graph()["nodes"])
        self.assertEqual(ids, ["domain/billing", "home"])

    def test_scans_the_archive(self) -> None:
        self.write("04_archive/old-billing/index.md", "id: domain/old-billing\ntype: domain")
        node = self.graph()["nodes"][0]
        self.assertEqual(node["id"], "domain/old-billing")
        self.assertEqual(node["type"], "domain")

    def test_skips_raw_captures(self) -> None:
        self.write("03_resources/paper/index.md", "id: resource/paper")
        self.write("03_resources/paper/raw/page.md", "id: raw-page")
        ids = [n["id"] for n in self.graph()["nodes"]]
        self.assertEqual(ids, ["resource/paper"])


class TestValidateExitCode(VaultTestCase):
    """--validate must fail the run, not just print, on any model violation."""

    def validate(self) -> subprocess.CompletedProcess:
        return self.run_generator("--validate")

    def test_passes_on_a_well_formed_vault(self) -> None:
        self.write(
            "01_domains/billing/index.md",
            "id: domain/billing",
            '[API](repository/billing-api){"type":"implemented-in","link-info":"invoice endpoints"}\n'
            '[RFC](resource/oauth2){"type":"context","link-info":"token flow the API follows"}',
        )
        self.write("02_repositories/billing-api/index.md", "id: repository/billing-api")
        self.write("03_resources/oauth2/index.md", "id: resource/oauth2")
        proc = self.validate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("all node types are in the controlled vocabulary", proc.stdout)

    def test_fails_on_an_unknown_type(self) -> None:
        self.write("README.md", "id: home\ntype: descision")
        proc = self.validate()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("descision", proc.stdout)

    def test_fails_on_a_note_whose_type_contradicts_its_folder(self) -> None:
        self.write("01_domains/billing/rules/r.md", "id: rule/r\ntype: feature")
        proc = self.validate()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("01_domains/billing/rules/r.md", proc.stdout)
        self.assertIn("rule", proc.stdout)

    def test_fails_on_a_context_link_without_a_reason(self) -> None:
        self.write(
            "01_domains/billing/index.md",
            "id: domain/billing",
            '[RFC](resource/oauth2){"type":"context"}',
        )
        self.write("03_resources/oauth2/index.md", "id: resource/oauth2")
        proc = self.validate()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("link-info", proc.stdout)


if __name__ == "__main__":
    unittest.main()
