#!/usr/bin/bash

# earlier version. style and onclick no longer there. class name changed.

export vv=55;for i in *; do vv=$((vv+1)); echo "  <div class=\"column\">"; echo "    <img src=\"assets/$i\" style=\"width:100%\" onclick=\"openModal();currentSlide($vv)\" class=\"hover-shadow cursor\">"; echo "  </div>"; done > ../boo.txt
