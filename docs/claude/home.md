---
source: https://platform.claude.com/docs/en/home
fetched: 2026-05-20
note: |
  This URL is a React landing page, not a markdown doc. The Mintlify .md endpoint
  (https://platform.claude.com/docs/en/home.md) returns only the placeholder
  `<HomePage />`, meaning the page is rendered entirely client-side from a
  React component — there is no underlying markdown source to extract.
  See the live page in a browser for the actual content (hero, cards, links
  to API docs, Claude Code, Console, etc.).
---

# Claude Docs — Home (landing page)

> The home page at `platform.claude.com/docs/en/home` is a client-rendered
> React landing page. It does not have a markdown source, so this file is a
> placeholder.

## Why this is empty

- Mintlify (the docs platform) lets pages either be MDX content or a custom
  React component. The home page is configured as the latter.
- Fetching `home.md` returns the literal string `<HomePage />`.
- The visible content (hero, navigation cards, etc.) is composed in JS at
  runtime; no canonical markdown exists.

## Suggested follow-up URLs

If you want actual doc text, fetch a specific topic page instead. A few that
do have markdown sources:

- `https://platform.claude.com/docs/en/managed-agents/cloud-containers` — saved as `managed-agents-cloud-containers.md`
- `https://platform.claude.com/docs/en/managed-agents/overview` (if exists)
- `https://platform.claude.com/docs/en/api/getting-started` (if exists)

Ask and I can fetch any of them.
