---
name: knowledge-base-document-repository
description: Document a code repository in the knowledge-base vault (repositories/<repo>/index.md) - where it lives (remote URL, default branch, local checkout), what it is for, its layout and where to find what, how to build/test/run it - and link the domains, features and rules it implements with `implemented-in`. Use when the user says "document this repo", "add repo X to the knowledge base", or when a domain note needs an implementation link to a repository the vault does not know yet.
---

# Document a Repository

A repository note answers: **where is the code, and where in it is what?** Domain,
feature and rule notes point here with `implemented-in` links whose `link-info`
names the part of the repository; this note gives the map that makes those
pointers usable.

Obey `AGENTS.md` (read it if not loaded this session). Write only what you
verified in the repository or what the user told you.

```
repositories/<repo>/index.md     id: repository/<repo>   (type: repository)
```

Extra notes for a large repository (e.g. `repositories/<repo>/layout.md`) are
allowed; they are `type: repository` too and link to `index.md` with `part-of`.

## 1. Check the vault

```bash
jq -r '.nodes[] | select(.type=="repository") | "\(.id)\t\(.path)"' index/graph.json
```

Or `graph_search_nodes(type="repository")` on the `knowledge-database` MCP
server. If the repository exists, update its note in place.

## 2. Inspect the repository

Work from a local checkout or the remote. Collect:

- **Location** - remote URL (`git remote get-url origin`), default branch,
  hosting (GitHub, GitLab, Gitea, ...).
- **Purpose** - from its README / docs, in 1-3 sentences.
- **Tech** - languages, frameworks, build tool (from manifests: `go.mod`,
  `package.json`, `pyproject.toml`, `Cargo.toml`, `pom.xml`, ...).
- **Layout** - top-level folders and what lives in each; entry points; where
  APIs, data models, config, migrations, tests and deployment manifests are.
- **Commands** - build, test, lint, run (from Makefile, scripts, CI config).
- **Dependencies on other repositories** - libraries, services, shared charts.

Do not copy code or secrets into the note.

## 3. Find the domains it implements

```bash
jq -r '.nodes[] | select(.type=="domain" or .type=="feature" or .type=="rule")
  | "\(.type)\t\(.id)\t\(.title)"' index/graph.json
```

Match the repository's modules to domains, features and rules. For each match,
note the part of the repository that implements it - that becomes the
`implemented-in` link-info on the domain side.

## 4. Write `repositories/<repo>/index.md`

```md
---
id: repository/<repo>
title: <repo>
status: active            # deprecated when the repo is archived
tags: [<language>, <framework>, <extra-tags...>]
last_reviewed: <today, YYYY-MM-DD>
---

# <repo>

## Location
- Remote: <https://host/org/repo>
- Default branch: <main>
- Hosting: <GitHub | GitLab | Gitea | ...>

## Purpose
<What the repository is for, 1-3 sentences.>

## Tech
<languages, frameworks, build tool>

## Where to find what
| Path            | Contains                                  |
|-----------------|-------------------------------------------|
| `cmd/server/`   | entry point of the API server             |
| `internal/...`  | ...                                       |

## Commands
- Build: `<command>`
- Test: `<command>`
- Run: `<command>`

## Implements
- [<Domain / feature / rule>](<note-id>) - <which part of this repo>

## Depends on
- [<other repo>](repository/<other>){"type":"depends-on","link-info":"<what it uses>"}
```

`## Implements` mirrors the `implemented-in` links of step 5, so the map is
readable from both ends. Write `None yet.` if no domain note exists. Do not
leave a section empty; write `None.` if it truly has nothing.

List the repository in `repositories/index.md` under `## Repositories`
(replace the `// no document, yet` line if present):
`- [<repo>](repository/<repo>){"type":"related","link-info":"<purpose in one line>"}`

## 5. Link the domain side

In each domain, feature or rule note from step 3, add under `## Implementation`
(features, domains) or `## Enforced in` (rules), creating the section if absent:

```md
- [<repo>](repository/<repo>){"type":"implemented-in","link-info":"<path / package / entry point>"}
```

The `link-info` is required; `make graph` fails without it. Use individual
edits; change nothing else in those notes.

## 6. Regenerate and validate

```bash
make graph
```

Fix every reported problem and re-run until clean.

## 7. Stage (do not commit unless asked)

Stage each touched path individually - never `git add -A` / `git add .`:

```bash
git add repositories/<repo>/
git add repositories/index.md
git add <each-domain-note-you-linked>.md
git add index/graph.json
```

## 8. Report

Summarize: the repository note path, location facts, the domain notes linked
with `implemented-in` (and their link-info), facts you could not verify, and
the graph-validation result.
