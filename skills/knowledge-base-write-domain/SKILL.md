---
name: knowledge-base-write-domain
description: Write or update domain knowledge in the knowledge-base vault - a working domain (domains/<domain>/index.md), a feature description inside it (features/<feature>.md), or a rule that holds in it (rules/<rule>.md) - and link it to the repositories that implement it (`implemented-in`) and the resources that give it context (`context`), each with the reason. Use when the user says "document this domain / feature / rule", "add a rule", "record how feature X works", or when new domain knowledge turns up while working.
---

# Write Domain Knowledge

A **domain** is a working area of the business or system (e.g. `billing`,
`identity`). Inside it live its **features** (what the domain provides) and its
**rules** (what must always hold). Domain notes do not hold code locations or
background material themselves - they link to:

- **repositories** with `implemented-in` - `link-info` says which part of the
  repository implements it (path, package, module);
- **resources** with `context` - `link-info` says why or in which way the
  resource is needed.

Obey `AGENTS.md` (read it if not loaded this session). Write only what the
sources (the user, the code, a resource) say - never invent behavior or rules.

```
domains/<domain>/
  index.md              the domain           id: domain/<domain>
  features/<f>.md       a feature            id: feature/<domain>/<f>
  rules/<r>.md          a rule               id: rule/<domain>/<r>
```

The folder implies `type` (`domain`, `feature`, `rule`); you may omit it, and if
you write it, it must match.

## 1. Locate the domain

```bash
jq -r '.nodes[] | select(.type=="domain") | "\(.domain)\t\(.id)\t\(.path)"' index/graph.json
```

Or `graph_search_nodes(type="domain")` on the `knowledge-database` MCP server.

- The domain exists: read its `index.md` and the notes in `features/` and
  `rules/` before writing, so you extend instead of duplicating.
- It does not exist: create it (step 2). Pick a short kebab-case name; check
  with the user if the domain boundary is unclear.

## 2. Domain note - `domains/<domain>/index.md`

```md
---
id: domain/<domain>
title: <Domain Title>
status: active
tags: [<domain>, <extra-tags...>]
last_reviewed: <today, YYYY-MM-DD>
---

# <Domain Title>

## Purpose
<What this domain is responsible for, in 2-4 sentences.>

## Scope
<What belongs to it, and what explicitly does not.>

## Vocabulary
- **<Term>** - <meaning in this domain>

## Features
- [<Feature>](feature/<domain>/<f>){"type":"related","link-info":"<one line>"}

## Rules
- [<Rule>](rule/<domain>/<r>){"type":"related","link-info":"<one line>"}

## Implementation
- [<repo>](repository/<repo>){"type":"implemented-in","link-info":"<which part of the repo>"}

## Context
- [<Resource>](resource/<slug>){"type":"context","link-info":"<why the domain needs it>"}
```

List the new domain in `domains/index.md` under `## Domains` (replace the
`// no document, yet` line if present):
`- [<Domain Title>](domain/<domain>){"type":"related","link-info":"<one line>"}`

## 3. Feature note - `domains/<domain>/features/<f>.md`

```md
---
id: feature/<domain>/<f>
title: <Feature Title>
status: active            # draft while still being designed
tags: [<domain>, <f>]
last_reviewed: <today, YYYY-MM-DD>
---

# <Feature Title>

Part of [<Domain Title>](domain/<domain>){"type":"part-of","link-info":"<role in the domain>"}

## Description
<What the feature does for whom, the main flow, inputs and outputs.>

## Behavior
- <observable behavior, edge cases, failure modes>

## Rules
- [<Rule>](rule/<domain>/<r>){"type":"depends-on","link-info":"<how the rule constrains this feature>"}

## Implementation
- [<repo>](repository/<repo>){"type":"implemented-in","link-info":"<path / package / entry point>"}

## Context
- [<Resource>](resource/<slug>){"type":"context","link-info":"<why the feature needs it>"}
```

Add the feature to the domain note's `## Features`.

## 4. Rule note - `domains/<domain>/rules/<r>.md`

A rule is one statement that must always hold in the domain (an invariant, a
constraint, a policy). One rule per note; name it after what it demands
(`no-negative-invoice-totals`).

```md
---
id: rule/<domain>/<r>
title: <Rule as a short statement>
status: active
tags: [<domain>, rule]
last_reviewed: <today, YYYY-MM-DD>
---

# <Rule as a short statement>

Part of [<Domain Title>](domain/<domain>){"type":"part-of","link-info":"<what the rule protects>"}

## Rule
<The rule, stated precisely. MUST / MUST NOT wording.>

## Why
<The reason: business, legal, technical. Link the source with `context`.>

## Applies to
- [<Feature>](feature/<domain>/<f>){"type":"related","link-info":"<how it applies>"}

## Enforced in
- [<repo>](repository/<repo>){"type":"implemented-in","link-info":"<where the check lives>"}

## Context
- [<Resource>](resource/<slug>){"type":"context","link-info":"<why this rule needs it>"}
```

Add the rule to the domain note's `## Rules`. When a rule replaces another,
link it with `supersedes` and set the old rule to `status: deprecated`.

## 5. Link rules

- `implemented-in` MUST target a `repository/<repo>` note and `context` a
  `resource/...` note, and both MUST carry a `link-info`. `make graph` fails
  otherwise.
- The repository is not documented yet: document it first with the
  `knowledge-base-document-repository` skill, or ask the user.
- The needed material is not in the vault yet: ingest it with the
  `knowledge-base-ingest-resource` skill, or leave the URL as plain text under
  `## Context` and tell the user.
- Other links use the controlled vocabulary: `related, supersedes,
  superseded-by, depends-on, part-of, parent, derived-from, see-also, source`.
  Never write `[[wiki links]]`.
- Do not leave a section empty; write `None.` if it truly has nothing.

## 6. Regenerate and validate

```bash
make graph
```

Fix every reported problem and re-run until clean.

## 7. Stage (do not commit unless asked)

Stage each touched path individually - never `git add -A` / `git add .`:

```bash
git add domains/<domain>/
git add domains/index.md
git add index/graph.json
```

## 8. Report

Summarize: notes created or changed (path + kind), the `implemented-in` and
`context` links with their link-info, gaps (undocumented repositories, missing
resources), and the graph-validation result.
