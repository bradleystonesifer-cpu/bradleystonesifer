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
        if cr['k'] in ('Lead Actors', 'Notable Talent'):
            names = [n.strip() for n in cr['v'].split(',') if n.strip()]
            actors = []
            for i, name in enumerate(names):
                ahref = link_for('Director', name, title)
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


def poster_tile_data(p):
    cs = bool(p.get('comingSoon'))
    # "poster" is the same kind of real-poster-file field as "posterImage"
    # (which comes from the POSTERS/OVERRIDES map) — just settable directly
    # on a project's own data entry. Either one switches the tile off the
    # still-with-title fallback with no layout changes.
    poster_file = p.get('poster') or p.get('posterImage') or ''
    tile_image = '' if cs else (poster_file or p.get('image') or '')
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
    else:
        if len(gallery) > 3:
            gallery[1], gallery[3] = gallery[3], gallery[1]
        gallery_left = gallery[0:3]
        gallery_right = gallery[3:6]
        gallery_bottom = gallery[6:]

    return {
        'creditGroups': group_credits(linked) if linked else [],
        'pressQuotes': press_quotes(linked) if linked else [],
        'episodes': p.get('episodes') or [],
        'logline': p.get('logline') or '',
        'posterImage': p.get('posterImage') or p.get('image'),
        'galleryLeft': gallery_left,
        'galleryRight': gallery_right,
        'galleryBottom': gallery_bottom,
        'galleryAr': gallery_ar,
        'galleryPc': gallery_pc,
        'galleryFlat': gallery,
        'backHref': CAT_FILENAME[p['catKey']] if p['section'] == 'films' else '../commercial.html',
        'backLabel': '← Back' if p['section'] == 'films' else '← All commercial',
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


def collage_tile_type(key, slot, ratio):
    """Classify a COLLAGE_SPEC entry for rendering: posters are fixed and
    unchanged; a scripted project's own gallery-sourced scope tile stays
    scripted; everything else (every non-scripted tile, and every scripted
    tile that was pointing at a Squarespace image/image2/image3 field —
    not allowed for scripted projects) is reassigned by shape to the
    matching non-scripted pool."""
    if slot == 'poster':
        return 'poster'
    if key.startswith('narrative-') and slot.startswith('gallery:') and ratio.startswith('2.35'):
        return 'scripted-scope'
    return '16x9' if ratio == '16/9' else 'scope'


def build_collage_pools(all_projects):
    """Three image pools for the randomized homepage collage, keyed by
    tile type. Scripted pool: every gallery image (real width >= 1500px)
    from narrative projects with 8+ galleryImages — automatic, so a film
    that gets a gallery later joins with no spec edit. Non-scripted pools:
    the (key, slot) pairs COLLAGE_SPEC already uses at that ratio today —
    those are the only non-scripted images anyone has actually vetted at
    that shape (Squarespace URLs can't be dimension-checked locally)."""
    scripted = []
    for key, p in all_projects.items():
        if not key.startswith('narrative-'):
            continue
        gallery = p.get('galleryImages') or []
        if len(gallery) < SCRIPTED_POOL_MIN_GALLERY:
            continue
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
            scripted.append({'url': url, 'href': p['href'], 'title': p['title']})

    non_scripted_16x9 = []
    non_scripted_scope = []
    seen = set()
    for key, slot, ratio, _span in COLLAGE_SPEC:
        ttype = collage_tile_type(key, slot, ratio)
        if ttype not in ('16x9', 'scope') or key.startswith('narrative-'):
            continue
        if (key, slot) in seen:
            continue
        seen.add((key, slot))
        p = all_projects[key]
        url = slot_url(all_projects, key, slot)
        if not url:
            continue
        item = {'url': url, 'href': p['href'], 'title': p['title']}
        (non_scripted_16x9 if ttype == '16x9' else non_scripted_scope).append(item)

    return {'scripted': scripted, '16x9': non_scripted_16x9, 'scope': non_scripted_scope}


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


def render_video_block(p, which, aspect='16/9'):
    """which: 'first' (top player) or 'second' (bottom Selects player)."""
    embed = p.get('videoEmbed') if which == 'first' else p.get('secondVideoEmbed')
    if not embed:
        return ''
    vid = vimeo_id(embed)
    # videoThumb (per-project, i.vimeocdn.com) wins when set; falls back to
    # the original p.get('image') otherwise — the-vicious-kind never sets
    # videoThumb, so its output is byte-for-byte unchanged.
    thumb_url = p.get('videoThumb') or p.get('image')
    if which == 'first':
        vattr = ' data-vimeo-id="' + vid + '"' if vid else ''
        return (
            '<div class="video-wrap" data-video-wrap style="aspect-ratio: ' + aspect + ';" data-embed-src="' + esc(embed) + '">'
            '<div class="video-thumb-overlay" data-video-thumb' + vattr + '>'
            + img(thumb_url, p['title']) +
            '<div class="play-btn"><div class="play-btn-tri"></div></div>'
            '</div></div>'
        )
    # second / "Selects" player. secondVideoThumb is optional — when unset
    # (the-vicious-kind never sets it) this renders exactly as before, a
    # plain gradient card with no image, byte-for-byte unchanged.
    second_thumb = p.get('secondVideoThumb')
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
        return render_video_block(p, 'first', aspect)
    videos = VIDEOS.get(p.get('slug'))
    if not videos:
        return ''
    # Each video carries its own Vimeo thumbnail (i.vimeocdn.com, or a
    # local root-relative still routed through asset()); falls back to
    # the project's existing still only if one wasn't supplied.
    thumb_url = asset(root, videos[0].get('thumb') or p.get('image'))
    main_src = vimeo_dnt_url(videos[0]['url'])
    play_label = 'Play ' + p['title']
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


def _gallery_item(item, title):
    """A gallery slot is either a plain URL string (title used as alt, the
    original behavior) or an (url, alt) pair when the project supplies
    per-image alt text via galleryAlts."""
    return item if isinstance(item, tuple) else (item, title)


def render_gallery(root, dd, title):
    # asset(root, url) root-prefixes a local path (no-op for absolute
    # http(s) URLs, e.g. the legacy Squarespace-hosted galleries) — same
    # treatment the poster image already gets, so galleryImages can store
    # plain root-relative paths like every other local image field instead
    # of a hardcoded '../' that breaks when the same path is reused
    # elsewhere (e.g. a COLLAGE_SPEC "gallery:N" homepage tile, which sits
    # at site root rather than inside /films/ or /commercial/).
    def cell(item):
        url, alt = _gallery_item(item, title)
        return '<div class="gallery-cell">' + img(asset(root, url), alt) + '</div>'
    left = ''.join(cell(u) for u in dd['galleryLeft'] if _gallery_item(u, title)[0])
    right = ''.join(cell(u) for u in dd['galleryRight'] if _gallery_item(u, title)[0])
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
    if bottom:
        out.append('<div class="gallery-bottom"' + bottom_style + '>')
        for item in bottom:
            url, alt = _gallery_item(item, title)
            if url:
                out.append('<div class="gallery-bottom-cell">' + img(asset(root, url), alt) + '</div>')
        out.append('</div>')
    return ''.join(out)


GALLERY_MOBILE_INITIAL = 16
GALLERY_MOBILE_BATCH = 16


def render_gallery_mobile(root, dd, title):
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
    cells = []
    for i, (url, alt) in enumerate(items):
        full_url = asset(root, url)
        if i < GALLERY_MOBILE_INITIAL:
            inner = img(full_url, alt, lazy=(i > 1))
        else:
            inner = ('<img alt="' + esc(alt) + '" decoding="async" draggable="false" data-gm-src="'
                      + esc(full_url) + '">')
        hidden = ' gm-hidden' if i >= GALLERY_MOBILE_INITIAL else ''
        cells.append('<button type="button" class="gm-cell' + hidden + '" data-gm-index="' + str(i)
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


def page_rel(current_folder, target_href):
    """Resolve a root-relative href ('films/x.html') for a page sitting in
    current_folder ('' | 'films' | 'commercial')."""
    if current_folder == '':
        return target_href
    prefix = current_folder + '/'
    if target_href.startswith(prefix):
        return target_href[len(prefix):]
    return '../' + target_href


# ---------------------------------------------------------------- pages --

def render_collage_tile(current_folder, item):
    """Fixed tile — posters only; never randomized."""
    href = page_rel(current_folder, item['href'])
    style = 'grid-column: span ' + str(item['span']) + '; aspect-ratio: ' + item['ratio'] + ';'
    return (
        '<a class="collage-tile" href="' + href + '" style="' + style + '" draggable="false">'
        + img(item['url'], item['title']) +
        '<div class="collage-scrim"><span>' + esc(item['title']) + '</span></div>'
        '</a>'
    )


def render_random_collage_tile(default_item, ratio, span, pool_key):
    """Randomizable tile — server renders a deterministic default (real
    href, no img src) plus a <noscript> fallback image, so the page works
    and links correctly with JS off or for crawlers. main.js replaces the
    src/href/alt on load from the matching pool, picking something new on
    every page view."""
    style = 'grid-column: span ' + str(span) + '; aspect-ratio: ' + ratio + ';'
    alt = esc(default_item['title'])
    return (
        '<a class="collage-tile" href="' + esc(default_item['href']) + '" data-pool="' + pool_key
        + '" style="' + style + '" draggable="false">'
        '<img alt="' + alt + '" decoding="async" draggable="false">'
        '<noscript>' + img(default_item['url'], default_item['title']) + '</noscript>'
        '<div class="collage-scrim"><span>' + alt + '</span></div>'
        '</a>'
    )


def render_home(all_projects):
    pools = build_collage_pools(all_projects)
    counters = {'scripted': 0, '16x9': 0, 'scope': 0}
    tiles = []
    for key, slot, ratio, span in COLLAGE_SPEC:
        ttype = collage_tile_type(key, slot, ratio)
        if ttype == 'poster':
            p = all_projects[key]
            url = slot_url(all_projects, key, slot)
            tiles.append(render_collage_tile('', {'href': p['href'], 'title': p['title'], 'url': url, 'ratio': ratio, 'span': span}))
            continue
        pool_key = 'scripted' if ttype == 'scripted-scope' else ttype
        pool = pools[pool_key]
        if pool:
            idx = counters[pool_key] % len(pool)
            counters[pool_key] += 1
            default_item = pool[idx]
        else:
            default_item = {'url': '', 'href': '#', 'title': ''}
        tiles.append(render_random_collage_tile(default_item, ratio, span, pool_key))

    # Escaped so a stray "</script>" inside any title/url can't prematurely
    # close the data block.
    pools_json = json.dumps(pools, separators=(',', ':')).replace('</', '<\\/')

    collage_script = (
        '<script>(function(){'
        'var data=document.getElementById("collage-pools");'
        'if(!data)return;'
        'var pools;try{pools=JSON.parse(data.textContent);}catch(e){return;}'
        'var tiles=document.querySelectorAll(".collage-tile[data-pool]");'
        'var used={};Object.keys(pools).forEach(function(k){used[k]=[];});'
        'var lastTitle=null;'
        'tiles.forEach(function(tile,i){'
        'var key=tile.getAttribute("data-pool");'
        'var pool=pools[key];'
        'if(!pool||!pool.length)return;'
        'var avail=pool.filter(function(it){return used[key].indexOf(it.url)===-1;});'
        'if(!avail.length){used[key]=[];avail=pool;}'
        'var preferred=avail.filter(function(it){return it.title!==lastTitle;});'
        'var choices=preferred.length?preferred:avail;'
        'var item=choices[Math.floor(Math.random()*choices.length)];'
        'used[key].push(item.url);lastTitle=item.title;'
        'var img=tile.querySelector("img");'
        'if(img){img.src=item.url;img.alt=item.title;if(i>3)img.loading="lazy";}'
        'tile.href=item.href;'
        'var scrim=tile.querySelector(".collage-scrim span");'
        'if(scrim)scrim.textContent=item.title;'
        '});'
        '})();</script>'
    )
    body = (
        '<div class="collage-outer"><div class="collage-grid">' + ''.join(tiles) + '</div></div>'
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


def render_detail_page(p, current_folder):
    root = '../'
    dd = detail_data(p)
    aspect = p.get('videoAspect', '16/9')

    left_html = render_credit_groups(dd['creditGroups']) if dd['creditGroups'] else ''
    center_html = render_video_player(p, aspect, root)
    right_parts = []
    if dd['logline']:
        right_parts.append('<div class="field-label">Logline</div><p class="logline-text">' + esc(dd['logline']) + '</p>')
    right_parts.append(render_press_quotes(dd['pressQuotes']))
    if p.get('watchUrl'):
        right_parts.append('<a class="watch-btn" href="' + esc(p['watchUrl']) + '" target="_blank" rel="noopener">' + esc(p.get('watchLabel', 'Watch')) + '</a>')
    right_html = ''.join(right_parts)

    body = ['<div class="detail-wrap">',
            '<div class="detail-head">',
            '<a class="back-link" href="' + dd['backHref'] + '">' + esc(dd['backLabel']) + '</a>',
            '<h1 class="detail-title">' + esc(p['title']) + '</h1>']
    if p.get('creditLine'):
        body.append('<div class="detail-credit-line">' + esc(p['creditLine']) + '</div>')
    body.append('</div>')
    if left_html or center_html or right_html:
        body.append('<div class="detail-grid">')
        if left_html:
            body.append('<div class="detail-col-left"><div>' + left_html + '</div></div>')
        if center_html:
            body.append('<div class="detail-col-center">' + center_html + '</div>')
        if right_html:
            body.append('<div class="detail-col-right"><div>' + right_html + '</div></div>')
        body.append('</div>')  # /detail-grid

    if dd['episodes']:
        body.append('<div class="field-label">Episodes</div><div class="episodes-list">')
        for ep in dd['episodes']:
            body.append('<div class="episode-row"><div class="episode-n">' + esc(ep['n']) + '</div>'
                         '<div class="episode-title">' + esc(ep['title']) + '</div>'
                         '<div class="episode-synopsis">' + esc(ep['synopsis']) + '</div></div>')
        body.append('</div>')

    body.append(render_gallery(root, dd, p['title']))
    body.append(render_gallery_mobile(root, dd, p['title']))
    body.append(render_video_block(p, 'second'))
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


def render_simple_detail_page(p, current_folder, video_only=False):
    """Music Video / Commercial detail pages: back link, title, a single
    full-width 16:9 video player, and a stills gallery — no credits sidebar."""
    root = '../'
    aspect = p.get('videoAspect', '16/9')
    back_href = CAT_FILENAME[p['catKey']] if p['section'] == 'films' else '../commercial.html'
    back_label = '← Back' if p['section'] == 'films' else '← All commercial'

    video_html = render_video_player(p, aspect, root)
    stills = [] if video_only else (p.get('galleryImages') or [u for u in (p.get('image2'), p.get('image3')) if u])

    body = ['<div class="detail-wrap">',
            '<div class="detail-head">',
            '<a class="back-link" href="' + back_href + '">' + esc(back_label) + '</a>',
            '<h1 class="detail-title">' + esc(p['title']) + '</h1>',
            '</div>']
    if video_html:
        body.append(video_html)
    if stills:
        body.append('<div class="field-label" style="margin-top: 34px;">Gallery</div><div class="stills-grid">')
        for u in stills:
            body.append('<div class="gallery-bottom-cell">' + img(u, p['title']) + '</div>')
        body.append('</div>')
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
    'ME+HER.jpg': 'poster-me-plus-her.jpg',
    'almost kings.jpg': 'poster-almost-kings.jpg',
    'spork.jpg': 'poster-spork.jpg',
    'theKid.jpg': 'poster-the-kid.jpg',
    'DePutaMadre.jpg': 'poster-de-puta-madre.jpg',
    'pasted-1787862845306-0.png': 'poster-woman-child.png',
    'posters-1787856825786-bd9q.jpg': 'poster-god-bless-america.jpg',
    'misfits and monsters.jpg': 'poster-misfits-and-monsters.jpg',
    'KTF.jpg': 'poster-kiss-the-future.jpg',
    'youth governor.jpg': 'poster-the-youth-governor.jpg',
    'fire on the hill.jpg': 'poster-fire-on-the-hill.jpg',
    'Call me Lucky.jpg': 'poster-call-me-lucky.jpg',
    'house of Ideas.avif': 'coming-soon-house-of-ideas.avif',
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
                write(p['href'], render_simple_detail_page(p, folder))
            elif cat['key'] == 'commercial':
                write(p['href'], render_simple_detail_page(p, folder, video_only=(p['slug'] in VIDEO_ONLY_SLUGS)))
            else:
                write(p['href'], render_detail_page(p, folder))

    copy_assets()
    print('Built', 6 + len(all_projects), 'pages for', len(all_projects), 'projects.')


if __name__ == '__main__':
    main()
