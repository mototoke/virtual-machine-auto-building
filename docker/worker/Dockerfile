FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip openssh-client git \
    && rm -rf /var/lib/apt/lists/*

# Terraform
ARG TERRAFORM_VERSION=1.9.8
RUN curl -fsSL "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    -o /tmp/terraform.zip \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm /tmp/terraform.zip

WORKDIR /app

COPY pyproject.toml README.md ./
COPY worker ./worker
COPY infra ./infra

RUN pip install --no-cache-dir -e ".[worker]"

EXPOSE 9002

CMD ["uvicorn", "worker.main:app", "--host", "0.0.0.0", "--port", "9002"]
