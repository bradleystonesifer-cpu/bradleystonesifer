#!/usr/bin/env python3
"""Static site generator for the Bradley Stonesifer cinematographer portfolio.

Ported (not framework-copied) from the Claude Design canvas source at
project/Bradley Stonesifer Site.dc.html — same visual system, real
multi-page URLs instead of the design tool's client-side view switching.
Run `python3 build.py` from this directory to (re)generate every page.
"""
import json
import os
import re
import shutil
import urllib.parse

from data import CATS, OVERRIDES, POSTERS, COLLAGE_SPEC, CATEGORY_ORDER, VIDEOS

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
FESTIVAL_DOMAINS = {
    'sundance': 'sundance.org', 'tribeca': 'tribecafilm.com', 'sxsw': 'sxsw.com',
    'cannes': 'festival-cannes.com', 'tiff': 'tiff.net', 'toronto': 'tiff.net', 'berlinale': 'berlinale.de',
}
PRESS_DOMAINS = {
    'variety': 'variety.com', 'indiewire': 'indiewire.com', 'hollywood reporter': 'hollywoodreporter.com',
    'vulture': 'vulture.com', 'deadline': 'deadline.com', 'rolling stone': 'rollingstone.com',
}
CAT_FILENAME = {'narrative': 'scripted.html', 'documentary': 'documentary.html', 'music_video': 'music-video.html'}
# Commercial pages that are video-only — no gallery section/heading even if
# still images exist in their data (those are used by the triptych thumbnail
# on the Commercial category page, not shown as a stills gallery here).
VIDEO_ONLY_SLUGS = {'t-mobile-iphone-14', 't-mobile-audition', 'google-the-big-presentation'}
# Per-page .gallery-bottom column override (desktop only) for pages whose
# bottom-grid image count doesn't divide evenly into the default 4 columns,
# picked so it divides evenly instead — see render_detail_page(). Only
# applies to pages still on the old fixed-crop gallery layout (currently
# just almost-kings, which is excluded from the new native-aspect-ratio
# engine — see GALLERY_NEW_LAYOUT_EXCLUDE in detail_data()); pages on the
# new engine always keep 4 columns regardless of row evenness, per Bradley.
GALLERY_BOTTOM_COLS = {
    'almost-kings': 3,  # 21 images: 7 rows of 3
}
# 1-based galleryImages position a page's bottom-grid/mobile-grid cells
# switch from object-fit: cover to contain, so wide-format images that
# don't match the gallery's shared --ar (set from image 1 — see
# detail_data()) show in full instead of being cropped to fit a box
# shaped for the rest of the gallery. Kiss the Future's images 40-45 are
# 4-camera 2x2 composites (~16:9) among otherwise ~2:1 interview stills.
GALLERY_CONTAIN_FROM = {
    'kiss-the-future': 40,
}

# ---------------------------------------------------------------- helpers --

def esc(s):
    if s is None:
        return ''
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))


