#!/bin/bash
VERSION="latest"

docker build extract-allowed -t extract-allowed-domains:${VERSION}
docker build crawler -t priv-accept-ps:${VERSION}
docker build post-process -t priv-accept-post-process:${VERSION}
docker build . -t query-privacy-sandbox-usage:${VERSION}