# Build with:
# docker build . --tag <user>/priv-accept
# Push with:
# docker push <user>/priv-accept

FROM sitespeedio/browsertime:11.6.3
LABEL maintainer="Priv Accept Team"

RUN mkdir /opt/priv-accept

ADD requirements.txt /opt/priv-accept
RUN pip3 install -r /opt/priv-accept/requirements.txt

# Add custom Chromium browser
ADD ./chromium /opt/chromium-topics

ADD priv-accept.py /opt/priv-accept
ADD accept_words.txt /root/
ADD rum-speedindex.js /root/

WORKDIR /root/
ENTRYPOINT ["/opt/priv-accept/priv-accept.py", "--chrome_driver", "/opt/chromium-topics/chromedriver", "--chrome_binary", "/opt/chromium-topics/chrome", "--docker", "--detect_topics" ]
