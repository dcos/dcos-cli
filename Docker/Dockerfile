FROM python:3
MAINTAINER "Tim <tim.fall@mesosphere.io>"

RUN apt-get update && apt-get install -y vim wget curl python-pip openjdk-7-jre-headless
RUN pip install virtualenv

WORKDIR /dcos

ADD https://downloads.mesosphere.io/dcos-cli/install.sh install.sh
ADD startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

ENTRYPOINT ["/usr/local/bin/startup.sh"]