def slugify(title):
    s = title.lower().replace('&', 'and').replace('+', 'plus').replace('/', ' ')
    s = re.sub(r"['\".]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or 'project'


def g_search(q):
    return 'https://www.google.com/search?q=' + urllib.parse.quote(q)


def link_for(k, v, title):
    if not v or v.lower().startswith('add '):
        return None
    lower = v.lower()
    first_name = v.split(',')[0].strip()
    if k in ('Director', 'Lead Actors', 'Notable Talent'):
        return g_search(first_name + ' imdb')
    if k == 'Production Company':
        return g_search(v + ' film production company')
    if k == 'Notable Festivals':
        for key, domain in FESTIVAL_DOMAINS.items():
            if key in lower:
                return g_search('site:' + domain + ' "' + title + '"')
        return None
    if k == 'Press':
        for key, domain in PRESS_DOMAINS.items():
            if key in lower:
                return g_search('site:' + domain + ' "' + title + '"')
        return None
    return None


def with_links(arr, title):
    out = []
    for cr in arr:
        href = cr.get('href') or link_for(cr['k'], cr['v'], title)
        item = dict(cr, href=href)
        if cr['k'] in ('Lead Actors', 'Actors', 'Notable Talent'):
            names = [n.strip() for n in cr['v'].split(',') if n.strip()]
            # actorLinks: optional {name: url} overrides for a specific
            # actor's own site instead of the auto-generated IMDb search —
            # e.g. a director/actor whose own name should link to their
            # own site on this row too (link_for('Director', ...) below
            # is still the default for every other name). A name mapped
            # to None/'' explicitly suppresses the link instead (a name
            # left out of the dict entirely still gets the IMDb default).
            overrides = cr.get('actorLinks') or {}
            actors = []
            for i, name in enumerate(names):
                ahref = overrides[name] if name in overrides else link_for('Director', name, title)
                actors.append({'name': name, 'href': ahref, 'last': i < len(names) - 1})
            item['isActorList'] = True
            item['actors'] = actors
        else:
            item['isActorList'] = False
        out.append(item)
    return out


def group_credits(arr):
    by_key = {cr['k']: cr for cr in arr}
    groups = []
    if 'Director' in by_key and 'Production Company' in by_key:
        groups.append([by_key['Director'], by_key['Production Company']])
    else:
        if 'Director' in by_key:
            groups.append([by_key['Director']])
        if 'Production Company' in by_key:
            groups.append([by_key['Production Company']])
    for k in ('Client', 'Agency'):
        if k in by_key:
            groups.append([by_key[k]])
    used = {'Director', 'Production Company', 'Client', 'Agency'}
    for cr in arr:
        if cr['k'] not in used and not cr['k'].startswith('Press'):
            groups.append([cr])
    return groups


def press_quotes(arr):
    return [cr for cr in arr if cr['k'].startswith('Press')]


def laurels_for(proj):
    credits = proj.get('overrideCredits') or []
    cr = next((c for c in credits if c['k'] == 'Notable Festivals'), None)
    if not cr:
        return []
    out = []
    for seg in cr['v'].split(';'):
        seg = seg.strip()
        m = re.search(r'\(([^)]+)\)', seg)
        sub = m.group(1) if m else ''
        name = re.sub(r'\([^)]*\)', '', seg).strip()
        yr = re.search(r"'(\d{2})\s*$", name)
        year = "'" + yr.group(1) if yr else ''
        name = re.sub(r"'(\d{2})\s*$", '', name).strip()
        name = re.sub(r'\s+(Film\s+)?Festival$', '', name, flags=re.I).strip()
        sub_final = sub or year
        if name:
            out.append({'name': name, 'sub': sub_final, 'hasSub': bool(sub_final)})
    return out[:3]


def vimeo_id(embed_url):
    if not embed_url:
        return None
    m = re.search(r'video/(\d+)', embed_url)
    return m.group(1) if m else None


# ------------------------------------------------------------- data build --

def build_all():
    all_projects = {}
    for cat in CATS:
        for i, p in enumerate(cat['projects']):
            key = cat['key'] + '-' + str(i)
            merged = dict(p, key=key, groupLabel=cat['label'], section=cat['section'], catKey=cat['key'])
            overrides = OVERRIDES.get(key)
            if overrides:
                merged.update(overrides)
            poster = POSTERS.get(key)
            if poster and 'posterImage' not in (overrides or {}):
                merged['posterImage'] = poster
            all_projects[key] = merged

    # slug + href per project, unique within its folder
    used_slugs = {'films': set(), 'commercial': set()}
    for cat in CATS:
        folder = 'films' if cat['section'] == 'films' else 'commercial'
        for i, p in enumerate(cat['projects']):
            key = cat['key'] + '-' + str(i)
            base = slugify(p['title'])
            slug = base
            n = 2
            while slug in used_slugs[folder]:
                slug = base + '-' + str(n)
                n += 1
            used_slugs[folder].add(slug)
            all_projects[key]['slug'] = slug
            all_projects[key]['href'] = folder + '/' + slug + '.html'

    return all_projects


def category_display_lists(all_projects):
    """Per-category project lists in on-site display order (poster grid /
    triptych rows), matching the `order` reorder + fallback in renderVals()."""
    groups = {}
    for cat in CATS:
        if cat['section'] != 'films':
            continue
        projects = [all_projects[cat['key'] + '-' + str(i)] for i in range(len(cat['projects']))]
        order = CATEGORY_ORDER.get(cat['key'])
        if order:
            reordered = [projects[i] for i in order if i < len(projects)]
            rest = [p for i, p in enumerate(projects) if i not in order]
            projects = reordered + rest
        groups[cat['key']] = {'label': cat['label'], 'no': cat['no'], 'projects': projects,
                               'isGrid': cat['key'] != 'music_video', 'isTriptych': cat['key'] == 'music_video'}
    return groups


def next_project_map(all_projects, groups):
    """slug -> next project, in the same order its own category page lists
    projects (films: the reordered `groups` lists; commercial: CATS' plain
    order, matching render_commercial_page), wrapping from the last project
    back to the first. comingSoon projects don't have a real page yet, so
    they're skipped in the rotation rather than linked to as "next"."""
    next_map = {}

    def link_up(projects):
        eligible = [p for p in projects if not p.get('comingSoon')]
        n = len(eligible)
        if n < 2:
            return
        for i, p in enumerate(eligible):
            next_map[p['slug']] = eligible[(i + 1) % n]

    for cat_key in ('narrative', 'documentary', 'music_video'):
        link_up(groups[cat_key]['projects'])
    commercial_cat = next(c for c in CATS if c['key'] == 'commercial')
    link_up([all_projects['commercial-' + str(i)] for i in range(len(commercial_cat['projects']))])

    return next_map


def poster_tile_data(p):
    cs = bool(p.get('comingSoon'))
    # "poster" is the same kind of real-poster-file field as "posterImage"
    # (which comes from the POSTERS/OVERRIDES map) — just settable directly
    # on a project's own data entry. Either one switches the tile off the
    # still-with-title fallback with no layout changes.
    poster_file = p.get('poster') or p.get('posterImage') or ''
    # posterThumb (optional) swaps in a smaller file for this grid tile only
    # — the detail page's own poster column keeps the full-res posterImage.
    tile_image = '' if cs else (p.get('posterThumb') or poster_file or p.get('image') or '')
    return {
        'comingSoon': cs,
        'hasTileImage': not cs and bool(tile_image),
        'tileImage': tile_image,
        'noPoster': (not cs) and not poster_file,
        'artImage': p.get('comingSoonImage') or '',
        'laurels': laurels_for(p),
    }


def local_image_path(url):
    """Absolute filesystem path for a root-relative local image path, or
    None for an external (http/https) URL — those can't be read with PIL
    without a network fetch, so callers fall back to a default ratio."""
    if not url or url.startswith('http://') or url.startswith('https://'):
        return None
    return os.path.join(SITE_DIR, url)


def image_aspect_ratio(url, default):
    """width/height of a local image via PIL, or `default` if the path is
    external, missing, or unreadable."""
    path = local_image_path(url)
    if not path:
        return default
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
            if h:
                return w / h
    except Exception:
        pass
    return default


# Slugs explicitly kept on the old fixed-crop 3-per-side gallery layout even
# though they have 8+ galleryImages — Almost Kings already has its own
# hand-tuned bottom-grid column count (GALLERY_BOTTOM_COLS) for its
# processed-to-2.35:1 stills, so it's excluded from the new native-aspect-
# ratio engine to avoid relayouting an already-finished page.
GALLERY_NEW_LAYOUT_EXCLUDE = {'almost-kings'}

# Desktop click-to-enlarge lightbox (reuses the mobile gm-lightbox JS/data).
# Previously opt-in per project (a slug allowlist); now on for every project
# with a gallery — main.js's desktop wiring is a no-op on any page where
# render_gallery() finds no data-gm-index cells, so this is safe everywhere.


def detail_data(p):
    title = p['title']
    raw_credits = p.get('overrideCredits') or []
    linked = with_links(raw_credits, title)

    gallery_source = p.get('galleryImages') or [u for u in (p.get('image2'), p.get('image3')) if u]
    gallery_alts = p.get('galleryAlts')
    if gallery_alts:
        # (url, alt) pairs when per-image alt text is supplied; every other
        # project keeps plain URL strings, unaffected.
        gallery_source = [(u, gallery_alts[i] if i < len(gallery_alts) else title)
                           for i, u in enumerate(gallery_source)]
    gallery = list(gallery_source)

    # 8+ galleryImages: stills keep their native aspect ratio (4 per side,
    # interleaved 1/3/5/7 left, 2/4/6/8 right) and the poster column is
    # sized to match the resulting side-stack height, instead of the old
    # fixed 3-per-side layout that force-cropped every still to whatever
    # shape fit the poster's height.
    gallery_ar = None
    gallery_pc = None
    use_new_layout = len(gallery) >= 8 and p.get('slug') not in GALLERY_NEW_LAYOUT_EXCLUDE
    if use_new_layout:
        first_url = _gallery_item(gallery[0], title)[0]
        gallery_ar = image_aspect_ratio(first_url, 2.39)
        poster_ar = image_aspect_ratio(p.get('posterImage') or p.get('image'), 2 / 3)
        gallery_pc = 4 * poster_ar / gallery_ar if gallery_ar else 1.1
        gallery_left = gallery[0:8:2]   # images 1,3,5,7
        gallery_right = gallery[1:8:2]  # images 2,4,6,8
        gallery_bottom = gallery[8:]
        gallery_left_idx = list(range(0, 8, 2))
        gallery_right_idx = list(range(1, 8, 2))
        gallery_bottom_idx = list(range(8, len(gallery)))
    else:
        if len(gallery) > 3:
            gallery[1], gallery[3] = gallery[3], gallery[1]
        gallery_left = gallery[0:3]
        gallery_right = gallery[3:6]
        gallery_bottom = gallery[6:]
        # gallery itself was just reordered above (not a fresh slice), so
        # galleryFlat already reflects it — positions line up 1:1.
        gallery_left_idx = list(range(0, 3))
        gallery_right_idx = list(range(3, 6))
        gallery_bottom_idx = list(range(6, len(gallery)))

    return {
        'creditGroups': group_credits(linked) if linked else [],
        'pressQuotes': press_quotes(linked) if linked else [],
        'logline': p.get('logline') or '',
        'posterImage': p.get('posterImage') or p.get('image'),
        'galleryLeft': gallery_left,
        'galleryRight': gallery_right,
        'galleryBottom': gallery_bottom,
        'galleryLeftIdx': gallery_left_idx,
        'galleryRightIdx': gallery_right_idx,
        'galleryBottomIdx': gallery_bottom_idx,
        'galleryAr': gallery_ar,
        'galleryPc': gallery_pc,
        'galleryFlat': gallery,
        # Desktop click-to-enlarge, on for every project: the click-to-enlarge
        # mobile lightbox, reused as-is, just triggered from the desktop
        # gallery's own cells instead of the phone-width grid.
        'desktopLightbox': True,
        'backHref': CAT_FILENAME[p['catKey']] if p['section'] == 'films' else '../commercial.html',
        'backLabel': 'Back',
    }


def slot_url(all_projects, key, slot):
    p = all_projects[key]
    if slot == 'image':
        return p.get('image', '')
    if slot == 'image2':
        return p.get('image2', '')
    if slot == 'image3':
        return p.get('image3', '')
    if slot.startswith('gallery:'):
        idx = int(slot.split(':')[1])
        gi = p.get('galleryImages') or []
        return gi[idx] if idx < len(gi) else ''
    if slot == 'poster':
        return p.get('posterImage') or p.get('image', '')
    return ''


# ------------------------------------------------------ homepage collage --

SCRIPTED_POOL_MIN_GALLERY = 8    # narrative projects need this many galleryImages to join the pool
SCRIPTED_POOL_MIN_WIDTH = 1500   # skip frames narrower than this (low-res / 2.35 reel scans)

# Every non-poster COLLAGE_SPEC entry is one of these — matches the pool
# key build_collage_pools() returns it under.
COLLAGE_TYPES = ('scripted', 'commercial', 'documentary', 'music_video')
# When a slot's own type has no unused project left, try the other types
# in this fixed order (skipping the slot's own type, already tried).
COLLAGE_FALLBACK_ORDER = ('scripted', 'commercial', 'documentary', 'music_video')


def collage_poster_keys():
    """The project keys COLLAGE_SPEC uses as fixed posters. Every one of
    the 32 collage tiles is a distinct project — a poster tile already
    *is* that project, so its key is excluded from every pool below
    (never drawn again as a random still elsewhere on the page). Misfits
    & Monsters is the one exception: when its own series key is a poster,
    its *episodes* are still pool-eligible, since the spec treats each
    episode as its own project separate from the series poster — that
    works for free here because each episode gets its own synthetic key
    (see build_collage_pools), never the series key itself."""
    return {key for ttype, key, _ratio, _span in COLLAGE_SPEC if ttype == 'poster'}


def build_collage_pools(all_projects):
    """Pools for the randomized homepage collage, keyed by COLLAGE_TYPES —
    one entry per *project* (not per still), each carrying every still of
    its own worth picking from. Every tile on the page lands on a
    distinct project; main.js's randomizer picks the project per slot
    (without replacement, with COLLAGE_FALLBACK_ORDER as backup) and then
    one random image from that project's own list.

    scripted: every narrative project with 8+ galleryImages (real width
    >= 1500px) — automatic, so a film that gets a gallery later joins
    with no spec edit — plus Misfits & Monsters' per-episode stills, each
    episode its own pool entry (its gallery is one folder per episode,
    not a flat galleryImages list) keyed "<project key>:ep:<folder>" so
    two tiles can never land on the same episode. A non-Misfits narrative
    project used as a COLLAGE_SPEC poster is excluded entirely (see
    collage_poster_keys()).

    commercial / documentary / music_video: every project in that
    category (excluding one used as a poster), each contributing its own
    image/image2/image3 — every project in these categories already
    carries 2-3 of them for its own triptych listing, so there's nothing
    further to vet the way the old hand-picked list required."""
    poster_keys = collage_poster_keys()
    pools = {t: [] for t in COLLAGE_TYPES}

    for key, p in all_projects.items():
        if not key.startswith('narrative-'):
            continue
        if key not in poster_keys:
            gallery = p.get('galleryImages') or []
            if len(gallery) >= SCRIPTED_POOL_MIN_GALLERY:
                images = []
                for item in gallery:
                    url = item[0] if isinstance(item, tuple) else item
                    path = local_image_path(url)
                    if not path:
                        continue
                    try:
                        from PIL import Image
                        with Image.open(path) as im:
                            w = im.size[0]
                    except Exception:
                        continue
                    if w < SCRIPTED_POOL_MIN_WIDTH:
                        continue
                    images.append(url)
                if images:
                    pools['scripted'].append({'key': key, 'title': p['title'], 'href': p['href'], 'images': images})

        # Episodes are pool-eligible even when the series itself (`key`)
        # is a poster — see collage_poster_keys()'s docstring.
        episodes_by_n = {e['n']: e['title'] for e in (p.get('episodes') or [])}
        for eg in (p.get('episodeGalleries') or []):
            folder = eg.get('folder')
            files = load_misfits_manifest().get(folder) or []
            if not files:
                continue
            wide = [f for f in files if (f['w'] / f['h']) > 1.5]
            narrow = [f for f in files if (f['w'] / f['h']) <= 1.5]
            if folder in EPISODE_VISUAL_GROUP:
                if wide:
                    wide = order_by_similar_look(folder, wide)
                if narrow:
                    narrow = order_by_similar_look(folder, narrow)
            # No SCRIPTED_POOL_MIN_WIDTH filter here (unlike narrative
            # galleryImages below) — most episodes' processed stills run
            # under that 1500px bar, which cut the collage's pool of
            # distinct Misfits episodes down to 4 of 8 for no quality
            # reason specific to this use (they're full-size everywhere
            # else on the episode's own gallery page).
            images = ['assets/images/misfits-and-monsters/' + folder + '/' + f['file']
                      for f in (wide + narrow)]
            if images:
                ep_title = p['title'] + ' — ' + episodes_by_n.get(eg.get('n'), folder)
                pools['scripted'].append({'key': key + ':ep:' + folder, 'title': ep_title,
                                           'href': p['href'], 'images': images})

    for cat_key in ('commercial', 'documentary', 'music_video'):
        cat = next(c for c in CATS if c['key'] == cat_key)
        for i in range(len(cat['projects'])):
            key = cat_key + '-' + str(i)
            if key in poster_keys:
                continue
            p = all_projects[key]
            images = [u for u in (p.get('image'), p.get('image2'), p.get('image3')) if u]
            if images:
                pools[cat_key].append({'key': key, 'title': p['title'], 'href': p['href'], 'images': images})

    return pools


# ------------------------------------------------------------------ head --

FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600'
             '&family=IBM+Plex+Mono:wght@400;500&family=Bebas+Neue&display=swap" rel="stylesheet">')


