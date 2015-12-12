all: env test packages

clean:
	bin/clean.sh
	rm -rf dist docopt

env:
	bin/env.sh

test: env
	bin/test.sh

doc: env
	bin/doc.sh

packages: env
	bin/packages.sh

docopt: env
	mkdir -p docopt
	cp env/lib/python*/site-packages/docopt.py docopt/__init__.py

pyinstaller: env docopt
	find pyinstaller -type f | xargs -n 1 pyinstaller
