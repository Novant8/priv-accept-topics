cp /vpn_shared/resolv.conf /etc/resolv.conf
python /opt/priv-accept/priv-accept.py \
    --chrome_driver /opt/chromium-topics/chromedriver \
    --chrome_binary /opt/chromium-topics/chrome \
    --docker --detect_topics \
    "$@" # Pass all arguments of this bash script