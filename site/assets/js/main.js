(function () {
  'use strict';

  // Sticky inner header: fade the background gradient once the page scrolls,
  // matching the original 15%-more-transparent-on-scroll behavior.
  var innerHeader = document.querySelector('.inner-header');
  if (innerHeader) {
    var onScroll = function () {
      var scrolled = window.scrollY > 20;
      innerHeader.classList.toggle('scrolled', scrolled);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Click-to-play video embeds: swap a thumbnail + play button for a live
  // iframe on click, with autoplay enabled (Vimeo/YouTube).
  document.querySelectorAll('[data-video-thumb]').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      var wrap = thumb.closest('[data-video-wrap]');
      if (!wrap) return;
      var src = wrap.getAttribute('data-embed-src');
      if (!src) return;
      if (!/[?&]autoplay=/.test(src)) {
        src += (src.indexOf('?') === -1 ? '?' : '&') + 'autoplay=1';
      }
      var iframe = document.createElement('iframe');
      iframe.src = src;
      iframe.allow = 'autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share';
      iframe.allowFullscreen = true;
      iframe.style.cssText = 'position:absolute;top:0;left:-1px;width:calc(100% + 2px);height:100%;border:0;display:block;';
      wrap.innerHTML = '';
      wrap.appendChild(iframe);
    });
  });

  // Pull each project's real Vimeo thumbnail (falls back to the static still
  // already in the page markup if the fetch fails or the video is YouTube).
  document.querySelectorAll('[data-vimeo-id]').forEach(function (el) {
    var id = el.getAttribute('data-vimeo-id');
    if (!id) return;
    var img = el.querySelector('img');
    if (!img) return;
    fetch('https://vimeo.com/api/oembed.json?url=' + encodeURIComponent('https://vimeo.com/' + id) + '&width=1920')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.thumbnail_url) {
          img.src = d.thumbnail_url.replace(/_\d+x\d+(\.\w+)?(\?.*)?$/, '_1920x1080$1');
        }
      })
      .catch(function () {});
  });

  // Deep-link from the footer "Contact" link into the About page's
  // representation block, offset clear of the sticky header.
  if (window.location.hash === '#contact-block') {
    var target = document.getElementById('contact-block');
    if (target) {
      requestAnimationFrame(function () {
        var top = target.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: top, behavior: 'smooth' });
      });
    }
  }

  // Preconnect to player.vimeo.com on first hover/focus of any play
  // control (old or new) rather than on page load, so visitors who never
  // touch a player never pay for that connection.
  var vimeoPreconnected = false;
  function preconnectVimeo() {
    if (vimeoPreconnected) return;
    vimeoPreconnected = true;
    var link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = 'https://player.vimeo.com';
    document.head.appendChild(link);
  }
  document.querySelectorAll('[data-video-thumb]').forEach(function (el) {
    el.addEventListener('mouseenter', preconnectVimeo, { once: true });
    el.addEventListener('focus', preconnectVimeo, { once: true });
  });

  // Vimeo facade player (added for new video pages) — same lazy-load-on-
  // click pattern as the one above, but on its own data attributes so it
  // never touches that original mechanism's elements or behavior.
  document.querySelectorAll('[data-vimeo-wrap]').forEach(function (wrap) {
    function loadVideo(src) {
      var iframe = document.createElement('iframe');
      iframe.src = src;
      iframe.title = wrap.getAttribute('data-vimeo-title') || 'Video player';
      iframe.allow = 'autoplay; fullscreen; picture-in-picture';
      iframe.allowFullscreen = true;
      iframe.style.cssText = 'position:absolute;top:0;left:-1px;width:calc(100% + 2px);height:100%;border:0;display:block;';
      wrap.innerHTML = '';
      wrap.appendChild(iframe);
    }
    function bindPlayButton(btn) {
      btn.addEventListener('click', function () {
        var src = wrap.getAttribute('data-vimeo-src');
        if (!src) return;
        loadVideo(src + (src.indexOf('?') === -1 ? '?' : '&') + 'autoplay=1');
      });
      btn.addEventListener('mouseenter', preconnectVimeo, { once: true });
      btn.addEventListener('focus', preconnectVimeo, { once: true });
    }
    // Rebuilds the facade (thumbnail + play button) for a different video —
    // used when a label button is clicked, so the thumb visibly swaps to
    // match the newly-selected video instead of jumping straight to
    // playback; the visitor still has to press Play to actually load it.
    function showFacade(thumbSrc, alt) {
      wrap.innerHTML = '';
      var overlay = document.createElement('div');
      overlay.className = 'video-thumb-overlay';
      var thumbImg = document.createElement('img');
      thumbImg.src = thumbSrc;
      thumbImg.alt = alt;
      thumbImg.loading = 'lazy';
      thumbImg.decoding = 'async';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'video-click-btn';
      btn.setAttribute('data-vimeo-play', '');
      btn.setAttribute('aria-label', wrap.getAttribute('data-vimeo-play-label') || alt);
      btn.innerHTML = '<div class="play-btn"><div class="play-btn-tri"></div></div>';
      overlay.appendChild(thumbImg);
      overlay.appendChild(btn);
      wrap.appendChild(overlay);
      bindPlayButton(btn);
    }
    var playBtn = wrap.querySelector('[data-vimeo-play]');
    if (playBtn) bindPlayButton(playBtn);

    wrap.parentElement.querySelectorAll('[data-vimeo-select]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var src = btn.getAttribute('data-vimeo-select');
        var thumb = btn.getAttribute('data-vimeo-select-thumb');
        if (!src) return;
        wrap.setAttribute('data-vimeo-src', src);
        wrap.parentElement.querySelectorAll('.video-select-btn').forEach(function (b) {
          b.classList.toggle('active', b === btn);
        });
        showFacade(thumb, wrap.getAttribute('data-vimeo-title') || '');
      });
      btn.addEventListener('mouseenter', preconnectVimeo, { once: true });
      btn.addEventListener('focus', preconnectVimeo, { once: true });
    });
  });

  // Mobile gallery (<=600px): "Show more" reveals the next batch of
  // still-unfetched cells, and tapping any cell opens a shared
  // full-screen lightbox with swipe/arrow navigation across every still
  // (including ones never revealed in the grid — those fetch on demand).
  var GM_BATCH = 16;
  var gmLightbox = null;
  var gmLastFocused = null;
  function gmOpenLightbox(items, index) {
    if (!items.length) return;
    gmLastFocused = document.activeElement;
    if (!gmLightbox) {
      gmLightbox = document.createElement('div');
      gmLightbox.className = 'gm-lightbox';
      gmLightbox.setAttribute('role', 'dialog');
      gmLightbox.setAttribute('aria-modal', 'true');
      gmLightbox.setAttribute('aria-label', 'Image viewer');
      gmLightbox.tabIndex = -1;
      gmLightbox.innerHTML =
        '<button type="button" class="gm-lb-close" aria-label="Close">&times;</button>' +
        '<button type="button" class="gm-lb-prev" aria-label="Previous">&#8249;</button>' +
        '<img alt="">' +
        '<button type="button" class="gm-lb-next" aria-label="Next">&#8250;</button>';
      document.body.appendChild(gmLightbox);
      gmLightbox.querySelector('.gm-lb-close').addEventListener('click', gmCloseLightbox);
      gmLightbox.addEventListener('click', function (e) {
        if (e.target === gmLightbox) gmCloseLightbox();
      });
      gmLightbox.querySelector('.gm-lb-prev').addEventListener('click', function () { gmStep(-1); });
      gmLightbox.querySelector('.gm-lb-next').addEventListener('click', function () { gmStep(1); });
      document.addEventListener('keydown', function (e) {
        if (gmLightbox.style.display !== 'flex') return;
        if (e.key === 'Escape') gmCloseLightbox();
        if (e.key === 'ArrowLeft') gmStep(-1);
        if (e.key === 'ArrowRight') gmStep(1);
      });
      var touchX = null;
      gmLightbox.addEventListener('touchstart', function (e) { touchX = e.touches[0].clientX; }, { passive: true });
      gmLightbox.addEventListener('touchend', function (e) {
        if (touchX === null) return;
        var dx = e.changedTouches[0].clientX - touchX;
        if (Math.abs(dx) > 40) gmStep(dx < 0 ? 1 : -1);
        touchX = null;
      }, { passive: true });
    }
    gmLightbox.dataset.items = JSON.stringify(items);
    gmLightbox.dataset.index = index;
    gmRenderLightbox();
    gmLightbox.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    gmLightbox.querySelector('.gm-lb-close').focus();
  }
  function gmRenderLightbox() {
    var list = JSON.parse(gmLightbox.dataset.items);
    var i = parseInt(gmLightbox.dataset.index, 10);
    var item = list[i];
    var img = gmLightbox.querySelector('img');
    img.src = item.url;
    img.alt = item.alt || '';
  }
  function gmStep(dir) {
    var list = JSON.parse(gmLightbox.dataset.items);
    var i = parseInt(gmLightbox.dataset.index, 10);
    i = (i + dir + list.length) % list.length;
    gmLightbox.dataset.index = i;
    gmRenderLightbox();
  }
  function gmCloseLightbox() {
    if (gmLightbox) gmLightbox.style.display = 'none';
    document.body.style.overflow = '';
    if (gmLastFocused && typeof gmLastFocused.focus === 'function') gmLastFocused.focus();
    gmLastFocused = null;
  }

  document.querySelectorAll('[data-gallery-mobile]').forEach(function (wrap) {
    var dataEl = wrap.querySelector('.gm-data');
    var items = [];
    if (dataEl) {
      try { items = JSON.parse(dataEl.textContent); } catch (e) {}
    }
    var cells = wrap.querySelectorAll('.gm-cell');
    var moreBtn = wrap.querySelector('[data-gm-more]');
    var revealed = GM_BATCH;

    if (moreBtn) {
      moreBtn.addEventListener('click', function () {
        var upTo = revealed + GM_BATCH;
        cells.forEach(function (cell) {
          var idx = parseInt(cell.getAttribute('data-gm-index'), 10);
          if (idx < upTo) {
            cell.classList.remove('gm-hidden');
            var img = cell.querySelector('img[data-gm-src]');
            if (img) {
              img.src = img.getAttribute('data-gm-src');
              img.loading = 'lazy';
              img.removeAttribute('data-gm-src');
            }
          }
        });
        revealed = upTo;
        if (revealed >= cells.length) moreBtn.remove();
      });
    }

    cells.forEach(function (cell) {
      cell.addEventListener('click', function () {
        var idx = parseInt(cell.getAttribute('data-gm-index'), 10);
        gmOpenLightbox(items, idx);
      });
    });
  });

  // Per-episode gallery selector (Misfits & Monsters). Separate from the
  // generic [data-gallery-mobile] wiring above — behavior genuinely
  // differs (featured count of 8 not 16, a real show-more/less toggle,
  // and switching episodes resets that toggle) — but reuses the same
  // .gm-cell/.gm-data/.gm-more markup inside each panel, and opens the
  // same shared lightbox, scoped to just that panel's own stills.
  //
  // The selector row (in the right/logline column) and the panels it
  // controls (full-width, below the whole detail-grid) are no longer
  // DOM siblings, so they're wired together by their own top-level
  // selectors instead of a shared wrapper — only one of each exists on
  // the page, so this doesn't need to be a multi-instance loop.
  var EP_FEATURED = 8;
  var epSelectorRow = document.querySelector('[data-episode-select-row]');
  var epPanelsWrap = document.querySelector('[data-episode-panels]');
  if (epSelectorRow && epPanelsWrap) {
    var panels = {};
    epPanelsWrap.querySelectorAll('[data-episode-panel]').forEach(function (panel) {
      panels[panel.getAttribute('data-episode-panel')] = panel;
    });
    var buttons = epSelectorRow.querySelectorAll('[data-ep-select]');

    function collapsePanel(panel) {
      var moreBtn = panel.querySelector('[data-gm-more]');
      panel.querySelectorAll('.gm-cell').forEach(function (cell) {
        if (parseInt(cell.getAttribute('data-gm-index'), 10) >= EP_FEATURED) {
          cell.classList.add('gm-hidden');
        }
      });
      if (moreBtn) {
        moreBtn.textContent = moreBtn.getAttribute('data-show-more-label');
        moreBtn.setAttribute('aria-expanded', 'false');
      }
    }

    // The 4:3 row (narrower cells, so more would naturally fit per row)
    // must never run wider than the 16:9 row above it. Measures the
    // 16:9 row's actual achieved width — not the full container, which
    // it rarely fills exactly — and caps the 4:3 row to that, so it
    // wraps at the same boundary instead of the full container width.
    function syncNarrowRowWidth(panel) {
      var wideRow = panel.querySelector('[data-ep-row-wide]');
      var narrowRow = panel.querySelector('[data-ep-row-narrow]');
      if (!wideRow || !narrowRow) return;
      var wideCells = wideRow.querySelectorAll('.gm-cell:not(.gm-hidden)');
      if (!wideCells.length) { narrowRow.style.maxWidth = ''; return; }
      var left = wideRow.getBoundingClientRect().left;
      var maxRight = 0;
      wideCells.forEach(function (cell) {
        maxRight = Math.max(maxRight, cell.getBoundingClientRect().right - left);
      });
      narrowRow.style.maxWidth = maxRight + 'px';
    }

    // Only called from a selector click, not the initial/hash-driven
    // activation — scrolls section C into view, but only if it isn't
    // already (fully in view above, or starting below the fold).
    function scrollPanelsIntoViewIfNeeded() {
      var rect = epPanelsWrap.getBoundingClientRect();
      var headerOffset = 90;
      if (rect.top < headerOffset || rect.top > window.innerHeight) {
        window.scrollTo({ top: rect.top + window.scrollY - headerOffset, behavior: 'smooth' });
      }
    }

    function activate(n, updateHash) {
      var panel = panels[n];
      if (!panel) return;
      Object.keys(panels).forEach(function (k) {
        panels[k].hidden = (k !== n);
      });
      collapsePanel(panel);
      buttons.forEach(function (b) {
        var active = b.getAttribute('data-ep-select') === n;
        b.classList.toggle('active', active);
        b.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      if (updateHash && history.replaceState) {
        history.replaceState(null, '', '#ep-' + n);
      }
    }

    epPanelsWrap.querySelectorAll('[data-episode-panel]').forEach(function (panel) {
      var dataEl = panel.querySelector('.gm-data');
      var items = [];
      if (dataEl) {
        try { items = JSON.parse(dataEl.textContent); } catch (e) {}
      }
      var cells = panel.querySelectorAll('.gm-cell');
      var moreBtn = panel.querySelector('[data-gm-more]');
      var expanded = false;
      if (moreBtn) {
        moreBtn.addEventListener('click', function () {
          expanded = !expanded;
          cells.forEach(function (cell) {
            if (parseInt(cell.getAttribute('data-gm-index'), 10) < EP_FEATURED) return;
            cell.classList.toggle('gm-hidden', !expanded);
            if (expanded) {
              var img = cell.querySelector('img[data-gm-src]');
              if (img) {
                img.src = img.getAttribute('data-gm-src');
                img.loading = 'lazy';
                img.removeAttribute('data-gm-src');
              }
            }
          });
          moreBtn.textContent = moreBtn.getAttribute(expanded ? 'data-show-less-label' : 'data-show-more-label');
          moreBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
          syncNarrowRowWidth(panel);
        });
      }
      cells.forEach(function (cell) {
        cell.addEventListener('click', function () {
          gmOpenLightbox(items, parseInt(cell.getAttribute('data-gm-index'), 10));
        });
      });
    });

    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        activate(btn.getAttribute('data-ep-select'), true);
        scrollPanelsIntoViewIfNeeded();
      });
    });

    var fromHash = (location.hash || '').indexOf('#ep-') === 0 ? location.hash.slice(4) : null;
    activate(panels[fromHash] ? fromHash : epPanelsWrap.getAttribute('data-default-episode'), false);
    window.addEventListener('hashchange', function () {
      var n = (location.hash || '').indexOf('#ep-') === 0 ? location.hash.slice(4) : null;
      if (n && panels[n]) activate(n, false);
    });

    // Re-measure on resize (debounced) — the 16:9 row's achieved width
    // changes with viewport width, so the 4:3 row's cap has to follow.
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        var activePanel = epPanelsWrap.querySelector('[data-episode-panel]:not([hidden])');
        if (activePanel) syncNarrowRowWidth(activePanel);
      }, 150);
    });
  }
})();
