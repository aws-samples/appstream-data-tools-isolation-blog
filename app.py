#// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#// SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
import os
import logging
import boto3

# from typing import Type
from aws_cdk import core
from stacks.data_sandbox_vpc import VPCStack
from stacks.data_sandbox_s3 import S3Stack
from stacks.data_sandbox_service_roles import AppstreamServiceRolesStack
from stacks.data_sandbox_appstream import AppstreamStack
from stacks.data_sandbox_start_fleet import AppstreamStartFleetStack
from stacks.data_sandbox_notebook import NotebookStack
from stacks.data_sandbox_saml import SamlStack

env = core.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])

logger = logging.getLogger()

logger.setLevel(logging.DEBUG)

app = core.App()

DataSandbox = core.Stack(app, 'DataSandbox', env=env)

vpcstack = VPCStack(DataSandbox, 'vpc-stack')
s3stack = S3Stack(DataSandbox, 's3-stack')
appstreamservicerolesstack = AppstreamServiceRolesStack(DataSandbox, "appstream-service-roles-stack")
appstreamstack = AppstreamStack(DataSandbox, 'appstream-stack', vpc=vpcstack.vpc, s3stack=s3stack.data_sandbox_bucket)
appstreamstartfleetstack = AppstreamStartFleetStack(DataSandbox, 'appstream-start-fleet-stack', appstreamrole=appstreamstack.appstream_role)
notebookstack = NotebookStack(DataSandbox, 'notebook-stack', vpc=vpcstack.vpc, s3stack=s3stack.data_sandbox_bucket, appstreamsg=appstreamstack.appstream_security_group)
samlstack = SamlStack(DataSandbox, 'saml-stack')