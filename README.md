# virtual-machine-auto-building
VMを自動で構築する為のシステム案

システム構成のイメージとしては下記

`Frontend -(WAF：ModSecurity)- Backend - Database ＆ Object Storage(Minio,RustFS,versitygw...etc) - DevopsTool/CICDTool(Jenkins, teamcity...etc)`

```
利用する技術スタックは「Terraform」、「Ansible」がメイン
こうしておくことでVMwareやProxmox、Cloud(AWS,Azure,GCP...)などに対応しやすくなると思われる

VirtualMachineの起動や停止、メモリ・CPU変更などの処理はDevopsToolが担う
BackendはDevopsToolに渡すパラメーターファイルの生成、StorageToolへの配置、ログイン認証やユーザー管理などを担う


ゴールデンイメージを予め作成しておき、テンプレート利用する事でセキュリティ強化
Ansibleを利用しておくことで特定のパッチやUpdateをしやすくしておく

更に昨今のランサムウェア攻撃などを考慮してFrontend - Backendの間にWAFTool(ModSecurity)を配置しておきたい

パワーオンやパワーオフ、シャットダウンについては出来るだけAPIを介さずにTerraform,Ansibleで行いたい
リアルタイムに画面反映が必要なものについての手立てがまだ定まっていない
```


↓Chatgptに相談してみる↓

https://chatgpt.com/share/69526ced-64b8-800a-baa0-5f9d533fdb68

# 1. 全体アーキテクチャ（完成形イメージ）
```
[ Frontend ]
   |
   | ① Job作成 / 状態取得（Polling or SSE）
   v
[ Backend API ]
   - Auth / RBAC
   - Parameter生成
   - Job管理（DB）
   - Webhook送信
   |
   | ② 設定ファイル配置
   v
[ Object Storage ]
 (MinIO / RustFS)
   - tfvars
   - inventory
   - playbook vars
   - log
   |
   | ③ Webhook
   v
[ DevOps Tool ]
(Jenkins / TeamCity)
   - Pipeline
   - Terraform
   - Ansible
   |
   | ④ Status/Log push
   v
[ Backend API ]
   |
   v
[ Job DB ]
```

# 2. Job管理の責務分離（超重要）
Backend が持つ責務
Jobの ライフサイクル管理
ユーザー視点の状態定義
進捗の正規化
DevOpsTool が持つ責務
実行
実行結果の通知

👉
「Jenkinsのビルド番号＝Job ID」にはしない
→ Backend の job_id を全てのキーにするのが正解です。


# 3. Jobステータスモデル（実用レベル）

## Job状態（Backend視点）
```
CREATED        ← Job登録
QUEUED         ← Webhook送信済
RUNNING        ← Jenkins/TeamCity開始
PROVISIONING   ← Terraform apply
CONFIGURING    ← Ansible
VERIFYING      ← 確認処理（任意）
SUCCESS
FAILED
CANCELED
```

## DB例
```
jobs
------
job_id (UUID)
job_type        -- CREATE_VM / POWER_ON / UPDATE_VM
status
current_phase
requested_by
devops_job_url
created_at
started_at
finished_at
error_summary
```

```
job_events
-----------
id
job_id
timestamp
level           -- INFO / WARN / ERROR
message
```

# 4. 実際の処理フロー（VM作成例）

### ① Frontend → Backend（Job作成）
```
POST /api/jobs
{
  "type": "CREATE_VM",
  "params": {
    "cpu": 4,
    "memory": 8192,
    "os": "rockylinux9"
  }
}
```

- Backend：<br />
job_id 発行<br />
Jobを CREATED で登録

### ② Backend → Storage（ファイル生成）
```
s3://iac-bucket/jobs/{job_id}/
  ├ terraform.tfvars.json
  ├ inventory.ini
  ├ ansible_vars.yml
```
✔ Terraform / Ansible は job_id だけ知っていればOK

### ③ Backend → DevOpsTool（Webhook）
```
POST https://jenkins/webhook/run

{
  "job_id": "xxxx-xxxx",
  "bucket": "iac-bucket",
  "path": "jobs/xxxx-xxxx",
  "operation": "CREATE_VM"
}
```

- Backend：<br />
job status → QUEUED

### ④ DevOpsTool Pipeline（実行）
Jenkins Pipeline（概念）
```
pipeline {
  stages {
    stage('Start') {
      steps {
        notify('RUNNING', 'Job started')
      }
    }

    stage('Terraform Apply') {
      steps {
        notify('PROVISIONING', 'Terraform apply started')
        sh "terraform apply -var-file=tfvars.json -auto-approve"
      }
    }

    stage('Ansible') {
      steps {
        notify('CONFIGURING', 'Ansible started')
        sh "ansible-playbook -i inventory.ini site.yml"
      }
    }
  }
  post {
    success {
      notify('SUCCESS', 'Completed successfully')
    }
    failure {
      notify('FAILED', 'Execution failed')
    }
  }
}
```

### ⑤ DevOpsTool → Backend（ステータスPush）
```
POST /api/jobs/{job_id}/events
{
  "status": "PROVISIONING",
  "message": "Creating VM"
}
```
✔ ここが疑似リアルタイムの要


# 5. フロントエンドのポーリング設計
ポーリングAPI
```
GET /api/jobs/{job_id}
```

レスポンス例：
```
{
  "job_id": "xxxx",
  "status": "CONFIGURING",
  "current_phase": "Ansible",
  "progress": 65,
  "last_message": "Installing security patches"
}
```
- ポーリング間隔<br />
2〜5秒（十分）
Job完了後は停止

# 6. Terraform / Ansible の「進捗感」を出すコツ
- Terraform
- - phase 単位で進捗を切る
- - apply 前後で通知

```shell:
10%  Terraform init
40%  Terraform apply
```

- Ansible
- - callback plugin で task 開始/完了を通知
- - role 単位で progress を加算

👉 「正確さ」より「納得感」

# 7. この構成の強み

- ✔ マルチ基盤対応しやすい
- ✔ DevOpsTool差し替え可能
- ✔ Backendが一切Terraform/Ansibleを知らなくてよい
- ✔ リトライ・再実行・監査ログが容易
- ✔ 将来Argo / GitOps にも寄せられる

# 8. よくある失敗と回避策


| 失敗                          | 回避           |
| --------------------------- | ------------ |
| Jenkins状態を直接参照              | Backendに必ず集約 |
| Terraform state をBackendで管理 | Storageに集約   |
| リアルタイムに拘りすぎる                | 疑似で十分        |
| Job粒度が粗すぎる                  | Phase設計を丁寧に  |



