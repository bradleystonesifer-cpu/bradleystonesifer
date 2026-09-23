#!/usr/bin/env python3
"""Static site generator for the Bradley Stonesifer cinematographer portfolio.

Ported (not framework-copied) from the Claude Design canvas source at
project/Bradley Stonesifer Site.dc.html — same visual system, real
multi-page URLs instead of the design tool's client-side view switching.
Run `python3 build.py` from this directory to (re)generate every page.
"""
import os
import re
import shutil
import urllib.parse

from data import CATS, OVERRIDES, POSTERS, COLLAGE_SPEC, CATEGORY_ORDER

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
FESTIVAL_DOMAINS = {
    'sundance': 'sundance.org', 'tribeca': 'tribecafilm.com', 'sxsw': 'sxsw.com',
    'cannes': 'festival-cannes.com', 'tiff': 'tiff.net', 'toronto': 'tiff.net', 'berlinale': 'berlinale.de',
}
PRESS_DOMAINS = {
    'variety': 'variety.com', 'indiewire': 'indiewire.com', 'hollywood reporter': 'hollywoodreporter.com',
    'vulture': 'vulture.com', 'deadline': 'deadline.com', 'rolling stone': 'rollingstone.com',
}
DEFAULT_TECH_SPECS = [
    {'k': 'Camera', 'v': 'Add camera'},
    {'k': 'Lens', 'v': 'Add lens set'},
    {'k': 'Look', 'v': 'Add look / LUT notes'},
]
CAT_FILENAME = {'narrative': 'scripted.html', 'documentary': 'documentary.html', 'music_video': 'music-video.html'}

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
    return {
        'comingSoon': cs,
        'hasTileImage': not cs,
        'tileImage': '' if cs else (p.get('posterImage') or p.get('image')),
        'noPoster': (not cs) and not p.get('posterImage'),
        'artImage': p.get('comingSoonImage') or '',
        'laurels': laurels_for(p),
    }


