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
})();
