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
    custom_resources as cr
)
from aws_cdk.core import Aws

current_dir = os.path.dirname(__file__)


class AppstreamStartFleetStack(cfn.NestedStack):
    def __init__(self, scope: core.Construct, id: str, aws_region='', appstreamrole='', **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        #parameters
        appstream_environment_name = self.node.try_get_context("appstream_environment_name")
        
        #build custom resource to start appstream fleet
        appstream_fleet_start_policy = cr.AwsCustomResourcePolicy.from_statements(statements=[
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=['appstream:StopFleet','appstream:StartFleet'],
                resources=[f'arn:aws:appstream:{Aws.REGION}:{Aws.ACCOUNT_ID}:fleet/{appstream_environment_name}-fleet',f'{appstreamrole.role_arn}']
            )
        ])

        appstream_fleet_start_create = cr.AwsSdkCall(
            action='startFleet',
            service='AppStream',
            physical_resource_id=cr.PhysicalResourceId.of(id='AppStreamFeeltIAMRoleAssignementCreate'),
            parameters={
                "Name": f'{appstream_environment_name}-fleet'
            }
        )
        

        appstream_fleet_start_trigger = cr.AwsCustomResource(
            self, 'appstream-start-fleet',
            on_create=appstream_fleet_start_create,
            policy=appstream_fleet_start_policy,
            log_retention=logs.RetentionDays.THREE_MONTHS
        )