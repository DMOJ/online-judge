#!/bin/bash
cd `dirname $0`
sass resources/style.sass 'resources/style$.css'
sass resources/content-description.sass resources/content-description.css
pleeease compile 'resources/style$.css' -t resources/style.css
rm 'resources/style$.css' 'resources/style$.css.map'
