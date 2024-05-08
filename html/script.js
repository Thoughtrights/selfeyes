// Wrap every letter in a span
var textWrapper = document.querySelector('.title');
textWrapper.innerHTML = textWrapper.textContent.replace(/\S/g, "<span class='letter'>$&</span>");

anime.timeline({loop: true})
    .add({
	targets: '.title .letter',
	translateX: [40,0],
	translateZ: 0,
	opacity: [0,1],
	easing: "easeOutExpo",
	duration: 1200,
	delay: (el, i) => 500 + 40 * i
    }).add({
	targets: '.title .letter',
	translateX: [0,-30],
	opacity: [1,0],
	easing: "easeInExpo",
	duration: 1100,
	delay: (el, i) => 5000 + 30 * i
    });


////////////////////////////////////////////////////////////////////
function openModal() {
    document.getElementById("myModal").style.display = "block";
}

function closeModal() {
    document.getElementById("myModal").style.display = "none";
}

var slideIndex = 1;
showSlides(slideIndex);

function plusSlides(n) {
    showSlides(slideIndex += n);
}

function currentSlide(n) {
    showSlides(slideIndex = n);
}

function showSlides(n) {
    var i;
    var slides = document.getElementsByClassName("mySlides");
    var captionText = document.getElementById("caption");
    if (n > slides.length) {slideIndex = 1}
    if (n < 1) {slideIndex = slides.length}
    for (i = 0; i < slides.length; i++) {
	slides[i].style.display = "none";
    }
    slides[slideIndex-1].style.display = "block";
}
