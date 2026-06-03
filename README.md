# 自働仮想マシン払い出しシステム

htmx + FastAPI の Web UI、RustFS 上の IaC 成果物、Terraform / Ansible パイプライン、ローカル向けクラウド／ハイパーバイザエミュレータを組み合わせた開発用雛形です。

> **用語**: ご指定の「floti / floti-az」は [Floci](https://floci.io/) / [Floci-az](https://github.com/floci-io/floci-az) を指す想定で、compose 上のサービス名は `floci` / `floci-az` です。

## アーキテクチャ

```mermaid
flowchart LR
  UI[htmx + FastAPI :8000]
  PG[(PostgreSQL)]
  RF[RustFS S3 :9000]
  EV[rustfs-events poller]
  WK[Worker :9002]
  FL[Floci AWS :4566]
  AZ[Floci-az Azure :4577]
  PVE[mock-pve Proxmox :8006]
  VS[vcsim vSphere :8989]

  UI --> PG
  UI --> RF
  RF --> EV
  EV -->|webhook| WK
  WK -->|terraform apply| FL
  WK -->|terraform apply| AZ
  WK -->|terraform apply| PVE
  WK -->|terraform apply| VS
  WK -->|ansible-playbook| WK
```

### コンポーネント

| 役割 | 技術 | ポート |
|------|------|--------|
| 画面・API | FastAPI + htmx + Jinja2 | 8000 |
| 状態管理 | PostgreSQL | 5432 |
| IaC ストア | RustFS (S3 互換) | 9000 / 9001 |
| 変更検知 | rustfs-events (ポーリング) | — |
| 払い出し実行 | worker (Terraform + Ansible) | 9002 |
| クラウド（AWS） | Floci | 4566 |
| クラウド（Azure） | Floci-az | 4577 |
| ハイパーバイザ（VMware） | vcsim | 8989 |
| ハイパーバイザ（Proxmox） | mock-pve-api | 8006 |

### 仮想マシン管理（実装済み）

Web UI **仮想マシン** (`/vms`) から以下を操作できます。

| 機能 | Proxmox (mock-pve) | vSphere (vcsim) | AWS EC2 (Floci) |
|------|-------------------|-----------------|-----------------|
| 起動状態表示 | ○ | ○ | ○ |
| 電源 ON/OFF・再起動 | ○ | ○ | ○ |
| CPU / メモリ変更 | ○ (cores/memory) | ○ (ReconfigVM) | ○ (instance type) |
| ディスク変更 | ○ (resize API) | ○ (仮想ディスク容量) | ○ (EBS modify_volume) |

API: `GET/POST /api/vms/...` — 詳細はアプリ起動後の `/docs` を参照。

### DevOps フロー

1. Web UI で **プロジェクト** を作成 → RustFS プレフィックスが発行される
2. `projects/terraform/{id}/` に `.tf` をアップロード → worker が Terraform apply
3. `projects/ansible/{id}/` に playbook を配置 → Ansible で構築後設定
4. 実行ログは worker コンテナ内 `/tmp/pipeline-runs`（将来 DB 連携）

## ディレクトリ構成

```
vm_work/
├── .devcontainer/          # VS Code / Cursor Dev Container
├── app/                    # FastAPI + htmx
├── worker/                 # パイプライン worker
├── infra/
│   ├── terraform/environments/local/
│   └── ansible/
├── docker/                 # 各サービス Dockerfile
├── scripts/init-rustfs.sh
├── docker-compose.yml
└── pyproject.toml
```

## クイックスタート

### 1. 環境ファイル

```bash
cp .env.example .env
```

### 2. スタック起動

```bash
docker compose up -d --build
```

### 3. RustFS バケット初期化

```bash
docker compose exec dev bash scripts/init-rustfs.sh
# またはホストから aws cli で .env のエンドポイントへ
```

### 4. アクセス

- Web UI: http://localhost:8000
- VM 管理: http://localhost:8000/vms
- RustFS Console: http://localhost:9001
- Floci (AWS): http://localhost:4566
- Floci-az (Azure): http://localhost:4577
- mock-pve (Proxmox API): https://localhost:8006
- vcsim: https://localhost:8989/sdk

疎通確認: `bash scripts/verify-emulators.sh`

## Dev Container

1. Cursor / VS Code で **Reopen in Container**
2. `postCreateCommand` で Python 依存と `.env` を準備
3. 開発コンテナ内に Terraform / Ansible CLI 済み

`docker-compose.devcontainer.yml` の `dev` サービスがメイン。フルスタックは compose プロファイル `full` で app / worker を追加可能。

## ローカルエミュレータ設定

### Floci (AWS)

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

Terraform の `infra/terraform/environments/local` は `aws_endpoint` / vSphere provider をローカル向けに設定済みです。

### Floci-az (Azure)

Blob / Queue / Table / Functions はすべて **4577** で提供されます（Azurite 互換アカウント `devstoreaccount1`）。

```bash
export AZURE_BLOB_ENDPOINT=http://localhost:4577/devstoreaccount1
export AZURE_STORAGE_ACCOUNT=devstoreaccount1
# キーは .env.example の AZURE_STORAGE_KEY を参照
```

Azure Functions を使う場合は Docker ソケットのマウントが必須です（`docker-compose.yml` 済み）。

詳細: `infra/terraform/modules/azure/README.md`

### mock-pve (Proxmox)

[mock-pve-api](https://github.com/jrjsmrtn/mock-pve-api) は PVE 8.x REST API の軽量シミュレータです。初期ノード `pve-node1` / `pve-node2` が含まれます。

```bash
curl -k https://localhost:8006/api2/json/version

# 認証例
curl -k -X POST https://localhost:8006/api2/json/access/ticket \
  -d "username=root@pam&password=secret"
```

Terraform 向けメモ: `infra/terraform/modules/proxmox/README.md`

> **フル Proxmox クラスタ**（KVM/LXC 実動）が必要な場合は [containerized-proxmox](https://github.com/LongQT-sea/containerized-proxmox) 等の別スタックを検討してください。本雛形は API 統合テスト向けに mock-pve を採用しています。

### vcsim (VMware)

```bash
export GOVC_URL=https://user:pass@localhost:8989/sdk
export GOVC_INSECURE=1
```

インベントリ名（`DC0`, `LocalDS_0` 等）は vcsim デフォルトモデルに合わせています。ホスト数を変える場合は `docker-compose.yml` の `vcsim` コマンド引数を調整してください。

## 次の実装ステップ（推奨）

- [ ] worker → FastAPI へ run 状態を POST（`ProvisionRun` 連携）
- [ ] RustFS ネイティブイベント通知で poller を置き換え
- [ ] プロジェクトごとの Terraform state を S3 backend（RustFS）へ
- [ ] 認証（OIDC / 社内 IdP）
- [ ] Floci-gcp を compose に追加
- [ ] Proxmox / Azure 向け Terraform モジュールを worker パイプラインに統合

## ライセンス

社内利用を想定した雛形です。Floci / Floci-az / mock-pve-api / vcsim / RustFS は各プロジェクトのライセンスに従ってください。