def head(root, title, description):
    return (
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>' + esc(title) + '</title>\n'
        '<meta name="description" content="' + esc(description) + '">\n'
        + FONT_LINK + '\n'
        '<link rel="stylesheet" href="' + root + 'assets/css/style.css">\n'
    )


def films_dropdown(root, align='left'):
    side = 'left: 0;' if align == 'left' else 'right: 0;'
    return (
        '<div class="nav-item">'
        '<a href="' + root + 'films/scripted.html">Films</a>'
        '<div class="nav-dropdown" style="' + side + '">'
        '<div class="nav-dropdown-inner">'
        '<a href="' + root + 'films/scripted.html">Scripted</a>'
        '<a href="' + root + 'films/documentary.html">Documentary</a>'
        '<a href="' + root + 'films/music-video.html">Music Video</a>'
        '</div></div></div>'
    )


def home_header(root):
    return (
        '<div class="home-header">'
        '<div class="home-eyebrow">35mm &nbsp;&middot;&nbsp; 16mm &nbsp;&middot;&nbsp; digital</div>'
        '<div class="home-name">Bradley Stonesifer</div>'
        '<div class="home-role">Cinematographer</div>'
        '</div>'
        '<nav class="home-nav">'
        + films_dropdown(root, 'left') +
        '<a href="' + root + 'commercial.html">Commercial</a>'
        '<a href="' + root + 'about.html">About</a>'
        '</nav>'
    )


def inner_header(root):
    return (
        '<header class="inner-header">'
        '<div class="inner-header-bg"></div>'
        '<div class="inner-header-row">'
        '<a href="' + root + 'index.html" class="inner-name-link">'
        '<div class="inner-name">Bradley Stonesifer</div>'
        '<div class="inner-role">Cinematographer</div>'
        '</a>'
        '<nav class="inner-nav">'
        + films_dropdown(root, 'right') +
        '<a href="' + root + 'commercial.html">Commercial</a>'
        '<a href="' + root + 'about.html">About</a>'
        '</nav>'
        '</div></header>'
    )


def footer(root):
    return (
        '<footer class="site-footer">'
        '<span>&copy; 2026 Bradley Stonesifer &mdash; Cinematographer</span>'
        '<div class="footer-right">'
        '<a class="footer-insta" href="https://www.instagram.com/bradleystonesifer/" target="_blank" rel="noopener" aria-label="Instagram">'
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2.5" y="2.5" width="19" height="19" rx="5"></rect>'
        '<circle cx="12" cy="12" r="4.2"></circle><circle cx="17.6" cy="6.4" r="1.1" fill="currentColor" stroke="none"></circle></svg>'
        '</a>'
        '<a class="footer-contact" href="' + root + 'about.html#contact-block">Contact</a>'
        '</div></footer>'
    )


def page(root, title, description, header_html, body_html, extra_head=''):
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n' + head(root, title, description) + extra_head + '\n</head>\n'
        '<body>\n<div class="page">\n<div class="grain"></div>\n'
        + header_html + '\n' + body_html + '\n' + footer(root) +
        '\n</div>\n<script src="' + root + 'assets/js/main.js"></script>\n</body>\n</html>\n'
    )


def asset(root, path):
    """Root-prefix a local asset path; leave absolute URLs untouched."""
    if not path or path.startswith('http://') or path.startswith('https://'):
        return path
    return root + path


def img(src, alt, cls='', extra='', lazy=True):
    loading = ' loading="lazy" decoding="async"' if lazy else ''
    cls_attr = ' class="' + cls + '"' if cls else ''
    # draggable="false": images are draggable by default, and a real mouse
    # almost always drifts a pixel between press and release — enough for
    # the browser to start a native image-drag gesture instead of firing a
    # click, which silently eats real clicks on <a><img></a> tiles (only a
    # perfectly still synthetic click would "work").
    return '<img src="' + esc(src) + '" alt="' + esc(alt) + '"' + cls_attr + loading + ' draggable="false"' + extra + '>'


# --------------------------------------------------------------- fragments --

def render_credit_value(cr):
    if cr.get('isActorList'):
        parts = []
        for act in cr['actors']:
            name = esc(act['name'])
            if act['href']:
                parts.append('<a href="' + esc(act['href']) + '" target="_blank" rel="noopener">' + name + '</a>')
            else:
                parts.append('<span>' + name + '</span>')
            if act['last']:
                parts.append(', ')
        return '<div class="credit-actors">' + ''.join(parts) + '</div>'
    if cr.get('href'):
        return '<a href="' + esc(cr['href']) + '" target="_blank" rel="noopener" class="credit-val">' + esc(cr['v']) + '</a>'
    return '<div class="credit-val">' + esc(cr['v']) + '</div>'


def render_credit_groups(groups):
    out = ['<div class="credit-groups">']
    for group in groups:
        out.append('<div class="credit-group">')
        for cr in group:
            out.append('<div class="credit-item">')
            out.append('<div class="credit-key">' + esc(cr['k']) + '</div>')
            out.append(render_credit_value(cr))
            out.append('</div>')
        out.append('</div>')
    out.append('</div>')
    return ''.join(out)


def render_press_quotes(quotes):
    if not quotes:
        return ''
    out = ['<div class="field-label">Press</div>', '<div class="press-grid">']
    for pq in quotes:
        out.append('<div class="press-card">')
        out.append('<div class="press-source">' + esc(pq['k']) + '</div>')
        if pq.get('href'):
            out.append('<a href="' + esc(pq['href']) + '" target="_blank" rel="noopener" class="press-quote">' + esc(pq['v']) + '</a>')
        else:
            out.append('<div class="press-quote">' + esc(pq['v']) + '</div>')
        out.append('</div>')
    out.append('</div>')
    return ''.join(out)


def render_video_block(p, which, aspect='16/9', root=''):
    """which: 'first' (top player) or 'second' (bottom Selects player)."""
    embed = p.get('videoEmbed') if which == 'first' else p.get('secondVideoEmbed')
    if not embed:
        return ''
    vid = vimeo_id(embed)
    # videoThumb (per-project, i.vimeocdn.com) wins when set; falls back to
    # the original p.get('image') otherwise — the-vicious-kind never sets
    # videoThumb, so its output is byte-for-byte unchanged. asset(root, ...)
    # root-prefixes a local path (no-op for the absolute Squarespace/
    # i.vimeocdn.com URLs every pre-existing caller of this function uses)
    # — needed now that a local root-relative still (e.g. a gallery image)
    # can end up here too, same as every other image field on the site.
    thumb_url = asset(root, p.get('videoThumb') or p.get('image'))
    if which == 'first':
        vattr = ' data-vimeo-id="' + vid + '"' if vid else ''
        return (
            '<div class="video-wrap" data-video-wrap style="aspect-ratio: ' + aspect + ';" data-embed-src="' + esc(embed) + '">'
            '<button type="button" class="video-thumb-overlay" data-video-thumb' + vattr + ' aria-label="Play">'
            + img(thumb_url, p['title']) +
            '<div class="play-btn"><div class="play-btn-tri"></div></div>'
            '</button></div>'
        )
    # second / "Selects" player. secondVideoThumb is optional — when unset
    # (the-vicious-kind never sets it) this renders exactly as before, a
    # plain gradient card with no image, byte-for-byte unchanged.
    second_thumb = asset(root, p.get('secondVideoThumb')) if p.get('secondVideoThumb') else ''
    thumb_html = img(second_thumb, p['title'] + ' — Selects', cls='selects-bg-img') if second_thumb else ''
    thumb_cls = ' has-thumb' if second_thumb else ''
    return (
        '<div class="selects-wrap">'
        '<div class="selects-video" data-video-wrap data-embed-src="' + esc(embed) + '">'
        + thumb_html +
        '<div class="selects-thumb' + thumb_cls + '" data-video-thumb>'
        '<div class="selects-inner"><span class="selects-label">Selects</span>'
        '<div class="play-btn"><div class="play-btn-tri"></div></div></div>'
        '</div></div></div>'
    )


