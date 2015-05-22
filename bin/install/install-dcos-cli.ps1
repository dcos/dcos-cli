param([Parameter(Mandatory=$true,ValueFromPipeline=$true)]
  [string]
  $installation_path,
  [Parameter(Mandatory=$true,ValueFromPipeline=$true)]
  [string]
  $dcos_url
  )

if (-Not(Get-Command python -errorAction SilentlyContinue))
{
  echo "The program 'python' could not be found. Make sure that 'python' is installed and that its directory is included in the PATH system variable."
  exit 1
}

$PYTHON_VERSION = (python --version) 2>&1

if ($PYTHON_VERSION -match "[0-9]+.[0-9]+") {
    $PYTHON_VERSION = $matches[0]

    if (-Not (($PYTHON_VERSION -eq "2.7") -Or ($PYTHON_VERSION -eq "3.4"))) {
        echo "Python must be version 2.7 or 3.4. Aborting."
        exit 1
    }
}

if (-Not(Get-Command pip -errorAction SilentlyContinue))
{
  echo "The program 'pip' could not be found. Make sure that 'pip' is installed and that its directory (eg 'C:\Python27\Scripts') is included in the PATH system variable."
  exit 1
}

if (-Not(Get-Command virtualenv -errorAction SilentlyContinue))
{
  echo "The program 'virtualenv' could not be found. Make sure that it has been installed with the 'pip' Python package program."
  exit 1
}

$VIRTUAL_ENV_VERSION = (virtualenv --version)

$VIRTUAL_ENV_VERSION  -match "[0-9]+"

if ($matches[0] -lt 12) {
  echo "Virtualenv version must be 12 or greater. Aborting."
  exit 1
}

if (-Not(Get-Command git -errorAction SilentlyContinue))
{
  echo "The program 'git' could not be found. Make sure that 'git' is installed and that its directory is included in the PATH system variable."
  exit 1
}

echo "Installing DCOS CLI from PyPI..."
echo ""

if (-Not([System.IO.Path]::IsPathRooted("$installation_path"))) {
  $installation_path = Join-Path (pwd) $installation_path
}

if (-Not( Test-Path $installation_path)) {
  mkdir  $installation_path
}

& virtualenv $installation_path
& $installation_path\Scripts\activate

[int]$PYTHON_ARCHITECTURE=(python -c 'import struct;print( 8 * struct.calcsize(\"P\"))')

if ($PYTHON_ARCHITECTURE -eq 64) {
  & $installation_path\Scripts\easy_install  "http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20219/pywin32-219.win-amd64-py$PYTHON_VERSION.exe" 2>&1 | out-null
} else {
  & $installation_path\Scripts\easy_install  "http://downloads.sourceforge.net/project/pywin32/pywin32/Build%20219/pywin32-219.win32-py$PYTHON_VERSION.exe" 2>&1 | out-null
}

if ($env:DCOS_CLI_VERSION) {
  & $installation_path\Scripts\pip install --quiet "dcoscli==$env:DCOS_CLI_VERSION"
} else {
  & $installation_path\Scripts\pip install --quiet "dcoscli"
}


[Environment]::SetEnvironmentVariable("Path", "$installation_path\Scripts\;", "User")
$env:Path="$env:Path;$installation_path\Scripts\"

$DCOS_CONFIG="$env:USERPROFILE\.dcos\dcos.toml"

if (-Not(Test-Path $DCOS_CONFIG)) {
  mkdir "$env:USERPROFILE\.dcos"
  New-Item $DCOS_CONFIG -type file
}
[Environment]::SetEnvironmentVariable("DCOS_CONFIG", "$DCOS_CONFIG", "User")
$env:DCOS_CONFIG = $DCOS_CONFIG

dcos config set core.reporting true
dcos config set core.dcos_url $dcos_url
dcos config set package.cache $env:temp\dcos\package-cache
dcos config set package.sources '[\"https://github.com/mesosphere/universe/archive/master.zip\"]'

dcos package update
