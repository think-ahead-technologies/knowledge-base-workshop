---
name: knowledge-base-ingest-resource
description: Ingest a resource (local file, URL/webpage, PDF, YouTube video, etc.) into the knowledge-base vault so it can feed domains with context. Copies the original into 03_resources/<slug>/raw/, reads it, breaks it into topics, and wires it to the domains, features and rules that need it with `context` links that say why. For YouTube, pulls the transcript into raw/. Use when the user says "ingest", "add this resource", "save this link/video/paper/spec", or hands you a file/URL to capture and link.
---

# Ingest a Resource

A resource is a static document or required online material. It exists in the
vault to give the **domains** context: every domain, feature or rule that needs
it links to it with a `context` link whose `link-info` says why or in which way
it is needed. Follow every step.

Obey `AGENTS.md` (read it if not already loaded this session).

The output is:

```
03_resources/<slug>/
  index.md          the resource note (summary, source, topics, who needs it)
  <topic>.md        one note per topic worth recalling
  raw/              original bytes / transcript / fetched page (not in the graph)
```

plus `context` links into it from the domain notes that need it. All notes in
`03_resources/` are `type: resource` (the folder implies it; you may omit `type`).

## 1. Identify the resource and its type

The resource comes from the conversation - a file path, a URL, a pasted link, or
an attachment. Classify it; this drives the capture in step 3:

| Type            | Signal                                   | Capture into `raw/`                  |
|-----------------|------------------------------------------|--------------------------------------|
| Local file      | a path that exists on disk               | copy the file verbatim               |
| YouTube video   | host is youtube.com / youtu.be           | pull the **transcript** (+ metadata) |
| Webpage / link  | any other http(s) URL                    | save the fetched page + URL          |
| PDF / doc       | path or URL ending in .pdf/.docx/...     | copy/download the binary verbatim    |

Also find out **why** it is being ingested - which domain, feature or rule it is
for. Take it from the conversation; ask only if nothing hints at it. A resource
nobody needs yet may still be ingested; it is then listed as unlinked in step 8.

## 2. Derive the slug and create the folder

Pick a short kebab-case `<slug>` from the title / filename (e.g.
`cyclonedx-sbom-spec`, `oauth2-rfc6749`).

```bash
ls 03_resources/                      # check the slug is not taken
mkdir -p 03_resources/<slug>/raw
```

If the slug exists, either you are re-ingesting (update in place, tell the user)
or pick a more specific slug.

## 3. Copy the original into `raw/`

Always preserve the source bytes untouched.

**Local file** - copy verbatim, keep the original name:
```bash
cp "<source-path>" "03_resources/<slug>/raw/"
```

**PDF / binary at a URL** - download verbatim:
```bash
curl -fsSL "<url>" -o "03_resources/<slug>/raw/<filename>"
```

**Webpage / link** - record the URL, fetch the page with `WebFetch` (request
markdown) and write the result to `raw/page.md`:
```bash
printf '%s\n' "<url>" > "03_resources/<slug>/raw/source.url"
```

**YouTube video** - record the URL, then pull the transcript:
```bash
printf '%s\n' "<url>" > "03_resources/<slug>/raw/source.url"

# Preferred: yt-dlp grabs subs + metadata without downloading the video
yt-dlp --skip-download --write-subs --write-auto-subs --sub-lang en \
  --convert-subs srt --write-info-json \
  -o "03_resources/<slug>/raw/%(title)s.%(ext)s" "<url>"

# Fallback if yt-dlp is absent: python transcript API
python3 -c "import youtube_transcript_api" 2>/dev/null && \
  python3 -c "from youtube_transcript_api import YouTubeTranscriptApi as A; \
vid='<VIDEO_ID>'; \
open('03_resources/<slug>/raw/transcript.txt','w').write(\
'\n'.join(s['text'] for s in A.get_transcript(vid)))"
```
If neither tool is installed, tell the user which to install (`pip install yt-dlp`
or `pip install youtube-transcript-api`) and stop. Never invent transcript text.

## 4. Read the captured content

Read what you stored in `raw/`. This - not the live URL - is the source of truth
for the rest of the steps. For long content, read enough to find every distinct
topic, not just the intro.

## 5. Find who needs it and what it covers

**Consumers.** Find the domain, feature and rule notes the resource gives
context to:

