# Local AWS operator session

The AWS CLI is installed in the ignored `.tools/aws-cli/portable` directory from
the official Amazon-signed Windows installer. No long-lived access key is used.

In PowerShell, from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. ./scripts/aws/session.ps1
aws login --profile codex-builder-login --remote --region ca-central-1
aws sts get-caller-identity
```

The execution-policy setting applies only to that terminal process. Alternatively,
use the Python wrapper without changing any PowerShell execution policy:

```powershell
.venv/Scripts/python.exe -m scripts.aws.run aws sts get-caller-identity
```

The verified Session Manager plugin is also available through this environment
for private EKS access via the operations host.

The login profile uses temporary browser-authorized credentials. The
`codex-builder` profile exposes those credentials through AWS CLI's process
provider for SDKs and Terraform. Local configuration and refresh credentials
remain under ignored `.cache/aws/`; do not commit or print their contents.
Login may need to be repeated when its session expires.

Check the caller account and identity before provisioning. Budget/expiry
protection must be deployed and verified before the chargeable D2 lab.
