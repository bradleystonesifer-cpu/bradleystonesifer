# bradleystonesifer.com — static site

Implementation of the "Bradley Stonesifer Site" Claude Design canvas
(see `../project/Bradley Stonesifer Site.dc.html` and `../chats/` for the
original design source and decision history). Plain HTML/CSS/JS, no build
tool required to serve it — everything in this folder is deployable as-is
to any static host (Netlify, Vercel, GitHub Pages, S3, etc.).

## Structure

- `index.html`, `about.html`, `commercial.html` — top-level pages
- `films/scripted.html`, `films/documentary.html`, `films/music-video.html` — category pages
- `films/<slug>.html` — one page per Scripted/Documentary/Music Video project
- `commercial/<slug>.html` — one page per commercial project
- `assets/css/style.css` — the whole design system (colors, type, layout)
- `assets/js/main.js` — sticky header fade, click-to-play video embeds, Vimeo
  thumbnail fetch, footer "Contact" deep link
- `assets/images/` — locally-hosted poster art and the About page photo

## Editing content

Don't hand-edit the generated `.html` files — edit `data.py` (project list,
credits, video embeds, poster overrides) and re-run:

```
python3 build.py
```

This regenerates every page from scratch. `build.py` also holds the credit
auto-linking rules (IMDb/festival/press search links), laurel parsing, and
gallery layout logic.

## Known gaps (carried over from the design source)

Per the design chats, these six titles are still missing full director/
cast/festival/press research: **The Kid, De Puta Madre, Woman Child, House
of Ideas, Misfits & Monsters, The Youth Governor.** Their pages render with
the same placeholder credit fields as any project with no `overrideCredits`
in `data.py` — fill those in as the research comes in.

Images are hotlinked from `images.squarespace-cdn.com` (the existing
Squarespace site) rather than re-hosted here, and video embeds point at
the original Vimeo/YouTube IDs — both by explicit choice, so the old site
stays the source of truth for that media until it's replaced.