def detail_data(p):
    title = p['title']
    if p.get('overrideCredits'):
        raw_credits = p['overrideCredits']
    elif p['section'] == 'films':
        raw_credits = [
            {'k': 'Director', 'v': 'Add director name'},
            {'k': 'Lead Actors', 'v': 'Add lead cast'},
            {'k': 'Notable Festivals', 'v': p.get('note') or 'Add festival selections'},
            {'k': 'Press', 'v': 'Add press quote'},
        ]
    else:
        raw_credits = [
            {'k': 'Client', 'v': title.split(' - ')[0] if title else 'Add client'},
            {'k': 'Agency', 'v': 'Add agency'},
            {'k': 'Director', 'v': 'Add director name'},
            {'k': 'Notable Talent', 'v': 'Add talent'},
        ]
    linked = with_links(raw_credits, title)

    gallery_source = p.get('galleryImages') or [u for u in (p.get('image2'), p.get('image3')) if u]
    gallery = list(gallery_source)
    if len(gallery) > 3:
        gallery[1], gallery[3] = gallery[3], gallery[1]

    return {
        'creditGroups': group_credits(linked),
        'pressQuotes': press_quotes(linked),
        'techSpecs': p.get('techSpecs') or DEFAULT_TECH_SPECS,
        'episodes': p.get('episodes') or [],
        'logline': p.get('logline') or 'Add a one-sentence logline for this project.',
        'posterImage': p.get('posterImage') or p.get('image'),
        'galleryLeft': gallery[0:3],
        'galleryRight': gallery[3:6],
        'galleryBottom': gallery[6:],
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
    return ''


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
    return '<img src="' + esc(src) + '" alt="' + esc(alt) + '"' + cls_attr + loading + extra + '>'


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
    thumb_url = p.get('image')
    if which == 'first':
        vattr = ' data-vimeo-id="' + vid + '"' if vid else ''
        return (
            '<div class="video-wrap" data-video-wrap style="aspect-ratio: ' + aspect + ';" data-embed-src="' + esc(embed) + '">'
            '<div class="video-thumb-overlay" data-video-thumb' + vattr + '>'
            + img(thumb_url, p['title']) +
            '<div class="play-btn"><div class="play-btn-tri"></div></div>'
            '</div></div>'
        )
    # second / "Selects" player
    return (
        '<div class="selects-wrap">'
        '<div class="selects-video" data-video-wrap data-embed-src="' + esc(embed) + '">'
        '<div class="selects-thumb" data-video-thumb>'
        '<div class="selects-inner"><span class="selects-label">Selects</span>'
        '<div class="play-btn"><div class="play-btn-tri"></div></div></div>'
        '</div></div></div>'
    )


def render_gallery(root, dd, title):
    def cell(url):
        return '<div class="gallery-cell">' + img(url, title) + '</div>'
    left = ''.join(cell(u) for u in dd['galleryLeft'] if u)
    right = ''.join(cell(u) for u in dd['galleryRight'] if u)
    poster = asset(root, dd['posterImage'])
    out = ['<div class="field-label" style="margin-top: 34px;">Gallery</div>', '<div class="gallery-main">']
    out.append('<div class="gallery-side"><div class="gallery-side-grid">' + left + '</div></div>')
    if poster:
        out.append('<div class="gallery-poster">' + img(poster, title + ' poster', lazy=False) + '</div>')
    out.append('<div class="gallery-side"><div class="gallery-side-grid">' + right + '</div></div>')
    out.append('</div>')
    bottom = dd['galleryBottom']
    if bottom:
        out.append('<div class="gallery-bottom">')
        for u in bottom:
            if u:
                out.append('<div class="gallery-bottom-cell">' + img(u, title) + '</div>')
        out.append('</div>')
    return ''.join(out)


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
    href = page_rel(current_folder, item['href'])
    style = 'grid-column: span ' + str(item['span']) + '; aspect-ratio: ' + item['ratio'] + ';'
    return (
        '<a class="collage-tile" href="' + href + '" style="' + style + '">'
        + img(item['url'], item['title']) +
        '<div class="collage-scrim"><span>' + esc(item['title']) + '</span></div>'
        '</a>'
    )


def render_home(all_projects):
    tiles = []
    for key, slot, ratio, span in COLLAGE_SPEC:
        p = all_projects[key]
        url = slot_url(all_projects, key, slot)
        tiles.append(render_collage_tile('', {'href': p['href'], 'title': p['title'], 'url': url, 'ratio': ratio, 'span': span}))
    body = (
        '<div class="collage-outer"><div class="collage-grid">' + ''.join(tiles) + '</div></div>'
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
    out = ['<a class="poster-tile" href="' + href + '">']
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
        cells.append('<a class="triptych-img-wrap" href="' + href + '">' + img(u, p['title']) + '<div class="triptych-hover"></div></a>')
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
    body = ['<div class="detail-wrap">',
            '<div class="detail-head">',
            '<a class="back-link" href="' + dd['backHref'] + '">' + esc(dd['backLabel']) + '</a>',
            '<h1 class="detail-title">' + esc(p['title']) + '</h1>',
            '</div>',
            '<div class="detail-grid">',
            '<div class="detail-col-left"><div>' + render_credit_groups(dd['creditGroups']) + '</div></div>',
            '<div class="detail-col-center">']
    body.append(render_video_block(p, 'first', aspect))
    body.append('<div class="tech-banner">')
    for ts in dd['techSpecs']:
        body.append('<div class="tech-cell"><div class="tech-key">' + esc(ts['k']) + '</div><div class="tech-val">' + esc(ts['v']) + '</div></div>')
    body.append('</div></div>')
    body.append('<div class="detail-col-right"><div>')
    body.append('<div class="field-label">Logline</div><p class="logline-text">' + esc(dd['logline']) + '</p>')
    body.append(render_press_quotes(dd['pressQuotes']))
    if p.get('watchUrl'):
        body.append('<a class="watch-btn" href="' + esc(p['watchUrl']) + '" target="_blank" rel="noopener">' + esc(p.get('watchLabel', 'Watch')) + '</a>')
    body.append('</div></div>')
    body.append('</div>')  # /detail-grid

    if dd['episodes']:
        body.append('<div class="field-label">Episodes</div><div class="episodes-list">')
        for ep in dd['episodes']:
            body.append('<div class="episode-row"><div class="episode-n">' + esc(ep['n']) + '</div>'
                         '<div class="episode-title">' + esc(ep['title']) + '</div>'
                         '<div class="episode-synopsis">' + esc(ep['synopsis']) + '</div></div>')
        body.append('</div>')

    body.append(render_gallery(root, dd, p['title']))
    body.append(render_video_block(p, 'second'))
    body.append('</div>')  # /detail-wrap

    return page(root, p['title'] + ' — Bradley Stonesifer',
                (dd['logline'] if not dd['logline'].startswith('Add a') else p['title'] + ', shot by cinematographer Bradley Stonesifer.'),
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
        '<li>&ldquo;Kiss the Future&rdquo; &mdash; Official Selection, Berlinale 2023</li>'
        '<li>&ldquo;Fire on the Hill&rdquo; &mdash; Winner, LAFF Documentary 2020</li>'
        '<li>&ldquo;Call Me Lucky&rdquo; &mdash; Sundance Documentary Competition 2015</li>'
        '<li>&ldquo;De Puta Madre&rdquo; &mdash; Best Cinematography 2014, Nom. Best Cinematography 2015, '
        'Columbia Gorge International Film Festival</li>'
        '<li>&ldquo;Hit &amp; Run&rdquo; &mdash; opened to over 2,800 theaters, Oct. 2012</li>'
        '<li>&ldquo;God Bless America&rdquo; &mdash; Toronto and SXSW ’11 &amp; ’12</li>'
        '<li>&ldquo;Spork&rdquo; &mdash; Tribeca 2010; Winner, Best Feature (Virtual Category)</li>'
        '<li>&ldquo;Almost Kings&rdquo; &mdash; LAFF 2010</li>'
        '<li>&ldquo;The Vicious Kind&rdquo; &mdash; Sundance 2009; Nom. Best Cinematography, Strasbourg '
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
        for field in ('posterImage', 'comingSoonImage'):
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
            write(p['href'], render_detail_page(p, folder))

    copy_assets()
    print('Built', 6 + len(all_projects), 'pages for', len(all_projects), 'projects.')


if __name__ == '__main__':
    main()
