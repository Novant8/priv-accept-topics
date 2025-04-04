#!/bin/bash

TODAY=$(date +%Y%m%d) # YYYYMMDD

# Customize these constants to your liking
WORKING_FOLDER="/home/$USER/priv-accept-topics"
OUTPUTS_FOLDER="$WORKING_FOLDER/outputs"
FINAL_OUTPUTS_FOLDER="$WORKING_FOLDER/outputs"
CHROME_CONFIG_FOLDER="/home/$USER/.config/google-chrome"
PRIV_ACCEPT_TIMEOUT="20m"
EXPRESSVPN_ACTIVATION_CODE="CHANGE_ME"

run_chrome() {
    echo "Running Chrome..."
    xvfb-run --auto-servernum google-chrome --disable-gpu > /dev/null 2>&1 &
}

kill_chrome() {
    echo "Killing Chrome..."
    pkill "chrome"
}

docker_auto_kill() {
    while true; do
        docker stop $(docker ps --filter "ancestor=salb98/priv-accept-topics:geo" --format "{{ .ID }} {{ .RunningFor }}" | awk "{if (\$0 ~ /hour/) print \$1}") > /dev/null 2>&1
        sleep 10;
    done
}

cwd=$(pwd)

# Parse arguments
lang="en, en-us, en-gb, it, fr, es, de, ru"
timeout=5
parallel_limit=0
website_limit=50000
date=$TODAY
while getopts ":r:l:t:p:w:d:" opt; do
    case $opt in
        r)
            remote_server=$OPTARG
            ;;
        l)
            lang=$OPTARG
            ;;
        t)
            timeout=$OPTARG
            ;;
        p)
            parallel_limit=$OPTARG
            ;;
        w)
            website_limit=$OPTARG
            ;;
        d)
            date=$OPTARG
            ;;
        *)
            echo "Usage: $0 [-d <date>] [-l <lang>] [-r <remote_location>] [-t <timeout>] [-p <parallel_max>] [-w <websites>]";
            exit 1
            ;;
    esac
done

# Add date suffix
OUTPUTS_FOLDER="$OUTPUTS_FOLDER-$date"

# Add location suffix if set
if [ -n "$remote_server" ]; then
    OUTPUTS_FOLDER="$OUTPUTS_FOLDER-$remote_server"
fi

# Create output folders
mkdir -p $OUTPUTS_FOLDER/priv-accept
mkdir -p $OUTPUTS_FOLDER/analyze-topics

if [ ! -f "$OUTPUTS_FOLDER/top-1m.csv" ]; then
    echo "DOWNLOADING LATEST TRANCO LIST..."

    # Download latest tranco list
    wget https://tranco-list.eu/top-1m.csv.zip -O $OUTPUTS_FOLDER/top-1m.csv.zip -q --show-progress
    unzip $OUTPUTS_FOLDER/top-1m.csv.zip -d $OUTPUTS_FOLDER
    rm $OUTPUTS_FOLDER/top-1m.csv.zip
fi

