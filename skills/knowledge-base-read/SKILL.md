---
name: knowledge-base-read
description: Read and query the knowledge-base vault - a docs-as-code knowledge graph of working domains (features + rules), code repositories, and resources. Use when the user asks what is known about a domain, a feature, a rule, a repository (where is it, where is what in it, which domains it implements), or a resource; wants context before working on a feature or in a repo; or asks to find/navigate notes by domain, kind, tag, or link. Resolves the question against the Markdown notes and the generated graph index.
---

# Read the Knowledge Base

The vault is a docs-as-code knowledge graph with three kinds of knowledge:

- **Domains** - `01_domains/<domain>/index.md` describes the working domain,
  `features/<feature>.md` its features, `rules/<rule>.md` the rules that hold.
- **Repositories** - `02_repositories/<repo>/index.md`: where the repository lives
  and where to find what inside it.
- **Resources** - `03_resources/<slug>/`: static documents and online material that
  give the domains context. Originals stay in `raw/`.

Domains link to repositories with `implemented-in` and to resources with
`context`; each such link carries a `link-info` saying where (in the repo) or
why (the resource is needed). Markdown is the source of truth;
`index/graph.json` is the generated navigation index.

Obey `AGENTS.md` (read it if not loaded this session). This skill is read-only -
do not modify notes.

## Layout

```
01_domains/index.md                     hub: list of domains
01_domains/<domain>/index.md            the domain             (type: domain)
01_domains/<domain>/features/<f>.md     a feature              (type: feature)
01_domains/<domain>/rules/<r>.md        a rule                 (type: rule)
02_repositories/index.md                hub: list of repositories
02_repositories/<repo>/index.md         a repository           (type: repository)
03_resources/index.md                   hub: list of resources
03_resources/<slug>/index.md            a resource             (type: resource)
03_resources/<slug>/<topic>.md          a topic of a resource  (type: resource)
03_resources/<slug>/raw/                untouched originals (not in the graph)
04_archive/index.md                     hub: retired notes
04_archive/<...>                        retired notes, any kind (keep type and id)
index/graph.json                     generated graph (nodes + edges)
README.md                            vault hub; AGENT_QUERY_GUIDE.md: graph schema + queries
```

Every graph node has `id`, `title`, `path`, `type`
(`hub|meta|domain|feature|rule|repository|resource`, implied by the folder),
`domain` (folder name under `01_domains/`, else `""`), `status`
(`active|draft|deprecated`), `tags`, `last_reviewed`. Links are typed markdown
links `[text](note-id){"type":"…","link-info":"…"}` resolved by `id`.

## 1. Orient

- `README.md` - the model and the hubs.
- `01_domains/index.md`, `02_repositories/index.md`, `03_resources/index.md` - what exists.

Classify the question:

| Question is about           | Start at                                    |
|-----------------------------|---------------------------------------------|
| a domain / a feature / a rule | `01_domains/<domain>/index.md`, then its `features/` and `rules/` |
| where code lives / where X is in a repo | `02_repositories/<repo>/index.md`; or the domain note's `implemented-in` links |
| background, specs, standards | `03_resources/<slug>/index.md`; or a domain note's `context` links |

If the domain or repository has no node, say it is not documented yet.

## 2. Query the graph

Use `jq` on `index/graph.json` (more in `AGENT_QUERY_GUIDE.md`), or the
`knowledge-database` MCP server when available (`graph_summary`,
`graph_search_nodes` with `domain` / `type` / `tag` / `query`,
`graph_neighbors`, `read_note`) - it is the same index.

```bash
# domains
jq -r '.nodes[] | select(.type=="domain") | "\(.domain)\t\(.id)\t\(.path)"' index/graph.json

# features and rules of one domain
jq -r '.nodes[] | select(.domain=="billing" and (.type=="feature" or .type=="rule")) | "\(.type)\t\(.id)\t\(.path)"' index/graph.json

# where a note is implemented (annotation = where in the repo)
jq -r --arg id "feature/billing/invoicing" '.edges[] | select(.from==$id and .type=="implemented-in") | "\(.to)\t\(.annotation)"' index/graph.json

# which resources a note needs (annotation = why)
jq -r --arg id "domain/billing" '.edges[] | select(.from==$id and .type=="context") | "\(.to)\t\(.annotation)"' index/graph.json

# which domain notes a repository / resource serves
jq -r --arg id "repository/billing-api" '.edges[] | select(.to==$id) | "\(.type)\t\(.from)\t\(.annotation)"' index/graph.json

# notes carrying a tag
jq -r '.nodes[] | select(.tags[]? == "invoices") | "\(.id)\t\(.path)"' index/graph.json
```

Full-text fallback when you do not know the tag, domain or id:

```bash
grep -rIl "<term>" 01_domains 02_repositories 03_resources 04_archive
```

## 3. Read the notes and follow the links

The graph gives ids and paths; the ANSWER lives in the Markdown. Open the
matched files. Then follow the model edges:

- From a feature or rule, read its domain (`part-of`) so the rule set and
  vocabulary are in view. Read every rule of the domain before advising a change
  to a feature in it.
- Follow `implemented-in` to the repository note; the `link-info` says which
  part of the repository to look at, the repository note says where the
  repository lives and how it is laid out.
- Follow `context` to the resource note when its `link-info` matters for the
  question; open `raw/` only when the distilled notes are not enough.

Track visited ids; stop when notes stop being relevant.

If the graph looks stale or a path is missing, regenerate read-only:
`python3 scripts/generate-graph.py` (does not touch Markdown). Do not commit.

## 4. Answer with citations

- Answer directly from what the notes say.
- Cite the backing notes by vault-relative `path` and/or `id`.
- Name the rules that constrain the answer, and the repository locations
  (from `implemented-in` link-info) where the work happens.
- Distinguish vault facts from inference. If the vault does not cover it, say
  so plainly - do not invent. Flag `status: draft`/`deprecated` notes.
- For "what links to / relates to X" questions, report the edges with their
  relationship `type` and `annotation`.
