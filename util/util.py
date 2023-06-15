import boto3
import botocore
import os
import datetime
import json

from enum import Enum

class LVL(Enum):
    SILENT = 1
    WARNING = 2
    DEBUG = 3

CONN_TIMEOUT = 60
READ_TIMEOUT = 60 
REGION = "us-east-1"
#TODO update dynamic generation in the future. Regenerate with e.g. 
# curl -s https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/endpoints.json | grep -B1 desc|grep {|cut -d \" -f2
AVAILABLE_REGIONS = ["af-south-1", "ap-east-1", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3", "ap-south-1", "ap-south-2", "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-4", "ca-central-1", "eu-central-1", "eu-central-2", "eu-north-1", "eu-south-1", "eu-south-2", "eu-west-1", "eu-west-2", "eu-west-3", "me-central-1", "me-south-1", "sa-east-1", "us-east-1", "us-east-2", "us-west-1", "us-west-2", "cn-north-1", "cn-northwest-1", "us-gov-east-1", "us-gov-west-1", "us-iso-east-1", "us-iso-west-1", "us-isob-east-1"] 
VERBOSE = LVL.SILENT


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


def get_static_param(param_name, service):
    #Static rules
    if "arn" in param_name.lower():
        if "policy" in param_name.lower():
            return "arn:aws:iam::aws:policy/foobar"
        elif "role" in param_name.lower():
            return "arn:aws:iam::000000000000:role/foobar"
        else:
            return f"arn:aws:{service}:{REGION}:000000000000:foobar"
    if "version" in param_name.lower():
        return "v123456789"
    if param_name.lower().endswith("list") or param_name.lower().endswith("ids"):
        return ["foo","bar"]
    if "JobId" in param_name:
        return "deadbeef-dead-beef-dead-beefdeadbeef"
    if "time" in param_name.lower():
        return datetime.datetime.now()
    if "MaxResults" in param_name or "MaxEntries" in param_name:
        return 42
    if param_name.lower().endswith("count"):
        return 42
    if "InstanceId" in param_name:
        return "i-deadbeefdeadbeefd"
    if "repositoryName" in param_name:
        return f"11122233334444.dkr.ecr.{REGION}.amazonaws.com/foobar"
    else:
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZ" 
    

def get_context_params(param_name, service, context):
    result = None
    level = []
    if "services" in context and service in list(context['services'].keys()): 
        level = context['services'][service]
    else:
        level = context

    for key in list(level.keys()):
            if param_name.lower() == key.lower():
                result = level[key]
    
    return result if result else []


def write_output_file(file, format, results, services):

    if format == "json":
        with open(file, "w") as fd:
            json.dump(consolidate_json_output(results, services), fd, indent=4)
    
    if format == "text":
        lines = list()
        for res in results:
            params = ("(" + ', '.join(res['parameters'].keys()) + ")") if res['parameters'] else ""
            line = f"{res['service']}.{res['action']}: {params}\n"
            lines.append(line)
        
        lines.sort()
        with open(file, "w") as fd:
            fd.writelines(lines)


def consolidate_json_output(results, services):
    cons_results = dict()
    for service in services:
        cons_results[service]= dict()
        for res in results:
            if res['service'] == service:
                if res["action"] in cons_results[service].keys():
                    cons_results[service][res["action"]].append(res["parameters"])
                else:
                    cons_results[service][res["action"]] = [res["parameters"]] if res["parameters"] else None   
                
    return cons_results
