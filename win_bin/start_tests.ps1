$BaseDir = (Get-Location).Path
& $BaseDir\win_bin\clean.ps1
& $BaseDir\win_bin\env.ps1
& $BaseDir\win_bin\packages.ps1
& $BaseDir\env\Scripts\activate
tox -c tox.win.ini
$DcosCliExitCode = $LastExitCode
& $BaseDir\env\Scripts\deactivate
cd cli
& $BaseDir\cli\win_bin\clean.ps1
& $BaseDir\cli\win_bin\env.ps1
& $BaseDir\cli\env\Scripts\activate
tox -c tox.win.ini
$CliExitCode = $LastExitCode
& $BaseDir\cli\env\Scripts\deactivate
exit ($DcosCliExitCode -or $CliExitCode)
