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
    "description": "Default DC/OS login provider"
  }
}
```

The above definition is a default DC/OS login provider, its ID is **dcos-users**.
The ID has no special semantic apart from uniquely identifying a login provider.

When the `/acs/api/v1/auth/providers` endpoint is not present, the available login provider is
detected by making an unauthenticated `HEAD` request to a well-known protected DC/OS resource and
reading the `WWW-Authenticate` header DC/OS returns in the 401 response:

- `acsjwt` : the cluster only supports the `dcos-users` provider as defined above.
- `oauthjwt` : the cluster only supports the OpenID Connect implicit flow provider, as defined below:

``` json
{
  "dcos-oidc-auth0": {
    "authentication-type": "oidc-implicit-flow",
    "client-method": "browser-prompt-oidcidtoken-get-authtoken",
    "config": {
      "start_flow_url": "/login?redirect_uri=urn:ietf:wg:oauth:2.0:oob"
    },
    "description": "Google, GitHub, or Microsoft"
  }
}
```

If the `Head` request returns a 200 response, authentication is disabled on this cluster. Setup will
succeed and the cluster will be usable but any calls to `dcos auth login` or
`dcos auth list-providers` will result in an error.

## Log in to a DC/OS cluster

"Login" is the process of presenting some credentials to a DC/OS cluster within an HTTP request which is then,
upon success, responded to with an HTTP response containing a so-called DC/OS authentication token.

The DC/OS CLI supports 6 providers types (`authentication-type`):

- **dcos-uid-password** : Log in using a regular DC/OS user account (username and password).
- **dcos-uid-password-ldap** : Log in using an LDAP user account (username and password).
- **dcos-uid-servicekey** : Log in using a DC/OS service user account (username and private key).
- **saml-sp-initiated** : Log in using SAML 2.0.
- **oidc-authorization-code-flow** : Log in using OpenID Connect authorization code flow.
- **oidc-implicit-flow** : Log in using OpenID Connect implicit flow.

A login happens through the `dcos auth login` command, which accepts the following flags:

- **--provider** : Specify the login provider ID to use.
- **--username** : Specify the username.
- **--password** : [INSECURE] Specify password in plaintext on the command-line. This should
                   only be used in development / testing environments as it can leak the
                   password in various ways.
- **--password-file** : Specify the path to a file that contains the password.
- **--private-key** : Specify the path to the private key for service account login.

The username and password can also be read from the `DCOS_USERNAME` and `DCOS_PASSWORD` environment
variables. Flags (`--username`, `--password`, `--password-file`) take precedence over environment variables.

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

Each login provider has one of these 5 login methods associated to it (`client-method`):

- **dcos-usercredential-post-receive-authtoken**, **dcos-credential-post-receive-authtoken** :
    POST username and password to the `start_flow_url` endpoint.
- **dcos-servicecredential-post-receive-authtoken** : Generate a login token from a service account
    private key. The login token is valid for 5 minutes. POST username and the generated token to the
    `start_flow_url` endpoint.
- **browser-prompt-authtoken** : Open the browser at the page referenced in `start_flow_url`. The user
    is then expected to continue the flow in the browser, eventually they are redirected to a page with
    a login token to copy-paste from the browser to their terminal (in some cases the token will be
    intercepted directly by the CLI, see `Local web server` section). POST this token to
    `/acs/api/v1/auth/login`.
- **browser-prompt-oidcidtoken-get-authtoken** : Open the browser at the page referenced in
    `start_flow_url`. The user is then expected to continue the flow in the browser, eventually
    they are redirected to a page with an OpenID Connect ID token to copy-paste from the browser
    to their terminal. Make a HEAD request to a well-known resource with the appropriate
    Authorization header in order to verify the token.

> `start_flow_url` can either be an absolute URL or a cluster relative path.

## Local web server

When initiating a flow for the `dcos-oidc-auth0` login provider ID, the CLI will spin-up
a local web server on a free port. This is done by using port `0`.

The CLI then tries to open the user browser (using `xdg-open <url>` on Linux, `open <url>` on macOS,
`rundll32 url.dll,FileProtocolHandler <url>` on Windows) at the `start_flow_url` with an extra
`redirect_uri` parameter (eg. `http://my-cluster.example.com/login?redirect_uri=http://localhost:8080`),
which refers to the URL where the local web server is listening.

In case the browser didn't open (eg. SSH session on a remote machine), the user also sees the following
message:

``` console
If your browser didn't open, please follow this link:

    http://my-cluster.example.com/login?redirect_uri=http://localhost:8080
```

On successful login, our [Auth0 universal login page](https://github.com/mesosphere/auth0-ui) is
configured to make a `GET` request to the `redirect_uri`, with the token as a `token` query parameter.
For example: `http://localhost:8080?token=myLoginToken123`

The local web server can then retrieve the token and continue the login flow. If this request fails
(eg. the CLI runs on a remote machine), the login page falls back to printing the token in a modal box,
asking the user to copy-paste it to their terminal. The CLI will read it from stdin and continue the login flow.
