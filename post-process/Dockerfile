FROM python:3.11-slim

RUN apt update && apt install -y jq

RUN mkdir /opt/priv-accept-post-process
ADD *.py *.jq modules/ entrypoint.sh requirements.txt /opt/priv-accept-post-process/

RUN pip install -r /opt/priv-accept-post-process/requirements.txt

WORKDIR /opt/priv-accept-post-process
ENTRYPOINT [ "bash", "entrypoint.sh" ]