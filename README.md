---
id: knowledge-base/home
title: Knowledge Base
type: hub
status: active
tags: [knowledge-base, agents, docs]
last_reviewed: 2026-11-03
---

# Knowledge Base

A Markdown knowledge graph for engineering agents. It holds three kinds of
knowledge, each in its own folder:

- **Domains** - the working domains: what each domain is, the features it
  provides, and the rules that hold in it.
- **Repositories** - where each code repository lives and where to find what
  inside it. Domains link here to find their implementations.
- **Resources** - static documents and required online material. Resources
  feed the domains with context; every link from a domain says why or in which
  way the resource is needed.

This repository is the empty **framework**: tooling, agents, skills and the
skeleton, with no notes in it. Clone it, run the bootstrap below, and start
writing notes.

## Layout

```
01_domains/<domain>/index.md            the domain (type: domain)
01_domains/<domain>/features/<f>.md     a feature of the domain (type: feature)
01_domains/<domain>/rules/<r>.md        a rule of the domain (type: rule)
02_repositories/<repo>/index.md         a code repository (type: repository)
03_resources/<slug>/index.md            a resource (type: resource)
03_resources/<slug>/<topic>.md          a topic distilled from it (type: resource)
03_resources/<slug>/raw/                untouched original bytes (not in the graph)
04_archive/<...>                        retired notes, moved whole (keep their type and id)
index/          generated graph (index/graph.json)
scripts/        graph generator, link inventory, MCP server, git hook
agents/         subagent definitions, symlinked into .claude/agents/
skills/         skill definitions, symlinked into .claude/skills/
tests/          unit tests for the tooling
```

The folder decides a note's kind. `type` in the frontmatter is optional; when
given it must match the folder, and `make validate-graph` fails otherwise. Only
`01_domains/`, `02_repositories/`, `03_resources/`, `04_archive/` and
root-level `*.md` files are in the graph. Notes in `04_archive/` keep the
`type` they declare.

## How the kinds connect

| From                    | Link type        | To         | `link-info` says                          |
|-------------------------|------------------|------------|-------------------------------------------|
| domain / feature / rule | `implemented-in` | repository | which part of the repo implements it      |
| domain / feature / rule | `context`        | resource   | why or in which way the resource is needed |
| feature / rule          | `part-of`        | domain     | (optional) the role in the domain         |
| resource topic          | `part-of`        | resource   | (optional) where the topic appears        |

`implemented-in` must point at a repository note and `context` at a resource
note, and both must carry a `link-info`. `make validate-graph` enforces this.

## Frontmatter

```yaml
---
id: feature/billing/invoicing     # stable id, the link target
title: Invoicing
type: feature                     # optional; must match the folder
status: active                    # active | draft | deprecated
tags: [billing, invoices]
last_reviewed: 2026-11-03
---
```

Id conventions: `domain/<domain>`, `feature/<domain>/<feature>`,
`rule/<domain>/<rule>`, `repository/<repo>`, `resource/<slug>`,
`resource/<slug>/<topic>`. Retired notes stay in place with
`status: deprecated`.

## Bootstrap

```sh
make install-hooks           # pre-commit hook: regenerate + validate the graph
make install-global-claude   # link skills & agents into ~/.claude so any repo can use them
make install-mcp-claude      # register scripts/mcp-server.py as the knowledge-database MCP server
make graph                   # generate index/graph.json and validate it
make test                    # run the tooling tests
```

## Rules
- Markdown is the source of truth; `index/graph.json` is generated (`make graph`).
- Link with typed markdown links: `[text](note-id){"type":"…","link-info":"…"}`.
  Legacy `[[wiki links]]` are rejected by `make validate-graph`.
- Put each note in the folder of its kind.
- Fix broken links - find them with `make graph` or `make validate-graph`.

## Hubs
- [Domains Hub](domain/index){"type":"related","link-info":"Lists the working domains"}
- [Repositories Hub](repository/index){"type":"related","link-info":"Lists the documented repositories"}
- [Resources Hub](resource/index){"type":"related","link-info":"Lists the resources that give domains context"}
- [Agent Query Guide](meta/agent-query-guide){"type":"see-also","link-info":"Graph schema and jq queries for agents"}
