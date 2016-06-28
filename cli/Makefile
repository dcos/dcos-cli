all: env test packages

clean:
	bin/clean.sh

env:
	bin/env.sh

test: env
	bin/test.sh

binary: clean env packages
	bin/create-binary.sh

test-binary: binary
	bin/test-binary.sh

doc: env
	bin/doc.sh

packages: env
	bin/packages.sh
