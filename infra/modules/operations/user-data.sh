#!/usr/bin/env bash
set -euo pipefail
# libicu, krb5-libs, openssl-libs, zlib and libstdc++ are the runner's .NET dependencies;
# GitHub's installdependencies.sh does not recognise Amazon Linux 2023.
dnf install -y docker git python3 unzip jq tar awscli-2 libicu krb5-libs openssl-libs zlib libstdc++
systemctl enable --now docker
systemctl enable --now amazon-ssm-agent

# Pinned, checksum-verified release tooling for the trusted main-only runner.
KUBECTL_VERSION=v1.35.9
KUBECTL_SHA256=3cfeaf80be482b435b0aa214aff6e0b2c312ee23c0ff20810c75517b6004c6eb
curl -fsSLo /tmp/kubectl "https://dl.k8s.io/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl"
echo "$KUBECTL_SHA256  /tmp/kubectl" | sha256sum -c -
install -m 0755 /tmp/kubectl /usr/local/bin/kubectl

RUNNER_VERSION=2.338.0
RUNNER_SHA256=af4b794c1bc41d73d40535e3fe092a39f9679cd8d965954c2aca25a05ca41d32
useradd --create-home --shell /bin/bash runner
mkdir -p /opt/actions-runner
curl -fsSLo /tmp/runner.tar.gz "https://github.com/actions/runner/releases/download/v$RUNNER_VERSION/actions-runner-linux-x64-$RUNNER_VERSION.tar.gz"
echo "$RUNNER_SHA256  /tmp/runner.tar.gz" | sha256sum -c -
tar -xzf /tmp/runner.tar.gz -C /opt/actions-runner
chown -R runner:runner /opt/actions-runner
touch /opt/actions-runner/.mybank-ready
# Registration happens later through scripts/demo; no tokens or credentials live here.
