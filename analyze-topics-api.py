import argparse
from datetime import datetime
import time
import traceback
import requests
import json
import sys
import os
import re
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('infile', type=str)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--privacy_sandbox_attestations', type=str, default='{}/.config/google-chrome/PrivacySandboxAttestationsPreloaded/2024.3.11.0/privacy-sandbox-attestations.dat'.format(os.path.expanduser('~')))
parser.add_argument('--outfile', type=str, default='topics_output.json')

globals().update(vars(parser.parse_args()))

log_entries = []

def main():
    input_json = json.load(open(infile))

    try:
        global privacy_sandbox_domains
        privacy_sandbox_domains = get_privacy_sandbox_attested_domains()
    except FileNotFoundError:
        log("Privacy Sandbox attestation file not found. No pre-computed domains will be used.")
        privacy_sandbox_domains = []
    
    data = {}

    # First visit data
    first_visit_data = input_json.get("first")
    if first_visit_data is not None:
        log("Analyzing first visit data")
        data["url"] = first_visit_data["requests"][0]["documentURL"]
        data["first"] = get_topics_api_data(first_visit_data)

    # Post-click data
    post_click_data = input_json.get("click")
    if post_click_data is not None:
        log("Analyzing post-click data")
        data["click"] = get_topics_api_data(post_click_data)

    # Second visit data
    second_visit_data = input_json.get("second")
    if second_visit_data is not None:
        log("Analyzing second visit data")
        data["second"] = get_topics_api_data(second_visit_data)

    # Internal visits data
    internal_visits_data = input_json.get("internal")
    if internal_visits_data is not None:
        log("Analyzing internal page visits data")
        data["internal"] = get_topics_api_data(internal_visits_data)

    json.dump(data, open(outfile, "w"), indent=4)

    data["log_entries"] = log_entries
    log("All Done")

def get_topics_api_data(network_data):
    requests = network_data["requests"]
    responses = network_data["responses"]
    responses_extra = network_data["responses-extra"]

    data = { "attested_domains": set(), "users": [] }
    for request in requests:
        url = request["documentURL"]
        domain = get_domain(url)
        attested = False
        if attest_privacy_sandbox(domain):
            data["attested_domains"].add(domain)
            attested = True

        headers = request["request"]["headers"]
        if attested and ("sec-browsing-topics" in headers or "Sec-Browsing-Topics" in headers):
            data["users"].append({ "url": url, "method": "header_request" })

    for response in responses:
        url = response["response"]["url"]
        domain = get_domain(url)
        attested = False
        if attest_privacy_sandbox(domain):
            data["attested_domains"].add(domain)
            attested = True
            
        headers = response["response"]["headers"]
        if "observe-browsing-topics" in headers or "Observe-Browsing-Topics" in headers:
            data["users"].append({ "url": url, "method": "header_response" })

        content_type = headers.get("content-type") or headers.get("Content-Type")
        if content_type is not None:
            if ('text/javascript' in content_type or "application/javascript" in content_type) and content_has_browsing_topics(url):
                data["users"].append({ "url": url, "method": "javascript" })

    data["attested_domains"] = list(data["attested_domains"])

    return data

def attest_privacy_sandbox(domain: str) -> bool:
    # This cache memorizes the result of previous operations, saving significant amounts of time
    global attestation_result_cache
    try: attestation_result_cache
    except NameError: attestation_result_cache = {}

    domain_levels = domain.strip(".").split(".")

    # Check each domain (from level 2 to level N) for the existence of the sandbox attestation file
    for level in range(2,len(domain_levels)+1):
        domain = ".".join(domain_levels[-level:])

        cached_result = attestation_result_cache.get(domain)
        if cached_result == True:
            return True
        elif cached_result == False:
            continue

        if len(privacy_sandbox_domains) > 0 and domain not in privacy_sandbox_domains:
            attestation_result_cache[domain] = False
            continue

        try:
            r = requests.get("https://{}/.well-known/privacy-sandbox-attestations.json".format(domain), timeout=timeout)
        except:
            # Connection error or invalid URL, suppose the domain is not valid
            attestation_result_cache[domain] = False
            continue

        content_type = r.headers.get('content-type') or r.headers.get('Content-Type')
        if r.status_code == 200 and content_type is not None and "application/json" in content_type:
            # Document is a JSON object, check if it contains valid information
            try:
                attestation_json = r.json()
            except requests.exceptions.JSONDecodeError:
                attestation_result_cache[domain] = False
                continue
            
            if valid_attestation_json(attestation_json, domain):
                attestation_result_cache[domain] = True
                return True
    return False

def valid_attestation_json(json, domain):
    sandbox_attestations = json.get("privacy_sandbox_api_attestations")
    if sandbox_attestations is None:
        return False
    for sandbox_attestation in sandbox_attestations:
        expiry = sandbox_attestation.get("expiry_seconds_since_epoch")
        if expiry is not None and expiry < time.time():
            continue
        enrollment_site = sandbox_attestation.get("enrollment_site")
        if enrollment_site is None or get_domain(enrollment_site) != get_domain(domain, len(enrollment_site.strip(".").split("."))):
            continue
        platform_attestations = sandbox_attestation.get("platform_attestations")
        for platform_attestation in platform_attestations:
            platform = platform_attestation.get("platform")
            if platform == "chrome":
                topics_api_attestations = platform_attestation.get("attestations", {}).get("topics_api", {})
                if topics_api_attestations.get("ServiceNotUsedForIdentifyingUserAcrossSites"):
                    return True
    return False

def get_privacy_sandbox_attested_domains():
    with open(privacy_sandbox_attestations) as file:
        file_content = file.read()
    non_url_chars = re.compile("[\\x00-\\x2c\\x7B-\\x7F]+")
    urls_unchecked = re.split(non_url_chars, file_content)
    return [ get_domain(url) for url in urls_unchecked if is_url(url) ]

def content_has_browsing_topics(url: str) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
    except:
        # Connection error or invalid URL, suppose the script does not contain API calls
        return False
    
    return r.status_code == 200 and "browsingTopics" in r.text or "browsingtopics" in r.text

def get_domain(url, level = None):
    parse_result = urlparse(url)
    domain = parse_result.netloc if len(parse_result.scheme) > 0 else parse_result.path
    domain_levels = domain.strip(".").split(".")
    level = len(domain_levels) if level is None else level
    return '.'.join(domain_levels[-level:])

def is_url(url):
  try:
    result = urlparse(url)
    return all([result.scheme, result.netloc])
  except ValueError:
    return False

def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))

if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)