#!/usr/bin/env python3

import os
import random
import string
import sys
import time

from dcos_e2e.backends import AWS
from dcos_e2e.cluster import Cluster
from passlib.hash import sha512_crypt

if len(sys.argv) != 2:
    print("Please specify the installer URL as argument.", file=sys.stderr)
    sys.exit(1)

test_license = os.environ.get('DCOS_TEST_LICENSE')
if not test_license:
    print("Please specify a license in $DCOS_TEST_LICENSE.", file=sys.stderr)
    sys.exit(1)

private_key_path = os.environ.get('DCOS_TEST_SSH_KEY_PATH')
aws_key_pair = ('default', private_key_path) if private_key_path else None

cluster_backend = AWS(aws_key_pair=aws_key_pair)
cluster = Cluster(cluster_backend=cluster_backend, agents=0, public_agents=0)

username = 'testuser'
password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(12))

extra_config = {
    'superuser_username': username,
    'superuser_password_hash': sha512_crypt.hash(password),
    'fault_domain_enabled': False,
    'license_key_contents': test_license,
}

dcos_config = {**cluster.base_config, **extra_config}

cluster.install_dcos_from_url(
    build_artifact=sys.argv[1],
    dcos_config=dcos_config,
    log_output_live=True,
    ip_detect_path=cluster_backend.ip_detect_path,
)

cluster.wait_for_dcos_ee(
    superuser_username=username,
    superuser_password=password,
)

master_node = next(iter(cluster.masters))
master_ip = master_node.public_ip_address.exploded

out = '''
export DCOS_TEST_DEFAULT_CLUSTER_VARIANT=enterprise
export DCOS_TEST_DEFAULT_CLUSTER_USERNAME={}
export DCOS_TEST_DEFAULT_CLUSTER_PASSWORD={}
export DCOS_TEST_DEFAULT_CLUSTER_HOST={}
'''.format(username, password, master_ip)

with open('test_cluster.env.sh', 'w') as f:
    f.write(out)
