#!/usr/bin/env bash
# ローカルエミュレータの疎通確認（ホストから実行想定）
set -euo pipefail

echo "== Floci (AWS) =="
curl -sf "http://localhost:4566/_localstack/health" >/dev/null && echo OK || echo FAIL

echo "== Floci-az (Azure) =="
curl -sf "http://localhost:4577/" >/dev/null && echo OK || echo FAIL

echo "== mock-pve (Proxmox) =="
curl -sfk "https://localhost:8006/api2/json/version" | head -c 120 && echo

echo "== vcsim (vSphere) =="
curl -sfk "https://localhost:8989/sdk" >/dev/null && echo OK || echo "SKIP (SOAP endpoint)"

echo "Done."
