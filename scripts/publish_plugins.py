#!/usr/bin/env python3

import os

import boto3

from plugin.package_plugin import package_plugin

if os.environ.get("TAG_NAME"):
    version =  os.environ.get("TAG_NAME")
    stability = "releases"
else:
    version = os.environ.get("BRANCH_NAME")
    stability = "testing"

build_path = os.path.dirname(os.path.realpath(__file__)) + "/../build"

platforms = ['linux', 'darwin', 'windows']

for platform in platforms:
    plugin_path = build_path + '/' + platform + '/plugin'

    python_bin_dir = os.path.join(plugin_path, "bin")
    package_plugin(build_path, platform, python_bin_dir)

s3_client = boto3.resource('s3', region_name='us-west-2').meta.client

for platform in platforms:
    zip_file = platform + "/dcos-core-cli.zip"
    bucket_key_pattern = "cli/{}/plugins/dcos-core-cli/{}/x86-64/dcos-core-cli-{}.zip"
    s3_client.upload_file(build_path + "/" + zip_file, "downloads.dcos.io", bucket_key_pattern.format(stability, platform, version))

    if os.environ.get("TAG_NAME"):
        # Update the latest endpoint if it's a tag release. There is no dedicated Jenkins build for this.
        # This means we're assuming that one shouldn't rebuild an old tag, or if they do, they should then
        # rebuild the real "latest" tag in order to keep the endpoint up-to-date.
        s3_client.upload_file(build_path + "/" + zip_file, "downloads.dcos.io", bucket_key_pattern.format(stability, platform, version.rsplit('.', 1)[0] + '.latest'))
