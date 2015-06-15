$BaseDir = (Get-Location).Path

cd $BASEDIR
& $BASEDIR\env\Scripts\activate
echo "Virtualenv activated."

tox