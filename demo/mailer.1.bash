#!/bin/bash

if test $(shuf -i1-10 -n1) -gt 5; then
  echo "This is an error which should never be reached."
  exit 1
fi

while true; do
  echo "processing..."
  sleep 1
done