```bash
jq -r '.nodes[] | select(.type=="domain" or .type=="feature" or .type=="rule")
  | "\(.type)\t\(.id)\t\(.title)"' index/graph.json
grep -rIl "<term>" 01_domains
```

Prefer the `knowledge-database` MCP server when available
(`graph_search_nodes` with `type` / `domain` / `query`, `read_note`). Open each
candidate and confirm the resource really matters to it. For each consumer,
write down **why** it needs the resource - that sentence becomes the
`link-info`.

**Topics.** List the concrete concepts, standards, formats or tools the resource
covers. For each, check the vault:

```bash
jq -r --arg q "<topic>" '.nodes[] | select(.type=="resource")
  | select((.id|ascii_downcase|contains($q)) or (.title|ascii_downcase|contains($q)))
  | "\(.id)\t\(.path)"' index/graph.json
```

- **Covered** - another resource note covers it: link it (`related`), do not
  duplicate.
- **New** - worth recalling: write a topic note (step 6).
- **External** - not worth a note but has an authoritative URL: list the URL.

## 6. Write a note per new topic

`03_resources/<slug>/<topic>.md`:

```md
---
id: resource/<slug>/<topic>
title: <Topic Title>
status: active
tags: [<topic>, <extra-tags...>]
source: <original url or path>
ingested: <today, YYYY-MM-DD>
last_reviewed: <today, YYYY-MM-DD>
---

# <Topic Title>

<What the resource says about this topic - a few sentences, in your words.>

## In this resource
[<Resource title>](resource/<slug>){"type":"part-of","link-info":"<where the topic appears>"}

## Related
- [<title>](<other-resource-note-id>){"type":"related","link-info":"<what to expect there>"}
- <https://authoritative-spec-url>
```

One topic = one file. Skip trivia.

## 7. Write the resource note

`03_resources/<slug>/index.md`:

```md
---
id: resource/<slug>
title: <Human Title>
status: active
tags: [<topic-tags...>]
source: <original url or path>
ingested: <today, YYYY-MM-DD>
last_reviewed: <today, YYYY-MM-DD>
---

# <Human Title>

## Summary
<2-5 sentences: what this resource is and what it is good for.>

## Source
- Type: <local file | webpage | youtube | pdf | ...>
- Origin: <url or original path>
- Raw: `03_resources/<slug>/raw/`

## Topics
- [<Topic>](resource/<slug>/<topic>){"type":"related","link-info":"<one line>"}
- [<Topic>](<other-resource-id>){"type":"related","link-info":"<one line>"}
- **<Topic>** - <one line> -> <https://external-spec-url>

## Needed by
- [<Domain / feature / rule>](<note-id>) - <why it needs this resource>
```

`## Needed by` mirrors the `context` links of step 8 so the reason is visible
from both ends. Write `None yet.` if no consumer exists. Do not leave a section
empty; write `None.` if it truly has nothing.

## 8. Wire `context` links from the consumers

This is what makes the resource useful. In each consumer note from step 5, add
under its `## Context` section (create it if absent):

```md
- [<Resource title>](resource/<slug>){"type":"context","link-info":"<why or in which way this note needs it>"}
```

Point at a topic note instead (`resource/<slug>/<topic>`) when only that topic
matters. The `link-info` is required - `make graph` fails without it. Use
individual edits; change nothing else in the consumer notes.

Then list the resource in `03_resources/index.md` under `## Resources`, replacing
the `// no document, yet` line if present:

```md
- [<Human Title>](resource/<slug>){"type":"related","link-info":"<one line>"}
```

## 9. Regenerate and validate the graph

```bash
make graph
```

Fix every reported problem: unresolved link targets, unknown edge `type`, a
`type` that contradicts the folder, or a `context` link without `link-info` /
not pointing at a resource. Re-run until clean. The pre-commit hook rejects a
stale or invalid graph.

## 10. Stage (do not commit unless asked)

NEVER use `git add -A` or `git add .`. Stage each touched path:

```bash
git add 03_resources/<slug>/
git add 03_resources/index.md
git add <each-consumer-note-you-linked>.md
git add index/graph.json
```

Only commit or open a PR if the user explicitly asks.

## 11. Report

Summarize: the resource id/path and type, what landed in `raw/`, the topic notes
created, each consumer linked with `context` and its why, topics linked to other
resources vs. captured as external URLs, files touched, and the
graph-validation result.
