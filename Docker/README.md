# dcos-cli-docker
DCOS CLI in a Docker Container

#### Usage
Once your cluster is up and running, you can input the URL to pull down the setup information.

```
docker run -i -t <container namespace needed> <url>
```

You can skip the initial setup step by specifying a different `ENTRYPOINT`.

```
docker run -i -t --entrypoint bash <container namespace needed>
```
