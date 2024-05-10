#!/usr/bin/bash

# this whole section is not needed any more. I reduced it to an HTML template populated by JS.

export vv=55;for i in *; do vv=$((vv+1)); echo "  <div class=\"mySlides\">"; echo "    <div class=\"numbertext\">$vv / 55</div>";echo "     <img src=\"assets/$i\" class=\"hover-zoom\">"; echo "  </div>"; done > ../boo.txt
