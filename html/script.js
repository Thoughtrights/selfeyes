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

// Toggle zoom on tap — ripple at tap point, then zoom toward it
modalWrap.addEventListener('click', function (e) {
  e.stopPropagation();

  // Spawn ripple at tap coordinates
  var ripple = document.createElement('div');
  ripple.className = 'tap-ripple';
  ripple.style.left = e.clientX + 'px';
  ripple.style.top  = e.clientY + 'px';
  document.body.appendChild(ripple);
  ripple.addEventListener('animationend', function () { ripple.remove(); });

  if (!zoomed) {
    var rect = modalImg.getBoundingClientRect();
    var pctX = ((e.clientX - rect.left) / rect.width  * 100).toFixed(2) + '%';
    var pctY = ((e.clientY - rect.top)  / rect.height * 100).toFixed(2) + '%';
    modalImg.style.transformOrigin = pctX + ' ' + pctY;
  }

  if (zoomed) {
    // Snap back instantly
    modalImg.style.transition = 'none';
    zoomed = false;
    modalWrap.classList.remove('zoomed');
  } else {
    // Brief pause so the ripple is visible before zoom begins
    setTimeout(function () {
      modalImg.style.transition = '';
      zoomed = true;
      modalWrap.classList.add('zoomed');
    }, 300);
  }
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
    modalImg.style.transition = '';
    zoomed = !zoomed;
    modalWrap.classList.toggle('zoomed', zoomed);
  }
});
