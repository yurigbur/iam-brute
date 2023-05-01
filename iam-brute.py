#!/usr/bin/env python

import argparse
import botocore
import boto3
import datetime
import multiprocessing
import re

from multiprocessing import Pool
from itertools import repeat

THREADS = 25
REGION = "us-east-1"
VERBOSE = "warning"

# The following services produce inaccurate results as certain errors are currently not captured.
EXCLUDED_SERVICES = ["alexaforbusiness", "chime", "cloud9", "cloudfront", "cloudtrail", "codecommit", "cognito-idp", "comprehend", "elasticbeanstalk", "fsx", "kinesis", "kinesis-video-signaling", "kms", "license-manager", "logs", "redshift-serverless", "resource-explorer-2", "route53", "sdb", "service-quotas", "sqs", "sso", "transcribe", "transfer", "waf", "waf-regional", "wafv2", "workdocs", "workspaces"]

BANNER = """
  _____            __  __   ____  _____  _    _ _______ ______   _ 
 |_   _|     /\   |  \/  | |  _ \|  __ \| |  | |__   __|  ____| | |
   | |      /  \  | \  / | | |_) | |__) | |  | |  | |  | |__    | |
   | |     / /\ \ | |\/| | |  _ <|  _  /| |  | |  | |  |  __|   | |
  _| |_   / ____ \| |  | | | |_) | | \ \| |__| |  | |  | |____  |_|
 |_____| /_/    \_\_|  |_| |____/|_|  \_\\\\____/   |_|  |______| (_)
 
     .^. .  _    
    /: ||`\/ \~  ,       
  , [   &    / \ y'   
 {v':   `\   / `&~-,  
'y. '    |`   .  ' /   
 \   '  .       , y   
 v .        '     v   
 V  .~.      .~.  V   
 : (  0)    (  0) :   
  i `'`      `'` j     
   i     __    ,j     
    `%`~....~'&         
 <~o' /  \/` \-s,        
  o.~'.  )(  r  .o ,.  
 o',  %``\/``& : 'bF  
d', ,ri.~~-~.ri , +h  
`oso' d`~..~`b 'sos`  
     d`+ II +`b              
     i_:_yi_;_y        ⠀⠀⠀⠀⠀⠀⠀⠀
                                                                   
"""

def parse_arguments():
    parser = argparse.ArgumentParser(description='IAM Brute')

    parser.add_argument('--access-key', help='AWS access key', required=True)
    parser.add_argument('--secret-key', help='AWS secret key', required=True)
    parser.add_argument('--session-token', help='STS session token', default=None)
    parser.add_argument('--services', nargs='+', help='Space-sepearated list of services to enumerate', default=None) 
    parser.add_argument('--verbose', help='Sets the level of information the script prints: "silent" only prints confirmed permissions, "warning" (default) prints parameter parsing errors and "debug" prints all errors', choices=["silent","warning","debug"], default="warning")
    parser.add_argument('--threads', help='Number of threads (Default 25)', type=int, default=25)
    parser.add_argument('--no-banner', help='Hides banner', action="store_true", default=False)

    return parser.parse_args()


def get_parameter(param_name, service):
    # Heuristical approach to choose a type of format that is required based on the parameter name
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


