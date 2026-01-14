# Build with:
# docker build . --tag <user>/priv-accept
# Push with:
# docker push <user>/priv-accept

ARG PYTHON_VERSION="3.13"
ARG CHROME_VERSION="138.0.7204.4"
ARG DEVTOOLS_VERSION="138"
ARG FIREFOX_VERSION="146.0.1"
ARG GECKODRIVER_VERSION="v0.36.0"

FROM alpine/curl:latest AS downloader
ARG CHROME_VERSION
ARG FIREFOX_VERSION
ARG GECKODRIVER_VERSION

# Download Chrome browser, WITHOUT Privacy Sandbox Attestations
RUN wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip -d /opt/google-chrome \
    && rm -r /opt/google-chrome/chrome-linux64/PrivacySandboxAttestationsPreloaded \
    && rm chrome-linux64.zip

# Download Chromedriver
RUN wget https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip -d /opt/google-chrome \
    && rm chromedriver-linux64.zip

# Download Firefox (linux64) and extract
RUN wget https://ftp.mozilla.org/pub/firefox/releases/${FIREFOX_VERSION}/linux-x86_64/en-US/firefox-${FIREFOX_VERSION}.tar.xz \
    && mkdir -p /opt/firefox \
    && tar -xJf firefox-${FIREFOX_VERSION}.tar.xz -C /opt \
    && rm firefox-${FIREFOX_VERSION}.tar.xz

# Download geckodriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz \
    && tar -xzf geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz -C /opt/firefox \
    && rm geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz

FROM python:${PYTHON_VERSION} AS devtools-builder
ARG CHROME_VERSION
ARG DEVTOOLS_VERSION

COPY ./devtools/*.py /build/devtools/
COPY ./devtools/requirements.txt /build/devtools/
RUN pip install -r /build/devtools/requirements.txt

# Download browser_protocol.pdl and convert to JSON
RUN curl -sSL https://raw.githubusercontent.com/chromium/chromium/${CHROME_VERSION}/third_party/blink/public/devtools_protocol/browser_protocol.pdl \
    > /tmp/browser_protocol.pdl \
    && python3 /build/devtools/convert_protocol_to_json.py /tmp/browser_protocol.pdl /tmp/browser_protocol.json --map_binary_to_string=true

# Download js_protocol.pdl and convert to JSON
RUN v8_revision=$(curl -sSL https://raw.githubusercontent.com/chromium/chromium/refs/tags/${CHROME_VERSION}/DEPS | grep "'v8_revision':" | sed -E "s/.*'([^']+)'[, ]*/\1/") \
    && curl -sSL https://github.com/v8/v8/raw/${v8_revision}/include/js_protocol.pdl > /tmp/js_protocol.pdl \
    && python3 /build/devtools/convert_protocol_to_json.py /tmp/js_protocol.pdl /tmp/js_protocol.json --map_binary_to_string=true

# Generate devtools bindings
RUN rm -rf /build/devtools/v${DEVTOOLS_VERSION} \
    && mkdir /build/devtools/v${DEVTOOLS_VERSION} \
    && python3 /build/devtools/generate.py /tmp/browser_protocol.json /tmp/js_protocol.json /build/devtools/v${DEVTOOLS_VERSION}

FROM python:${PYTHON_VERSION}-slim AS runner
LABEL maintainer="Priv Accept Team"
ARG PYTHON_VERSION
ARG DEVTOOLS_VERSION

ENV PYTHONUNBUFFERED=1

# Install package dependencies
RUN apt-get update && apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 libgbm1 libxkbcommon0 libpango1.0-dev libcairo2 libxrender1 libcap2 libgcrypt20 liblzma5 libzstd1 liblz4-1 libblkid1 libgpg-error0 libmd0 libc6 libgtk-3-0 libstdc++6 xorg libdbus-glib-1-2 libasound2 xvfb

RUN mkdir /opt/priv-accept

ADD requirements.txt /opt/priv-accept
RUN pip3 install -r /opt/priv-accept/requirements.txt

# Add devtools bindings to Selenium package folder
COPY --from=devtools-builder /build/devtools/v${DEVTOOLS_VERSION} /usr/local/lib/python${PYTHON_VERSION}/site-packages/selenium/webdriver/common/devtools/v${DEVTOOLS_VERSION}

# Add Chrome browser and Chromedriver
COPY --from=downloader /opt/google-chrome/chrome-linux64 /opt/google-chrome
COPY --from=downloader /opt/google-chrome/chromedriver-linux64/chromedriver /opt/google-chrome

# Add Firefox and Geckodriver
COPY --from=downloader /opt/firefox /opt/firefox
COPY . /opt/priv-accept

RUN chmod +x /opt/priv-accept/entrypoint.sh

WORKDIR /opt/priv-accept
ENTRYPOINT [ "/opt/priv-accept/entrypoint.sh" ]