#!/bin/bash

if [ ! -z "$1" ] ; then
    dcos config set core.dcos_url "$1";
fi

/bin/bash
