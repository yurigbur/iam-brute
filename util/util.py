import boto3
import botocore
import os

from enum import Enum

class LVL(Enum):
    SILENT = 1
    WARNING = 2
    DEBUG = 3

CONN_TIMEOUT = 60
READ_TIMEOUT = 60 
REGION = "eu-central-1"
VERBOSE = LVL.SILENT.value


def write_output(level, msg):
    if level.value <= VERBOSE.value:
        print(msg)


def get_client(service, profile, ak, sk, st):

    config = botocore.client.Config(connect_timeout=CONN_TIMEOUT, read_timeout=READ_TIMEOUT, retries={'max_attempts': 1})
    if profile:
        # Workaround via the environment variable as clients without a session do not support profile names as parameters.
        os.environ["AWS_PROFILE"]=profile
        return boto3.client(service, region_name=REGION, config=config)
    elif ak:
        if not st:
            return boto3.client(service, aws_access_key_id=ak, aws_secret_access_key=sk, region_name=REGION, config=config)
        else:
            return boto3.client(service, aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=st, region_name=REGION, config=config)
    else:
        os.environ["AWS_PROFILE"]="default"
        return boto3.client(service, region_name=REGION, config=config)


