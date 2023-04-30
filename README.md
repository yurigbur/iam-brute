# I am Brute!
The idea of this enumeration script is to derive available AWS APIs directly from the boto3 library. As this library is (currently) nicely maintained and up to date with the AWS API, this removes the necessity to re-generate and maintain a list of endpoints that are checked. As far as no fundamental things are changed in boto3 or AWS, this script will always be up to date.

Currently, only get, list and describe permissions are checked to avoid accidentially manipulating resources. The dynamic parameter generation currently only supports parameters that allow arbitrary inputs as a static dummy parameter is used. For parameters that expect certain formats, the parameter validation will fail. If this is the case, no access rights can be checked. 

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

By default, the tool enumerates over all services and permissions that are available in boto3. The flag `--services` expects a space-separated list and limits the enumeration to the specified services.


## Disclaimer
I started writing this tool as I was frustrated with the coverage and maintenance state of other well known aws iam enumeration tools like enumerate-iam and weirdAAL. I am not a developer and I work on this with a very limted time budget. Therefore, you should not expect the script to be performant.

### Roadmap / Ideas
- Include permissions besides get, list and describe with dry-runs if available
- Increase the dynamic parameter generation success rate by identifying re-occuring patterns and use fitting dummy parameters. 
- Multi-threading  
