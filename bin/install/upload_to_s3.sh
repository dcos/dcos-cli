#!/bin/bash -x

aws s3 --region=us-east-1 cp \
dcos-cli/bin/install/install-dcos-cli.sh \
%aws.bash_destination_url%

aws s3 --region=us-east-1 cp \
dcos-cli/bin/install/install-optout-dcos-cli.sh \
%aws.bash_optout_destination_url%

aws s3 --region=us-east-1 cp \
dcos-cli/win_bin/install/install-dcos-cli.ps1 \
%aws.powershell_destination_url%

aws s3 --region=us-east-1 cp \
dcos-cli/bin/install/legacy/install-legacy-dcos-cli.sh \
%aws.bash_legacy_destination_url%

aws s3 --region=us-east-1 cp \
dcos-cli/bin/install/install-legacy_optout-dcos-cli.sh \
%aws.bash_legacy_optout_destination_url%

aws s3 --region=us-east-1 cp \
dcos-cli/win_bin/install/legacy/install-legacy-dcos-cli.ps1 \
%aws.powershell_legacy_destination_legacy_url%
