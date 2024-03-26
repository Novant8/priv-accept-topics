FROM python:3.11.8

RUN mkdir /opt/analyze-topics-api
ADD analyze-topics-api.py /opt/analyze-topics-api

ADD requirements.txt /opt/analyze-topics-api
RUN pip install -r /opt/analyze-topics-api/requirements.txt

ENTRYPOINT [ "python", "/opt/analyze-topics-api/analyze-topics-api.py" ]