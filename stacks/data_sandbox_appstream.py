#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    aws_appstream as appstream,
    aws_ec2 as ec2,
    core,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_cloudformation as cfn,
    custom_resources as cr,
    aws_s3 as s3
)
from aws_cdk.core import Aws

current_dir = os.path.dirname(__file__)


class AppstreamStack(cfn.NestedStack):
    def __init__(self, scope: core.Construct, id: str, aws_region='', vpc='', s3stack='', **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        #parameters
        appstream_environment_name = self.node.try_get_context("appstream_environment_name")
        appstream_image_name = self.node.try_get_context("appstream_image_name")
        appstream_instance_type = self.node.try_get_context("appstream_instance_type")
        appstream_fleet_type = self.node.try_get_context("appstream_fleet_type")
        
        #build AppStream security
        self.appstream_security_group = ec2.SecurityGroup(
            self, 'AppStreamSecurityGroup',
            vpc=vpc,
            security_group_name='appstream-sg'
        )
        
        #build AppStream role
        self.appstream_role = iam.Role(
            self,
            id='appstream-role',
            description='Role for the AppStream fleet',
            max_session_duration=core.Duration.seconds(3600),
            assumed_by=iam.ServicePrincipal('appstream.amazonaws.com'),
            inline_policies={
                'AllowSSMAccess': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=['ssm:GetParameter'],
                            resources=['*']
                        )
                    ]
                ),
                'AllowS3Access': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=['s3:GetObject', 's3:ListBucket'],
                            resources=[f'arn:aws:s3:::{s3stack.bucket_name}/*',
                                      f'arn:aws:s3:::{s3stack.bucket_name}']
                        )
                    ]
                )
            }
        )

        appstream_fleet = appstream.CfnFleet(self, 'AppStreamFleet',
             compute_capacity=appstream.CfnFleet.ComputeCapacityProperty(
                 desired_instances=5),
             instance_type=appstream_instance_type,
             fleet_type=appstream_fleet_type,
             idle_disconnect_timeout_in_seconds=0,
             disconnect_timeout_in_seconds=345600,
             max_user_duration_in_seconds=345600,
             image_name=appstream_image_name,
             name=f'{appstream_environment_name}-fleet',
             vpc_config=appstream.CfnFleet.VpcConfigProperty(
                 security_group_ids=[self.appstream_security_group.security_group_id],
                 subnet_ids=vpc.select_subnets(
                     subnet_type=ec2.SubnetType.ISOLATED).subnet_ids))

        appstream_stack = appstream.CfnStack(self, 'AppStreamStack',
             description='AppStream stack for Data Sandbox',
             display_name='AppStream Data Sandbox Stack',
             name=f'{appstream_environment_name}-stack',
             storage_connectors=[appstream.CfnStack.StorageConnectorProperty(
                 connector_type='HOMEFOLDERS')],
             user_settings=[{"action": "CLIPBOARD_COPY_FROM_LOCAL_DEVICE",
                             "permission": "ENABLED"},
                            {"action": "CLIPBOARD_COPY_TO_LOCAL_DEVICE",
                             "permission": "DISABLED"},
                            {"action": "FILE_DOWNLOAD", "permission": "DISABLED"},
                            {"action": "PRINTING_TO_LOCAL_DEVICE",
                             "permission": "DISABLED"}]
             )

        fleet_association = appstream.CfnStackFleetAssociation(self, 'AppStreamFleetAssociation',
           fleet_name=f'{appstream_environment_name}-fleet',
           stack_name=f'{appstream_environment_name}-stack'
           )

        fleet_association.add_depends_on(appstream_stack)
        fleet_association.add_depends_on(appstream_fleet)

        # Build Lambda Function Resources

        # Define Lambda Function Policy

        lambda_inline_policy = {
            'AllowS3ListBkt': iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            's3:ListBucket',
                            's3:ListBucketByTags',
                            's3:GetObject',
                            's3:PutObject'
                        ],
                        resources=[f'arn:aws:s3:::appstream2-36fb080bb8-{Aws.REGION}-{Aws.ACCOUNT_ID}',
                                   f'arn:aws:s3:::appstream2-36fb080bb8-{Aws.REGION}-{Aws.ACCOUNT_ID}/*']
                    )
                ]
            ),
            'AllowLogGroup': iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                            'logs:PutRetentionPolicy'
                        ],
                        resources=["*"]
                    )
                ]
            ),
            'AllowNotebookAccess': iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=['sagemaker:ListTags', 'sagemaker:ListNotebookInstances',
                                 'sagemaker:CreatePresignedDomainUrl', 'sagemaker:CreatePresignedNotebookInstanceUrl'],
                        resources=[
                            f'arn:aws:sagemaker:{Aws.REGION}:{Aws.ACCOUNT_ID}:notebook-instance/data-sandbox-notebook']
                    )
                ]
            )
        }

        # Build Lambda Role
        lambda_role = iam.Role(
            self,
            id='lambda-role',
            description='Role Data Sandbox lambda',
            max_session_duration=core.Duration.seconds(3600),
            role_name=f'data-sandbox-{Aws.REGION}-lambda-role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonAppStreamReadOnlyAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMReadOnlyAccess")],
            inline_policies=lambda_inline_policy
        )


        # Build Lambda Function
        data_sandbox_lambda = _lambda.Function(self, 'DataSandboxLambda',
           handler='data_sandbox_lambda.lambda_handler',
           runtime=_lambda.Runtime.PYTHON_3_8,
           code=_lambda.Code.asset(os.path.join(current_dir, '../lambda')),
           role=lambda_role,
           memory_size=256,
           timeout=core.Duration.seconds(60),
           log_retention=logs.RetentionDays.THREE_MONTHS,
           log_retention_role=lambda_role
           )

        # Grant S3 access to invoke the lambda function
        data_sandbox_lambda_permissions = _lambda.CfnPermission(self, 'LambdaPermissions',
            principal='s3.amazonaws.com',
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:s3:::appstream2-36fb080bb8-{Aws.REGION}-{Aws.ACCOUNT_ID}",
            function_name=data_sandbox_lambda.function_name,
            source_account=f'{Aws.ACCOUNT_ID}'
            )

        #put bucket notification on AppStream homefolder
        
        appstream_homefolder_bucket_array = [f'arn:aws:s3:::appstream2-36fb080bb8-{Aws.REGION}-{Aws.ACCOUNT_ID}']
        appstream_homefolder_bucket_string = f'appstream2-36fb080bb8-{Aws.REGION}-{Aws.ACCOUNT_ID}'
        
        s3_event_config_custom_sdk_policy = cr.AwsCustomResourcePolicy.from_statements(statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['s3:PutBucketNotification'],
                resources=appstream_homefolder_bucket_array
            )
        ])

        s3_event_config_custom_sdk_param = cr.AwsSdkCall(
            action='putBucketNotificationConfiguration',
            service='S3',
            physical_resource_id=cr.PhysicalResourceId.of(id='s3EventNotification'),
            parameters={
                "Bucket": appstream_homefolder_bucket_string,
                "NotificationConfiguration": {
                    "LambdaFunctionConfigurations": [
                        {
                          "Id": "string",
                          "LambdaFunctionArn":  f"{data_sandbox_lambda.function_arn}",
                          "Events": ["s3:ObjectCreated:*"],
                          "Filter": {
                            "Key": {
                              "FilterRules": [
                                {
                                  "Name": "suffix",
                                  "Value": ".json"
                                }
                              ]
                            }
                          }
                        }
                      ]
                }
            }
        )
        

        s3_event_config_custom_sdk_delete_param = cr.AwsSdkCall(
            action='putBucketNotificationConfiguration',
            service='S3',
            physical_resource_id=cr.PhysicalResourceId.of(id='s3EventNotification'),
            parameters={
                "Bucket": appstream_homefolder_bucket_string,
                "NotificationConfiguration": {}
            }
        )

        s3_event_custom_sdk_trigger = cr.AwsCustomResource(
            self, 'custom-event-sdk',
            on_create=s3_event_config_custom_sdk_param,
            on_update=s3_event_config_custom_sdk_delete_param,
            on_delete=s3_event_config_custom_sdk_delete_param,
            policy=s3_event_config_custom_sdk_policy,
            log_retention=logs.RetentionDays.THREE_MONTHS
        )
        
        #build custom resource to assign IAM role to AppStream fleet
        appstream_fleet_iam_role_assignment_policy = cr.AwsCustomResourcePolicy.from_statements(statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['appstream:UpdateFleet','iam:PassRole'],
                resources=[f'arn:aws:appstream:{Aws.REGION}:{Aws.ACCOUNT_ID}:fleet/{appstream_environment_name}-fleet',f'{self.appstream_role.role_arn}']
            )
        ])

        appstream_fleet_iam_role_assignment_create = cr.AwsSdkCall(
            action='updateFleet',
            service='AppStream',
            physical_resource_id=cr.PhysicalResourceId.of(id='AppStreamFeeltIAMRoleAssignementCreat'),
            parameters={
                "Name": appstream_fleet.name,
                "IamRoleArn": self.appstream_role.role_arn
            }
        )
        

        appstream_fleet_iam_role_assignment_trigger = cr.AwsCustomResource(
            self, 'appstream-iam-role-assignment',
            on_create=appstream_fleet_iam_role_assignment_create,
            policy=appstream_fleet_iam_role_assignment_policy,
            log_retention=logs.RetentionDays.THREE_MONTHS
        )
        
        
        #enable AppStream usage reports
        appstream_usage_reports_policy = cr.AwsCustomResourcePolicy.from_statements(statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['appstream:CreateUsageReportSubscription','appstream:DeleteUsageReportSubscription'],
                resources=['*']
            )
        ])

        appstream_usage_reports_create = cr.AwsSdkCall(
            action='createUsageReportSubscription',
            service='AppStream',
            physical_resource_id=cr.PhysicalResourceId.of(id='AppStreamUsageReports')
        )
        
        

        appstream_usage_reports_trigger = cr.AwsCustomResource(
            self, 'appstream-usage-reports',
            on_create=appstream_usage_reports_create,
            policy=appstream_usage_reports_policy,
            log_retention=logs.RetentionDays.THREE_MONTHS
        )
        
