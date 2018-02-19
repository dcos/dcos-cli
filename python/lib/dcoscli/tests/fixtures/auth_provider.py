
def auth_provider_fixture():
    """Auth provider fixture

    :rtype: dict
    """

    return {
        "dcos-users": {
            "authentication-type": "dcos-uid-password",
            "client-method": "dcos-usercredential-post-receive-authtoken",
            "config": {
                "start_flow_url": "/acs/api/v1/auth/login"
            },
            "description": "Default DC/OS authenticator"
        }
    }
