#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

# Define initial variables from AppStream

$UserName = $Env:AppStream_UserName
$SessionId = $Env:AppStream_Session_ID
$StackName = $Env:AppStream_Stack_Name
$FleetName = $Env:AppStream_Resource_Name
$AuthType = $Env:AppStream_User_Access_Mode
$PrefixStatic = "user/custom/"
$HomeLocation = "C:\Users\PhotonUser\My Files\Home Folder\"
$HomeLocationRequests = "C:\Users\PhotonUser\My Files\Home Folder\"
$HomeLocationURIs = "C:\Users\PhotonUser\My Files\Home Folder\session_url.txt"

# Greet the user in the PowerShell Terminal

Write-Host "Welcome, $UserName."

# Get the bucket string of where AppStream syncs the Home Folder

$BucketStatic = "appstream2-36fb080bb8-"
$ArnID = $env:AppStream_Image_Arn -replace "[^0-9]", ''
$AccountId = $ArnID.substring(1)
$BucketName = "$($BucketStatic)$($env:AWS_Region)-$($AccountId)".Trim()

# Hash the Username using Get-FileHash

$StringAsStream = [System.IO.MemoryStream]::new()
$Writer = [System.IO.StreamWriter]::new($stringAsStream)
$Writer.write("$UserName")
$Writer.Flush()
$StringAsStream.Position = 0
$Hash = Get-FileHash -Algorithm SHA256 -InputStream $StringAsStream | Select-Object Hash | Format-Table -HideTableHeaders | Out-String
$HashTrim = $Hash.Trim()

$PrefixName = "$($prefixStatic)$($HashTrim)".ToLower()

# Create the initial message to trigger the security lambda function

$Str =@"
{"user":"$UserName", "sessionId": "$SessionId", "bucketName": "$BucketName", "prefixName": "$PrefixName", "stackName": "$StackName", "fleetName": "$FleetName", "authType": "$AuthType"}
"@

$JsonPath = "$($HomeLocationRequests)session.json"

# Stalls the script if it's a first time user, so that the home folder can be set up

$FolderSetUp  = Test-Path $JsonPath

If ( $FolderSetUp -eq $false )
{
    Write-Host "Setting up your Home Folder location for the first time."
    Do {
        $SetUp = $false
        Try {
             $Json = $Str | Out-File $JsonPath
        } Catch { $SetUp = $True }
    } While ( $SetUp )
}

$Json = $Str | Out-File $JsonPath
Write-Host "Opening your SageMaker Instance...Please wait a moment."

# Add for each loop to run it 300 times with one second sleeps. This corresponds to boto3 SageMaker pre-signed URL expiration

foreach ( $i in 1..300 )
{
    if ( Test-Path $HomeLocationURIs )
    {
        $ResponseContent = Get-Content $HomeLocationURIs
        if ( $ResponseContent -eq "You are running an invalid session, please log back in." )
        {
            $Output = "Invalid session, please close the session and log back in"
            echo $ResponseContent
            Break
        } else {
            start-process 'C:\Program Files (x86)\Mozilla Firefox\firefox.exe' $ResponseContent
            $Output = "SageMaker opened successfully"
            Break
        }
        Break
    }
    Sleep 1
}

Remove-Item $HomeLocationURIs
