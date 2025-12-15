#!/bin/bash

# Exit script on any command error
set -e

VERSION="2.0-beta1"
TODAY=$(date +%Y%m%d) # YYYYMMDD

# Customize these constants to your liking
WORKING_FOLDER="/home/$USER/priv-accept-ps"
OUTPUTS_FOLDER="$WORKING_FOLDER/outputs"
FINAL_OUTPUTS_FOLDER="$WORKING_FOLDER/outputs"
PRIV_ACCEPT_TIMEOUT="20m"
EXPRESSVPN_ACTIVATION_CODE="CHANGE_ME"

docker_auto_kill() {
    # Auto-kill docker containers that run for more than 1 hour (assume that they are stuck)
    while true; do
        docker stop $(docker ps --filter "ancestor=$1" --format "{{ .ID }} {{ .RunningFor }}" | awk "{if (\$0 ~ /hour/) print \$1}") > /dev/null 2>&1
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
while getopts ":r:l:t:p:w:d:c" opt; do
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
        c)
            # Do nothing
            ;;
        *)
            echo "Usage: $0 [-d <date>] [-l <lang>] [-r <remote_location>] [-t <timeout>] [-p <parallel_max>] [-w <websites>] [-c]";
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
mkdir -p $OUTPUTS_FOLDER/priv-accept/accept
mkdir -p $OUTPUTS_FOLDER/priv-accept/deny

if [ ! -f "$OUTPUTS_FOLDER/top-1m.csv" ]; then
    echo "DOWNLOADING LATEST TRANCO LIST..."

    # Download latest tranco list
    wget https://tranco-list.eu/top-1m.csv.zip -O $OUTPUTS_FOLDER/top-1m.csv.zip -q --show-progress
    unzip $OUTPUTS_FOLDER/top-1m.csv.zip -d $OUTPUTS_FOLDER
    rm $OUTPUTS_FOLDER/top-1m.csv.zip
fi

if [ ! -f "$OUTPUTS_FOLDER/allowed_domains.csv" ]; then
    echo "EXTRACTING ALLOWED DOMAINS..."
    docker run --rm \
        -v "$OUTPUTS_FOLDER":/opt/extract-allowed-domains/output \
        salb98/extract-allowed-domains:$VERSION \
        --output /opt/extract-allowed-domains/output/allowed_domains.csv
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
docker_auto_kill salb98/priv-accept-ps:$VERSION &
docker_auto_kill_pid=$!

echo "RUNNING CRAWLER..."
head -n $website_limit "$OUTPUTS_FOLDER/top-1m.csv" |
sed -e "s/\r//g" |
xargs -I {} echo -e "{},accept\n{},deny" |
parallel --load 80% \
    --resume \
    --retries 3 \
    --jobs $parallel_limit \
    --joblog "$OUTPUTS_FOLDER/priv-accept-ps.log" \
    --results "$OUTPUTS_FOLDER/priv-accept-logs" \
    --progress --bar --eta \
    --colsep=',' \
    "
        timeout -s KILL $PRIV_ACCEPT_TIMEOUT \
            docker run --rm \
            --name priv-accept-{2}-{3}-$date-${remote_server:-it} \
            --network "${network:=bridge}" \
            -v "$OUTPUTS_FOLDER"/priv-accept/{3}:/opt/priv-accept-ps/output \
            -v vpn-shared:/vpn_shared \
            salb98/priv-accept-ps:$VERSION \
            --url {2} \
            --outfile /opt/priv-accept-ps/output/\$(printf %05d {1})_output_{2}.json \
            --timeout $timeout \
            --clear_cache --lang \"$lang\" --xvfb \
            --rum_speed_index \
            --chrome_extra_option="disable-features=TrackingProtection3pcd" \
            --pretty_print \
            \$( if [ {3} = 'deny' ]; then echo '--deny'; fi )
    "

# Terminate docker_auto_kill process
kill $docker_auto_kill_pid || true

# Auto-kill docker containers after 1 hour of execution
docker_auto_kill salb98/priv-accept-post-process:$VERSION &
docker_auto_kill_pid=$!

if [ ! -f "$OUTPUTS_FOLDER/allowed_attested.csv" ]; then
    # Attest allowed domains
    echo "EXTRACTING ATTESTED AND ALLOWED DOMAINS..."
    echo "domain,attestation_result" > "$OUTPUTS_FOLDER/allowed_attested.csv"
    cat "$OUTPUTS_FOLDER/allowed_domains.csv" |
    cut -d, -f1 |
    parallel --load 80% \
        --progress --bar --eta \
        "docker run --rm salb98/priv-accept-post-process:$VERSION attest-domain {}" >> "$OUTPUTS_FOLDER/allowed_attested.csv"
