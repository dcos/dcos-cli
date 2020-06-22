provider "aws" {}

variable "custom_dcos_download_path" {
  type    = "string"
  default = "https://downloads.mesosphere.com/dcos-enterprise/testing/master/dcos_generate_config.ee.sh"
}

variable "variant" {
  type    = "string"
  default = "ee"
}

variable "dcos_security" {
  type    = "string"
  default = "strict"
}

variable "owner" {
  type    = "string"
  default = "dcos-core-cli"
}

variable "expiration" {
  type    = "string"
  default = "2h"
}

variable "ssh_public_key_file" {
  type        = "string"
  default     = "~/.ssh/id_rsa.pub"
  description = "Defines the public key to log on the cluster."
}

variable "dcos_license_key_contents" {
  type        = "string"
  default     = ""
  description = "Defines content of license used for EE."
}

variable "instance_type" {
  type        = "string"
  default     = "m5.large"
  description = "Defines type of used machine."
}

variable "build_id" {
  type        = "string"
  default     = ""
  description = "Build ID from CI."
}

variable "build_type" {
  type        = "string"
  default     = ""
  description = "Build type from CI."
}

variable "dcos_user" {
  type        = "string"
  default     = "bootstrapuser"
  description = "DC/OS Superuser."
}

variable "dcos_pass_hash" {
  type        = "string"
  default     = "$6$rounds=656000$YSvuFmasQDXheddh$TpYlCxNHF6PbsGkjlK99Pwxg7D0mgWJ.y0hE2JKoa61wHx.1wtxTAHVRHfsJU9zzHWDoE08wpdtToHimNR9FJ/"
  description = "DC/OS Superuser Password Hash."
}

resource "random_string" "password" {
  length  = 12
  special = false
}

locals {
  cluster_name = "generic-dcos-it-${random_string.password.result}"
}

module "dcos" {
  source  = "dcos-terraform/dcos/aws"
  version = "~> 0.2.0"

  providers = {
    aws = "aws"
  }

  tags {
    owner         = "${var.owner}"
    expiration    = "${var.expiration}"
    build_id      = "${var.build_id}"
    build_type_id = "${var.build_type}"
  }

  cluster_name        = "${local.cluster_name}"
  ssh_public_key_file = "${var.ssh_public_key_file}"
  admin_ips           = ["0.0.0.0/0"]

  num_masters        = "1"
  num_private_agents = "1"
  num_public_agents  = "1"

  dcos_instance_os = "centos_7.5"

  masters_instance_type        = "${var.instance_type}"
  private_agents_instance_type = "${var.instance_type}"
  public_agents_instance_type  = "${var.instance_type}"

  dcos_variant              = "${var.variant}"
  dcos_security             = "${var.dcos_security}"
  dcos_license_key_contents = "${var.dcos_license_key_contents}"

  custom_dcos_download_path = "${var.custom_dcos_download_path}"

  dcos_superuser_username      = "${var.dcos_user}"
  dcos_superuser_password_hash = "${var.dcos_pass_hash}"
}

output "master_public_ip" {
  description = "This is the public masters IP to SSH"
  value       = "${element(module.dcos.infrastructure.masters.public_ips, 0)}"
}