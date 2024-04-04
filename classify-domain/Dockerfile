FROM python:3.11.8

RUN apt update && apt install -y protobuf-compiler libusb-1.0-0-dev
RUN mkdir /opt/classify-domain

ADD ./classify.py /opt/classify-domain
ADD ./requirements.txt /opt/classify-domain

RUN pip install -r /opt/classify-domain/requirements.txt

WORKDIR /opt/classify-domain

ENTRYPOINT [ "python", "classify.py" ]