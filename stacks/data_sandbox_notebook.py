#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    aws_ec2 as ec2,
    core,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_kms as kms,
    aws_cloudformation as cfn
)
from aws_cdk.core import Aws

class NotebookStack(cfn.NestedStack):
    def __init__(self, scope: core.Construct, id: str, aws_region='', vpc='', s3stack='', appstreamsg='', **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        # build sagemaker notebook

        # Create KMS Key to be associated with Sagemaker Notebook
        notebook_kms = kms.Key(
            self,
            id='notebook-kms-key',
            alias='notebook-kms',
            removal_policy=core.RemovalPolicy.RETAIN,
            enabled=True,
            enable_key_rotation=True,
            policy=iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        effect=iam.Effect.ALLOW,
                        actions=[
                        "kms:Encrypt",
                        "kms:Decrypt",
                        "kms:ReEncrypt",
                        "kms:GenerateDataKey",
                        "kms:DescribeKey"
                        ],
                        resources=['*'],
                        principals=[
                            iam.ArnPrincipal(f"arn:aws:iam::{Aws.ACCOUNT_ID}:root")
                        ]
                    )
                ]
            )
        )

        # build security group
        self.notebook_security_group = ec2.SecurityGroup(
            self, 'NotebookecurityGroup',
            vpc=vpc,
            security_group_name='notebook-sg'
        )

        notebook_security_group_ingress_rule = self.notebook_security_group.add_ingress_rule(
            peer=appstreamsg,
            connection=ec2.Port.tcp(443),
            description='Allow 443 ingress for Appstream instances'
        )

        # Create role for steward sagemaker notebook
        notebook_role = iam.Role(
            self, 'notebook_role',
            description='Notebook Role',
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com')
        )
        
        # Grant the notebook role access to the KMS key
        notebook_kms.grant_encrypt_decrypt(notebook_role)
        
        self.notebook_instance = sagemaker.CfnNotebookInstance(self,
              id='Data-Sandbox-Notebook',
              instance_type='ml.t3.medium',
              role_arn=notebook_role.role_arn,
              notebook_instance_name='Data-Sandbox-Notebook',
              kms_key_id=notebook_kms.key_arn,
              root_access='Disabled',
              direct_internet_access='Disabled',
              subnet_id=vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids[0],
              security_group_ids=[self.notebook_security_group.security_group_id],
              volume_size_in_gb=20
              )