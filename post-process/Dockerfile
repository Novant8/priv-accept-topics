FROM python:3.11-slim

RUN apt update && apt install -y jq

COPY *.py *.jq entrypoint.sh requirements.txt /opt/priv-accept-post-process/
COPY modules /opt/priv-accept-post-process/modules

RUN pip install -r /opt/priv-accept-post-process/requirements.txt

WORKDIR /opt/priv-accept-post-process
ENTRYPOINT [ "bash", "entrypoint.sh" ]