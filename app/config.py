from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "dev-secret"
    database_url: str = "postgresql+asyncpg://vmapp:vmapp@localhost:5432/vmapp"

    rustfs_endpoint: str = "http://localhost:9000"
    rustfs_access_key: str = "rustfsadmin"
    rustfs_secret_key: str = "rustfsadmin"
    rustfs_bucket_projects: str = "vm-projects"

    aws_endpoint_url: str = "http://localhost:4566"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_default_region: str = "us-east-1"

    azure_storage_account: str = "devstoreaccount1"
    azure_storage_key: str = ""
    azure_blob_endpoint: str = "http://localhost:4577/devstoreaccount1"
    azure_queue_endpoint: str = "http://localhost:4577/devstoreaccount1-queue"
    azure_table_endpoint: str = "http://localhost:4577/devstoreaccount1-table"

    proxmox_api_url: str = "https://localhost:8006"
    proxmox_user: str = "root@pam"
    proxmox_password: str = "secret"
    proxmox_api_token: str = "root@pam!test=secret"
    proxmox_insecure: bool = True

    vsphere_url: str = "https://localhost:8989/sdk"
    vsphere_user: str = "user"
    vsphere_password: str = "pass"
    vsphere_insecure: bool = True


settings = Settings()
