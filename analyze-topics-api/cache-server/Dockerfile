FROM python:3.11.8

RUN mkdir /opt/cache-server
ADD cache-server.py /opt/cache-server

ENTRYPOINT [ "python", "/opt/cache-server/cache-server.py" ]