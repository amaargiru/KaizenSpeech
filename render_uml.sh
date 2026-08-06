#!/usr/local/env bash

if ! which pyreverse > /dev/null
then
  >&2 echo 'pyreverse was not found. Please install pyreverse then try this script again.'
  exit 1
fi

pyreverse -o png Code/ --output-directory uml/
