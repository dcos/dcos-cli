all: env test packages

clean:
	bin/clean.sh
	rm -rf dist

env:
	bin/env.sh

test: env
	bin/test.sh

doc: env
	bin/doc.sh

packages: env
	bin/packages.sh

pyinstaller: env
	find pyinstaller -type f | xargs -n 1 pyinstaller
