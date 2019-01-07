#!/usr/bin/env python3

import configparser
import os
import subprocess
import sys
import tempfile
from distutils.version import StrictVersion

import requests
from github import Github

platform = sys.platform
ext = ''

if platform == 'win32':
    platform = 'windows'
    ext = '.exe'

g = Github(os.environ.get("GITHUB_TOKEN"))

dcos_cli_repo = g.get_repo("dcos/dcos-cli")

latest_0_5 = "0.5.0"
latest_0_6 = "0.6.0"
latest_0_7 = "0.7.0"
latest_overall = "0.7.0"
latest_commit = dcos_cli_repo.get_commit('master').sha

for tag in dcos_cli_repo.get_tags():
    if tag.name.startswith('0.5') and StrictVersion(latest_0_5) < StrictVersion(tag.name):
            latest_0_5 = tag.name
    elif tag.name.startswith('0.6') and StrictVersion(latest_0_6) < StrictVersion(tag.name):
            latest_0_6 = tag.name
    elif tag.name.startswith('0.7') and StrictVersion(latest_0_7) < StrictVersion(tag.name):
            latest_0_7 = tag.name

    if StrictVersion(latest_overall) < StrictVersion(tag.name):
        latest_overall = tag.name

expectations = [
#    The latest endpoints are not published yet, it should happen on the next 0.7.x tag release.
#    The lines below could then be uncommented.
#    (
#        "https://downloads.dcos.io/cli/releases/binaries/dcos/{}/x86-64/latest/dcos{}".format(platform, ext),
#        latest_overall
#    ),
#    (
#        "https://downloads.dcos.io/binaries/cli/{}/x86-64/latest/dcos{}".format(platform, ext),
#        latest_overall
#    ),
    (
        "https://downloads.dcos.io/binaries/cli/{}/x86-64/dcos-1.12/dcos{}".format(platform, ext),
        latest_0_7
    ),
    (
        "https://downloads.dcos.io/binaries/cli/{}/x86-64/dcos-1.11/dcos{}".format(platform, ext),
        latest_0_6
    ),
    (
        "https://downloads.dcos.io/binaries/cli/{}/x86-64/dcos-1.10/dcos{}".format(platform, ext),
        latest_0_5
    ),
    (
        "https://downloads.dcos.io/cli/testing/binaries/dcos/{}/x86-64/master/dcos{}".format(platform, ext),
        latest_commit
    )
]

for url, expected_version in expectations:
    print('Verifying ' + url + '...')
    r = requests.get(url, stream=True)
    fd, binary = tempfile.mkstemp()
    try:
        with os.fdopen(fd, 'wb') as tmp:
            for chunk in r.iter_content(1024):
                tmp.write(chunk)

        os.chmod(binary, 0o744)

        output = subprocess.check_output([binary, '--version']).decode()

        version = configparser.ConfigParser()
        version.read_string('[version]\n' + output)
        actual_version = version.get('version', 'dcoscli.version')

        assert actual_version == expected_version, 'expected {}, got {}'.format(expected_version, actual_version)
    finally:
        os.remove(binary)

