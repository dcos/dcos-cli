# Configure a Debian testing distro to run Tox for Python 2.7 and 3.4
FROM debian:testing
MAINTAINER José Armando García Sancio <jose@mesosphere.io>
RUN apt-get update && \
    apt-get install -y python2.7 python3.4 python-pip python-dev && \
    apt-get clean
RUN pip install tox
