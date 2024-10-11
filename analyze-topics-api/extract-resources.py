import argparse
import json
import requests
import hashlib
import sys
from get_domain import getGood2LD
from nltk.metrics import edit_distance

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DISTANCE_THRESH = 0.5

parser = argparse.ArgumentParser()
parser.add_argument('--infile', type=str)
parser.add_argument('--domain', type=str)

def get_first_part(domain):
    return domain.split('.')[0]
 
def get_distance(domain1, domain2):
    str1 = get_first_part(domain1)
    str2 = get_first_part(domain2)
    dist = edit_distance(str1,str2) / max([len(str1), len(str2)])
    return dist

def is_same_domain(domain1, domain2):
    return get_distance(domain1, domain2) <= DISTANCE_THRESH

def hash_content(url):
    r = requests.get(url, headers={ "User-Agent": USER_AGENT })
    return hashlib.sha256(r.content).hexdigest()

def main(args):
    with open(args.infile, "r") as file:
        priv_accept_output = json.load(file)["second"]

    for request in priv_accept_output["requests"]:
        url = request["request"]["url"]
        domain = getGood2LD(url)
        if domain is not None and is_same_domain(domain, args.domain):
            try:
                digest = hash_content(url)
            except requests.RequestException:
                digest = ""
            print(f"\"{url}\",{digest}")

    print(f"Input {args.infile} analyzed", file=sys.stderr)

if __name__ == '__main__':
    main(parser.parse_args())