#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import json
import boto3

appstream = boto3.client('appstream')
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')
sagemaker = boto3.client('sagemaker')


def lambda_handler(event, context):
    for i in range(len(event)):
        event_bucket = event['Records'][i]['s3']['bucket']['name']
        event_key = event['Records'][i]['s3']['object']['key']

    json_object = s3_client.get_object(Bucket=event_bucket, Key=event_key)
    json_data = json_object['Body'].read()
    json_dict = json.loads(json_data)

    resp = appstream.describe_sessions(StackName=json_dict['stackName'], FleetName=json_dict['fleetName'],
                                       UserId=json_dict['user'])
    resp_user_session = resp['Sessions'][0]['Id']

    if json_dict['sessionId'] == resp_user_session:
        sagemaker_resp = sagemaker.create_presigned_notebook_instance_url(NotebookInstanceName="Data-Sandbox-Notebook",
                                                                          SessionExpirationDurationInSeconds=1800)
        sagemaker_url = sagemaker_resp['AuthorizedUrl']
        s3_client.put_object(Bucket=json_dict['bucketName'],
                             Body=sagemaker_url,
                             Key=f"{json_dict['prefixName']}/session_url.txt")
    else:
        error_msg = "You are running an invalid session, please log back in."
        s3_client.put_object(Bucket=json_dict['bucketName'],
                             Body=error_msg,
                             Key=f"{json_dict['prefixName']}/session_url.txt")
