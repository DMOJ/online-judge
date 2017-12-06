#!/usr/bin/perl -pi
s/\{% trans "([^"]+)" %\}/\{\{ _\('$1'\) \}\}/g;
s/if  +/if /g;
s/\{% *static "([^"]+)" *%\}/{{ static('$1') }}/g;
s/\{% *url "([^"]+)" *%\}/{{ url('$1') }}/g;
s/\.jade"/\.html"/g;
s/\|escape//g;
