#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import json
import boto3

iam = boto3.client('iam')


def lambda_handler(event, context):
    
    appstream_service_role_policy_document = { "Version": "2012-10-17", "Statement": [ { "Effect": "Allow", "Principal": { "Service": "appstream.amazonaws.com" }, "Action": "sts:AssumeRole" } ] }
    appstream_autoscaling_role_policy_document = { "Version": "2012-10-17", "Statement": [ { "Effect": "Allow", "Principal": { "Service": "application-autoscaling.amazonaws.com" }, "Action": "sts:AssumeRole" } ] }

    try:
        query_appstream_service_role = iam.get_role(
        RoleName='AmazonAppStreamServiceAccess'
        )
        print("AppStream Service role already exists")
    except:
        print('AppStream Service role does not yet exist, and will be created')
        create_appstream_service_role = iam.create_role(
            Path="/service-role/",
            RoleName="AmazonAppStreamServiceAccess",
            AssumeRolePolicyDocument=json.dumps(appstream_service_role_policy_document),
            Description="Amazon AppStream Service Access Role"
            )
        attach_appstream_service_access_role_policy = iam.attach_role_policy(
                RoleName="AmazonAppStreamServiceAccess",
                PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonAppStreamServiceAccess'
            )
            
    try:
        query_appstream_autoscaling_role = iam.get_role(
        RoleName='ApplicationAutoScalingForAmazonAppStreamAccess'
        )
        print("AppStream Autoscaling role already exists")
    except:
        print('AppStream Autoscaling role does not yet exist, and will be created')
        create_appstream_autoscaling_role = iam.create_role(
            Path="/service-role/",
            RoleName="ApplicationAutoScalingForAmazonAppStreamAccess",
            AssumeRolePolicyDocument=json.dumps(appstream_autoscaling_role_policy_document),
            Description="Amazon AppStream Service Access Role"
            )
        attach_appstream_service_access_role_policy = iam.attach_role_policy(
                RoleName="ApplicationAutoScalingForAmazonAppStreamAccess",
                PolicyArn='arn:aws:iam::aws:policy/service-role/ApplicationAutoScalingForAmazonAppStreamAccess'
            )
