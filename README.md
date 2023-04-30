# I am Brute!
Currently, only get, list and describe permissions are checked. The dynamic parameter generation currently only supports static parameters. Sometimes, these fail client parameter validation. If this is the case, no access rights can be checked. 

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
