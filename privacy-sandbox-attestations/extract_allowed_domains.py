import argparse
import os
from get_domain import getFullDomain
import privacy_sandbox_attestations_pb2

parser = argparse.ArgumentParser()
parser.add_argument('attestations_file', type=str, default='privacy-sandbox-attestations.dat')
args = parser.parse_args()

TOPICS = privacy_sandbox_attestations_pb2.PrivacySandboxAttestationsGatedAPIProto.TOPICS

def read_attestations():
    attestations = privacy_sandbox_attestations_pb2.PrivacySandboxAttestationsProto()
    try:
      with open(args.attestations_file, "rb") as file:
        attestations.ParseFromString(file.read())
      return attestations
    except IOError:
      print("Could not read file {}.".format(args.attestations_file))
      exit(1)

def main():
    attestations = read_attestations()

    for site in attestations.sites_attested_for_all_apis:
        print(getFullDomain(site))

    for site,attestations in attestations.site_attestations.items():
       if TOPICS in attestations.attested_apis:  
        print(getFullDomain(site))

if __name__ == '__main__':
   main()