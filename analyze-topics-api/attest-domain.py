import argparse
import requests
import json
from json.decoder import JSONDecodeError
import sys
import time

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

parser = argparse.ArgumentParser()
parser.add_argument('domain', type=str)
parser.add_argument('--timeout', type=int, default=60)

def main(args):
    sandbox_attestation = get_privacy_sandbox_attestation_data(args.domain, args.timeout)
    if sandbox_attestation is not None:
        print(f"Found attested domain {args.domain}", file=sys.stderr)
        sandbox_attestation_csv = json.dumps(sandbox_attestation).replace('"', '""')
        print(f'{args.domain},"{sandbox_attestation_csv}"')

def get_privacy_sandbox_attestation_data(domain, timeout):
    try:
        r = requests.get("https://{}/.well-known/privacy-sandbox-attestations.json".format(domain), headers={ "User-Agent": USER_AGENT }, timeout=timeout, verify=False)
    except Exception as e:
        # Connection error or invalid URL, suppose the domain is not valid
        return None

    if not r.ok:
        return None

    # Document is a JSON object, check if it contains valid information
    try:
        attestation_json = r.json()
    except JSONDecodeError as e:
        return None
    
    try:
        valid_sandbox_attestations = get_valid_sandbox_attestations(attestation_json)
    except:
        return None
    
    if len(valid_sandbox_attestations) == 0:
        return None

    return attestation_json

def get_valid_sandbox_attestations(json):
    expired = True
    valid_attestations = []
    sandbox_attestations = json.get("privacy_sandbox_api_attestations")
    if sandbox_attestations is None:
        return []
    for sandbox_attestation in sandbox_attestations:
        expiry = sandbox_attestation.get("expiry_seconds_since_epoch")
        if expiry is None or expiry > time.time():
            expired = False
        platform_attestations = sandbox_attestation.get("platform_attestations")
        for platform_attestation in platform_attestations:
            platform = platform_attestation.get("platform")
            if platform == "chrome":
                topics_api_attestations = platform_attestation.get("attestations", {}).get("topics_api", {})
                if topics_api_attestations.get("ServiceNotUsedForIdentifyingUserAcrossSites"):
                    valid_attestations.append(sandbox_attestation)

    if not expired:
        return valid_attestations
    else:
        return []
    
if __name__ == '__main__':
    main(parser.parse_args())