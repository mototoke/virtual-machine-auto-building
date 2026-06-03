"""
RustFS (S3) のオブジェクト変更をポーリングし、worker にパイプライン起動を通知する簡易ブリッジ。

本番では RustFS のイベント通知 Webhook を直接 worker に向けることを推奨。
"""
from __future__ import annotations

import hashlib
import os
import time
from urllib.parse import urlparse

import boto3
import httpx

ENDPOINT = os.environ.get("RUSTFS_ENDPOINT", "http://rustfs:9000")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "http://worker:9002/internal/pipeline/trigger")
BUCKET = os.environ.get("RUSTFS_BUCKET_PROJECTS", "vm-projects")
PREFIXES = [
    os.environ.get("RUSTFS_PREFIX_TERRAFORM", "projects/terraform/"),
    os.environ.get("RUSTFS_PREFIX_ANSIBLE", "projects/ansible/"),
]
POLL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", "5"))
ACCESS_KEY = os.environ.get("RUSTFS_ACCESS_KEY", "rustfsadmin")
SECRET_KEY = os.environ.get("RUSTFS_SECRET_KEY", "rustfsadmin")


def _client():
    parsed = urlparse(ENDPOINT)
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
    )


def _etag_state() -> dict[str, str]:
    return {}


def main() -> None:
    s3 = _client()
    state: dict[str, str] = {}
    while True:
        for prefix in PREFIXES:
            resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                etag = obj.get("ETag", "")
                if state.get(key) == etag:
                    continue
                state[key] = etag
                project_id = _project_id_from_key(key)
                payload = {
                    "bucket": BUCKET,
                    "key": key,
                    "etag": etag,
                    "project_id": project_id,
                    "stage": "terraform" if "terraform" in prefix else "ansible",
                }
                try:
                    httpx.post(WEBHOOK_URL, json=payload, timeout=30.0)
                except httpx.HTTPError as exc:
                    print(f"webhook failed for {key}: {exc}")
        time.sleep(POLL_SEC)


def _project_id_from_key(key: str) -> str:
    # projects/terraform/{project_id}/...
    parts = key.strip("/").split("/")
    if len(parts) >= 3:
        return parts[2]
    return hashlib.sha256(key.encode()).hexdigest()[:12]


if __name__ == "__main__":
    main()
