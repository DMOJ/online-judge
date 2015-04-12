#!/bin/bash
cd `dirname $0`
sass resources/style.sass 'resources/style$.css'
pleeease compile 'resources/style$.css' -t resources/style.css
rm 'resources/style$.css'
