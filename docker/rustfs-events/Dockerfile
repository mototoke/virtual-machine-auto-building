FROM python:3.12-slim-bookworm

WORKDIR /app
COPY docker/rustfs-events/poller.py ./poller.py

RUN pip install --no-cache-dir boto3 httpx

CMD ["python", "poller.py"]
