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
  function gmOpenLightbox(items, index) {
    if (!items.length) return;
    if (!gmLightbox) {
      gmLightbox = document.createElement('div');
      gmLightbox.className = 'gm-lightbox';
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
})();
