#!/usr/bin/env python3
"""bdx: a read-only CLI for bestdesignsonx.com.

The site is a Svelte SPA that reads published rows straight from a public
Supabase project using the anon key shipped in its JS bundle. This CLI makes
the same read-only queries. It never writes (no likes, submissions or signups).

Unofficial and not affiliated with bestdesignsonx.com. HTTP goes through curl
so the only dependencies are python3 and curl (python's urllib often fails
cert verification on macOS).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlencode

SITE = "https://bestdesignsonx.com"
SUPABASE = "https://tuzpqmdnxvlzwqthgseg.supabase.co/rest/v1"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "bdx"
KEY_TTL = 7 * 24 * 3600

# Tag slugs as hard-coded in the site's bundle (filter list on the feed).
TAGS = [
    "landing-page", "hero-section", "dashboard", "sidebar", "modal", "dropdown", "button", "cta",
    "form", "sign-up", "onboarding", "pricing", "navigation", "menu", "tabs", "card", "bento",
    "table", "analytics-chart", "statistics", "mobile-app", "app-screens", "mac-app", "portfolio",
    "branding", "logo", "typography", "illustration", "3d", "motion", "web-animation",
    "scroll-animation", "loading-animation", "loading", "framer", "shader", "dark-mode", "ai",
    "ai-agents", "ai-flow", "chat-layout", "e-commerce", "checkout", "crypto", "calendar", "search",
    "command-bar", "tooltip-popover", "notification", "progress", "image-slider", "footer",
    "features", "testimonials", "settings-page", "user-profile", "empty-states", "404-page",
    "wireframe", "ui-kit", "icons", "app-icon", "poster", "color-palette", "css", "hover-state",
    "liquid-glass", "terminal-aesthetic", "ui-interaction", "widget", "accordion", "badge",
    "gallery", "map", "music-player", "todo-list", "text-effect", "file-upload", "range-slider",
    "switch-button",
]

DESIGN_SORTS = {
    "new": "created_at.desc",
    "likes": "interaction->likes.desc.nullslast",
    "views": "interaction->views.desc.nullslast",
    "bookmarks": "interaction->bookmarks.desc.nullslast",
}

PUBLISHED = {"approval_status": "eq.published", "status": "eq.published"}

# The site's other tabs. Each maps to one public table.
SECTIONS = {
    "websites": dict(table="mobbin_sites", filters={}, order="published_at.desc.nullslast",
                     search=["name", "description"], tag_col="categories",
                     title="name", sub="description", url="url", image="photo"),
    "fonts": dict(table="fonts", filters={"status": "eq.Published"}, order="report_date.desc",
                  search=["title"], tag_col="tags",
                  title="title", sub="details.foundry", url="url", image="thumbnail"),
    "app-icons": dict(table="bestdesignsonx_app_icons", filters=PUBLISHED,
                      order="published_at.desc.nullslast", search=["title", "developer_name"],
                      tag_col=None, title="title", sub="category_name", url="app_url",
                      image="icon_url"),
    "og-images": dict(table="bestdesignsonx_og_images", filters=PUBLISHED, order="updated_at.desc",
                      search=["title"], tag_col="categories",
                      title="title", sub="categories", url="site_url", image="image_url"),
    "studios": dict(table="bestdesignsonx_design_studios",
                    filters={"approval_status": "eq.published"}, order="id.desc",
                    search=["name", "city", "country"], tag_col="categories",
                    title="name", sub="city,country", url="website_url", image="og_image_url"),
    "systems": dict(table="bestdesignsonx_systems", filters={"approval_status": "eq.published"},
                    order="id.desc", search=["company_name", "system_name"], tag_col=None,
                    title="company_name", sub="system_name", url="source_url", image="logo_url"),
    "skills": dict(table="bestdesignsonx_skills", filters={"approval_status": "eq.published"},
                   order="id.desc", search=["title", "owner", "repo"], tag_col="categories",
                   title="title", sub="owner,repo", url="url", image="image_url"),
    "launch-videos": dict(table="launchvideos_posts", filters={"status": "eq.Published"},
                          order="published_at.desc.nullslast", search=["description"],
                          tag_col="categories", title="brand_username", sub="title",
                          url="source_url", image="media_url"),
    "instagram": dict(table="bestdesignsonx_instagram", filters=PUBLISHED,
                      order="report_date.desc.nullslast", search=["title", "username"],
                      tag_col=None, title="username", sub="title", url="post_url",
                      image="image_url"),
    "on-design": dict(table="bestdesignsonx_on_design", filters=PUBLISHED,
                      order="posted_at.desc.nullslast", search=["title", "content", "username"],
                      tag_col="tags", title="title", sub="author_name", url="post_url",
                      image="image_url"),
}


class BdxError(Exception):
    pass


# --- HTTP -------------------------------------------------------------------

def curl(url, headers=None, include_headers=False):
    cmd = ["curl", "-sS", "-g", "-L", "--max-time", "30", "-A", "bdx-cli"]
    if include_headers:
        cmd.append("-i")
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise BdxError(f"curl failed ({res.returncode}): {res.stderr.strip()}")
    return res.stdout


def anon_key(refresh=False):
    """The public anon key the site ships to every browser. Env wins, then cache, then the bundle."""
    if os.environ.get("BDX_ANON_KEY"):
        return os.environ["BDX_ANON_KEY"]
    cache = CACHE / "anon.json"
    if not refresh and cache.exists():
        data = json.loads(cache.read_text())
        if time.time() - data.get("fetched", 0) < KEY_TTL:
            return data["key"]
    html = curl(SITE + "/")
    m = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not m:
        raise BdxError("could not find the site's JS bundle")
    bundle = curl(SITE + m.group(1))
    keys = re.findall(r"eyJ[\w-]{20,}\.[\w-]+\.[\w-]+", bundle)
    if not keys:
        raise BdxError("could not find the public anon key in the site bundle")
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"key": keys[0], "fetched": time.time()}))
    return keys[0]


def rest(table, params, count=False, _retry=True):
    """GET a PostgREST table. Returns (rows, total or None)."""
    key = anon_key()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if count:
        headers["Prefer"] = "count=exact"
    raw = curl(f"{SUPABASE}/{table}?{urlencode(params, safe='*,.()>{}-:', quote_via=quote)}", headers, True)
    head, body = (re.split(r"\r?\n\r?\n", raw, maxsplit=1) + [""])[:2]
    status = int(head.split()[1]) if head.startswith("HTTP") else 0
    if status == 401 and _retry and not os.environ.get("BDX_ANON_KEY"):
        anon_key(refresh=True)  # key rotated with a new deploy
        return rest(table, params, count, _retry=False)
    if status >= 400:
        raise BdxError(f"HTTP {status}: {body[:300]}")
    total = None
    m = re.search(r"content-range:\s*[\d*-]+/(\d+)", head, re.I)
    if m:
        total = int(m.group(1))
    return json.loads(body or "[]"), total


def rpc(fn):
    key = anon_key()
    cmd = ["curl", "-sS", "-g", "--max-time", "30", "-X", "POST", "-H", f"apikey: {key}",
           "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json",
           "-d", "{}", f"{SUPABASE}/rpc/{fn}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise BdxError(res.stderr.strip())
    return json.loads(res.stdout)


# --- helpers ------------------------------------------------------------------

def clean(q):
    """Strip characters that would break a PostgREST or()/ilike expression."""
    return " ".join(re.sub(r"[,()*%]", " ", q).split())


def ilike_any(cols, q):
    q = clean(q)
    return "(" + ",".join(f"{c}.ilike.*{q}*" for c in cols) + ")"


def pick(row, path):
    """Resolve 'a.b' or 'a,b' field specs against a row for display."""
    if "," in path:
        return ", ".join(str(v) for v in (pick(row, p) for p in path.split(",")) if v)
    cur = row
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    if isinstance(cur, list):
        return ", ".join(map(str, cur))
    return cur


def short(text, n=70):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def num(n):
    if n is None:
        return "-"
    return f"{n / 1_000_000:.1f}M" if n >= 1_000_000 else f"{n / 1000:.1f}K" if n >= 1000 else str(n)


def x_url(row):
    return "https://x.com" + row["post_url"] if row.get("post_url") else None


def media_urls(row):
    urls = []
    for m in row.get("media") or []:
        for k in ("video", "video_url", "url", "image"):
            if m.get(k):
                urls.append(m[k])
                break
    return urls


def emit(args, rows, render, total=None):
    if args.json:
        print(json.dumps(rows if total is None else {"total": total, "items": rows}, indent=2))
        return
    for r in rows:
        print(render(r))
    if total is not None:
        start = args.page * args.limit
        print(f"\n{start + 1 if rows else 0}-{start + len(rows)} of {total}"
              + (f"  (next: --page {args.page + 1})" if start + len(rows) < total else ""))


# --- commands -----------------------------------------------------------------

def render_design(r):
    i = r.get("interaction") or {}
    kind = "video" if any(m.get("type") != "photo" for m in r.get("media") or []) else "img"
    return (f"{r['id']:>6}  @{r.get('handle', ''):<18} {short(r.get('tweet_text'), 50):<50}  "
            f"♥ {num(i.get('likes')):>6}  👁 {num(i.get('views')):>6}  {kind:<5} "
            f"{','.join(r.get('tags') or [])}")


def cmd_designs(args):
    params = {"select": "*", "status": "eq.Published", "order": DESIGN_SORTS[args.sort],
              "limit": args.limit, "offset": args.page * args.limit}
    if args.tag:
        bad = [t for t in args.tag if t not in TAGS]
        if bad:
            raise BdxError(f"unknown tag(s): {', '.join(bad)}. Run `bdx tags` for the list.")
        params["tags"] = "cs.{" + ",".join(args.tag) + "}"
    if args.creator:
        params["handle"] = "ilike." + clean(args.creator.lstrip("@"))
    if args.search:
        params["or"] = ilike_any(["tweet_text", "author_name", "handle"], args.search)
    if args.featured:
        params["featured"] = "is.true"
    if args.since:
        params["created_at"] = f"gte.{args.since}"
    rows, total = rest("bestdesignsonx", params, count=True)
    emit(args, rows, render_design, total)


def get_design(ref):
    m = re.search(r"/status/(\d+)", ref)
    if m:
        params = {"post_url": f"like.*/status/{m.group(1)}"}
    elif ref.isdigit():
        params = {"id": f"eq.{ref}"}
    else:
        raise BdxError("pass a design id or an x.com status URL")
    rows, _ = rest("bestdesignsonx", {"select": "*", "status": "eq.Published", **params, "limit": 1})
    if not rows:
        raise BdxError(f"no published design matches {ref}")
    return rows[0]


def cmd_design(args):
    r = get_design(args.ref)
    if args.json:
        print(json.dumps(r, indent=2))
        return
    i = r.get("interaction") or {}
    print(f"#{r['id']}  {r.get('author_name')} (@{r.get('handle')})")
    print(f"  {r.get('tweet_text')}")
    print(f"  posted   {r.get('time')}   added {r.get('created_at')}")
    print(f"  likes {num(i.get('likes'))}  views {num(i.get('views'))}  "
          f"bookmarks {num(i.get('bookmarks'))}  reposts {num(i.get('reposts'))}")
    print(f"  tags     {', '.join(r.get('tags') or []) or '-'}")
    print(f"  post     {x_url(r)}")
    for u in media_urls(r):
        print(f"  media    {u}")


def cmd_download(args):
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    for ref in args.ref:
        r = get_design(ref)
        for n, u in enumerate(media_urls(r), 1):
            ext = Path(u.split("?")[0]).suffix or ".bin"
            dest = out / f"{r['handle']}-{r['id']}-{n}{ext}"
            res = subprocess.run(["curl", "-sS", "-g", "-L", "--fail", "-o", str(dest), u])
            print(("saved  " if res.returncode == 0 else "FAILED ") + str(dest))


def cmd_open(args):
    r = get_design(args.ref)
    webbrowser.open(x_url(r))
    print(x_url(r))


def cmd_tags(args):
    if not args.counts:
        if args.json:
            print(json.dumps(TAGS))
        else:
            print("\n".join(TAGS))
        return
    counts = []
    for t in TAGS:
        _, total = rest("bestdesignsonx", {"select": "id", "status": "eq.Published",
                                           "tags": "cs.{" + t + "}", "limit": 1}, count=True)
        counts.append({"tag": t, "count": total})
    counts.sort(key=lambda c: -(c["count"] or 0))
    if args.json:
        print(json.dumps(counts, indent=2))
    else:
        for c in counts:
            print(f"{c['count']:>6}  {c['tag']}")


def cmd_creators(args):
    q = clean(args.query.lstrip("@"))
    rows, _ = rest("bestdesignsonx", {"select": "handle,author_name", "status": "eq.Published",
                                      "or": f"(handle.ilike.{q}*,author_name.ilike.*{q}*)",
                                      "limit": 500})
    seen = {}
    for r in rows:
        h = r["handle"]
        seen.setdefault(h.lower(), {"handle": h, "author_name": r.get("author_name"), "designs": 0})
        seen[h.lower()]["designs"] += 1
    found = sorted(seen.values(), key=lambda c: -c["designs"])[: args.limit]
    if args.json:
        print(json.dumps(found, indent=2))
    else:
        for c in found:
            print(f"@{c['handle']:<22} {short(c['author_name'], 30):<30} {c['designs']} designs")


def cmd_browse(args):
    s = SECTIONS[args.section]
    params = {"select": "*", **s["filters"], "order": s["order"],
              "limit": args.limit, "offset": args.page * args.limit}
    if args.search:
        params["or"] = ilike_any(s["search"], args.search)
    if args.tag:
        if not s["tag_col"]:
            raise BdxError(f"{args.section} has no tags/categories to filter on")
        params[s["tag_col"]] = "cs.{" + clean(args.tag) + "}"
    rows, total = rest(s["table"], params, count=True)

    def render(r):
        return (f"{str(r.get('id'))[:8]:>8}  {short(pick(r, s['title']), 32):<32} "
                f"{short(pick(r, s['sub']), 40):<40} {pick(r, s['url']) or ''}")
    emit(args, rows, render, total)


def cmd_stats(args):
    out = {"designs": rpc("get_published_designs_count")}
    for name, s in SECTIONS.items():
        _, total = rest(s["table"], {"select": "id", **s["filters"], "limit": 1}, count=True)
        out[name] = total
    latest, _ = rest("bestdesignsonx", {"select": "created_at", "status": "eq.Published",
                                        "order": "created_at.desc", "limit": 1})
    out["latest_design_added"] = latest[0]["created_at"] if latest else None
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for k, v in out.items():
            print(f"{k:<20} {v}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bdx", description="Read-only CLI for bestdesignsonx.com")
    p.add_argument("--json", action="store_true", help="print raw JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    def paged(sp, limit=20):
        sp.add_argument("-n", "--limit", type=int, default=limit)
        sp.add_argument("-p", "--page", type=int, default=0, help="0-based page")

    d = sub.add_parser("designs", aliases=["feed", "ls"], help="the main X design feed")
    d.add_argument("-t", "--tag", action="append", help="tag slug (repeat to AND tags)")
    d.add_argument("-c", "--creator", help="X handle")
    d.add_argument("-s", "--search", help="text in the post, author name or handle")
    d.add_argument("--sort", choices=DESIGN_SORTS, default="new")
    d.add_argument("--featured", action="store_true")
    d.add_argument("--since", help="added on/after this date, e.g. 2026-10-01")
    paged(d)
    d.set_defaults(fn=cmd_designs)

    s = sub.add_parser("design", aliases=["show"], help="one design by id or x.com URL")
    s.add_argument("ref")
    s.set_defaults(fn=cmd_design)

    dl = sub.add_parser("download", aliases=["dl"], help="save a design's images/videos")
    dl.add_argument("ref", nargs="+")
    dl.add_argument("-o", "--out", default=".")
    dl.set_defaults(fn=cmd_download)

    o = sub.add_parser("open", help="open the original X post in the browser")
    o.add_argument("ref")
    o.set_defaults(fn=cmd_open)

    t = sub.add_parser("tags", help="list tag slugs")
    t.add_argument("--counts", action="store_true", help="count designs per tag (80 requests)")
    t.set_defaults(fn=cmd_tags)

    c = sub.add_parser("creators", help="find creators by handle or name")
    c.add_argument("query")
    c.add_argument("-n", "--limit", type=int, default=20)
    c.set_defaults(fn=cmd_creators)

    b = sub.add_parser("browse", help="the site's other tabs: " + ", ".join(SECTIONS))
    b.add_argument("section", choices=SECTIONS)
    b.add_argument("-s", "--search")
    b.add_argument("-t", "--tag", help="category/tag, where the section has them")
    paged(b)
    b.set_defaults(fn=cmd_browse)

    st = sub.add_parser("stats", help="item counts per section")
    st.set_defaults(fn=cmd_stats)

    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv  # accept --json before or after the subcommand
    args = p.parse_args([a for a in argv if a != "--json"])
    args.json = as_json
    try:
        args.fn(args)
    except BdxError as e:
        print(f"bdx: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
