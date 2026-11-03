# Skills

Skill definitions for this vault, symlinked into `.claude/skills/`
(`.claude/skills/<name> -> ../../skills/<name>`). Each skill works one kind of
knowledge in the domains / repositories / resources model (see `README.md`):

- `knowledge-base-read/` - answer questions from the vault: domain -> features
  and rules -> `implemented-in` repositories and `context` resources.
- `knowledge-base-write-domain/` - write a domain, a feature or a rule, and link
  it to its repositories and resources.
- `knowledge-base-document-repository/` - document where a repository lives and
  where to find what in it, and link the domains it implements.
- `knowledge-base-ingest-resource/` - capture a document or online resource
  into `resources/<slug>/` and link it with `context` to the domains that need it.

When creating a new skill or renaming a folder, adjust the links in
`./.claude/skills/`.
