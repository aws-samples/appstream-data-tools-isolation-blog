#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

import os
import json
from aws_cdk import (
    core,
    aws_ssm as ssm,
    aws_s3_deployment as s3_deployment,
    aws_s3 as s3,
    aws_cloudformation as cfn
)
from aws_cdk.core import Aws

current_dir = os.path.dirname(__file__)


class S3Stack(cfn.NestedStack):

    def __init__(self, scope: core.Construct, id: str, aws_region='', **kwargs) -> None:
        super().__init__(scope, id, **kwargs)


        # Build S3 bucket
        self.data_sandbox_bucket = s3.Bucket(self, 'DataSandboxBucket',
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Upload appstream scripts

        deploy_appstream_scripts = s3_deployment.BucketDeployment(
            self, 'AppstreamScriptsDeployment',
            sources=[s3_deployment.Source.asset(os.path.join(current_dir, '../appstream_scripts/'))],
            destination_bucket=self.data_sandbox_bucket,
            destination_key_prefix='appstream-scripts'
        )
        
        # build ssm parameters
        ssm.StringParameter(self, 'BucketParam',
            parameter_name='/s3/datasandboxbucket',
            string_value=json.dumps({
                "bucket-name": [f'{self.data_sandbox_bucket.bucket_name}']
            }))