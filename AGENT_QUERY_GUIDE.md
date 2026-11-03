---
id: meta/agent-query-guide
title: Agent Query Guide
type: meta
status: active
tags: [agents, jq, graph]
last_reviewed: 2026-11-03
---

# Agent Query Guide

`index/graph.json` is for navigation. You can query kinds, domains, tags and
links there. Use it!

The vault holds three kinds of knowledge (see `README.md`):

- `domains/<domain>/` - the domain (`index.md`), its `features/` and `rules/`
- `repositories/<repo>/` - where a repository lives and what is where in it
- `resources/<slug>/` - static or online material that gives domains context

## Schema

- Top-level object:
  - `version` (number): schema version
  - `generated_at` (string): ISO-8601 UTC timestamp
  - `nodes` (array): note metadata records
  - `edges` (array): directed link records
- Node object (`nodes[]`):
  - `id` (string): stable note identifier (usually from frontmatter)
  - `title` (string): note title
  - `path` (string): vault-relative markdown path
  - `domain` (string): the folder name under `domains/` for domain, feature and
    rule notes; `""` for every other note
  - `type` (string): the kind of note, from a controlled vocabulary -
    `hub|meta|domain|feature|rule|repository|resource`. The folder implies it
    (`domains/<d>/features/` is `feature`, `domains/<d>/rules/` is `rule`, other
    `domains/<d>/` files are `domain`, `repositories/` is `repository`,
    `resources/` is `resource`, the three folder `index.md` files are `hub`,
    root notes default to `meta`). `--validate` fails on a value outside the
    vocabulary and on a frontmatter `type` that contradicts the folder.
  - `status` (string): lifecycle state (`active`, `draft`, `deprecated`)
  - `tags` (string array): topic tags
  - `last_reviewed` (string): `YYYY-MM-DD`
  - `outbound_links` (string array): linked note IDs from this note
  - `inbound_count` (number): number of edges targeting this note
- Edge object (`edges[]`):
  - `from` (string): source note ID
  - `to` (string): target note ID
  - `kind` (string): link *mechanism* - normally `markdown_link` (legacy
    `wiki_link` is rejected by `--validate` and should not appear in a valid graph)
  - `type` (string): semantic *relationship* (see vocabulary below); default `related`
  - `anchor_text` (string): display / alias text used in the link
  - `annotation` (string): free-text "what the source needs from the destination"
    (from the link's `link-info`, falling back to a trailing `- gloss`); may be empty
  - `weight` (number): link weight, currently `1.0`

## Link syntax

Links are standard **markdown links** whose target is the stable note `id`, with an
optional JSON brace suffix carrying the relationship and annotation:

```md
[billing-api](repository/billing-api){"type":"implemented-in","link-info":"invoice endpoints in internal/invoice/"}
[OAuth 2.0](resource/oauth2-rfc6749){"type":"context","link-info":"token flow the login feature follows"}
```

- A bare `[text](id)` with no brace is a `related` edge.
- `type` must be one of the controlled vocabulary; `generate-graph.py --validate`
  fails on any other value:
  `related, supersedes, superseded-by, depends-on, part-of, parent, derived-from,
  see-also, source, implemented-in, context`.
- `implemented-in` must target a `repository` note and `context` a `resource`
  note, and both must carry a non-empty `link-info` (the why). `--validate`
  fails otherwise.
- Legacy `[[wiki links]]` are **not accepted**: `generate-graph.py --validate`
  fails on any that remain. Locate and convert them with
  `python3 scripts/list-wiki-links.py`.

## Navigating the model

A typical question walks domain -> features/rules -> repositories + resources:

1. Find the domain: `type=="domain"` nodes, or `domain=="<name>"`.
2. Read its features and rules: nodes with that `domain`.
3. Find the implementation: outbound `implemented-in` edges (annotation says
   where in the repo), then read the repository note.
4. Find the context: outbound `context` edges (annotation says why), then read
   the resource note.

Reverse it to answer "which domains does this repository / resource serve?":
inbound `implemented-in` / `context` edges.

## Examples with `jq`

```bash
# list domains
jq -r '.nodes[] | select(.type=="domain" and (.path|endswith("/index.md"))) | "\(.domain)\t\(.id)"' index/graph.json

# every feature and rule of one domain
jq -r '.nodes[] | select(.domain=="billing" and (.type=="feature" or .type=="rule")) | "\(.type)\t\(.id)\t\(.path)"' index/graph.json

# all repositories / all resources
jq -r '.nodes[] | select(.type=="repository") | "\(.id)\t\(.path)"' index/graph.json
jq -r '.nodes[] | select(.type=="resource") | "\(.id)\t\(.path)"' index/graph.json

# where a domain note is implemented, and why
NOTE_ID="domain/billing"
jq -r --arg id "$NOTE_ID" '.edges[] | select(.from==$id and .type=="implemented-in") | "\(.to)\t\(.annotation)"' index/graph.json

# which resources a note needs, and why
jq -r --arg id "$NOTE_ID" '.edges[] | select(.from==$id and .type=="context") | "\(.to)\t\(.annotation)"' index/graph.json

# which domain notes a repository implements
REPO_ID="repository/billing-api"
jq -r --arg id "$REPO_ID" '.edges[] | select(.to==$id and .type=="implemented-in") | "\(.from)\t\(.annotation)"' index/graph.json

# the tag vocabulary, most frequent first (tags are matched verbatim)
jq -r '[.nodes[].tags[]?] | group_by(.) | map({tag: .[0], count: length})
  | sort_by(-.count)[] | "\(.count)\t\(.tag)"' index/graph.json

# top linked notes
jq -r '.nodes | sort_by(-(.inbound_count // 0))[] | "\(.inbound_count // 0)\t\(.id)\t\(.path)"' index/graph.json

# outbound edges of a note WITH relationship type + annotation
jq -r --arg id "$NOTE_ID" '.edges[] | select(.from==$id) | "\(.type)\t\(.to)\t\(.annotation)"' index/graph.json

# incoming links to one note
jq -r --arg id "$NOTE_ID" '.edges[] | select(.to==$id) | "\(.type)\t\(.from)\t\(.annotation)"' index/graph.json

# all edges of a given relationship type (e.g. what supersedes what)
jq -r '.edges[] | select(.type=="supersedes") | "\(.from) -> \(.to)"' index/graph.json
```

For `jg`, use the same filters if your local `jg` is jq-compatible.

## Validation

```bash
# validate: non-zero exit on unresolved links, edge types or note types outside
# their vocabularies, notes whose type contradicts their folder, malformed
# implemented-in/context edges, OR any remaining legacy [[wiki links]]
python3 scripts/generate-graph.py --validate

# regenerate graph and validate
python3 scripts/generate-graph.py && python3 scripts/generate-graph.py --validate

# list any remaining legacy [[wiki links]] (rejected by --validate) to convert
python3 scripts/list-wiki-links.py
```
