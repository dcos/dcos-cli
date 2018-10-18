# setup

The setup package is responsible for configuring the DC/OS CLI to interact with DC/OS clusters.

## Goals

For a given DC/OS master URL, the package will:

- Download the DC/OS CA bundle (in case of an HTTPS URL).
- Initiate a login.
- Create a cluster config with the ACS token, the TLS configuration, and cluster name.
- Attach the CLI to the newly created cluster config.
- Automatically install "dcos-core-cli" and "dcos-enterprise-cli" plugins after the setup (experimental).

## Implementation

The setup is triggered with the following command:

    dcos cluster setup https://dcos.example.com

The URL refers to a DC/OS master node. The command accepts the following flags which only apply for an
HTTPS URL:

    --ca-certs=<ca-certs>
        Specify the path to a CA bundle file in PEM format. The CLI will then use it to verify that
        certificates returned by the cluster have a trusted chain.

    --insecure
        INSECURE: Do not verify certificates returned by the cluster. With this option, even though the
        HTTPS protocol is used, there is no guarantee that the remote end is your actual DC/OS cluster.
        This flag should only be used during development / testing.

    --no-check
        INSECURE: When the --ca-certs flag is not passed, the CLI will attempt to download the CA
        bundle from the DC/OS cluster. As this uses an insecure request, the user is prompted with
        CA bundle information and fingerprints and is expected to confirm that they are to be trusted.
        Passing --no-check disables this manual verification step, it should only be used during
        development / testing.

The setup command also accepts all the flags from the `dcos auth login` command as it triggers a login
flow during the setup.

### Detect the canonical cluster URL

The first step of the setup flow is to detect the cluster canonical URL. This is done by making
an HTTP HEAD request to the root path (eg. http://dcos.example.com/). If the response is one of
the following redirect codes, the CLI will follow it, up to a maximum of 10 redirects:

- 301 (Moved Permanently)
- 302 (Found)
- 303 (See Other)
- 307 (Temporary Redirect)
- 308 (Permanent Redirect)

When there are more than 10 redirects or the status code of the last response is not 200,
the setup flow errors-out. Otherwise, the URL associated with the last response is considered
as the **canonical cluster URL**.

When the canonical cluster URL is different than the one given in argument of the `dcos cluster setup`
command, a warning indicates to the user that the setup will continue with this new URL.

### Install the root CA bundle (HTTPS only)

When the URL to setup has the https scheme (either originally, or has been switched from http to https
afterwards during the canonical URL detection) and the `--insecure` option hasn't been passed, the CLI
must ensure that it is able to communicate with the server securely.

The CLI first makes an HTTPS HEAD request to the cluster in order to check if the server certificate
has been issued by an authority already trusted by the system. When it's the case, there is nothing
more to configure and the CLI is ready to use HTTPS with this cluster. When the server certificate is
not from a trusted anchor, the root CA bundle must be installed:

- either from the filesystem (when the `--ca-bundle=/path/to/ca` option has been passed), this assumes
    the user got the CA bundle out-of-band before initiating the cluster from the CLI.

- or by downloading it from the cluster. As this uses an insecure request, the user is prompted for
    manual verification of all certificates in the bundle (unless the `--no-check` option has been
    passed). The prompt includes the certificate issuer, its validity dates, and fingerprint.
    The fingerprint is the hexadecimal SHA256 hash of the whole certificate in DER format.

### Login

The next steps is to login to the cluster, the setup command accepts the same flags as the
`dcos auth login` command and acts similarly in this regard.

If authentication is disabled on the cluster, a warning will be printed and this step will
be skipped.

### Cluster ID and name

In order to manage different clusters, the CLI keeps track of their ID and name. The cluster ID is
retrieved through the `/dcos-metadata/dcos-version.json` endpoint while the name is extracted from
the Mesos `/state/summary` endpoint.

## Creating the cluster config

When all the above steps have been completed, the cluster config is persisted on disk and the CLI is
attached to it. A cluster config looks like this:

    # /home/user/.dcos/clusters/<cluster_id>/dcos.toml
    [core]
    dcos_url = "<dcos_cluster_url>"
    dcos_acs_token = "<authentication_token>"
    ssl_verify = "/home/user/.dcos/clusters/<cluster_id>/dcos-ca.crt"

    [cluster]
    name= "<cluster_name>"

## Automatically installing default plugins (experimental)

Finally, when the `DCOS_CLI_EXPERIMENTAL_AUTOINSTALL_PLUGINS` env var is set, the CLI will attempt to
auto-install "dcos-core-cli" and "dcos-enterprise-cli" plugins.

These plugins download URLs are retrieved through Cosmos, where they are registered as packages.

### dcos-core-cli

The [core plugin](https://github.com/dcos/dcos-core-cli) contains subcommands such as marathon, job, node,
package, service, task.

### dcos-enterprise-cli

The [enterprise plugin](https://github.com/mesosphere/dcos-enterprise-cli) gets installed when an EE
cluster is detected.

This is determined through the [DC/OS variant](https://jira.mesosphere.com/browse/DCOS_OSS-2283) field
(new in 1.12). For previous versions of DC/OS we won’t try to detect open / enterprise as it’d involve
some hacks, but rather display a message saying “Please run “dcos package install dcos-enterprise-cli” if
you use a DC/OS Enterprise cluster”.
