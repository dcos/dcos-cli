$BaseDir = (Get-Location).Path

echo "Building wheel..."
"$BASEDIR/env/bin/python" setup.py bdist_wheel

echo "Building egg..."
"$BASEDIR/env/bin/python" setup.py sdist
