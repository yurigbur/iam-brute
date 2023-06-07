import botocore
import boto3
import datetime
import time
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
                )

                if check:
                    results.put({
                        "service":val['service'],
                        "action":val['action'],
                        "parameters":val['action']
                    })
                
            except EOFError:
                break

        print(f"{val['service']}:{val['action']}")


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
            return f"arn:aws:{service}:{util.REGION}:000000000000:foobar"
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
        return f"11122233334444.dkr.ecr.{util.REGION}.amazonaws.com/foobar"
    else:
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZ" 
    

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
            params_needed = False
            method = getattr(client, val['action'])
            response = method()
        
        util.write_output(util.LVL.DEBUG, str(response))
    
    except botocore.exceptions.ParamValidationError as param_error:
        
        # if param validation error occurs without parameters, the action requires some. 
        # The error message is used to infer the needed parameters.
        # If the error occurs with parameters the used parameters (context or static) are wrong.
        if val['parameters']:
            util.write_output(util.LVL.WARNING,f"[!] Cannot determine correct parameter format for {val['service']}.{val['action']}\n{str(param_error)}\n")
            return False
        else:
            parameter_error_list = str(param_error).split("\n")[1:]
            parameter_dict = dict()
            params_needed = True

            # TODO add support for multiple values in the context
            for param_error_text in parameter_error_list:
                param_name = param_error_text[38:-1] 
                parameter_dict[param_name] = get_parameter(param_name, val['service'], context) 

            val['parameters'] = parameter_dict
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
    

    params = ("(" + ', '.join(parameter_dict.keys()) + ")") if params_needed else ""
    util.write_output(util.LVL.SILENT,f"[+] {val['service']}.{val['action']}: {params}")
    return True
