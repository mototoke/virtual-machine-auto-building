# Azure (floci-az) 向け Terraform / ARM

ローカル開発では Azurite 互換アカウント `devstoreaccount1` と floci-az のエンドポイントを使用します。

環境変数（`.env` 参照）:

- `AZURE_BLOB_ENDPOINT=http://floci-az:4577/devstoreaccount1`
- `AZURE_STORAGE_ACCOUNT=devstoreaccount1`
- `AZURE_STORAGE_KEY=...`（Azurite 既定キー）

`azurerm` provider の `storage_use_azuread = false` とカスタムエンドポイント設定で接続できます。VM 払い出しは Azure Compute Emulator が必要な場合は、将来 Floci エコシステムの拡張または実サブスクリプション検証環境と併用してください。
