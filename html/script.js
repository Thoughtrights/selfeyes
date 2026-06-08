// Title letter animation
(function () {
  var title = document.querySelector('.site-title');
  if (!title) return;
  title.innerHTML = title.textContent.replace(/\S/g, "<span class='letter'>$&</span>");
  anime.timeline({ loop: true })
    .add({
      targets: '.site-title .letter',
      translateX: [30, 0],
      opacity: [0, 1],
      easing: 'easeOutExpo',
      duration: 1000,
      delay: (el, i) => 400 + 35 * i
    })
    .add({
      targets: '.site-title .letter',
      translateX: [0, -20],
      opacity: [1, 0],
      easing: 'easeInExpo',
      duration: 900,
      delay: (el, i) => 5000 + 25 * i
    });
})();

// Gallery & modal state
var items = [];       // manifest items array
var current = 0;      // index of open photo
var zoomed = false;

var modal       = document.getElementById('modal');
var modalImg    = document.getElementById('modal-img');
var modalWrap   = document.getElementById('modal-img-wrap');
var modalClose  = document.getElementById('modal-close');
var modalPrev   = document.getElementById('modal-prev');
var modalNext   = document.getElementById('modal-next');
var modalCtr    = document.getElementById('modal-counter');
var gallery     = document.getElementById('gallery');

// Build gallery from manifest
fetch('manifest.json')
  .then(function (r) { return r.json(); })
  .then(function (manifest) {
    items = manifest.items;

    // True lazy load: images only requested when they scroll into view.
    // Explicit aspect-ratio + single DocumentFragment append ensure items
    // have correct height before any image loads, so the IntersectionObserver
    // only fires for items that are genuinely near the viewport.
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var img = entry.target.querySelector('img');
          if (img && img.dataset.src) {
            img.src = img.dataset.src;
            delete img.dataset.src;
          }
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '300px' });

    // Build all DOM nodes first, then do a single append so the browser
    // paints once — not once per item.
    var frag = document.createDocumentFragment();
    var wraps = [];

    items.forEach(function (item, idx) {
      var wrap = document.createElement('div');
      wrap.className = 'gallery-item';

      var img = document.createElement('img');
      img.dataset.src = item.src;
      img.alt = item.alt || '';
      if (item.w && item.h) {
        // Explicit style ensures height is reserved before src loads,
        // in all browsers, regardless of img intrinsic-size support.
        img.style.aspectRatio = item.w + ' / ' + item.h;
        img.width  = item.w;
        img.height = item.h;
      }

      wrap.appendChild(img);
      wrap.addEventListener('click', function () { openModal(idx); });
      frag.appendChild(wrap);
      wraps.push(wrap);
    });

    gallery.appendChild(frag);          // single DOM mutation → single paint
    wraps.forEach(function (w) { observer.observe(w); });
  });

// Modal open/close
function resetZoom() {
  zoomed = false;
  modalWrap.classList.remove('zoomed');
  modalImg.style.transition = 'none';
  modalImg.style.transform = '';
}

function openModal(idx) {
  current = idx;
  resetZoom();
  modalImg.src = items[idx].src;
  modal.style.display = 'block';
  modal.classList.remove('closing');
  updateCounter();
  updateArrows();
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.add('closing');
  resetZoom();
  setTimeout(function () {
    modal.style.display = 'none';
    modal.classList.remove('closing');
    document.body.style.overflow = '';
  }, 200);
}

function goTo(idx) {
  if (idx < 0 || idx >= items.length) return;
  current = idx;
  resetZoom();
  modalImg.src = items[idx].src;
  updateCounter();
  updateArrows();
}

function updateCounter() {
  modalCtr.textContent = (current + 1) + ' / ' + items.length;
}

function updateArrows() {
  modalPrev.classList.toggle('hidden', current === 0);
  modalNext.classList.toggle('hidden', current === items.length - 1);
}

// Toggle zoom on tap — ripple at tap point, then zoom toward it.
// Uses scale(3) + translate so the tapped region is always centered
// in the viewport, which works correctly on both desktop and mobile.
modalWrap.addEventListener('click', function (e) {
  e.stopPropagation();

  if (zoomed) {
    // Snap back instantly, no transition
    resetZoom();
    return;
  }

  // Spawn ripple at tap coordinates
  var ripple = document.createElement('div');
  ripple.className = 'tap-ripple';
  ripple.style.left = e.clientX + 'px';
  ripple.style.top  = e.clientY + 'px';
  document.body.appendChild(ripple);
  ripple.addEventListener('animationend', function () { ripple.remove(); });

  // Calculate translate so the tap point ends up at the image center
  // (which is already centered in the viewport).
  // With transform: scale(S) translate(-dx, -dy) and transform-origin: 50% 50%:
  //   the tap point moves to the image center before scaling, so it stays centered.
  var rect = modalImg.getBoundingClientRect();
  var dx = (e.clientX - rect.left) - rect.width  / 2;
  var dy = (e.clientY - rect.top)  - rect.height / 2;

  // Brief pause so the ripple is visible before zoom begins
  setTimeout(function () {
    modalImg.style.transformOrigin = '50% 50%';
    modalImg.style.transition = '';
    modalImg.style.transform = 'scale(3) translate(' + (-dx) + 'px, ' + (-dy) + 'px)';
    zoomed = true;
    modalWrap.classList.add('zoomed');
  }, 300);
});

// Close on backdrop click
modal.addEventListener('click', function (e) {
  if (e.target === modal || e.target === document.querySelector('.modal-ui')) {
    closeModal();
  }
});

modalClose.addEventListener('click', closeModal);
modalPrev.addEventListener('click', function (e) { e.stopPropagation(); goTo(current - 1); });
modalNext.addEventListener('click', function (e) { e.stopPropagation(); goTo(current + 1); });

// Keyboard
document.addEventListener('keydown', function (e) {
  if (modal.style.display !== 'block') return;
  if (e.key === 'Escape')       closeModal();
  if (e.key === 'ArrowLeft')    goTo(current - 1);
  if (e.key === 'ArrowRight')   goTo(current + 1);
  if (e.key === 'z' || e.key === 'Z') {
    if (zoomed) {
      resetZoom();
    } else {
      // Zoom to center of image when using keyboard
      modalImg.style.transformOrigin = '50% 50%';
      modalImg.style.transition = '';
      modalImg.style.transform = 'scale(3) translate(0px, 0px)';
      zoomed = true;
      modalWrap.classList.add('zoomed');
    }
  }
});
