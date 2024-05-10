# Selfeyes

Artistic reflections of the world in the eyes of selfie photos.

## Thanks

Built on foundation of a responsive lightbox gallery slideshow found on CodePen.io. Original URL:
[https://codepen.io/tofjadesign/pen/NWoQWYQ](https://codepen.io/tofjadesign/pen/NWoQWYQ).

# TODO

* Get the styling cleaned so the markup doesn't have a `<p />` which is not legal. [LOW]
* I sometimes see a focus issue for the on mouseover CSS. [TBD]
* Have the slow zoom-in be directed by the mouse. [LOW]

# Change Log

## 2024 May-10

* Ripped out the style markup from HTML and pushed into style.css.
* Ripped out the onclick from HTML and enabled via script.js.
* Removed expectation that previews would be in the same order as modal HTML.
* Removed all modal HTML except for a single template.
* Made some special work for prev/next to work correctly in all cases.
* Performance improvements.
* Reduced expectations on the HTML.
* Effectively changed all JS except title animation.
* Turned out to be good to modularize.

## 2024 May-9

* Doubled the number of images.
* Added slow zoom-in.
* Added click to dismiss which seems to be an intuitive UX
* Adjusted UI so zoom is cleaner.

## 2024 May-8

* Initial assembly.

