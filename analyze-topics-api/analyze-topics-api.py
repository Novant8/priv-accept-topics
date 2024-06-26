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
import psycopg2

parser = argparse.ArgumentParser()
parser.add_argument('infile', type=str)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--privacy_sandbox_attestations', type=str, default='{}/.config/google-chrome/PrivacySandboxAttestationsPreloaded/2024.3.11.0/privacy-sandbox-attestations.dat'.format(os.path.expanduser('~')))
parser.add_argument('--outfile', type=str, default='topics_output.json')
parser.add_argument('--pretty_print', action='store_true')
parser.add_argument('--cache_db_host', type=str, default='localhost')
parser.add_argument('--cache_db_port', type=str, default='5432')
parser.add_argument('--cache_db_name', type=str, default='analyze_topics_cache')
parser.add_argument('--cache_db_user', type=str, default='docker')
parser.add_argument('--cache_db_password', type=str, default='docker')

globals().update(vars(parser.parse_args()))

log_entries = []

def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))

try:
    db_conn = psycopg2.connect(host=cache_db_host, port=cache_db_port, dbname=cache_db_name, user=cache_db_user, password=cache_db_password)
except psycopg2.OperationalError:
    log("Connection to cache database failed, cache will not be used")
    db_conn = None

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
    
    # Save whether accept button has been clicked
    clicked_element = input_json.get("banner_data", {}).get("clicked_element")
    data["banner_clicked"] = clicked_element is not None

    json.dump(data, open(outfile, "w"), indent=4 if pretty_print else None)

    data["log_entries"] = log_entries
    log("All Done")

def get_topics_api_data(network_data):
    requests = network_data["requests"]
    responses = network_data["responses"]

    # Map the Origin URL to the API usage object
    topics_api_usages_map = { obj["context_origin_url"]: obj for obj in network_data["topics_api_usages"] }

    data = { "attestations": {} }
    for request in requests:
        url = request["documentURL"]
        domain = get_domain(url)
        privacy_sandbox_attestation_result = get_privacy_sandbox_attestation_data(domain)
        if privacy_sandbox_attestation_result:
            attestation_domain = privacy_sandbox_attestation_result["domain"]
            data["attestations"][attestation_domain] = privacy_sandbox_attestation_result

        origin = get_origin(url)
        topics_api_usage = topics_api_usages_map.get(origin)
        if topics_api_usage is None:
            continue

        headers = request["request"]["headers"]
        if topics_api_usage["caller_source"] in ["fetch", "iframe"] and ("sec-browsing-topics" in headers or "Sec-Browsing-Topics" in headers):
            topics_api_usage["possible_callers"] = topics_api_usage.get("possible_callers", [])
            topics_api_usage["possible_callers"].append({ "url": url, "reason": "header-request" })

    for response in responses:
        url = response["response"]["url"]
        domain = get_domain(url)
        privacy_sandbox_attestation_result = get_privacy_sandbox_attestation_data(domain)
        if privacy_sandbox_attestation_result:
            attestation_domain = privacy_sandbox_attestation_result["domain"]
            data["attestations"][attestation_domain] = privacy_sandbox_attestation_result
            
        origin = get_origin(url)
        topics_api_usage = topics_api_usages_map.get(origin)
        if topics_api_usage is None:
            continue
        
        headers = response["response"]["headers"]
        if topics_api_usage["caller_source"] in ["fetch", "iframe"] and ("observe-browsing-topics" in headers or "Observe-Browsing-Topics" in headers):
            topics_api_usage["possible_callers"] = topics_api_usage.get("possible_callers", [])
            topics_api_usage["possible_callers"].append({ "url": url, "reason": "header-response" })

        content_type = headers.get("content-type") or headers.get("Content-Type")
        if topics_api_usage["caller_source"] == "javascript" and content_type is not None:
            if ('text/javascript' in content_type or "application/javascript" in content_type) and content_has_browsing_topics(url):
                topics_api_usage["possible_callers"] = topics_api_usage.get("possible_callers", [])
                topics_api_usage["possible_callers"].append({ "url": url, "reason": "browsingtopics-in-script" })

    data["topics_api_usages"] = list(topics_api_usages_map.values())
    data["attestations"] = list(data["attestations"].values())

    return data

