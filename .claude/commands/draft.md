---
description: Draft post angles for an account on a topic
argument-hint: <account> <topic>
---

Draft content for account `$1` on the topic: $2

Do this in order:

1. Read `docs/voice/$1.md`.
2. Read the 10 most recent files in `content/$1/posted/` for register.
3. Run `python3 scripts/sm.py report --account $1 --top 8` and note which
   topics and formats actually performed.

Then give me **8 distinct angles**, not 8 rewrites of one. Each one:

- The post itself, ready to ship, at the right length for the platform
- One line underneath: why this angle, and what would make it fail

Rank them. Say which one you'd ship and which two you'd cut.

Obey every rule in CLAUDE.md under "Writing rules". If an angle needs a
number or example I haven't given you, mark it `[NEED: ...]` rather than
inventing one.

Do not create files yet. I'll tell you which ones to keep, then you run
`sm new` for those.
