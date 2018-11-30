#!/usr/bin/env python3

# Usage example:
#   ./generate_universe_resource.py dcos-core-cli 1.12-patch.2

import json
import sys
import hashlib as hash

import requests


plugin_name = sys.argv[1]
plugin_version = sys.argv[2]

resource =	{
  "cli": {
      "binaries": {}
  }
}

for platform in ['linux', 'darwin', 'windows']:
    url = "https://downloads.dcos.io/cli/releases/plugins/{}/{}/x86-64/{}-{}.zip".format(
        plugin_name, platform, plugin_name, plugin_version)

    sha = hash.sha256()
    r = requests.get(url, stream=True)
    for chunk in r.iter_content(1024):
        sha.update(chunk)

    resource['cli']['binaries'][platform] = {
        'x86-64': {
            'kind': 'zip',
            'url': url,
            'contentHash': [
                {
                    'algo': 'sha256',
                    'value': sha.hexdigest()
                }
            ]
        }
    }

json.dump(resource, sys.stdout, indent=4)
