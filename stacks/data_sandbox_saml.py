#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import os
from aws_cdk import (
    core,
    aws_iam as iam,
    aws_cloudformation as cfn
)
from aws_cdk.core import Aws


class SamlStack(cfn.NestedStack):
    def __init__(self, scope: core.Construct, id: str, aws_region='', **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        #parameters
        idp_name = self.node.try_get_context("idp_name")
        appstream_environment_name = self.node.try_get_context("appstream_environment_name")

        # # build SAML role - uncomment if using SAML
        Assume_condition_object={"StringEquals": {
                "SAML:aud": "https://signin.aws.amazon.com/saml"}}

        Federated_Prin_with_conditionb_obj = iam.FederatedPrincipal(f'arn:aws:iam::{Aws.ACCOUNT_ID}:saml-provider/{idp_name}', Assume_condition_object,'sts:AssumeRoleWithSAML')
        
        saml_inline_policies = {
                    'AllowAppStreamAccessSAML': iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                effect=iam.Effect.ALLOW,
                                actions=['appstream:Stream'],
                                resources=[f'arn:aws:appstream:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/{appstream_environment_name}-stack']
                            )
                        ]
                    )
                }
                
        saml_role=iam.Role(
            self,
            id='saml-role',
            description='Role for SAML',
            role_name=f'{Aws.REGION}-appstream-saml-role',
            max_session_duration=core.Duration.seconds(3600),
            assumed_by=Federated_Prin_with_conditionb_obj,
            inline_policies = saml_inline_policies
            )
        