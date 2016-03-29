all: env test packages

clean:
	bin/clean.sh

env:
	bin/env.sh

test: env
	bin/test.sh

test-binary: env
	bin/test-binary.sh

doc: env
	bin/doc.sh

packages: env
	bin/packages.sh
