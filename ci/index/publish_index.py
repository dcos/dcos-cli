#!/usr/bin/env python3

import os
import boto3

OSS_BUCKET="downloads.dcos.io"
EE_BUCKET="downloads.mesosphere.io"
PREFIX="cli"
PREFIX_RELEASE="cli/releases"
INDEX_FILE="index.html"
ASSETS_FOLDER="html"

def upload_file(client, src, dst):
    types = {
      ".css": "text/css",
      ".html": "text/html",
      ".ico": "image/x-icon",
      ".js": "text/javascript",
      ".json": "text/json",
    }

    name, ext = os.path.splitext(os.path.basename(src))
    if not ext in types.keys():
        raise Exception("Unrecognized extension on file '{}'".format(src))

    client.upload_file(
        Filename=src,
        Bucket=OSS_BUCKET,
        Key=dst,
        ExtraArgs={
            "ACL": "bucket-owner-full-control",
            "ContentType": types[ext]})

client = boto3.client('s3', region_name='us-west-2')

upload_file(client, INDEX_FILE, PREFIX + '/' + INDEX_FILE)
for root, dirs, files in os.walk(ASSETS_FOLDER):
   for name in files:
      path = os.path.join(root, name)
      upload_file(client, path, PREFIX + '/' + path)
