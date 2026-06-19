ARG VERSION="latest"
ARG PYTHON_VERSION="3.13"

FROM extract-allowed-domains:${VERSION} AS extract-allowed

FROM priv-accept-ps:${VERSION} AS crawler

FROM priv-accept-post-process:${VERSION} AS post-process

FROM python:${PYTHON_VERSION}-slim AS runner

ARG PYTHON_VERSION

# Install xargs and jq
RUN apt-get update && apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 libgbm1 libxkbcommon0 libpango1.0-dev libcairo2 libxrender1 libcap2 libgcrypt20 liblzma5 libzstd1 liblz4-1 libblkid1 libgpg-error0 libmd0 xvfb libc6 libgtk-3-0 libstdc++6 xorg

RUN mkdir -p /opt/priv-accept-ps

# Copy crawler, post-process and allowed domain extraction files
COPY --from=extract-allowed /opt/extract-allowed-domains /opt/priv-accept-ps/extract-allowed-domains
COPY --from=crawler /opt/priv-accept /root/* /opt/priv-accept-ps/crawler/
COPY --from=crawler /opt/google-chrome /opt/google-chrome
COPY --from=post-process /opt/priv-accept-post-process /opt/priv-accept-post-process/modules /opt/priv-accept-ps/post-process/
COPY ./analyze-ps-single.sh /opt/priv-accept-ps/analyze-ps.sh

RUN pip install -r /opt/priv-accept-ps/extract-allowed-domains/requirements.txt -r /opt/priv-accept-ps/crawler/requirements.txt -r /opt/priv-accept-ps/post-process/requirements.txt

# Copy devtools patch
COPY --from=crawler /usr/local/lib/python${PYTHON_VERSION}/site-packages/selenium/webdriver/common/devtools /usr/local/lib/python${PYTHON_VERSION}/site-packages/selenium/webdriver/common/devtools

WORKDIR /opt/priv-accept-ps

ENTRYPOINT [ "bash", "analyze-ps.sh" ]