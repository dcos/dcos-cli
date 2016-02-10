#!/bin/bash -x

COSMOS_VERSION="0.4.0"

cosmos_cli()
{
        # result is the larger of the two versions
        # convert the str to numbers, sort, and return the larger
        result=$(echo -e "$COSMOS_VERSION\n$TAG_VERSION" | sed '/^$/d' | sort -nr | head -1)
        # if TAGGED_VERSION >= COSMOS_VERSION we want to use cosmos cli
        [[ "$result" = "$TAG_VERSION" ]]
}

if cosmos_cli ; then
        aws s3 --region=us-east-1 cp \
        dcos-cli/bin/install/install-dcos-cli.sh \
        %aws.bash_destination_url%

        aws s3 --region=us-east-1 cp \
        dcos-cli/win_bin/install/install-dcos-cli.ps1 \
        %aws.powershell_destination_url%
else
        aws s3 --region=us-east-1 cp \
        dcos-cli/bin/install/legacy/install-legacy-dcos-cli.sh \
        %aws.legacy_bash_destination_url%

        aws s3 --region=us-east-1 cp \
        dcos-cli/win_bin/install/legacy/install-legacy-dcos-cli.ps1 \
        %aws.legacy_powershell_destination_legacy_url%
fi
