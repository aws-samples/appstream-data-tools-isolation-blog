#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import json
import boto3

appstream = boto3.client('appstream')
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')
sagemaker = boto3.client('sagemaker')


def lambda_handler(event, context):
    #grab the bucket name and the object from the users's homefolder on S3. 
    for i in range(len(event)):
        event_bucket = event['Records'][i]['s3']['bucket']['name']
        event_key = event['Records'][i]['s3']['object']['key']

    json_object = s3_client.get_object(Bucket=event_bucket, Key=event_key)
    json_data = json_object['Body'].read()
    json_dict = json.loads(json_data)
    
    #print some information, to help with troubleshooting. 
    print('Print bucket name where the users home folder resides')
    print(json_dict['bucketName'])
    print('Print prefix name where the user objects can be found')
    print(json_dict['prefixName'])
    print('Print authentication type being used by the user (for example, userpool, custom, saml')
    print(json_dict['authType'])


    #set authtype so it can be used to describe the AppStream session. 
    authtype = json_dict['authType']
    
    #set prefix so that it can be used to post back files to the homefolder bucket. 
    prefix = json_dict['prefixName']
    
    #convert authtpye and prefix based on the type of connection. 
    if authtype == 'custom':
        authtype = 'API'
    elif authtype == 'userpool':
        #convert prefix as the original prefix comes in as 'custom' and should really be 'userpool'
        rawprefix = json_dict['prefixName']
        prefix = rawprefix.replace("custom", authtype)
        

    #grab session information from the AppStream API to determine whether the Session ID and the UserID match. 
    resp = appstream.describe_sessions(StackName=json_dict['stackName'], FleetName=json_dict['fleetName'],
                                       UserId=json_dict['user'], AuthenticationType=authtype.upper())
    print (resp)                                     
    resp_user_session = resp['Sessions'][0]['Id']

    
    if json_dict['sessionId'] == resp_user_session:
        print("AppStream Session ID has been validated")
        
        #generate the SageMaker pre-signed URL. 
        sagemaker_resp = sagemaker.create_presigned_notebook_instance_url(NotebookInstanceName="Data-Sandbox-Notebook",
                                                                          SessionExpirationDurationInSeconds=1800)
        sagemaker_url = sagemaker_resp['AuthorizedUrl']

        #place the URL in the users's homefolder so that they can launch the Notebook. 
        s3_client.put_object(Bucket=json_dict['bucketName'],
                                 Body=sagemaker_url,
                                 Key=f"{prefix}/session_url.txt")
    else:
        print("AppStream Session ID is invalid")
        error_msg = "You are running an invalid session, please close your session and log back in."
        s3_client.put_object(Bucket=json_dict['bucketName'],
                             Body=error_msg,
                             Key=f"{prefix}/session_url.txt")