if [ ! -f "$OUTPUTS_FOLDER/allowed_domains.txt" ]; then
    echo "EXTRACTING ALLOWED DOMAINS..."

    # Download allowed domains
    # Step 1: Delete config files
    rm -rf $CHROME_CONFIG_FOLDER
    # Step 2: Open Chrome, wait until config folders have been created, then close Chrome
    run_chrome
    echo "Waiting for config folder creation..."
    until ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded" > /dev/null 2>&1; do sleep 5; done
    kill_chrome
    # Step 3: Open Chrome again, wait until the latest version of the list has been downloaded, then close Chrome
    run_chrome
    echo "Waiting for allow-list download (may take a couple minutes)..."
    until ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded" | grep -E "[0-9]" > /dev/null 2>&1; do sleep 5; done
    kill_chrome
    # Step 4: Copy the list to the outputs folder
    folder=$(ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded" -1 | head -n 1)
    cp $CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded/$folder/privacy-sandbox-attestations.dat $OUTPUTS_FOLDER

    # Extract allowed domains from sandbox attestations list
    docker run --rm \
        -v $OUTPUTS_FOLDER/privacy-sandbox-attestations.dat:/opt/extract-allowed-domains/privacy-sandbox-attestations.dat \
        salb98/extract-allowed-domains /opt/extract-allowed-domains/privacy-sandbox-attestations.dat \
        > $OUTPUTS_FOLDER/allowed_domains.txt
fi

if [ -n "$remote_server" ]; then
    # Create ExpressVPN Docker container
    docker run -d \
        --rm \
        --name expressvpn-$remote_server \
        --env ACTIVATION_CODE=$EXPRESSVPN_ACTIVATION_CODE \
        --env SERVER=$remote_server \
        --cap-add NET_ADMIN \
        --device /dev/net/tun \
        --tty \
        --privileged \
        --volume vpn-shared:/vpn_shared \
        polkaned/expressvpn \
        /bin/bash -c "cp /etc/resolv.conf /vpn_shared/resolv.conf && sleep infinity"
    network="container:expressvpn-$remote_server"
fi

# Auto-kill docker containers after 1 hour of execution
docker_auto_kill &
docker_auto_kill_pid=$!

# Run priv-accept
echo "RUNNING CRAWLER..."
head -n $website_limit $OUTPUTS_FOLDER/top-1m.csv |
cut -d "," -f2 | sed -e "s/\r//g" |
parallel --load 80% \
    --resume \
    --jobs $parallel_limit \
    --joblog $OUTPUTS_FOLDER/priv-accept-topics.log \
    --results $OUTPUTS_FOLDER/priv-accept-logs \
    --progress --bar --eta \
    "
        timeout -s KILL $PRIV_ACCEPT_TIMEOUT \
            docker run --rm \
            --name priv-accept-{}-$date-${remote_server:-it} \
            --network "${network:=bridge}" \
            -v $OUTPUTS_FOLDER/priv-accept:/opt/priv-accept-topics/output \
            -v vpn-shared:/vpn_shared \
            salb98/priv-accept-topics:geo \
            --url {} \
            --outfile /opt/priv-accept-topics/output/output_{}.json \
            --timeout $timeout \
            --clear_cache --full_net_log --lang \"$lang\" --xvfb \
            --rum_speed_index
    "

# Terminate docker_auto_kill process
kill $docker_auto_kill_pid

# Prepend sequence numbers to priv-accept output files
echo "Adding sequence number to crawler output files..."
head -n $website_limit $OUTPUTS_FOLDER/top-1m.csv |
sed -e "s/\r//g" |
while IFS=, read -r seq domain; do
    [ -f "$OUTPUTS_FOLDER/priv-accept/output_${domain}.json" ] &&
    mv $OUTPUTS_FOLDER/priv-accept/output_${domain}.json $OUTPUTS_FOLDER/priv-accept/$(printf "%07d" $seq)_output_${domain}.json;
done

if [ ! -f "$OUTPUTS_FOLDER/connected_domains.txt" ]; then
    echo "EXTRACTING CONTACTED DOMAINS..."

    # Run extract-domains
    ls -1 $OUTPUTS_FOLDER/priv-accept |
    parallel --load 80% \
        --progress --bar --eta \
        "python3 $WORKING_FOLDER/analyze-topics-api/extract-domains.py $OUTPUTS_FOLDER/priv-accept/{}" 2> $OUTPUTS_FOLDER/extract-domains.stderr |
        sort | uniq > $OUTPUTS_FOLDER/connected_domains.txt
fi

if [ ! -f "$OUTPUTS_FOLDER/allowed_attested.csv" ]; then
    # Attest allowed domains
    echo "EXTRACTING ATTESTED AND ALLOWED DOMAINS..."
    echo "domain,attestation_result" > $OUTPUTS_FOLDER/allowed_attested.csv
    cat $OUTPUTS_FOLDER/allowed_domains.txt |
    parallel --load 80% \
        --progress --bar --eta \
        "python3 $WORKING_FOLDER/analyze-topics-api/attest-domain.py {}" >> $OUTPUTS_FOLDER/allowed_attested.csv
fi

if [ ! -f "$OUTPUTS_FOLDER/attested_domains.csv" ]; then
    # Attest domains found during the crawling
    echo "EXTRACTING ATTESTED AND CONTACTED DOMAINS..."
    echo "domain,attestation_result" > $OUTPUTS_FOLDER/attested_domains.csv
    
    cat $OUTPUTS_FOLDER/connected_domains.txt |
    parallel --load 80% \
        --progress --bar --eta \
        "python3 $WORKING_FOLDER/analyze-topics-api/attest-domain.py {}" >> $OUTPUTS_FOLDER/attested_domains.csv
fi

# Run analyze-topics
echo "EXTRACTING TOPICS API DATA FROM CRAWLER OUTPUTS..."
ls -1 $OUTPUTS_FOLDER/priv-accept | parallel --load 80% --resume --joblog $OUTPUTS_FOLDER/analyze-topics.log --results $OUTPUTS_FOLDER/analyze-topics-logs --progress --bar --eta "python3 $WORKING_FOLDER/analyze-topics-api/analyze-topics-api.py $OUTPUTS_FOLDER/priv-accept/{} --attested_domains_file $OUTPUTS_FOLDER/attested_domains.csv --allowed_domains_file $OUTPUTS_FOLDER/allowed_domains.txt --consent_managers_file $WORKING_FOLDER/analyze-topics-api/consent-managers.txt --outfile $OUTPUTS_FOLDER/analyze-topics/{}"

if [ -n "$remote_server" ]; then
    # Stop VPN container
    docker stop expressvpn-$remote_server
    final_output_prefix="-$remote_server"
fi

if [ ! -f "$OUTPUTS_FOLDER/analyze-topics-output.csv" ]; then
    echo "Condensing outputs into CSV file..."
    
    # Condense all JSON output files into a single CSV file
    cd $OUTPUTS_FOLDER/analyze-topics
    echo 'domain,first_attested_domains,first_allowed_domains,first_topics_api_usages,first_consent_managers,first_has_gtm,banner_clicked,second_attested_domains,second_allowed_domains,second_topics_api_usages,second_consent_managers,second_has_gtm' > $OUTPUTS_FOLDER/analyze-topics-output.csv
    jq -r '[.url, (.first.attested_domains | tostring), (.first.allowed_domains | tostring), (.first.topics_api_usages | tostring), (.first.consent_managers | tostring), (.first.has_gtm), .banner_clicked, (.second.attested_domains | tostring), (.second.allowed_domains | tostring), (.second.topics_api_usages | tostring), (.second.consent_managers | tostring), (.second.has_gtm)] | @csv' *.json >> $OUTPUTS_FOLDER/analyze-topics-output.csv
    cd $cwd
fi

mkdir -p $FINAL_OUTPUTS_FOLDER

if [ ! -f "$FINAL_OUTPUTS_FOLDER/output-$date$final_output_prefix.zip" ]; then
    echo "Creating final output..."

    # Zip important files into final output
    zip -j $FINAL_OUTPUTS_FOLDER/output-$date$final_output_prefix.zip $OUTPUTS_FOLDER/connected_domains.txt $OUTPUTS_FOLDER/attested_domains.csv $OUTPUTS_FOLDER/allowed_domains.txt $OUTPUTS_FOLDER/allowed_attested.csv $OUTPUTS_FOLDER/analyze-topics-output.csv
    
    # Final cleanup
    # rm -rf $OUTPUTS_FOLDER
fi
