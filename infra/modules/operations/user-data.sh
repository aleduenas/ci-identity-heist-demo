#!/usr/bin/env bash
set -euo pipefail
dnf install -y docker git python3 unzip jq
systemctl enable --now docker
systemctl enable --now amazon-ssm-agent
# Install/register the trusted GitHub runner explicitly after host review.
# Do not embed registration tokens, AWS credentials, or lab API keys here.
