FROM rvolosatovs/protoc AS protoc

WORKDIR /app

COPY ./privacy_sandbox_attestations.proto /app/

RUN protoc --proto_path=/app/ --python_out=/app/ privacy_sandbox_attestations.proto

FROM python:3.13-slim AS runner

WORKDIR /app

COPY ./*.py ./requirements.txt /app/
COPY --from=protoc /app/privacy_sandbox_attestations_pb2.py /app/

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python3", "/app/extract_allowed.py" ]