# Extend the marathon docker image to also include zookeeper and python so that
# we can run integration tests
FROM mesosphere/python-tox:v1
MAINTAINER José Armando García Sancio <jose@mesosphere.io>
RUN echo "deb http://repos.mesosphere.io/debian wheezy main" > \
      /etc/apt/sources.list.d/mesosphere.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv E56151BF && \
    apt-get update && \
    apt-get install -y openjdk-7-jre-headless marathon mesos zookeeper && \
    apt-get clean
