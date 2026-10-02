# Content checklist — path to launch

Tracks what's left before the site is ready to go public: real images/
galleries, working video links, and real credits for every project. The
tables below are generated from the actual data in `site/data.py` (not
hand-maintained) — re-run the snippet at the bottom to refresh them after a
batch of updates.

## Workflow: do this here, not in Claude Design

This phase is content population (files and facts going into slots that
already exist), not design work — there's no layout left to explore, so
routing it through the Design canvas just adds an expensive re-export/diff
round-trip for no benefit. Work directly in this session instead:

- **Images** — attach files directly in chat, or give me a URL if they're
  already hosted somewhere (fastest — no upload needed). Say which project
  and which slot (poster / still / gallery).
- **Video** — paste the Vimeo or YouTube share link, same as we did for
  The Vicious Kind, Spork, and Hit & Run. I'll turn it into a working embed.
- **Research** (director, cast, press quotes, festival selections) — just
  ask me directly in this chat. I can search the web and did this earlier
  for Hit & Run, Kiss the Future, Call Me Lucky, etc.
- **Google Drive** — the original design chats mention a Drive folder you
  were organizing for these assets. If it still exists, connecting Google
  Drive to this session may let me pull files straight from it instead of
  you re-uploading everything by hand — worth checking before you do a big
  manual upload pass.

**Work in batches, one category at a time** (e.g. finish all of Scripted
before moving to Documentary) rather than jumping around — makes progress
easy to see and each push easy to verify before moving on.

## Priority order (fastest path to "ready to launch")

1. **Real credits for Scripted/Documentary (14 titles)** — the single
   biggest "looks unfinished" signal: these currently show literal
   placeholder text like "Add director name" on the live page. Highest
   visible impact for the least effort — usually just a few facts per
   title, often findable by web search alone, no new images needed.
2. **Poster art for the 9 titles missing it** — they currently fall back to
   a title-over-still-image card, which is a real design state (not
   broken), so this is lower urgency than #1, but adding real poster art
   closes the gap with the rest of Scripted/Documentary's grid.
3. **Gallery depth** — every project except The Vicious Kind is running on
   just the 2 stills that came from the original Squarespace scrape (or
   fewer). More real stills per project is the single highest-leverage
   visual upgrade once credits are sorted.
4. **Video embeds** — only 5 of 24 film titles have one. Nice to have, not
   blocking — most projects never had a trailer in the first place, and a
   project page without a video already reads fine (no empty black box).
5. **Commercial credits/galleries** — all 34 are still on defaults. Lower
   priority per your earlier call to deprioritize commercial/music-video
   research versus Scripted/Documentary — revisit once 1-4 are done.

Items 1-2 are what most affects how "finished" the site feels to a first-
time visitor. If you want to go live sooner rather than later, clearing
those for Scripted + Documentary is the real minimum bar — everything else
can keep improving after launch without looking unfinished.

## Status by project

