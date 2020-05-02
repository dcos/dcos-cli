#!/usr/bin/env python3

import os
import pathlib
import sys

import boto3
import requests


if os.environ.get("TAG_NAME"):
    version =  os.environ.get("TAG_NAME")

    artifacts = [
        ("linux/dcos",       "cli/releases/binaries/dcos/linux/x86-64/latest/dcos"),
        ("darwin/dcos",      "cli/releases/binaries/dcos/darwin/x86-64/latest/dcos"),
        ("darwin/dcos.zip",  "cli/releases/binaries/dcos/darwin/x86-64/latest/dcos.zip"),
        ("windows/dcos.exe", "cli/releases/binaries/dcos/windows/x86-64/latest/dcos.exe"),

        ("linux/dcos",       "cli/releases/binaries/dcos/linux/x86-64/{}/dcos".format(version)),
        ("darwin/dcos",      "cli/releases/binaries/dcos/darwin/x86-64/{}/dcos".format(version)),
        ("darwin/dcos.zip",  "cli/releases/binaries/dcos/darwin/x86-64/{}/dcos.zip".format(version)),
        ("windows/dcos.exe", "cli/releases/binaries/dcos/windows/x86-64/{}/dcos.exe".format(version)),

        # For tag releases, still push to the legacy locations.
        ("linux/dcos",       "binaries/cli/linux/x86-64/latest/dcos"),
        ("darwin/dcos",      "binaries/cli/darwin/x86-64/latest/dcos"),
        ("darwin/dcos.zip",  "binaries/cli/darwin/x86-64/latest/dcos.zip"),
        ("windows/dcos.exe", "binaries/cli/windows/x86-64/latest/dcos.exe"),

        ("linux/dcos",       "binaries/cli/linux/x86-64/{}/dcos".format(version)),
        ("darwin/dcos",      "binaries/cli/darwin/x86-64/{}/dcos".format(version)),
        ("darwin/dcos.zip",  "binaries/cli/darwin/x86-64/{}/dcos.zip".format(version)),
        ("windows/dcos.exe", "binaries/cli/windows/x86-64/{}/dcos.exe".format(version))
    ]
else:
    version = os.environ.get("BRANCH_NAME")

    artifacts = [
        ("linux/dcos",       "cli/testing/binaries/dcos/linux/x86-64/{}/dcos".format(version)),
        ("darwin/dcos",      "cli/testing/binaries/dcos/darwin/x86-64/{}/dcos".format(version)),
        ("darwin/dcos.zip",  "cli/testing/binaries/dcos/darwin/x86-64/{}/dcos.zip".format(version)),
        ("windows/dcos.exe", "cli/testing/binaries/dcos/windows/x86-64/{}/dcos.exe".format(version))
    ]

s3_client = boto3.resource('s3', region_name='us-west-2').meta.client
bucket = "downloads.dcos.io"

# TODO: this should probably passed as argument.
build_path = os.path.dirname(os.path.realpath(__file__)) + "/../build"

for f, bucket_key in artifacts:
    s3_client.upload_file(build_path + "/" + f, bucket, bucket_key)

slack_token = os.environ.get("SLACK_API_TOKEN")
if not slack_token or not os.environ.get("TAG_NAME"):
    sys.exit(0)

attachment_text = "The DC/OS CLI " + version + " has been released!"
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
                "title": "dcos-cli",
                "text":  "\n".join([attachment_text + " :rocket:"] + s3_urls),
                "fallback": "[dcos-cli] " + attachment_text
            }
        ]
      }, timeout=30)

    if resp.status_code != 200:
        raise Exception("received {} status response: {}".format(resp.status_code, resp.text))
except Exception as e:
    print("Couldn't post Slack notification:\n  {}".format(e))
