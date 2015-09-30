FROM python:3
MAINTAINER Mesosphere <support@mesosphere.io>

# install dependencies
RUN apt-get update && \
    apt-get install -y python-pip
RUN pip install virtualenv

# install DCOS
RUN virtualenv /dcos
ADD https://downloads.mesosphere.io/dcos-cli/install.sh /tmp/install.sh
RUN chmod +x /tmp/install.sh
RUN DCOS_CLI_VERSION=$docker_cli_version /tmp/install.sh /dcos http://localhost
ENV DCOS_CONFIG=/root/.dcos/dcos.toml
ENV PATH=/dcos/bin:$PATH

ADD init.sh /tmp/init.sh
ENTRYPOINT ["/tmp/init.sh"]
