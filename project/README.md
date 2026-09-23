# Handoff: Bradley Stonesifer — Cinematographer Portfolio

## Overview
Portfolio site for cinematographer Bradley Stonesifer. Home collage, film category pages (Scripted, Documentary, Music Video), Commercial grid, per-project detail pages with trailer + credits + press, and an About page with bio and representation contact.

## About the Design Files
`Bradley Stonesifer Site.dc.html` is a **design reference built in HTML**: a working prototype showing the intended look and behavior. It is not production code to ship. Recreate it in the target stack. If there's no codebase yet, a static-friendly framework (Next.js / Astro) with a simple project data file is a good fit.

To view the prototype: serve this folder (e.g. `npx serve .`) and open `Bradley Stonesifer Site.dc.html`. `support.js` is the prototype's runtime only and isn't needed in production.

All project data (titles, credits, loglines, press, video embeds, stills, posters) lives in the logic class near the bottom of the file (`_all`, `applyOverrides()`, `_collageSpec`). Pull it into a `projects.json` / CMS.

## Fidelity
**High-fidelity.** Final colors, type, spacing and interactions. Match pixel-for-pixel.

## Design Tokens
Colors
- Page ground: `#0E0C0A`
- Hero glow (radial, top-center, 1100×1400 ellipse): `#4a3016` 0% → `#241a0e` 30% → `#0E0C0A` 62%
- Panel/menu brown: `#17130F`
- Ink (primary text): `#EDE6D8`
- Muted text / nav: `#A79E8C`
- Accent (amber): `#C88A3E`
- Hairlines: `rgba(237,230,216,0.14)`
- Film grain overlay: SVG fractalNoise, opacity 0.05, mix-blend overlay

Type (Google Fonts)
- Name / wordmark: **Bebas Neue** 400, uppercase. Hero 78px / 0.92, tracking 0.11em. Header 26px / 1, tracking 0.09em
- Labels / eyebrows: **IBM Plex Mono** 500, uppercase, tracking 0.12–0.34em, 9–20px
- Body / nav: **Inter** 300–600. Nav 12px, tracking 0.12em, uppercase
- Fraunces is loaded and used for some display titles (see file)

Other
- Radius: 2px on all tiles/menus
- Menu shadow: `0 12px 30px rgba(0,0,0,0.3)`
- Page side gutter: `clamp(10px, 1.4vw, 28px)`
- Link hover: opacity 0.62
- Layout bleeds edge-to-edge on large monitors (no max-width container)

## Screens

### Header
- **Home:** centered marquee. Eyebrow "35mm · 16mm · digital" (mono 10px accent), name (Bebas 78px), "Cinematographer" (mono 20px accent). Right-aligned nav row below with a bottom hairline.
- **Inner pages:** sticky compact bar. Name (Bebas 26px) + "Cinematographer" (mono 9px) on the left links home. Nav on the right. Behind it, a masked gradient fades in on scroll (`headerOpacity`).
- **Nav:** Films (hover dropdown: Scripted / Documentary / Music Video), Commercial, About.

### Home — collage
- 40-tile responsive collage built from `_collageSpec`. Each entry is `IMG(projectKey, slot, aspect, span)`.
- Mix of 16:9 stills and 2:3 posters (Vicious Kind, Hit & Run, Misfits & Monsters, Kiss the Future, Call Me Lucky, Fire on the Hill).
- The collage is data-driven, so tiles update when project data changes. Every tile links to its project.

### Scripted / Documentary
- Title plus a left-aligned sub-nav under it.
- 4-column grid (`repeat(4, minmax(0,1fr))`, gap `clamp(10px,1.4vw,24px)`) of **2:3 tiles**.
- If a project has a poster, show it full-bleed with no overlay.
- If it doesn't, show the project still cropped to 2:3 with the title/laurel overlay.
- *House of Ideas* is a "coming soon" card: title (uppercase) above the contained artwork, "Coming soon" (mono 11px accent) below, on `#17130F`.
- Scripted order: Vicious Kind, Hit & Run, Me + Her, Spork, Woman Child, God Bless America, House of Ideas, Misfits & Monsters, The Kid, De Puta Madre, Almost Kings.
- Documentary order: Kiss the Future, Call Me Lucky, Fire on the Hill, The Youth Governor, then the rest.

### Music Video
- Triptych rows of stills per project.

### Commercial
- Grid of stills.

### Project detail
- Back link pinned at `top: 34px`, left, above the title.
- 3-column grid `0.85fr / 2fr / 0.85fr`, gap `clamp(16px,2vw,30px)`, **all columns vertically centered** on each other:
  - **Left:** credits (Director, Lead Actors, Producers, Subjects, etc.). Names can link out.
  - **Center:** trailer. It shows a poster/thumbnail first and swaps to a Vimeo/YouTube iframe with autoplay on click. Aspect is 16:9 by default (Spork uses 2.35:1). Optional "Selects" second video. Vimeo thumbnails come from the oEmbed API. YouTube falls back to the project still.
  - **Right:** logline at the top, press quotes, and a "Watch Now" button when an external link exists.
- Projects without video render no player (no empty black box).
- There is no tech-spec strip under the player (removed).

### About
- Portrait, bio, and a representation contact block. The footer "Contact" link scrolls to this block.

## Interactions
- Client-side view switching (home / category / project / about). Use real routes in production (`/films/scripted`, `/project/[slug]`, etc.).
- Films dropdown opens on hover.
- Clicking a video starts playback in place.
- Pages load scrolled to the top.

## Assets
- `uploads/` contains the poster art supplied by the client.
  - Scripted posters (`narrative-*`):
    - `posters-…69yy.jpg`: Vicious Kind
    - `…bis9.jpg`: Hit & Run
    - `ME+HER.jpg`
    - `almost kings.jpg`
    - `spork.jpg`
    - `theKid.jpg`
    - `DePutaMadre.jpg`
    - `pasted-…png`: Woman Child
    - `…bd9q.jpg`: God Bless America
    - `misfits and monsters.jpg`
    - `house of Ideas.avif`
  - Documentary posters (`documentary-*`):
    - `KTF.jpg`
    - `youth governor.jpg`
    - `fire on the hill.jpg`
    - `Call me Lucky.jpg`
- Stills are hotlinked from the client's existing Squarespace CDN. Download them and self-host before launch.
- Videos are Vimeo/YouTube embeds (URLs are in the project data).

## Files
- `Bradley Stonesifer Site.dc.html`: full prototype (template + logic + data)
- `support.js`: prototype runtime (reference only)
- `uploads/`: poster assets
