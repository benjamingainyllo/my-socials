---
description: Weekly review across accounts
---

Run the weekly review:

1. `python3 scripts/sm.py report --since <date 7 days ago>`
2. `python3 scripts/sm.py due --days 7`
3. `python3 scripts/sm.py lint`
4. `git log --since="7 days ago" --oneline`

Then write me a short review, in this shape:

**What worked** - the top 2 posts, and your actual theory of why. Not
"it resonated". A mechanism: the hook, the format, the timing, the topic.

**What flopped** - the bottom 2, and what you'd change about them.

**Pipeline** - what's overdue, what's thin, which account is starving.

**Next week** - 3 concrete bets, each tied to something in the data above.

Be blunt. If a week was flat, say it was flat and say why rather than
finding a silver lining.
