#!/usr/bin/env python3
"""Build `index/graph.json` from the vault's Markdown, and validate it.

The vault models three kinds of knowledge, each in its own folder, plus an
archive for retired notes:

  01_domains/<domain>/         a working domain (index.md), its feature
                               descriptions (features/) and rules (rules/)
  02_repositories/<repo>/      where a repository lives and what is where in it
  03_resources/<slug>/         static or online material that gives domains
                               context; originals kept untouched in raw/
  04_archive/                  retired notes of any kind, moved here whole;
                               they keep their declared `type` and their id

The graph is the derived navigation layer agents query instead of walking the
tree: one node per note (frontmatter, kind, domain, link counts) and one edge
per typed markdown link.  `--validate` is the gate that keeps it trustworthy -
it fails on links that resolve to nothing, on edge relationship types or note
`type` values outside their controlled vocabularies, on a note whose `type`
contradicts its folder, on `implemented-in` / `context` edges that do not reach
a repository / resource or give no reason, and on legacy `[[wiki links]]`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


# Obsidian-style wiki link: [[target#anchor|alias]]
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
# Standard markdown link: [display](target); (?<!!) excludes ![img](...)
MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
# Trailing "— gloss" (em-dash / en-dash / hyphen) used as an annotation fallback
GLOSS_RE = re.compile(r"^\s*[—–-]\s+(\S.*)$")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
# Markdown targets that are external (not vault edges, not unresolved-link errors)
EXTERNAL_TARGET_RE = re.compile(r"^(?:[a-z][a-z0-9+.\-]*://|mailto:|tel:|#)", re.IGNORECASE)

# Strict controlled vocabulary for edge relationship types. A link with no brace
# (or no "type") defaults to "related"; --validate fails on any type not in this set.
RELATION_TYPES = {
    "related",
    "supersedes",
    "superseded-by",
    "depends-on",
    "part-of",
    "parent",
    "derived-from",
    "see-also",
    "source",
    "implemented-in",
    "context",
}

# Edges that join the three kinds of knowledge. Each must reach a note of the
# given type and carry a `link-info` saying why the link exists.
MODEL_EDGE_TARGETS = {
    "implemented-in": "repository",
    "context": "resource",
}


# Strict controlled vocabulary for a note's `type`. A note without one takes the
# kind its folder implies (see expected_type), or "meta" at the vault root;
# --validate fails on any value outside this set.
NOTE_TYPES = {
    "hub",
    "meta",
    "domain",
    "feature",
    "rule",
    "repository",
    "resource",
}

# Folders that hold notes. Everything else (agents/, skills/, tests/, ...) is
# tooling and stays out of the graph; root-level *.md files count as notes when
# they carry frontmatter. The archive keeps retired notes in the graph so links
# to them still resolve; an archived note keeps the `type` it declares.
DOMAINS_DIR = "01_domains"
REPOSITORIES_DIR = "02_repositories"
RESOURCES_DIR = "03_resources"
ARCHIVE_DIR = "04_archive"
CONTENT_DIRS = (DOMAINS_DIR, REPOSITORIES_DIR, RESOURCES_DIR, ARCHIVE_DIR)
ROOT_TYPE = "meta"


@dataclass
class LinkRef:
    target: str  # raw target text (resolution key: id / rel-path / title / stem, or a URL)
    anchor: str  # display / alias text -> edge anchor_text
    kind: str  # "wiki_link" | "markdown_link"
    rel_type: str  # semantic relationship type (default "related")
    annotation: str  # per-edge "what to expect there" note
    lineno: int  # 1-based line number in the note body
    raw: str  # the raw link text as written (for the inventory script)
    is_external: bool  # markdown link whose target is a URL/anchor -> no edge


@dataclass
class Note:
    path: Path
    rel_path: str
    stem: str
    meta: Dict[str, object]
    title: str
    note_id: str
    links: List[LinkRef]


@dataclass(frozen=True)
class UnresolvedLink:
    from_id: str
    from_path: str
    target: str


@dataclass(frozen=True)
class WikiLinkUse:
    from_id: str
    from_path: str
    target: str
    lineno: int
    raw: str


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    fm_block = text[4:end]
    body = text[end + 5 :]
    meta: Dict[str, object] = {}

    for raw in fm_block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                meta[key] = [v.strip().strip('"').strip("'") for v in inner.split(",")]
            else:
                meta[key] = []
        else:
            meta[key] = value.strip('"').strip("'")

    return meta, body


def derive_title(meta: Dict[str, object], body: str, stem: str) -> str:
    if isinstance(meta.get("title"), str) and meta["title"].strip():
        return str(meta["title"]).strip()
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return stem.replace("-", " ").strip().title()


def expected_type(rel_path: str) -> str | None:
    """The note type a vault-relative path implies, or None at the vault root."""
    parts = Path(rel_path).parts
    if len(parts) < 2 or parts[0] not in CONTENT_DIRS:
        return None
    if len(parts) == 2:
        return "hub"
    if parts[0] == ARCHIVE_DIR:
        return None
    if parts[0] == REPOSITORIES_DIR:
        return "repository"
    if parts[0] == RESOURCES_DIR:
        return "resource"
    if len(parts) >= 4 and parts[2] == "features":
        return "feature"
    if len(parts) >= 4 and parts[2] == "rules":
        return "rule"
    return "domain"


def domain_of(rel_path: str) -> str:
    """The domain a note belongs to (its folder under 01_domains/), else ""."""
    parts = Path(rel_path).parts
    if len(parts) >= 3 and parts[0] == DOMAINS_DIR:
        return parts[1]
    return ""


def mask_code(body: str) -> str:
    """Blank out code so links inside code samples are ignored, preserving line
    boundaries so line-based parsing (gloss fallback, line numbers) stays aligned."""
    body = FENCED_CODE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), body)
    body = INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), body)
    return body


def scan_brace(text: str, start: int) -> Tuple[object, int]:
    """Given text[start] == '{', scan to the matching '}' respecting JSON string
    quoting, and json.loads the block. Returns (obj_or_None, end_index_after_brace).
    On an unterminated or malformed brace, returns (None, start) so the caller
    treats it as no brace."""
    depth = 0
    in_str = False
    esc = False
    i = start
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                raw = text[start : i + 1]
                try:
                    return json.loads(raw), i + 1
                except (json.JSONDecodeError, ValueError):
                    return None, start
        i += 1
    return None, start


def clean_md_target(raw: str) -> str:
    """Normalize a markdown link target: drop a trailing ``"title"`` and <> wrappers."""
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        raw = raw[1:-1].strip()
    # `[text](target "title")` -> target
    for sep in (' "', " '"):
        if sep in raw:
            raw = raw.split(sep, 1)[0].strip()
    return raw


def parse_links(body: str) -> List[LinkRef]:
    masked = mask_code(body)
    refs: List[LinkRef] = []

    for lineno, line in enumerate(masked.splitlines(), start=1):
        # Collect wiki + markdown link matches on this line, in order.
        raw_matches: List[Tuple[int, int, str, str, str, str]] = []
        for m in WIKI_LINK_RE.finditer(line):
            target = m.group(1).strip()
            alias = (m.group(2) or target).strip()
            if target:
                raw_matches.append(
                    (m.start(), m.end(), "wiki_link", target, alias, m.group(0))
                )
        for m in MD_LINK_RE.finditer(line):
            target = clean_md_target(m.group(2))
            display = m.group(1).strip()
            if target:
                raw_matches.append(
                    (
                        m.start(),
                        m.end(),
                        "markdown_link",
                        target,
                        display or target,
                        m.group(0),
                    )
                )
        raw_matches.sort(key=lambda x: x[0])

        line_refs: List[Tuple[LinkRef, int]] = []  # (ref, end-index-after-brace)
        for start, end, kind, target, anchor, raw in raw_matches:
            rel_type, annotation = "related", ""
            brace_end = end
            if end < len(line) and line[end] == "{":
                obj, be = scan_brace(line, end)
                if isinstance(obj, dict):
                    brace_end = be
                    t = obj.get("type")
                    if isinstance(t, str) and t.strip():
                        rel_type = t.strip()
                    info = obj.get("link-info")
                    if isinstance(info, str) and info.strip():
                        annotation = info.strip()
            is_external = kind == "markdown_link" and bool(
                EXTERNAL_TARGET_RE.match(target)
            )
            ref = LinkRef(
                target=target,
                anchor=anchor,
                kind=kind,
                rel_type=rel_type,
                annotation=annotation,
                lineno=lineno,
                raw=raw,
                is_external=is_external,
            )
            line_refs.append((ref, brace_end))

        # Annotation fallback: a trailing "— gloss" applies only when the link is
        # the sole link on its line (so we don't mis-assign a shared gloss).
        if len(line_refs) == 1:
            ref, brace_end = line_refs[0]
            if not ref.annotation:
                gloss = GLOSS_RE.match(line[brace_end:])
                if gloss:
                    ref.annotation = gloss.group(1).strip()

        refs.extend(ref for ref, _ in line_refs)

    return refs


def norm(s: str) -> str:
    return s.strip().lower()


def build_notes(root: Path) -> List[Note]:
    notes: List[Note] = []
    candidates = list(root.glob("*.md"))
    for folder in CONTENT_DIRS:
        candidates.extend((root / folder).rglob("*.md"))
    for p in sorted(candidates):
        rel = p.relative_to(root)
        # `raw/` holds untouched ingested originals (external READMEs, specs, …),
        # not vault notes — skip them so their file-relative markdown links are not
        # treated as (broken) graph edges.
        if "raw" in rel.parts:
            continue

        text = p.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        # Root-level files are notes only when they say so with frontmatter;
        # AGENTS.md, CLAUDE.md and similar agent instructions stay out.
        if len(rel.parts) == 1 and not meta:
            continue
        title = derive_title(meta, body, p.stem)
        note_id = str(meta.get("id") or rel.with_suffix("")).strip()
        links = parse_links(body)
        # parse_links numbers lines within `body`; shift to absolute file line
        # numbers by the number of lines the frontmatter block occupied.
        line_offset = text.count("\n", 0, len(text) - len(body))
        if line_offset:
            for ref in links:
                ref.lineno += line_offset

        notes.append(
            Note(
                path=p,
                rel_path=rel.as_posix(),
                stem=p.stem,
                meta=meta,
                title=title,
                note_id=note_id,
                links=links,
            )
        )
    return notes


def build_alias_map(notes: List[Note]) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    stem_buckets: Dict[str, List[str]] = defaultdict(list)

    for n in notes:
        stem_buckets[norm(n.stem)].append(n.note_id)

    for n in notes:
        alias_map[norm(n.note_id)] = n.note_id
        alias_map[norm(n.rel_path)] = n.note_id
        alias_map[norm(Path(n.rel_path).with_suffix("").as_posix())] = n.note_id
        alias_map[norm(n.title)] = n.note_id

    for stem, ids in stem_buckets.items():
        if len(ids) == 1:
            alias_map[stem] = ids[0]

    return alias_map


def generate_graph(
    root: Path, existing_generated_at: str = ""
) -> Tuple[Dict[str, object], List[UnresolvedLink], List[WikiLinkUse]]:
    notes = build_notes(root)
    alias_map = build_alias_map(notes)

    edges_set = set()
    outbound: Dict[str, List[str]] = defaultdict(list)
    inbound_count: Dict[str, int] = defaultdict(int)
    unresolved_set = set()
    wiki_uses_set = set()

    for n in notes:
        for ref in n.links:
            # Legacy [[wiki links]] are still parsed (so we can flag them) but are
            # no longer an accepted link form — --validate rejects any that remain.
            if ref.kind == "wiki_link":
                wiki_uses_set.add(
                    WikiLinkUse(
                        from_id=n.note_id,
                        from_path=n.rel_path,
                        target=ref.target,
                        lineno=ref.lineno,
                        raw=ref.raw,
                    )
                )
            if ref.is_external:
                continue
            target = alias_map.get(norm(ref.target))
            if not target:
                unresolved_set.add(
                    UnresolvedLink(
                        from_id=n.note_id,
                        from_path=n.rel_path,
                        target=ref.target,
                    )
                )
                continue
            edge = (n.note_id, target, ref.kind, ref.rel_type, ref.annotation, ref.anchor)
            if edge in edges_set:
                continue
            edges_set.add(edge)
            outbound[n.note_id].append(target)
            inbound_count[target] += 1

    nodes = []
    for n in sorted(notes, key=lambda x: x.note_id):
        tags = n.meta.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        nodes.append(
            {
                "id": n.note_id,
                "title": n.title,
                "path": n.rel_path,
                "domain": domain_of(n.rel_path),
                "type": n.meta.get("type") or expected_type(n.rel_path) or ROOT_TYPE,
                "status": n.meta.get("status", "active"),
                "tags": tags,
                "last_reviewed": n.meta.get("last_reviewed", ""),
                "outbound_links": sorted(set(outbound.get(n.note_id, []))),
                "inbound_count": inbound_count.get(n.note_id, 0),
            }
        )

    edges = [
        {
            "from": src,
            "to": dst,
            "kind": kind,
            "type": rel_type,
            "anchor_text": anchor,
            "annotation": annotation,
            "weight": 1.0,
        }
        for src, dst, kind, rel_type, annotation, anchor in sorted(edges_set)
    ]

    graph = {
        "version": 1,
        "generated_at": existing_generated_at
        if existing_generated_at
        else datetime.now(timezone.utc).isoformat(),
        "nodes": nodes,
        "edges": edges,
    }
    unresolved = sorted(unresolved_set, key=lambda x: (x.from_path, x.target))
    wiki_uses = sorted(wiki_uses_set, key=lambda x: (x.from_path, x.lineno, x.raw))
    return graph, unresolved, wiki_uses


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate the vault graph JSON"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate the graph: unresolved targets, edge relationship types, "
        "note types, notes outside their folder's kind, malformed "
        "implemented-in/context edges, and legacy [[wiki links]] (all rejected)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write index/graph.json (default unless --validate is used alone)",
    )
    return parser.parse_args()


def print_unresolved(unresolved: List[UnresolvedLink]) -> None:
    if not unresolved:
        print("Validation passed: no unresolved links")
        return

    print(f"Validation failed: {len(unresolved)} unresolved link(s)")
    for link in unresolved:
        print(f"- {link.from_path}: [[{link.target}]]")


def print_wiki_links(wiki_uses: List[WikiLinkUse]) -> None:
    if not wiki_uses:
        print("Validation passed: no legacy [[wiki links]]")
        return

    print(f"Validation failed: {len(wiki_uses)} legacy [[wiki link(s)]]")
    print("  use typed markdown links; find/convert them with scripts/list-wiki-links.py")
    for w in wiki_uses:
        print(f"- {w.from_path}:{w.lineno}: {w.raw}")


def find_invalid_types(graph: Dict[str, object]) -> List[Dict[str, object]]:
    return [
        e
        for e in graph.get("edges", [])  # type: ignore[union-attr]
        if e.get("type") not in RELATION_TYPES
    ]


def print_invalid_types(invalid: List[Dict[str, object]]) -> None:
    if not invalid:
        print("Validation passed: all edge types are in the controlled vocabulary")
        return

    print(f"Validation failed: {len(invalid)} edge(s) with unknown relationship type")
    print(f"  allowed: {', '.join(sorted(RELATION_TYPES))}")
    for e in invalid:
        print(f"- {e.get('from')} -> {e.get('to')}: type={e.get('type')!r}")


def find_invalid_node_types(graph: Dict[str, object]) -> List[Dict[str, object]]:
    return [
        n
        for n in graph.get("nodes", [])  # type: ignore[union-attr]
        if n.get("type") not in NOTE_TYPES
    ]


def find_misplaced_notes(graph: Dict[str, object]) -> List[Dict[str, object]]:
    """Notes whose `type` contradicts the kind their folder implies."""
    misplaced = []
    for n in graph.get("nodes", []):  # type: ignore[union-attr]
        expected = expected_type(str(n.get("path", "")))
        if expected and n.get("type") != expected:
            misplaced.append(n)
    return misplaced


def print_misplaced_notes(misplaced: List[Dict[str, object]]) -> None:
    if not misplaced:
        print("Validation passed: every note's type matches its folder")
        return

    print(f"Validation failed: {len(misplaced)} note(s) whose type contradicts its folder")
    for n in misplaced:
        print(
            f"- {n.get('path')}: type={n.get('type')!r}, "
            f"folder implies {expected_type(str(n.get('path')))!r}"
        )


def find_invalid_edges(graph: Dict[str, object]) -> List[str]:
    """Model edges (implemented-in, context) that reach the wrong kind of note
    or give no reason; one human-readable problem per offending edge."""
    types = {n.get("id"): n.get("type") for n in graph.get("nodes", [])}  # type: ignore[union-attr]
    problems: List[str] = []
    for e in graph.get("edges", []):  # type: ignore[union-attr]
        rel = e.get("type")
        wanted = MODEL_EDGE_TARGETS.get(rel)
        if not wanted:
            continue
        where = f"{e.get('from')} -> {e.get('to')} ({rel})"
        if types.get(e.get("to")) != wanted:
            problems.append(f"{where}: target must be a {wanted} note")
        elif not str(e.get("annotation") or "").strip():
            problems.append(f"{where}: needs a link-info saying why")
    return problems


def print_invalid_edges(problems: List[str]) -> None:
    if not problems:
        print("Validation passed: implemented-in and context edges are well formed")
        return

    print(f"Validation failed: {len(problems)} malformed implemented-in/context edge(s)")
    for p in problems:
        print(f"- {p}")


def print_invalid_node_types(invalid: List[Dict[str, object]]) -> None:
    if not invalid:
        print("Validation passed: all node types are in the controlled vocabulary")
        return

    print(f"Validation failed: {len(invalid)} note(s) with unknown type")
    print(f"  allowed: {', '.join(sorted(NOTE_TYPES))}")
    for n in invalid:
        print(f"- {n.get('id')} ({n.get('path')}): type={n.get('type')!r}")


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "index" / "graph.json"
    should_write = args.write or not args.validate

    if should_write:
        output.parent.mkdir(parents=True, exist_ok=True)

    existing_generated_at = ""
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
            existing_nodes = existing.get("nodes", [])
            existing_edges = existing.get("edges", [])
            candidate_graph, unresolved, wiki_uses = generate_graph(root)
            if (
                candidate_graph["nodes"] == existing_nodes
                and candidate_graph["edges"] == existing_edges
            ):
                existing_generated_at = str(existing.get("generated_at", ""))
            graph, unresolved, wiki_uses = generate_graph(
                root, existing_generated_at=existing_generated_at
            )
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            graph, unresolved, wiki_uses = generate_graph(root)
    else:
        graph, unresolved, wiki_uses = generate_graph(root)

    if should_write:
        output.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {output}")

    if args.validate:
        print_unresolved(unresolved)
        invalid = find_invalid_types(graph)
        print_invalid_types(invalid)
        invalid_nodes = find_invalid_node_types(graph)
        print_invalid_node_types(invalid_nodes)
        misplaced = find_misplaced_notes(graph)
        print_misplaced_notes(misplaced)
        bad_edges = find_invalid_edges(graph)
        print_invalid_edges(bad_edges)
        print_wiki_links(wiki_uses)
        if unresolved or invalid or invalid_nodes or misplaced or bad_edges or wiki_uses:
            sys.exit(1)


if __name__ == "__main__":
    main()
