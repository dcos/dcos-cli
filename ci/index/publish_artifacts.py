#!/usr/bin/env python3

import json
import os

import boto3

from publish_index import upload_file
from publish_index import BUCKET
from publish_index import PREFIX
from publish_index import ASSETS_FOLDER

ARTIFACTS_FILE = ASSETS_FOLDER + "/artifacts.json"


def splitpath(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def format_path(o):
    split = splitpath(o['Key'])
    return "/".join(split[1:])


def filter_objects(objects):
    # For now we use the 'valid_artifacts' list above to do our filtering.
    # In the end, the filtering should look more like:
    filtered = []
    for o in objects:
        split = splitpath(o['Key'])
        if split[1] == "releases":
            filtered.append(o)
    return filtered


client = boto3.client('s3', region_name='us-west-2')
objects = client.list_objects(Bucket=BUCKET, Prefix=PREFIX)['Contents']

with open(ARTIFACTS_FILE, mode='w+') as f:
    contents = { "artifacts": [] }
    for o in filter_objects(objects):
        contents["artifacts"].append(format_path(o))
    f.write(json.dumps(contents))

upload_file(client, ARTIFACTS_FILE, PREFIX + '/' + ARTIFACTS_FILE)
