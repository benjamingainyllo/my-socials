# my-socials

Content, calendar, and performance data for the accounts I run. One CLI,
no dependencies, no build step. Python 3.9+.

## Layout

```
config.json              accounts and platform limits - edit this first
content/<account>/
  drafts/                being written
  queue/                 approved, waiting on its scheduled date
  posted/                shipped, with the live url in front-matter
analytics/
  posts.csv              per-post performance
  followers.csv          follower counts over time
docs/voice/<account>.md  the voice spec for each account
templates/               starting points for each post type
scripts/sm.py            the CLI
.claude/commands/        /draft, /replies, /reddit, /weekly
```

## Daily loop

```bash
alias sm='python3 scripts/sm.py'

sm due                              # what's scheduled or overdue
sm new scaile "aeo vs seo" --type thread --topic aeo
# ...write it...
sm lint                             # catch over-length tweets, missing fields
sm move content/scaile/drafts/2026-09-19-aeo-vs-seo.md queue --date 2026-09-22
sm move content/scaile/queue/2026-09-19-aeo-vs-seo.md posted --url https://x.com/...
```

## Weekly loop

```bash
# bulk: export analytics from X/LinkedIn/Reddit, then
sm import ~/Downloads/x-analytics.csv --account scaile --platform x --dry-run
sm import ~/Downloads/x-analytics.csv --account scaile --platform x

# or one post at a time
sm log 2026-09-19-aeo-vs-seo --impressions 41000 --likes 380 --replies 44 --reposts 61

sm snapshot scaile x 3120
sm report --since 2026-09-12
```

`import` figures out the column names itself, so a raw platform export works
without editing. It skips rows already in the CSV, so re-importing the same
export is safe. Always `--dry-run` first to check the column mapping.

`report` gives you per-account rollups, top posts by engagement rate and by
reach, performance grouped by topic, and follower deltas. That's the input
for what to write next.

## With Claude Code

`CLAUDE.md` holds the writing rules and the workflow, so any session picks
them up automatically. Four slash commands:

| command | what it does |
| --- | --- |
| `/draft <account> <topic>` | 8 distinct angles, ranked, with failure modes |
| `/replies <account> <post>` | 6 reply angles at different postures |
| `/reddit <account> <sub> <topic>` | 3 versions by involvement level, with removal risk |
| `/weekly` | reads the data and writes the honest review |

They read the voice doc and the analytics before writing, which is the whole
point of keeping this in one repo.

## Automation

- **lint content** - runs `sm lint --strict` on every push touching content.
- **queue digest** - weekday mornings, updates a single open issue with
  what's due. Edit the cron in `.github/workflows/queue-digest.yml`, or
  delete the file to turn it off.

## First things to do

1. Fill in the `TODO` handles in `config.json`. Add any staff or client
   accounts you want tracked here.
2. Paste real posts into the `Reference posts` section of `docs/voice/*.md`.
   Everything else in those files is filled in.
3. Export your analytics from each platform and run `sm import` on the file.
   Reports need ~30 posts before the topic breakdown means anything.