def vimeo_dnt_url(url):
    """Vimeo's "do not track" param — ?dnt=1 if the URL has no query yet,
    &dnt=1 if it already carries ?h=HASH."""
    return url + ('&dnt=1' if '?' in url else '?dnt=1')


def render_video_player(p, aspect='16/9', root=''):
    """Vimeo facade player for every detail page except the five that
    already have one via the older videoEmbed/secondVideoEmbed mechanism
    (the-vicious-kind, hit-and-run, spork, both Re:Purpose titles) — those
    are left completely alone by checking for videoEmbed first.

    Separate markup/data-attributes/JS from render_video_block() above on
    purpose, so this never touches those five pages' elements or behavior.
    Reuses the same .video-wrap / .video-thumb-overlay / .play-btn /
    .play-btn-tri CSS classes for visual consistency.
    """
    if p.get('videoEmbed'):
        return render_video_block(p, 'first', aspect, root)
    videos = VIDEOS.get(p.get('slug'))
    if not videos:
        return ''
    # Each video carries its own Vimeo thumbnail (i.vimeocdn.com, or a
    # local root-relative still routed through asset()); falls back to
    # the project's existing still only if one wasn't supplied.
    thumb_url = asset(root, videos[0].get('thumb') or p.get('image'))
    main_src = vimeo_dnt_url(videos[0]['url'])
    play_label = 'Play'
    out = [
        '<div class="video-wrap" data-vimeo-wrap data-vimeo-title="' + esc(p['title'])
        + '" data-vimeo-play-label="' + esc(play_label) + '" style="aspect-ratio: ' + aspect
        + ';" data-vimeo-src="' + esc(main_src) + '">',
        '<div class="video-thumb-overlay">',
        img(thumb_url, p['title']),
        '<button type="button" class="video-click-btn" data-vimeo-play aria-label="' + esc(play_label) + '">',
        '<div class="play-btn"><div class="play-btn-tri"></div></div>',
        '</button>',
        '</div></div>',
    ]
    if len(videos) > 1:
        out.append('<div class="video-select-row">')
        for i, v in enumerate(videos):
            cls = 'video-select-btn active' if i == 0 else 'video-select-btn'
            thumb = asset(root, v.get('thumb') or p.get('image') or '')
            out.append(
                '<button type="button" class="' + cls + '" data-vimeo-select="'
                + esc(vimeo_dnt_url(v['url'])) + '" data-vimeo-select-thumb="' + esc(thumb) + '">'
                + esc(v.get('label', '')) + '</button>'
            )
        out.append('</div>')
    return ''.join(out)


def render_static_video_thumb(p, aspect, root):
    """Fallback for a project with no trailer at all (comingSoon, no
    videoEmbed/VIDEOS entry): a plain, non-clickable still in the same
    .video-wrap box/sizing as a real player, no play button or overlay.
    Only used when render_video_player() itself found nothing to render."""
    url = p.get('staticVideoThumb')
    if not url:
        return ''
    return ('<div class="video-wrap" style="aspect-ratio: ' + aspect + ';">'
            + img(asset(root, url), p['title'], lazy=False) + '</div>')


def render_key_art(p, root, aspect='16/9'):
    """Fallback for the detail page's center column when a project has no
    VIDEOS entry (no trailer/clip to play) — a plain hyperlinked key-art
    image instead of an empty slot, sized the same as the video player it
    stands in for. Opt-in via keyArtImage/keyArtUrl so every other
    project's output is unaffected."""
    url = p.get('keyArtImage')
    link = p.get('keyArtUrl')
    if not url or not link:
        return ''
    return (
        '<a class="key-art-link" href="' + esc(link) + '" target="_blank" rel="noopener" '
        'style="aspect-ratio: ' + aspect + ';">'
        + img(asset(root, url), p['title'] + ' key art', lazy=False) +
        '</a>'
    )


def _gallery_item(item, title):
    """A gallery slot is either a plain URL string (title used as alt, the
    original behavior) or an (url, alt) pair when the project supplies
    per-image alt text via galleryAlts."""
    return item if isinstance(item, tuple) else (item, title)


def render_gallery(root, dd, title, slug=None):
    # asset(root, url) root-prefixes a local path (no-op for absolute
    # http(s) URLs, e.g. the legacy Squarespace-hosted galleries) — same
    # treatment the poster image already gets, so galleryImages can store
    # plain root-relative paths like every other local image field instead
    # of a hardcoded '../' that breaks when the same path is reused
    # elsewhere (e.g. a COLLAGE_SPEC "gallery:N" homepage tile, which sits
    # at site root rather than inside /films/ or /commercial/).
    desktop_lb = dd.get('desktopLightbox')
    # data-gm-index matches this still's position in galleryFlat, the same
    # order the mobile gm-data JSON (render_gallery_mobile) uses — so the
    # desktop click-to-enlarge wiring in main.js can reuse that one dataset
    # instead of embedding a second copy.
    lb_attrs = (lambda idx: ' data-gm-index="' + str(idx) + '" tabindex="0" role="button"') if desktop_lb else (lambda idx: '')

    def cell(item, idx, cls):
        url, alt = _gallery_item(item, title)
        return '<div class="' + cls + '"' + lb_attrs(idx) + '>' + img(asset(root, url), alt) + '</div>'
    left = ''.join(cell(u, i, 'gallery-cell') for u, i in zip(dd['galleryLeft'], dd['galleryLeftIdx']) if _gallery_item(u, title)[0])
    right = ''.join(cell(u, i, 'gallery-cell') for u, i in zip(dd['galleryRight'], dd['galleryRightIdx']) if _gallery_item(u, title)[0])
    poster = asset(root, dd['posterImage'])

    # Native-aspect-ratio layout (8+ galleryImages, see detail_data()):
    # --ar/--pc drive .gallery-main--ar's CSS (scoped so <8-image pages are
    # untouched). --ar also has to go on .gallery-bottom directly since it
    # sits outside .gallery-main and CSS custom properties only inherit
    # down the DOM tree, not across siblings.
    ar = dd.get('galleryAr')
    main_cls = 'gallery-main' + (' gallery-main--ar' if ar else '')
    main_style = ''
    bottom_style = ''
    if ar:
        pc = dd.get('galleryPc') or 1.1
        main_style = ' style="--ar: %.4f; --pc: %.4ffr;"' % (ar, pc)
        bottom_style = ' style="--ar: %.4f;"' % ar

    out = ['<div class="field-label" style="margin-top: 34px;">Gallery</div>',
           '<div class="' + main_cls + '"' + main_style + '>']
    out.append('<div class="gallery-side"><div class="gallery-side-grid">' + left + '</div></div>')
    if poster:
        out.append('<div class="gallery-poster">' + img(poster, title + ' poster', lazy=False) + '</div>')
    out.append('<div class="gallery-side"><div class="gallery-side-grid">' + right + '</div></div>')
    out.append('</div>')
    bottom = dd['galleryBottom']
    contain_from = GALLERY_CONTAIN_FROM.get(slug)
    if bottom:
        out.append('<div class="gallery-bottom"' + bottom_style + '>')
        for item, idx in zip(bottom, dd['galleryBottomIdx']):
            url, alt = _gallery_item(item, title)
            if url:
                cell_cls = 'gallery-bottom-cell' + (' gallery-bottom-cell--contain' if contain_from and (idx + 1) >= contain_from else '')
                out.append('<div class="' + cell_cls + '"' + lb_attrs(idx) + '>' + img(asset(root, url), alt) + '</div>')
        out.append('</div>')
    return ''.join(out)


GALLERY_MOBILE_INITIAL = 16
GALLERY_MOBILE_BATCH = 16


