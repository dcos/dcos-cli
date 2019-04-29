#!/usr/bin/env python3

import json
import os
import random
import string
import sys
import time

import requests

from dcos_e2e.backends import AWS
from dcos_e2e.cluster import Cluster
from dcos_e2e.node import Output
from passlib.hash import sha512_crypt

if len(sys.argv) != 2:
    print("Please specify the installer URL as argument.", file=sys.stderr)
    sys.exit(1)

dcos_variant = os.environ.get('DCOS_TEST_VARIANT')
if not dcos_variant:
    print("Please set DCOS_TEST_VARIANT to 'open' or 'enterprise'.", file=sys.stderr)
    sys.exit(1)

private_key_path = os.environ.get('DCOS_TEST_SSH_KEY_PATH')
aws_key_pair = ('default', private_key_path) if private_key_path else None

cluster_backend = AWS(aws_region='us-east-1', aws_key_pair=aws_key_pair)
cluster = Cluster(cluster_backend=cluster_backend, agents=0, public_agents=0)

username = 'testuser'
password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(12))

extra_config = {
    'superuser_username': username,
    'superuser_password_hash': sha512_crypt.hash(password),
#    'fault_domain_enabled': False,
}

test_license = os.environ.get('DCOS_TEST_LICENSE')
if test_license:
    extra_config['license_key_contents'] = test_license

dcos_config = {**cluster.base_config, **extra_config}

cluster.install_dcos_from_url(
    dcos_installer=sys.argv[1],
    dcos_config=dcos_config,
    ip_detect_path=cluster_backend.ip_detect_path,
    output=Output.LOG_AND_CAPTURE,
)

if dcos_variant == 'open':
    cluster.wait_for_dcos_oss()
else:
    cluster.wait_for_dcos_ee(
        superuser_username=username,
        superuser_password=password,
    )

master_node = next(iter(cluster.masters))
master_ip = master_node.public_ip_address.exploded

# In order to create a user with a password on DC/OS Open, we login with the well-known key
# from the default user to get an ACS token and then hit the IAM API directly.
# Hopefully in the future there will be a simpler way to do it.
if dcos_variant == 'open':
    response = requests.post(
        'http://' + master_ip + '/acs/api/v1/auth/login',
        headers={"Content-Type" : "application/json"},
        data=json.dumps({
            "token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik9UQkVOakZFTWtWQ09VRTRPRVpGTlRNMFJrWXlRa015Tnprd1JrSkVRemRCTWpBM1FqYzVOZyJ9.eyJlbWFpbCI6ImFsYmVydEBiZWtzdGlsLm5ldCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczovL2Rjb3MuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA5OTY0NDk5MDExMTA4OTA1MDUwIiwiYXVkIjoiM3lGNVRPU3pkbEk0NVExeHNweHplb0dCZTlmTnhtOW0iLCJleHAiOjIwOTA4ODQ5NzQsImlhdCI6MTQ2MDE2NDk3NH0.OxcoJJp06L1z2_41_p65FriEGkPzwFB_0pA9ULCvwvzJ8pJXw9hLbmsx-23aY2f-ydwJ7LSibL9i5NbQSR2riJWTcW4N7tLLCCMeFXKEK4hErN2hyxz71Fl765EjQSO5KD1A-HsOPr3ZZPoGTBjE0-EFtmXkSlHb1T2zd0Z8T5Z2-q96WkFoT6PiEdbrDA-e47LKtRmqsddnPZnp0xmMQdTr2MjpVgvqG7TlRvxDcYc-62rkwQXDNSWsW61FcKfQ-TRIZSf2GS9F9esDF4b5tRtrXcBNaorYa9ql0XAWH5W_ct4ylRNl3vwkYKWa4cmPvOqT5Wlj9Tf0af4lNO40PQ"
        }),
    )

    if response.status_code != 200:
        print("Couldn't login.", file=sys.stderr)
        sys.exit(1)

    response = requests.put(
        'http://' + master_ip + '/acs/api/v1/users/' + username,
        headers={
            "Authorization" : "token=" + response.json().get('token'),
            "Content-Type" : "application/json",
        },
        data=json.dumps({'password': password}),
    )

    if response.status_code != 201:
        print("Unexpected status code " + response.status_code + " when creating user", file=sys.stderr)
        sys.exit(1)

out = '''
export DCOS_TEST_DEFAULT_CLUSTER_VARIANT={}
export DCOS_TEST_DEFAULT_CLUSTER_USERNAME={}
export DCOS_TEST_DEFAULT_CLUSTER_PASSWORD={}
export DCOS_TEST_DEFAULT_CLUSTER_HOST={}
'''.format(dcos_variant, username, password, master_ip)

with open('test_cluster.env.sh', 'w') as f:
    f.write(out)