def check_permission(service, action, ak, sk, st):
    client = None
    if st == None:
        client = boto3.client(service, aws_access_key_id=ak, aws_secret_access_key=sk, region_name=REGION)
    else:
        client = boto3.client(service, aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=st, region_name=REGION)

    params_needed = False
    try:
        method = getattr(client, action)
        method()
    except KeyboardInterrupt:
        exit()
    except botocore.exceptions.ParamValidationError as param_error:
        try:
            parameter_error_list = str(param_error).split("\n")[1:]
            parameter_dict = dict()
            params_needed = True
            
            for param_error_text in parameter_error_list:
                param_name = param_error_text[38:-1] 
                parameter_dict[param_name] = get_parameter(param_name, service) 
            
            method(**parameter_dict)
        except KeyboardInterrupt:
            exit()
        except botocore.exceptions.ClientError as client_error:
            if "AccessDenied" in str(client_error) or "UnauthorizedOperation" in str(client_error) or "ForbiddenException" in str(client_error):
                return
            elif "NoSuchBucket" in str(client_error):
                return
            elif re.compile(r"Invalid(Input|Request|ParameterValue)|Validation(Error|Exception)").search(str(client_error)):
                if VERBOSE in ["warning", "debug"]:
                    print(f"[!] Cannot determine correct input for {service}.{action}\n{str(client_error)}\n")
                return
            elif re.compile(r"Invalid.*I(d|D)").search(str(client_error)):
                if VERBOSE in ["warning", "debug"]:
                    print(f"[!] Cannot determine correct ID for {service}.{action}\n{str(client_error)}\n")
                return
            elif re.compile(r"Invalid.*A(rn|RN)").search(str(client_error)):
                if VERBOSE in ["warning", "debug"]:
                    print(f"[!] Cannot determine correct Arn for {service}.{action}\n{str(client_error)}\n")
                return
            elif "BadRequestException" in str(client_error):
                if VERBOSE in ["warning", "debug"]:
                    print(f"[!] Bad request send for {service}.{action}. Parameters likely have invalid format\n{str(client_error)}\n")
                return

        except botocore.exceptions.ParamValidationError as param_validation_error:
            if VERBOSE in ["warning", "debug"]:
                print(f"[!] Cannot determine correct parameter format for {service}.{action}\n{str(param_validation_error)}\n")
            return
        except Exception as ie:
            if VERBOSE == "debug":
                print(f"[!] Unknown error for {service}.{action}\n{str(ie)}\n")
            return
    except Exception as oe:
        if VERBOSE == "debug":
            print(f"[!] Unknown error for {service}.{action}\n{str(oe)}\n")
        return

    params = ("(" + ', '.join(parameter_dict.keys()) + ")") if params_needed else ""
    print(f"[+] {service}.{action}: {params}")


def enumerate_permissions(ak, sk, st, services):
    
    #Check that provided credentials are valid
    if st == None:
        client = boto3.client("sts", aws_access_key_id=ak, aws_secret_access_key=sk, region_name=REGION)
    else:
        client = boto3.client("sts", aws_access_key_id=ak, aws_secret_access_key=sk, aws_session_token=st, region_name=REGION)
    try:
        identity = client.get_caller_identity()
        print(f"[*] Account ID: {identity['Account']}")
        print(f"[*] Principal: {identity['Arn']}")
    except:
        print("[!] Provided credentials are invalid")
        exit()

    # Check if provided services are valid
    all_services = boto3.Session().get_available_services()
    if services == None:
        services = all_services
    if not set(services).issubset(set(all_services)):
        print("[!] Unknown services specified")
        exit()

    # remove excluded services
    services = [x for x in services if x not in EXCLUDED_SERVICES]

    # Generate a list of service and action tuples for all list, get and describe actions
    to_test = []
    for service in services:
        client = boto3.client(service,region_name=REGION)
        actions = filter(lambda action: not (action.startswith("__") or action.startswith("_")), dir(client))
        for action in actions:
            if action.startswith("get_") or action.startswith("list_") or action.startswith("describe_"):
                if not (action == "get_paginator" or action == "get_waiter"):
                    to_test.append((service,action,ak,sk,st))
                
    print(f"[*] Checking {len(to_test)} permissions\n")

    thread_pool = Pool(THREADS)

    try:
        results = thread_pool.starmap(check_permission, to_test)
    except KeyboardInterrupt:
        print("[*] Keyboard Interrupt detected, exiting!")
    finally:
        try:
            thread_pool.close()
            thread_pool.join()
        except:
            print("[!] Threads not shutting down nicely, exiting hard")
    

def main():
    args = parse_arguments()
    global VERBOSE, THREADS
    VERBOSE = args.verbose
    THREADS = args.threads
    
    if not args.no_banner: 
        print(BANNER)
    
    enumerate_permissions(args.access_key, args.secret_key, args.session_token, args.services)


if __name__ == '__main__':
    main()