def render_gallery_mobile(root, dd, title, slug=None):
    """Phone-width (<=600px) gallery: poster full-width first, then every
    still in the same order used elsewhere (the 8 featured/interleaved
    stills, then the rest) in a 2-column grid. Only the first 16 cells get
    a real src; the rest carry data-gm-src and stay empty until "Show
    more" reveals the next 16 — so nothing past the first batch is
    fetched up front. A shared JSON blob of every still (including ones
    never revealed in the grid) feeds the tap-to-enlarge lightbox, which
    fetches on demand as the visitor swipes/arrows through it."""
    items = [_gallery_item(it, title) for it in dd['galleryFlat']]
    items = [(url, alt) for url, alt in items if url]
    if not items:
        return ''
    ar = dd.get('galleryAr') or 2.35
    cell_style = ' style="aspect-ratio: %.4f;"' % ar
    contain_from = GALLERY_CONTAIN_FROM.get(slug)
    cells = []
    for i, (url, alt) in enumerate(items):
        full_url = asset(root, url)
        if i < GALLERY_MOBILE_INITIAL:
            inner = img(full_url, alt, lazy=(i > 1))
        else:
            inner = ('<img alt="' + esc(alt) + '" decoding="async" draggable="false" data-gm-src="'
                      + esc(full_url) + '">')
        hidden = ' gm-hidden' if i >= GALLERY_MOBILE_INITIAL else ''
        contain = ' gm-cell--contain' if contain_from and (i + 1) >= contain_from else ''
        cells.append('<button type="button" class="gm-cell' + hidden + contain + '" data-gm-index="' + str(i)
                      + '"' + cell_style + '>' + inner + '</button>')
    more_btn = '<button type="button" class="gm-more" data-gm-more>Show more</button>' if len(items) > GALLERY_MOBILE_INITIAL else ''
    poster = asset(root, dd['posterImage'])
    poster_html = '<div class="gm-poster">' + img(poster, title + ' poster', lazy=False) + '</div>' if poster else ''
    data_json = json.dumps([{'url': asset(root, u), 'alt': a} for u, a in items], separators=(',', ':')).replace('</', '<\\/')
    return (
        '<div class="gallery-mobile" data-gallery-mobile>' + poster_html
        + '<div class="gm-grid">' + ''.join(cells) + '</div>' + more_btn
        + '<script type="application/json" class="gm-data">' + data_json + '</script>'
        '</div>'
    )


EPISODE_FEATURED_COUNT = 8
_MISFITS_MANIFEST = None


def load_misfits_manifest():
    """site/assets/images/misfits-and-monsters/manifest.json: {folder:
    [{file, w, h}, ...]} — real dimensions for the per-episode gallery
    selector's justified-row (desktop) / 2-col (mobile) layouts. Cached
    after the first successful read; returns {} if the branch's images
    haven't been checked out (so a build never hard-fails over it)."""
    global _MISFITS_MANIFEST
    if _MISFITS_MANIFEST is None:
        path = os.path.join(SITE_DIR, 'assets/images/misfits-and-monsters/manifest.json')
        try:
            with open(path) as f:
                _MISFITS_MANIFEST = json.load(f)
        except Exception:
            _MISFITS_MANIFEST = {}
    return _MISFITS_MANIFEST


# Folders whose stills get reordered by visual similarity (see
# order_by_similar_look) instead of kept in their original shot order —
# there's no usable "date originally created" metadata on these frame
# grabs (checked: no EXIF, and file mtimes just reflect when they were
# checked out, not when the frame was captured), so similarity is the
# only grouping signal actually available.
EPISODE_VISUAL_GROUP = {'ep-06'}


def _color_signature(path, size=(12, 7)):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.convert('RGB').resize(size).tobytes()
    except Exception:
        return None


