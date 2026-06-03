FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

ARG TERRAFORM_VERSION=1.9.8
ARG USERNAME=vscode

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y --no-install-recommends \
        unzip curl openssh-client git ansible \
    && curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
        -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