fi

if [ ! -f "$OUTPUTS_FOLDER/attested_domains.csv" ]; then
    # Attest domains found during the crawling
    echo "EXTRACTING ATTESTED AND CONTACTED DOMAINS..."
    echo "domain,attestation_result" > "$OUTPUTS_FOLDER/attested_domains.csv"
    
    visits_json='["first","second"]'

    # Extract unique second-level domains of websites contacted across the entire campaign.
    find "$OUTPUTS_FOLDER/priv-accept/accept" "$OUTPUTS_FOLDER/priv-accept/deny" -type f |
    awk -F/ '{print $(NF-1) "/" $NF}' | # Crop path to "(accept|deny)/filename"
    parallel --load 80% \
        --progress --bar --eta \
        "
            docker run \
            --rm \
            -v "$OUTPUTS_FOLDER/priv-accept":/var/data:ro \
            salb98/priv-accept-post-process:$VERSION extract-contacted-2ld \
            -r \
            --argjson visits '$visits_json' \
            --arg full_net_log 0 \
            --arg separate 0 \
            /var/data/{}
        " |

    # For each extracted domain, check for its attestation file.
    sort | uniq |
    parallel --load 80% \
        --progress --bar --eta \
        "docker run --rm salb98/priv-accept-post-process:$VERSION attest-domain {}" \
        >> $OUTPUTS_FOLDER/attested_domains.csv
fi

# Terminate docker_auto_kill process
kill $docker_auto_kill_pid || true

if [ -n "$remote_server" ]; then
    # Stop VPN container
    docker stop expressvpn-$remote_server
    final_output_suffix="-$remote_server"
fi

if [ ! -f "$OUTPUTS_FOLDER/crawler_outputs.csv" ]; then
    echo "GENERATING FINAL OUTPUT FILE..."

    # Generate header: cartesian product between visits and fields
    visits=(first second)
    fields=(contacted_domains api_calls cookies)
    old_ifs=$IFS
    IFS=,
    csv_fields=$(eval "echo "position website {"${visits[*]}"}_{"${fields[*]}"}"")
    IFS=$old_ifs
    csv_header=$(echo $csv_fields | sed "s/\s/,/g")

    # Convert bash array to JSON
    visits_json='["'"$(printf '%s","' "${visits[@]}" | sed 's/,"$//')"']'
    fields_json='["'"$(printf '%s","' "${fields[@]}" | sed 's/,"$//')"']'
    
    # Create two CSV files: one for accept, one for deny
    for action in accept deny; do
        if [ ! -f "$OUTPUTS_FOLDER/crawler_outputs_$action.csv" ]; then
            echo "Condensing crawler outputs into CSV file ($action)..."
            echo $csv_header > "$OUTPUTS_FOLDER/crawler_outputs_$action.csv"

            find "$OUTPUTS_FOLDER/priv-accept/$action" -type f |
            xargs basename -a |
            sort | # Linux find does not sort by default
            parallel --load 80% \
                --progress --bar --eta \
                --keep-order \
                "
                    docker run \
                    --rm \
                    -v "$OUTPUTS_FOLDER/priv-accept/$action":/var/data:ro \
                    salb98/priv-accept-post-process:$VERSION post-process-output \
                    --argjson visits '$visits_json' \
                    --argjson fields '$fields_json' \
                    --arg position \"\$(echo {} | cut -d_ -f1)\" \
                    --arg full_net_log 0 \
                    --arg csv_format 1 \
                    /var/data/{}
                " >> "$OUTPUTS_FOLDER/crawler_outputs_$action.csv"
        fi
    done

    # Merge CSV files into one
    echo "Merging CSV files..."
    docker run \
        --rm \
        -v "$OUTPUTS_FOLDER":/var/data:rw \
        salb98/priv-accept-post-process:$VERSION \
        merge-csv \
        /var/data/crawler_outputs_accept.csv \
        /var/data/crawler_outputs_deny.csv \
        --join_type outer \
        --join_on position website \
        --suffix1 _accept \
        --suffix2 _deny \
        --sorted \
        --output /var/data/crawler_outputs.csv
fi

mkdir -p $FINAL_OUTPUTS_FOLDER

if [ ! -f "$FINAL_OUTPUTS_FOLDER/output-$date$final_output_suffix.zip" ]; then
    echo "Creating final output..."

    # Zip important files into final output
    zip -j $FINAL_OUTPUTS_FOLDER/outputs-$date$final_output_suffix.zip $OUTPUTS_FOLDER/attested_domains.csv $OUTPUTS_FOLDER/allowed_domains.csv $OUTPUTS_FOLDER/allowed_attested.csv $OUTPUTS_FOLDER/crawler_outputs.csv
fi

echo "Done!"