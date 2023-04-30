#!/usr/bin/python
import argparse
import botocore
import boto3
import datetime

REGION = "us-east-1"

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
    parser.add_argument('--silent', help='If set, only verified permissions are printed', action='store_true', default=False)

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
    else:
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZ" 


def enumerate_permissions(ak, sk, st, services, silent):
    
    session = None
    if st == None:
        session = boto3.Session(
                aws_access_key_id=ak,
                aws_secret_access_key=sk,
                region_name=REGION
        )
    else:
        session = boto3.Session(
                aws_access_key_id=ak,
                aws_secret_access_key=sk,
                aws_session_token=st,
                region_name=REGION
        )

    if services == None:
        services = session.get_available_services()

    #TODO implement catch for user input services that do not exist. Currently it should just crash.
    for service in services:
        client = session.client(service)
        actions = filter(lambda action: not (action.startswith("__") or action.startswith("_")), dir(client))
        params_needed = False
        for action in actions:
            if action.startswith("get_") or action.startswith("list_") or action.startswith("describe_"):
                try:
                    method = getattr(client, action)
                    method()
                except KeyboardInterrupt:
                    exit()
                except botocore.exceptions.ParamValidationError as param_error:
                    parameter_error_list = str(param_error).split("\n")[1:]
                    parameter_dict = dict()
                    params_needed = True
                    for param_error_text in parameter_error_list:
                        param_name = param_error_text[38:-1] 
                        parameter_dict[param_name] = get_parameter(param_name, service) 
                    try:
                        method(**parameter_dict)
                    except KeyboardInterrupt:
                        exit()
                    except botocore.exceptions.ClientError as client_error:
                        prams_needed = False
                        if "AccessDenied" in str(client_error):
                            continue
                        elif "InvalidInput" in str(client_error) or "ValidationError" in str(client_error):
                            if not silent:
                                print(f"[!] Cannot determine correct parameter format for {service}.{action}\n")
                                print(client_error)
                                print("")
                            continue
                    except botocore.exceptions.ParamValidationError as param_validation_error:
                        if not silent:
                            print(f"[!] Cannot determine correct parameters for {service}.{action}\n")
                            print(param_validation_error)
                            print("")
                        continue 
                    except Exception as ie:
                        continue #Might miss some unknown errors. E.g. some endpoint connection errors
                except Exception as oe:
                    continue
                print(f"[+] {service}.{action}")
                if params_needed: 
                    print(f" |--Parameters: {', '.join(parameter_dict.keys())}")
                print("")
                params_needed = False
                


def main():
    args = parse_arguments()
    
    print(BANNER)
    enumerate_permissions(args.access_key, args.secret_key, args.session_token, args.services, args.silent)


if __name__ == '__main__':
    main()
