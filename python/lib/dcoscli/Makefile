all: env packages binary test
all-docker: env-docker packages-docker binary-docker test-docker

clean:
	@bash bin/clean.sh

distclean: clean
	@bash bin/distclean.sh

env:
	@bash bin/env.sh

packages: env
	@bash bin/packages.sh

binary: env
	@bash bin/binary.sh

test: env
	@bash bin/test.sh

test-binary: binary
	@bash bin/test-binary.sh

env-docker:
	@bash bin/docker.sh env

packages-docker: env-docker
	@bash bin/docker.sh packages

binary-docker: env-docker
	@bash bin/docker.sh binary

test-docker: env-docker
	@bash bin/docker.sh test

test-binary-docker: binary-docker
	@bash bin/docker.sh test-binary

.PHONY: env env-docker
