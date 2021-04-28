#!/bin/bash
if ! [ -x "$(command -v sass)" ]; then
  echo 'Error: sass is not installed.' >&2
  exit 1
fi

if ! [ -x "$(command -v postcss)" ]; then
  echo 'Error: postcss is not installed.' >&2
  exit 1
fi

if ! [ -x "$(command -v autoprefixer)" ]; then
  echo 'Error: autoprefixer is not installed.' >&2
  exit 1
fi

FILES=(sass_processed/style.css sass_processed/content-description.css sass_processed/table.css
       sass_processed/ranks.css sass_processed/martor-description.css)

cd "$(dirname "$0")" || exit
sass resources:sass_processed

echo
postcss "${FILES[@]}" --verbose --use autoprefixer -d resources
