# Build with:
# docker build . --tag <user>/priv-accept
# Push with:
# docker push <user>/priv-accept

FROM python:3.13 AS builder

ARG CHROME_VERSION="122.0.6261.128"
ARG DEVTOOLS_VERSION="122"

COPY ./devtools /build/devtools

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
RUN mkdir /build/devtools/v${DEVTOOLS_VERSION} \
    && python3 /build/devtools/generate.py /tmp/browser_protocol.json /tmp/js_protocol.json /build/devtools/v${DEVTOOLS_VERSION}

FROM python:3.13-slim AS runner
LABEL maintainer="Priv Accept Team"

ENV PYTHONUNBUFFERED=1

# Install package dependencies
RUN apt-get update && apt-get install -y libglib2.0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxcomposite1 libxdamage1 libgbm1 libxkbcommon0 libpango1.0-0 libcairo2 libxrender1 libcap2 libgcrypt20 liblzma5 libzstd1 liblz4-1 libblkid1 libgpg-error0 libmd0 xvfb

RUN mkdir /opt/priv-accept

ADD requirements.txt /opt/priv-accept
RUN pip3 install -r /opt/priv-accept/requirements.txt

# Add devtools bindings to Selenium package folder
COPY --from=builder /build/devtools/v*/ /usr/local/lib/python3.14/site-packages/selenium/webdriver/common/devtools/

# Add custom Chromium browser
ADD ./chromium /opt/chromium-topics

ADD *.py /opt/priv-accept
ADD *.js /opt/priv-accept
ADD accept_words.txt /root/
ADD rum-speedindex.js /root/

COPY ./entrypoint.sh /root/
RUN chmod +x /root/entrypoint.sh

WORKDIR /root/
ENTRYPOINT [ "/root/entrypoint.sh" ]