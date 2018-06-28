#!/usr/bin/env python3

import uuid
import os
import sys

from passlib.hash import sha512_crypt

from dcos_launch import config, get_launcher


assert 'DCOS_TEST_INSTALLER_URL' in os.environ
assert 'DCOS_TEST_LICENSE' in os.environ
assert 'DCOS_TEST_SSH_KEY_PATH' in os.environ
assert 'DCOS_TEST_ADMIN_USERNAME' in os.environ
assert 'DCOS_TEST_ADMIN_PASSWORD' in os.environ

dcos_launch_config = {
    'launch_config_version': 1,
    'deployment_name': "dcos-core-cli-e2e-tests-" + uuid.uuid4().hex,
    'installer_url': os.environ['DCOS_TEST_INSTALLER_URL'],
    'platform': 'aws',
    'provider': 'onprem',
    'aws_region': 'us-west-2',
    'aws_key_name': 'default',
    'ssh_private_key_filename': os.environ['DCOS_TEST_SSH_KEY_PATH'],
    'os_name': 'cent-os-7-dcos-prereqs',
    'instance_type': 'm4.large',
    'num_masters': 1,
    'num_private_agents': 1,
    'num_public_agents': 1,
    'dcos_config': {
        'cluster_name': 'DC/OS Licensing CLI Integration Tests',
        'resolvers': ['10.10.0.2'],
        'dns_search': 'us-west-2.compute.internal',
        'master_discovery': 'static',
        'exhibitor_storage_backend': 'static',
        'superuser_username': os.environ['DCOS_TEST_ADMIN_USERNAME'],
        'superuser_password_hash': sha512_crypt.hash(os.environ['DCOS_TEST_ADMIN_PASSWORD']),
        'fault_domain_enabled': False,
    },
}

dcos_launch_config = config.get_validated_config(dcos_launch_config, '/tmp')

launcher = get_launcher(dcos_launch_config)

cluster_info = launcher.create()

launcher = get_launcher(cluster_info)
launcher.wait()

# Workaround for `launcher.install_dcos()` printing to stdout.
real_stdout = sys.stdout
sys.stdout = open(os.devnull, "w")
try:
    launcher.install_dcos()
finally:
    sys.stdout.close()
    sys.stdout = real_stdout

master = next(iter(launcher.describe().get('masters')))

print(master.get('public_ip'), end='')