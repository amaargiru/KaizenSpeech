#!/usr/bin/env bash

if ! which pigar > /dev/null
then
  >&2 echo 'Please install pigar to generate requirements.txt for your version of Python.'
  echo 'Pigar can be installed with:'
  echo '  pip install pigar'
  echo 'For more information, see https://github.com/damnever/pigar'
  exit 1
fi

pigar gen -f Code/requirements.txt Code/
