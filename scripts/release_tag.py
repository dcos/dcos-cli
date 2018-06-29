#!/usr/bin/env python3

import os
import pathlib
import sys

import boto3
import requests

tag_name = os.environ.get("TAG_NAME")
dcos_version = os.environ.get("DCOS_VERSION")

if not tag_name:
    print("Missing TAG_NAME.", file=sys.stderr)
    sys.exit(1)

if not dcos_version:
    print("Missing DCOS_VERSION.", file=sys.stderr)
    sys.exit(1)

s3_client = boto3.resource('s3', region_name='us-west-2').meta.client
bucket = "downloads.dcos.io"
artifacts = [
    "binaries/cli/linux/x86-64/{}/dcos",
    "binaries/cli/darwin/x86-64/{}/dcos",
    "binaries/cli/windows/x86-64/{}/dcos.exe"
]

for artifact in artifacts:
    src = {'Bucket': bucket, 'Key': artifact.format(tag_name)}
    dst = artifact.format("dcos-" + dcos_version)

    s3_client.copy(src, bucket, dst)

slack_token = os.environ.get("SLACK_API_TOKEN")
if not slack_token:
    sys.exit(0)

attachment_text = tag_name + " has been released!"
s3_urls = ["https://{}/{}".format(bucket, a.format("dcos-" + dcos_version)) for a in artifacts]

try:
    resp = requests.post(
      "https://mesosphere.slack.com/services/hooks/jenkins-ci?token=" + slack_token,
      json={
        "channel": "#dcos-cli-ci",
        "color": "good",
        "attachments": [
            {
                "color": "good",
                "title": "dcos-core-cli",
                "text":  "\n".join([attachment_text + " :tada:"] + s3_urls),
                "fallback": "[dcos-core-cli] " + attachment_text
            }
        ]
      }, timeout=30)

    if resp.status_code != 200:
        raise Exception("received {} status response: {}".format(resp.status_code, resp.text))
except Exception as e:
    print("Couldn't post Slack notification:\n  {}".format(e))
