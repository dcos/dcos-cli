#!/usr/bin/env python3

import os
import pathlib
import sys

import boto3
import requests

# TODO: the current DC/OS dev version (1.12) should be pulled dynamically (from the Github API?).
version = os.environ.get("TAG_NAME") or "dcos-1.12"

s3_client = boto3.resource('s3', region_name='us-west-2').meta.client
bucket = "downloads.dcos.io"
artifacts = [
    ("linux/plugin/bin/dcos", "binaries/cli/linux/x86-64/{}/dcos".format(version)),
    ("darwin/plugin/bin/dcos", "binaries/cli/darwin/x86-64/{}/dcos".format(version)),
    ("windows/plugin/bin/dcos.exe", "binaries/cli/windows/x86-64/{}/dcos.exe".format(version))
]

# TODO: this should probably passed as argument.
build_path = os.path.dirname(os.path.realpath(__file__)) + "/../build"

for f, bucket_key in artifacts:
    s3_client.upload_file(build_path + "/" + f, bucket, bucket_key)

slack_token = os.environ.get("SLACK_API_TOKEN")
if not slack_token or version.startswith("dcos-"):
    sys.exit(0)

attachment_text = version + " has been published!"
s3_urls = ["https://{}/{}".format(bucket, a[1]) for a in artifacts]

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
                "text":  "\n".join([attachment_text + " :rocket:"] + s3_urls),
                "fallback": "[dcos-core-cli] " + attachment_text
            }
        ]
      }, timeout=30)

    if resp.status_code != 200:
        raise Exception("received {} status response: {}".format(resp.status_code, resp.text))
except Exception as e:
    print("Couldn't post Slack notification:\n  {}".format(e))
