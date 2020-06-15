#!/usr/bin/env python3

import json
import os

import requests
import sys

username = os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_USERNAME')
password = os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_PASSWORD')
master_ip = os.environ.get('DCOS_TEST_DEFAULT_CLUSTER_HOST')

# In order to create a user with a password on DC/OS Open, we login with the well-known key
# from the default user to get an ACS token and then hit the IAM API directly.
# Hopefully in the future there will be a simpler way to do it.
response = requests.post(
    'http://' + master_ip + '/acs/api/v1/auth/login',
    headers={"Content-Type": "application/json"},
    data=json.dumps({
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik9UQkVOakZFTWtWQ09VRTRPRVpGTlRNMFJrWXlRa015Tnprd1JrSkVRemRCTWpBM1FqYzVOZyJ9.eyJlbWFpbCI6ImFsYmVydEBiZWtzdGlsLm5ldCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczovL2Rjb3MuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA5OTY0NDk5MDExMTA4OTA1MDUwIiwiYXVkIjoiM3lGNVRPU3pkbEk0NVExeHNweHplb0dCZTlmTnhtOW0iLCJleHAiOjIwOTA4ODQ5NzQsImlhdCI6MTQ2MDE2NDk3NH0.OxcoJJp06L1z2_41_p65FriEGkPzwFB_0pA9ULCvwvzJ8pJXw9hLbmsx-23aY2f-ydwJ7LSibL9i5NbQSR2riJWTcW4N7tLLCCMeFXKEK4hErN2hyxz71Fl765EjQSO5KD1A-HsOPr3ZZPoGTBjE0-EFtmXkSlHb1T2zd0Z8T5Z2-q96WkFoT6PiEdbrDA-e47LKtRmqsddnPZnp0xmMQdTr2MjpVgvqG7TlRvxDcYc-62rkwQXDNSWsW61FcKfQ-TRIZSf2GS9F9esDF4b5tRtrXcBNaorYa9ql0XAWH5W_ct4ylRNl3vwkYKWa4cmPvOqT5Wlj9Tf0af4lNO40PQ"
    }),
)

if response.status_code != 200:
    print("Couldn't login.", file=sys.stderr)
    sys.exit(1)

response = requests.put(
    'http://' + master_ip + '/acs/api/v1/users/' + username,
    headers={
        "Authorization": "token=" + response.json().get('token'),
        "Content-Type": "application/json",
    },
    data=json.dumps({'password': password}),
)

if response.status_code != 201:
    print("Unexpected status code " + response.status_code + " when creating user", file=sys.stderr)
    sys.exit(1)
