#!/usr/bin/env python3

# Usage example:
#   ./generate_universe_resource.py "https://downloads.dcos.io/cli/releases/plugins/dcos-core-cli/{platform}/x86-64/dcos-core-cli-1.12-patch.0.zip"


import json
import sys
import hashlib as hash

import requests


url_pattern = sys.argv[1]

resource =	{
  "cli": {
      "binaries": {}
  }
}

for platform in ['linux', 'darwin', 'windows']:
    url = url_pattern.format(platform=platform)

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
