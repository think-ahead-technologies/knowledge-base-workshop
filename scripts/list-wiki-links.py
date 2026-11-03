#!/usr/bin/env python3
"""List remaining [[wiki links]] so they can be converted to markdown links by hand.

Legacy `[[wiki links]]` are no longer accepted — `generate-graph.py --validate`
(run by the pre-commit hook) fails on any that remain. This tool locates the
offenders so you can fix them.

Read-only: this script never edits notes. It reports every `[[wiki link]]` still in
the vault (skipping code samples) with its file, line, resolved target, and the full
line as context, plus a suggested markdown conversion. Convert each link yourself,
adding the right `type` and `link-info`, e.g.:

    [[resource/old-deadlines]]  ->  [old deadline table](resource/old-deadlines){"type":"supersedes","link-info":"the table this replaces"}

The relationship `type` must be one of the controlled vocabulary in generate-graph.py
(RELATION_TYPES); the pre-commit hook rejects unknown types.
"""
import argparse
import importlib.util
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

# Reuse the parser/resolver from generate-graph.py (hyphenated name -> load by path).
_GG_PATH = Path(__file__).resolve().with_name("generate-graph.py")
_spec = importlib.util.spec_from_file_location("generate_graph", _GG_PATH)
gg = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(gg)


def collect(root: Path):
    notes = gg.build_notes(root)
    alias_map = gg.build_alias_map(notes)
    title_by_id = {n.note_id: n.title for n in notes}
    line_cache: Dict[str, List[str]] = {}

    rows = []
    for n in sorted(notes, key=lambda x: x.rel_path):
        wiki = [ref for ref in n.links if ref.kind == "wiki_link"]
        if not wiki:
            continue
        lines = line_cache.setdefault(
            n.rel_path, n.path.read_text(encoding="utf-8").splitlines()
        )
        for ref in wiki:
            resolved = alias_map.get(gg.norm(ref.target))
            title = title_by_id.get(resolved, "") if resolved else ""
            context = lines[ref.lineno - 1].strip() if ref.lineno - 1 < len(lines) else ""
            display = title or (resolved or ref.target)
            suggestion = f'[{display}]({resolved or ref.target})' + (
                '{"type":"related","link-info":"…"}'
            )
            rows.append(
                {
                    "path": n.rel_path,
                    "line": ref.lineno,
                    "raw": ref.raw,
                    "resolved": resolved or "<unresolved>",
                    "title": title,
                    "context": context,
                    "suggestion": suggestion,
                }
            )
    return rows


def print_grouped(rows) -> None:
    by_file: Dict[str, list] = defaultdict(list)
    for r in rows:
        by_file[r["path"]].append(r)

    for path in sorted(by_file):
        items = by_file[path]
        print(f"\n{path}  ({len(items)})")
        for r in items:
            print(f"  L{r['line']}: {r['raw']}  ->  {r['resolved']}")
            if r["context"]:
                print(f"      context: {r['context']}")
            print(f"      suggest: {r['suggestion']}")

    print("\n" + "=" * 60)
    print(f"{len(rows)} wiki link(s) remaining across {len(by_file)} file(s)")
    if not rows:
        print("All links migrated to markdown form. 🎉")


def print_tsv(rows) -> None:
    print("path\tline\traw\tresolved\ttitle\tcontext")
    for r in rows:
        ctx = r["context"].replace("\t", " ")
        print(
            f"{r['path']}\t{r['line']}\t{r['raw']}\t{r['resolved']}\t{r['title']}\t{ctx}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["grouped", "tsv"],
        default="grouped",
        help="output format (default: grouped text)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    rows = collect(root)
    if args.format == "tsv":
        print_tsv(rows)
    else:
        print_grouped(rows)


if __name__ == "__main__":
    main()
