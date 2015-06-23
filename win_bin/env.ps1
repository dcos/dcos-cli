$BaseDir = (Get-Location).Path
if (-Not (Test-Path $BaseDir\env -PathType Container)) {
    virtualenv -q $BASEDIR/env --prompt='(dcoscli) '
    echo "Virtualenv created."

    & $BASEDIR/env/Scripts/activate
    echo "Virtualenv activated."

    & $BASEDIR/env/Scripts/pip.exe install -r $BASEDIR/requirements.txt
    & $BASEDIR/env/Scripts/pip.exe install -e $BASEDIR
    echo "Requirements installed."
}
ElseIf ((Test-Path $BASEDIR/env/bin/activate )) {

    & $BASEDIR/env/Scripts/activate
    echo "Virtualenv activated."

    & $BASEDIR/env/Scripts/pip install -r $BASEDIR/requirements.txt
    & $BASEDIR/env/Scripts/pip install -e $BASEDIR
    echo "Requirements installed."

}