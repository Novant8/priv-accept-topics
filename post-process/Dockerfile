FROM python:3.11.8

RUN mkdir /opt/analyze-topics-api
ADD . /opt/analyze-topics-api

ADD requirements.txt /opt/analyze-topics-api
RUN pip install -r /opt/analyze-topics-api/requirements.txt

ENTRYPOINT [ "bash", "/opt/analyze-topics-api/entrypoint.sh" ]