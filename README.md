# bdx: a CLI for bestdesignsonx.com

An unofficial, read-only command line for [bestdesignsonx.com](https://bestdesignsonx.com), the hand-picked feed of design posts from X. It also covers the site's other galleries: websites, fonts, app icons, OG images, design studios, design systems, agent skills, launch videos, Instagram and on.design.

It's built for people and AI agents (Claude Code, Codex, Cursor) that want design references from the terminal. It's one Python file with no dependencies beyond `python3` and `curl`.

> Not affiliated with bestdesignsonx.com. All credit for the curation goes to [@bestdesignsonx](https://x.com/bestdesignsonx) and the designers whose work it features.

## Install

```bash
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/ary4n/bestdesignsonx-cli/main/bdx.py -o ~/.local/bin/bdx
chmod +x ~/.local/bin/bdx
bdx stats
```

(Make sure `~/.local/bin` is on your `PATH`.)

## Usage

```bash
bdx designs                                  # newest 20, same order as the site
bdx designs -t landing-page --sort likes     # most-liked landing pages
bdx designs -t dashboard -t dark-mode        # tags are ANDed
bdx designs -c jamesm                        # one creator
bdx designs -s "pricing" --since 2026-10-01 -n 50 -p 1
bdx design 7355                              # detail; also accepts an x.com status URL
bdx download 7355 8928 -o ~/inspo            # save images/videos
bdx open 7355                                # open the X post
bdx tags [--counts]                          # 80 tag slugs; --counts makes 80 requests
bdx creators basit                           # find handles
bdx browse fonts -t Monospace
bdx browse studios -s london
bdx browse systems | websites | app-icons | og-images | skills | launch-videos | instagram | on-design
bdx stats
bdx --json designs -t logo                   # any command, raw JSON
```

Sort options for `designs` are `new` (the default), `likes`, `views` and `bookmarks`.

## Use it from an AI agent

[`skills/bdx/SKILL.md`](skills/bdx/SKILL.md) is a ready-made agent skill.

- **Claude Code:** copy the `skills/bdx` folder to `~/.claude/skills/bdx`, or to `.claude/skills/bdx` in a project.
- **Other agents:** paste the file's contents into `AGENTS.md` or your rules file.

## How it works

The site is a single-page app with no public API. Your browser reads published rows directly from the site's Supabase backend, using the public anon key in its JS bundle. `bdx` makes those same read-only requests:

- The key is read from the live site at runtime and cached for 7 days in `~/.cache/bdx/`. A deploy that rotates it triggers a re-fetch. You can set `BDX_ANON_KEY` to override it.
- No writes. Likes, submissions, signups and feedback are deliberately not implemented.
- Only content the site itself shows publicly.

Because this relies on an undocumented backend, it can break whenever the site changes.

## Be nice

This hits a small independent site's backend. Use it for browsing and research, not bulk scraping or mirroring. Every command makes a single request, except `tags --counts` and `stats`. If the site owner asks for this to come down, it will.

## License

MIT
