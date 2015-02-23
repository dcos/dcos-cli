all: env test

clean:
	bin/clean.sh

env:
	bin/env.sh

test:
	bin/test.sh

doc:
	bin/doc.sh

packages:
	bin/packages.sh
