#!/bin/bash
cd `dirname $0`
sass --update resources:sass_processed
pleeease compile sass_processed/style.css -t resources/style.css
