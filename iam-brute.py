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
    # OLD WAY:
    # tmp_loader = botocore.loaders.Loader()
    # services = tmp_loader.list_available_services("service-2")
    # Not entirely sure what this service-2 exactly is. there are also other options like paginators-1 and waiters-2.json.
    # Another option could be to get the services from botocore/data/endpoints.json but it seems to contain less services.
    # Example: cat endpoints.json | jq -r '.partitions[].services | keys | .[]' | sort -u
    
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
        for action in actions:
            if "get" in action or "list" in action or "describe" in action:
                try:
                    method = getattr(client, action)
                    method()
                except KeyboardInterrupt:
                    exit()
                except:
                    continue
                print(f"{service}.{action}")
                


def main():
    args = parse_arguments()

    print(BANNER)
    enumerate_permissions(args.access_key, args.secret_key, args.session_token, args.services)


if __name__ == '__main__':
    main()
