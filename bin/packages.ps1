$BaseDir = (Get-Location).Path

echo "Building wheel..."
& "$BASEDIR\env\Scripts\python.exe" setup.py bdist_wheel

echo "Building egg..."
& "$BASEDIR\env\Scripts\python.exe" setup.py sdist
