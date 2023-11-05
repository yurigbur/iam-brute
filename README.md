# I am Brute!
The idea of this enumeration script is to derive available AWS APIs directly from the boto3 library. As this library is (currently) nicely maintained and up to date with the AWS API, this removes the necessity to re-generate and maintain a list of endpoints that are checked. As far as no fundamental things are changed in boto3 or AWS, this script will always be up to date.

Currently, only get, list and describe permissions are checked to avoid accidentially manipulating resources. The dynamic parameter generation currently only supports a few parameters that allow arbitrary input or are covered by the basic heuristical dummy parameter generation. For parameters that expect unknown formats, the parameter validation will fail. If this is the case, no access rights can be checked. The context feature can be used to add known parameters. See usage instructions for how to use the context feature.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
The tool can be used with user access keys or with temporary access keys for roles as well as with AWS CLI profiles
```bash
python3 iam-brute.py --access-key AKIA... --secret-key ...
python3 iam-brute.py --access-key ASIA... --secret-key ... --session-token ey...
python3 iam-brute.py --profile my-profile
```

Refer to the help menu for more options
```bash
$ python3 iam-brute.py -h                                                                                                 
usage: iam-brute.py [-h] [--profile PROFILE] [--access-key ACCESS_KEY] [--secret-key SECRET_KEY] [--session-token SESSION_TOKEN] [--region REGION]
                    [--services SERVICES [SERVICES ...]] [--exclude-services EXCLUDE_SERVICES [EXCLUDE_SERVICES ...]] [--verbose {SILENT,WARNING,DEBUG}]
                    [--threads THREADS] [--no-banner] [--context CONTEXT] [--output OUTPUT] [--output-format {json,text}]

IAM Brute

options:
  -h, --help            show this help message and exit
  --profile PROFILE     AWS CLI profile, using a profile explicitly will ignore --access-key and --secret-key
  --access-key ACCESS_KEY
                        AWS access key
  --secret-key SECRET_KEY
                        AWS secret key
  --session-token SESSION_TOKEN
                        STS session token
  --region REGION       Region to test permissions against (Default us-east-1)
  --services SERVICES [SERVICES ...]
                        Space-sepearated list of services to enumerate
  --exclude-services EXCLUDE_SERVICES [EXCLUDE_SERVICES ...]
                        Space-sepearated list of excluded services (overwrites --services)
  --verbose {SILENT,WARNING,DEBUG}
                        Sets the level of information the script prints: "SILENT" (default) only prints confirmed permissions, "WARNING" prints parameter
                        errors and "DEBUG" prints infos for all requests
  --threads THREADS     Number of threads (Default 25)
  --no-banner           Hides banner
  --context CONTEXT     relativ path to a context file that is used to obtain parameters for the requests
  --output OUTPUT       relativ path to the output file
  --output-format {json,text}
                        format of the output

```


### Misleading Outputs
Some permissions always seem to return 200 status codes. If you encounter, one of the following outputs, they might not be very interesting.
```
[+] dynamodb.describe_endpoints: 
[+] elasticbeanstalk.describe_applications: 
[+] elasticbeanstalk.describe_application_versions: 
[+] elasticbeanstalk.describe_environments: 
[+] elasticbeanstalk.describe_events: 
[+] elasticbeanstalk.list_available_solution_stacks: 
[+] elasticbeanstalk.list_platform_versions: 
[+] kinesis-video-archived-media.get_hls_streaming_session_url: 
[+] kinesis-video-archived-media.get_dash_streaming_session_url: 
[+] kinesis-video-archived-media.list_fragments: 
[+] route53.get_checker_ip_ranges: 
[+] route53.get_geo_location: 
[+] route53.list_geo_locations: 
[+] serverlessrepo.list_applications: 
[+] sts.get_caller_identity: 
[+] sts.get_session_token: 
[+] kinesis-video-signaling.get_ice_server_config: (ChannelARN)
```

### Context Support
As AWS permissions can be scoped to certain resources, the script might receive access denied responses for dummy parameters even though the request would succeed with other parameters. With the --context flag a JSON file can be provided that contains valid role names, arns, ids, ... that are than used in the requests. The parameters can be scoped globally or for specific services. Have a look at the `context.json.example` for information on how to format the context file. Service scoped parameters have precedence over gloablly scoped parameters. The dummy parameters will always also be included.

### Output
The live output is generated as the tasks are exeuted and might not be ordered due to the asynchronous processing. The text output can be used to get an ordered version of the live output without additional highlighting. The json output also contains the actual parameters values that were successfull. **If a parameter is present in the result, it does not necessarily mean that it actually is a valid parameter if the permissions are not scoped**.


## Disclaimer
I started writing this tool as I was frustrated with the coverage and maintenance state of other well known aws iam enumeration tools like enumerate-iam and weirdAAL. I am not a developer and I work on this with a very limted time budget. Therefore, you should not expect the script to be performant or bug-free. Feel free to create issues or pull requests but do not expect them to be processed in a timely manner.

### Roadmap / Ideas
- Include permissions besides get, list and describe with dry-runs if available
- Add static check to request attached and inline policies for role, user, group to avoid brute forcing if not necessary. 
- Increase the dynamic parameter generation success rate by identifying re-occuring patterns and use fitting dummy parameters. 
- Re-write Logging / Live Output with an acutal Logging library.
- Improve context with the collected successful responses.
- Add support for other Cloud Providers (GCP, Azure)
