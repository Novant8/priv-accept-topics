import io
import sys
import argparse
import csv
import json
from zipfile import ZipFile
from chrome_component_downloader import download_component

from get_domain import getFullDomain
import privacy_sandbox_attestations_pb2

PRIVACY_SANDBOX_ATTESTATIONS_ID = "niikhdgajlphfehepabhhblakbdgeefj"

def read_attestations(attestations_file: io.BytesIO) -> any:
    attestations_proto = privacy_sandbox_attestations_pb2.PrivacySandboxAttestationsProto()
    try:
        attestations_proto.ParseFromString(attestations_file.read())
        return attestations_proto
    except IOError:
        print("Could not read file 'privacy-sandbox-attestations.dat'.", file=sys.stderr)
        exit(1)

def get_attestations_per_api(attested_apis: list[int], all_apis: list[int]) -> list[bool]:
    attested_apis_set = set(attested_apis)
    attestations = [ api in attested_apis_set for api in all_apis ]
    return attestations

def extract_allowed_domains_from_protobuf(attestations_file: io.BytesIO) -> tuple[list[list[str | bool]], list[int]]:
    attestations_proto = read_attestations(attestations_file)
    allowed_websites_csv = (
        [
            [ getFullDomain(site) ] + [ True ] * len(attestations_proto.all_apis)
            for site in attestations_proto.sites_attested_for_all_apis
        ]
        +
        [
            [ getFullDomain(site) ] + get_attestations_per_api(attestations.attested_apis, attestations_proto.all_apis)
            for site,attestations in attestations_proto.site_attestations.items()
        ]
    )
    return allowed_websites_csv, attestations_proto.all_apis

def save_allowed_websites_file(allowed_websites: list[list[str | bool]], output_filename: str, apis_map_file: str, all_apis: str):
    with open(apis_map_file, "r") as fp:
        privacy_sandbox_apis_map = json.load(fp)
    header = [ "domain" ] + [ "{}_allowed".format(privacy_sandbox_apis_map[str(api)]) for api in all_apis ]
    with open(output_filename, "w") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(allowed_websites)

def main(args):
    # Download latest version
    component_zip,_ = download_component(PRIVACY_SANDBOX_ATTESTATIONS_ID)
    zip_file = ZipFile(io.BytesIO(component_zip), mode="r")

    # Extract allowed domains from downloaded zip
    with zip_file.open("privacy-sandbox-attestations.dat", "r") as attestations_file:
        allowed_websites, all_apis = extract_allowed_domains_from_protobuf(attestations_file)
        save_allowed_websites_file(allowed_websites, args.output, args.api_map, all_apis)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api_map", type=str, default="ps_api_map.json")
    parser.add_argument("--output", type=str, default="allowed_domains.csv")

    main(parser.parse_args())