def order_by_similar_look(folder, files):
    """Greedy nearest-neighbor chain over a small per-image color/
    composition signature (a resized-down RGB pixel grid) — groups
    visually similar stills together (bright outdoor shots, dark
    military scenes, the purple-lit lab, etc.) instead of leaving them
    in shot order. Falls back to the given order untouched if any image
    can't be read (e.g. the branch's images aren't checked out)."""
    sigs = {}
    for f in files:
        path = os.path.join(SITE_DIR, 'assets/images/misfits-and-monsters', folder, f['file'])
        sig = _color_signature(path)
        if sig is None:
            return files
        sigs[f['file']] = sig

    def dist(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    remaining = list(files)
    ordered = [remaining.pop(0)]
    while remaining:
        last_sig = sigs[ordered[-1]['file']]
        nxt = min(remaining, key=lambda f: dist(last_sig, sigs[f['file']]))
        remaining.remove(nxt)
        ordered.append(nxt)
    return ordered


EPISODE_GALLERY_PREFERRED_DEFAULT = '02'  # "02" was the first episode with stills; kept as the default even after episode 1 got its own gallery, so the page doesn't silently change which one opens


def _episode_gallery_default(p):
    """The preferred default episode if it has a stills folder, else the
    first episode that does (or just the first entry if somehow none
    do) — shared between render_episode_selector and
    render_episode_panels so both agree on which one starts active."""
    galleries = p.get('episodeGalleries') or []
    if not galleries:
        return None
    by_n = {g['n']: g for g in galleries}
    preferred = by_n.get(EPISODE_GALLERY_PREFERRED_DEFAULT)
    if preferred and preferred.get('folder'):
        return EPISODE_GALLERY_PREFERRED_DEFAULT
    return next((g['n'] for g in galleries if g.get('folder')), None) or galleries[0]['n']


def render_episode_selector(p):
    """Episode selector buttons for Misfits & Monsters — its own
    full-width row directly below the detail-grid (credits | key art |
    logline+press), above the episode panels it controls. Styled like
    the commercial pages' multi-video selector. The panels (title,
    synopsis, gallery) render separately via render_episode_panels(),
    wired together in main.js by their own top-level selectors
    (data-episode-select-row / data-episode-panels), not by DOM nesting,
    since they're not DOM siblings."""
    galleries = p.get('episodeGalleries') or []
    if not galleries:
        return ''
    episodes_by_n = {e['n']: e for e in (p.get('episodes') or [])}
    default_n = _episode_gallery_default(p)

    buttons = []
    for g in galleries:
        n = g['n']
        title = episodes_by_n.get(n, {}).get('title', '')
        is_default = n == default_n
        btn_cls = 'video-select-btn ep-select-btn' + (' active' if is_default else '')
        buttons.append(
            '<button type="button" class="' + btn_cls + '" data-ep-select="' + esc(n)
            + '" aria-pressed="' + ('true' if is_default else 'false') + '">'
            + esc(n) + ' ' + esc(title) + '</button>'
        )

    return '<div class="episode-select-row" data-episode-select-row>' + ''.join(buttons) + '</div>'


def render_episode_panels(root, p):
    """Full-width episode panels for Misfits & Monsters — one per
    episode, swapped by the selector buttons above (JS, no reload). Each
    panel's stills render as a single uniform CSS grid (3 columns desktop,
    2 at 900px and below — see .ep-grid in style.css): every tile is a
    16:9 box with object-fit: cover, so a 4:3 still (episode 2's news-
    broadcast frames) crops to fit rather than letterboxing, and every
    row — including a sparse last row after Show more — uses identical
    tile sizes. Reuses the same .gm-cell/.gm-more/.gm-data wiring and
    shared lightbox as every other gallery page, just with its own
    collapse-on-episode-switch behavior layered on in main.js.
    Episode titles/synopses are reused from the existing "episodes" list
    by matching "n" — never duplicated here. Episodes with no folder yet
    (1 and 8) still get a real, clickable panel — title, synopsis, and a
    "Stills coming soon" note — rather than being disabled or hidden, so
    the full 8-episode structure and every #ep-NN hash link works."""
    galleries = p.get('episodeGalleries') or []
    if not galleries:
        return ''
    episodes_by_n = {e['n']: e for e in (p.get('episodes') or [])}
    manifest = load_misfits_manifest()
    default_n = _episode_gallery_default(p)

    panels = []
    for g in galleries:
        n = g['n']
        folder = g.get('folder')
        info = episodes_by_n.get(n, {})
        title = info.get('title', '')
        synopsis = info.get('synopsis', '')
        has_images = bool(folder) and manifest.get(folder)
        is_default = n == default_n

        info_html = ('<div class="episode-info"><div class="ep-active-title">' + esc(n) + ' · ' + esc(title) + '</div>'
                      + ('<p class="logline-text">' + esc(synopsis) + '</p>' if synopsis else '') + '</div>')

        if has_images:
            # Group by shape — every 16:9 still first, then the 4:3 ones
            # (episode 2's news-broadcast frames) together at the end —
            # rather than interleaved in whatever order they were shot.
            # Threshold of 1.5 cleanly separates 16:9 (1.78) from 4:3
            # (1.33). Within each shape group, episodes in
            # EPISODE_VISUAL_GROUP (episode 6) are further reordered by
            # visual similarity instead of shot order (kept separate per
            # group so a visually-reordered 4:3 still never ends up
            # ahead of the 16:9 group).
            raw_wide = [f for f in manifest.get(folder, []) if (f['w'] / f['h']) > 1.5]
            raw_narrow = [f for f in manifest.get(folder, []) if (f['w'] / f['h']) <= 1.5]
            if folder in EPISODE_VISUAL_GROUP:
                if raw_wide:
                    raw_wide = order_by_similar_look(folder, raw_wide)
                if raw_narrow:
                    raw_narrow = order_by_similar_look(folder, raw_narrow)
            files = raw_wide + raw_narrow
            items, cells = [], []
            for i, f in enumerate(files):
                url = asset(root, 'assets/images/misfits-and-monsters/' + folder + '/' + f['file'])
                alt = (title or ('Episode ' + n)) + ' — still ' + str(i + 1)
                items.append({'url': url, 'alt': alt})
                if i < EPISODE_FEATURED_COUNT:
                    # Only the default/visible-on-load episode gets its
                    # first couple of images eager — every other panel
                    # (hidden until its selector button is clicked) stays
                    # fully lazy even for its "featured" cells, since
                    # nothing in it is on screen yet.
                    inner = img(url, alt, lazy=(not is_default) or i > 1)
                else:
                    inner = ('<img alt="' + esc(alt) + '" decoding="async" draggable="false" data-gm-src="' + esc(url) + '">')
                hidden = ' gm-hidden' if i >= EPISODE_FEATURED_COUNT else ''
                cells.append('<button type="button" class="gm-cell' + hidden + '" data-gm-index="' + str(i) + '">' + inner + '</button>')

            more_btn = ''
            rest = len(files) - EPISODE_FEATURED_COUNT
            if rest > 0:
                more_label = 'Show more (' + str(rest) + ')'
                more_btn = ('<button type="button" class="gm-more" data-gm-more aria-expanded="false" '
                             'data-show-more-label="' + esc(more_label) + '" data-show-less-label="Show less">'
                             + esc(more_label) + '</button>')

            data_json = json.dumps(items, separators=(',', ':')).replace('</', '<\\/')
            gallery_html = ('<div class="ep-grid">' + ''.join(cells) + '</div>' + more_btn
                             + '<script type="application/json" class="gm-data">' + data_json + '</script>')
        else:
            gallery_html = '<p class="ep-coming-soon">Stills coming soon.</p>'

        panels.append(
            '<div class="episode-panel" data-episode-panel="' + esc(n) + '"' + ('' if is_default else ' hidden') + '>'
            + info_html + gallery_html + '</div>'
        )

    return ('<div class="episode-panels" data-episode-panels data-default-episode="' + esc(default_n or '') + '">'
            + ''.join(panels) + '</div>')


def page_rel(current_folder, target_href):
    """Resolve a root-relative href ('films/x.html') for a page sitting in
    current_folder ('' | 'films' | 'commercial')."""
    if current_folder == '':
        return target_href
    prefix = current_folder + '/'
    if target_href.startswith(prefix):
        return target_href[len(prefix):]
    return '../' + target_href


def render_next_link(current_folder, next_p):
    """Mirrors back-link's own markup/class (next-link is a visual
    modifier, not a separate style). Visible text is always just "Next →"
    — the next project's name is accessibility-only, via aria-label/title,
    not shown on screen at any width."""
    if not next_p:
        return ''
    href = page_rel(current_folder, next_p['href'])
    label = 'Next project: ' + esc(next_p['title'])
    return (
        '<a class="back-link next-link" href="' + href + '" aria-label="' + label + '" title="' + label + '">'
        'Next &#8594;'
        '</a>'
    )


# ---------------------------------------------------------------- pages --

def render_collage_tile(current_folder, item):
    """Fixed tile — posters only; never randomized. collage-tile--poster
    lets main.js's dedup pass and the phone layout (forced full-width)
    both target the poster tile directly, regardless of which side of
    its row it sits on. data-key seeds the project-level dedup set so a
    poster's own film is never also drawn as a random tile elsewhere."""
    href = page_rel(current_folder, item['href'])
    style = 'grid-column: span ' + str(item['span']) + '; aspect-ratio: ' + item['ratio'] + ';'
    title = esc(item['title'])
    return (
        '<a class="collage-tile collage-tile--poster" href="' + href + '" style="' + style
        + '" data-key="' + esc(item['key']) + '" draggable="false">'
        + img(item['url'], item['title']) +
        '<div class="collage-scrim"><span>' + title + '</span></div>'
        '</a>'
    )


def render_random_collage_tile(default_project, default_url, ratio, span, ttype):
    """Randomizable tile — server renders a deterministic default project
    (real href, no img src) plus a <noscript> fallback image, so the page
    works and links correctly with JS off or for crawlers. main.js
    replaces the src/href/alt/data-key on load, picking a different
    *project* (never one already used elsewhere on the page — see
    build_collage_pools()) and a random image from that project."""
    style = 'grid-column: span ' + str(span) + '; aspect-ratio: ' + ratio + ';'
    alt = esc(default_project['title'])
    return (
        '<a class="collage-tile" href="' + esc(default_project['href']) + '" data-pool="' + ttype
        + '" data-key="' + esc(default_project['key']) + '" style="' + style + '" draggable="false">'
        '<img alt="' + alt + '" decoding="async" draggable="false">'
        '<noscript>' + img(default_url, default_project['title']) + '</noscript>'
        '<div class="collage-scrim"><span>' + alt + '</span></div>'
        '</a>'
    )


# One row-wrapper div per 3/2/3-tile group; cycled over COLLAGE_SPEC's
# flat 32-entry list purely by position (which 3 entries make up a row
# never changes even though the poster can sit first or last within its
# own row's 3 — see the COLLAGE_SPEC comment in data.py).
COLLAGE_ROW_SIZES = [3, 2, 3]
COLLAGE_ROW_CLASSES = ['collage-row--mixed', 'collage-row--pair', 'collage-row--trio']


def _collage_pick_project(pools, ttype, used_keys):
    """First unused project for `ttype`, falling back through
    COLLAGE_FALLBACK_ORDER (skipping `ttype`, already tried) if that
    pool has nothing left — used for the deterministic server-rendered
    default; main.js runs the same try-own-type-then-fallback shape but
    picks randomly among what's left instead of the first match."""
    for t in (ttype,) + tuple(t for t in COLLAGE_FALLBACK_ORDER if t != ttype):
        for proj in pools.get(t, ()):
            if proj['key'] not in used_keys:
                return proj
    return None


def render_home(all_projects):
    pools = build_collage_pools(all_projects)
    used_keys = set(collage_poster_keys())
    tiles = []
    for ttype, key, ratio, span in COLLAGE_SPEC:
        if ttype == 'poster':
            p = all_projects[key]
            url = slot_url(all_projects, key, 'poster')
            tiles.append(render_collage_tile('', {'key': key, 'href': p['href'], 'title': p['title'], 'url': url, 'ratio': ratio, 'span': span}))
            continue
        proj = _collage_pick_project(pools, ttype, used_keys)
        if proj:
            used_keys.add(proj['key'])
            default_url = proj['images'][0]
        else:
            proj = {'key': '', 'title': '', 'href': '#'}
            default_url = ''
        tiles.append(render_random_collage_tile(proj, default_url, ratio, span, ttype))

    rows = []
    i = 0
    r = 0
    while i < len(tiles):
        size = COLLAGE_ROW_SIZES[r % 3]
        cls = COLLAGE_ROW_CLASSES[r % 3]
        rows.append('<div class="collage-row ' + cls + '">' + ''.join(tiles[i:i + size]) + '</div>')
        i += size
        r += 1

    # Escaped so a stray "</script>" inside any title/url can't prematurely
    # close the data block.
    pools_json = json.dumps(pools, separators=(',', ':')).replace('</', '<\\/')
    fallback_json = json.dumps(list(COLLAGE_FALLBACK_ORDER), separators=(',', ':'))

    collage_script = (
        '<script>(function(){'
        'var data=document.getElementById("collage-pools");'
        'if(!data)return;'
        'var pools;try{pools=JSON.parse(data.textContent);}catch(e){return;}'
        'var fallbackOrder=' + fallback_json + ';'
        # Every tile on the page is a distinct project — seeded from the
        # fixed poster tiles' keys (permanent, never re-rolled) so a
        # poster's own film is never also drawn as a random tile.
        'var usedKeys={};'
        'document.querySelectorAll(".collage-tile.collage-tile--poster").forEach(function(t){'
        'var k=t.getAttribute("data-key");if(k)usedKeys[k]=true;'
        '});'
        'function pickProject(ttype){'
        'var order=[ttype].concat(fallbackOrder.filter(function(t){return t!==ttype;}));'
        'for(var i=0;i<order.length;i++){'
        'var pool=pools[order[i]]||[];'
        'var avail=pool.filter(function(p){return !usedKeys[p.key];});'
        'if(avail.length)return avail[Math.floor(Math.random()*avail.length)];'
        '}'
        'return null;'
        '}'
        'document.querySelectorAll(".collage-tile[data-pool]").forEach(function(tile,i){'
        'var proj=pickProject(tile.getAttribute("data-pool"));'
        'if(!proj)return;'
        'usedKeys[proj.key]=true;'
        'var url=proj.images[Math.floor(Math.random()*proj.images.length)];'
        'var img=tile.querySelector("img");'
        'if(img){img.src=url;img.alt=proj.title;if(i>3)img.loading="lazy";}'
        'tile.href=proj.href;'
        'tile.setAttribute("data-key",proj.key);'
        'var scrim=tile.querySelector(".collage-scrim span");'
        'if(scrim)scrim.textContent=proj.title;'
        '});'
        '})();</script>'
    )
    body = (
        '<div class="collage-outer"><div class="collage-rows">' + ''.join(rows) + '</div></div>'
        '<script type="application/json" id="collage-pools">' + pools_json + '</script>'
        + collage_script +
        '<div class="home-intro">'
        '<p>Bradley Stonesifer is a Los Angeles-based cinematographer shooting narrative, documentary, '
        'and music video work &mdash; light-led, patient, and image-first. Available for select commercial work.</p>'
        '<div class="home-cta">'
        '<a href="films/scripted.html" class="btn-primary">See the films</a>'
        '<a href="about.html" class="btn-outline">Get in touch</a>'
        '</div></div>'
    )
    return page('', 'Bradley Stonesifer — Cinematographer',
                 'Los Angeles-based cinematographer shooting narrative, documentary, and music video work.',
                 home_header(''), body)


def render_poster_tile(current_folder, p):
    root = '' if current_folder == '' else '../'
    href = page_rel(current_folder, p['href'])
    d = poster_tile_data(p)
    out = ['<a class="poster-tile" href="' + href + '" draggable="false">']
    if d['hasTileImage']:
        out.append(img(asset(root, d['tileImage']), p['title']))
    if d['comingSoon']:
        out.append('<div class="coming-soon"><div class="coming-soon-title">' + esc(p['title']) + '</div>')
        if d['artImage']:
            out.append(img(asset(root, d['artImage']), p['title']))
        out.append('<div class="coming-soon-label">Coming soon</div></div>')
    if d['noPoster']:
        out.append('<div class="no-poster"><div class="no-poster-title">' + esc(p['title']) + '</div>')
        if d['laurels']:
            out.append('<div class="laurels">')
            for l in d['laurels']:
                out.append('<div class="laurel"><span class="laurel-name">' + esc(l['name']) + '</span>')
                if l['hasSub']:
                    out.append('<span class="laurel-sub">' + esc(l['sub']) + '</span>')
                out.append('</div>')
            out.append('</div>')
        out.append('</div>')
    out.append('</a>')
    return ''.join(out)


def render_triptych_block(current_folder, p):
    href = page_rel(current_folder, p['href'])
    imgs = [u for u in (p.get('image'), p.get('image2'), p.get('image3')) if u]
    cells = []
    for u in imgs:
        cells.append('<a class="triptych-img-wrap" href="' + href + '" draggable="false">' + img(u, p['title']) + '<div class="triptych-hover"></div></a>')
    note = ''
    if p.get('note'):
        note = ' <span class="triptych-note">&mdash; ' + esc(p['note']) + '</span>'
    return (
        '<div class="triptych-block">'
        '<a class="triptych-title" href="' + href + '">' + esc(p['title']) + note + '</a>'
        '<div class="triptych-row">' + ''.join(cells) + '</div>'
        '</div>'
    )


def render_category_page(cat_key, groups):
    group = groups[cat_key]
    root = '../'
    subnav = []
    for k, label in (('narrative', 'Scripted'), ('documentary', 'Documentary'), ('music_video', 'Music Video')):
        cls = ' class="active"' if k == cat_key else ''
        subnav.append('<a href="' + CAT_FILENAME[k] + '"' + cls + '>' + label + '</a>')
    body = ['<div class="cat-wrap"><div class="cat-head">',
            '<h1 class="cat-title">' + esc(group['label']) + '</h1>',
            '<div class="cat-subnav">' + ''.join(subnav) + '</div></div>']
    if group['isGrid']:
        body.append('<div class="poster-grid">')
        for p in group['projects']:
            body.append(render_poster_tile('films', p))
        body.append('</div>')
    else:
        for p in group['projects']:
            body.append(render_triptych_block('films', p))
    body.append('</div>')
    return page(root, group['label'] + ' — Bradley Stonesifer',
                'Bradley Stonesifer ' + group['label'].lower() + ' work as a cinematographer.',
                inner_header(root), ''.join(body))


def render_commercial_page(all_projects):
    root = ''
    projects = [all_projects['commercial-' + str(i)] for i in range(len([c for c in CATS if c['key'] == 'commercial'][0]['projects']))]
    body = ['<div class="cat-wrap"><div class="cat-head"><h1 class="cat-title">Commercial</h1></div>']
    for p in projects:
        body.append(render_triptych_block('', p))
    body.append('</div>')
    return page(root, 'Commercial — Bradley Stonesifer',
                'Select commercial cinematography work by Bradley Stonesifer.',
                inner_header(root), ''.join(body))


def render_detail_page(p, current_folder, next_map):
    root = '../'
    dd = detail_data(p)
    aspect = p.get('videoAspect', '16/9')

    left_html = render_credit_groups(dd['creditGroups']) if dd['creditGroups'] else ''
    center_html = (render_video_player(p, aspect, root)
                   or render_static_video_thumb(p, aspect, root)
                   or render_key_art(p, root, aspect))
    right_parts = []
    if dd['logline']:
        right_parts.append('<div class="field-label">Logline</div><p class="logline-text">' + esc(dd['logline']) + '</p>')
    right_parts.append(render_press_quotes(dd['pressQuotes']))
    if p.get('watchUrl'):
        right_parts.append('<a class="watch-btn" href="' + esc(p['watchUrl']) + '" target="_blank" rel="noopener">' + esc(p.get('watchLabel', 'Watch')) + '</a>')
    right_html = ''.join(right_parts)

    nav_html = ('<a class="back-link" href="' + dd['backHref'] + '">' + esc(dd['backLabel']) + '</a>'
                + render_next_link(current_folder, next_map.get(p['slug'])))
    body = ['<div class="detail-wrap">',
            '<div class="detail-head">',
            '<div class="detail-head-nav">' + nav_html + '</div>',
            '<h1 class="detail-title">' + esc(p['title']) + '</h1>']
    if p.get('creditLine'):
        body.append('<div class="detail-credit-line">' + esc(p['creditLine']) + '</div>')
    body.append('</div>')
    if left_html or center_html or right_html:
        # When there's no video (center_html empty — e.g. Misfits &
        # Monsters has no VIDEOS entry), the right column must still
        # land in the grid's 3rd (narrow) track explicitly — otherwise
        # CSS grid auto-placement slides it into the unused 2nd (wide)
        # track, leaving a blank gap where the video would have been
        # instead of the page reading like every other film page just
        # missing its video. A class (not inline style) so the existing
        # <=1150px breakpoint, which collapses this column to full width
        # on its own row, still wins on specificity+source order.
        right_col_cls = 'detail-col-right' + ('' if center_html else ' detail-col-right--solo')
        body.append('<div class="detail-grid">')
        if left_html:
            body.append('<div class="detail-col-left"><div>' + left_html + '</div></div>')
        if center_html:
            body.append('<div class="detail-col-center">' + center_html + '</div>')
        if right_html:
            body.append('<div class="' + right_col_cls + '"><div>' + right_html + '</div></div>')
        body.append('</div>')  # /detail-grid

    if p.get('episodeGalleries'):
        body.append('<div class="field-label">Episodes</div>')
        body.append(render_episode_selector(p))
        body.append(render_episode_panels(root, p))
    else:
        body.append(render_gallery(root, dd, p['title'], p.get('slug')))
        body.append(render_gallery_mobile(root, dd, p['title'], p.get('slug')))
    body.append(render_video_block(p, 'second', root=root))
    body.append('</div>')  # /detail-wrap

    extra_head = ''
    bottom_cols = GALLERY_BOTTOM_COLS.get(p.get('slug'))
    if bottom_cols:
        # The default 4 columns leaves a ragged last row for this page's
        # bottom-grid count; this column count divides it evenly instead.
        # Scoped to this page only via an inline <style> (desktop-only, so
        # it doesn't interfere with the shared ≤900px collapse-to-1-column
        # rule) — no other page's CSS or output changes.
        extra_head = ('<style>@media (min-width: 901px) {.gallery-bottom{grid-template-columns:repeat('
                       + str(bottom_cols) + ',minmax(0,1fr));}}</style>')

    return page(root, p['title'] + ' — Bradley Stonesifer',
                (dd['logline'] or (p['title'] + ', shot by cinematographer Bradley Stonesifer.')),
                inner_header(root), ''.join(body), extra_head)


def render_simple_detail_page(p, current_folder, next_map, video_only=False):
    """Music Video / Commercial detail pages: back link, title, a single
    full-width 16:9 video player, and a stills gallery — no credits sidebar."""
    root = '../'
    aspect = p.get('videoAspect', '16/9')
    back_href = CAT_FILENAME[p['catKey']] if p['section'] == 'films' else '../commercial.html'
    back_label = 'Back'

    video_html = render_video_player(p, aspect, root)
    stills = [] if video_only else (p.get('galleryImages') or [u for u in (p.get('image2'), p.get('image3')) if u])

    nav_html = ('<a class="back-link" href="' + back_href + '">' + esc(back_label) + '</a>'
                + render_next_link(current_folder, next_map.get(p['slug'])))
    body = ['<div class="detail-wrap">',
            '<div class="detail-head">',
            '<div class="detail-head-nav">' + nav_html + '</div>',
            '<h1 class="detail-title">' + esc(p['title']) + '</h1>',
            '</div>']
    if video_html:
        body.append(video_html)
    if stills:
        # data-gm-index + a .gm-data JSON block reuse the exact same desktop
        # click-to-enlarge wiring render_gallery()/main.js already provide
        # (desktopGalleryCells there queries .gallery-bottom-cell[data-gm-
        # index] with no template-specific selector) — no JS changes needed
        # to light up the lightbox here too.
        body.append('<div class="field-label" style="margin-top: 34px;">Gallery</div><div class="stills-grid">')
        for i, u in enumerate(stills):
            body.append('<div class="gallery-bottom-cell" data-gm-index="' + str(i)
                         + '" tabindex="0" role="button">' + img(u, p['title']) + '</div>')
        body.append('</div>')
        data_json = json.dumps([{'url': u, 'alt': p['title']} for u in stills], separators=(',', ':')).replace('</', '<\\/')
        body.append('<script type="application/json" class="gm-data">' + data_json + '</script>')
    body.append('</div>')  # /detail-wrap

    return page(root, p['title'] + ' — Bradley Stonesifer',
                p['title'] + ', shot by cinematographer Bradley Stonesifer.',
                inner_header(root), ''.join(body))


def render_about():
    root = ''
    body = (
        '<div class="about-wrap">'
        '<h1 class="about-title">About</h1>'
        '<div class="about-top">'
        '<div class="about-photo">' + img('assets/images/childhood-trailer.png', 'Childhood photo', lazy=False) + '</div>'
        '<div class="about-caption">The trailer where it started &mdash; Appalachian foothills</div>'
        '<p class="about-intro-p">Bradley Stonesifer was raised in a small agrarian town in central Maryland, '
        'one of four children who spent his school days immersed equally in athletics and art. That upbringing '
        'shaped an eye that finds beauty in the ordinary &mdash; long before it was trained by a camera.</p>'
        '</div>'
        '<p class="about-p">A Summa Cum Laude graduate of the Brooks Institute of Photography and a member of '
        'ICG Local 600, Bradley has spent more than 20 years behind the lens across narrative features, TV shows, '
        'feature documentary, and large-scale commercial work. His favorite kind of project is the one presented '
        'with a world of inconceivable challenges, always finding the beauty in the process. He credits Baraka and '
        'the Qatsi trilogy as an early influence &mdash; wordless, observational filmmaking that shaped how he '
        'thinks about image over dialogue.</p>'
        '<p class="about-p">His narrative work includes <em>Kiss the Future</em> (Official Selection, Berlinale), '
        'the Sundance titles <em>Call Me Lucky</em>, <em>The Vicious Kind</em>, and <em>Me + Her</em>, Bobcat '
        'Goldthwait’s <em>God Bless America</em> (Toronto &amp; SXSW), the LAFF-winning documentary '
        '<em>Fire on the Hill</em>, and Dax Shepard’s <em>Hit &amp; Run</em>, which played in over 3,000 '
        'theaters nationwide. On the commercial side, he’s shot for studios, networks, and brands including '
        'Microsoft, T-Mobile, Google, Samsung, Apple, Absolut, Fossil, and Subaru &mdash; lensing more than a dozen '
        'Super Bowl commercials for T-Mobile and Microsoft, and directing Microsoft’s 2024 Super Bowl campaign, '
        '&ldquo;Watch Me,&rdquo; for its Copilot AI platform.</p>'
        '<p class="about-p">He is also founder and partner of media[box] CAMERA in Culver City, a boutique camera '
        'equipment house serving the film and commercial community. He believes the strongest rules on a project '
        'come from the whole team, not just the director’s chair &mdash; once those rules are set, the film '
        'starts to find its own answers.</p>'
        '<div class="about-pullquote"><p>&ldquo;Cinematography is selfishly me seeing the movie for the first time. '
        'Every take is a connection to a place, a time, a character, a moment.&rdquo;</p></div>'
        '<p class="about-p">Off set, that same rural-meets-refined sensibility follows him &mdash; a bucolic, '
        'unhurried eye paired with a sophisticated, exacting craft. It’s an approach as comfortable on an '
        'indie feature as it is on a national ad campaign, always in service of the people and places in front of '
        'the lens.</p>'
        '<div class="about-section">'
        '<div class="about-section-label">Award-Winning Films, Major Festivals, Theatrical Releases</div>'
        '<ul class="award-list">'
        '<li><em>Kiss the Future</em> &mdash; Official Selection, Berlinale 2023</li>'
        '<li><em>Fire on the Hill</em> &mdash; Winner, LA Film Festival Documentary 2018 (LA Muse Documentary Award)</li>'
        '<li><em>Call Me Lucky</em> &mdash; Sundance Documentary Competition 2015</li>'
        '<li><em>Me + Her</em> &mdash; Sundance Film Festival 2014</li>'
        '<li><em>De Puta Madre</em> &mdash; Best Cinematography 2014, Nom. Best Cinematography 2015, '
        'Columbia Gorge International Film Festival</li>'
        # todo: Hit & Run theater count — prose above says "over 3,000 theaters,"
        # this line says "over 2,800" — needs reconciling with a verified source.
        '<li><em>Hit &amp; Run</em> &mdash; opened to over 2,800 theaters, Oct. 2012</li>'
        '<li><em>God Bless America</em> &mdash; Toronto and SXSW ’11 &amp; ’12</li>'
        '<li><em>Spork</em> &mdash; Tribeca 2010; Winner, Best Feature (Virtual Category)</li>'
        '<li><em>Almost Kings</em> &mdash; LAFF 2010</li>'
        '<li><em>The Vicious Kind</em> &mdash; Sundance 2009; Nom. Best Cinematography, Strasbourg '
        'International Film Festival</li>'
        '</ul></div>'
        '<div class="contact-section">'
        '<div class="contact-eyebrow">Get in Touch</div>'
        '<div class="contact-desc">For general inquiries, press, and personal projects.</div>'
        '<a href="mailto:bradley.stonesifer@gmail.com" class="email-btn">Email Bradley &#8594;</a>'
        '</div>'
        '<div class="contact-section" id="contact-block">'
        '<div class="contact-eyebrow">Commercial Representation</div>'
        '<div class="contact-desc">For bookings and commercial work, contact Process Artists.</div>'
        '<div class="rep-grid">'
        '<div class="rep-person">Rich Schafler<br><a href="mailto:rich@processartists.com">rich@processartists.com</a>'
        '<br>+1 (917) 328-1700</div>'
        '<div class="rep-person">Madeline Saloga<br><a href="mailto:MADELINE@processartists.com">madeline@processartists.com</a>'
        '<br>+1 (630) 816-4404</div>'
        '</div></div>'
        '<div class="contact-section">'
        '<a class="insta-link" href="https://www.instagram.com/bradleystonesifer/">Instagram &#8594; @bradleystonesifer</a>'
        '</div>'
        '</div>'
    )
    return page(root, 'About — Bradley Stonesifer',
                'Bradley Stonesifer is a Los Angeles-based cinematographer and ICG 600 member with 20+ years behind the lens.',
                inner_header(root), body)


# -------------------------------------------------------------------- main --

# Original upload filenames (from the design bundle) -> clean, space-free names.
ASSET_RENAME = {
    'posters-1787856825910-69yy.jpg': 'poster-the-vicious-kind.jpg',
    'posters-1787856825898-bis9.jpg': 'poster-hit-and-run.jpg',
    'spork.jpg': 'poster-spork.jpg',
    'theKid.jpg': 'poster-the-kid.jpg',
    'DePutaMadre.jpg': 'poster-de-puta-madre.jpg',
    'posters-1787856825786-bd9q.jpg': 'poster-god-bless-america.jpg',
    'misfits and monsters.jpg': 'poster-misfits-and-monsters.jpg',
    'KTF.jpg': 'poster-kiss-the-future.jpg',
    'youth governor.jpg': 'poster-the-youth-governor.jpg',
    'fire on the hill.jpg': 'poster-fire-on-the-hill.jpg',
    'Call me Lucky.jpg': 'poster-call-me-lucky.jpg',
}


def copy_assets():
    src_uploads = os.path.join(SITE_DIR, '..', 'project', 'uploads')
    dst = os.path.join(SITE_DIR, 'assets', 'images')
    os.makedirs(dst, exist_ok=True)
    for src_name, dst_name in ASSET_RENAME.items():
        s = os.path.join(src_uploads, src_name)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(dst, dst_name))
    # childhood photo -> clean name used by about.html
    shutil.copyfile(os.path.join(src_uploads, 'pasted-1787086005745-0.png'),
                     os.path.join(dst, 'childhood-trailer.png'))


