#!/bin/bash

if [ -z $1 ]; then
  echo "Usage:"
  echo "Input the url of your cluster. Example:"
  echo "name.us-west-1.elb.amazonaws.com"
  echo ""
elif [ ! -z $1 ]; then
  bash ./install.sh . $1

  echo "Setup complete."
  echo "Run 'source bin/env-setup' to get started."
  echo ""
fi
bash
