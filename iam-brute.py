#!/usr/bin/env python

import argparse
import botocore
import boto3
import time
#import re
#import random
import json

from multiprocessing import Manager, Process

from enumeration_worker import worker
from util import util

THREADS = 25

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
     i_:_yi_;_y       
                                                                   
"""

def parse_arguments():
    parser = argparse.ArgumentParser(description='IAM Brute')

    parser.add_argument('--profile', help='AWS CLI profile, using a profile explicitly will ignore --access-key and --secret-key', default=None)
    parser.add_argument('--access-key', help='AWS access key', default=None)
    parser.add_argument('--secret-key', help='AWS secret key', default=None)
    parser.add_argument('--session-token', help='STS session token', default=None)
    parser.add_argument('--region', help='Region to test permissions against (Default us-east-1)', default="us-east-1")
    parser.add_argument('--services', nargs='+', help='Space-sepearated list of services to enumerate', default=None) 
    parser.add_argument('--exclude-services', nargs='+', help='Space-sepearated list of excluded services (overwrites --services)', default=None) 
    parser.add_argument('--verbose', help='Sets the level of information the script prints: "SILENT" (default) only prints confirmed permissions, "WARNING" prints parameter errors and "DEBUG" prints infos for all requests', choices=["SILENT","WARNING","DEBUG"], default="SILENT")    
    parser.add_argument('--threads', help='Number of threads (Default 25)', type=int, default=25)
    parser.add_argument('--no-banner', help='Hides banner', action="store_true", default=False)
    parser.add_argument('--context', help='relativ path to a context file that is used to obtain parameters for the requests', default=None)
    parser.add_argument('--output', help='relativ path to the output file', default=None)
    parser.add_argument('--output-format', help='format of the output', choices=["json", "text"], default="text")

    args = parser.parse_args()

    if args.profile and args.access_key:
        util.write_output(util.LVL.SILENT,f"[!] Access key and profile used")
        exit()
    if args.access_key and not args.secret_key:
        util.write_output(util.LVL.SILENT,f"[!] Access key used without secret key")
        exit()
    if args.secret_key and not args.access_key:
        util.write_output(util.LVL.SILENT,f"[!] Secret key provided without access key")
        exit()
    if args.session_token and not args.access_key and not args.secret_key:
        util.write_output(util.LVL.SILENT,f"[!] Session token without access key and secret key provided")
        exit()
    if args.region not in util.AVAILABLE_REGIONS:
        util.write_output(util.LVL.SILENT,f"[!] Region identifier not a valid. Choose one of the following:\n{', '.join(util.AVAILABLE_REGIONS)}")
        exit()

    return args


def generate_inital_queue(queue, profile, ak, sk, st, services):

    # Generate a list of service and action tuples for all list, get and describe actions
    count = 0
    for service in services:
        client = boto3.client(service,region_name=util.REGION)
        actions = filter(lambda action: not (action.startswith("__") or action.startswith("_")), dir(client))
        for action in actions:
            if action.startswith("get_") or action.startswith("list_") or action.startswith("describe_"):
                if not (action == "get_paginator" or action == "get_waiter"):
                    count += 1
                    queue.put({
                        "service":service,
                        "action":action,
                        "profile":profile,
                        "ak":ak,
                        "sk":sk,
                        "st":st,
                        "parameters":None
                    })

    print(f"[*] Checking {count} permissions\n")


def enumerate_permissions(profile, ak, sk, st, services, context, threads):

    with Manager() as manager:
        queue = manager.Queue()
        results = manager.Queue()

        generate_inital_queue(queue, profile, ak, sk, st, services)

        try:
            processes = [Process(target=worker.run, args=(queue,results,context)) for _ in range(threads)]

            for process in processes:
                process.start()

            while True:
                if queue.empty():
                    break

            for process in processes:
                process.kill()

        except KeyboardInterrupt:
            print("[*] Keyboard Interrupt detected")
            for p in processes:
                p.kill()

        results_list = list()
        while True:
            if results.empty():
                break
            results_list.append(results.get())
            
        return results_list
    

def main():
    args = parse_arguments()
    util.VERBOSE = util.LVL[args.verbose]
    util.REGION = args.region

    if not args.no_banner: 
        print(BANNER)

    # Load context if provided
    context = None
    if args.context:
        with open(args.context, "r") as fd:
            context = json.load(fd)
        
    services = boto3.Session().get_available_services()
    if args.services:
        if not set(args.services).issubset(set(services)):
            print("[!] Unknown services specified")
            exit()
        services = args.services
    if args.exclude_services:
        services = [x for x in services if x not in args.exclude_services]

    #Check that provided credentials are valid
    client = util.get_client('sts', args.profile, args.access_key, args.secret_key, args.session_token)
    try:
        identity = client.get_caller_identity()
        print(f"[*] Account ID: {identity['Account']}")
        print(f"[*] Principal: {identity['Arn']}")
    except:
        print("[!] Provided credentials are invalid")
        exit()
    
    results_list = enumerate_permissions(
        args.profile, 
        args.access_key, 
        args.secret_key, 
        args.session_token, 
        services, 
        context,
        args.threads)
    
    if args.output:
        util.write_output_file(args.output, args.output_format, results_list, services)


if __name__ == '__main__':
    main()

