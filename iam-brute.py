#!/usr/bin/python
import argparse
import botocore
import boto3

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

    return parser.parse_args()


def enumerate_permissions(ak, sk, st, services):
    
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
            if "get" in action or "list" in action or "describe" in action:
                try:
                    method = getattr(client, action)
                    method()
                except KeyboardInterrupt:
                    exit()
                except botocore.exceptions.ParamValidationError as param_error:
                    parameter_list = str(param_error).split("\n")[1:]
                    parameter_dict = dict()
                    params_needed = True
                    for param in parameter_list:
                        parameter_dict[param[38:-1]] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Some random string for now.
                    try:
                        method(**parameter_dict)
                    except KeyboardInterrupt:
                        exit()
                    except botocore.exceptions.ClientError as client_error:
                        prams_needed = False
                        if "AccessDenied" in str(client_error):
                            continue
                    except botocore.exceptions.ParamValidationError as param_validation_error:
                        #Param validation fails before auth check. Actions that are listed here might still be allowed.
                        print(f"[!] Cannot determine correct parameters for {service}.{action}\n")
                        continue 
                    except:
                        continue #Might miss some unknown errors. E.g. some endpoint connection errors
                except:
                    continue
                print(f"[+] {service}.{action}")
                if params_needed: 
                    print(f" |--Parameters: {', '.join(parameter_dict.keys())}")
                print("")
                params_needed = False
                


def main():
    args = parse_arguments()

    print(BANNER)
    enumerate_permissions(args.access_key, args.secret_key, args.session_token, args.services)


if __name__ == '__main__':
    main()
