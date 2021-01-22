#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

$SSM1 = aws ssm get-parameter --name /s3/datasandboxbucket --region $Env:AWS_Region --profile appstream_machine_role| ConvertFrom-Json
$SSM2 = $SSM1.Parameter.Value | Out-String
$SSM3 = $SSM2 | ConvertFrom-Json

$ScriptBucket = $SSM3.'bucket-name'
$S3Path = "s3://$ScriptBucket"
$UserProfile = $env:USERPROFILE

$S3ScriptLocation = 'appstream-scripts/sagemaker-notebook.ps1'

$ScriptLocalLocation = "$UserProfile\Documents\sagemaker-notebook.ps1"

$CopyScriptFile = aws s3 cp "$($S3Path)/$($S3ScriptLocation)" $ScriptLocalLocation --profile appstream_machine_role

Start-Process PowerShell.exe $ScriptLocalLocation