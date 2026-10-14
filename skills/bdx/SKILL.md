---
name: bdx
description: Use when finding design inspiration or references: UI patterns, landing pages, dashboards, branding, logos, motion, fonts, app icons, design studios, design systems, launch videos. Searches bestdesignsonx.com (curated design posts from X plus 10 other galleries) via the read-only `bdx` CLI.
---

# bdx: bestdesignsonx.com CLI

Run `bdx`. If it isn't installed, install it first:
`mkdir -p ~/.local/bin && curl -fsSL https://raw.githubusercontent.com/ary4n/bestdesignsonx-cli/main/bdx.py -o ~/.local/bin/bdx && chmod +x ~/.local/bin/bdx`
(or run `python3 bdx.py` directly). It needs python3 and curl, is read-only and needs no auth. Add `--json` to any command for machine-readable output.

## Main feed (designs from X)
- `bdx designs -t <tag> --sort likes -n 10`: best examples of a pattern. Sorts: new (default), likes, views, bookmarks
- Repeat `-t` to AND tags: `-t dashboard -t dark-mode`
- `-s "text"` searches post text/author; `-c handle` for one creator; `--since 2026-10-01`; `-p 1` next page
- `bdx tags` lists the 80 valid tag slugs (landing-page, hero-section, pricing, onboarding, bento, motion, branding, logo, …). Unknown tags error out, so check first.
- `bdx design <id|x.com URL>`: full detail + media URLs
- `bdx download <id...> -o <dir>`: saves images/MP4s
- `bdx creators <name>`: find handles

## Other galleries
`bdx browse <section> [-s text] [-t tag] [-n N]` with sections: websites, fonts (`-t Monospace`, Serif, Display…), app-icons, og-images, studios (`-s london`), systems, skills, launch-videos, instagram, on-design.

`bdx stats` shows counts per section.

## Tips
- For "find references for X": run `designs -t <tag> --sort likes -n 10 --json`, then share the x.com post URLs; download only if asked.
- Engagement numbers can be 0 for recently added posts; don't treat that as low quality.
- If a command fails with HTTP 401 twice, the site changed its backend. Report it rather than retry.
- Keep request volume low: this is a small independent site, not an API.
