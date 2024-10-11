import argparse
import json
import sys
from get_domain import getGood2LD

parser = argparse.ArgumentParser()
parser.add_argument('input_file', type=str)

def main(args):
    with open(args.input_file, "r") as input_json_file:
        input_json = json.load(input_json_file)
    banner_clicked = input_json.get("banner_data", {}).get("clicked_element") is not None
    if banner_clicked:
        domains = extract_domains(input_json)
        print(f"Found {len(domains)} domain(s) in {args.input_file}", file=sys.stderr)
        for domain in domains:
            print(domain)

def extract_domains(input_json):
    domains = set()
    for stage in [ "second" ]:
        visit_data = input_json.get(stage)
        if visit_data is None:
            continue
        for request in visit_data["requests"]:
            domain = getGood2LD(request["request"]["url"])
            if domain is not None:
                domains.add(domain)
        for response in visit_data["responses"]:
            domain = getGood2LD(response["response"]["url"])
            if domain is not None:
                domains.add(domain)
    return domains

if __name__ == '__main__':
    main(parser.parse_args())