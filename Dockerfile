FROM sitespeedio/browsertime:24.5.0

# Install xargs and jq
RUN apt update && apt install -y findutils jq xvfb

# Add custom version of Chromium
ADD ./crawler/chromium /opt/chromium-topics

# Create workdir
RUN mkdir /opt/priv-accept-topics
ADD crawler/ /opt/priv-accept-topics/crawler
ADD analyze-topics-api/ /opt/priv-accept-topics/analyze-topics-api
ADD analyze-topics-single.sh /opt/priv-accept-topics/analyze-topics.sh

# Install Python libraries
RUN pip install -r /opt/priv-accept-topics/analyze-topics-api/requirements.txt
RUN pip install -r /opt/priv-accept-topics/crawler/requirements.txt

WORKDIR /opt/priv-accept-topics
ENTRYPOINT [ "bash", "/opt/priv-accept-topics/analyze-topics.sh" ]