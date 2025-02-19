#!/bin/bash

# Environment variables
WORKING_DIR="${WORKING_DIR:=$PWD}"
OUTPUT_DIR="${OUTPUT_DIR:="$WORKING_DIR/output"}"
CHROMIUM_DIR="${CHROMIUM_DIR:="$WORKING_DIR/crawler/chromium"}"

# Extract allowed domains if unavailable
if [ ! -f "$WORKING_DIR/input/allowed-domains.txt" ]; then
    echo "No list of allowed domains given, using empty list." >&2
    mkdir "$WORKING_DIR/input"
    touch "$WORKING_DIR/input/allowed-domains.txt"
fi

if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir "$OUTPUT_DIR"
fi

# RUN PRIV-ACCEPT
python3 "$WORKING_DIR/crawler/priv-accept.py" \
    --url "$1" \
    --outfile "$OUTPUT_DIR/priv-accept-output.json" \
    --timeout "${PRIV_ACCEPT_TIMEOUT:=5}" \
    --chrome_driver "$CHROMIUM_DIR/chromedriver" \
    --chrome_binary "$CHROMIUM_DIR/chrome" \
    --accept_words "$WORKING_DIR/crawler/accept_words.txt" \
    --screenshot_dir "$OUTPUT_DIR/screenshots" \
    --lang "en, en-us, en-gb, it, fr, es, de, ru" \
    --docker --clear_cache --full_net_log --xvfb \
    --detect_topics \
    $PRIV_ACCEPT_ARGS

if [ $? -ne 0 ]; then
    exit 1
fi

# EXTRACT AND ATTEST DOMAINS
echo "domain,attestation_json" > "$OUTPUT_DIR/attested-domains.csv"
echo "Extracting contacted domains"
python3 "$WORKING_DIR/analyze-topics-api/extract-domains.py" "$OUTPUT_DIR/priv-accept-output.json" --visit first | sort | uniq > "$OUTPUT_DIR/contacted-domains-first.txt"
python3 "$WORKING_DIR/analyze-topics-api/extract-domains.py" "$OUTPUT_DIR/priv-accept-output.json" --visit second | sort | uniq > "$OUTPUT_DIR/contacted-domains-second.txt"
cat "$OUTPUT_DIR/contacted-domains-first.txt" "$OUTPUT_DIR/contacted-domains-second.txt" | sort | uniq > "$OUTPUT_DIR/contacted-domains.txt"
echo "Checking for attested domains"
cat "$OUTPUT_DIR/contacted-domains.txt" | xargs -I {} timeout -s KILL ${CONNECTION_TIMEOUT:=30} python3 "$WORKING_DIR/analyze-topics-api/attest-domain.py" {} >> "$OUTPUT_DIR/attested-domains.csv"

# EXTRACT TOPICS API DATA FROM OUTPUTS
python3 "$WORKING_DIR/analyze-topics-api/analyze-topics-api.py" "$OUTPUT_DIR/priv-accept-output.json" \
    --attested_domains_file "$OUTPUT_DIR/attested-domains.csv" \
    --allowed_domains_file "$WORKING_DIR/input/allowed-domains.txt" \
    --consent_managers_file "$WORKING_DIR/analyze-topics-api/consent-managers.txt" \
    --outfile "$OUTPUT_DIR/analyze-topics-output.json"

if [ $? -ne 0 ]; then
    exit 2
fi

# ADD CONTACTED DOMAINS INTO FINAL JSON
jq -c \
    --rawfile contacted_domains_first "$OUTPUT_DIR/contacted-domains-first.txt" \
    --rawfile contacted_domains_second "$OUTPUT_DIR/contacted-domains-second.txt" \
    '. + { first: (.first + { contacted_domains: ($contacted_domains_first | split("\n") | map(select(length > 0))) }), second: (.second + { contacted_domains: ($contacted_domains_second | split("\n") | map(select(length > 0))) }) }' \
    "$OUTPUT_DIR/analyze-topics-output.json" \
    > "$OUTPUT_DIR/final-output.json"

if [ $? -ne 0 ]; then
    exit 3
fi