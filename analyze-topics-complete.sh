#!/bin/bash

TODAY=$(date +%Y%m%d) # YYYYMMDD

# Customize these constants to your liking
WORKING_FOLDER="/home/$USER/priv-accept-topics"
OUTPUTS_FOLDER="$WORKING_FOLDER/outputs-$TODAY"
FINAL_OUTPUTS_FOLDER="$WORKING_FOLDER/outputs"
CHROME_CONFIG_FOLDER="/home/$USER/.config/google-chrome"
WEBSITE_LIMIT=50000
PRIV_ACCEPT_TIMEOUT="20m"

run_chrome() {
    echo "Running Chrome..."
    xvfb-run --auto-servernum google-chrome --disable-gpu &
}

kill_chrome() {
    echo "Killing Chrome..."
    ps -ax | grep "chrome" | cut -d " " -f2 | xargs kill -15
    while ps -ax | grep "chrome"; do sleep 5; done
}

docker_auto_kill() {
    while true; do
        docker stop $(docker ps --filter "ancestor=salb98/priv-accept-topics:latest" --format "{{ .ID }} {{ .RunningFor }}" | awk "{if (\$0 ~ /hour/) print \$1}")
        sleep 10;
    done
}

cwd=$(pwd)

# Create output folders
mkdir -p $OUTPUTS_FOLDER/priv-accept
mkdir -p $OUTPUTS_FOLDER/analyze-topics

if [ ! -f "$OUTPUTS_FOLDER/top-1m.csv" ]; then
    # Download latest tranco list
    wget https://tranco-list.eu/top-1m.csv.zip -O $OUTPUTS_FOLDER/top-1m.csv.zip
    unzip $OUTPUTS_FOLDER/top-1m.csv.zip -d $OUTPUTS_FOLDER
    rm $OUTPUTS_FOLDER/top-1m.csv.zip
fi

if [ ! -f "$OUTPUTS_FOLDER/allowed_domains.txt" ]; then

    # Download allowed domains
    # Step 1: Delete config files
    rm -rf $CHROME_CONFIG_FOLDER
    # Step 2: Open Chrome, wait until config folders have been created, then close Chrome
    run_chrome
    until ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded"; do sleep 5; done
    kill_chrome
    # Step 3: Open Chrome again, wait until the latest version of the list has been downloaded, then close Chrome
    run_chrome
    until ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded" | grep -E "[0-9]"; do sleep 5; done
    kill_chrome
    # Step 4: Copy the list to the outputs folder
    folder=$(ls "$CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded" -1 | head -n 1)
    cp $CHROME_CONFIG_FOLDER/PrivacySandboxAttestationsPreloaded/$folder/privacy-sandbox-attestations.dat $OUTPUTS_FOLDER

    # Extract allowed domains from sandbox attestations list
    docker run --rm -v $OUTPUTS_FOLDER/privacy-sandbox-attestations.dat:/opt/extract-allowed-domains/privacy-sandbox-attestations.dat salb98/extract-allowed-domains /opt/extract-allowed-domains/privacy-sandbox-attestations.dat > $OUTPUTS_FOLDER/allowed_domains.txt
fi

# Auto-kill docker containers after 1 hour of execution
docker_auto_kill &
docker_auto_kill_pid=$!

# Run priv-accept
head -n $WEBSITE_LIMIT $OUTPUTS_FOLDER/top-1m.csv | cut -d "," -f2 | sed -e "s/\r//g" | parallel --load 80% --resume --joblog $OUTPUTS_FOLDER/priv-accept-topics.log "timeout -s KILL $PRIV_ACCEPT_TIMEOUT docker run --name priv-accept-{}-$TODAY --rm -v $OUTPUTS_FOLDER/priv-accept:/opt/priv-accept-topics/output salb98/priv-accept-topics:latest --url {} --outfile /opt/priv-accept-topics/output/output_{}.json --clear_cache --full_net_log --xvfb"

# Terminate docker_auto_kill process
kill $docker_auto_kill_pid

# Prepend sequence numbers to priv-accept output files
head -n $WEBSITE_LIMIT $OUTPUTS_FOLDER/top-1m.csv | sed -e "s/\r//g" | while IFS=, read -r seq domain; do [ -f "$OUTPUTS_FOLDER/priv-accept/output_${domain}.json" ] && mv $OUTPUTS_FOLDER/priv-accept/output_${domain}.json $OUTPUTS_FOLDER/priv-accept/$(printf "%07d" $seq)_output_${domain}.json; done

if [ ! -f "$OUTPUTS_FOLDER/connected_domains.txt" ]; then
    # Run extract-domains
    ls -1 $OUTPUTS_FOLDER/priv-accept | parallel --load 80% "python3 $WORKING_FOLDER/analyze-topics-api/extract-domains.py $OUTPUTS_FOLDER/priv-accept/{}" | sort | uniq > $OUTPUTS_FOLDER/connected_domains.txt
fi

if [ ! -f "$OUTPUTS_FOLDER/attested_domains.csv" ]; then
    # Run attest-domains
    echo "domain,attestation_result" > $OUTPUTS_FOLDER/attested_domains.csv
    cat $OUTPUTS_FOLDER/connected_domains.txt | parallel --load 80% "python3 $WORKING_FOLDER/analyze-topics-api/attest-domain.py {}" >> $OUTPUTS_FOLDER/attested_domains.csv
fi

# Run analyze-topics
ls -1 $OUTPUTS_FOLDER/priv-accept | parallel --load 80% --resume --joblog $OUTPUTS_FOLDER/analyze-topics.log "python3 $WORKING_FOLDER/analyze-topics-api/analyze-topics-api.py $OUTPUTS_FOLDER/priv-accept/{} --attested_domains_file $OUTPUTS_FOLDER/attested_domains.csv --allowed_domains_file $OUTPUTS_FOLDER/allowed_domains.txt --consent_managers_file $WORKING_FOLDER/analyze-topics-api/consent-managers.txt --outfile $OUTPUTS_FOLDER/analyze-topics/{}"

if [ ! -f "$OUTPUTS_FOLDER/analyze-topics-output.csv" ]; then
    # Condense all JSON output files into a single CSV file
    cd $OUTPUTS_FOLDER/analyze-topics
    echo 'domain,first_attested_domains,first_allowed_domains,first_topics_api_usages,first_consent_managers,first_has_gtm,banner_clicked,second_attested_domains,second_allowed_domains,second_topics_api_usages,second_consent_managers,second_has_gtm' > $OUTPUTS_FOLDER/analyze-topics-output.csv
    jq -r '[.url, (.first.attested_domains | tostring), (.first.allowed_domains | tostring), (.first.topics_api_usages | tostring), (.first.consent_managers | tostring), (.first.has_gtm), .banner_clicked, (.second.attested_domains | tostring), (.second.allowed_domains | tostring), (.second.topics_api_usages | tostring), (.second.consent_managers | tostring), (.second.has_gtm)] | @csv' *.json >> $OUTPUTS_FOLDER/analyze-topics-output.csv
    cd $cwd
fi

if [ ! -f "$FINAL_OUTPUTS_FOLDER/output-$TODAY.zip" ]; then
    # Zip important files into final output
    zip -j $FINAL_OUTPUTS_FOLDER/output-$TODAY.zip $OUTPUTS_FOLDER/connected_domains.txt $OUTPUTS_FOLDER/attested_domains.csv $OUTPUTS_FOLDER/allowed_domains.txt $OUTPUTS_FOLDER/analyze-topics-output.csv
    
    # Final cleanup
    rm -rf $OUTPUTS_FOLDER
fi