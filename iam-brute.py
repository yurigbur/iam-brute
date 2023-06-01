#!/usr/bin/env python

import os
import argparse
import botocore
import boto3
import datetime
import multiprocessing
import re
import requests
import random
import json

from multiprocessing import Pool
from itertools import repeat
from enum import Enum

class LVL(Enum):
    SILENT = 1
    WARNING = 2
    DEBUG = 3

THREADS = 25
REGION = "us-east-1"
VERBOSE = LVL.WARNING.value
CONN_TIMEOUT = 60
READ_TIMEOUT = 60 

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

    parser.add_argument('--profile', help='AWS CLI profile, using a profile explicitly will ignore --access-key and --secret-key', default=None)
    parser.add_argument('--access-key', help='AWS access key', default=None)
    parser.add_argument('--secret-key', help='AWS secret key', default=None)
    parser.add_argument('--session-token', help='STS session token', default=None)
    parser.add_argument('--services', nargs='+', help='Space-sepearated list of services to enumerate', default=None) 
    parser.add_argument('--exclude-services', nargs='+', help='Space-sepearated list of excluded services (overwrites --services)', default=None) 
    parser.add_argument('--verbose', help='Sets the level of information the script prints: "silent" only prints confirmed permissions, "warning" (default) prints parameter parsing errors and "debug" prints all errors', choices=["SILENT","WARNING","DEBUG"], default="WARNING")
    parser.add_argument('--threads', help='Number of threads (Default 25)', type=int, default=25)
    parser.add_argument('--no-banner', help='Hides banner', action="store_true", default=False)
    parser.add_argument('--context', help='Path to a context file that is used to obtain parameters for the requests', default=None)

    args = parser.parse_args()

    if args.profile and args.access_key:
        print("[!] Access key and profile used")
        exit()
    if args.access_key and not args.secret_key:
        print("[!] Access key used without secret key")
        exit()
    if args.secret_key and not args.access_key:
        print("[!] Secret key provided without access key")
        exit()
    if args.session_token and not args.access_key and not args.secret_key:
        print("[!] Session token without access key and secret key provided")
        exit()

    return args


def get_context_param(service, param_name, context):
    result = None
    level = []
    if "services" in context and service in list(context['services'].keys()): 
        level = context['services'][service]
    else:
        level = context

    for key in list(level.keys()):
            if param_name.lower() == key.lower():
                result = level[key]
    
    return result



def get_parameter(param_name, service, context):
    # Heuristical approach to choose a type of format that is required based on the parameter name
    
    if context:
        context_param = get_context_param(service, param_name, context)
        if context_param:
            return context_param
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


def evaluate_client_error(service, action, error_response):
    if error_response['ResponseMetadata']['HTTPStatusCode'] in [403, 401]:
        write_output(LVL.DEBUG,f"[*] Access denied for {service}.{action}\n{str(error_response)}\n")
        return True

    if error_response['ResponseMetadata']['HTTPStatusCode'] in [400,422,500]:
        write_output(LVL.WARNING,f"[!] Cannot determine valid parameters for {service}.{action}\n{str(error_response)}\n")
        return True
        
    # special case for services that check certain parameters before the permissions are checked
    if service in ["s3", "chime", "cloudfront", "route53", "workdocs"] and error_response['ResponseMetadata']['HTTPStatusCode'] == 404:
        write_output(LVL.WARNING,f"[!] Resource not found or not allowed with provided dummy parameter(s) {service}.{action}\n{str(error_response)}\n")
        return True

    if error_response['Error']['Code'] == "DeprecatedAPIException":
        write_output(LVL.WARNING,f"[!] Deprecated API Endpoint for {service}.{action}\n{str(error_response)}\n")
        return True

    # For some services boto3 throws access denied exceptions on a 400 status code (LOL).
    if error_response['ResponseMetadata']['HTTPStatusCode'] == 400 and error_response['Error']['Code'] == "AccessDeniedException":
        write_output(LVL.DEBUG,f"[*] Access denied for {service}.{action}\n{str(error_response)}\n")
        return True

    return False


def check_permission_with_param(service, action, parameters, client):
    try:
        method = getattr(client, action)
        response = method(**parameters)

        write_output(LVL.DEBUG,f"[*] Response for {service}.{action}\n{str(response)}\n")

    except botocore.exceptions.ClientError as client_error:
        if evaluate_client_error(service, action, client_error.response):
            return True

        write_output(LVL.DEBUG,f"[*] ClientError for {service}.{action}\n{str(client_error.response)}\n")

    except botocore.exceptions.ParamValidationError as param_validation_error:
        write_output(LVL.WARNING,f"[!] Cannot determine correct parameter format for {service}.{action}\n{str(param_validation_error)}\n")
        return True

    except botocore.exceptions.NoAuthTokenError as no_auth_token:
        write_output(LVL.DEBUG,f"[*] No authentication token for {service}.{action}\n{str(no_auth_token)}\n")
        return True

    except botocore.exceptions.EndpointConnectionError as endpoint_error:
        write_output(LVL.WARNING,f"[*] Endpoint connection error for: {service}.{action}\n{str(endpoint_error)}\n")
        return True

    except KeyError as key_error:
        #remove silent output when clarified what happens with the special key errors.
        write_output(LVL.SILENT,f"[!] Cannot determine correct parameter format for {service}.{action}\n{str(key_error)}\n")
        return True

    except botocore.exceptions.EndpointResolutionError as endpoint_resolution_error:
        write_output(LVL.WARNING,f"[!] Cannot determine correct parameter for {service}.{action}\n{str(endpoint_resolution_error)}\n")
        return True

    return False


