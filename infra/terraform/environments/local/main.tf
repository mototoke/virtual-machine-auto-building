terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    vsphere = {
      source  = "hashicorp/vsphere"
      version = "~> 2.8"
    }
  }
}

# --- AWS (Floci ローカルエミュレータ) ---
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    ec2 = var.aws_endpoint
    s3  = var.aws_endpoint
  }
}

# --- vSphere (vcsim) ---
provider "vsphere" {
  user                 = var.vsphere_user
  password             = var.vsphere_password
  vsphere_server       = var.vsphere_server
  allow_unverified_ssl = true
}

variable "aws_region" {
  default = "us-east-1"
}

variable "aws_endpoint" {
  default = "http://floci:4566"
}

variable "vsphere_server" {
  default = "vcsim"
}

variable "vsphere_user" {
  default = "user"
}

variable "vsphere_password" {
  default = "pass"
}

variable "vm_name_prefix" {
  default = "auto-vm"
}

# 例: vcsim 上のリソースプールに VM リソース定義（実環境に合わせて data ソースを調整）
data "vsphere_datacenter" "dc" {
  name = "DC0"
}

data "vsphere_datastore" "ds" {
  name          = "LocalDS_0"
  datacenter_id = data.vsphere_datacenter.dc.id
}

data "vsphere_resource_pool" "pool" {
  name          = "Resources"
  datacenter_id = data.vsphere_datacenter.dc.id
}

resource "vsphere_virtual_machine" "vm" {
  count            = var.vm_count
  name             = "${var.vm_name_prefix}-${count.index}"
  resource_pool_id = data.vsphere_resource_pool.pool.id
  datastore_id     = data.vsphere_datastore.ds.id
  num_cpus         = 1
  memory           = 1024
  guest_id         = "otherGuest64"
  network_interface {
    network_id = data.vsphere_network.default.id
  }
  disk {
    label = "disk0"
    size  = 20
  }
}

data "vsphere_network" "default" {
  name          = "VM Network"
  datacenter_id = data.vsphere_datacenter.dc.id
}

variable "vm_count" {
  type    = number
  default = 1
}

output "vm_ids" {
  value = vsphere_virtual_machine.vm[*].id
}
