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
    items.forEach(function (item, idx) {
      var wrap = document.createElement('div');
      wrap.className = 'gallery-item';
      wrap.style.animationDelay = Math.min(idx * 30, 1200) + 'ms';

      var img = document.createElement('img');
      img.src = item.src;
      img.alt = item.alt || '';
      img.loading = 'lazy';

      wrap.appendChild(img);
      wrap.addEventListener('click', function () { openModal(idx); });
      gallery.appendChild(wrap);
    });
  });

// Modal open/close
function openModal(idx) {
  current = idx;
  zoomed = false;
  modalWrap.classList.remove('zoomed');
  modalImg.style.transition = 'none';
  modalImg.src = items[idx].src;
  modal.style.display = 'block';
  modal.classList.remove('closing');
  updateCounter();
  updateArrows();
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.add('closing');
  setTimeout(function () {
    modal.style.display = 'none';
    modal.classList.remove('closing');
    document.body.style.overflow = '';
    zoomed = false;
    modalWrap.classList.remove('zoomed');
  }, 200);
}

function goTo(idx) {
  if (idx < 0 || idx >= items.length) return;
  current = idx;
  zoomed = false;
  modalWrap.classList.remove('zoomed');
  modalImg.style.transition = 'none';
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
    modalImg.style.transition = 'none';
    modalImg.style.transform = '';
    modalImg.style.transformOrigin = '50% 40%';
    zoomed = false;
    modalWrap.classList.remove('zoomed');
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
      modalImg.style.transition = 'none';
      modalImg.style.transform = '';
      zoomed = false;
      modalWrap.classList.remove('zoomed');
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
