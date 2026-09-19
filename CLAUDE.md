# Working in this repo

This is Benjamin's social ops repo. Content lives as markdown, performance
lives as CSV, and `scripts/sm.py` is the only tool. No dependencies, no build.

## Before you draft anything

1. Read `docs/voice/<account>.md`. That file is the spec, not a suggestion.
2. Read the last ~10 files in `content/<account>/posted/` to match register.
3. Run `python3 scripts/sm.py report --account <account>` to see what actually
   performed. Pitch toward topics with a high ER, not toward what sounds smart.

## Creating content

Always go through the CLI so front-matter stays valid:

```
python3 scripts/sm.py new scaile "aeo vs seo" --type thread --topic aeo
```

Then edit the file it prints. Never hand-create files in `content/`.

Move it along as it progresses:

```
python3 scripts/sm.py move content/scaile/drafts/2026-09-19-aeo-vs-seo.md queue
python3 scripts/sm.py move content/scaile/queue/2026-09-19-aeo-vs-seo.md posted --url https://x.com/...
```

Run `python3 scripts/sm.py lint` before committing. It catches over-length
tweets, missing front-matter, and queued posts with no date.

## Loading performance data

If Benjamin hands you a platform analytics export, don't transcribe it:

```
python3 scripts/sm.py import <file.csv> --account scaile --platform x --dry-run
```

Check the column mapping it prints, then run it without `--dry-run`. It
dedupes on re-import, so running it twice is safe.

## Writing rules

These apply to every draft you produce, for every account.

- Write like a person who is tired of the topic, not excited about it.
- Strongest line first. If the first line needs the second line to make
  sense, delete the first line.
- Specifics over claims. A number, a name, a date, or don't say it.
- One idea per post. If there are two, that's two posts.
- No em-dashes. No "it's not X, it's Y". No rhetorical questions as hooks.
- No hashtags, no emoji bullets, no "Let's dive in", no "Here's the thing".
- If a line could appear on any brand's account, cut it.
- Reddit: answer first, context second, and never lead with the product.
  Disclose the SCAILE affiliation in plain words if it's relevant.

## Drafting volume

When asked for content, produce 5-10 distinct angles, not 3 variations of
one angle. Different angles means different claims, not different wording.
Mark the one you'd actually ship and say why in one line.

## Feedback

Benjamin wants the flaw named. If a draft is weak, say which line is weak
and what it should be instead. Don't pad with what works.
