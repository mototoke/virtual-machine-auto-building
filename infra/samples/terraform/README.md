# Terraform サンプル配置

RustFS バケット `vm-projects` に以下のようにアップロードすると worker が検知します。

```
s3://vm-projects/projects/terraform/{project_id}/main.tf
s3://vm-projects/projects/terraform/{project_id}/variables.tf
```

プロジェクト ID は Web UI で作成した ID を使用してください。
