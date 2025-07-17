#!/bin/bash

# Exit script on any command error
set -e

# Environment variables
WORKING_DIR="${WORKING_DIR:=$PWD}"
INPUT_DIR="${INPUT_DIR:="$WORKING_DIR/input"}"
OUTPUT_DIR="${OUTPUT_DIR:="$WORKING_DIR/output"}"
CHROMIUM_DIR="${CHROMIUM_DIR:="/opt/google-chrome"}"

# Check for parameters
deny=0
for arg in "$@"; do
    if [ "$arg" == "--deny" ]; then
        deny=1
        break
    fi
done

# Extract allowed domains if unavailable
if [ ! -f "$INPUT_DIR/allowed-domains.csv" ]; then
    echo "No list of allowed domains given, downloading allowed domains" >&2
    mkdir -p "$INPUT_DIR"
    python3 "$WORKING_DIR/extract-allowed-domains/extract_allowed_domains.py" \
        --api_map "$WORKING_DIR/extract-allowed-domains/ps_api_map.json" \
        --output "$INPUT_DIR/allowed_domains.csv"
fi

if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
fi

# RUN PRIV-ACCEPT
echo "Running crawler"
python3 "$WORKING_DIR/crawler/priv-accept.py" \
    --url "$1" \
    --outfile "$OUTPUT_DIR/priv-accept-output.json" \
    --timeout "${PRIV_ACCEPT_TIMEOUT:=5}" \
    --chrome_driver "$CHROMIUM_DIR/chromedriver" \
    --chrome_binary "$CHROMIUM_DIR/chrome" \
    --accept_words "$WORKING_DIR/crawler/accept_words.txt" \
    --deny_words "$WORKING_DIR/crawler/deny_words.txt" \
    --option_words "$WORKING_DIR/crawler/option_words.txt" \
    --screenshot_dir "$OUTPUT_DIR/screenshots" \
    --lang "en, en-us, en-gb, it, fr, es, de, ru" \
    --docker --clear_cache --full_net_log --xvfb \
    $( if [ "$deny" = 1 ]; then echo '--deny'; fi ) \
    $PRIV_ACCEPT_ARGS

visits_json='["first","second"]'
fields_json='["contacted_domains","api_calls","partitioned_cookies"]'

echo "Extracting contacted domains"
echo "domain,attestation_json" > "$OUTPUT_DIR/attested-domains.csv"
jq  -L "$WORKING_DIR/post-process/modules" \
    -f "$WORKING_DIR/post-process/extract_contacted_2ld.jq" \
    --argjson visits $visits_json \
    --arg separate 1 \
    --arg full_net_log 1 \
    "$OUTPUT_DIR/priv-accept-output.json" \
    > "$OUTPUT_DIR/contacted-domains.json"

echo "Checking for attested domains"
jq -r 'flatten | unique[]' "$OUTPUT_DIR/contacted-domains.json" |
xargs -I {} sh -c "timeout -s KILL ${CONNECTION_TIMEOUT:=30} python3 "$WORKING_DIR/post-process/attest-domain.py" {} || true" >> "$OUTPUT_DIR/attested-domains.csv"

echo "Extracting meaningful data from crawler output"
jq  -L "$WORKING_DIR/post-process/modules" \
    -f "$WORKING_DIR/post-process/post_process_output.jq" \
    "$OUTPUT_DIR/priv-accept-output.json" \
    --argjson visits $visits_json \
    --argjson fields $fields_json \
    --arg position -1 \
    --arg full_net_log 1 \
    --arg csv_format 0 \
    > "$OUTPUT_DIR/final-output.json"