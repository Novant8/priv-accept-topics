#!/bin/bash

case $1 in
    extract-contacted-2ld)
        cmd="jq -L modules -f extract_contacted_2ld.jq"
        ;;
    attest-domain)
        cmd="python3 attest-domain.py"
        ;;
    post-process-output)
        cmd="jq -r -L modules -f post_process_output.jq"
        ;;
    merge-csv)
        cmd="python3 merge-csv.py"
        ;;
    *)
        echo "Usage: $0 <extract-contacted-2ld | attest-domain | post-process-output | merge-csv> <args>";
        exit 1
        ;;
esac

$cmd ${@:2}