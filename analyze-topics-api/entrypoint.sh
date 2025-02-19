#!/bin/bash

case $1 in
    analyze)
        script=extract-domains.py
        ;;
    attest-domain)
        script=attest-domain.py
        ;;
    extract-domains)
        script=extract-domains.py
        ;;
    *)
        echo "Usage: $0 [analyze | attest-domain | extract-domains] <args>";
        exit 1
        ;;
esac

python3 "$script" ${@:2}