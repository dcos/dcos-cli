from dcos_cli.cli.dcos import dcos

# This file is a workaround for pyinstaller not being able to use entrypoints
# by default (cf. https://github.com/pyinstaller/pyinstaller/issues/305).

dcos(prog_name='dcos')
