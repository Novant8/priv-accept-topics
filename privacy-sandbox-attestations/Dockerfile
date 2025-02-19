# Stage 1: Generate Protobuf library for Python
FROM buildpack-deps:bookworm as base

RUN apt-get update && apt-get install --no-install-recommends --assume-yes protobuf-compiler

RUN mkdir /opt/extract-allowed-domains
ADD privacy_sandbox_attestations.proto /opt/extract-allowed-domains

RUN protoc /opt/extract-allowed-domains/privacy_sandbox_attestations.proto --proto_path /opt/extract-allowed-domains --python_out /opt/extract-allowed-domains

# Stage 2: Final image, copy Python script and generated protobuf library
FROM python:3.11.8 as final

RUN mkdir /opt/extract-allowed-domains
COPY --from=base /opt/extract-allowed-domains/privacy_sandbox_attestations_pb2.py /opt/extract-allowed-domains
ADD extract_allowed_domains.py /opt/extract-allowed-domains
ADD get_domain.py /opt/extract-allowed-domains

ADD requirements.txt /opt/extract-allowed-domains
RUN pip3 install -r /opt/extract-allowed-domains/requirements.txt

WORKDIR /opt/extract-allowed-domains
ENTRYPOINT [ "python3", "extract_allowed_domains.py" ]