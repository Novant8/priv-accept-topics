import os
import io
import sys
import argparse
from zipfile import ZipFile
from chrome_component_downloader import download_component, DownloadFailedException

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
    if output_filename is None:
        for site in allowed_websites:
            print(site)
    else:
        with open(output_filename, "w") as outfile:
            outfile.writelines(f"{site}\n" for site in allowed_websites)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default="allowed-domains.txt", help="Output file name")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of saving to a file")
    parser.add_argument("--target_version", type=str, default="", help="Target version of Attestations list to download. If not specified, the latest version will be downloaded.")
    parser.add_argument("--send_system_info", action="store_true", help="Send system info to the server")

    args = parser.parse_args()

    # Download component
    try:
        component_zip,_ = download_component(
            component_id=PRIVACY_SANDBOX_ATTESTATIONS_ID,
            target_version=args.target_version,
            send_system_info=args.send_system_info
        )
        if component_zip is None:
            print("Target version does not exist.", file=sys.stderr)
            exit(1)
    except DownloadFailedException as e:
        print(f"Failed to download component. Try again later.", file=sys.stderr)
        exit(1)

    zip_file = ZipFile(io.BytesIO(component_zip), mode="r")

    # Extract allowed domains from downloaded zip
    with zip_file.open("privacy-sandbox-attestations.dat", "r") as attestations_file:
        allowed_websites = extract_allowed_domains_from_protobuf(attestations_file)
        save_allowed_websites_file(allowed_websites, args.output if not args.stdout else None)

if __name__ == "__main__":
    main()