def get_privacy_sandbox_attestation_data(domain: str) -> dict | None:
    domain_levels = domain.strip(".").split(".")

    # Check each domain (from level 2 to level N) for the existence of the sandbox attestation file
    for level in range(2,len(domain_levels)+1):
        domain = ".".join(domain_levels[-level:])

        cached_result = get_attestation_result_from_cache(domain)
        if cached_result:
            attested = cached_result["attested"]
            cached_attestation_result = cached_result.get("attestation_result")
            if attested:
                return { "domain": domain, "sandbox_attestations": cached_attestation_result }
            else:
                continue

        if len(privacy_sandbox_domains) > 0 and domain not in privacy_sandbox_domains:
            save_attestation_result_to_cache(domain, None)
            continue

        try:
            r = requests.get("https://{}/.well-known/privacy-sandbox-attestations.json".format(domain), timeout=timeout)
        except:
            # Connection error or invalid URL, suppose the domain is not valid
            save_attestation_result_to_cache(domain, None)
            continue

        content_type = r.headers.get('content-type') or r.headers.get('Content-Type')
        if r.status_code != 200 or content_type is None or "application/json" not in content_type:
            save_attestation_result_to_cache(domain, None)
            continue
        
        # Document is a JSON object, check if it contains valid information
        try:
            attestation_json = r.json()
        except requests.exceptions.JSONDecodeError:
            save_attestation_result_to_cache(domain, None)
            continue
        try:
            valid_sandbox_attestations = get_valid_sandbox_attestations(attestation_json)
        except:
            continue
        
        if len(valid_sandbox_attestations) == 0:
            save_attestation_result_to_cache(domain, None)
            continue

        sandbox_attestations_info = [
            {
                "issued": sandbox_attestation["issued_seconds_since_epoch"],
                "expired": sandbox_attestation.get("expiry_seconds_since_epoch")
            }
            for sandbox_attestation in valid_sandbox_attestations
        ]

        save_attestation_result_to_cache(domain, sandbox_attestations_info)
        attestation_result = { "domain": domain, "sandbox_attestations": sandbox_attestations_info }
        return attestation_result
    return None

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

def get_privacy_sandbox_attested_domains():
    if db_conn is None:
        return []
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

def get_attestation_result_from_cache(domain) -> dict:
    if db_conn is None:
        return None
    try:
        sql = """
            SELECT attested, attestation_result
            FROM cache
            WHERE domain = %s;
        """
        cur = db_conn.cursor()
        cur.execute(sql, (domain,))
        result = cur.fetchone()
        if result is None:
            return None
        attested, attestation_result = result
        return { "attested": attested, "attestation_result": attestation_result }
    except psycopg2.Error:
        # Connection error or invalid URL, suppose the website is not attested
        return None

def save_attestation_result_to_cache(domain, result):
    if db_conn is None:
        return
    try:
        sql =  """
            INSERT INTO cache(domain, attested, attestation_result)
            VALUES(%s,%s,%s)
            ON CONFLICT DO NOTHING;
        """
        cur = db_conn.cursor()
        cur.execute(sql, (domain, result is not None, json.dumps(result)))
        db_conn.commit()
    except psycopg2.Error:
        pass

def get_origin(url):
    parse_result = urlparse(url)
    return "{}://{}/".format(parse_result.scheme, parse_result.netloc)

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

if __name__ == "__main__":

    try:
        main()
        if db_conn is not None:
            db_conn.close()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        if db_conn is not None:
            db_conn.close()
        exit(1)