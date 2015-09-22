FROM timfallmk/dcos-cli-docker
MAINTAINER "Tim <tim.fall@mesosphere.io>"

RUN apt-get update && apt-get -y install \
                              linux-tools \
                              traceroute \
                              wget \
                              curl \
                              iputils-arping \
                              iputils-ping \
                              iputils-tracepath \
                              iputils-clockdiff \
                              jq \
                              gdb \
                              sysstat \
                              procps \
                              htop \
                              vim \
                              emacs \
                              git \
                              findutils\
 && apt-get clean

ADD https://raw.githubusercontent.com/mesosphere/docker-containers/master/dcos-debug/toolbox ./toolbox