Legend: **Poster** = real poster art on the Scripted/Documentary grid tile.
**Video** = a working trailer/Vimeo-or-YouTube embed on the project page.
**Gallery imgs** = how many real stills show in that project's gallery
(The Vicious Kind's 14 is the bar every other project is still short of).
**Real credits** = director/cast/press/festivals filled in, vs. the
"Add director name" style placeholder.

<!-- BEGIN GENERATED TABLE -->
### Scripted

| Project | Poster | Video | Gallery imgs | Real credits |
|---|---|---|---|---|
| The Vicious Kind | [x] | [x] | 14 | [x] |
| Hit & Run | [x] | [x] | 2 | [x] |
| Me + Her | [x] | [ ] | 2 | [x] |
| Almost Kings | [x] | [ ] | 2 | [x] |
| Spork | [x] | [x] | 2 | [x] |
| The Kid | [x] | [ ] | 2 | [ ] |
| De Puta Madre: A Love Story | [x] | [ ] | 2 | [ ] |
| Woman Child | [x] | [ ] | 2 | [ ] |
| God Bless America | [x] | [ ] | 2 | [ ] |
| House of Ideas | [x] | [ ] | 2 | [ ] |
| Misfits & Monsters | [x] | [ ] | 1 | [ ] |

### Documentary

| Project | Poster | Video | Gallery imgs | Real credits |
|---|---|---|---|---|
| Kiss the Future | [x] | [ ] | 2 | [x] |
| The Youth Governor | [x] | [ ] | 2 | [ ] |
| Fire on the Hill | [x] | [ ] | 2 | [x] |
| Call Me Lucky | [x] | [ ] | 2 | [x] |
| Microsoft Philanthropies - Mary Mwende | [ ] | [ ] | 2 | [ ] |
| Re:Purpose - Afro Beat | [ ] | [x] | 2 | [x] |
| Re:Purpose - Farriers | [ ] | [x] | 2 | [x] |

### Music Video

| Project | Poster | Video | Gallery imgs | Real credits |
|---|---|---|---|---|
| M. Rivers - Champion | [ ] | [ ] | 2 | [ ] |
| Lissie - Go Your Own Way | [ ] | [ ] | 2 | [ ] |
| Train - Bulletproof Picasso | [ ] | [ ] | 2 | [ ] |
| Jamie Joseph - Hit the Ground Running | [ ] | [ ] | 2 | [ ] |
| The Lady Tigra - Thing-a-Ling | [ ] | [ ] | 2 | [ ] |
| AWOLNATION - Burn It Down | [ ] | [ ] | 2 | [ ] |

### Commercial

| Project | Gallery imgs | Real credits |
|---|---|---|
| Microsoft - Be The Pilot | 2 | [ ] |
| T-Mobile - Oscars | 2 | [ ] |
| Microsoft - Co-Pilot | 2 | [ ] |
| T-Mobile - Home Internet | 2 | [ ] |
| T-Mobile - Snoop | 2 | [ ] |
| T-Mobile - Neighbors | 2 | [ ] |
| T-Mobile - Grandma | 2 | [ ] |
| Microsoft - Opportunity | 2 | [ ] |
| T-Mobile - Zach & Donald | 2 | [ ] |
| Carnival Cruise - Funderstruck | 2 | [ ] |
| Caterpillar - Do the Work | 2 | [ ] |
| T-Mobile - Misunderstandings | 2 | [ ] |
| Google / Samsung - Passport | 2 | [ ] |
| T-Mobile - iPhone 14 | 2 | [ ] |
| Triller - Tyson vs. Jones | 1 | [ ] |
| T-Mobile - Audition | 2 | [ ] |
| Invesco - QQQ | 1 | [ ] |
| T-Mobile - Mama | 2 | [ ] |
| Microsoft - Daisuke | 2 | [ ] |
| Apple - iPhone 11 | 2 | [ ] |
| KiwiCo - Believe | 2 | [ ] |
| Absolut - Awakening | 2 | [ ] |
| Fossil Firsts - Leslie Odom Jr. | 2 | [ ] |
| Microsoft - Creators | 2 | [ ] |
| Microsoft - Earth Day | 2 | [ ] |
| Rockstar - Back on Track | 2 | [ ] |
| Microsoft - Estella's Brilliant Bus | 2 | [ ] |
| Super Bowl '15 | 2 | [ ] |
| Alibaba - Get to Yes | 2 | [ ] |
| Quaker - Who Do You Put 1st? | 2 | [ ] |
| Asus - A Father's Touch | 2 | [ ] |
| Subaru - Andres Amador | 2 | [ ] |
| Dodgers - Stadium Intro | 2 | [ ] |
| Google - The Big Presentation | 2 | [ ] |
<!-- END GENERATED TABLE -->

## Regenerating this table

After a batch of `data.py` updates, regenerate the tables above with:

```
cd site && python3 - << 'PYEOF'
import sys; sys.path.insert(0, '.')
from data import CATS
from build import build_all

all_p = build_all()

def status(proj):
    has_poster = bool(proj.get('posterImage')) or bool(proj.get('comingSoon'))
    has_video = bool(proj.get('videoEmbed'))
    gallery = proj.get('galleryImages') or [u for u in (proj.get('image2'), proj.get('image3')) if u]
    has_real_credits = bool(proj.get('overrideCredits'))
    return has_poster, has_video, len(gallery), has_real_credits

for cat in CATS:
    is_commercial = cat['key'] == 'commercial'
    print('### ' + cat['label'] + '\n')
    print('| Project | Gallery imgs | Real credits |' if is_commercial
          else '| Project | Poster | Video | Gallery imgs | Real credits |')
    print('|---|---|---|' if is_commercial else '|---|---|---|---|---|')
    for i, p in enumerate(cat['projects']):
        proj = all_p[cat['key'] + '-' + str(i)]
        hp, hv, gn, hc = status(proj)
        if is_commercial:
            print('| %s | %d | %s |' % (proj['title'], gn, '[x]' if hc else '[ ]'))
        else:
            print('| %s | %s | %s | %d | %s |' % (
                proj['title'], '[x]' if hp else '[ ]', '[x]' if hv else '[ ]', gn, '[x]' if hc else '[ ]'))
    print()
PYEOF
```
