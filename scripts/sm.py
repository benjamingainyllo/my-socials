#!/usr/bin/env python3
"""sm - social ops CLI for this repo. Python stdlib only, no installs.

Every post is a markdown file with a front-matter block:

    ---
    account: scaile
    platform: x
    type: thread
    status: draft
    created: 2026-09-19
    scheduled: 2026-09-22
    topic: aeo
    url:
    ---

    Body text. In a thread, a line containing only --- separates tweets.

Status is the folder it lives in:
    content/<account>/{drafts,queue,posted}/<slug>.md

Run `python3 scripts/sm.py help` for commands.
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.json"
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
ANALYTICS = ROOT / "analytics"
POSTS_CSV = ANALYTICS / "posts.csv"
FOLLOWERS_CSV = ANALYTICS / "followers.csv"

STATUSES = ["drafts", "queue", "posted"]
POST_FIELDS = [
    "date", "account", "platform", "slug", "url",
    "impressions", "likes", "replies", "reposts", "clicks",
    "followers_gained", "notes",
]
FOLLOWER_FIELDS = ["date", "account", "platform", "followers"]
METRIC_FIELDS = ["impressions", "likes", "replies", "reposts", "clicks", "followers_gained"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def today() -> str:
    return dt.date.today().isoformat()


def load_config() -> dict:
    if not CONFIG.exists():
        die(f"no config.json at {CONFIG} - see README.md")
    return json.loads(CONFIG.read_text())


def die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "untitled"


def parse_post(path: Path) -> dict:
    """Return {'meta': {...}, 'body': str, 'path': Path}. Tolerates a missing block."""
    raw = path.read_text()
    meta, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2].lstrip("\n")
    meta.setdefault("slug", path.stem)
    meta.setdefault("status", path.parent.name)
    meta.setdefault("account", path.parent.parent.name)
    return {"meta": meta, "body": body, "path": path}


def write_post(path: Path, meta: dict, body: str):
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines += ["---", "", body.rstrip(), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def iter_posts(account=None, status=None, platform=None):
    if not CONTENT.exists():
        return
    for path in sorted(CONTENT.glob("*/*/*.md")):
        if account and path.parent.parent.name != account:
            continue
        if status and path.parent.name != status:
            continue
        post = parse_post(path)
        if platform and post["meta"].get("platform") != platform:
            continue
        yield post


def segments(body: str) -> list:
    """Split a thread body into individual posts on --- separator lines."""
    chunks = re.split(r"^\s*---\s*$", body, flags=re.MULTILINE)
    return [c.strip() for c in chunks if c.strip()]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path, fields: list) -> list:
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def append_csv(path: Path, fields: list, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)


def num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_new(args):
    cfg = load_config()
    if args.account not in cfg["accounts"]:
        die(f"unknown account '{args.account}'. Known: {', '.join(cfg['accounts'])}")

    tpl_path = TEMPLATES / f"{args.type}.md"
    body = ""
    if tpl_path.exists():
        tpl = parse_post(tpl_path)
        body = tpl["body"]

    slug = slugify(args.title)
    path = CONTENT / args.account / "drafts" / f"{today()}-{slug}.md"
    if path.exists():
        die(f"{rel(path)} already exists")

    meta = {
        "account": args.account,
        "platform": args.platform or cfg["accounts"][args.account]["platforms"][0],
        "type": args.type,
        "status": "drafts",
        "title": args.title,
        "created": today(),
        "scheduled": args.scheduled or "",
        "topic": args.topic or "",
        "url": "",
    }
    write_post(path, meta, body)
    print(rel(path))


def cmd_list(args):
    rows = []
    for post in iter_posts(args.account, args.status, args.platform):
        m = post["meta"]
        rows.append((
            m.get("status", "?"),
            m.get("account", "?"),
            m.get("platform", "?"),
            m.get("scheduled") or "-",
            m.get("title") or m.get("slug"),
            rel(post["path"]),
        ))
    if not rows:
        print("nothing found")
        return
    rows.sort(key=lambda r: (STATUSES.index(r[0]) if r[0] in STATUSES else 9, r[3]))
    width = max(len(r[4]) for r in rows)
    for status, account, platform, sched, title, path in rows:
        print(f"{status:<7} {account:<12} {platform:<9} {sched:<11} {title:<{width}}  {path}")
    print(f"\n{len(rows)} post(s)")


def cmd_due(args):
    limit = (dt.date.today() + dt.timedelta(days=args.days)).isoformat()
    overdue, upcoming, unscheduled = [], [], []
    for post in iter_posts(args.account, "queue"):
        m = post["meta"]
        sched = m.get("scheduled", "").strip()
        label = f"{m.get('account')}/{m.get('platform')}  {m.get('title') or m.get('slug')}"
        if not sched:
            unscheduled.append(f"  {label}  [{rel(post['path'])}]")
        elif sched < today():
            overdue.append(f"  {sched}  {label}  [{rel(post['path'])}]")
        elif sched <= limit:
            upcoming.append(f"  {sched}  {label}  [{rel(post['path'])}]")

    for header, items in (
        ("OVERDUE", sorted(overdue)),
        (f"NEXT {args.days} DAYS", sorted(upcoming)),
        ("IN QUEUE, NO DATE", sorted(unscheduled)),
    ):
        if items:
            print(f"\n{header}")
            print("\n".join(items))
    if not (overdue or upcoming or unscheduled):
        print("queue is clear")


def cmd_move(args):
    path = Path(args.path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        die(f"no such file: {args.path}")
    if args.status not in STATUSES:
        die(f"status must be one of: {', '.join(STATUSES)}")

    post = parse_post(path)
    meta = post["meta"]
    meta["status"] = args.status
    if args.status == "posted":
        meta["posted"] = args.date or today()
        if args.url:
            meta["url"] = args.url
    dest = path.parent.parent / args.status / path.name
    write_post(dest, meta, post["body"])
    if dest != path:
        path.unlink()
    print(f"{rel(path)} -> {rel(dest)}")


def cmd_lint(args):
    cfg = load_config()
    problems = 0
    for post in iter_posts(args.account):
        m, path = post["meta"], post["path"]
        issues = []
        for field in ("account", "platform", "type", "status"):
            if not m.get(field):
                issues.append(f"missing '{field}'")
        platform = m.get("platform")
        limits = cfg.get("platforms", {}).get(platform, {})
        limit = limits.get("limit")
        if limit:
            for i, seg in enumerate(segments(post["body"]), 1):
                if len(seg) > limit:
                    issues.append(f"part {i} is {len(seg)} chars (limit {limit})")
        if m.get("status") == "posted" and not m.get("url"):
            issues.append("posted but no url recorded")
        if m.get("status") == "queue" and not m.get("scheduled"):
            issues.append("queued but not scheduled")
        if not post["body"].strip():
            issues.append("empty body")
        if issues:
            problems += 1
            print(f"{rel(path)}")
            for issue in issues:
                print(f"  - {issue}")
    print("all clean" if not problems else f"\n{problems} file(s) need attention")
    return 1 if problems and args.strict else 0


def cmd_log(args):
    matches = [p for p in iter_posts() if args.slug in p["path"].stem]
    if not matches:
        die(f"no post matching '{args.slug}'")
    if len(matches) > 1:
        die("ambiguous slug, matches:\n  " + "\n  ".join(rel(p["path"]) for p in matches))
    post = matches[0]
    m = post["meta"]
    row = {
        "date": args.date or today(),
        "account": m.get("account", ""),
        "platform": m.get("platform", ""),
        "slug": post["path"].stem,
        "url": args.url or m.get("url", ""),
        "notes": args.notes or m.get("topic", ""),
    }
    for field in METRIC_FIELDS:
        row[field] = getattr(args, field) or 0
    append_csv(POSTS_CSV, POST_FIELDS, row)
    print(f"logged {row['slug']} -> {rel(POSTS_CSV)}")


def cmd_snapshot(args):
    append_csv(FOLLOWERS_CSV, FOLLOWER_FIELDS, {
        "date": args.date or today(),
        "account": args.account,
        "platform": args.platform,
        "followers": args.followers,
    })
    print(f"logged {args.account}/{args.platform}: {args.followers}")


def engagement(row: dict) -> float:
    interactions = num(row.get("likes")) + num(row.get("replies")) + num(row.get("reposts"))
    impressions = num(row.get("impressions"))
    return (interactions / impressions * 100) if impressions else 0.0


def cmd_report(args):
    rows = read_csv(POSTS_CSV, POST_FIELDS)
    if args.account:
        rows = [r for r in rows if r.get("account") == args.account]
    if args.since:
        rows = [r for r in rows if r.get("date", "") >= args.since]
    if not rows:
        print("no analytics logged yet - use `sm log <slug> --impressions N --likes N`")
        return

    print(f"{len(rows)} logged post(s)\n")
    print("BY ACCOUNT")
    by_account = {}
    for r in rows:
        by_account.setdefault(r.get("account", "?"), []).append(r)
    for account, group in sorted(by_account.items()):
        impressions = sum(num(r["impressions"]) for r in group)
        likes = sum(num(r["likes"]) for r in group)
        replies = sum(num(r["replies"]) for r in group)
        gained = sum(num(r["followers_gained"]) for r in group)
        avg_er = sum(engagement(r) for r in group) / len(group)
        print(f"  {account:<12} {len(group):>3} posts  {impressions:>10,.0f} impr  "
              f"{likes:>7,.0f} likes  {replies:>6,.0f} replies  {avg_er:>5.2f}% ER  "
              f"{gained:>+6,.0f} followers")

    print("\nTOP BY ENGAGEMENT RATE")
    ranked = sorted(rows, key=engagement, reverse=True)
    for r in ranked[:args.top]:
        if not num(r.get("impressions")):
            continue
        print(f"  {engagement(r):>5.2f}%  {num(r['impressions']):>9,.0f} impr  "
              f"{r.get('account','?'):<12} {r.get('slug','')}")

    print("\nTOP BY IMPRESSIONS")
    for r in sorted(rows, key=lambda r: num(r.get("impressions")), reverse=True)[:args.top]:
        print(f"  {num(r['impressions']):>9,.0f}  {engagement(r):>5.2f}% ER  "
              f"{r.get('account','?'):<12} {r.get('slug','')}")

    topics = {}
    for r in rows:
        key = (r.get("notes") or "").strip()
        if key:
            topics.setdefault(key, []).append(r)
    if topics:
        print("\nBY TOPIC")
        scored = sorted(topics.items(),
                        key=lambda kv: sum(engagement(r) for r in kv[1]) / len(kv[1]),
                        reverse=True)
        for topic, group in scored:
            avg_er = sum(engagement(r) for r in group) / len(group)
            avg_impr = sum(num(r["impressions"]) for r in group) / len(group)
            print(f"  {topic:<24} {len(group):>3} posts  {avg_er:>5.2f}% avg ER  "
                  f"{avg_impr:>9,.0f} avg impr")

    follows = read_csv(FOLLOWERS_CSV, FOLLOWER_FIELDS)
    if follows:
        print("\nFOLLOWER GROWTH")
        by_key = {}
        for r in follows:
            by_key.setdefault((r["account"], r["platform"]), []).append(r)
        for (account, platform), group in sorted(by_key.items()):
            group.sort(key=lambda r: r["date"])
            first, last = group[0], group[-1]
            delta = num(last["followers"]) - num(first["followers"])
            print(f"  {account:<12} {platform:<9} {num(first['followers']):>8,.0f} -> "
                  f"{num(last['followers']):>8,.0f}  ({delta:+,.0f} since {first['date']})")


def cmd_accounts(args):
    cfg = load_config()
    for name, meta in cfg["accounts"].items():
        counts = {s: len(list(iter_posts(name, s))) for s in STATUSES}
        handles = ", ".join(f"{p}:{meta.get('handles', {}).get(p, '?')}"
                            for p in meta.get("platforms", []))
        print(f"{name:<12} {handles}")
        print(f"             drafts {counts['drafts']}  queue {counts['queue']}  "
              f"posted {counts['posted']}")
        if meta.get("notes"):
            print(f"             {meta['notes']}")


# --------------------------------------------------------------------------
# import: map a platform analytics export onto analytics/posts.csv
# --------------------------------------------------------------------------

# Checked in priority order. X, LinkedIn and Reddit exports all name these
# differently, so match on the normalised header rather than an exact string.
IMPORT_ALIASES = {
    "impressions": ["impressions", "impression", "views", "totalviews", "reach"],
    "likes": ["likes", "like", "favorites", "favorite", "upvotes", "reactions"],
    "replies": ["replies", "reply", "comments", "comment"],
    "reposts": ["reposts", "repost", "retweets", "retweet", "shares", "share"],
    "clicks": ["urlclicks", "linkclicks", "permalinkclicks", "clicks", "click"],
    "followers_gained": ["follows", "followersgained", "newfollowers", "netfollowers"],
}
DATE_ALIASES = ["date", "time", "posttime", "createdat", "published", "datetime", "postdate"]
URL_ALIASES = ["permalink", "posturl", "url", "link", "permalinkurl"]
ID_ALIASES = ["postid", "tweetid", "id", "slug"]
TEXT_ALIASES = ["posttext", "tweettext", "text", "content", "title", "body"]


def norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def find_col(headers: list, aliases: list, taken=()):
    """Exact normalised match wins; only then fall back to a substring hit.

    `taken` holds columns already claimed by an earlier field, so a loose
    alias like "url" can't steal the "Url clicks" column from `clicks`.
    """
    normed = {norm_header(h): h for h in headers if h not in taken}
    for alias in aliases:
        if alias in normed:
            return normed[alias]
    for alias in aliases:
        for key, original in normed.items():
            if alias in key:
                return original
    return None


def extract_date(value: str) -> str:
    m = re.search(r"\d{4}-\d{2}-\d{2}", value or "")
    if m:
        return m.group(0)
    m = re.search(r"(\d{2})[/.](\d{2})[/.](\d{4})", value or "")
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo}-{d}"
    return ""


def cmd_import(args):
    cfg = load_config()
    if args.account not in cfg["accounts"]:
        die(f"unknown account '{args.account}'. Known: {', '.join(cfg['accounts'])}")

    src = Path(args.csv)
    if not src.exists():
        die(f"no such file: {args.csv}")

    with src.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        rows = list(reader)
    if not headers:
        die(f"{args.csv} has no header row")

    mapping = {}
    for field, aliases in IMPORT_ALIASES.items():
        mapping[field] = find_col(headers, aliases, taken=set(mapping.values()))
    claimed = {c for c in mapping.values() if c}
    date_col = find_col(headers, DATE_ALIASES, taken=claimed)
    url_col = find_col(headers, URL_ALIASES, taken=claimed | {date_col})
    id_col = find_col(headers, ID_ALIASES, taken=claimed | {date_col, url_col})
    text_col = find_col(headers, TEXT_ALIASES,
                        taken=claimed | {date_col, url_col, id_col})

    print("COLUMN MAPPING")
    for field, col in mapping.items():
        print(f"  {field:<18} <- {col or '(not found, will be 0)'}")
    for label, col in (("date", date_col), ("url", url_col),
                       ("slug from", id_col or text_col)):
        print(f"  {label:<18} <- {col or '(not found)'}")
    print()

    existing = {r["slug"] for r in read_csv(POSTS_CSV, POST_FIELDS)}
    staged, skipped, undated = [], 0, 0

    for row in rows:
        post_id = (row.get(id_col) or "").strip() if id_col else ""
        text = (row.get(text_col) or "").strip() if text_col else ""
        if text and post_id:
            # Readable in reports, still unique per post.
            slug = f"{slugify(text)[:48]}-{re.sub(r'[^a-zA-Z0-9]', '', post_id)[-6:]}"
        elif text:
            slug = slugify(text[:60])
        elif post_id:
            slug = slugify(post_id)
        else:
            skipped += 1
            continue
        if not slug or slug == "untitled":
            skipped += 1
            continue
        if slug in existing:
            skipped += 1
            continue

        date = extract_date(row.get(date_col, "")) if date_col else ""
        if not date:
            undated += 1
            date = args.date or today()

        out = {
            "date": date,
            "account": args.account,
            "platform": args.platform,
            "slug": slug,
            "url": (row.get(url_col) or "").strip() if url_col else "",
            "notes": args.topic or "",
        }
        for field, col in mapping.items():
            out[field] = int(num(re.sub(r"[,\s]", "", row.get(col, "")))) if col else 0
        staged.append(out)
        existing.add(slug)

    if args.dry_run:
        for row in staged[:10]:
            print(f"  {row['date']}  {row['impressions']:>8,} impr  "
                  f"{row['likes']:>6,} likes  {row['slug']}")
        if len(staged) > 10:
            print(f"  ... and {len(staged) - 10} more")
        print(f"\ndry run: {len(staged)} would import, {skipped} skipped "
              f"(duplicate or unidentifiable)")
        return 0

    for row in staged:
        append_csv(POSTS_CSV, POST_FIELDS, row)
    print(f"imported {len(staged)} row(s) into {rel(POSTS_CSV)}")
    if skipped:
        print(f"skipped {skipped} (already present, or no id/text column to key on)")
    if undated:
        print(f"note: {undated} row(s) had no parsable date, dated {args.date or today()}")
    print("\nnow run: python3 scripts/sm.py report")
    return 0


# --------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="sm", description="social ops for this repo")
    sub = p.add_subparsers(dest="cmd")

    n = sub.add_parser("new", help="create a draft")
    n.add_argument("account")
    n.add_argument("title")
    n.add_argument("--type", default="tweet", help="tweet, thread, reddit, ... (matches templates/)")
    n.add_argument("--platform")
    n.add_argument("--scheduled", help="YYYY-MM-DD")
    n.add_argument("--topic")
    n.set_defaults(func=cmd_new)

    l = sub.add_parser("list", aliases=["ls"], help="list posts")
    l.add_argument("--account")
    l.add_argument("--status", choices=STATUSES)
    l.add_argument("--platform")
    l.set_defaults(func=cmd_list)

    d = sub.add_parser("due", help="what is scheduled or overdue")
    d.add_argument("--account")
    d.add_argument("--days", type=int, default=7)
    d.set_defaults(func=cmd_due)

    m = sub.add_parser("move", help="move a post between drafts/queue/posted")
    m.add_argument("path")
    m.add_argument("status", choices=STATUSES)
    m.add_argument("--url", help="live url, when moving to posted")
    m.add_argument("--date", help="post date, defaults to today")
    m.set_defaults(func=cmd_move)

    li = sub.add_parser("lint", help="check front-matter and length limits")
    li.add_argument("--account")
    li.add_argument("--strict", action="store_true", help="exit 1 on problems (for CI)")
    li.set_defaults(func=cmd_lint)

    lg = sub.add_parser("log", help="record performance for a post")
    lg.add_argument("slug")
    for field in METRIC_FIELDS:
        lg.add_argument(f"--{field.replace('_', '-')}", dest=field, type=int, default=0)
    lg.add_argument("--url")
    lg.add_argument("--notes", help="topic tag, used to group in reports")
    lg.add_argument("--date")
    lg.set_defaults(func=cmd_log)

    s = sub.add_parser("snapshot", help="record a follower count")
    s.add_argument("account")
    s.add_argument("platform")
    s.add_argument("followers", type=int)
    s.add_argument("--date")
    s.set_defaults(func=cmd_snapshot)

    r = sub.add_parser("report", help="what is working")
    r.add_argument("--account")
    r.add_argument("--since", help="YYYY-MM-DD")
    r.add_argument("--top", type=int, default=5)
    r.set_defaults(func=cmd_report)

    a = sub.add_parser("accounts", help="show accounts and pipeline counts")
    a.set_defaults(func=cmd_accounts)

    imp = sub.add_parser("import", help="bulk-load a platform analytics export")
    imp.add_argument("csv", help="path to the exported csv")
    imp.add_argument("--account", required=True)
    imp.add_argument("--platform", required=True)
    imp.add_argument("--topic", help="tag every imported row with this topic")
    imp.add_argument("--date", help="fallback date for rows with no parsable date")
    imp.add_argument("--dry-run", action="store_true",
                     help="show the column mapping and a preview, write nothing")
    imp.set_defaults(func=cmd_import)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
