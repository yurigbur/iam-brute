# I am Brute!

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
Currently, only get, list and describe permissions are checked.

By default, the tool enumerates over all services and permissions that are available in boto3. The flag `--services` expects a space-separated list and limits the enumeration to the specified services.


## Disclaimer
I started writing this tool as I was frustrated with the coverage and maintenance state of other well known aws iam enumeration tools like enumerate-iam and weirdAAL. I am not a developer and I work on this with a very limted time budget. Therefore, you should not expect the script to be performant.

### Roadmap / Ideas
- Include permissions besides get, list and describe with using dummy parameters and dry-runs (if available)
- Identify needed parameters dynamically from the functions themeselves. 
- Multi-threading  
