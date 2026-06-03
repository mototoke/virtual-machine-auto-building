# ローカルエミュレータ疎通確認 (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "== Floci (AWS) =="
try { Invoke-WebRequest -Uri "http://localhost:4566/_localstack/health" -UseBasicParsing | Out-Null; "OK" } catch { "FAIL" }

Write-Host "== Floci-az (Azure) =="
try { Invoke-WebRequest -Uri "http://localhost:4577/" -UseBasicParsing | Out-Null; "OK" } catch { "FAIL" }

Write-Host "== mock-pve (Proxmox) =="
try {
  $r = Invoke-WebRequest -Uri "https://localhost:8006/api2/json/version" -SkipCertificateCheck -UseBasicParsing
  $r.Content.Substring(0, [Math]::Min(120, $r.Content.Length))
} catch { "FAIL: $_" }

Write-Host "Done."
