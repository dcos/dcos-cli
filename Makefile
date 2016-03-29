all: env test packages

clean:
	bin/clean.sh

env:
	bin/env.sh

test: env
	bin/test.sh

doc: env
	bin/doc.sh

packages: env
	bin/packages.sh

binary: clean env packages
	rm -rf dist build
	pyinstaller binary/binary.spec