def rewrite_upload_paths(all_projects):
    """Local project image fields reference 'uploads/<name>' (design-tool
    relative path) — repoint them at assets/images/<clean-name> in the new site."""
    for p in all_projects.values():
        for field in ('posterImage', 'comingSoonImage', 'poster'):
            v = p.get(field)
            if v and v.startswith('uploads/'):
                orig_name = v[len('uploads/'):]
                clean_name = ASSET_RENAME.get(orig_name, orig_name)
                p[field] = 'assets/images/' + clean_name


def write(path, content):
    full = os.path.join(SITE_DIR, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    all_projects = build_all()
    rewrite_upload_paths(all_projects)
    groups = category_display_lists(all_projects)
    next_map = next_project_map(all_projects, groups)

    write('index.html', render_home(all_projects))
    write('about.html', render_about())
    write('commercial.html', render_commercial_page(all_projects))
    for cat_key in ('narrative', 'documentary', 'music_video'):
        write('films/' + CAT_FILENAME[cat_key], render_category_page(cat_key, groups))

    for cat in CATS:
        folder = 'films' if cat['section'] == 'films' else 'commercial'
        for i in range(len(cat['projects'])):
            p = all_projects[cat['key'] + '-' + str(i)]
            if cat['key'] == 'music_video':
                write(p['href'], render_simple_detail_page(p, folder, next_map))
            elif cat['key'] == 'commercial':
                write(p['href'], render_simple_detail_page(p, folder, next_map, video_only=(p['slug'] in VIDEO_ONLY_SLUGS)))
            else:
                write(p['href'], render_detail_page(p, folder, next_map))

    copy_assets()
    print('Built', 6 + len(all_projects), 'pages for', len(all_projects), 'projects.')


if __name__ == '__main__':
    main()
