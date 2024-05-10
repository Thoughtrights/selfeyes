// Title animation
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

// Gather photos from DOM
photos = document.getElementsByClassName("photograph-preview");
photoSrcIndex = [];
for (i = 0; i < photos.length; i++) {
    photos[i].onclick = clickOnPreview; // Set all the onClick events
    photoSrcIndex[i] = photos[i].src; // Used for prev/next search later
}

// Gather modal elements
modal = document.getElementById("myModal");
x = document.getElementById("x");
x.onclick = closeModal;
slideTemplate = document.getElementById("slideTemplate");
slideTemplate.onclick = closeModal;
slideTemplateImage = document.getElementById("slideTemplateImage");
slideNumberText = document.getElementById("slideNumberText");

// Modal prev/next stuff
prev = document.getElementById("prev");
next = document.getElementById("next");
prev.onclick = clickOnPrev;
next.onclick = clickOnNext;
photoNumber = 0;
slideNumberText.innerHTML = "1 / " + photos.length;


function closeModal() {
    slideTemplate.style.display = "none";
    modal.style.display = "none";
}
function showThisSlide(theImage) {
    slideTemplateImage.src = theImage; 
    slideTemplate.style.display = "block";
    modal.style.display = "block";
    photoNumber = photoSrcIndex.indexOf(theImage);
    slideNumberText.innerHTML = (photoNumber + 1) + " / " + photos.length;
    return(photoNumber);
}
function showPrevNextArrows(num) {
    if (num == 0) {
	prev.style.display = "none";
    } else {
	prev.style.display = "block";
    }
    if ((num +1) >= photos.length) {
	next.style.display = "none";
    } else {
	next.style.display = "block";
    }
}
function clickOnPreview() {
    image = event.srcElement.src; // grab the image that was clicked
    photoNumber = showThisSlide(image);
    showPrevNextArrows(photoNumber);
}

function clickOnPrev() {                   // we don't have context so
    image = photoSrcIndex[photoNumber -1]; // rely on photoNumber avail globally
    photoNumber = showThisSlide(image);
    showPrevNextArrows(photoNumber);
}
function clickOnNext() {                   // we don't have context so
    image = photoSrcIndex[photoNumber +1]; // rely on photoNumber avail globally
    photoNumber = showThisSlide(image);
    showPrevNextArrows(photoNumber);
}


  

   