def check_permission(service, action, profile, ak, sk, st, context):

    client = get_client(service, profile, ak, sk, st)
    params_needed = False
    
    try:
        method = getattr(client, action)
        response = method()
        
        write_output(LVL.DEBUG, str(response))
    
    except botocore.exceptions.ParamValidationError as param_error:
        parameter_error_list = str(param_error).split("\n")[1:]
        parameter_dict = dict()
        params_needed = True
            
        for param_error_text in parameter_error_list:
            param_name = param_error_text[38:-1] 
            parameter_dict[param_name] = get_parameter(param_name, service, context) 
        
        if check_permission_with_param(service, action, parameter_dict, client):
            return
        
    except botocore.exceptions.ClientError as client_error:
        if evaluate_client_error(service, action, client_error.response):
            return
        
        write_ouput(LVL.DEBUG,f"[*] ClientError for {service}.{action}\n{str(client_error.response)}\n")

    except botocore.exceptions.NoAuthTokenError as no_auth_token:
        write_output(LVL.DEBUG,f"[*] No authentication token for {service}.{action}\n{str(no_auth_token)}\n")
        return

    except botocore.exceptions.EndpointConnectionError as endpoint_error:
        write_output(LVL.WARNING,f"[*] Endpoint connection error for: {service}.{action}\n{str(endpoint_error)}\n")
        return

    #TODO extract missing parmaters from key error and re-do check similar to ParamValidationError
    except KeyError as key_error:
        #remove error output for silent after error is resolved
        write_output(LVL.SILENT,f"[!] Cannot determine correct parameter format for {service}.{action}\n{str(key_error)}\n")
        return
    

    params = ("(" + ', '.join(parameter_dict.keys()) + ")") if params_needed else ""
    write_output(LVL.SILENT,f"[+] {service}.{action}: {params}")
    return


def enumerate_permissions(profile, ak, sk, st, services, context):
    
    #Check that provided credentials are valid
    client = get_client('sts', profile, ak, sk, st)
    try:
        identity = client.get_caller_identity()
        print(f"[*] Account ID: {identity['Account']}")
        print(f"[*] Principal: {identity['Arn']}")
    except:
        print("[!] Provided credentials are invalid")
        exit()

    # Generate a list of service and action tuples for all list, get and describe actions
    to_test = []
    for service in services:
        client = boto3.client(service,region_name=REGION)
        actions = filter(lambda action: not (action.startswith("__") or action.startswith("_")), dir(client))
        for action in actions:
            if action.startswith("get_") or action.startswith("list_") or action.startswith("describe_"):
                if not (action == "get_paginator" or action == "get_waiter"):
                    to_test.append((service,action,profile,ak,sk,st,context))
                
    print(f"[*] Checking {len(to_test)} permissions\n")


    try:
        thread_pool = Pool(THREADS)
        results = thread_pool.starmap(check_permission, to_test)
    except KeyboardInterrupt:
        print("[*] Keyboard Interrupt detected")
        try:
            print("[*] Trying to shutdown threads. Press Ctrl+C again to exit hard")
            thread_pool.close()
            thread_pool.join()
        except KeyboardInterrupt:
            print("[!] Threads not shutting down nicely, exiting hard!")
            exit()
        
    #TODO find out why this happens
    except multiprocessing.pool.MaybeEncodingError as encoding_error:
        write_output(LVL.SILENT,f"[!] Weird internal encoding error while shutting down threads\n{str(encoding_error)}\n")
    
    try:
        thread_pool.close()
        thread_pool.join()
    except:
        exit()
    

def main():
    args = parse_arguments()
    global VERBOSE, THREADS
    VERBOSE = LVL[args.verbose]
    THREADS = args.threads

    context = None
    if args.context:
        with open(args.context, "r") as fd:
            context = json.load(fd)

    if not args.no_banner: 
        print(BANNER)
        
    services = boto3.Session().get_available_services()
    if args.services:
        if not set(args.services).issubset(set(services)):
            print("[!] Unknown services specified")
            exit()
        services = args.services
    if args.exclude_services:
        services = [x for x in services if x not in args.exclude_services]
    
    enumerate_permissions(args.profile, args.access_key, args.secret_key, args.session_token, services, context)


if __name__ == '__main__':
    main()

