"""
Terraform → Ansible の順で実行するパイプライン骨格。
実際の provider 設定は infra/terraform/environments/local を編集してください。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import boto3

RUSTFS_ENDPOINT = os.environ.get("RUSTFS_ENDPOINT", "http://rustfs:9000")
ACCESS_KEY = os.environ.get("RUSTFS_ACCESS_KEY", "rustfsadmin")
SECRET_KEY = os.environ.get("RUSTFS_SECRET_KEY", "rustfsadmin")
TERRAFORM_ROOT = Path(os.environ.get("TERRAFORM_DIR", "/workspace/infra/terraform"))
ANSIBLE_ROOT = Path(os.environ.get("ANSIBLE_DIR", "/workspace/infra/ansible"))


def run_pipeline(payload: dict, work_dir: Path, run_id: str) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    project_id = payload["project_id"]
    stage = payload["stage"]
    key = payload["key"]
    bucket = payload["bucket"]

    local_iac = work_dir / "iac"
    local_iac.mkdir(exist_ok=True)
    _sync_prefix(bucket, key, local_iac)

    if stage == "terraform" or _has_terraform_files(local_iac):
        _terraform_apply(local_iac, project_id, run_id)

    if stage == "ansible" or _has_ansible_files(local_iac):
        _ansible_play(local_iac, project_id, run_id)


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=RUSTFS_ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
    )


def _sync_prefix(bucket: str, trigger_key: str, dest: Path) -> None:
    """トリガーキーの親プレフィックスを同期（簡易）。"""
    s3 = _s3()
    parts = trigger_key.strip("/").split("/")
    prefix = "/".join(parts[:3]) + "/" if len(parts) >= 3 else trigger_key
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    for obj in resp.get("Contents", []):
        rel = obj["Key"][len(prefix) :] if obj["Key"].startswith(prefix) else obj["Key"]
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, obj["Key"], str(target))


def _has_terraform_files(path: Path) -> bool:
    return any(path.rglob("*.tf"))


def _has_ansible_files(path: Path) -> bool:
    return any(path.rglob("*.yml")) or any(path.rglob("*.yaml"))


def _terraform_apply(iac_dir: Path, project_id: str, run_id: str) -> None:
    env = os.environ.copy()
    env.setdefault("TF_IN_AUTOMATION", "1")
    env.setdefault("AWS_ENDPOINT_URL", os.environ.get("AWS_ENDPOINT_URL", "http://floci:4566"))
    env.setdefault("AWS_ACCESS_KEY_ID", "test")
    env.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    env.setdefault("AWS_DEFAULT_REGION", "us-east-1")

    module = TERRAFORM_ROOT / "environments" / "local"
    if not module.exists():
        module = iac_dir

    log = iac_dir.parent / f"{run_id}-terraform.log"
    for cmd in [
        ["terraform", "-chdir=" + str(module), "init", "-input=false"],
        ["terraform", "-chdir=" + str(module), "apply", "-auto-approve", "-input=false"],
    ]:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        log.write_text((log.read_text() if log.exists() else "") + result.stdout + result.stderr)
        if result.returncode != 0:
            raise RuntimeError(f"terraform failed for project {project_id}: {result.stderr[:500]}")


def _ansible_play(iac_dir: Path, project_id: str, run_id: str) -> None:
    playbook = next(iac_dir.rglob("playbook.yml"), None) or next(iac_dir.rglob("site.yml"), None)
    if not playbook:
        playbook = ANSIBLE_ROOT / "playbooks" / "site.yml"
    if not playbook.exists():
        return

    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    log = iac_dir.parent / f"{run_id}-ansible.log"
    cmd = [
        "ansible-playbook",
        str(playbook),
        "-i",
        str(ANSIBLE_ROOT / "inventories" / "local"),
        "-e",
        f"project_id={project_id}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(playbook.parent))
    log.write_text(result.stdout + result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"ansible failed for project {project_id}")
