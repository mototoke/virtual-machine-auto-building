# Proxmox (mock-pve-api) 向け Terraform

ローカルでは `mock-pve` サービス（`https://mock-pve:8006`）をエンドポイントにします。

```hcl
provider "proxmox" {
  pm_api_url      = "https://mock-pve:8006/api2/json"
  pm_user         = "root@pam"
  pm_password     = "secret"
  pm_tls_insecure = true
}
```

`telmate/proxmox` 等の provider を利用する場合、API トークンは `.env` の `PROXMOX_API_TOKEN` を参照してください。

> **注意**: mock-pve-api は `/cluster/resources` の集約が本番 PVE と異なる場合があります。インベントリ取得はノード単位の `/nodes/{node}/qemu` 列挙のフォールバックを検討してください。
