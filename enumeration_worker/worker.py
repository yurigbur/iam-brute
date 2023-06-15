import botocore
import boto3
#import datetime
#import time
import itertools
#import json
#import re

from util import util

def run(queue, results, context):
    while True:
        if queue.empty():
            break
        else:
            try:
                val = queue.get()
                #print(val)

                client = util.get_client(
                    val['service'],
                    val['profile'],
                    val['ak'],
                    val['sk'],
                    val['st']
                    )

                check = check_permission(
                    val, 
                    client,
                    context,
                    queue
                )

                if check:
                    results.put({
                        "service":val['service'],
                        "action":val['action'],
                        "parameters":val['parameters']
                    })
                
            except EOFError:
                break


def get_parameters(param_names, service, context):

    all_params = list()
    for p in param_names:
        tmp_params = list()
        if context:
            tmp_params = tmp_params + util.get_context_params(p, service, context)
        tmp_params.append(util.get_static_param(p, service))
        #print(tmp_params)
        all_params.append(tmp_params)
    
    
    all_combs = list(itertools.product(*all_params))
    all_combs_as_dicts = []
    for c in all_combs:
        tmp_dict = dict()
        for i in range(len(param_names)):
            tmp_dict[param_names[i]] = c[i]
        all_combs_as_dicts.append(tmp_dict)

    return all_combs_as_dicts

    
def evaluate_client_error(service, action, error_response):
    if error_response['ResponseMetadata']['HTTPStatusCode'] in [403, 401]:
        util.write_output(util.LVL.DEBUG,f"[*] Access denied for {service}.{action}\n{str(error_response)}\n")
        return True

    if error_response['ResponseMetadata']['HTTPStatusCode'] in [400,422,500]:
        util.write_output(util.LVL.WARNING,f"[!] Cannot determine valid parameters for {service}.{action}\n{str(error_response)}\n")
        return True
        
    # special case for services that check certain parameters before the permissions are checked
    if service in ["s3", "chime", "cloudfront", "route53", "workdocs"] and error_response['ResponseMetadata']['HTTPStatusCode'] == 404:
        util.write_output(util.LVL.WARNING,f"[!] Resource not found or not allowed with provided dummy parameter(s) {service}.{action}\n{str(error_response)}\n")
        return True

    if error_response['Error']['Code'] == "DeprecatedAPIException":
        util.write_output(util.LVL.WARNING,f"[!] Deprecated API Endpoint for {service}.{action}\n{str(error_response)}\n")
        return True

    # For some services boto3 throws access denied exceptions on a 400 status code (LOL).
    if error_response['ResponseMetadata']['HTTPStatusCode'] == 400 and error_response['Error']['Code'] == "AccessDeniedException":
        util.write_output(util.LVL.DEBUG,f"[*] Access denied for {service}.{action}\n{str(error_response)}\n")
        return True

    return False



def check_permission(val, client, context, queue):
    
    try:
        response = None
        if val['parameters']:
            method = getattr(client, val['action'])
            response = method(**val['parameters'])

        else:
            method = getattr(client, val['action'])
            response = method()
        
        util.write_output(util.LVL.DEBUG, str(response))
    
    except botocore.exceptions.ParamValidationError as param_error:
        
        # if param validation error occurs without parameters, the action requires some. 
        # The error message is used to infer the needed parameters.
        # If the error occurs with parameters the used parameters (context or static) are wrong.

        if val['parameters']:
            util.write_output(util.LVL.WARNING,f"[!] Cannot determine correct parameter format for {val['service']}.{val['action']}\n{str(param_error)}\n")
        else:
            parameter_error_list = str(param_error).split("\n")[1:]
            parameter_names = list()

            for param_error_text in parameter_error_list:
                parameter_names.append(param_error_text[38:-1])
                
            parameter_list = get_parameters(parameter_names, val['service'], context) 
            
            for p in parameter_list:
                val['parameters'] = p
                queue.put(val)

        return False
        
    except botocore.exceptions.ClientError as client_error:
        if evaluate_client_error(val['service'], val['action'], client_error.response):
            return False
        
        util.write_output(util.LVL.DEBUG,f"[*] ClientError for {val['service']}.{val['action']}\n{str(client_error.response)}\n")

    except botocore.exceptions.NoAuthTokenError as no_auth_token:
        util.write_output(util.LVL.DEBUG,f"[*] No authentication token for {val['service']}.{val['action']}\n{str(no_auth_token)}\n")
        return False

    except botocore.exceptions.EndpointConnectionError as endpoint_error:
        util.write_output(util.LVL.WARNING,f"[*] Endpoint connection error for: {val['service']}.{val['action']}\n{str(endpoint_error)}\n")
        return False
    
    except botocore.exceptions.EndpointResolutionError as endpoint_resolution_error:
        util.write_output(util.LVL.WARNING,f"[!] Cannot determine correct parameter for {val['service']}.{val['action']}\n{str(endpoint_resolution_error)}\n")
        return False

    #TODO extract missing parmaters from key error and re-do check similar to ParamValidationError
    except KeyError as key_error:
        #remove error output for silent after error is resolved
        util.write_output(util.LVL.SILENT,f"[!] Cannot determine correct parameter format for {val['service']}.{val['action']}\n{str(key_error)}\n")
        return False

    params = ("(" + ', '.join(val['parameters'].keys()) + ")") if val['parameters'] else ""
    util.write_output(util.LVL.SILENT,f"[+] {val['service']}.{val['action']}: {params}")
    return True