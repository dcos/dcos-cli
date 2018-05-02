# login

The login package handles DC/OS login related operations.

## Goals

The goals of the login package are to:

- Detect available login providers for a DC/OS cluster.
- Log in to a DC/OS cluster using a given login provider.

## Login providers detection

To detect available login providers for a given DC/OS cluster, the CLI issues a GET request to the
`/acs/api/v1/auth/providers` endpoint. This endpoint returns a list of providers in JSON. Each
top-level key refers to the login provider ID, while its value is the login provider definition:

``` json
{
  "dcos-users": {
    "authentication-type": "dcos-uid-password",
    "client-method": "dcos-usercredential-post-receive-authtoken",
    "config": {
      "start_flow_url": "/acs/api/v1/auth/login"
    },
    "description": "Default DC/OS authenticator"
  }
}
```

The above definition is a default DC/OS login provider, its ID is **dcos-users**.
The ID has no special semantic apart from uniquely identifying a login provider.

When the `/acs/api/v1/auth/providers` endpoint is not present, the available login provider is
detected by making an unauthenticated `HEAD` request to a well-known protected DC/OS resource and
reading the `WWW-Authenticate` header DC/OS returns in the 401 response:

- `acsjwt` : the cluster only supports the `dcos-users` provider as defined above.
- `oauthjwt` : the cluster only supports the OpenID implicit flow provider, as defined below:

``` json
{
  "dcos-oidc-auth0": {
    "authentication-type": "oidc-implicit-flow",
    "client-method": "browser-prompt-authtoken",
    "config": {
      "start_flow_url": "/login?redirect_uri=urn:ietf:wg:oauth:2.0:oob"
    },
    "description": "Google, GitHub, or Microsoft"
  }
}
```

## Log in to a DC/OS cluster

Log in to a DC/OS cluster is the action of presenting some credentials to the cluster in order to
get an authorization token in return (also known as `ACS token`).

The DC/OS CLI supports 6 login providers types (`authentication-type`):

- **dcos-uid-password** : Log in using a standard DC/OS user account (username and password).
- **dcos-uid-password-ldap** : Log in using an LDAP user account (username and password).
- **dcos-uid-servicekey** : Log in using a DC/OS service user account (username and private key).
- **saml-sp-initiated** : Log in using SAML 2.0.
- **oidc-authorization-code-flow** : Log in using OpenID Connect authorization code flow.
- **oidc-implicit-flow** : Log in using OpenID Connect implicit flow.

A login happens through the `dcos auth login` command, which accepts the following flags:

- **--provider** (string) : Specify the login provider ID to use.
- **--username** (string) : Specify the username.
- **--password** (string) : Specify password in plaintext (insecure).
- **--password-file** (string) : Specify the path to a file that contains the password (insecure).
- **--password-env** (string) : Specify an environment variable name that contains the password.
- **--private-key** (string) : Specify the path to a file that contains the private key for service
    account login.

(A login also happens at the end of the `dcos cluster setup` command, which accepts all the flags
from the `dcos auth login` command.)

In order to perform a login, the CLI must select a login provider to use. This selection can occur
in 3 different ways:

- **explicitly** : the user passed the `--provider` flag with a given login provider ID.
- **implicitly** : a single login provider is available or the user passed some flags
    which are specific to a single login provider.
- **manually** : when the login provider is not explicit nor implicit, a list is prompted to let
    the user select a login provider manually.

Once the login provider is selected, its relevant credentials are read from command-line flags
and the user is being prompted for the missing ones (if any). The login provider's `client-method`
is then triggered.

Each login provider has one of these 4 login methods associated to it (`client-method`):

- **dcos-usercredential-post-receive-authtoken**, **dcos-credential-post-receive-authtoken** :
    POST username and password to the `start_flow_url` endpoint.
- **dcos-servicecredential-post-receive-authtoken** : Generate a login token from a service account
    private key. POST username and the generated token to the `start_flow_url` endpoint.
- **browser-prompt-authtoken** : Open the DC/OS cluster UI in a browser, at the page referenced
    in `start_flow_url`. The user is then expected to continue the flow in the browser, eventually
    they are redirected to a page with a token to copy-paste from the browser to their terminal.
    POST this token to `/acs/api/v1/auth/login`.
