FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY halberd/ halberd/

RUN pip install --no-cache-dir ".[server]"

ENV HALBERD_DATA_DIR=/data

EXPOSE 8000

VOLUME ["/data"]

ENTRYPOINT ["halberd"]
CMD ["server", "--host", "0.0.0.0", "--port", "8000"]
