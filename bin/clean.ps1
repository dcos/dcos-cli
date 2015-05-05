$BaseDir = (Get-Location).Path
Remove-Item $BASEDIR\env -Recurse -Force -erroraction 'silentlycontinue'
Remove-Item $BASEDIR\dist -Recurse -Force -erroraction 'silentlycontinue'
Remove-Item $BASEDIR\build -Recurse -Force -erroraction 'silentlycontinue'
Get-ChildItem -Path $BaseDir -Filter *.pyc -Recurse | Remove-Item -Force