# httpclient

The httpclient package manages the HTTP requests from the DC/OS CLI to DC/OS clusters.

It is is largely based on the client provided by the "net/http" package.

## Goals

The goal of the httpclient package is to offer simple functions to send requests to DC/OS clusters. The client uses the DC/OS CLI configuration to know what is the URL of the cluster and which headers should be added to each request made against the cluster.

