# Agents

Subagent definitions for this vault. Mirrors the `skills/` convention: each agent
lives here and is wired into `.claude/agents/` as a relative symlink
(`.claude/agents/<name>.md -> ../../agents/<name>.md`).

- `the-knowing-one.md` - read-only information gatherer. Send it a topic or task;
  it finds the domain, reads its features and rules, follows `implemented-in`
  links to the repositories and `context` links to the resources, and returns a
  cited, synthesized briefing.
- `the-scribe.md` - MCP-only writer. Picks the matching skill
  (`knowledge-base-ingest-resource`, `knowledge-base-write-domain`,
  `knowledge-base-document-repository`) and records one item - a resource, a
  domain / feature / rule, or a repository - then refreshes the graph, commits
  the named paths, and pushes, entirely through the `knowledge-database` MCP
  server.

When creating a new agent or renaming a file, adjust the symlinks in
`./.claude/agents/`. To use an agent from another agent's home dir, link it like
the skills, e.g.:

```sh
ln -s "$PWD/agents/the-knowing-one.md" ~/.claude/agents/the-knowing-one.md
```
