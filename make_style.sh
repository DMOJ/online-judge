#!/bin/sh
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

cd "$(dirname "$0")" || exit

build_style() {
  echo "Creating $1 style..."
  cp resources/vars-$1.scss resources/vars.scss
  sass resources:sass_processed
  postcss sass_processed/style.css sass_processed/martor-description.css sass_processed/select2-dmoj.css --verbose --use autoprefixer -d $2
}

build_style 'default' 'resources'
build_style 'dark' 'resources/dark'
