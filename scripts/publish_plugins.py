#!/usr/bin/env python3

import os
import shutil

import boto3

version = os.environ.get("TAG_NAME")

plugin_toml = '''
schema_version = 1
name = "dcos-core-cli"

[[commands]]
name = "job"
path = "bin/dcos{0}"
description = "Deploy and manage jobs in DC/OS"

[[commands]]
name = "marathon"
path = "bin/dcos{0}"
description = "Deploy and manage applications to DC/OS"

[[commands]]
name = "node"
path = "bin/dcos{0}"
description = "View DC/OS node information"

[[commands]]
name = "package"
path = "bin/dcos{0}"
description = "Install and manage DC/OS software packages"

[[commands]]
name = "service"
path = "bin/dcos{0}"
description = "Manage DC/OS services"

[[commands]]
name = "task"
path = "bin/dcos{0}"
description = "Manage DC/OS tasks"
'''

build_path = os.path.dirname(os.path.realpath(__file__)) + "/../build"

platforms = ['linux', 'darwin', 'windows']

for platform in platforms:
    plugin_path = build_path + '/' + platform + '/plugin'
    bin_extension = '.exe' if platform == 'windows' else ''

    with open(plugin_path + '/plugin.toml', encoding='utf-8', mode='w') as file:
        file.write(plugin_toml.format(bin_extension))

    shutil.make_archive(
        '{}/{}/dcos-core-cli'.format(build_path, platform),
        'zip',
        plugin_path
    )

s3_client = boto3.resource('s3', region_name='us-west-2').meta.client

for platform in platforms:
    zip_file = platform + "/dcos-core-cli.zip"
    bucket_key = 'cli/plugins/dcos-core-cli/{}/{}/x86-64/dcos-core-cli.zip'.format(version, platform)
    s3_client.upload_file(build_path + "/" + zip_file, "downloads.dcos.io", bucket_key)