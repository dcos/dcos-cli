all: env packages doc test
all-docker: env-docker packages-docker doc-docker test-docker

clean:
	@bash bin/clean.sh

distclean: clean
	@bash bin/distclean.sh

env:
	@bash bin/env.sh

packages: env
	@bash bin/packages.sh

doc: env
	@bash bin/doc.sh

test: env
	@bash bin/test.sh

env-docker:
	@bash bin/docker.sh env

packages-docker: env-docker
	@bash bin/docker.sh packages

doc-docker: env-docker
	@bash bin/docker.sh doc

test-docker: env-docker
	@bash bin/docker.sh test


.PHONY: plugin
plugin:
	@python3 scripts/plugin/package_plugin.py

.PHONY: env env-docker
