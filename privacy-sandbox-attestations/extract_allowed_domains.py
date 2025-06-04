import os
import io
import sys
import argparse
from zipfile import ZipFile
from chrome_component_downloader import download_component

from get_domain import getFullDomain
import privacy_sandbox_attestations_pb2

PRIVACY_SANDBOX_ATTESTATIONS_ID = "niikhdgajlphfehepabhhblakbdgeefj"

TOPICS = privacy_sandbox_attestations_pb2.PrivacySandboxAttestationsGatedAPIProto.TOPICS

def read_attestations(attestations_file: io.BytesIO) -> any:
    attestations_proto = privacy_sandbox_attestations_pb2.PrivacySandboxAttestationsProto()
    try:
        attestations_proto.ParseFromString(attestations_file.read())
        return attestations_proto
    except IOError:
        print("Could not read file 'privacy-sandbox-attestations.dat'.", file=sys.stderr)
        exit(1)

def extract_allowed_domains_from_protobuf(attestations_file: io.BytesIO) -> list[str]:
    attestations_proto = read_attestations(attestations_file)
    allowed_websites = (
        [ getFullDomain(site) for site in attestations_proto.sites_attested_for_all_apis ] +
        [ getFullDomain(site) for site,attestations in attestations_proto.site_attestations.items() if TOPICS in attestations.attested_apis ]
    )
    return allowed_websites

def save_allowed_websites_file(allowed_websites: list[str], output_filename: str):
    with open(output_filename, "w") as outfile:
        outfile.writelines(f"{site}\n" for site in allowed_websites)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="allowed-domains.txt")

    args = parser.parse_args()

    # Download latest version
    component_zip,_ = download_component(PRIVACY_SANDBOX_ATTESTATIONS_ID)
    zip_file = ZipFile(io.BytesIO(component_zip), mode="r")

    # Extract allowed domains from downloaded zip
    with zip_file.open("privacy-sandbox-attestations.dat", "r") as attestations_file:
        allowed_websites = extract_allowed_domains_from_protobuf(attestations_file)
        save_allowed_websites_file(allowed_websites, args.output)

if __name__ == "__main__":
    main()