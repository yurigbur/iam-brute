# I am Brute!
The idea of this enumeration script is to derive available AWS APIs directly from the boto3 library. As this library is (currently) nicely maintained and up to date with the AWS API, this removes the necessity to re-generate and maintain a list of endpoints that are checked. As far as no fundamental things are changed in boto3 or AWS, this script will always be up to date.

Currently, only get, list and describe permissions are checked to avoid accidentially manipulating resources. The dynamic parameter generation currently only supports a few parameters that allow arbitrary input or are covered by the basic heuristical dummy parameter generation. For parameters that expect unknowncformats, the parameter validation will fail. If this is the case, no access rights can be checked. The script prints the permissions in question and lists the parameters where the dummy input failed.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
The tool can be used with user access keys or with temporary access keys for roles
```bash
python iam-brute.py --access-key AKIA... --secret-key ...
python iam-brute.py --access-key ASIA... --secret-key ... --session-token ey...
```

Refer to the help menu for further flags
```bash
$ python3 iam-brute.py -h                                                                                                                     
usage: iam-brute.py [-h] --access-key ACCESS_KEY --secret-key SECRET_KEY [--session-token SESSION_TOKEN] [--services SERVICES [SERVICES ...]]
                    [--verbose {silent,warning,debug}] [--threads THREADS] [--no-banner]

IAM Brute

options:
  -h, --help            show this help message and exit
  --access-key ACCESS_KEY
                        AWS access key
  --secret-key SECRET_KEY
                        AWS secret key
  --session-token SESSION_TOKEN
                        STS session token
  --services SERVICES [SERVICES ...]
                        Space-sepearated list of services to enumerate
  --verbose {silent,warning,debug}
                        Sets the level of information the script prints: "silent" only prints confirmed permissions, "warning" (default) prints parameter
                        parsing errors and "debug" prints all errors
  --threads THREADS     Number of threads (Default 25)
  --no-banner           Hides banner
```

**Review the EXCLUDED_SERVICE variable, it may contain services that you are looking for**

### Docker
```bash
sudo docker run -it yukonsec/iam-brute 
```

## Disclaimer
I started writing this tool as I was frustrated with the coverage and maintenance state of other well known aws iam enumeration tools like enumerate-iam and weirdAAL. I am not a developer and I work on this with a very limted time budget. Therefore, you should not expect the script to be performant.

### Roadmap / Ideas
- Include permissions besides get, list and describe with dry-runs if available
- Increase the dynamic parameter generation success rate by identifying re-occuring patterns and use fitting dummy parameters. 
- Improve multi-threading exception handling
- Write watcher that kills hanging threads.
