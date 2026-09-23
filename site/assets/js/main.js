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
})();
