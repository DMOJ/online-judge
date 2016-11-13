#!/bin/bash
cd `dirname $0`
sass --update resources:sass_processed
pleeease compile sass_processed/style.css -t resources/style.css
mv sass_processed/content-description.css resources/content-description.css
mv sass_processed/table.css resources/table.css
mv sass_processed/ranks.css resources/ranks.css
