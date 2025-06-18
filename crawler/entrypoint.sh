#!/bin/sh
if [ -f "/vpn_shared/resolv.conf" ]; then
    cp /vpn_shared/resolv.conf /etc/resolv.conf
fi

python3 /opt/priv-accept/priv-accept.py \
    --chrome_driver /opt/google-chrome/chromedriver \
    --chrome_binary /opt/google-chrome/chrome \
    --docker \
    "$@" # Pass all arguments of this bash script