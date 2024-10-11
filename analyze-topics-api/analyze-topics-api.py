import argparse
from datetime import datetime
import traceback
import requests
import json
import sys
from urllib.parse import urlparse
from get_domain import getGood2LD

parser = argparse.ArgumentParser()
parser.add_argument('infile', type=str)
parser.add_argument('--timeout', type=int, default=5)
parser.add_argument('--attested_domains_file', type=str, default='attested_domains.csv')
parser.add_argument('--allowed_domains_file', type=str, default='allowed_domains.txt')
parser.add_argument('--outfile', type=str, default='topics_output.json')
parser.add_argument('--pretty_print', action='store_true')

globals().update(vars(parser.parse_args()))

log_entries = []

def log(str):
    print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"), str)
    log_entries.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str))

def read_domains_file(file_path):
    with open(file_path) as file:
        domains = { line.split(",")[0].strip() for line in file.readlines() }
    return domains

def main():
    input_json = json.load(open(infile))
    
    data = {}
    attested_domains = read_domains_file(attested_domains_file)
    allowed_domains = read_domains_file(allowed_domains_file)

    data["url"] = input_json["first"]["requests"][0]["documentURL"]
    for stage in [ "first", "click", "second", "internal" ]:
        visit_data = input_json.get(stage)
        if visit_data is None:
            continue
        log(f"Analyzing data for stage {stage}")
        data[stage] = get_topics_api_data(visit_data, attested_domains, allowed_domains)
    
    # Save whether accept button has been clicked
    clicked_element = input_json.get("banner_data", {}).get("clicked_element")
    data["banner_clicked"] = clicked_element is not None

    json.dump(data, open(outfile, "w"), indent=4 if pretty_print else None)

    data["log_entries"] = log_entries
    log("All Done")

def get_topics_api_data(network_data, attested_domains, allowed_domains):
    requests = network_data["requests"]
    responses = network_data["responses"]

    # Map the Origin URL to the API usage object
    topics_api_usages_map = { obj["context_origin_url"]: obj for obj in network_data["topics_api_usages"] }

    data = { "attested_domains": set(), "allowed_domains": set() }
    for request in requests:
        url = request["request"]["url"]
        domain = getGood2LD(url)
        if domain in attested_domains:
            data["attested_domains"].add(domain)
        if domain in allowed_domains:
            data["allowed_domains"].add(domain)

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
        domain = getGood2LD(url)
        if domain in attested_domains:
            data["attested_domains"].add(domain)
        if domain in allowed_domains:
            data["allowed_domains"].add(domain)
            
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
    data["attested_domains"] = list(data["attested_domains"])
    data["allowed_domains"] = list(data["allowed_domains"])

    return data

def content_has_browsing_topics(url: str) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200 and "browsingtopics" in r.text.lower()
    except:
        # Connection error or invalid URL, suppose the script does not contain API calls
        return False

def get_origin(url):
    parse_result = urlparse(url)
    return "{}://{}/".format(parse_result.scheme, parse_result.netloc)

def is_url(url):
  try:
    result = urlparse(url)
    return all([result.scheme, result.netloc])
  except ValueError:
    return False

if __name__ == "__main__":

    try:
        main()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log("Exception at line {}: {}".format(exc_tb.tb_lineno, e))
        traceback.print_exception(exc_type, exc_obj, exc_tb)
        exit(1)